/* Waste Intelligence web app — zero-build, no keys, runs on GitHub Pages.
   Sources are labelled in every view. Demo fleet/history are generated in
   the browser (seeded, deterministic) because the hub API returns no bins.
   Forecasting ports services/forecasting/app.py: current-cycle cut on a
   drop > 30 points, least-squares slope, R-squared, z-score anomaly. */
'use strict';
const $ = s => document.querySelector(s);
const $$ = s => [...document.querySelectorAll(s)];
const fmt = n => (n==null||isNaN(n)?'—':Number(n).toLocaleString(undefined,{maximumFractionDigits:1}));
const esc = s => String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));

/* ---------- routing ---------- */
const VIEWS=['dashboard','live','bins','forecast','graph','contamination','connect'];
function route(){
  const v=(location.hash||'#dashboard').slice(1).split('?')[0];
  const view=VIEWS.includes(v)?v:'dashboard';
  VIEWS.forEach(x=>{const el=$('#view-'+x); if(el) el.classList.toggle('hidden',x!==view);});
  $$('#nav a').forEach(a=>a.classList.toggle('active',a.dataset.nav===view));
  if(view==='forecast') drawForecast();
  if(view==='graph' && kgData) drawGraph();
}
window.addEventListener('hashchange',route);

/* ---------- seeded demo fleet ---------- */
function rng(seed){let a=seed>>>0;return()=>{a|=0;a=a+0x6D2B79F5|0;let t=Math.imul(a^a>>>15,1|a);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296;};}
const BOROUGHS={Manhattan:[40.7831,-73.9712],Brooklyn:[40.6782,-73.9442],Queens:[40.7282,-73.7949],Bronx:[40.8448,-73.8648],'Staten Island':[40.5795,-74.1502]};
const SITES={Manhattan:['Union Square','Central Park West','Harlem Market','Chelsea Piers'],Brooklyn:['Prospect Park','Williamsburg','Brooklyn Heights','Bushwick'],Queens:['Astoria','Flushing','Long Island City'],Bronx:['Fordham','South Bronx Hub','Riverdale'], 'Staten Island':['St. George Ferry','New Dorp']};
const DEFAULT_BINS=[];
{let i=0;Object.entries(SITES).forEach(([b,sites])=>sites.forEach((site,j)=>{
  const r=rng(1000+i*77); const fill=Math.round(18+r()*72);
  DEFAULT_BINS.push({id:`BIN-${b.slice(0,2).toUpperCase()}-${100+i}`,site,borough:b,fill,
    lat:BOROUGHS[b][0]+(r()-0.5)*0.06, lon:BOROUGHS[b][1]+(r()-0.5)*0.08, _seed:1000+i*77});
  i++;}));}
