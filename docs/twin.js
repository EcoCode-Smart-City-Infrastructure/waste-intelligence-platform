/* Digital Twin + AR infrastructure (preview).
   What this is: a 3D scene and an AR entry point that are READY for a
   live feed, running today on the labelled demo fleet. What it is not:
   live telemetry, surveyed buildings, or a working AR session on a
   device that does not support WebXR AR. Every live claim is gated on
   an actual feed fetch succeeding; every AR claim is gated on the
   device reporting support. No data is invented to fill a gap. */
(function(){
'use strict';
let renderer=null, scene=null, camera=null, markers=[], twinBins=[], feedLive=false, feedUrl='', twinReady=false, twinLoading=false;
let theta=0.9, phi=1.05, radius=90, dragging=false, lastX=0, lastY=0, arSession=null;

function esc(s){return String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function $(id){return document.getElementById(id);}
function statusColor(f){return f>=80?0xec4899:f>=60?0xf59e0b:0x22c55e;}
function statusCss(f){return f>=80?'#ec4899':f>=60?'#f59e0b':'#22c55e';}
// Same mapping family as the 2D grid (dashXY): lon/lat -> scene plane.
function twinXY(lat, lon){const x=((lon+74.25)/0.55)*100-50, z=((40.90-lat)/0.40)*80-40; return [x, z];}

/* Feed contract parsing: array | {bins:[]} | GeoJSON FeatureCollection.
   Returns {bins:[{id,lat,lon,fill,site?}], skipped:number}. Rows missing
   id/lat/lon/fill are skipped and counted, never invented. */
function wiParseFeed(json){
  let rows=[];
  if(Array.isArray(json)) rows=json;
  else if(json&&Array.isArray(json.bins)) rows=json.bins;
  else if(json&&json.type==='FeatureCollection'&&Array.isArray(json.features)) rows=json.features.map(f=>({id:f.properties&&f.properties.id, site:f.properties&&f.properties.site, fill:f.properties&&f.properties.fill, lon:f.geometry&&f.geometry.coordinates&&f.geometry.coordinates[0], lat:f.geometry&&f.geometry.coordinates&&f.geometry.coordinates[1]}));
  else return {bins:[], skipped:0, error:'Feed did not match the contract: expected an array, {"bins":[...]}, or a GeoJSON FeatureCollection.'};
  let skipped=0; const bins=[];
  rows.forEach(r=>{
    const id=r&&r.id!=null?String(r.id):'';
    if(r==null||r.lat==null||r.lon==null||r.fill==null||r.lat===''||r.lon===''||r.fill===''){skipped++; return;}
    const lat=+r.lat, lon=+r.lon, fill=+r.fill;
    if(!id||!isFinite(lat)||!isFinite(lon)||!isFinite(fill)){skipped++; return;}
    bins.push({id:id, site:r.site?String(r.site):id, lat:lat, lon:lon, fill:Math.max(0,Math.min(100,fill))});
  });
  return {bins:bins, skipped:skipped, error:''};
}

function renderBinList(){
  const ul=$('twinBinList'); if(!ul) return;
  ul.innerHTML=twinBins.map(b=>`<li><a href="#forecast?bin=${esc(b.id)}">${esc(b.id)}</a> — ${esc(b.site||b.id)} · <strong style="color:${statusCss(b.fill)}">${b.fill}%</strong></li>`).join('')||'<li class="muted small">No bins in this scene.</li>';
}
function setBadge(){
  const badge=$('twinFeedBadge'); if(!badge) return;
  badge.textContent=feedLive?('LIVE FEED · '+(feedUrl.replace(/^https?:\/\//,'').split('/')[0])):'DEMO FLEET · no live feed';
  badge.className='pill'+(feedLive?'':' warn');
}
function buildMarkers(){
  if(!scene) return;
  markers.forEach(m=>scene.remove(m.group)); markers=[];
  const THREE=window.THREE;
  twinBins.forEach(b=>{
    const [x,z]=twinXY(b.lat,b.lon);
    const group=new THREE.Group();
    const h=1+ (b.fill/100)*5;
    const mat=new THREE.MeshLambertMaterial({color:statusColor(b.fill)});
    const bar=new THREE.Mesh(new THREE.BoxGeometry(1.6,h,1.6), mat);
    bar.position.y=h/2; group.add(bar);
    const cap=new THREE.Mesh(new THREE.ConeGeometry(1.2,1.6,4), mat);
    cap.position.y=h+0.8; group.add(cap);
    group.position.set(x,0,z);
    group.userData.binId=b.id;
    scene.add(group); markers.push({group:group, bin:b});
  });
}
function buildCity(){
  const THREE=window.THREE;
  const ground=new THREE.Mesh(new THREE.PlaneGeometry(120,100), new THREE.MeshLambertMaterial({color:0x1d2b22}));
  ground.rotation.x=-Math.PI/2; scene.add(ground);
  // Illustrative blocks only: deterministic heights from block index,
  // labelled as such on the page. NOT surveyed building data.
  for(let i=0;i<28;i++){
    const bx=-52+(i%7)*16, bz=-40+Math.floor(i/7)*20;
    const h=4+((i*37)%40);
    const block=new THREE.Mesh(new THREE.BoxGeometry(10,h,12), new THREE.MeshLambertMaterial({color:0x36564c}));
    block.position.set(bx,h/2,bz); scene.add(block);
  }
  scene.add(new THREE.AmbientLight(0xffffff,0.85));
  const sun=new THREE.DirectionalLight(0xffffff,0.7); sun.position.set(40,60,20); scene.add(sun);
}
function updateCamera(){
  if(!camera) return;
  const tx=0, ty=6, tz=0;
  camera.position.set(tx+radius*Math.sin(phi)*Math.sin(theta), ty+radius*Math.cos(phi), tz+radius*Math.sin(phi)*Math.cos(theta));
  camera.lookAt(tx,ty,tz);
}
function setCam(kind){
  if(kind==='top'){phi=0.15; theta=0.9; radius=110;}
  else if(kind==='street'){phi=1.45; theta=0.9; radius=34;}
  else {phi=1.05; theta=0.9; radius=90;}
  updateCamera();
}
function initScene(){
  const THREE=window.THREE;
  const wrap=$('twinCanvasWrap'); wrap.innerHTML='';
  renderer=new THREE.WebGLRenderer({antialias:true});
  renderer.setSize(wrap.clientWidth||600, 420);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio||1,2));
  wrap.appendChild(renderer.domElement);
  scene=new THREE.Scene(); scene.background=new THREE.Color(0x0f1d16);
  camera=new THREE.PerspectiveCamera(55,(wrap.clientWidth||600)/420,0.1,1000);
  buildCity(); buildMarkers(); setCam('reset');
  renderer.setAnimationLoop(()=>{ if(renderer) renderer.render(scene,camera); });
  const el=renderer.domElement;
  el.addEventListener('pointerdown',e=>{dragging=true; lastX=e.clientX; lastY=e.clientY;});
  window.addEventListener('pointerup',()=>dragging=false);
  window.addEventListener('pointermove',e=>{ if(!dragging) return; theta-=(e.clientX-lastX)*0.01; phi=Math.max(0.15,Math.min(1.5,phi-(e.clientY-lastY)*0.01)); lastX=e.clientX; lastY=e.clientY; updateCamera(); });
  el.addEventListener('wheel',e=>{e.preventDefault(); radius=Math.max(20,Math.min(180,radius+e.deltaY*0.08)); updateCamera();},{passive:false});
  el.addEventListener('click',e=>{
    if(!scene||!camera) return;
    const rect=el.getBoundingClientRect();
    const mouse=new THREE.Vector2(((e.clientX-rect.left)/rect.width)*2-1, -((e.clientY-rect.top)/rect.height)*2+1);
    const ray=new THREE.Raycaster(); ray.setFromCamera(mouse,camera);
    const hits=ray.intersectObjects(markers.map(m=>m.group),true);
    if(hits.length){let o=hits[0].object; while(o&&!o.userData.binId) o=o.parent; if(o&&o.userData.binId) location.hash='#forecast?bin='+o.userData.binId;}
  });
}
function loadThree(cb){
  if(window.THREE) return cb();
  if(twinLoading) return;
  twinLoading=true;
  const tag=document.createElement('script');
  tag.src='https://cdnjs.cloudflare.com/ajax/libs/three.js/0.152.2/three.min.js';
  tag.onload=()=>{twinLoading=false; cb();};
  tag.onerror=()=>{twinLoading=false; const w=$('twinCanvasWrap'); if(w) w.innerHTML='<p class="muted small" style="padding:1rem;color:#cbd3c6">The 3D library could not load (offline or blocked CDN). The 2D city grid on the Dashboard still works — <a href="#dashboard">open it there</a>.</p>';};
  document.head.appendChild(tag);
}
function probeAR(){
  const st=$('twinArStatus'), btn=$('twinArBtn');
  if(!st||!btn) return;
  if(!navigator.xr){st.textContent='WebXR is not available in this browser, so AR cannot start here. On an AR-capable Android phone with Chrome, this probe reports support and the button enables.'; btn.disabled=true; return;}
  try{
    navigator.xr.isSessionSupported('immersive-ar').then(ok=>{
      if(ok){st.textContent='This device and browser report WebXR immersive-ar support. Enter AR to view the same scene in your space. (AR itself is verified on a phone, not by a desktop check.)'; btn.disabled=false;}
      else {st.textContent='This device/browser does not report WebXR immersive-ar support, so AR stays off here. That is the device state, not an app failure.'; btn.disabled=true;}
    }).catch(()=>{st.textContent='The AR capability check failed in this browser, so AR stays off here.'; btn.disabled=true;});
  }catch(e){st.textContent='The AR capability check failed in this browser, so AR stays off here.'; btn.disabled=true;}
}
async function toggleAR(){
  const btn=$('twinArBtn'), st=$('twinArStatus');
  try{
    if(arSession){await arSession.end(); return;}
    if(!renderer) { if(st) st.textContent='Open the 3D scene first (it loads when this view opens), then try AR again.'; return; }
    renderer.xr.enabled=true;
    const session=await navigator.xr.requestSession('immersive-ar',{optionalFeatures:['local-floor','bounded-floor']});
    arSession=session;
    renderer.xr.setSession(session);
    if(btn) btn.textContent='Exit AR';
    if(st) st.textContent='AR session active — the scene is rendered in your space. Exit AR to return to the page.';
    session.addEventListener('end',()=>{arSession=null; if(btn) btn.textContent='Enter AR'; if(st) st.textContent='AR session ended. The 3D scene on this page is unchanged.';});
  }catch(e){
    if(st) st.textContent='AR could not start: '+(e&&e.message?e.message:'the device declined the session.')+' The 3D scene on this page is unchanged.';
  }
}
function wiInitTwin(){
  if(twinReady) return; twinReady=true;
  // Demo fleet first: fleet is defined by app.js (DEFAULT_BINS / saved fleet).
  try{ twinBins=((typeof window.wipFleet==='function'?window.wipFleet():[])||[]).map(b=>({id:b.id, site:b.site, lat:b.lat, lon:b.lon, fill:b.fill})); }catch(e){ twinBins=[]; }
  renderBinList(); setBadge();
  const saved=(()=>{try{return localStorage.getItem('wi_twin_feed_url')||'';}catch(e){return '';}})();
  const urlInput=$('twinFeedUrl'); if(urlInput&&saved) urlInput.value=saved;
  const fs=$('twinFeedStatus'); if(fs&&saved) fs.textContent='A feed URL is saved in this browser. Click Connect feed to try it.';
  loadThree(()=>{ try{initScene(); const s=$('twinStatus'); if(s) s.textContent='3D scene loaded (demo fleet, illustrative buildings). Drag to orbit, scroll to zoom, click a bin marker to open its forecast.';}catch(e){ const w=$('twinCanvasWrap'); if(w) w.innerHTML='<p class="muted small" style="padding:1rem;color:#cbd3c6">The 3D scene failed to start in this browser. The 2D city grid on the Dashboard still works.</p>'; } });
  $('twinCamTop')?.addEventListener('click',()=>setCam('top'));
  $('twinCamStreet')?.addEventListener('click',()=>setCam('street'));
  $('twinCamReset')?.addEventListener('click',()=>setCam('reset'));
  $('twinArBtn')?.addEventListener('click',toggleAR);
  $('twinFeedConnect')?.addEventListener('click',async()=>{
    const url=(urlInput?.value||'').trim();
    if(!url){ if(fs) fs.textContent='Paste a feed URL first.'; return; }
    if(/key=|token=|secret/i.test(url)){ if(fs) fs.textContent='That URL looks like it contains a key or token. Do not paste secrets into a browser field — use a keyless public feed URL instead. Demo fleet unchanged.'; return; }
    if(fs) fs.textContent='Fetching the feed in this browser…';
    try{
      const res=await fetch(url);
      if(!res.ok) throw new Error('HTTP '+res.status);
      const json=await res.json();
      const parsed=wiParseFeed(json);
      if(parsed.error) throw new Error(parsed.error);
      if(!parsed.bins.length) throw new Error('Feed loaded but contained no usable bins (every row was skipped).');
      twinBins=parsed.bins; feedLive=true; feedUrl=url;
      try{localStorage.setItem('wi_twin_feed_url',url);}catch(e){}
      buildMarkers(); renderBinList(); setBadge();
      if(fs) fs.textContent=`LIVE FEED connected: ${parsed.bins.length} bins plotted, ${parsed.skipped} row(s) skipped for missing id/lat/lon/fill. Demo fleet replaced only because this feed actually loaded.`;
    }catch(e){
      if(fs) fs.textContent='Feed failed: '+(e.message||'fetch error')+'. Demo fleet unchanged — check the URL, the contract, and that the feed allows browser (CORS) access.';
    }
  });
  $('twinFeedDisconnect')?.addEventListener('click',()=>{
    try{ twinBins=((typeof window.wipFleet==='function'?window.wipFleet():[])||[]).map(b=>({id:b.id, site:b.site, lat:b.lat, lon:b.lon, fill:b.fill})); }catch(e){ twinBins=[]; }
    feedLive=false; feedUrl='';
    try{localStorage.removeItem('wi_twin_feed_url');}catch(e){}
    if(urlInput) urlInput.value='';
    buildMarkers(); renderBinList(); setBadge();
    if(fs) fs.textContent='Disconnected. Demo fleet restored.';
  });
  probeAR();
}
window.wiInitTwin=wiInitTwin;
window.wiParseFeed=wiParseFeed;
})();
