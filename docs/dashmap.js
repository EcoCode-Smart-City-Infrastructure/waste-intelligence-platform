/* Live City Operations Map — real map, not the old SVG grid.
   Why the old map looked blank/sparse on phones: it was an SVG schematic
   with no map tiles at all, borough labels at fixed SVG positions that
   did not line up with the dots, and a full innerHTML rebuild on every
   replay tick (that rebuild is what blinked). This map fixes all three:
   - Real tiles: CARTO Dark Matter (matches the dark ops theme) with an
     automatic OpenStreetMap Standard fallback if CARTO tiles error.
   - Connection validation, shown in the status pill, not hidden:
     tile loads, tile errors, library load failure, and a Retry button.
   - No blink: the Leaflet map is created ONCE and markers are updated
     in place (setLatLng/setStyle) on replay/fleet changes; the map is
     never rebuilt, and invalidateSize() runs only when the view becomes
     visible or the window resizes (debounced).
   - Lazy: Leaflet loads only when the dashboard is first shown.
   Data honesty: markers are the demo fleet (labelled demo), with live
   DSNY tonnage in the KPI/charts beside it. Tap a marker -> Forecasting. */
(function(){
'use strict';
const $d = s => document.querySelector(s);
const escD = s => String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
let map = null, layers = null, pulseTimer = null, pulseIdx = 0, tileErrors = 0, tileLoads = 0, tileOk = false, switched = false, inited = false, fitted = false;
const BORO_C = {Manhattan:[40.7831,-73.9712],Brooklyn:[40.6782,-73.9442],Queens:[40.7282,-73.7949],Bronx:[40.8448,-73.8648],'Staten Island':[40.5795,-74.1502]};
function colorOf(f){ return f>=80 ? '#f87171' : f>=60 ? '#f59e0b' : '#22c55e'; }
function status(msg, bad){
  const el = $d('#dashMapStatus'); if(el){ el.textContent = msg; el.className = 'pill' + (bad ? ' bad' : ''); }
  const badge = $d('#dashGridBadge'); if(badge) badge.textContent = msg;
}
function loadLeaflet(){
  if(window.L) return Promise.resolve(true);
  if(loadLeaflet.p) return loadLeaflet.p;
  loadLeaflet.p = new Promise(res=>{
    const link = document.createElement('link'); link.rel='stylesheet'; link.href='https://unpkg.com/leaflet@1.9.4/dist/leaflet.css'; document.head.appendChild(link);
    // Wait for the stylesheet (or a short timeout) before resolving:
    // creating the map before its CSS applies leaves tile panes in
    // normal flow, which is how tiles ended up displaced outside the box.
    let done = false; const finish = ()=>{ if(!done){ done = true; res(!!window.L); } };
    link.onload = ()=>{ const sc = document.createElement('script'); sc.src='https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'; sc.onload=finish; sc.onerror=finish; document.body.appendChild(sc); };
    link.onerror = ()=>{ const sc = document.createElement('script'); sc.src='https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'; sc.onload=finish; sc.onerror=finish; document.body.appendChild(sc); };
    setTimeout(()=>{ if(!window.L && !document.querySelector('script[src*="leaflet"]')){ const sc = document.createElement('script'); sc.src='https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'; sc.onload=finish; sc.onerror=finish; document.body.appendChild(sc); } }, 1500);
  });
  return loadLeaflet.p;
}
function setTiles(kind){
  const L = window.L;
  const defs = {
    osm: {url:'https://tile.openstreetmap.org/{z}/{x}/{y}.png', attr:'&copy; OpenStreetMap contributors', name:'OpenStreetMap'},
    voyager: {url:'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', attr:'&copy; OpenStreetMap contributors &copy; CARTO', name:'CARTO Voyager'},
    carto: {url:'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', attr:'&copy; OpenStreetMap contributors &copy; CARTO', name:'CARTO Dark'}
  };
  tileErrors = 0; tileLoads = 0; tileOk = false;
  if(layers.base) map.removeLayer(layers.base);
  layers.base = L.tileLayer(defs[kind].url, {maxZoom:19, attribution:defs[kind].attr, subdomains:'abcd'});
  layers.base.on('tileload', ()=>{
    tileLoads++;
    // Do not claim "live" on a single tile: require several successful
    // loads with no errors, so a lone cached/transparent tile cannot
    // masquerade as a populated map (the overhaul22 defect).
    if(!tileOk && tileLoads>=4 && tileErrors===0){ tileOk = true; status('Map tiles live: ' + defs[kind].name); }
  });
  layers.base.on('tileerror', ()=>{
    tileErrors++;
    if(kind!=='osm' && tileErrors>=5 && !switched){ switched = true; status('Tiles failing — switched to OpenStreetMap', true); setTiles('osm'); }
    else if(kind==='osm' && tileErrors>=10){ status('Map tiles failing — check connection', true); }
  });
  layers.base.addTo(map);
  status('Map tiles loading… (' + defs[kind].name + ')');
  setTimeout(()=>{ if(!tileOk && !switched) status('Map tiles loading… (slow connection?)'); }, 6000);
}
function fleetNow(){
  const fl = (typeof fleet !== 'undefined') ? fleet : (window.wipFleet ? window.wipFleet() : []);
  const fillFn = (typeof dashFill === 'function') ? dashFill : (b=>b.fill);
  return fl.map(b=>({...b, _fill: fillFn(b)}));
}
function render(){
  if(!map || !layers) return;
  const showFleet = $d('#dashLayerFleet')?.checked!==false;
  const showRoute = $d('#dashLayerRoute')?.checked!==false;
  const showHeat = $d('#dashLayerHeat')?.checked!==false;
  const showLabels = $d('#dashLayerLabels')?.checked!==false;
  const bins = fleetNow();
  const byId = {};
  layers.markers.eachLayer(m=>{ byId[m.options._binId] = m; });
  const seen = new Set();
  if(showFleet){
    bins.forEach(b=>{
      seen.add(b.id);
      const r = showHeat ? 5 + b._fill/12 : 7;
      const style = {radius:r, color:'#0f172a', weight:1.5, fillColor:colorOf(b._fill), fillOpacity:0.95};
      let m = byId[b.id];
      if(m){ m.setLatLng([b.lat,b.lon]); m.setStyle(style); }
      else{
        m = window.L.circleMarker([b.lat,b.lon], {...style, _binId:b.id});
        m.bindPopup(`<strong>${escD(b.id)}</strong><br>${escD(b.site)}, ${escD(b.borough)}<br>Fill ${b._fill}%<br><a href="#forecast?bin=${encodeURIComponent(b.id)}">Open forecast →</a>`);
        m.addTo(layers.markers);
      }
      m.setPopupContent(`<strong>${escD(b.id)}</strong><br>${escD(b.site)}, ${escD(b.borough)}<br>Fill ${b._fill}%<br><a href="#forecast?bin=${encodeURIComponent(b.id)}">Open forecast →</a>`);
    });
  }
  layers.markers.eachLayer(m=>{ if(!seen.has(m.options._binId)) layers.markers.removeLayer(m); });
  const urgent = bins.filter(b=>b._fill>=80).sort((a,b)=>b._fill-a._fill);
  if(layers.route) { map.removeLayer(layers.route); layers.route = null; }
  if(showRoute && urgent.length>1){
    layers.route = window.L.polyline(urgent.map(b=>[b.lat,b.lon]), {color:'#ec4899', weight:3, dashArray:'12 8', opacity:0.9}).addTo(map);
  }
  layers.labels.clearLayers();
  if(showLabels){
    Object.entries(BORO_C).forEach(([name, ll])=>{
      window.L.marker(ll, {icon: window.L.divIcon({className:'sap-map-label', html:escD(name), iconSize:[110,20], iconAnchor:[55,10]}), interactive:false}).addTo(layers.labels);
    });
  }
  // Frame the fleet on first render so markers are spread across the
  // view instead of clustered — a fixed centre/zoom left them bunched
  // when the container size differed from the assumed one.
  if(!fitted && bins.length){
    fitted = true;
    try{ map.fitBounds(window.L.latLngBounds(bins.map(b=>[b.lat,b.lon])), {padding:[24,24]}); }catch(e){}
  }
  // Note text (kept from the old grid so replay behaviour is unchanged)
  const hour = (typeof dashReplayHour !== 'undefined') ? dashReplayHour : 47;
  const note = $d('#dashGridNote');
  if(note){
    const top = urgent[0];
    note.innerHTML = hour<47
      ? `Replay: hour ${hour} of the last 48 (demo history, not live now). Urgent at that hour: ${urgent.length?urgent.map(b=>escD(b.id)).join(', '):'none'}. Move the slider to 47 for now.`
      : (top ? `Urgent route: ${urgent.map(b=>escD(b.id)).join(' → ')}. Tap any marker for its forecast.` : 'No urgent bins right now — the route layer appears when a bin reaches 80%.');
  }
  // Pulse marker travelling the urgent route
  if(layers.pulse) { map.removeLayer(layers.pulse); layers.pulse = null; }
  if(pulseTimer) { clearInterval(pulseTimer); pulseTimer = null; }
  const paused = $d('#view-dashboard .dash-hero')?.classList.contains('paused');
  if(showRoute && urgent.length>1 && !paused){
    const pts = urgent.map(b=>[b.lat,b.lon]);
    layers.pulse = window.L.circleMarker(pts[0], {radius:7, color:'#22c55e', weight:2, fillColor:'#22c55e', fillOpacity:1}).addTo(map);
    pulseIdx = 0;
    pulseTimer = setInterval(()=>{
      if(!layers.pulse) return;
      pulseIdx = (pulseIdx+1) % (pts.length*20);
      const seg = Math.floor(pulseIdx/20), t = (pulseIdx%20)/20;
      const a = pts[seg], c = pts[Math.min(seg+1, pts.length-1)];
      layers.pulse.setLatLng([a[0]+(c[0]-a[0])*t, a[1]+(c[1]-a[1])*t]);
    }, 120);
  }
}
async function init(){
  const el = $d('#dashLiveMap'); if(!el) return;
  if(map){ try{ map.invalidateSize(); }catch(e){} render(); return; }
  status('Loading map library…');
  const ok = await loadLeaflet();
  if(!ok || !window.L){
    status('Map library failed to load — check connection, then Retry', true);
    const note = $d('#dashGridNote'); if(note) note.innerHTML = 'The map library (Leaflet, from unpkg) did not load. <button class="btn" id="dashMapRetry">Retry map</button>';
    $d('#dashMapRetry')?.addEventListener('click', ()=>{ inited = false; init(); });
    return;
  }
  map = window.L.map(el, {zoomControl:true, scrollWheelZoom:false}).setView([40.7128,-74.006], 11);
  layers = {markers: window.L.layerGroup().addTo(map), labels: window.L.layerGroup().addTo(map), base:null, route:null, pulse:null};
  // Default is OpenStreetMap Standard: it is the provider that already
  // proved itself live in the Collection Network map, needs no key, and
  // shows streets/water unmistakably. CARTO (Voyager/Dark) is offered as
  // an option, but in the overhaul23 check its tiles came back as
  // watermark/placeholder images for anonymous requests — if you pick
  // CARTO and see watermark tiles, switch back to OpenStreetMap.
  setTiles($d('#dashTile')?.value || 'osm');
  $d('#dashTile')?.addEventListener('change', ()=>{ switched = false; setTiles($d('#dashTile').value); });
  $d('#dashRecentre')?.addEventListener('click', ()=>{
    try{ map.invalidateSize(); }catch(e){}
    const bins = fleetNow();
    if(bins.length){ try{ map.fitBounds(window.L.latLngBounds(bins.map(b=>[b.lat,b.lon])), {padding:[24,24]}); }catch(e){} }
    try{ layers.base && layers.base.redraw(); }catch(e){}
    render();
  });
  render();
  setTimeout(()=>{ try{ map.invalidateSize(); }catch(e){} }, 150);
  setTimeout(()=>{ try{ map.invalidateSize(); }catch(e){} try{ layers.base && layers.base.redraw(); }catch(e){} }, 600);
  inited = true;
}
let resizeTimer = null;
window.addEventListener('resize', ()=>{ clearTimeout(resizeTimer); resizeTimer = setTimeout(()=>{ if(map && !$d('#view-dashboard')?.classList.contains('hidden')){ try{ map.invalidateSize(); }catch(e){} } }, 200); });
window.addEventListener('hashchange', ()=>{ if((location.hash||'#dashboard').split('?')[0]==='#dashboard') setTimeout(init, 30); });
window.wipDashMap = {init, render, get inited(){ return inited; }};
if(document.readyState!=='loading' && (location.hash||'#dashboard').split('?')[0]==='#dashboard') setTimeout(init, 50);
})();