let fleet;
try{fleet=JSON.parse(localStorage.getItem('wip_fleet')||'null')||structuredClone(DEFAULT_BINS);}catch(e){fleet=structuredClone(DEFAULT_BINS);}
function saveFleet(){try{localStorage.setItem('wip_fleet',JSON.stringify(fleet));}catch(e){}}
function statusOf(f){return f>=80?'urgent':f>=60?'watch':'ok';}
function historyFor(bin){
  const r=rng(bin._seed||999); const pts=[]; let fill=Math.max(8,bin.fill-38);
  for(let h=47;h>=0;h--){ fill=Math.min(98,Math.max(5,fill+0.7+r()*1.1));
    if(h===20 && r()>0.4) fill=Math.max(8,fill-55); // a collection mid-history
    pts.push({h:47-h,fill:Math.round(fill*10)/10}); }
  pts[pts.length-1].fill=bin.fill;
  try{const extra=JSON.parse(localStorage.getItem('wip_readings')||'{}')[bin.id]||[];
    extra.forEach((v,k)=>pts.push({h:48+k,fill:v}));}catch(e){}
  return pts;
}
/* forecasting, ported from services/forecasting/app.py */
function analyse(pts){
  let cycle=pts;
  for(let i=pts.length-1;i>0;i--){ if(pts[i-1].fill-pts[i].fill>30){cycle=pts.slice(i);break;} }
  const n=cycle.length, mx=cycle.reduce((s,p)=>s+p.h,0)/n, my=cycle.reduce((s,p)=>s+p.fill,0)/n;
  let sxx=0,sxy=0,syy=0; cycle.forEach(p=>{sxx+=(p.h-mx)**2;sxy+=(p.h-mx)*(p.fill-my);syy+=(p.fill-my)**2;});
  const slope=sxx?sxy/sxx:0, intercept=my-slope*mx, r2=(sxx*syy)?(sxy*sxy)/(sxx*syy):0;
  const mean=my, sd=Math.sqrt(syy/Math.max(1,n-1)||0);
  const last=cycle[cycle.length-1].fill, z=sd?Math.abs(last-mean)/sd:0;
  const toFull=slope>0.05?(100-last)/slope:Infinity;
  return {cycle,slope,intercept,r2,mean,sd,last,z,toFull};
}
function haversine(a,b){const R=6371,dLa=(b.lat-a.lat)*Math.PI/180,dLo=(b.lon-a.lon)*Math.PI/180;
  const h=Math.sin(dLa/2)**2+Math.cos(a.lat*Math.PI/180)*Math.cos(b.lat*Math.PI/180)*Math.sin(dLo/2)**2; return 2*R*Math.asin(Math.sqrt(h));}

/* ---------- dashboard ---------- */
const SAMPLE_TONNAGE=[{month:'2026 / 09',borough:'Manhattan',refuse:48210,paper:5120,mgp:2980,organics:1420},{month:'2026 / 09',borough:'Brooklyn',refuse:52140,paper:4980,mgp:3120,organics:1180},{month:'2026 / 09',borough:'Queens',refuse:49880,paper:4610,mgp:2890,organics:960},{month:'2026 / 09',borough:'Bronx',refuse:38920,paper:3210,mgp:1980,organics:740},{month:'2026 / 09',borough:'Staten Island',refuse:17450,paper:1680,mgp:1040,organics:410}];
async function loadDashboard(){
  const urgent=fleet.filter(b=>b.fill>=80);
  const avg=fleet.reduce((s,b)=>s+b.fill,0)/fleet.length;
  $('#kpis').innerHTML=`<div><b>${fleet.length}</b><span>Demo bins in fleet</span></div><div><b>${urgent.length}</b><span>Bins at ≥ 80% fill</span></div><div><b>${fmt(avg)}%</b><span>Average fill (demo fleet)</span></div><div><b>31 / 55</b><span>Knowledge-graph nodes / edges</span></div>`;
  $('#urgentCount').textContent=urgent.length+' urgent';
  $('#urgentList').innerHTML=urgent.length?urgent.map(b=>`<li><a href="#forecast?bin=${b.id}">${esc(b.id)}</a> — ${esc(b.site)}, ${esc(b.borough)} · <strong>${b.fill}%</strong></li>`).join(''):'<li>No bin is at 80% or above right now.</li>';
  // Live tonnage, aggregated by borough for the latest month in the feed
  let rows=null, live=true;
  try{const res=await fetch('https://data.cityofnewyork.us/resource/ebb7-mvp5.json?$limit=500&$order=month%20DESC');
    if(!res.ok) throw new Error('HTTP '+res.status); rows=await res.json(); if(!rows.length) throw new Error('empty');}
  catch(e){live=false;}
  let agg;
  if(live){
    const month=rows[0].month; const by={};
    rows.filter(r=>r.month===month).forEach(r=>{const b=by[r.borough]||={borough:r.borough,refuse:0,paper:0,mgp:0,organics:0};
      b.refuse+=+r.refusetonscollected||0;b.paper+=+r.papertonscollected||0;b.mgp+=+r.mgptonscollected||0;b.organics+=(+r.resorganicstons||0)+(+r.schoolorganictons||0);});
    agg=Object.values(by).sort((a,b)=>b.refuse-a.refuse); agg.month=month;
  } else {agg=SAMPLE_TONNAGE; agg.month=SAMPLE_TONNAGE[0].month;}
  $('#liveBadge').textContent=live?('Live · '+agg.month):'Sample fallback · live feed unreachable';
  $('#liveBadge').className='pill'+(live?'':' warn');
  $('#dashTonnage tbody').innerHTML=agg.map(r=>`<tr><td>${esc(agg.month)}</td><td>${esc(r.borough)}</td><td>${fmt(r.refuse)}</td><td>${fmt(r.paper)}</td><td>${fmt(r.mgp)}</td><td>${fmt(r.organics)}</td></tr>`).join('');
}

