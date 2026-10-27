/* Platform backend wiring (Round 5).
   What the platform repo actually contains (read 2026-10-25 from
   EcoCode-Smart-City-Infrastructure/waste-intelligence-platform,
   default branch init/repository-scaffold):
   - Platform API (src/waste_intelligence_api, compose waste-intel-api
     :8001, Dockerfile.api): GET /health, GET /mcp/waste/bins,
     GET /mcp/waste/bin?bin_id=, POST /mcp/waste/kg {query, limit}.
     CORS default "*" (Config.CORS_ORIGINS) — browser-callable once it
     has a public HTTPS URL. DB-backed: empty DB means empty lists.
   - Hub Flask API (hub_layer, port 5000 in code, composed as
     hub-flask): GET /health, GET /bins, /facilities,
     /analytics/summary — DB-backed via the repositories on platform
     branch fix/browser-cors-kg-service-hub-db (503 when the DB is
     unreachable). Older code returns hardcoded empty/zero stubs;
     wiring to them must show "0 registered (stub)" and never
     replace the demo fleet with an empty list.
   - Forecasting (services/forecasting, :8002): GET /health,
     POST /forecast {bin_id, horizon_hours} and POST /anomaly
     {bin_id, features:{filllevelpct}}. Real math, DB telemetry.
     CORS middleware added on platform branch
     fix/browser-cors-kg-service-hub-db (defaults include the Pages
     origin); deployments from older code still need a reverse
     proxy that adds CORS headers (see the Connect guide).
   - Copilot (copilot_service, :8004): GET /health,
     POST /copilot/query {user_id, question} -> {answer, model,
     used_tools, audit_id}. Optional X-API-Key when REQUIRE_API_KEY.
     CORS origins are env-driven (CORS_ORIGINS) with the Pages
     origin in the defaults, on platform branch
     fix/browser-cors-kg-service-hub-db; older code defaults to
     localhost/grafana only.
   - Contamination (services/contamination, :8005): GET /health,
     POST /predict (multipart image + stream) -> detections,
     contaminants, model. CORS middleware added on platform branch
     fix/browser-cors-kg-service-hub-db (same as forecasting).
   - Compose now defines a real kg-service:8003 (platform branch
     fix/browser-cors-kg-service-hub-db): GET /health, POST /kg
     {query, limit}, POST /kg/pathways — the same W2RKG engine the
     Platform API serves in-memory at /mcp/waste/kg.
   - Pages is HTTPS: browsers block plain-HTTP backend calls
     (mixed content). A deployed backend MUST be HTTPS, ideally
     behind one reverse proxy that also fixes CORS.
   This file therefore does three honest things: (1) stores backend
   URLs + optional keys in THIS browser only (localStorage, never
   committed, never sent anywhere except the configured backend);
   (2) probes /health per service and reports what each service
   actually returns today, including stubs; (3) calls the real
   endpoints from the views that have them, and on ANY failure shows
   the failure and keeps the labelled local/demo result — it never
   presents a failed backend call as data, and never silently falls
   back in a way that hides the failure. */
