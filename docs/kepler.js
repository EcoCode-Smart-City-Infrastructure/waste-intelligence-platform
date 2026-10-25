/* Waste Intelligence — Kepler.gl geospatial operations view.
   Real Kepler.gl 3.0.0 (UMD) over the same data the main app uses.
   Fleet logic mirrors app.js exactly (same seeds, same localStorage keys
   wip_fleet / wip_readings), so bins added or collected in Bins & Routes
   show up here, and vice versa. Nothing here is presented as live sensor
   data: the fleet is the labelled demo fleet, tonnage is Socrata live data
   (or the labelled sample fallback), and KG nodes are not geo-plotted
   because they have no coordinates. */
'use strict';
const $ = s => document.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const fmt = n => (n == null || isNaN(n) ? '—' : Number(n).toLocaleString(undefined, { maximumFractionDigits: 1 }));
const statusEl = $('#kepler-status');
function setStatus(html) { if (statusEl) statusEl.innerHTML = html; }
function hideStatus() { if (statusEl) statusEl.classList.add('hidden'); }

/* ---------- fleet: verbatim mirror of app.js ---------- */
function rng(seed) { let a = seed >>> 0; return () => { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
const BOROUGHS = { Manhattan: [40.7831, -73.9712], Brooklyn: [40.6782, -73.9442], Queens: [40.7282, -73.7949], Bronx: [40.8448, -73.8648], 'Staten Island': [40.5795, -74.1502] };
const SITES = { Manhattan: ['Union Square', 'Central Park West', 'Harlem Market', 'Chelsea Piers'], Brooklyn: ['Prospect Park', 'Williamsburg', 'Brooklyn Heights', 'Bushwick'], Queens: ['Astoria', 'Flushing', 'Long Island City'], Bronx: ['Fordham', 'South Bronx Hub', 'Riverdale'], 'Staten Island': ['St. George Ferry', 'New Dorp'] };
const DEFAULT_BINS = [];
{ let i = 0; Object.entries(SITES).forEach(([b, sites]) => sites.forEach((site) => {
  const r = rng(1000 + i * 77); const fill = Math.round(18 + r() * 72);
  DEFAULT_BINS.push({ id: `BIN-${b.slice(0, 2).toUpperCase()}-${100 + i}`, site, borough: b, fill,
    lat: BOROUGHS[b][0] + (r() - 0.5) * 0.06, lon: BOROUGHS[b][1] + (r() - 0.5) * 0.08, _seed: 1000 + i * 77 });
  i++; })); }
let fleet;
try { fleet = JSON.parse(localStorage.getItem('wip_fleet') || 'null') || structuredClone(DEFAULT_BINS); } catch (e) { fleet = structuredClone(DEFAULT_BINS); }
function statusOf(f) { return f >= 80 ? 'urgent' : f >= 60 ? 'watch' : 'ok'; }
function historyFor(bin) {
  const r = rng(bin._seed || 999); const pts = []; let fill = Math.max(8, bin.fill - 38);
  for (let h = 47; h >= 0; h--) { fill = Math.min(98, Math.max(5, fill + 0.7 + r() * 1.1));
    if (h === 20 && r() > 0.4) fill = Math.max(8, fill - 55);
    pts.push({ h: 47 - h, fill: Math.round(fill * 10) / 10 }); }
  pts[pts.length - 1].fill = bin.fill;
  try { const extra = JSON.parse(localStorage.getItem('wip_readings') || '{}')[bin.id] || [];
    extra.forEach((v, k) => pts.push({ h: 48 + k, fill: v })); } catch (e) {}
  return pts;
}
function analyse(pts) {
  let cycle = pts;
  for (let i = pts.length - 1; i > 0; i--) { if (pts[i - 1].fill - pts[i].fill > 30) { cycle = pts.slice(i); break; } }
  const n = cycle.length, mx = cycle.reduce((s, p) => s + p.h, 0) / n, my = cycle.reduce((s, p) => s + p.fill, 0) / n;
  let sxx = 0, sxy = 0, syy = 0; cycle.forEach(p => { sxx += (p.h - mx) ** 2; sxy += (p.h - mx) * (p.fill - my); syy += (p.fill - my) ** 2; });
  const slope = sxx ? sxy / sxx : 0, intercept = my - slope * mx, r2 = (sxx * syy) ? (sxy * sxy) / (sxx * syy) : 0;
  const last = cycle[cycle.length - 1].fill;
  const toFull = slope > 0.05 ? (100 - last) / slope : Infinity;
  return { slope, intercept, r2, last, toFull };
}
function haversine(a, b) { const R = 6371, dLa = (b.lat - a.lat) * Math.PI / 180, dLo = (b.lon - a.lon) * Math.PI / 180;
  const h = Math.sin(dLa / 2) ** 2 + Math.cos(a.lat * Math.PI / 180) * Math.cos(b.lat * Math.PI / 180) * Math.sin(dLo / 2) ** 2; return 2 * R * Math.asin(Math.sqrt(h)); }
function buildRoute(bins) {
  if (bins.length < 2) return { order: bins, dist: 0 };
  const remaining = [...bins], order = [remaining.shift()];
  while (remaining.length) { let best = 0, bd = 1e9; remaining.forEach((c, i) => { const d = haversine(order[order.length - 1], c); if (d < bd) { bd = d; best = i; } }); order.push(remaining.splice(best, 1)[0]); }
  let dist = 0; for (let i = 1; i < order.length; i++) dist += haversine(order[i - 1], order[i]);
  return { order, dist };
}

/* ---------- live tonnage (same query + aggregation as the dashboard) ---------- */
const SAMPLE_TONNAGE = [{ month: '2026 / 09', borough: 'Manhattan', refuse: 48210, paper: 5120, mgp: 2980, organics: 1420 }, { month: '2026 / 09', borough: 'Brooklyn', refuse: 52140, paper: 4980, mgp: 3120, organics: 1180 }, { month: '2026 / 09', borough: 'Queens', refuse: 49880, paper: 4610, mgp: 2890, organics: 960 }, { month: '2026 / 09', borough: 'Bronx', refuse: 38920, paper: 3210, mgp: 1980, organics: 740 }, { month: '2026 / 09', borough: 'Staten Island', refuse: 17450, paper: 1680, mgp: 1040, organics: 410 }];
async function loadTonnage() {
  try {
    const res = await fetch('https://data.cityofnewyork.us/resource/ebb7-mvp5.json?$limit=500&$order=month%20DESC');
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const rows = await res.json(); if (!rows.length) throw new Error('empty');
    const month = rows[0].month; const by = {};
    rows.filter(r => r.month === month).forEach(r => { const b = by[r.borough] || (by[r.borough] = { borough: r.borough, refuse: 0, paper: 0, mgp: 0, organics: 0 });
      b.refuse += +r.refusetonscollected || 0; b.paper += +r.papertonscollected || 0; b.mgp += +r.mgptonscollected || 0; b.organics += (+r.resorganicstons || 0) + (+r.schoolorganictons || 0); });
    return { rows: Object.values(by).sort((a, b) => b.refuse - a.refuse), month, live: true };
  } catch (e) { return { rows: SAMPLE_TONNAGE, month: SAMPLE_TONNAGE[0].month, live: false }; }
}

/* ---------- Kepler datasets + config ---------- */
const GREEN_RANGE = { name: 'Waste fill', type: 'sequential', category: 'Custom', colors: ['#e6f2e9', '#7fb998', '#1d7a4f', '#b7791f', '#b42318'] };
function fields(spec) { return spec.map(([name, type]) => ({ name, type })); }
let timeMin = 0, timeMax = 0;

function buildDatasets(tonnage) {
  const now = Date.now();
  const binFields = fields([['id', 'string'], ['site', 'string'], ['borough', 'string'], ['status', 'string'], ['fill', 'real'], ['lat', 'real'], ['lng', 'real'], ['forecast_hours', 'real'], ['forecast_fill_24h', 'real']]);
  const binRows = fleet.map(b => {
    const a = analyse(historyFor(b));
    const fc24 = Math.min(100, Math.max(0, a.intercept + a.slope * (historyFor(b).length - 1 + 24)));
    return [b.id, b.site, b.borough, statusOf(b.fill), b.fill, b.lat, b.lon, isFinite(a.toFull) ? Math.round(a.toFull * 10) / 10 : -1, Math.round(fc24 * 10) / 10];
  });
  const histFields = fields([['bin_id', 'string'], ['site', 'string'], ['borough', 'string'], ['status', 'string'], ['fill', 'real'], ['timestamp', 'timestamp'], ['hour_offset', 'integer'], ['lat', 'real'], ['lng', 'real']]);
  const histRows = [];
  fleet.forEach(b => {
    const pts = historyFor(b);
    pts.forEach(p => {
      const ts = now - (pts[pts.length - 1].h - p.h) * 3600e3;
      histRows.push([b.id, b.site, b.borough, statusOf(b.fill), p.fill, ts, p.h, b.lat, b.lon]);
    });
  });
  timeMin = Math.min(...histRows.map(r => r[5])); timeMax = Math.max(...histRows.map(r => r[5]));
  const route = buildRoute(fleet.filter(b => b.fill >= 80));
  const routeFields = fields([['from_bin', 'string'], ['to_bin', 'string'], ['stop', 'integer'], ['leg_km', 'real'], ['from_lat', 'real'], ['from_lng', 'real'], ['to_lat', 'real'], ['to_lng', 'real']]);
  const routeRows = [];
  for (let i = 1; i < route.order.length; i++) {
    const a = route.order[i - 1], b = route.order[i];
    routeRows.push([a.id, b.id, i, Math.round(haversine(a, b) * 10) / 10, a.lat, a.lon, b.lat, b.lon]);
  }
  const tonFields = fields([['borough', 'string'], ['month', 'string'], ['refuse', 'real'], ['paper', 'real'], ['mgp', 'real'], ['organics', 'real'], ['total', 'real'], ['lat', 'real'], ['lng', 'real']]);
  const tonRows = tonnage.rows.filter(r => BOROUGHS[r.borough]).map(r => [r.borough, tonnage.month, r.refuse, r.paper, r.mgp, r.organics, r.refuse + r.paper + r.mgp + r.organics, BOROUGHS[r.borough][0], BOROUGHS[r.borough][1]]);
  return {
    datasets: [
      { info: { id: 'bins', label: 'Bins — fill & status (demo fleet)' }, data: { fields: binFields, rows: binRows } },
      { info: { id: 'history', label: 'Bin fill tracking — 48 h' }, data: { fields: histFields, rows: histRows } },
      { info: { id: 'routes', label: 'Urgent collection route' }, data: { fields: routeFields, rows: routeRows } },
      { info: { id: 'tonnage', label: 'Live tonnage by borough' }, data: { fields: tonFields, rows: tonRows } }
    ],
    route
  };
}

function buildConfig() {
  return {
    version: 'v1',
    config: {
      visState: {
        filters: [
          { dataId: 'bins', id: 'borough-filter', name: 'borough', fieldIdx: 2, type: 'multiSelect', value: ['Manhattan', 'Brooklyn', 'Queens', 'Bronx', 'Staten Island'] },
          { dataId: 'bins', id: 'fill-filter', name: 'fill', fieldIdx: 4, type: 'range', value: [0, 100] },
          { dataId: 'history', id: 'time-filter', name: 'timestamp', fieldIdx: 5, type: 'timeRange', value: [timeMin, timeMax], enlarged: true, plotType: { type: 'histogram' } }
        ],
        layers: [
          { id: 'bins-point', type: 'point',
            config: { dataId: 'bins', label: 'Bins — fill & status', color: [29, 122, 79], columns: { lat: 'lat', lng: 'lng', altitude: null }, isVisible: true,
              visConfig: { radius: 12, fixedRadius: false, opacity: 0.85, outline: false, thickness: 2, strokeColor: [255, 255, 255], colorRange: GREEN_RANGE, radiusRange: [0, 50], filled: true } },
            visualChannels: { colorField: { name: 'fill', type: 'real' }, colorScale: 'quantize', sizeField: { name: 'fill', type: 'real' }, sizeScale: 'sqrt' } },
          { id: 'bins-grid', type: 'grid',
            config: { dataId: 'bins', label: 'Fill density — 3D grid', color: [29, 122, 79], columns: { lat: 'lat', lng: 'lng' }, isVisible: false, colorAggregation: 'average', sizeAggregation: 'average',
              visConfig: { opacity: 0.85, colorRange: GREEN_RANGE, worldUnitSize: 1, coverage: 1, sizeRange: [0, 500], elevationScale: 60, enable3d: true } },
            visualChannels: { colorField: { name: 'fill', type: 'real' }, colorScale: 'quantile', sizeField: { name: 'fill', type: 'real' }, sizeScale: 'linear' } },
          { id: 'route-arc', type: 'arc',
            config: { dataId: 'routes', label: 'Urgent collection route', color: [183, 121, 31], columns: { lat0: 'from_lat', lng0: 'from_lng', lat1: 'to_lat', lng1: 'to_lng' }, isVisible: true,
              visConfig: { opacity: 0.85, thickness: 2, colorRange: GREEN_RANGE, sizeRange: [0, 10] } },
            visualChannels: { colorField: { name: 'leg_km', type: 'real' }, colorScale: 'quantize', sizeField: { name: 'leg_km', type: 'real' }, sizeScale: 'sqrt' } },
          { id: 'tonnage-point', type: 'point',
            config: { dataId: 'tonnage', label: 'Live tonnage by borough', color: [37, 99, 235], columns: { lat: 'lat', lng: 'lng', altitude: null }, isVisible: true,
              visConfig: { radius: 30, fixedRadius: false, opacity: 0.75, outline: false, thickness: 2, strokeColor: [255, 255, 255], colorRange: GREEN_RANGE, radiusRange: [0, 50], filled: true } },
            visualChannels: { colorField: { name: 'refuse', type: 'real' }, colorScale: 'quantize', sizeField: { name: 'refuse', type: 'real' }, sizeScale: 'sqrt' } },
          { id: 'history-point', type: 'point',
            config: { dataId: 'history', label: 'Bin fill tracking — 48 h', color: [124, 92, 191], columns: { lat: 'lat', lng: 'lng', altitude: null }, isVisible: false,
              visConfig: { radius: 6, fixedRadius: false, opacity: 0.7, outline: false, thickness: 2, strokeColor: [255, 255, 255], colorRange: GREEN_RANGE, radiusRange: [0, 50], filled: true } },
            visualChannels: { colorField: { name: 'fill', type: 'real' }, colorScale: 'quantize', sizeField: { name: 'fill', type: 'real' }, sizeScale: 'sqrt' } }
        ],
        interactionConfig: {
          tooltip: { enabled: true, fieldsToShow: {
            bins: [{ name: 'id', format: null }, { name: 'site', format: null }, { name: 'borough', format: null }, { name: 'status', format: null }, { name: 'fill', format: null }, { name: 'forecast_hours', format: null }, { name: 'forecast_fill_24h', format: null }],
            tonnage: [{ name: 'borough', format: null }, { name: 'refuse', format: null }, { name: 'paper', format: null }, { name: 'mgp', format: null }, { name: 'organics', format: null }, { name: 'total', format: null }],
            routes: [{ name: 'from_bin', format: null }, { name: 'to_bin', format: null }, { name: 'leg_km', format: null }],
            history: [{ name: 'bin_id', format: null }, { name: 'site', format: null }, { name: 'fill', format: null }]
          } },
          brush: { enabled: false }, geocoder: { enabled: false }, coordinate: { enabled: false }
        },
        layerBlending: 'normal', splitMaps: [], animationConfig: { currentTime: null, speed: 1 }
      },
      mapState: { latitude: 40.73, longitude: -73.94, zoom: 10.2, pitch: 45, bearing: 0, dragRotate: true, isSplit: false },
      mapStyle: {
        // Kepler's built-in 'dark-matter' (CARTO Dark Matter, no token).
        // Do NOT use 'dark'/'light'/'muted' here: those are mapbox:// styles
        // that render a blank canvas without a Mapbox token (verified live
        // twice). Custom mapStyles dict entries were also removed: a custom
        // id did not produce tiles either, and offering it in the picker
        // would only offer another blank choice.
        styleType: 'dark-matter',
        topLayerGroups: {}, visibleLayerGroups: { label: true, road: true, border: true, building: true, water: true, land: true, '3d building': false },
        threeDBuildingColor: [9, 17, 24],
        mapStyles: {}
      }
    }
  };
}

/* ---------- boot Kepler ---------- */
let store = null, KG = null, KeplerComp = null, lastRoute = null, lastTonnage = null;

function resolveKeplerGlobals() {
  KG = window.KeplerGl;
  if (!KG) return 'Kepler.gl script did not define window.KeplerGl.';
  KeplerComp = KG.KeplerGl || KG.default || (typeof KG === 'function' ? KG : null);
  if (!KeplerComp) return 'Kepler.gl loaded but no component export was found (keys: ' + Object.keys(KG).join(', ') + ').';
  if (!KG.keplerGlReducer) return 'Kepler.gl loaded but keplerGlReducer is missing.';
  if (!KG.addDataToMap) return 'Kepler.gl loaded but addDataToMap is missing.';
  return null;
}

function createStore() {
  const reducers = window.Redux.combineReducers({ keplerGl: KG.keplerGlReducer });
  // Kepler's enhanceReduxMiddleware changed shape across versions (a single
  // middleware in some, an array of middlewares in others). Passing an array
  // to applyMiddleware as if it were one middleware throws inside Redux, so
  // accept either shape here instead of assuming one.
  let enhancer = null;
  if (KG.enhanceReduxMiddleware) {
    const res = KG.enhanceReduxMiddleware([]);
    if (Array.isArray(res)) enhancer = window.Redux.applyMiddleware(...res);
    else if (typeof res === 'function') enhancer = window.Redux.applyMiddleware(res);
  }
  store = enhancer ? window.Redux.createStore(reducers, {}, enhancer)
                   : window.Redux.createStore(reducers, {});
}

function mountKepler() {
  const token = (() => { try { return localStorage.getItem('wip_mapbox_token') || ''; } catch (e) { return ''; } })();
  const tokenInput = $('#mapboxToken'); if (tokenInput && token) tokenInput.value = token;
  const e = window.React.createElement;
  function App() {
    const [size, setSize] = window.React.useState({ w: window.innerWidth, h: Math.max(560, window.innerHeight - 340) });
    window.React.useEffect(() => {
      const onR = () => setSize({ w: window.innerWidth, h: Math.max(560, window.innerHeight - 340) });
      window.addEventListener('resize', onR); return () => window.removeEventListener('resize', onR);
    }, []);
    return e(window.ReactRedux.Provider, { store },
      e(KeplerComp, { id: 'map', mapboxApiAccessToken: token, width: size.w, height: size.h, appName: 'Waste Intelligence', version: 'Kepler 3.0' }));
  }
  const rootEl = $('#kepler-root');
  if (window.ReactDOM.createRoot) window.ReactDOM.createRoot(rootEl).render(e(App));
  else window.ReactDOM.render(e(App), rootEl);
}

function mapInstance() {
  try { return store.getState().keplerGl.map; } catch (e) { return null; }
}

async function loadDataIntoKepler(attempt) {
  const inst = mapInstance();
  if (!inst) {
    if (attempt < 40) return setTimeout(() => loadDataIntoKepler(attempt + 1), 150);
    return setStatus('Kepler mounted, but its map instance did not appear — press “Reload data” to retry.');
  }
  setStatus('Loading fleet, route and live tonnage into Kepler…');
  const tonnage = await loadTonnage();
  lastTonnage = tonnage;
  const built = buildDatasets(tonnage);
  lastRoute = built.route;
  try {
    store.dispatch(KG.addDataToMap({ datasets: built.datasets, config: buildConfig() }));
  } catch (err) {
    return setStatus('Kepler data failed to load: ' + esc(err.message) + ' — the main app is unaffected.');
  }
  setTimeout(() => {
    const inst2 = mapInstance();
    const n = inst2 && inst2.visState && inst2.visState.datasets ? Object.keys(inst2.visState.datasets).length : 0;
    const layers = inst2 && inst2.visState ? (inst2.visState.layers || []).length : 0;
    if (!n) { setStatus('Kepler accepted the data call but reports 0 datasets — try “Reload data”; if it persists, Kepler’s dispatch shape differs from this build and the config export below will show the store state for diagnosis.'); return; }
    hideStatus();
    renderKpis(tonnage);
  }, 600);
}

function renderKpis(tonnage) {
  const urgent = fleet.filter(b => b.fill >= 80);
  const avg = fleet.reduce((s, b) => s + b.fill, 0) / fleet.length;
  const tonTotal = tonnage.rows.reduce((s, r) => s + r.refuse + r.paper + r.mgp + r.organics, 0);
  $('#keplerKpis').innerHTML =
    `<div><b>${fleet.length}</b><span>Demo bins in fleet</span></div>` +
    `<div><b>${urgent.length}</b><span>Bins at ≥ 80% fill</span></div>` +
    `<div><b>${fmt(avg)}%</b><span>Average fill (demo fleet)</span></div>` +
    `<div><b>${fmt(tonTotal)} t</b><span>${tonnage.live ? 'Live' : 'Sample'} tonnage · ${esc(tonnage.month)}</span></div>` +
    `<div><b>${lastRoute ? lastRoute.order.length : 0} stops · ${lastRoute ? lastRoute.dist.toFixed(1) : '—'} km</b><span>Urgent collection route</span></div>`;
  const badge = $('#liveBadge');
  badge.textContent = tonnage.live ? ('LIVE · ' + tonnage.month) : 'SAMPLE FALLBACK · live feed unreachable';
  badge.className = 'pill' + (tonnage.live ? '' : ' warn');
}

/* ---------- presets, export, token ---------- */
function setLayerVisibility(label, want) {
  const inst = mapInstance(); if (!inst || !KG.layerConfigChange) return false;
  const layer = (inst.visState.layers || []).find(l => l.config.label === label);
  if (!layer) return false;
  try { store.dispatch(KG.layerConfigChange(layer, Object.assign({}, layer.config, { isVisible: want }))); return true; }
  catch (e) { return false; }
}
function applyPreset(name, camera, visibleLabels) {
  const inst = mapInstance();
  if (!inst) { setStatus('Kepler is not ready yet — wait for the map to load, then try again.'); return; }
  let switched = 0;
  if (KG.updateMap) { try { store.dispatch(KG.updateMap(Object.assign({ bearing: 0 }, camera))); } catch (e) {} }
  const allLabels = ['Bins — fill & status', 'Fill density — 3D grid', 'Urgent collection route', 'Live tonnage by borough', 'Bin fill tracking — 48 h'];
  allLabels.forEach(l => { if (setLayerVisibility(l, visibleLabels.includes(l))) switched++; });
  if (name === 'Tracking · 48 h' && KG.setFilter) {
    const fi = (inst.visState.filters || []).findIndex(f => f.type === 'timeRange');
    if (fi >= 0) { try { store.dispatch(KG.setFilter(fi, 'value', [timeMin, timeMax])); } catch (e) {} }
  }
  setStatus('Preset applied: ' + esc(name) + (switched ? ' — layers switched in Kepler.' : ' — if a layer did not switch, toggle it in Kepler’s left panel.'));
  setTimeout(hideStatus, 4000);
}
$('#presetFleet')?.addEventListener('click', () => applyPreset('Fleet 3D', { latitude: 40.73, longitude: -73.94, zoom: 11, pitch: 60 }, ['Bins — fill & status', 'Fill density — 3D grid', 'Urgent collection route']));
$('#presetRoutes')?.addEventListener('click', () => applyPreset('Routes', { latitude: 40.73, longitude: -73.94, zoom: 11, pitch: 0 }, ['Bins — fill & status', 'Urgent collection route']));
$('#presetTonnage')?.addEventListener('click', () => applyPreset('Tonnage', { latitude: 40.73, longitude: -73.94, zoom: 10.2, pitch: 45 }, ['Live tonnage by borough', 'Bins — fill & status']));
$('#presetTracking')?.addEventListener('click', () => applyPreset('Tracking · 48 h', { latitude: 40.73, longitude: -73.94, zoom: 11, pitch: 45 }, ['Bin fill tracking — 48 h', 'Bins — fill & status']));
$('#reloadKepler')?.addEventListener('click', () => location.reload());
$('#saveToken')?.addEventListener('click', () => {
  try { localStorage.setItem('wip_mapbox_token', ($('#mapboxToken').value || '').trim()); } catch (e) {}
  location.reload();
});
$('#exportConfig')?.addEventListener('click', () => {
  const inst = mapInstance();
  if (!inst) { alert('Kepler is not ready yet.'); return; }
  let payload = null;
  try { if (KG.KeplerGlSchema && KG.KeplerGlSchema.save) payload = KG.KeplerGlSchema.save(inst); } catch (e) {}
  if (!payload) payload = { visState: inst.visState, mapState: inst.mapState, mapStyle: inst.mapStyle };
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
  const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'waste-intelligence-kepler-config.json'; a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 5000);
});

/* ---------- boot ---------- */
(function boot() {
  const missing = [];
  if (!window.React) missing.push('React');
  if (!window.ReactDOM) missing.push('ReactDOM');
  if (!window.Redux) missing.push('Redux');
  if (!window.ReactRedux) missing.push('React-Redux');
  if (!window.ReactIs) missing.push('react-is');
  if (!window.styled) missing.push('styled-components');
  if (missing.length) { setStatus('Kepler could not start — these CDN scripts did not load: ' + missing.join(', ') + '. Check your connection and reload; the main app is unaffected.'); return; }
  const err = resolveKeplerGlobals();
  if (err) { setStatus('Kepler could not start — ' + esc(err)); return; }
  try { createStore(); }
  catch (e) { setStatus('Kepler failed at store setup: ' + esc(e.message)); return; }
  try { mountKepler(); }
  catch (e) { setStatus('Kepler failed at mount: ' + esc(e.message)); return; }
  loadDataIntoKepler(0);
})();