/* ---------- live data ---------- */
const SAMPLES={
 'ebb7-mvp5':SAMPLE_TONNAGE,
 'gaq9-z3hz':[{district:'BKN01',fiscal_year:'2019',diversion_rate:'14.7%',capture_rate_paper:'44.9%',capture_rate_mgp:'43.0%'}],
 '6yag-pnij':[{fiscal_year:'2012',tons_dsny:23,tons_non_dsny:209,total:232}],
 '6r9j-qrwz':[{facility:'Sample facility',year:'2024',tons_delivered:'—'}]
};
async function loadLive(){
  const id=$('#liveDataset').value, limit=+$('#liveLimit').value, q=($('#liveFilter').value||'').toLowerCase();
  let rows=null, live=true;
  try{const res=await fetch(`https://data.cityofnewyork.us/resource/${id}.json?$limit=${limit}`);
    if(!res.ok) throw new Error('HTTP '+res.status); rows=await res.json();}
  catch(e){live=false; rows=SAMPLES[id]||[];}
  if(q) rows=rows.filter(r=>JSON.stringify(r).toLowerCase().includes(q));
  const cols=rows.length?Object.keys(rows[0]).filter(k=>!k.startsWith('_')).slice(0,8):[];
  $('#liveTable thead').innerHTML='<tr>'+cols.map(c=>`<th>${esc(c)}</th>`).join('')+'</tr>';
  $('#liveTable tbody').innerHTML=rows.length?rows.map(r=>'<tr>'+cols.map(c=>`<td>${esc(r[c])}</td>`).join('')+'</tr>').join(''):'<tr><td>No rows match.</td></tr>';
  $('#liveSourceBadge').textContent=live?'LIVE · NYC Open Data':'SAMPLE FALLBACK · live feed unreachable';
  $('#liveSourceBadge').className='pill'+(live?'':' warn');
  $('#liveNote').textContent=live?`${rows.length} rows from data.cityofnewyork.us/resource/${id}.json (no key required).`:'Live Socrata call failed, so the table shows a small labelled sample. Check your connection and press Load live data again.';
}
$('#liveLoad')?.addEventListener('click',loadLive);