(function(){
'use strict';
function esc(s){return String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function $(id){return document.getElementById(id);}
function trim(u){return (u||'').trim().replace(/\/+$/,'');}
function wiBackendLoad(){
  try{return Object.assign({platform:'',hub:'',forecasting:'',copilot:'',contamination:'',platformKey:'',copilotKey:''}, JSON.parse(localStorage.getItem('wi_backend')||'{}'));}catch(e){return {platform:'',hub:'',forecasting:'',copilot:'',contamination:'',platformKey:'',copilotKey:''};}
}
function wiBackendSave(cfg){try{localStorage.setItem('wi_backend',JSON.stringify(cfg));}catch(e){}}
async function wiBackendCall(base, path, opts){
  opts=opts||{};
  const headers=Object.assign({}, opts.headers||{});
  if(opts.apiKey) headers['X-API-Key']=opts.apiKey;
  const ctrl=new AbortController(); const to=setTimeout(()=>ctrl.abort(), opts.timeout||10000);
  try{
    const r=await fetch(base+path,{...opts, headers:headers, signal:ctrl.signal});
    const text=await r.text();
    let json=null; try{json=JSON.parse(text);}catch(e){}
    return {ok:r.ok, status:r.status, json:json, text:text};
  }catch(e){
    return {ok:false, status:0, error:(e.name==='AbortError'?'timed out':e.message||'network error'), blocked:true};
  }finally{clearTimeout(to);}
}
function failHint(res){
  if(res.status) return `Backend answered HTTP ${res.status}${res.json&&res.json.detail?': '+esc(String(res.json.detail)).slice(0,200):''}.`;
  return 'Browser could not reach it (network error, CORS block, or mixed-content block — an HTTPS page cannot call a plain-HTTP backend). See the deployment guide in Connect: the backend needs HTTPS, and deployments from older code need a proxy that adds CORS headers for forecasting/contamination.';
}
const SERVICES=[
  {key:'platform', label:'Platform API (src, :8001)', health:'/health', note:'GET /mcp/waste/bins, /mcp/waste/bin, POST /mcp/waste/kg. CORS default *.'},
  {key:'hub', label:'Hub Flask API (:5000)', health:'/health', note:'GET /bins (with latest fill per bin), /facilities, /analytics/summary — DB-backed on the fix branch; hardcoded stubs on older code.'},
  {key:'kg', label:'Knowledge Graph service (:8003)', health:'/health', note:'POST /kg {query, limit} — same shape as Platform /mcp/waste/kg. New on the fix branch.'},
  {key:'forecasting', label:'Forecasting (:8002)', health:'/health', note:'POST /forecast + /anomaly, real math on DB telemetry. CORS middleware added on fix branch (defaults include Pages origin); older deployments need a proxy.'},
  {key:'copilot', label:'Copilot (:8004)', health:'/health', note:'POST /copilot/query. CORS origins env-driven, Pages origin in defaults on fix branch.'},
  {key:'contamination', label:'Contamination (:8005)', health:'/health', note:'POST /predict (YOLOv11 image). CORS middleware added on fix branch; older deployments need a proxy.'},
];
async function wiBackendProbe(){
  const cfg=wiBackendLoad(); const box=$('connectResult'); if(!box) return;
  const jobs=SERVICES.filter(s=>trim(cfg[s.key]));
  if(!jobs.length){box.innerHTML='<p class="muted">No backend URLs saved yet. Paste at least one above and click Save, then Probe.</p>'; return;}
  box.innerHTML='<p>Probing…</p>';
  const out=[];
  for(const s of jobs){
    const res=await wiBackendCall(trim(cfg[s.key]), s.health, {timeout:8000});
    out.push(`<li><strong>${esc(s.label)}</strong>: ${res.ok?`OK — HTTP ${res.status} — ${esc((res.text||'').slice(0,160))}`:`FAILED — ${failHint(res)}`} <span class="muted small">${esc(s.note)}</span></li>`);
  }
  box.innerHTML='<ul class="list">'+out.join('')+'</ul>';
}
function wiInitBackend(){
  if(window.__beInit) return; window.__beInit=true;
  const cfg=wiBackendLoad();
  const map={bePlatform:'platform',beHub:'hub',beForecasting:'forecasting',beCopilot:'copilot',beContamination:'contamination',beKg:'kg',bePlatformKey:'platformKey',beCopilotKey:'copilotKey'};
  Object.keys(map).forEach(id=>{const el=$(id); if(el) el.value=cfg[map[id]]||'';});
  $('beSave')?.addEventListener('click',()=>{
    const next={}; Object.keys(map).forEach(id=>{const el=$(id); next[map[id]]=el?(id.toLowerCase().includes('key')?el.value.trim():trim(el.value)):'';});
    wiBackendSave(next);
    const st=$('beSaveStatus'); if(st) st.textContent='Backend URLs saved in this browser only. Nothing was sent to any server by saving.';
    wiBackendProbe();
  });
  $('beProbe')?.addEventListener('click',wiBackendProbe);
  $('connectForm')?.addEventListener('submit',e=>{e.preventDefault(); $('beSave')?.click();});
  // Forecasting view: ask the real service, shown BESIDE local math.
  $('fcBackendBtn')?.addEventListener('click',async()=>{
    const out=$('fcBackendResult'); const cfg2=wiBackendLoad();
    const base=trim(cfg2.forecasting);
    if(!base){if(out) out.innerHTML='<p class="muted">No forecasting URL saved. Set it in <a href="#connect">Connect</a>, then try again. Local forecast above is unchanged.</p>'; return;}
    const bin=(window.currentBin?window.currentBin():null)||null;
    const binId=bin?bin.id:((document.getElementById('fcBin')||{}).value||'');
    const horizon=+(document.getElementById('fcHorizon')?.value||24);
    if(out) out.innerHTML='<p>Asking the forecasting service…</p>';
    const res=await wiBackendCall(base,'/forecast',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({bin_id:binId,horizon_hours:horizon})});
    if(!res.ok){if(out) out.innerHTML=`<p><strong>Backend forecast failed.</strong> ${failHint(res)} Local forecast above is unchanged and stays labelled local.</p>`; return;}
    const j=res.json||{};
    let anom='';
    const ares=await wiBackendCall(base,'/anomaly',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({bin_id:binId,features:{filllevelpct:bin?bin.fill:null}})});
    if(ares.ok&&ares.json) anom=`<p>Backend anomaly: <strong>${ares.json.is_anomaly?'ANOMALY':'normal'}</strong> · score ${esc(ares.json.anomaly_score)} · z-scores ${esc(JSON.stringify(ares.json.z_scores||ares.json.scores||{}))}</p>`;
    else if(ares.json) anom=`<p class="muted small">Backend anomaly not returned (${esc(String(ares.json.detail||('HTTP '+ares.status)))}).</p>`;
    if(out) out.innerHTML=`<p><span class="pill">BACKEND · ${esc(j.model_version||'waste-forecast-v1.0')}</span> ${esc(binId)}: predicted <strong>${esc(j.predicted_value)}%</strong> in ${esc(j.horizon_hours)} h · confidence ${esc(j.confidence)} · trend ${esc(j.trend_fill_per_hour)} /h · R² ${esc(j.r_squared)} · readings used ${esc(j.readings_used)} · hours to full ${esc(j.hours_until_full==null?'—':j.hours_until_full)}.</p>${anom}<p class="muted small">This is the platform service's answer from DB telemetry. If it disagrees with the local card, the local card is the ported math on demo history — the backend wins only when its telemetry is real.</p>`;
  });
  // Bins view: registered bins from the Platform API (+ hub stub count).
  $('beBinsFetch')?.addEventListener('click',async()=>{
    const out=$('beBinsResult'); const cfg2=wiBackendLoad(); const base=trim(cfg2.platform);
    if(!base){if(out) out.innerHTML='<p class="muted">No Platform API URL saved. Set it in <a href="#connect">Connect</a>. The demo fleet below is unchanged.</p>'; return;}
    if(out) out.innerHTML='<p>Fetching registered bins…</p>';
    const res=await wiBackendCall(base,'/mcp/waste/bins?limit=100',{apiKey:trim(cfg2.platformKey)||undefined});
    if(!res.ok && !(res.status===404)){if(out) out.innerHTML=`<p><strong>Platform bins fetch failed.</strong> ${failHint(res)} Demo fleet below is unchanged.</p>`; return;}
    if(!res.ok && res.status===404){if(out) out.innerHTML=`<p><strong>Platform API returned 0 registered bins.</strong> The API answers 404 when its database has no bin telemetry yet — that is an empty database, not a broken endpoint. Demo fleet below is unchanged and stays labelled demo.</p>`; return;}
    const list=Array.isArray(res.json)?res.json:(res.json&&Array.isArray(res.json.bins)?res.json.bins:[]);
    let hubNote='';
    const hub=trim(cfg2.hub);
    if(hub){const h=await wiBackendCall(hub,'/bins'); hubNote=h.ok?`<p class="muted small">Hub Flask /bins answered: ${esc(JSON.stringify(h.json)).slice(0,200)} — on the platform fix branch this is DB-backed (with latest fill per bin); on older code it is a hardcoded empty stub, so 0 there is a stub, not a sensor count.</p>`:`<p class="muted small">Hub Flask /bins could not be read (${failHint(h)})</p>`;}
    if(out) out.innerHTML=list.length
      ?`<p><strong>Platform API registered bins: ${list.length}</strong> (first 20 shown). These are DB-backed telemetry bins — they are NOT the demo fleet below, which stays separate until you choose to replace it.</p><ul class="list">${list.slice(0,20).map(b=>`<li>${esc(b.bin_id||b.id||'?')} — ${esc(b.timestamp||'')} — ${esc(JSON.stringify(b.sensors||b.location||{}).slice(0,160))}</li>`).join('')}</ul>${hubNote}`
      :`<p><strong>Platform API returned 0 registered bins.</strong> That means the database has no bin telemetry yet (or the API key/DB is not wired) — it does NOT mean the city has no bins. Demo fleet below is unchanged and stays labelled demo.</p>${hubNote}`;
  });
  // Contamination view: real YOLO via the service, when configured.
  $('beContamBtn')?.addEventListener('click',async()=>{
    const out=$('beContamResult'); const cfg2=wiBackendLoad(); const base=trim(cfg2.contamination);
    const file=document.getElementById('photoInput')?.files?.[0];
    if(!base){if(out) out.textContent='No contamination URL saved. Set it in Connect, then try again. Manual tagging below is unchanged.'; return;}
    if(!file){if(out) out.textContent='Choose a photo first (step 1 above), then click Backend YOLO check.'; return;}
    if(out) out.textContent='Uploading the photo to the contamination service… (the photo goes only to the URL you configured).';
    const stream=(document.querySelector('input[name="stream"]:checked')||{}).value||'recycling';
    const fd=new FormData(); fd.append('image',file); fd.append('stream',stream);
    try{
      const r=await fetch(base+'/predict',{method:'POST',body:fd,signal:AbortSignal.timeout(60000)});
      const j=await r.json().catch(()=>null);
      if(!r.ok||!j){if(out) out.innerHTML=`<p><strong>Backend check failed (HTTP ${r.status}).</strong> Manual verdict below is unchanged.</p>`; return;}
      const dets=(j.detections||[]).map(d=>`${esc(d.material)} (${esc(d.confidence)})`).join(', ')||'none';
      const cons=(j.contaminants||[]).map(d=>`${esc(d.material)} (${esc(d.confidence)})`).join(', ')||'none';
      if(out) out.innerHTML=`<p><span class="pill">BACKEND YOLO · ${esc(j.model||'')}</span> Stream <strong>${esc(j.stream)}</strong> · Verdict: <strong>${j.is_contaminated?'CONTAMINATED':'CLEAN'}</strong> · contaminant count ${esc(j.contaminant_count)}.</p><p>Detections: ${dets}</p><p>Contaminants: ${cons}</p><p class="muted small">This is the service's model output on your photo. The manual ticks below are a separate demo and were not used for this verdict.</p>`;
    }catch(e){
      if(out) out.innerHTML=`<p><strong>Backend check could not reach the service.</strong> ${esc(e.message||'network error')} — most likely CORS (deployments from older code ship no CORS middleware for this service) or mixed content. Deploy from the platform fix branch, or put it behind a reverse proxy that adds CORS headers for the Pages origin, or run this page locally. Manual verdict below is unchanged.</p>`;
    }
  });
  // Graph view: ask the Platform API's in-memory KG.
  $('beKgBtn')?.addEventListener('click',async()=>{
    const out=$('beKgResult'); const cfg2=wiBackendLoad(); const base=trim(cfg2.platform)||trim(cfg2.kg); const viaKgService=!trim(cfg2.platform)&&!!trim(cfg2.kg);
    const q=($('beKgQuery')?.value||'').trim();
    if(!base){if(out) out.innerHTML='<p class="muted">No Platform API or KG service URL saved. Set one in <a href="#connect">Connect</a>. The local sample graph above is unchanged.</p>'; return;}
    if(!q){if(out) out.textContent='Type a KG query first (e.g. a node name or waste type).'; return;}
    if(out) out.textContent='Asking the Platform KG…';
    const res=await wiBackendCall(base,viaKgService?'/kg':'/mcp/waste/kg',{method:'POST',headers:{'Content-Type':'application/json'},apiKey:trim(cfg2.platformKey)||undefined,body:JSON.stringify({query:q,limit:10})});
    if(!res.ok){if(out) out.innerHTML=`<p><strong>Platform KG failed.</strong> ${failHint(res)} Local sample graph above is unchanged.</p>`; return;}
    const j=res.json||{};
    const rows=Array.isArray(j.results)?j.results:[];
    if(out) out.innerHTML=rows.length
      ?`<p><strong>Platform KG answered in ${esc(j.execution_time)}s:</strong></p><ul class="list">${rows.slice(0,10).map(r=>`<li>${esc(JSON.stringify(r).slice(0,300))}</li>`).join('')}</ul><p class="muted small">This is the platform's in-memory KG engine, not the local kg.json file — compare the two before treating either as the only truth.</p>`
      :`<p>${viaKgService?'KG service':'Platform KG'} returned no results for "${esc(q)}". Local sample graph above is unchanged.</p>`;
  });
}
window.wiBackendLoad=wiBackendLoad;
window.wiBackendSave=wiBackendSave;
window.wiBackendProbe=wiBackendProbe;
window.wiInitBackend=wiInitBackend;
// Copilot backend call, used by the Assistant when "Platform copilot" is chosen.
window.wiBackendCopilotAsk=async function(question){
  const cfg=wiBackendLoad(); const base=trim(cfg.copilot);
  if(!base) throw new Error('No copilot URL saved. Set it in Connect, then choose Platform copilot again.');
  const res=await wiBackendCall(base,'/copilot/query',{method:'POST',headers:{'Content-Type':'application/json'},apiKey:trim(cfg.copilotKey)||undefined,body:JSON.stringify({user_id:'web-app-user',question:question})});
  if(!res.ok){
    if(res.status===401) throw new Error('Copilot answered 401 — it requires an API key. Save one in Connect (Copilot API key) and try again.');
    throw new Error(failHint(res).replace(/<[^>]+>/g,''));
  }
  const j=res.json||{};
  return {answer:j.answer||'(empty answer from copilot)', model:j.model||'', tools:j.used_tools||[], auditId:j.audit_id||''};
};
document.addEventListener('DOMContentLoaded',()=>{try{wiInitBackend();}catch(e){}});
if(document.readyState!=='loading'){try{wiInitBackend();}catch(e){}}
})();