/* ---------- bins & routes ---------- */
let selectedBins=new Set();
function renderBins(){
  const boro=$('#binBorough').value, st=$('#binStatus').value, q=($('#binSearch').value||'').toLowerCase();
  const rows=fleet.filter(b=>(!boro||b.borough===boro)&&(!st||statusOf(b.fill)===st)&&(!q||(b.id+b.site).toLowerCase().includes(q)));
  $('#binCount').textContent=rows.length+' shown';
  $('#binTable tbody').innerHTML=rows.map(b=>{const s=statusOf(b.fill);
    return `<tr><td><input type="checkbox" data-sel="${b.id}" ${selectedBins.has(b.id)?'checked':''}> <a href="#forecast?bin=${b.id}">${esc(b.id)}</a></td><td>${esc(b.site)} · ${esc(b.borough)}</td><td><div class="bar"><i class="${s==='urgent'?'high':s==='watch'?'mid':''}" style="width:${b.fill}%"></i></div> ${b.fill}%</td><td><button class="btn" data-collect="${b.id}">Collect</button></td></tr>`;}).join('');
  $$('#binTable [data-sel]').forEach(cb=>cb.addEventListener('change',()=>{cb.checked?selectedBins.add(cb.dataset.sel):selectedBins.delete(cb.dataset.sel);$('#customRouteBtn').classList.toggle('hidden',selectedBins.size<2);}));
  $$('#binTable [data-collect]').forEach(btn=>btn.addEventListener('click',()=>{const b=fleet.find(x=>x.id===btn.dataset.collect); if(b){b.fill=8; saveFleet(); renderBins(); loadDashboard();}}));
}
function buildRoute(bins){
  if(bins.length<2){$('#routeSummary').textContent='Pick at least two bins (tick them, or use urgent bins).';return;}
  const remaining=[...bins], order=[remaining.shift()];
  while(remaining.length){let best=0,bd=1e9; remaining.forEach((c,i)=>{const d=haversine(order[order.length-1],c); if(d<bd){bd=d;best=i;}}); order.push(remaining.splice(best,1)[0]);}
  let dist=0; for(let i=1;i<order.length;i++) dist+=haversine(order[i-1],order[i]);
  $('#routeSummary').textContent=`${order.length} stops · ${dist.toFixed(1)} km driving-line distance (straight-line segments) · about ${Math.round(dist/22*60+order.length*6)} min at city pace + 6 min per stop.`;
  $('#routeList').innerHTML=order.map((b,i)=>`<li><strong>${esc(b.id)}</strong> — ${esc(b.site)}, ${esc(b.borough)} · ${b.fill}% full</li>`).join('');
  $('#copyRouteBtn').classList.remove('hidden');
  $('#copyRouteBtn').onclick=()=>navigator.clipboard?.writeText(order.map((b,i)=>`${i+1}. ${b.id} — ${b.site}, ${b.borough} (${b.fill}%)`).join('\n')).then(()=>{$('#copyRouteBtn').textContent='Copied ✓'; setTimeout(()=>$('#copyRouteBtn').textContent='Copy route as text',1500);});
}
$('#routeBtn')?.addEventListener('click',()=>buildRoute(fleet.filter(b=>b.fill>=80)));
$('#customRouteBtn')?.addEventListener('click',()=>buildRoute(fleet.filter(b=>selectedBins.has(b.id))));
['binBorough','binStatus'].forEach(id=>$('#'+id)?.addEventListener('change',renderBins));
$('#binSearch')?.addEventListener('input',renderBins);
$('#resetFleet')?.addEventListener('click',()=>{fleet=structuredClone(DEFAULT_BINS); selectedBins.clear(); saveFleet(); localStorage.removeItem('wip_readings'); renderBins(); loadDashboard();});
$('#addBinForm')?.addEventListener('submit',e=>{e.preventDefault();
  const b={id:$('#newBinId').value.trim(),site:$('#newBinSite').value.trim(),borough:$('#newBinBorough').value,fill:+$('#newBinFill').value||0,lat:BOROUGHS[$('#newBinBorough').value][0],lon:BOROUGHS[$('#newBinBorough').value][1],_seed:Math.floor(Math.random()*9000)+500};
  fleet.unshift(b); saveFleet(); renderBins(); loadDashboard(); e.target.reset(); $('#newBinFill').value=40;});

/* ---------- forecast ---------- */
function currentBin(){const m=(location.hash.match(/bin=([^&]+)/)||[])[1]; return fleet.find(b=>b.id===decodeURIComponent(m||''))||fleet[0];}
function drawForecast(){
  const bin=currentBin(); if(!bin) return;
  const sel=$('#fcBin'); if(sel && !sel.options.length){fleet.forEach(b=>{const o=document.createElement('option');o.value=b.id;o.textContent=`${b.id} — ${b.site}`;sel.appendChild(o);}); sel.addEventListener('change',()=>{location.hash='#forecast?bin='+sel.value;});}
  if(sel) sel.value=bin.id;
  const pts=historyFor(bin), a=analyse(pts), H=+$('#fcHorizon').value;
  const fc=Math.min(100,Math.max(0,a.intercept+a.slope*(pts[pts.length-1].h+H)));
  $('#fcKpis').innerHTML=`<div><b>${bin.fill}%</b><span>Current fill · ${esc(bin.id)}</span></div><div><b>${a.slope>=0?'+':''}${a.slope.toFixed(2)} / h</b><span>Trend (current cycle, ${a.cycle.length} readings)</span></div><div><b>${fmt(fc)}%</b><span>Forecast in ${H} h</span></div><div><b>${isFinite(a.toFull)?Math.round(a.toFull)+' h':'—'}</b><span>Time to 100% at current trend</span></div><div><b>R² ${a.r2.toFixed(2)}</b><span>Fit quality</span></div><div><b>${a.z>2?'⚠ Anomaly':'Normal'}</b><span>z-score ${a.z.toFixed(2)} (flag &gt; 2)</span></div>`;
  $('#fcNote').textContent=pts.length<8?'Warning (backend-style 422): history is too thin for a reliable forecast — add readings below.':`Current cycle starts after the last collection drop. Mean ${a.mean.toFixed(1)}%, SD ${a.sd.toFixed(1)}%. Forecast is a straight-line extrapolation, not a guarantee.`;
  const cv=$('#fcChart'), ctx=cv.getContext('2d'); ctx.clearRect(0,0,cv.width,cv.height);
  const all=[...pts.map(p=>p.fill),fc]; const min=Math.min(...all)-5, max=Math.max(...all)+5;
  const X=h=>40+h/(pts[pts.length-1].h+H)*(cv.width-80), Y=v=>cv.height-30-(v-min)/(max-min)*(cv.height-70);
  ctx.strokeStyle='#dbe3dc'; ctx.beginPath(); ctx.moveTo(40,20); ctx.lineTo(40,cv.height-30); ctx.lineTo(cv.width-20,cv.height-30); ctx.stroke();
  ctx.fillStyle='#5a6a5f'; ctx.font='12px system-ui'; ctx.fillText('100%',4,Y(100)); ctx.fillText('0%',10,Y(0));
  ctx.strokeStyle='#1d7a4f'; ctx.lineWidth=2; ctx.beginPath(); pts.forEach((p,i)=>{i?ctx.lineTo(X(p.h),Y(p.fill)):ctx.moveTo(X(p.h),Y(p.fill));}); ctx.stroke();
  ctx.strokeStyle='#b7791f'; ctx.setLineDash([6,4]); ctx.beginPath(); ctx.moveTo(X(pts[pts.length-1].h),Y(pts[pts.length-1].fill)); ctx.lineTo(X(pts[pts.length-1].h+H),Y(fc)); ctx.stroke(); ctx.setLineDash([]);
  ctx.fillStyle='#b7791f'; ctx.beginPath(); ctx.arc(X(pts[pts.length-1].h+H),Y(fc),5,0,7); ctx.fill();
  ctx.fillStyle='#16211a'; ctx.fillText(`Forecast ${fmt(fc)}%`,X(pts[pts.length-1].h+H)-70,Y(fc)-10);
}
$('#fcHorizon')?.addEventListener('change',drawForecast);
$('#fcAdd')?.addEventListener('click',()=>{const v=+$('#fcReading').value; if(isNaN(v)||v<0||v>100){alert('Enter a reading between 0 and 100.');return;}
  const bin=currentBin(); const map=JSON.parse(localStorage.getItem('wip_readings')||'{}'); (map[bin.id]||(map[bin.id]=[])).push(v); localStorage.setItem('wip_readings',JSON.stringify(map)); bin.fill=v; saveFleet(); drawForecast(); loadDashboard();});

/* ---------- knowledge graph ---------- */
let kgData=null;
async function loadKG(){try{const r=await fetch('kg.json'); kgData=await r.json();}catch(e){kgData={nodes:[],edges:[]};}
  const sel=$('#kgAsk'); kgData.nodes.filter(n=>n.type==='Waste_Type'||n.type==='Waste_Stream').forEach(n=>{const o=document.createElement('option');o.value=n.id;o.textContent=n.name;sel.appendChild(o);});
  drawGraph();}
const COLORS={Waste_Type:'#1d7a4f',Waste_Stream:'#2a9d8f',Process:'#7c5cbf',Resource:'#b7791f',Facility:'#2563eb',Actor:'#64748b',Constraint:'#b42318'};
let kgSelected=null;
function drawGraph(){
  if(!kgData) return;
  const q=($('#kgSearch').value||'').toLowerCase(), type=$('#kgType').value;
  const nodes=kgData.nodes.filter(n=>(!q||(n.name+n.id).toLowerCase().includes(q))&&(!type||n.type===type));
  const ids=new Set(nodes.map(n=>n.id));
  const edges=kgData.edges.filter(e=>ids.has(e.from)&&ids.has(e.to));
  const svg=$('#kgSvg'); const pos={}; nodes.forEach((n,i)=>{const a=i/nodes.length*Math.PI*2; pos[n.id]=[450+330*Math.cos(a),260+200*Math.sin(a)];});
  const neigh=new Set([kgSelected]); if(kgSelected){edges.forEach(e=>{if(e.from===kgSelected)neigh.add(e.to); if(e.to===kgSelected)neigh.add(e.from);});}
  svg.innerHTML=edges.map(e=>{const [x1,y1]=pos[e.from],[x2,y2]=pos[e.to]; const dim=kgSelected&&!(neigh.has(e.from)&&neigh.has(e.to));
    return `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${dim?'#e2e8e2':'#94a894'}" stroke-width="1.2"/>`;}).join('')
    +nodes.map(n=>{const [x,y]=pos[n.id]; const dim=kgSelected&&!neigh.has(n.id);
      return `<g class="node" data-node="${n.id}" opacity="${dim?0.35:1}"><circle cx="${x}" cy="${y}" r="${n.id===kgSelected?13:9}" fill="${COLORS[n.type]||'#333'}"/><text x="${x}" y="${y+24}" text-anchor="middle">${esc(n.name.length>22?n.name.slice(0,21)+'…':n.name)}</text></g>`;}).join('');
  $$('#kgSvg .node').forEach(g=>g.addEventListener('click',()=>showNode(g.dataset.node)));
}
function showNode(id){
  kgSelected=id; const n=kgData.nodes.find(x=>x.id===id); if(!n) return;
  const out=kgData.edges.filter(e=>e.from===id), inn=kgData.edges.filter(e=>e.to===id);
  const name=i=>esc((kgData.nodes.find(x=>x.id===i)||{name:i}).name);
  $('#kgDetail').innerHTML=`<h2>${esc(n.name)}</h2><p><span class="pill">${esc(n.type)}</span></p><p>${esc(n.desc)}</p>`
    +(Object.keys(n.detail||{}).length?`<p class="small">${Object.entries(n.detail).map(([k,v])=>`<strong>${esc(k)}:</strong> ${esc(v)}`).join(' · ')}</p>`:'')
    +`<h3>Goes to (${out.length})</h3><ul class="list">${out.map(e=>`<li>${esc(e.type.replaceAll('_',' '))} → <a href="#" data-jump="${e.to}">${name(e.to)}</a></li>`).join('')||'<li>—</li>'}</ul>`
    +`<h3>Comes from (${inn.length})</h3><ul class="list">${inn.map(e=>`<li><a href="#" data-jump="${e.from}">${name(e.from)}</a> → ${esc(e.type.replaceAll('_',' '))}</li>`).join('')||'<li>—</li>'}</ul>`;
  $$('#kgDetail [data-jump]').forEach(a=>a.addEventListener('click',e=>{e.preventDefault();showNode(a.dataset.jump);drawGraph();}));
  drawGraph();
}
$('#kgSearch')?.addEventListener('input',drawGraph); $('#kgType')?.addEventListener('change',drawGraph);
$('#kgAskBtn')?.addEventListener('click',()=>{const id=$('#kgAsk').value; const paths=[];
  kgData.edges.filter(e=>e.from===id&&e.type==='WASTECANBEPROCESSEDBY').forEach(e=>{
    const res=kgData.edges.filter(x=>x.from===e.to&&x.type==='PROCESSPRODUCESRESOURCE').map(x=>kgData.nodes.find(n=>n.id===x.to)?.name||x.to);
    paths.push(`${kgData.nodes.find(n=>n.id===e.to)?.name||e.to} → ${res.join(', ')||'no resource edge in sample'}`);});
  showNode(id); const d=$('#kgDetail'); d.innerHTML+=`<h3>What it can become</h3><ul class="list">${paths.map(p=>`<li>${esc(p)}</li>`).join('')||'<li>No processing edge in this sample.</li>'}</ul>`;});

/* ---------- contamination ---------- */
const STREAMS={recycling:new Set(['Plastic','Metal','Glass','Paper']),organics:new Set([]),landfill:new Set(['Other'])};
const MATERIALS=['Plastic','Metal','Glass','Paper','Other'];
$('#materialChecks').innerHTML=MATERIALS.map(m=>`<label><input type="checkbox" value="${m}"> ${m}</label>`).join('');
$('#photoInput')?.addEventListener('change',e=>{const f=e.target.files[0]; if(!f) return; const r=new FileReader(); r.onload=()=>{$('#photoPreview').innerHTML=`<img src="${r.result}" alt="Uploaded waste photo preview">`;}; r.readAsDataURL(f);});
$('#checkBtn')?.addEventListener('click',()=>{
  const stream=document.querySelector('input[name="stream"]:checked').value;
  const seen=$$('#materialChecks input:checked').map(c=>c.value);
  const accepted=STREAMS[stream], bad=seen.filter(m=>!accepted.has(m)), good=seen.filter(m=>accepted.has(m));
  const contaminated=bad.length>0;
  $('#contamResult').innerHTML=`<h2>Verdict: ${contaminated?'<span style="color:#b42318">CONTAMINATED ⚠</span>':'<span style="color:#1d7a4f">CLEAN ✓</span>'}</h2>
  <p>Stream: <strong>${esc(stream)}</strong> · Materials tagged: ${seen.length?seen.map(esc).join(', '):'none'}</p>
  ${good.length?`<p>Accepted here: ${good.map(esc).join(', ')}</p>`:''}
  ${bad.length?`<p><strong>Contaminants (${bad.length}):</strong> ${bad.map(esc).join(', ')} — not accepted for ${esc(stream)} under the backend map.</p>`:''}
  ${!seen.length?'<p class="muted">No materials ticked, so no verdict on contents — tick what you can see in the photo.</p>':''}
  <p class="muted small">Manual-tagging demo. Production verdicts come from YOLOv11 <code>/predict</code> detections, not from these ticks; the acceptance map is identical.</p>`;
});

/* ---------- connect ---------- */
$('#connectForm')?.addEventListener('submit',async e=>{e.preventDefault(); const box=$('#connectResult'); box.innerHTML='<p>Probing…</p>';
  const jobs=[['Hub API',$('#hubUrl').value],['Forecasting',$('#fcUrl').value],['Contamination',$('#fcContamUrl').value]].filter(([,u])=>u.trim());
  const out=await Promise.all(jobs.map(async([name,url])=>{try{const r=await fetch(url.replace(/\/$/,'')+'/health',{signal:AbortSignal.timeout(6000)}); const t=await r.text(); return `<li><strong>${name}</strong>: HTTP ${r.status} — ${esc(t.slice(0,160))}</li>`;}
    catch(err){return `<li><strong>${name}</strong>: unreachable / blocked — ${esc(err.message)} (see mixed-content note below)</li>`;}}));
  box.innerHTML='<ul class="list">'+out.join('')+'</ul>';});

/* ---------- boot ---------- */
renderBins(); loadDashboard(); loadLive(); loadKG(); route();
