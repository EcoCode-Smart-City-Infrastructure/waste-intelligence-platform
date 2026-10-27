
(function(){const jb=document.getElementById('jsBuild'); if(jb) jb.textContent='HTML + app.js overhaul14 parsed';
window.addEventListener('error',e=>{const j=document.getElementById('jsBuild'); if(j) j.textContent+=' · ERROR: '+(e.message||'script error');});})();
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
const VIEWS=['dashboard','live','bins','forecast','graph','contamination','connect','assistant','twin','network'];
function route(){
  const v=(location.hash||'#dashboard').slice(1).split('?')[0];
  const view=VIEWS.includes(v)?v:'dashboard';
  VIEWS.forEach(x=>{const el=$('#view-'+x); if(el) el.classList.toggle('hidden',x!==view);});
  const activeEl=$('#view-'+view); if(activeEl){activeEl.classList.remove('view-in'); void activeEl.offsetWidth; activeEl.classList.add('view-in');}
  $$('#nav a').forEach(a=>a.classList.toggle('active',a.dataset.nav===view));
  if(view==='forecast') drawForecast();
  if(view==='graph' && kgData) drawGraph();
  if(view==='assistant') wiInitAssistant();
  if(view==='twin' && typeof wiInitTwin==='function') wiInitTwin();
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
// Twin view reads the fleet through this getter: a top-level `let` in a
// classic script does NOT become window.fleet, which left the twin empty.
window.wipFleet=function(){return fleet;};
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
  $('#urgentCount').textContent=urgent.length+' urgent';
  $('#urgentList').innerHTML=urgent.length?urgent.map(b=>`<li><a href="#forecast?bin=${b.id}">${esc(b.id)}</a> — ${esc(b.site)}, ${esc(b.borough)} · <strong>${b.fill}%</strong></li>`).join(''):'<li>No bin is at 80% or above right now.</li>';
  // Live tonnage, aggregated by borough for the latest month in the feed
  let rows=null, live=true;
  try{const res=await fetch('https://data.cityofnewyork.us/resource/ebb7-mvp5.json?$select=month,borough,refusetonscollected,papertonscollected,mgptonscollected,resorganicstons,schoolorganictons&$limit=500&$order=month%20DESC');
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
  try{dashRender(agg, live);}catch(e){console.warn('Dashboard grid failed, table still available:',e);}
  try{renderOverview(agg, live);}catch(e){console.warn('City overview failed, rest of dashboard still available:',e);}
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
  const fcR=$('#fcReasoning');
  if(fcR){
    const cyc=a.cycle, first=cyc[0], last=cyc[cyc.length-1];
    const fitWord=a.r2>=0.8?'strong':a.r2>=0.5?'moderate':'weak';
    const changeWord=a.slope>0?'keep rising at this rate':a.slope<0?'fall — a collection may be near':'stay flat';
    fcR.innerHTML=`<p><strong>Evidence:</strong> ${cyc.length} readings in the current cycle, from ${first?first.fill+'%':'—'} (hour ${first?first.h:'—'}) to ${last?last.fill+'%':'—'} (hour ${last?last.h:'—'}). The cycle restarts after any collection drop over 30 points, so older history does not drag this trend.</p>
    <p><strong>Reasoning:</strong> a least-squares line through those readings gives slope ${a.slope>=0?'+':''}${a.slope.toFixed(2)} points/hour and R² ${a.r2.toFixed(2)} — a ${fitWord} fit. At that slope the bin should ${changeWord}; time to 100% is ${isFinite(a.toFull)?Math.round(a.toFull)+' hours':'not reached in this trend'}. Anomaly check: latest reading z-score ${a.z.toFixed(2)} against its own cycle (mean ${a.mean.toFixed(1)}%, SD ${a.sd.toFixed(1)}%) — ${a.z>2?'flagged, because it is more than 2 SD from the cycle mean':'normal, within 2 SD'}.</p>
    <p><strong>What would change this:</strong> a new reading, a collection (drop &gt; 30 points restarts the cycle), or a slope change. <strong>Caveat:</strong> this is demo fleet history, not live sensor readings, and a straight-line extrapolation is a guide, not a guarantee.</p>`;
  }
  const cv=$('#fcChart'), ctx=cv.getContext('2d'); ctx.clearRect(0,0,cv.width,cv.height);
  const all=[...pts.map(p=>p.fill),fc]; const min=Math.min(...all)-5, max=Math.max(...all)+5;
  const X=h=>40+h/(pts[pts.length-1].h+H)*(cv.width-80), Y=v=>cv.height-30-(v-min)/(max-min)*(cv.height-70);
  ctx.strokeStyle='#dbe3dc'; ctx.beginPath(); ctx.moveTo(40,20); ctx.lineTo(40,cv.height-30); ctx.lineTo(cv.width-20,cv.height-30); ctx.stroke();
  ctx.fillStyle='#5a6a5f'; ctx.font='12px system-ui'; ctx.fillText('100%',4,Y(100)); ctx.fillText('0%',10,Y(0));
  const grad=ctx.createLinearGradient(0,20,0,cv.height-30); grad.addColorStop(0,'rgba(29,122,79,.25)'); grad.addColorStop(1,'rgba(29,122,79,0)'); ctx.fillStyle=grad; ctx.beginPath(); pts.forEach((p,i)=>{i?ctx.lineTo(X(p.h),Y(p.fill)):ctx.moveTo(X(p.h),Y(p.fill));}); ctx.lineTo(X(pts[pts.length-1].h),Y(0)); ctx.lineTo(X(pts[0].h),Y(0)); ctx.closePath(); ctx.fill();
  ctx.strokeStyle='#1d7a4f'; ctx.lineWidth=2; ctx.beginPath(); pts.forEach((p,i)=>{i?ctx.lineTo(X(p.h),Y(p.fill)):ctx.moveTo(X(p.h),Y(p.fill));}); ctx.stroke();
  ctx.strokeStyle='#b7791f'; ctx.setLineDash([6,4]); ctx.beginPath(); ctx.moveTo(X(pts[pts.length-1].h),Y(pts[pts.length-1].fill)); ctx.lineTo(X(pts[pts.length-1].h+H),Y(fc)); ctx.stroke(); ctx.setLineDash([]);
  ctx.fillStyle='#b7791f'; ctx.beginPath(); ctx.arc(X(pts[pts.length-1].h+H),Y(fc),5,0,7); ctx.fill();
  ctx.fillStyle='#16211a'; ctx.fillText(`Forecast ${fmt(fc)}%`,X(pts[pts.length-1].h+H)-70,Y(fc)-10);
}
$('#fcHorizon')?.addEventListener('change',drawForecast);
$('#fcAdd')?.addEventListener('click',()=>{const v=+$('#fcReading').value; if(isNaN(v)||v<0||v>100){alert('Enter a reading between 0 and 100.');return;}
  const bin=currentBin(); const map=JSON.parse(localStorage.getItem('wip_readings')||'{}'); (map[bin.id]||(map[bin.id]=[])).push(v); localStorage.setItem('wip_readings',JSON.stringify(map)); bin.fill=v; saveFleet(); drawForecast(); loadDashboard();});

/* ---------- knowledge graph: circular, organic, animated ---------- */
let kgData=null, kgSelected=null, kgTracePath=[];
const COLORS={Waste_Type:'#1d7a4f',Waste_Stream:'#2a9d8f',Process:'#7c5cbf',Resource:'#b7791f',Facility:'#2563eb',Actor:'#64748b',Constraint:'#b42318'};
const TYPE_ORDER=['Waste_Type','Waste_Stream','Process','Resource','Facility','Actor','Constraint'];
const RING=[{label:'All',filter:''},{label:'Waste',filter:'Waste'},{label:'Process',filter:'Process'},{label:'Resource',filter:'Resource'},{label:'Facility',filter:'Facility'},{label:'Actor',filter:'Actor'},{label:'Constraint',filter:'Constraint'}];
const kgNode=id=>kgData.nodes.find(n=>n.id===id);
const kgName=id=>(kgNode(id)||{name:id}).name;
const typeMatches=(n,f)=>!f||(f==='Waste'?(n.type==='Waste_Type'||n.type==='Waste_Stream'):n.type===f);
function fmtVal(v){if(Array.isArray(v))return v.join(', '); if(v&&typeof v==='object')return Object.entries(v).map(([k,x])=>`${k} ${x}`).join(', '); return String(v);}
function fmtProps(p){return Object.entries(p||{}).map(([k,v])=>`${k.replaceAll('_',' ')}: ${fmtVal(v)}`).join(' · ');}
async function loadKG(){try{const r=await fetch('kg.json'); kgData=await r.json();}catch(e){kgData={nodes:[],edges:[]};}
  const wastes=kgData.nodes.filter(n=>n.type==='Waste_Type'||n.type==='Waste_Stream');
  [['#kgAsk'],['#flowWaste']].forEach(([sel])=>{const el=$(sel); wastes.forEach(n=>{const o=document.createElement('option');o.value=n.id;o.textContent=n.name;el.appendChild(o);});});
  buildRing(); populateFlowProcesses(); populateFlowResources(); renderFlow(); try{buildLoopGallery(); populateStudio(); loadCuratedLoops();}catch(e){console.warn('Loop gallery failed, graph still available:',e);} drawGraph();}
function buildRing(){
  const ring=$('#kgRing'); if(!ring) return;
  ring.innerHTML=`<div class="kg-ring-hub" id="kgRingHub"></div>`+RING.map((s,i)=>{const a=(-90+i*360/RING.length)*Math.PI/180, x=50+42*Math.cos(a), y=50+42*Math.sin(a);
    return `<button class="kg-ring-seg" data-filter="${s.filter}" style="left:${x}%;top:${y}%" aria-label="Filter to ${s.label}">${s.label}</button>`;}).join('');
  $$('#kgRing .kg-ring-seg').forEach(b=>b.addEventListener('click',()=>{$('#kgType').value=b.dataset.filter; syncRing(); drawGraph();}));
  syncRing();
}
function syncRing(){
  const f=$('#kgType').value;
  $$('#kgRing .kg-ring-seg').forEach(b=>b.classList.toggle('active',b.dataset.filter===f));
  const seg=RING.find(s=>s.filter===f)||RING[0];
  const count=kgData?kgData.nodes.filter(n=>typeMatches(n,f)).length:0;
  const hub=$('#kgRingHub'); if(hub) hub.innerHTML=`<strong>${seg.label}</strong><span>${count} node${count===1?'':'s'}</span><span class="small">of ${kgData?kgData.nodes.length:0}</span>`;
}
function drawGraph(){
  if(!kgData) return;
  const q=($('#kgSearch').value||'').toLowerCase(), type=$('#kgType').value;
  const nodes=[...kgData.nodes].sort((a,b)=>TYPE_ORDER.indexOf(a.type)-TYPE_ORDER.indexOf(b.type)||(a.name||'').localeCompare(b.name||''))
    .filter(n=>(!q||(n.name+n.id).toLowerCase().includes(q))&&typeMatches(n,type));
  const ids=new Set(nodes.map(n=>n.id));
  const edges=kgData.edges.filter(e=>ids.has(e.from)&&ids.has(e.to));
  const svg=$('#kgSvg'); const pos={}; nodes.forEach((n,i)=>{const a=i/Math.max(1,nodes.length)*Math.PI*2-Math.PI/2; pos[n.id]=[450+340*Math.cos(a),260+195*Math.sin(a)];});
  const neigh=new Set([kgSelected]); if(kgSelected){edges.forEach(e=>{if(e.from===kgSelected)neigh.add(e.to); if(e.to===kgSelected)neigh.add(e.from);});}
  const inTrace=(a,b)=>kgTracePath.length>1&&kgTracePath.some((x,i)=>i<kgTracePath.length-1&&kgTracePath[i]===a&&kgTracePath[i+1]===b);
  const defs=Object.entries(COLORS).map(([t,c])=>`<linearGradient id="grad-${t}" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="${c}"/><stop offset="100%" stop-color="${c}" stop-opacity=".65"/></linearGradient>`).join('');
  const edgeHtml=edges.map(e=>{const [x1,y1]=pos[e.from],[x2,y2]=pos[e.to], mx=(x1+x2)/2, my=(y1+y2)/2;
    const cx=mx+(mx-450)*0.22, cy=my+(my-260)*0.22, dim=kgSelected&&!(neigh.has(e.from)&&neigh.has(e.to)), traced=inTrace(e.from,e.to);
    return `<path d="M ${x1} ${y1} Q ${cx} ${cy} ${x2} ${y2}" fill="none" class="${traced?'flow-edge':''}" stroke="${traced?'#1d7a4f':dim?'#e6ebe6':'#9db3a0'}" stroke-width="${traced?3:1.2}"/>`;}).join('');
  const nodeHtml=nodes.map(n=>{const [x,y]=pos[n.id]; const dim=kgSelected&&!neigh.has(n.id);
    return `<g class="node" data-node="${n.id}" opacity="${dim?0.35:1}"><circle cx="${x}" cy="${y}" r="${n.id===kgSelected?14:10}" fill="url(#grad-${n.type})" stroke="#fff" stroke-width="2"/><text x="${x}" y="${y+26}" text-anchor="middle">${esc(n.name.length>22?n.name.slice(0,21)+'…':n.name)}</text></g>`;}).join('');
  svg.innerHTML=`<defs>${defs}</defs>`+edgeHtml+nodeHtml;
  $$('#kgSvg .node').forEach(g=>g.addEventListener('click',()=>showNode(g.dataset.node)));
  syncRing();
}
function conversionBlock(n){
  const d=n.detail||{}, rows=[];
  const add=(label,key,unit='')=>{if(d[key]!=null) rows.push(`<tr><td>${label}</td><td><strong>${fmtVal(d[key])}${unit}</strong></td></tr>`);};
  if(n.type==='Process'){add('Efficiency','efficiency','%');add('Processing time','processing_time_hours',' h');add('Energy required','energy_requirement_kwh_per_tonne',' kWh/t');add('Carbon footprint','carbon_footprint_kg_co2_per_tonne',' kg CO₂/t');add('Biogas yield','biogas_yield_m3_per_tonne',' m³/t');add('Larvae yield','larvae_yield_kg_per_tonne_waste',' kg/t');add('Optimal temperature','optimal_temperature_c',' °C');}
  if(n.type==='Resource'){add('Economic value','economic_value_per_tonne',' $/t');add('Market demand','market_demand');add('Quality grade','quality_grade');add('Energy content','energy_content_mj_per_kg',' MJ/kg');add('Methane content','methane_content_percent','%');}
  if(n.type==='Facility'){add('Capacity','capacity_tonnes_per_year',' t/yr');add('Location','location');add('Status','operational_status');}
  if(n.type==='Waste_Stream'){add('Volume','volume_tonnes_per_year',' t/yr');add('Collection','collection_frequency');add('Diversion rate','diversion_rate');add('Participation','participation_rate');}
  if(n.type==='Waste_Type'){add('Organic content','organic_content','%');add('Moisture content','moisture_content','%');add('C:N ratio','c_n_ratio');}
  return rows.length?`<h3>Conversion metrics</h3><table><tbody>${rows.join('')}</tbody></table><p class="muted small">Values are the sample's own properties for this node — nothing here is estimated.</p>`:'';
}
function showNode(id){
  kgSelected=id; const n=kgNode(id); if(!n) return;
  const out=kgData.edges.filter(e=>e.from===id), inn=kgData.edges.filter(e=>e.to===id);
  $('#kgDetail').innerHTML=`<h2>${esc(n.name)}</h2><p><span class="pill">${esc(n.type)}</span></p><p>${esc(n.desc)}</p>${conversionBlock(n)}`
    +(Object.keys(n.detail||{}).length?`<h3>All recorded properties</h3><p class="small">${Object.entries(n.detail).map(([k,v])=>`<strong>${esc(k.replaceAll('_',' '))}:</strong> ${esc(fmtVal(v))}`).join(' · ')}</p>`:'')
    +`<h3>Goes to (${out.length})</h3><ul class="list">${out.map(e=>`<li>${esc(e.type.replaceAll('_',' '))} → <a href="#" data-jump="${e.to}">${esc(kgName(e.to))}</a>${e.props&&Object.keys(e.props).length?` <span class="muted small">(${esc(fmtProps(e.props))})</span>`:''}</li>`).join('')||'<li>—</li>'}</ul>`
    +`<h3>Comes from (${inn.length})</h3><ul class="list">${inn.map(e=>`<li><a href="#" data-jump="${e.from}">${esc(kgName(e.from))}</a> → ${esc(e.type.replaceAll('_',' '))}${e.props&&Object.keys(e.props).length?` <span class="muted small">(${esc(fmtProps(e.props))})</span>`:''}</li>`).join('')||'<li>—</li>'}</ul>`;
  $$('#kgDetail [data-jump]').forEach(a=>a.addEventListener('click',e=>{e.preventDefault();showNode(a.dataset.jump);drawGraph();}));
  drawGraph();
}
$('#kgSearch')?.addEventListener('input',drawGraph);
$('#kgType')?.addEventListener('change',()=>{syncRing();drawGraph();});
$('#kgAskBtn')?.addEventListener('click',()=>{
  const id=$('#kgAsk').value; const paths=[];
  const wasteTypes=kgNode(id)?.type==='Waste_Stream'?kgData.edges.filter(e=>e.from===id&&e.type==='WASTESTREAMHASWASTETYPE').map(e=>e.to):[id];
  wasteTypes.forEach(wt=>kgData.edges.filter(e=>e.from===wt&&e.type==='WASTECANBEPROCESSEDBY').forEach(e=>{
    const res=kgData.edges.filter(x=>x.from===e.to&&x.type==='PROCESSPRODUCESRESOURCE').map(x=>{
      const rn=kgNode(x.to), pn=kgNode(e.to);
      return `${rn?.name||x.to} (yield ${fmtProps(x.props)}; process ${pn?.detail?.efficiency??'—'}% efficient)`;
    });
    paths.push(`${kgName(e.to)} — suitability ${e.props?.suitability||'—'}, diversion ${e.props?.typical_diversion_rate!=null?Math.round(e.props.typical_diversion_rate*100)+'%':'—'} → ${res.join(', ')||'no resource edge in sample'}`);}));
  showNode(id); const d=$('#kgDetail'); d.innerHTML+=`<h3>What it can become</h3><ul class="list">${paths.map(p=>`<li>${esc(p)}</li>`).join('')||'<li>No processing edge in this sample.</li>'}</ul>`;
  // carry the first real pathway into the animated flow
  const first=kgData.edges.find(e=>wasteTypes.includes(e.from)&&e.type==='WASTECANBEPROCESSEDBY');
  if(first){$('#flowWaste').value=id; populateFlowProcesses(first.to); const fres=kgData.edges.find(x=>x.from===first.to&&x.type==='PROCESSPRODUCESRESOURCE'); if(fres){populateFlowResources(fres.to);} renderFlow();}
});
/* ---------- animated circular flow ---------- */
let flowPlaying=false;
function processesFor(wasteId){
  const n=kgNode(wasteId); if(!n) return [];
  if(n.type==='Waste_Stream'){const types=kgData.edges.filter(e=>e.from===wasteId&&e.type==='WASTESTREAMHASWASTETYPE').map(e=>e.to);
    return [...new Set(kgData.edges.filter(e=>types.includes(e.from)&&e.type==='WASTECANBEPROCESSEDBY').map(e=>e.to))];}
  return kgData.edges.filter(e=>e.from===wasteId&&e.type==='WASTECANBEPROCESSEDBY').map(e=>e.to);
}
function fillSelect(el,ids,keep){el.innerHTML=''; ids.forEach(id=>{const o=document.createElement('option');o.value=id;o.textContent=kgName(id);el.appendChild(o);}); if(keep&&ids.includes(keep)) el.value=keep;}
function populateFlowProcesses(keep){fillSelect($('#flowProcess'),processesFor($('#flowWaste').value),keep); populateFlowResources();}
function populateFlowResources(keep){const p=$('#flowProcess').value; fillSelect($('#flowResource'),kgData.edges.filter(e=>e.from===p&&e.type==='PROCESSPRODUCESRESOURCE').map(e=>e.to),keep);}
$('#flowWaste')?.addEventListener('change',()=>{populateFlowProcesses();renderFlow();});
$('#flowProcess')?.addEventListener('change',()=>{populateFlowResources();renderFlow();});
$('#flowResource')?.addEventListener('change',renderFlow);
$('#flowTonnes')?.addEventListener('input',renderFlow);
$('#flowSpeed')?.addEventListener('change',renderFlow);
$('#flowPlayBtn')?.addEventListener('click',()=>{flowPlaying=!flowPlaying; $('#flowPlayBtn').textContent=flowPlaying?'⏸ Pause flow':'▶ Play flow'; renderFlow();});
$('#flowShowBtn')?.addEventListener('click',()=>{
  const w=$('#flowWaste').value,p=$('#flowProcess').value,r=$('#flowResource').value;
  kgTracePath=[w,p,r].filter(Boolean);
  const dem=kgData.edges.find(e=>e.from===r&&e.type==='RESOURCEDEMANDEDBY_ACTOR'); if(dem) kgTracePath.push(dem.to);
  $('#kgType').value=''; $('#kgSearch').value=''; syncRing(); drawGraph();
  document.querySelector('.kg-graph-card')?.scrollIntoView({behavior:'smooth',block:'center'});
});
function yieldOf(edgeProps){
  if(edgeProps.yield_tonnes_per_tonne_waste!=null) return {qty:edgeProps.yield_tonnes_per_tonne_waste,unit:'t'};
  if(edgeProps.yield_m3_per_tonne_waste!=null) return {qty:edgeProps.yield_m3_per_tonne_waste,unit:'m³'};
  if(edgeProps.yield_kg_per_tonne_waste!=null) return {qty:edgeProps.yield_kg_per_tonne_waste,unit:'kg'};
  if(edgeProps.yield_percent!=null) return {qty:edgeProps.yield_percent/100,unit:'t'};
  return null;
}
function renderFlow(){
  if(!kgData||!$('#flowWaste').value) return;
  const w=kgNode($('#flowWaste').value), p=kgNode($('#flowProcess').value), r=kgNode($('#flowResource').value);
  const T=Math.max(0.1,+$('#flowTonnes').value||1);
  const wp=kgData.edges.find(e=>e.from===w.id&&e.type==='WASTECANBEPROCESSEDBY'&&e.to===p.id)
    ||kgData.edges.find(e=>e.from===w.id&&e.type==='WASTESTREAMHASWASTETYPE'&&processesFor(w.id).includes(p.id)&&kgData.edges.some(x=>x.from===e.to&&x.to===p.id&&x.type==='WASTECANBEPROCESSEDBY'));
  const wpEdge=kgData.edges.find(e=>e.to===p.id&&e.type==='WASTECANBEPROCESSEDBY'&&e.from===w.id)||kgData.edges.find(e=>e.to===p.id&&e.type==='WASTECANBEPROCESSEDBY'&&w.type==='Waste_Stream'&&kgData.edges.some(x=>x.from===w.id&&x.to===e.from));
  const pr=kgData.edges.find(e=>e.from===p.id&&e.to===r.id&&e.type==='PROCESSPRODUCESRESOURCE');
  const dem=kgData.edges.find(e=>e.from===r.id&&e.type==='RESOURCEDEMANDEDBY_ACTOR');
  const actor=dem?kgNode(dem.to):null;
  const facEdge=actor?kgData.edges.find(e=>e.from===actor.id&&e.type==='ACTOROPERATESFACILITY'):null;
  const fac=facEdge?kgNode(facEdge.to):null;
  const back=fac?kgData.edges.find(e=>e.from===fac.id&&e.type==='FACILITYACCEPTSWASTE'&&(e.to===w.id||true)):null;
  const dur=$('#flowSpeed').value;
  const cx=260, cy=170, R=110;
  const arc=(a0,a1)=>{const p0=[cx+R*Math.cos(a0),cy+R*Math.sin(a0)], p1=[cx+R*Math.cos(a1),cy+R*Math.sin(a1)]; return `M ${p0[0]} ${p0[1]} A ${R} ${R} 0 0 1 ${p1[0]} ${p1[1]}`;};
  const labels=[['WASTE',w?.name||'',-93],['PROCESS',p?.name||'',1],['RESOURCE',r?.name||'',96],['DEMAND',actor?.name||'Demand',-175]];
  $('#flowSvg').innerHTML=`<defs><linearGradient id="flowGrad" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="#1d7a4f"/><stop offset="55%" stop-color="#2a9d8f"/><stop offset="100%" stop-color="#b7791f"/></linearGradient></defs>
  <circle cx="${cx}" cy="${cy}" r="${R}" fill="none" stroke="#e6ede7" stroke-width="22"/>
  <path d="${arc(-2.4,-0.85)}" fill="none" stroke="#1d7a4f" stroke-width="20" stroke-linecap="round"/>
  <path d="${arc(-0.75,0.8)}" fill="none" stroke="#7c5cbf" stroke-width="20" stroke-linecap="round"/>
  <path d="${arc(0.9,2.45)}" fill="none" stroke="#b7791f" stroke-width="20" stroke-linecap="round"/>
  <path d="${arc(2.55,3.9)}" fill="none" stroke="#2a9d8f" stroke-width="20" stroke-linecap="round"/>
  ${labels.map(([k,name,deg])=>{const a=deg*Math.PI/180, LR=R+42; return `<text x="${cx+LR*Math.cos(a)}" y="${cy+LR*Math.sin(a)-6}" text-anchor="middle" font-size="11" font-weight="700">${k}</text><text x="${cx+LR*Math.cos(a)}" y="${cy+LR*Math.sin(a)+10}" text-anchor="middle" font-size="10">${esc((name||'').length>20?name.slice(0,19)+'…':name||'')}</text>`;}).join('')}
  <text x="${cx}" y="${cy-4}" text-anchor="middle" font-size="15" font-weight="700">The loop</text><text x="${cx}" y="${cy+16}" text-anchor="middle" font-size="11" fill="#5a6a5f">${fmt(T)} t in</text>
  ${flowPlaying?`<circle r="8" fill="#0f5132" stroke="#fff" stroke-width="2"><animateMotion dur="${dur}s" repeatCount="indefinite" path="M ${cx},${cy-R} a ${R},${R} 0 1,1 -0.1,0"/></circle>`:''}`;
  const yld=pr?yieldOf(pr.props):null;
  const outQty=yld?yld.qty*T:null;
  let valueTxt='—';
  if(yld&&outQty!=null){
    if(yld.unit==='t'&&r.detail?.economic_value_per_tonne!=null) valueTxt=`$${fmt(outQty*r.detail.economic_value_per_tonne)} (at $${r.detail.economic_value_per_tonne}/t of resource)`;
    else if(yld.unit==='kg'&&r.detail?.economic_value_per_tonne!=null) valueTxt=`$${fmt(outQty/1000*r.detail.economic_value_per_tonne)} (from ${fmt(outQty)} kg at $${r.detail.economic_value_per_tonne}/t)`;
    else if(yld.unit==='m³'&&dem?.props?.willing_to_pay_per_m3!=null) valueTxt=`$${fmt(outQty*dem.props.willing_to_pay_per_m3)} (at $${dem.props.willing_to_pay_per_m3}/m³ demanded)`;
    else valueTxt='Not directly computable from the sample units — see note below.';
  }
  const div=wpEdge?.props?.typical_diversion_rate;
  const co2f=wpEdge?.props?.co2e_saved_mt_per_metric_tonne_warm_v15, ch4f=wpEdge?.props?.methane_avoided_kg_per_tonne;
  const divertedT=div!=null?T*div:T;
  const co2Txt=co2f!=null?fmt(divertedT*co2f)+' MTCO₂e':'—';
  const ch4Txt=ch4f!=null?fmt(divertedT*ch4f)+' kg CH₄':'—';
  $('#flowSteps').innerHTML=`
    <div class="flow-step"><strong>1 · Waste</strong><p>${esc(w?.name||'—')}</p><p class="muted small">${esc(w?.desc||'')}</p></div>
    <div class="flow-step"><strong>2 · Process</strong><p>${esc(p?.name||'—')}</p><p class="muted small">Suitability ${esc(wpEdge?.props?.suitability||'—')} · diversion ${div!=null?Math.round(div*100)+'%':'—'} · ${p?.detail?.efficiency??'—'}% efficient · ${p?.detail?.processing_time_hours??'—'} h · ${p?.detail?.energy_requirement_kwh_per_tonne??'—'} kWh/t · ${p?.detail?.carbon_footprint_kg_co2_per_tonne??'—'} kg CO₂/t</p></div>
    <div class="flow-step"><strong>3 · Resource</strong><p>${esc(r?.name||'—')}</p><p class="muted small">Yield ${yld?fmt(yld.qty)+' '+yld.unit+' per tonne of waste':'—'} · quality ${esc(pr?.props?.quality||r?.detail?.quality_grade||'—')} · market demand ${esc(r?.detail?.market_demand||'—')}</p></div>
    <div class="flow-step"><strong>4 · Demand → loop closes</strong><p>${actor?esc(actor.name):'No demand edge for this resource in the sample'}</p><p class="muted small">${dem?`Annual demand ${fmt(dem.props.annual_demand_tonnes||dem.props.annual_demand_m3)} ${dem.props.annual_demand_m3?'m³':'t'} · ${esc(dem.props.demand_frequency||'')}`:''}${fac?` · ${esc(actor.name)} operates ${esc(fac.name)}, which accepts waste${back?` (tipping fee $${back.props?.tipping_fee_per_tonne??'—'}/t, contamination limit ${back.props?.contamination_limit_percent??'—'}%)`:''} — so demand feeds the next collection, not an endpoint.`:''}</p></div>`;
  $('#flowMetrics').innerHTML=`<div class="kpis"><div><b>${fmt(T)} t</b><span>Input waste</span></div><div><b>${div!=null?fmt(T*div)+' t':'—'}</b><span>Diverted (at sample diversion rate)</span></div><div><b>${outQty!=null?fmt(outQty)+' '+(yld.unit):'—'}</b><span>Resource output</span></div><div><b>${valueTxt}</b><span>Indicative value, sample prices only</span></div><div><b>${co2Txt}</b><span>CO₂e avoided vs landfill (WARM v15, per diverted tonne)</span></div><div><b>${ch4Txt}</b><span>Methane avoided (separate from CO₂e — do not add)</span></div></div>
  <p class="muted small">Units are kept separate on purpose: biogas is priced per m³ demanded, compost and feed per tonne of resource. Where the sample gives no matching price, the value is left as “—” rather than guessed. Preprocessing for this step: ${esc((wpEdge?.props?.preprocessing_required||[]).join(', ')||'none listed')}. ${co2f!=null?`Emissions: EPA WARM v15, ${esc(wpEdge.props.emissions_source||'')}; the older WARM v13 compost saving is 0.95 MTCO₂e/t — a version difference, not a second measurement. Methane figures are CH₄ only and are already inside the WARM CO₂e factor, so never add them to it.`:'Emissions: no WARM factor on this sample edge — the “—” is honest, not zero.'}</p>`;
}


/* ---------- demonstration loops for every element + Ask / Studio ---------- */
const STAGES=['Waste','Process','Resource','Actor','Facility'];
const stageOfNode=n=>n.type==='Waste_Type'||n.type==='Waste_Stream'?'Waste':n.type;
const edgeBetween=(a,b)=>kgData.edges.find(e=>e.from===a&&e.to===b)||null;
const firstOut=(from,type)=>kgData.edges.find(e=>e.from===from&&e.type===type)||null;
function wasteToProcess(wasteId,prefer){
  const n=kgNode(wasteId); if(!n) return null;
  if(n.type==='Waste_Stream'){
    for(const c of kgData.edges.filter(e=>e.from===wasteId&&e.type==='WASTESTREAMHASWASTETYPE')){
      const p=kgData.edges.find(e=>e.from===c.to&&e.type==='WASTECANBEPROCESSEDBY');
      if(p) return {id:p.to,edge:p,via:c.to};
    }
    return null;
  }
  if(prefer){const p=kgData.edges.find(e=>e.from===wasteId&&e.to===prefer&&e.type==='WASTECANBEPROCESSEDBY'); if(p) return {id:prefer,edge:p};}
  const p=firstOut(wasteId,'WASTECANBEPROCESSEDBY'); return p?{id:p.to,edge:p}:null;
}
function processToResource(procId,prefer){
  if(prefer){const p=kgData.edges.find(e=>e.from===procId&&e.to===prefer&&e.type==='PROCESSPRODUCESRESOURCE'); if(p) return {id:prefer,edge:p};}
  const p=firstOut(procId,'PROCESSPRODUCESRESOURCE'); return p?{id:p.to,edge:p}:null;
}
function actorToFacility(actorId,ctx){
  const op=firstOut(actorId,'ACTOROPERATESFACILITY'); if(op) return {id:op.to,edge:op,real:true};
  // demand actor with no operate edge: go via the resource it demands -> process -> facility
  const dem=kgData.edges.find(e=>e.to===actorId&&e.type==='RESOURCEDEMANDEDBY_ACTOR');
  if(dem){const pr=processForResource(dem.from); if(pr){const f=kgData.edges.find(x=>x.to===pr&&x.type==='FACILITYSUPPORTSPROCESS'); if(f) return {id:f.from,edge:null,real:false,note:'System bridge: this actor does not operate a facility in the sample, so the loop uses the facility that runs the process making the resource it demands.'};}}
  if(ctx.processId){const f=kgData.edges.find(x=>x.to===ctx.processId&&x.type==='FACILITYSUPPORTSPROCESS'); if(f) return {id:f.from,edge:null,real:false,note:'System bridge: this actor does not operate a facility in the sample, so the loop uses the facility that runs this process.'};}
  if(ctx.resourceId){const pr=kgData.edges.find(e=>e.to===ctx.resourceId&&e.type==='PROCESSPRODUCESRESOURCE'); if(pr){const f=firstOut(pr.from,'FACILITYSUPPORTSPROCESS'); if(f) return {id:f.from,edge:null,real:false,note:'System bridge: this actor does not operate a facility in the sample, so the loop uses the facility that runs the process making this resource.'};}}
  if(ctx.wasteId){const f=kgData.edges.find(e=>e.to===ctx.wasteId&&e.type==='FACILITYACCEPTSWASTE'); if(f) return {id:f.from,edge:null,real:false,note:'System bridge: this actor does not operate a facility in the sample, so the loop uses a facility that accepts this waste.'};}
  const f=kgData.nodes.find(n=>n.type==='Facility'); return f?{id:f.id,edge:null,real:false,note:'System bridge: no facility link for this actor in the sample.'}:null;
}
function facilityToWaste(facId,prefer){
  if(prefer){const p=kgData.edges.find(e=>e.from===facId&&e.to===prefer&&e.type==='FACILITYACCEPTSWASTE'); if(p) return {id:prefer,edge:p};}
  const p=firstOut(facId,'FACILITYACCEPTSWASTE'); return p?{id:p.to,edge:p}:null;
}
function processForResource(resId){const e=kgData.edges.find(x=>x.to===resId&&x.type==='PROCESSPRODUCESRESOURCE'); return e?e.from:null;}
function processForFacility(facId){const e=kgData.edges.find(x=>x.from===facId&&x.type==='FACILITYSUPPORTSPROCESS'); return e?e.to:null;}
function buildElementLoop(elementId){
  const el=kgNode(elementId); if(!el) return null;
  if(el.type==='Constraint'){
    const tgt=firstOut(elementId,'CONSTRAINTAPPLIESTO'); if(!tgt) return null;
    const loop=buildElementLoop(tgt.to); if(loop){loop.gate=el; loop.elementId=elementId; loop.title=`${el.name} — gates ${kgName(tgt.to)}`;} return loop;
  }
  const startStage=stageOfNode(el), startIdx=STAGES.indexOf(startStage);
  const byStage={}; byStage[startStage]=elementId;
  // preferred targets that would close the loop nicely
  const preferProcess = startStage==='Resource'?processForResource(elementId):startStage==='Facility'?processForFacility(elementId):null;
  const preferResource = null;
  for(let k=1;k<5;k++){
    const curStage=STAGES[(startIdx+k-1)%5], nextStage=STAGES[(startIdx+k)%5], curId=byStage[curStage];
    let pick=null;
    if(curStage==='Waste'&&nextStage==='Process') pick=wasteToProcess(curId, preferProcess|| (startStage==='Process'?elementId:null));
    else if(curStage==='Process'&&nextStage==='Resource') pick=processToResource(curId, startStage==='Resource'?elementId:null);
    else if(curStage==='Resource'&&nextStage==='Actor') {const e=firstOut(curId,'RESOURCEDEMANDEDBY_ACTOR'); pick=e?{id:e.to,edge:e}:null;}
    else if(curStage==='Actor'&&nextStage==='Facility') pick=actorToFacility(curId,{processId:byStage.Process,resourceId:byStage.Resource,wasteId:byStage.Waste});
    else if(curStage==='Facility'&&nextStage==='Waste') pick=facilityToWaste(curId, startStage==='Waste'?elementId:null);
    if(pick) byStage[nextStage]=pick.id;
    else { // fall back to any node of the next stage so the loop still plays, marked as a bridge
      const cand=kgData.nodes.find(n=>stageOfNode(n)===nextStage); if(cand) byStage[nextStage]=cand.id;
    }
  }
  const order=[]; for(let k=0;k<5;k++) order.push(byStage[STAGES[(startIdx+k)%5]]);
  return stagesToLoop(order, `${el.name} loop`, 'sample', elementId, null);
}
function stagesToLoop(stageIds, title, source, elementId, gate){
  const stages=stageIds.map(id=>{const n=kgNode(id); return n||{id,name:id,type:'Proposed',desc:'Proposed — not in the sample',detail:{}};});
  const transitions=[];
  for(let i=0;i<stages.length;i++){
    const from=stages[i], to=stages[(i+1)%stages.length], isClosure=i===stages.length-1;
    const edge=edgeBetween(from.id,to.id);
    transitions.push({from:from.id,to:to.id,edge,real:!!edge,isClosure,
      note:edge?'':isClosure?'Loop closes — next load / new waste arises (system step, not a sample edge).':'System bridge — no direct sample edge between these stages; the step is labelled, not invented as data.'});
  }
  return {title,source,elementId,gate,stages,transitions};
}
let loopPlaying=false, currentLoop=null;
function loopDiagramSvg(loop,playing,dur){
  const n=loop.stages.length, cx=260, cy=170, R=110;
  const cols={Waste:'#1d7a4f',Process:'#7c5cbf',Resource:'#b7791f',Actor:'#64748b',Facility:'#2563eb',Proposed:'#94a3b8',Gate:'#b42318'};
  const arc=(a0,a1)=>{const p0=[cx+R*Math.cos(a0),cy+R*Math.sin(a0)], p1=[cx+R*Math.cos(a1),cy+R*Math.sin(a1)]; return `M ${p0[0]} ${p0[1]} A ${R} ${R} 0 0 1 ${p1[0]} ${p1[1]}`;};
  let arcs='', labels='';
  loop.stages.forEach((s,i)=>{
    const a0=-Math.PI/2+i*(2*Math.PI/n)+0.12, a1=-Math.PI/2+(i+1)*(2*Math.PI/n)-0.12, mid=(a0+a1)/2, col=cols[stageOfNode(s)]||'#333';
    const tr=loop.transitions[i];
    arcs+=`<path d="${arc(a0,a1)}" fill="none" stroke="${col}" stroke-width="20" stroke-linecap="round" stroke-dasharray="${tr.real?'':'6 6'}" opacity="${tr.real?1:0.85}"/>`;
    const LR=R+42;
    labels+=`<text x="${cx+LR*Math.cos(mid)}" y="${cy+LR*Math.sin(mid)-6}" text-anchor="middle" font-size="11" font-weight="700">${esc(stageOfNode(s).toUpperCase())}</text><text x="${cx+LR*Math.cos(mid)}" y="${cy+LR*Math.sin(mid)+10}" text-anchor="middle" font-size="10">${esc((s.name||'').length>20?s.name.slice(0,19)+'…':s.name||'')}</text>`;
  });
  return `<circle cx="${cx}" cy="${cy}" r="${R}" fill="none" stroke="#e6ede7" stroke-width="22"/>${arcs}${labels}
  <text x="${cx}" y="${cy-4}" text-anchor="middle" font-size="14" font-weight="700">${esc(loop.title.length>28?loop.title.slice(0,27)+'…':loop.title)}</text><text x="${cx}" y="${cy+16}" text-anchor="middle" font-size="11" fill="#5a6a5f">${loop.stages.length} stages · ${loop.transitions.filter(t=>t.real).length} real · ${loop.transitions.filter(t=>!t.real).length} bridge</text>
  ${playing?`<circle r="8" fill="#0f5132" stroke="#fff" stroke-width="2"><animateMotion dur="${dur}s" repeatCount="indefinite" path="M ${cx},${cy-R} a ${R},${R} 0 1,1 -0.1,0"/></circle>`:''}`;
}
function renderLoopPlayer(loop){
  currentLoop=loop; if(!loop) return;
  const dur=$('#loopSpeed')?.value||'7';
  $('#loopSvg').innerHTML=loopDiagramSvg(loop,loopPlaying,dur);
  $('#loopSteps').innerHTML=loop.stages.map((s,i)=>{
    const tr=loop.transitions[i];
    const metric = s.type==='Process'?`${s.detail?.efficiency??'—'}% efficient · ${s.detail?.processing_time_hours??'—'} h · ${s.detail?.energy_requirement_kwh_per_tonne??'—'} kWh/t · ${s.detail?.carbon_footprint_kg_co2_per_tonne??'—'} kg CO₂/t`
      : s.type==='Resource'?`Value $${s.detail?.economic_value_per_tonne??'—'}/t · demand ${esc(s.detail?.market_demand||'—')}`
      : s.type==='Facility'?`Capacity ${fmt(s.detail?.capacity_tonnes_per_year)} t/yr`
      : s.type==='Waste_Stream'?`${fmt(s.detail?.volume_tonnes_per_year)} t/yr`
      : esc(s.desc||'');
    return `<div class="flow-step"><strong>${i+1} · ${esc(stageOfNode(s))}</strong><p><a href="#" data-loopjump="${s.id}">${esc(s.name)}</a> ${s.type==='Proposed'?'<span class="pill warn">PROPOSED</span>':''}</p><p class="muted small">${metric}</p><p class="muted small">${tr.real?`→ ${esc(tr.edge.type.replaceAll('_',' '))} ${esc(fmtProps(tr.edge.props))}`:`→ <strong>Bridge:</strong> ${esc(tr.note)}`}</p></div>`;
  }).join('');
  $$('#loopSteps [data-loopjump]').forEach(a=>a.addEventListener('click',e=>{e.preventDefault(); if(kgNode(a.dataset.loopjump)) showNode(a.dataset.loopjump);}));
  // metrics: process + resource + demand + facility from this loop
  const proc=loop.stages.find(s=>s.type==='Process'), res=loop.stages.find(s=>s.type==='Resource'), fac=loop.stages.find(s=>s.type==='Facility');
  const prEdge=proc&&res?edgeBetween(proc.id,res.id):null, demEdge=res?kgData.edges.find(e=>e.from===res.id&&e.type==='RESOURCEDEMANDEDBY_ACTOR'):null;
  const yld=prEdge?yieldOf(prEdge.props):null;
  $('#loopMetrics').innerHTML=`<div class="kpis"><div><b>${proc?proc.detail?.efficiency??'—': '—'}%</b><span>Process efficiency</span></div><div><b>${yld?fmt(yld.qty)+' '+yld.unit:'—'}</b><span>Yield per tonne of waste</span></div><div><b>${demEdge?fmt(demEdge.props.annual_demand_tonnes||demEdge.props.annual_demand_m3):'—'}</b><span>Annual demand (sample units)</span></div><div><b>${fac?fmt(fac.detail?.capacity_tonnes_per_year):'—'}</b><span>Facility capacity t/yr</span></div></div>
  ${loop.gate?`<p><span class="pill bad">Gate: ${esc(loop.gate.name)}</span> — this constraint applies to a stage in this loop; it does not create a cycle on its own. ${esc(fmtProps(kgData.edges.find(e=>e.from===loop.gate.id)||{}.props||{}))}</p>`:''}
  <p class="muted small">Source: ${esc(loop.source)} · Real transitions use sample edges with their props; bridges are dashed in the diagram and labelled in the steps. No metric is invented for a proposed stage.</p>`;
}
function buildLoopGallery(){
  const g=$('#loopGallery'); if(!g||!kgData) return;
  g.innerHTML=TYPE_ORDER.map(t=>{
    const nodes=kgData.nodes.filter(n=>n.type===t);
    return `<div class="loop-group"><strong>${esc(t)}</strong><div>${nodes.map(n=>`<button class="btn loop-btn" data-loop="${n.id}">${esc(n.name)}</button>`).join('')}</div></div>`;
  }).join('');
  $$('#loopGallery .loop-btn').forEach(b=>b.addEventListener('click',()=>{const loop=buildElementLoop(b.dataset.loop); $('#loopElement').value=b.dataset.loop; renderLoopPlayer(loop);}));
  const sel=$('#loopElement'); if(sel&&!sel.options.length){kgData.nodes.forEach(n=>{const o=document.createElement('option');o.value=n.id;o.textContent=`${n.name} (${n.type})`;sel.appendChild(o);});}
  if(!currentLoop){const first=buildElementLoop('FoodScraps'); renderLoopPlayer(first);}
}
$('#loopElement')?.addEventListener('change',()=>renderLoopPlayer(buildElementLoop($('#loopElement').value)));
$('#loopSpeed')?.addEventListener('change',()=>{if(currentLoop) renderLoopPlayer(currentLoop);});
$('#loopPlayBtn')?.addEventListener('click',()=>{loopPlaying=!loopPlaying; $('#loopPlayBtn').textContent=loopPlaying?'⏸ Pause loop':'▶ Play loop'; if(currentLoop) renderLoopPlayer(currentLoop);});
$('#loopShowBtn')?.addEventListener('click',()=>{
  if(!currentLoop) return;
  kgTracePath=currentLoop.stages.map(s=>s.id); $('#kgType').value=''; $('#kgSearch').value=''; syncRing(); drawGraph();
  document.querySelector('.kg-graph-card')?.scrollIntoView({behavior:'smooth',block:'center'});
});
/* ---------- custom loops: curated file + browser storage ---------- */
let curatedLoops=[];
async function loadCuratedLoops(){try{const r=await fetch('loops.json'); if(!r.ok) return; const arr=await r.json(); curatedLoops=Array.isArray(arr)?arr:[];}catch(e){curatedLoops=[];} renderYourLoops();}
function customLoopsLocal(){try{return JSON.parse(localStorage.getItem('wip_custom_loops')||'[]');}catch(e){return [];}}
function saveCustomLoops(arr){try{localStorage.setItem('wip_custom_loops',JSON.stringify(arr));}catch(e){}}
function renderYourLoops(){
  const box=$('#yourLoops'); if(!box) return;
  const all=[
    ...curatedLoops.map(l=>({...l,source:'curated (loops.json)'})),
    ...customLoopsLocal().map(l=>({...l,source:'saved in this browser'}))
  ];
  if(!all.length){box.innerHTML='<p class="muted small">No saved loops yet. Save one in Loop Studio above, or ask Muse in chat to add one to <code>loops.json</code> — it will appear here on the next visit.</p>'; return;}
  box.innerHTML='<h3>Your loops</h3>'+all.map((l,i)=>`<div class="flow-step"><strong>${esc(l.name)}</strong> <span class="pill">${esc(l.source)}</span><p class="muted small">${(l.stages||[]).map(s=>esc(kgName(s))).join(' → ')}</p><p class="muted small">${esc(l.desc||'')}</p><button class="btn" data-playloop="${i}">Play this loop</button>${l.source.includes('browser')?` <button class="btn" data-delloop="${l.name}">Delete</button>`:''}</div>`).join('');
  $$('#yourLoops [data-playloop]').forEach(b=>b.addEventListener('click',()=>{const l=all[+b.dataset.playloop]; renderLoopPlayer(stagesToLoop(l.stages,l.name,l.source,null,null)); $('#loopElement').value='';}));
  $$('#yourLoops [data-delloop]').forEach(b=>b.addEventListener('click',()=>{saveCustomLoops(customLoopsLocal().filter(x=>x.name!==b.dataset.delloop)); renderYourLoops();}));
}
function populateStudio(){
  const fill=(id,types)=>{const el=$(id); if(!el||el.options.length) return; const o0=document.createElement('option');o0.value='';o0.textContent='— Proposed / leave blank —';el.appendChild(o0); kgData.nodes.filter(n=>types.includes(n.type)).forEach(n=>{const o=document.createElement('option');o.value=n.id;o.textContent=n.name;el.appendChild(o);});};
  fill('#studioWaste',['Waste_Type','Waste_Stream']); fill('#studioProcess',['Process']); fill('#studioResource',['Resource']); fill('#studioActor',['Actor']); fill('#studioFacility',['Facility']);
}
$('#studioSaveBtn')?.addEventListener('click',()=>{
  const name=$('#studioName').value.trim(); if(!name){alert('Give the loop a name first.');return;}
  const stages=[$('#studioWaste').value,$('#studioProcess').value,$('#studioResource').value,$('#studioActor').value,$('#studioFacility').value].filter(Boolean);
  if(stages.length<2){alert('Pick at least two stages.');return;}
  const arr=customLoopsLocal(); arr.push({name,desc:'Saved in Loop Studio (this browser).',stages,source:'user'}); saveCustomLoops(arr); renderYourLoops(); alert('Saved: '+name);
});
$('#studioExportBtn')?.addEventListener('click',()=>{
  const data=JSON.stringify(customLoopsLocal(),null,2); const blob=new Blob([data],{type:'application/json'}); const a=document.createElement('a'); a.href=URL.createObjectURL(blob); a.download='loops.json'; a.click();
  navigator.clipboard?.writeText(data).catch(()=>{});
});
$('#studioImportBtn')?.addEventListener('click',()=>{
  try{const arr=JSON.parse($('#studioImport').value); if(!Array.isArray(arr)) throw new Error('not an array');
    const good=arr.filter(x=>x&&x.name&&Array.isArray(x.stages)); if(!good.length) throw new Error('no valid loops');
    const merged=[...customLoopsLocal(),...good.map(x=>({...x,source:'user'}))]; saveCustomLoops(merged); renderYourLoops(); $('#studioImport').value=''; alert(`Imported ${good.length} loop(s).`);}
  catch(e){alert('Could not import: '+e.message);}
});
/* ---------- Ask for a loop: plain-language parsing against the sample ---------- */
const ALIASES={'dsny':'DSNY','sanitation':'DSNY','coffee':'CoffeeGrounds','yard':'YardWaste','food':'FoodScraps','spent grain':'SpentGrain','brewery':'SpentGrain','grease':'FatsOilsGrease','fog':'FatsOilsGrease','biogas':'Biogas','compost':'CompostAmendment','biochar':'Biochar','syngas':'Syngas','animal feed':'AnimalFeed','frass':'Frass','digestate':'DigestateFertilizer','brooklyn':'FACILITY-BK-COMPOST-01','queens':'AD_PLANT-QUEENS-02','bronx':'BSFL_FARM-BRONX-01','staten island':'BIOCHAR_PLANT-SI-01','anaerobic':'AnaerobicDigestion','aerobic':'AerobicComposting','vermi':'Vermicomposting','bsfl':'BlackSoldierFlyLarvae','larvae':'BlackSoldierFlyLarvae','urban farm':'UrbanFarm','waste processor':'Waste_Processor','hauler':'PrivateHauler','law 146':'NYCRegulationOrganicWaste','odor':'OdorControlRequirement','heavy metal':'HeavyMetal_Limit','restaurant':'RestaurantFoodWaste_Downtown','residential':'ResidentialOrganicsBrooklyn','citywide':'ResidentialOrganicsCitywide','staten island compost':'SICF_StatenIsland','newtown creek':'NewtownCreekAD','soundview':'SoundviewYardCompost','earth matter':'EarthMatterCommunity','community garden':'CommunityGarden','getcompost':'GetCompostDistribution','rng':'RNG','zero waste act':'ZeroWasteActOrganics','commercial waste zones':'CommercialWasteZones','ll146':'CommercialOrganicsLL146','drop-off':'CommunityFoodScraps'};
function matchNodes(text){
  const low=' '+text.toLowerCase().replace(/[^a-z0-9 ]/g,' ')+' '; const hits=[];
  kgData.nodes.forEach(n=>{const nm=n.name.toLowerCase(); const idx=low.indexOf(nm); if(idx>=0) hits.push({id:n.id,idx});});
  Object.entries(ALIASES).forEach(([k,id])=>{const idx=low.indexOf(' '+k+' '); if(idx>=0&&!hits.some(h=>h.id===id)) hits.push({id,idx});});
  // single distinctive words
  kgData.nodes.forEach(n=>{n.name.toLowerCase().split(/[^a-z]+/).filter(w=>w.length>=5).forEach(w=>{const idx=low.indexOf(' '+w+' '); if(idx>=0&&!hits.some(h=>h.id===n.id)) hits.push({id:n.id,idx});});});
  return hits.sort((a,b)=>a.idx-b.idx).map(h=>h.id).filter((v,i,a)=>a.indexOf(v)===i);
}
function findPath(from,to,max=7){
  const adj={}; kgData.edges.forEach(e=>{(adj[e.from]||(adj[e.from]=[])).push(e.to);});
  const q=[[from]], seen=new Set([from]);
  while(q.length){const p=q.shift(); const cur=p[p.length-1]; if(cur===to&&p.length>1) return p; if(p.length>max) continue;
    (adj[cur]||[]).forEach(n=>{if(!seen.has(n)){seen.add(n); q.push([...p,n]);}});}
  return null;
}
$('#askBtn')?.addEventListener('click',()=>{
  const text=$('#askInput').value.trim(); const out=$('#askOutput');
  if(!text){out.innerHTML='<p class="muted">Type a request first — for example, “coffee grounds to animal feed”.</p>'; return;}
  if(/every|all (elements|nodes|loops)/i.test(text)){out.innerHTML='<p>Showing every element’s loop below — tap any element in the gallery to play its loop.</p>'; document.querySelector('.kg-loops-card')?.scrollIntoView({behavior:'smooth'}); return;}
  const matched=matchNodes(text);
  if(matched.length>=2){
    const path=findPath(matched[0],matched[1]);
    if(path){const loop=stagesToLoop(path,`Path: ${kgName(path[0])} → ${kgName(path[path.length-1])}`,'sample path',path[0],null); renderLoopPlayer(loop);
      out.innerHTML=`<p>Found a real sample path: <strong>${path.map(kgName).join(' → ')}</strong>. It is playing in the loop player above (the final step back to the start is a dashed closure, not a sample edge, unless that edge exists).</p>`; return;}
    const loop=buildElementLoop(matched[0]); renderLoopPlayer(loop);
    out.innerHTML=`<p>I found <strong>${esc(kgName(matched[0]))}</strong> and <strong>${esc(kgName(matched[1]))}</strong>, but there is <strong>no directed sample path</strong> from the first to the second in the 43-node graph — so I have not invented one. Playing the first element’s loop instead; use Loop Studio below to propose a bridge, or copy the request for Muse to research a real one.</p>`; return;
  }
  if(matched.length===1){const loop=buildElementLoop(matched[0]); renderLoopPlayer(loop);
    out.innerHTML=`<p>Playing the loop for <strong>${esc(kgName(matched[0]))}</strong> in the loop player above.</p>`; return;}
  out.innerHTML=`<p><strong>Not in the sample.</strong> Nothing in “${esc(text)}” matches a node in the 43-node graph, so I have not guessed a pathway. Try a sample element (Food Scraps, Coffee Grounds, Biogas, Brooklyn, Anaerobic Digestion…), build a proposed loop in Loop Studio below, or copy the request for Muse — Muse can research whether a real pathway exists and add it to <code>loops.json</code> with labelled sources.</p>`;
});
$('#copyAskBtn')?.addEventListener('click',()=>{
  const text=$('#askInput').value.trim()||'[your loop request]';
  const msg=`Add a W2RKG loop to the waste web app (branch web-app, docs/loops.json): ${text}. Use the sample first (43 nodes / 81 edges in docs/kg.json); if the pathway is not in the sample, research real conversion data, label every source, and do not invent metrics. The loop format is {"name":"...","desc":"...","stages":["<node id>",...]} with stages in Waste → Process → Resource → Actor → Facility order. After pushing, the loop should appear in the app's Your loops gallery.`;
  navigator.clipboard?.writeText(msg).then(()=>{alert('Request copied — paste it into Muse chat.');}).catch(()=>{prompt('Copy this request for Muse:',msg);});
});


/* ---------- embedded AI assistant (mirrors copilot_service + ATMA chat) ---------- */
function wiMd(t){
  let h=esc(t);
  h=h.replace(/\*\*(.+?)\*\*/g,'<strong>$1</strong>').replace(/`([^`]+)`/g,'<code>$1</code>');
  h=h.replace(/\[([^\]]+)\]\(#(dashboard|live|bins|forecast|graph|contamination|connect|assistant)\)/g,'<a href="#$2">$1</a>');
  return h;
}
function wiChatHistory(){try{return JSON.parse(localStorage.getItem('wi_assistant_history')||'[]');}catch(e){return [];}}
function wiSaveChatHistory(){try{const msgs=$$('#wiChat .msg').map(d=>({who:d.classList.contains('me')?'you':'assistant',text:d.dataset.text||''})).slice(-50); localStorage.setItem('wi_assistant_history',JSON.stringify(msgs));}catch(e){}}
function wiAddMsg(who,text){
  const d=document.createElement('div'); d.className='msg'+(who==='you'?' me':''); d.dataset.text=text;
  d.innerHTML=`<div class="who">${who==='you'?'You':'Waste Assistant'}</div><div>${wiMd(text)}</div>`;
  $('#wiChat').appendChild(d); $('#wiChat').scrollTop=$('#wiChat').scrollHeight; wiSaveChatHistory(); return d;
}
function wiContext(){
  const urgent=fleet.filter(b=>b.fill>=80);
  const avg=fleet.length?Math.round(fleet.reduce((s,b)=>s+b.fill,0)/fleet.length):0;
  return `Waste Intelligence Platform web app (static GitHub Pages). Demo fleet: ${fleet.length} bins, average fill ${avg}%, urgent (>=80%): ${urgent.map(b=>`${b.id} ${b.site} ${b.fill}%`).join('; ')||'none'}. Knowledge graph: 43 nodes, 81 edges (31-node sample + 12 public-data nodes: citywide curbside organics, LL146 commercial organics, community drop-offs, Staten Island Compost Facility, Newtown Creek AD, Soundview, Earth Matter, community gardens, GetCompost, RNG, Zero Waste Act, Commercial Waste Zones) (Waste -> Process -> Resource -> Demand -> Facility). No node sits on a directed cycle in the sample: demand actors do not operate facilities, so loops have 4 real steps + 1 labelled bridge. Live data comes from NYC Open Data Socrata (DSNY tonnage ebb7-mvp5, diversion gaq9-z3hz, organics 6yag-pnij, facilities 6r9j-qrwz). Contamination stream map: recycling accepts Plastic, Metal, Glass, Paper; landfill accepts Other; organics accepts none of the detected litter materials. Forecasting: current-cycle least-squares trend, R-squared, time-to-full, z-score anomaly. Demo fleet numbers are NOT live sensor data.`;
}
function wiDemoAnswer(q){
  const l=q.toLowerCase();
  if(l.includes('groq')||l.includes('secret')||l.includes('api key')) return "Security model: a repo secret is never in this browser bundle and cannot power live chat. It is only used inside a GitHub Actions workflow to refresh docs/ai-briefing.json. Live chat needs a Groq key you paste in the Connect card above, stored only in this browser's localStorage and sent only to api.groq.com. With no key, I answer from the built-in demo knowledge base in this page.";
  if(l.includes('delete')||l.includes('remove a bin')||l.includes('change the route')||l.includes('modify')||l.includes('actuat')) return "I won't change bins or routes directly — this assistant is read-only, mirroring the platform copilot's guardrails (no write / delete / actuate actions). To change something, use the [Bins & Routes](#bins) view yourself, or the [Forecasting](#forecast) view for a bin. I can explain what a change would do first, if you like.";
  if(l.includes('urgent')||l.includes('bin')){
    const urgent=fleet.filter(b=>b.fill>=80);
    return `Demo fleet right now: ${fleet.length} bins, average fill ${Math.round(fleet.reduce((s,b)=>s+b.fill,0)/fleet.length)}%. Urgent bins (>=80%): ${urgent.length?urgent.map(b=>`${b.id} at ${b.site} (${b.fill}%)`).join(', '):'none'}. Open [Bins & Routes](#bins) to collect one, or [Forecasting](#forecast) to see when a bin will fill. These are demo bins — the hub API returns no bins — not live sensor readings.`;
  }
  if(l.includes('contamination')) return "Contamination check, from services/contamination/app.py: the production model is YOLOv11 (CatSat/yolov11-litter-materials). On Pages it cannot run, so the [Contamination](#contamination) view uses manual tagging with the backend's exact map: recycling accepts Plastic, Metal, Glass, Paper; landfill accepts Other; organics accepts none of those detected litter materials, so any of them in an organics bin is a contaminant by that map.";
  if(l.includes('troubleshoot')||l.includes('diagnos')||l.includes('not working')||l.includes("isn't working")||l.includes('broken')||l.includes("won't load")||l.includes('blank')||l.includes('fix')||l.includes('repair')) return "Run diagnostics first: press 'Run diagnostics' in the Diagnose & repair card in this Assistant view. It checks live Socrata feeds, the graph and loops files, both briefing sources, saved local data, and your Connect backends, then offers click-to-apply repairs (retry feeds, reload graph, reset demo fleet, clear saved data). Repairs are local to this browser only and never run from chat alone. It cannot fix a Pages deployment, a repo secret, an Actions workflow, or a server that is actually down — in those cases it tells you the exact next step instead of claiming a fix.";
  if(l.includes('loop')||l.includes('bridge')||l.includes('cycle')) return "The loop is Waste → Process → Resource → Demand → Facility → back to Waste. Honest caveat: no node in the 43-node graph sits on a directed cycle, because the sample's demand actors do not operate facilities. So every demonstration loop has 4 real steps plus 1 dashed, labelled bridge (demand → facility, or facility → next load). Try the loop gallery in the [Knowledge Graph](#graph) view, or ask for a specific element, e.g. 'What can Food Scraps become?'";
  if(l.includes('forecast')||l.includes('fill')||l.includes('anomaly')) return "Forecasting ports services/forecasting/app.py: drop pre-collection history after a fill drop over 30 points, fit a least-squares line to the current cycle, and report slope, R-squared, time-to-full, plus a z-score anomaly check (flag over 2). See the [Forecasting](#forecast) view, pick a bin, and add a reading to refit.";
  if(l.includes('tonnage')||l.includes('live')||l.includes('nyc data')||l.includes('socrata')) return "Live NYC data comes straight from NYC Open Data (Socrata, no key): DSNY Monthly Tonnage ebb7-mvp5, Recycling Diversion and Capture gaq9-z3hz, Other Organics 6yag-pnij, and Disposal Facilities 6r9j-qrwz. Open the [Live NYC Data](#live) view to filter and load them; if a live call fails, that view shows a labelled sample instead of pretending it is live.";
  const matched=kgData?matchNodes(q):[];
  if(matched.length){
    const loop=buildElementLoop(matched[0]);
    if(loop) return `${kgName(matched[0])} loop: ${loop.stages.map(s=>s.name).join(' → ')}. ${loop.transitions.filter(t=>t.real).length} of ${loop.transitions.length} steps are real sample edges; the rest are labelled bridges. Open the [Knowledge Graph](#graph) view and tap that element to play the animated loop with its full conversion metrics.`;
  }
  if(l.includes('knowledge graph')||l.includes('waste-to-resource')||l.includes('w2rkg')) return "The Waste-to-Resource Knowledge Graph (W2RKG) is the platform's semantic engine: waste types and streams → processes → resources → actors (demand) → facilities. The web app uses kg.json: the repo's 31-node / 55-edge sample plus 12 sourced public-data nodes (43 nodes / 81 edges), with EPA WARM v15 emissions factors on the new organics conversion edges. Open the [Knowledge Graph](#graph) view for the circular navigation ring, the animated flow, and a loop for every element.";
  return "I can explain this web app: bins and routes, forecasting, the knowledge graph and its loops, contamination checks, and live NYC data — all labelled as live, demo, or sample. Try one of the quick prompts above, or ask about a specific bin, waste type, process, or resource. With a Groq key saved above, I answer live via Groq; without one, I answer from the demo knowledge base in this page.";
}
let wiAbort=null, wiInitDone=false;
function wiInitAssistant(){
  if(wiInitDone) return; wiInitDone=true;
  const hasKey=!!localStorage.getItem('wi_groq_key');
  $('#wiKeyStatus').textContent=hasKey?'Key saved in this browser':'No key saved — demo mode';
  const savedModel=localStorage.getItem('wi_groq_model'); if(savedModel) $('#wiGroqModel').value=savedModel;
  const savedBackend=localStorage.getItem('wi_chat_backend'); if(savedBackend) $('#wiChatBackend').value=savedBackend;
  try{const h=wiChatHistory(); if(h.length){h.forEach(m=>wiAddMsg(m.who,m.text));} else wiAddMsg('assistant',"Hi — I'm the Waste Assistant. Ask about bins, forecasting, the knowledge graph, or contamination. With a Groq key saved above I answer live; without one I answer from the demo knowledge base in this page.");}catch(e){wiAddMsg('assistant',"Hi — I'm the Waste Assistant. Ask about bins, forecasting, the knowledge graph, or contamination.");}
  // Briefing sources (newest wins): this repo's own briefing, and the
  // OpenForge repo's briefing — the OpenForge workflow runs with the
  // GROQ_API secret stored in Etienne0101-lab/OpenForge-Workbench- and
  // publishes docs/waste-ai-briefing.json on OpenForge Pages (CORS: *),
  // so this app can read it without ever seeing the key. A secret in one
  // repo cannot be read by another repo's workflow, which is why the
  // OpenForge workflow must live in the OpenForge repo itself.
  Promise.allSettled([
    fetch('ai-briefing.json').then(r=>{if(!r.ok) throw new Error('no briefing'); return r.json();}).then(b=>({...b,_source:'Waste repo Actions (GROQ_API)'})),
    fetch('https://etienne0101-lab.github.io/OpenForge-Workbench-/waste-ai-briefing.json').then(r=>{if(!r.ok) throw new Error('no briefing'); return r.json();}).then(b=>({...b,_source:b._source||'OpenForge repo Actions (GROQ_API)'}))
  ]).then(results=>{
    const briefings=results.filter(r=>r.status==='fulfilled').map(r=>r.value).sort((a,b)=>String(b.generated_at||'').localeCompare(String(a.generated_at||'')));
    if(!briefings.length) throw new Error('no briefing');
    const b=briefings[0];
    $('#wiBriefing').innerHTML=`<p><span class="pill">${esc(b.generated_at||'')}</span> <span class="pill">${esc(b.model||'Groq')}</span> <span class="pill">${esc(b._source)}</span></p><p>${esc(b.briefing||'')}</p><p class="muted small">Sources: ${esc((b.source_datasets||[]).join(', ')||'NYC Open Data (Socrata)')}. Generated inside GitHub Actions from a repo secret; the key itself is never in this file.</p>`;
  }).catch(()=>{$('#wiBriefing').innerHTML='<p class="muted">No briefing yet. For the OpenForge route: copy <code>github-workflows/groq-waste-briefing-openforge.yml</code> to <code>.github/workflows/groq-waste-briefing.yml</code> in <code>Etienne0101-lab/OpenForge-Workbench-</code> (by hand — the GitHub App cannot create workflow files) and dispatch it there; it uses that repo\'s <code>GROQ_API</code> secret inside the runner only, then publishes <code>docs/waste-ai-briefing.json</code> on OpenForge Pages for this card. Alternative: add a <code>GROQ_API</code> secret to this waste repo and run <code>github-workflows/groq-briefing.yml</code> here instead.</p>';});
}
$('#wiSaveKeyBtn')?.addEventListener('click',()=>{const k=$('#wiGroqKey').value.trim(); if(!k){alert('Paste a Groq key first.');return;} localStorage.setItem('wi_groq_key',k); localStorage.setItem('wi_groq_model',$('#wiGroqModel').value); $('#wiKeyStatus').textContent='Key saved in this browser'; $('#wiGroqKey').value=''; wiAddMsg('assistant','Groq key saved in this browser only. Ask me something and I will answer live via Groq.');});
$('#wiRemoveKeyBtn')?.addEventListener('click',()=>{localStorage.removeItem('wi_groq_key'); $('#wiKeyStatus').textContent='No key saved — demo mode'; wiAddMsg('assistant','Saved Groq key removed. Back to offline demo mode.');});
$('#wiTestKeyBtn')?.addEventListener('click',async()=>{
  const k=localStorage.getItem('wi_groq_key')||$('#wiGroqKey').value.trim(); if(!k){$('#wiKeyResult').textContent='No key to test — paste one above, or use demo mode.'; return;}
  try{const r=await fetch('https://api.groq.com/openai/v1/models',{headers:{Authorization:'Bearer '+k}}); const j=await r.json().catch(()=>({})); $('#wiKeyResult').textContent=r.ok?`Key works: Groq returned ${(j.data||[]).length} models (error codes only are shown on failure; the key itself is never displayed).`:`Key test failed: HTTP ${r.status} — ${(j.error&&j.error.message)||'check the key and try again.'}`;}
  catch(e){$('#wiKeyResult').textContent='Key test could not reach Groq: '+e.message;}
});
$('#wiGroqModel')?.addEventListener('change',e=>localStorage.setItem('wi_groq_model',e.target.value));
$('#wiChatBackend')?.addEventListener('change',e=>localStorage.setItem('wi_chat_backend',e.target.value));
$$('[data-quick]').forEach(b=>b.addEventListener('click',()=>{$('#wiChatInput').value=b.dataset.quick; wiAsk();}));
async function wiAsk(){
  const inp=$('#wiChatInput'); const q=inp.value.trim(); if(!q) return; inp.value='';
  wiAddMsg('you',q);
  // Troubleshooting intent: ground truth is diagnostics, not the model.
  // Run diagnostics, summarise them, and stop — never claim a fix the
  // diagnostics did not perform, and never apply a repair from chat alone.
  if(/troubleshoot|diagnos|not working|isn't working|isnt working|broken|won't load|wont load|blank page|fix (it|this|the|my)|repair/i.test(q)){
    const d=await wiRunDiagnostics();
    const f=d&&d.fails.length?`Failing now: ${d.fails.join(', ')}.`:'Nothing failing right now.';
    const w=d&&d.warns.length?` Warnings: ${d.warns.join(', ')}.`:'';
    wiAddMsg('assistant',`Diagnostics run (${d?d.total:'?'} checks). ${f}${w} Repairs are in the Diagnose & repair card above — click the repair you want; destructive repairs confirm first. I have not applied any repair from this message. If a feed or backend is failing, the card's repair is retry/reload/re-probe; if a server, deployment, secret, or workflow is the problem, the card gives the exact next step instead.`);
    return;
  }
  if(wiStageFromChat(q)){wiAddMsg('assistant','Staged, not executed: see the Staged actions card above. Approve it to run it, or discard it. Nothing has changed yet.'); return;}
  const backend=$('#wiChatBackend').value; const model=$('#wiGroqModel').value; localStorage.setItem('wi_chat_backend',backend); localStorage.setItem('wi_groq_model',model);
  const key=localStorage.getItem('wi_groq_key');
  if(/show (me )?your (groq )?key|what is (the|my) (groq )?key|reveal.*key|print.*secret/i.test(q)){wiAddMsg('assistant','I will not reveal a saved key or secret value — not in chat, not in the app, and not in any file. If you need to replace it, paste a new key in the Connect card above (it overwrites the old one in this browser only).'); return;}
  if(/(delete|remove|destroy).*(bin|fleet)|change.*route.*to|modify.*(bin|fleet)|actuat|run.*(command|task)/i.test(q)&&!/explain|how (do|would)/i.test(q)){wiAddMsg('assistant',wiDemoAnswer(q)); return;}
  if(backend==='platform'){
    try{
      const ans=await window.wiBackendCopilotAsk(q);
      wiAddMsg('assistant',ans.answer+`  [Platform copilot${ans.model?` · model ${ans.model}`:''}${ans.tools&&ans.tools.length?` · tools: ${ans.tools.join(', ')}`:''}${ans.auditId?` · audit ${ans.auditId}`:''} — answered by the deployed copilot service, not by Groq direct or demo.]`);
    }catch(e){wiAddMsg('assistant',`Platform copilot failed: ${e.message} Nothing was sent to Groq or demo as a silent fallback — fix the backend URL/key in Connect, or switch the backend selector to Groq direct or Demo.`);}
    return;
  }
  if(backend==='demo'||!key){wiAddMsg('assistant',wiDemoAnswer(q)+'  [Offline demo answer — save a Groq key above for live streaming.]'); return;}
  const sys=`You are the Waste Intelligence Assistant for the EcoCode Waste Intelligence Platform web app. Answer concisely and accurately about bins, forecasting, the knowledge graph, contamination, and NYC waste data. Grounding context: ${wiContext()} Rules: never claim demo fleet numbers are live sensor data; never invent conversion metrics — use only the sample numbers in context or say they are not in the sample; never reveal, repeat, or hint at any API key or secret; do not help delete, modify, or actuate backend systems; if the user reports something broken, do not claim you fixed it — tell them to run diagnostics in the Diagnose & repair card, which can only repair things in this browser. For other changes, explain and point to the relevant view instead.`;
  const history=wiChatHistory().filter(m=>m.who==='you'||m.who==='assistant').slice(-10).map(m=>({role:m.who==='you'?'user':'assistant',content:m.text}));
  const messages=[{role:'system',content:sys},...history,{role:'user',content:q}];
  const msgEl=wiAddMsg('assistant','Thinking…'); const bodyEl=msgEl.querySelector('div:last-child');
  wiAbort=new AbortController();
  try{
    const r=await fetch('https://api.groq.com/openai/v1/chat/completions',{method:'POST',headers:{'Content-Type':'application/json',Authorization:'Bearer '+key},signal:wiAbort.signal,body:JSON.stringify({model,messages,temperature:0.3,max_tokens:1200,stream:true})});
    if(!r.ok||!r.body){const t=await r.text(); bodyEl.textContent=`Chat error (${r.status}): ${t.slice(0,300)}. Check your key/model in the Connect card above.`; wiSaveChatHistory(); return;}
    const reader=r.body.getReader(); const dec=new TextDecoder(); let buf='', full='';
    while(true){const {done,value}=await reader.read(); if(done) break; buf+=dec.decode(value,{stream:true}); const parts=buf.split('\n\n'); buf=parts.pop();
      for(const p of parts){const line=p.trim(); if(!line.startsWith('data:')) continue; const data=line.slice(5).trim(); if(data==='[DONE]') continue;
        try{const j=JSON.parse(data); const tok=j.choices&&j.choices[0]&&j.choices[0].delta?j.choices[0].delta.content:''; if(tok){full+=tok; msgEl.dataset.text=full; bodyEl.innerHTML=wiMd(full); $('#wiChat').scrollTop=$('#wiChat').scrollHeight;}}catch{}}}
    if(!full) bodyEl.textContent='Stream completed without a text response — try again or switch model/backend.';
    wiSaveChatHistory();
  }catch(e){if(e.name==='AbortError') bodyEl.textContent+='  [Stopped]'; else bodyEl.textContent='Network error: '+e.message+'. Check your key and connection.'; wiSaveChatHistory();}
  finally{wiAbort=null;}
}
$('#wiSendBtn')?.addEventListener('click',wiAsk);
$('#wiStopBtn')?.addEventListener('click',()=>{if(wiAbort) wiAbort.abort();});
$('#wiChatInput')?.addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault(); wiAsk();}});
$('#wiNewChatBtn')?.addEventListener('click',()=>{$('#wiChat').innerHTML=''; localStorage.removeItem('wi_assistant_history'); wiAddMsg('assistant','New chat started. Ask about bins, forecasting, the knowledge graph, or contamination.');});


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

/* ---------- connect: see backend.js (wiInitBackend) ---------- */

/* ---------- limited troubleshooting: diagnose & repair (local browser only) ---------- */
async function wiProbe(url, ms=8000){
  const t0=performance.now();
  try{const r=await fetch(url,{signal:AbortSignal.timeout(ms)}); return {ok:r.ok,status:r.status,ms:Math.round(performance.now()-t0)};}
  catch(e){return {ok:false,status:0,ms:Math.round(performance.now()-t0),error:e.name==='TimeoutError'?'timed out':e.message};}
}
function wiLocalInfo(key){
  try{
    const v=localStorage.getItem(key);
    if(v===null) return {present:false};
    let parsed='unparseable';
    try{const j=JSON.parse(v); parsed=Array.isArray(j)?j.length+' items':typeof j;}catch(e){}
    return {present:true,bytes:v.length,parsed};
  }catch(e){return {present:false,error:e.message};}
}
let wiLastDiag=null;
async function wiRunDiagnostics(){
  const box=$('#wiDiagResults'), status=$('#wiDiagStatus'), actions=$('#wiRepairActions');
  if(!box) return null;
  status.textContent='Running…'; box.innerHTML='<p class="muted">Checking feeds, files, briefings, local data, and backends…</p>'; actions.innerHTML='';
  const checks=[];
  const add=(name,state,detail,repair)=>checks.push({name,state,detail,repair});
  add('Browser connection', navigator.onLine?'ok':'fail', navigator.onLine?'Online.':'Browser reports offline — repairs cannot reach any feed until the device is back online.', null);
  add('Page origin', location.protocol==='https:'?'ok':'warn', location.protocol+' — Pages is HTTPS; plain-HTTP backends will be blocked by the browser (mixed content), not by this app.', null);
  const socrata=await Promise.all(['ebb7-mvp5','gaq9-z3hz','6yag-pnij','6r9j-qrwz'].map(async id=>{const p=await wiProbe(`https://data.cityofnewyork.us/resource/${id}.json?$limit=1`); return {id,p};}));
  socrata.forEach(({id,p})=>add(`Live feed ${id}`, p.ok?'ok':'fail', p.ok?`HTTP ${p.status} in ${p.ms} ms.`:`Unreachable (${p.status||p.error||'network error'}). The Live and Dashboard views will show a labelled sample until it returns.`, 'retry-live'));
  try{const r=await fetch('kg.json'); const j=await r.json(); add('Knowledge graph file', (j.nodes||[]).length===43&&(j.edges||[]).length===81?'ok':'warn', `${(j.nodes||[]).length} nodes / ${(j.edges||[]).length} edges (expected 43 / 81).`, 'reload-kg');}
  catch(e){add('Knowledge graph file','fail','kg.json could not be loaded — the Graph view will be empty until it loads.','reload-kg');}
  try{const r=await fetch('loops.json'); const j=await r.json(); add('Curated loops file', Array.isArray(j)&&j.length?'ok':'warn', `${Array.isArray(j)?j.length:0} curated loops.`, 'reload-kg');}
  catch(e){add('Curated loops file','fail','loops.json could not be loaded — the loop gallery will miss curated loops.','reload-kg');}
  const bw=await wiProbe('ai-briefing.json'); add('Briefing — waste repo', bw.ok?'ok':'warn', bw.ok?`HTTP ${bw.status}.`:'No waste-repo briefing published yet (workflow not run, or file missing). This is expected until a briefing workflow runs.', null);
  const bo=await wiProbe('https://etienne0101-lab.github.io/OpenForge-Workbench-/waste-ai-briefing.json'); add('Briefing — OpenForge repo (GROQ_API)', bo.ok?'ok':'warn', bo.ok?`HTTP ${bo.status}.`:'No OpenForge briefing published yet — copy the workflow to the OpenForge repo and dispatch it there. This card cannot run that workflow itself.', null);
  const fleetInfo=wiLocalInfo('wip_fleet'); add('Saved demo fleet', fleetInfo.present?(fleetInfo.parsed==='unparseable'?'fail':'ok'):'warn', fleetInfo.present?`${fleetInfo.bytes} bytes, ${fleetInfo.parsed}.`:'No saved fleet — the seeded demo fleet is in use.', fleetInfo.parsed==='unparseable'?'reset-fleet':null);
  const loopsInfo=wiLocalInfo('wip_custom_loops'); add('Saved custom loops', loopsInfo.parsed==='unparseable'?'fail':'ok', loopsInfo.present?`${loopsInfo.bytes} bytes, ${loopsInfo.parsed}.`:'None saved.', loopsInfo.parsed==='unparseable'?'clear-custom-loops':null);
  const histInfo=wiLocalInfo('wi_assistant_history'); add('Assistant history', 'ok', histInfo.present?`${histInfo.bytes} bytes, ${histInfo.parsed}.`:'None saved in this browser.', null);
  add('Groq key (presence only)', localStorage.getItem('wi_groq_key')?'ok':'warn', localStorage.getItem('wi_groq_key')?'A key is saved in this browser (its value is never read or shown here).':'No key saved — live chat falls back to demo mode. Paste a key in the Connect card above for live chat.', null);
  const urls=[['Hub API',$('#hubUrl')?.value||''],['Forecasting',$('#fcUrl')?.value||''],['Contamination',$('#fcContamUrl')?.value||'']].filter(([,u])=>u.trim());
  if(!urls.length){add('Connect backends','warn','No backend URLs entered in the Connect view this session — nothing to probe. Enter them in Connect and press Probe, or run diagnostics again after entering them.',null);}
  else{
    for(const [name,url] of urls){
      const p=await wiProbe(url.replace(/\/$/,'')+'/health',6000);
      const mixed=location.protocol==='https:'&&url.startsWith('http://');
      add(`Backend ${name}`, p.ok?'ok':'fail', p.ok?`HTTP ${p.status} in ${p.ms} ms.`:`Unreachable (${p.status||p.error||'blocked'}). ${mixed?'This is likely mixed-content blocking: an HTTPS page cannot call a plain-HTTP backend — run this page locally (same folder, python3 -m http.server) or put the backend behind HTTPS.':''}`, 'reprobe-connect');
    }
  }
  const fails=checks.filter(c=>c.state==='fail'), warns=checks.filter(c=>c.state==='warn');
  box.innerHTML='<ul class="list">'+checks.map(c=>`<li><span class="pill${c.state==='ok'?'':' warn'}">${c.state.toUpperCase()}</span> <strong>${esc(c.name)}</strong> — ${esc(c.detail)}</li>`).join('')+'</ul>';
  status.textContent=`Done: ${checks.filter(c=>c.state==='ok').length} OK, ${fails.length} failed, ${warns.length} warnings.`;
  const repairs=[...new Set(checks.map(c=>c.repair).filter(Boolean))];
  const labels={'retry-live':'Retry live feeds','reload-kg':'Reload graph + loops','reprobe-connect':'Re-probe Connect backends','reset-fleet':'Reset demo fleet (confirm)','clear-custom-loops':'Clear custom loops (confirm)','clear-history':'Clear assistant history','clear-all-local':'Clear all saved app data (confirm, key kept)','reload-page':'Reload page'};
  actions.innerHTML='<p class="muted small">Repairs (each needs a click; destructive ones confirm first):</p>'+[...repairs,'clear-history','reload-page'].map(a=>`<button class="btn" data-repair="${a}">${labels[a]}</button>`).join('');
  $$('#wiRepairActions [data-repair]').forEach(b=>b.addEventListener('click',()=>wiDoRepair(b.dataset.repair)));
  wiLastDiag={fails:fails.map(c=>c.name),warns:warns.map(c=>c.name),total:checks.length};
  return wiLastDiag;
}
async function wiDoRepair(action){
  const out=$('#wiRepairResult'); out.textContent='Working…';
  try{
    if(action==='retry-live'){await loadLive(); await loadDashboard(); out.textContent='Live feeds retried — check the Dashboard and Live views for the LIVE badge, or a labelled sample if a feed is still down.';}
    else if(action==='reload-kg'){await loadKG(); out.textContent='Graph and loops reloaded from kg.json / loops.json.';}
    else if(action==='reprobe-connect'){const f=$('#connectForm'); if(f) f.dispatchEvent(new Event('submit',{cancelable:true})); out.textContent='Connect backends re-probed — see the Connect view result.';}
    else if(action==='reset-fleet'){if(!confirm('Reset the demo fleet to its seeded defaults and delete saved readings? This cannot be undone.')){out.textContent='Fleet reset cancelled.'; return;} fleet=structuredClone(DEFAULT_BINS); selectedBins.clear(); saveFleet(); localStorage.removeItem('wip_readings'); renderBins(); loadDashboard(); out.textContent='Demo fleet reset to seeded defaults.';}
    else if(action==='clear-custom-loops'){if(!confirm('Delete all custom loops saved in this browser? Curated loops are unaffected.')){out.textContent='Custom-loop clear cancelled.'; return;} localStorage.removeItem('wip_custom_loops'); await loadKG(); out.textContent='Custom loops cleared.';}
    else if(action==='clear-history'){localStorage.removeItem('wi_assistant_history'); $('#wiChat').innerHTML=''; wiAddMsg('assistant','History cleared. Ask about bins, forecasting, the knowledge graph, or contamination.'); out.textContent='Assistant history cleared.';}
    else if(action==='clear-all-local'){if(!confirm('Clear all saved app data in this browser (fleet, readings, custom loops, assistant history)? Your Groq key is NOT cleared by this.')){out.textContent='Clear-all cancelled.'; return;} ['wip_fleet','wip_readings','wip_custom_loops','wi_assistant_history'].forEach(k=>localStorage.removeItem(k)); fleet=structuredClone(DEFAULT_BINS); selectedBins.clear(); renderBins(); loadDashboard(); await loadKG(); $('#wiChat').innerHTML=''; wiAddMsg('assistant','Saved app data cleared (Groq key kept). Ask about bins, forecasting, the knowledge graph, or contamination.'); out.textContent='Saved app data cleared (Groq key kept).';}
    else if(action==='reload-page'){location.reload(); return;}
    await wiRunDiagnostics();
  }catch(e){out.textContent='Repair failed: '+e.message;}
}
$('#wiDiagBtn')?.addEventListener('click',wiRunDiagnostics);


/* ---------- dashboard grid + interactive city grid (2D, no 3D, no phased loop) ---------- */
function dashXY(b){const x=20+((b.lon+74.25)/( -73.70+74.25))*560, y=320-((b.lat-40.50)/(40.90-40.50))*300; return [Math.max(15,Math.min(585,x)),Math.max(15,Math.min(325,y))];}
function dashStatusColor(f){return f>=80?'#ec4899':f>=60?'#f59e0b':'#22c55e';}
function dashRender(agg, live){
  const urgent=fleet.filter(b=>b.fill>=80);
  const avg=fleet.length?fleet.reduce((s,b)=>s+b.fill,0)/fleet.length:0;
  const byBorough={};
  fleet.forEach(b=>{const x=byBorough[b.borough]||={borough:b.borough,n:0,sum:0}; x.n++; x.sum+=b.fill;});
  const boroughs=Object.values(byBorough).sort((a,b)=>b.sum/b.n-a.sum/a.n);
  $('#dashBoroughBars').innerHTML=boroughs.map(x=>{const a=x.sum/x.n; return `<div class="dash-row"><span>${esc(x.borough)}</span><span class="bar"><i style="width:${a}%" class="${a>=80?'high':a>=60?'mid':''}"></i></span><span>${a.toFixed(0)}% · ${x.n}</span></div>`;}).join('');
  const totals={refuse:0,paper:0,mgp:0,organics:0};
  agg.forEach(r=>{totals.refuse+=r.refuse; totals.paper+=r.paper; totals.mgp+=r.mgp; totals.organics+=r.organics;});
  const totalT=totals.refuse+totals.paper+totals.mgp+totals.organics;
  $('#dashWaveTotal').textContent=fmt(totalT)+' t';
  $('#dashWaveBadge').textContent=live?('LIVE · '+agg.month):'SAMPLE · live feed unreachable';
  $('#dashWaveNote').textContent=live?`Latest month in the DSNY feed (${agg.month}), all boroughs combined. Bars are borough totals.`:'Live feed unreachable — this is the labelled sample, not live tonnage.';
  const maxB=Math.max(...agg.map(r=>r.refuse+r.paper+r.mgp+r.organics),1);
  $('#dashWaveBars').innerHTML=agg.map(r=>{const t=r.refuse+r.paper+r.mgp+r.organics; return `<i style="--h:${Math.max(12,Math.round(t/maxB*100))}%;height:${Math.max(12,Math.round(t/maxB*100))}%" title="${esc(r.borough)}: ${fmt(t)} t"></i>`;}).join('');
  const streams=[['Refuse',totals.refuse,'#64748b'],['Paper',totals.paper,'#2dd4bf'],['MGP',totals.mgp,'#f59e0b'],['Organics',totals.organics,'#22c55e']];
  let off=0; const C=2*Math.PI*80;
  $('#dashDonutSvg').innerHTML=streams.map(([name,v,color])=>{const frac=totalT?v/totalT:0, dash=frac*C, gap=C-dash; const el=`<circle cx="100" cy="100" r="80" fill="none" stroke="${color}" stroke-width="26" stroke-dasharray="${dash.toFixed(1)} ${gap.toFixed(1)}" stroke-dashoffset="${(-off).toFixed(1)}"/>`; off+=dash; return el;}).join('');
  $('#dashDonutCentre').innerHTML=`${fmt(totalT)} t<br><span style="font-size:.8rem;font-weight:400;color:#94a3b8">total tonnage</span>`;
  $('#dashDonutLegend').innerHTML='<div class="dash-legend">'+streams.map(([name,v,color])=>`<div><span style="background:${color}"></span>${name}: ${fmt(v)} t (${totalT?Math.round(v/totalT*100):0}%)</div>`).join('')+'</div>';
  $('#dashHeatDots').innerHTML=fleet.map(b=>`<button style="background:${dashStatusColor(b.fill)}" title="${esc(b.id)} — ${esc(b.site)}, ${esc(b.borough)} · ${b.fill}%" aria-label="${esc(b.id)} ${b.fill} percent" data-bin="${b.id}"></button>`).join('');
  $$('#dashHeatDots [data-bin]').forEach(btn=>btn.addEventListener('click',()=>{location.hash='#forecast?bin='+btn.dataset.bin;}));
  const healthy=fleet.length?Math.round(fleet.filter(b=>b.fill<80).length/fleet.length*100):0;
  const organicsShare=totalT?Math.round(totals.organics/totalT*100):0;
  const rings=[['Healthy bins',healthy,'#22c55e'],['Live feed',live?100:0,'#2dd4bf'],['Organics share',organicsShare,'#f59e0b']];
  $('#dashRings').innerHTML=rings.map(([name,v,color])=>{const circ=2*Math.PI*34; return `<div class="dash-ring"><svg viewBox="0 0 90 90"><circle cx="45" cy="45" r="34" fill="none" stroke="#334155" stroke-width="9"/><circle cx="45" cy="45" r="34" fill="none" stroke="${color}" stroke-width="9" stroke-dasharray="${(v/100*circ).toFixed(1)} ${circ.toFixed(1)}" stroke-linecap="round"/></svg><b>${v}%</b><span>${name}</span></div>`;}).join('');
  $('#dashRingsNote').textContent='Healthy = bins below 80% fill. Live feed = DSNY tonnage reachable on this load. Organics share = organics tonnes ÷ total tonnes.';
  $('#dashTonnageBars').innerHTML=agg.map(r=>{const t=r.refuse+r.paper+r.mgp+r.organics; return `<div><i style="height:${Math.max(10,Math.round(t/maxB*110))}px"></i><span>${fmt(t)} t<br>${esc(r.borough)}</span></div>`;}).join('');
  const top=urgent.length?[...urgent].sort((a,b)=>b.fill-a.fill)[0]:fleet[0];
  if(top){
    const pts=historyFor(top), maxF=100, minF=0;
    const X=(i)=>20+i/(pts.length-1)*480, Y=(v)=>160-(v-minF)/(maxF-minF)*140;
    const line=pts.map((p,i)=>`${i?'L':'M'}${X(i).toFixed(1)},${Y(p.fill).toFixed(1)}`).join(' ');
    $('#dashForecastSvg').innerHTML=`<path d="${line} L${X(pts.length-1).toFixed(1)},160 L20,160 Z" fill="rgba(34,197,94,.18)" stroke="none"/><path d="${line}" fill="none" stroke="#22c55e" stroke-width="2.5"/>`;
    $('#dashForecastNote').innerHTML=`<strong>${esc(top.id)}</strong> — ${esc(top.site)}, ${esc(top.borough)} · now ${top.fill}%. History is the demo fill series used by Forecasting. <a href="#forecast?bin=${top.id}">Open full forecast →</a>`;
  }
  $('#dashSideLive').textContent=live?('LIVE · '+agg.month):'SAMPLE · feed unreachable';
  $('#dashSideUrgent').textContent=urgent.length?`${urgent.length} urgent bin${urgent.length===1?'':'s'}`:'No urgent bins';
  try{wiOpsBrief(agg, live);}catch(e){}
  $('#dashBellCount').textContent=urgent.length;
  $('#dashGridBadge').textContent=live?'demo fleet · live tonnage':'demo fleet · sample tonnage';
  dashGrid();
}
let dashReplayHour=47;
function dashFill(b){
  if(dashReplayHour>=47) return b.fill;
  const pts=historyFor(b); const pt=pts[Math.min(dashReplayHour, pts.length-1)];
  return pt?pt.fill:b.fill;
}
function dashGrid(){
  const svg=$('#dashGridSvg'); if(!svg) return;
  const showFleet=$('#dashLayerFleet')?.checked!==false, showRoute=$('#dashLayerRoute')?.checked!==false, showHeat=$('#dashLayerHeat')?.checked!==false, showLabels=$('#dashLayerLabels')?.checked!==false;
  let streets='';
  for(let x=60;x<600;x+=60) streets+=`<line x1="${x}" y1="10" x2="${x}" y2="330" class="dash-grid-street"/>`;
  for(let y=50;y<340;y+=50) streets+=`<line x1="10" y1="${y}" x2="590" y2="${y}" class="dash-grid-street"/>`;
  const labels=showLabels?`<g fill="#94a3b8" font-size="12"><text x="90" y="40">Manhattan</text><text x="330" y="120">Brooklyn</text><text x="380" y="60">Queens</text><text x="330" y="210">Bronx</text><text x="90" y="290">Staten Island</text></g>`:'';
  const urgent=[...fleet].map(b=>({...b,fill:dashFill(b)})).filter(b=>b.fill>=80).sort((a,b)=>b.fill-a.fill);
  const routePath=showRoute&&urgent.length>1?`<path class="dash-grid-route" d="${urgent.map((b,i)=>`${i?'L':'M'}${dashXY(b).join(',')}`).join(' ')}"/>`:'';
  const dots=showFleet?fleet.map(b=>{const f=dashFill(b); const [x,y]=dashXY(b); const r=showHeat?4+f/14:6; return `<g><circle class="dash-grid-pulse" cx="${x}" cy="${y}" r="6" style="${f>=80?'':'display:none'}"/><circle class="dash-grid-dot" cx="${x}" cy="${y}" r="${r.toFixed(1)}" fill="${dashStatusColor(f)}" data-bin="${b.id}" tabindex="0" role="button" aria-label="${esc(b.id)} ${esc(b.site)}, ${f} percent, open forecast"><title>${esc(b.id)} — ${esc(b.site)} · ${f}%</title></circle></g>`;}).join(''):'';
  svg.innerHTML=streets+labels+routePath+dots;
  $$('#dashGridSvg .dash-grid-dot').forEach(c=>c.addEventListener('click',()=>{location.hash='#forecast?bin='+c.dataset.bin;}));
  $$('#dashGridSvg .dash-grid-dot').forEach(c=>c.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault(); location.hash='#forecast?bin='+c.dataset.bin;}}));
  const top=urgent[0];
  $('#dashGridNote').innerHTML=dashReplayHour<47?`Replay: hour ${dashReplayHour} of the last 48 (demo history, not live now). Urgent at that hour: ${urgent.length?urgent.map(b=>esc(b.id)).join(', '):'none'}. Move the slider to 47 for now.`:(top?`Urgent route: ${urgent.map(b=>esc(b.id)).join(' → ')}. Tap any dot for its forecast.`:'No urgent bins right now — the route layer appears when a bin reaches 80%.');
}
['dashLayerFleet','dashLayerRoute','dashLayerHeat','dashLayerLabels'].forEach(id=>$('#'+id)?.addEventListener('change',dashGrid));
$('#dashPulseBtn')?.addEventListener('click',()=>{const hero=$('#view-dashboard .dash-hero'); hero.classList.toggle('paused'); $('#dashPulseBtn').textContent=hero.classList.contains('paused')?'▶ Resume pulses':'⏸ Pause pulses';});
$('#dashReplay')?.addEventListener('input',e=>{dashReplayHour=+e.target.value; const lab=$('#dashReplayLabel'); if(lab) lab.textContent=dashReplayHour>=47?'now':`hour ${dashReplayHour} / 47`; dashGrid();});
let dashReplayTimer=null;
$('#dashReplayPlay')?.addEventListener('click',()=>{
  const btn=$('#dashReplayPlay');
  if(dashReplayTimer){clearInterval(dashReplayTimer); dashReplayTimer=null; btn.textContent='▶ Play replay'; return;}
  if(dashReplayHour>=47) dashReplayHour=0;
  btn.textContent='⏸ Pause replay';
  dashReplayTimer=setInterval(()=>{
    dashReplayHour++;
    const slider=$('#dashReplay'); if(slider) slider.value=dashReplayHour;
    const lab=$('#dashReplayLabel'); if(lab) lab.textContent=dashReplayHour>=47?'now':`hour ${dashReplayHour} / 47`;
    dashGrid();
    if(dashReplayHour>=47){clearInterval(dashReplayTimer); dashReplayTimer=null; btn.textContent='▶ Play replay';}
  },400);
});
$('#whatifBtn')?.addEventListener('click',()=>{
  const v=+($('#whatifVehicles')?.value||1); const urgent=fleet.filter(b=>b.fill>=80).length;
  const cleared=Math.min(urgent, v*8); const left=urgent-cleared;
  const out=$('#whatifOut'); if(out) out.innerHTML=`<strong>Simulated, 4 hours, +${v} vehicle${v===1?'':'s'}:</strong> urgent bins ${urgent} → ${left} (clears ${cleared}). Assumption: 1 vehicle clears 1 urgent bin per 30 minutes, starting now. <strong>This is not a live forecast and changes nothing live</strong> — approve a real re-route in Bins & Routes, or stage it in the Assistant, to act on it.`;
});
$('#dashSearch')?.addEventListener('keydown',e=>{if(e.key==='Enter'){const v=$('#dashSearch').value.trim(); const inp=$('#binSearch'); if(inp){inp.value=v; inp.dispatchEvent(new Event('input'));} location.hash='#bins';}});



/* ---------- Round 1 overhaul: roles, saved views, Ops Brief, staged actions ---------- */
const ROLES={
 dispatcher:{brief:'Dispatcher: exceptions first — urgent bins, the city grid, and the route layer.',order:['Urgent bins','Fleet fill by borough','Live tonnage','Tonnage by borough','Forecast trend','Tonnage mix','Fill heatmap','At a glance','The loop']},
 depot:{brief:'Depot manager: capacity first — fleet fill, live tonnage, and tonnage by borough.',order:['Fleet fill by borough','Live tonnage','Tonnage by borough','Urgent bins','Forecast trend','Fill heatmap','At a glance','Tonnage mix','The loop']},
 analyst:{brief:'Analyst: evidence first — forecast trend, tonnage mix, and the loop.',order:['Forecast trend','Tonnage mix','Live tonnage','Tonnage by borough','Fleet fill by borough','Urgent bins','Fill heatmap','At a glance','The loop']},
 executive:{brief:'Executive: the city in one screen — live tonnage, tonnage by borough, and the brief above.',order:['Live tonnage','Tonnage by borough','Tonnage mix','Urgent bins','Fleet fill by borough','Forecast trend','Fill heatmap','At a glance','The loop']},
 crew:{brief:'Field crew: your bins first — urgent bins and the fill heatmap, nothing else in the way.',order:['Urgent bins','Fill heatmap','Fleet fill by borough','Live tonnage','Forecast trend','Tonnage by borough','Tonnage mix','At a glance','The loop']},
};
function wiRole(){try{return localStorage.getItem('wip_role')||'dispatcher';}catch(e){return 'dispatcher';}}
function wiApplyRole(role){
  try{localStorage.setItem('wip_role',role);}catch(e){}
  const r=ROLES[role]||ROLES.dispatcher;
  const brief=$('#roleBrief'); if(brief) brief.textContent=r.brief;
  $$('.role-bar [data-role]').forEach(b=>b.classList.toggle('active',b.dataset.role===role));
  const grid=document.querySelector('.dash-grid');
  const cards=$$('.dash-grid .dash-card');
  cards.forEach(card=>{
    const h=card.querySelector('h2')?.textContent||'';
    const idx=r.order.findIndex(o=>h.startsWith(o));
    card.style.order=idx>=0?idx:99;
    card.classList.toggle('role-focus', idx===0);
  });
  // Physical DOM reorder, not CSS order alone: grid spans make a CSS-only
  // reorder hard to see, and a screen reader follows DOM order, not CSS order.
  if(grid){const sorted=[...cards].sort((a,b)=>(+a.style.order)-(+b.style.order)); sorted.forEach(c=>grid.appendChild(c));}
}
function wiSavedViews(){try{return JSON.parse(localStorage.getItem('wip_saved_views')||'[]');}catch(e){return [];}}
function wiRenderSavedViews(){
  const el=$('#savedViews'); if(!el) return;
  const views=wiSavedViews();
  el.innerHTML=views.length?views.map((v,i)=>`<button type="button" data-saved="${i}">${esc(v.name)}</button>`).join(''):'<span class="muted small">none yet</span>';
  $$('#savedViews [data-saved]').forEach(b=>b.addEventListener('click',()=>{
    const v=wiSavedViews()[+b.dataset.saved]; if(!v) return;
    if(v.role) wiApplyRole(v.role);
    if(v.hash) location.hash=v.hash;
  }));
}
function wiInitRoles(){
  $$('.role-bar [data-role]').forEach(b=>b.addEventListener('click',()=>wiApplyRole(b.dataset.role)));
  $('#wiSaveViewBtn')?.addEventListener('click',()=>{
    const name=prompt('Name for this saved view? (role + current view are saved with it)');
    if(!name) return;
    const views=wiSavedViews(); views.push({name:name.trim(),role:wiRole(),hash:location.hash||'#dashboard'});
    try{localStorage.setItem('wip_saved_views',JSON.stringify(views));}catch(e){}
    wiRenderSavedViews();
  });
  wiApplyRole(wiRole()); wiRenderSavedViews();
}
function wiOpsBrief(agg, live){
  const el=$('#opsBriefBody'); if(!el) return;
  const urgent=fleet.filter(b=>b.fill>=80).sort((a,b)=>b.fill-a.fill);
  const avg=fleet.length?fleet.reduce((s,b)=>s+b.fill,0)/fleet.length:0;
  const total=agg.reduce((s,r)=>s+r.refuse+r.paper+r.mgp+r.organics,0);
  const organics=agg.reduce((s,r)=>s+r.organics,0);
  const top=urgent[0];
  let fc='';
  if(top){const a=analyse(historyFor(top)); fc=a.toFull!==Infinity?` <span class="forecast">Forecast: ${esc(top.id)} reaches full in about ${Math.round(a.toFull)} hours (slope ${a.slope.toFixed(2)}/h, R² ${a.r2.toFixed(2)})</span> — a forecast, not a measurement.`:' <span class="forecast">Forecast: no rising trend detected for the most urgent bin.</span>';}
  el.innerHTML=`<p><span class="measured">Measured now: ${fleet.length} demo bins, ${avg.toFixed(0)}% average fill, ${urgent.length} urgent bin${urgent.length===1?'':'s'}.</span> <span class="measured">Latest live tonnage (${esc(agg.month)}): ${fmt(total)} t, organics ${total?Math.round(organics/total*100):0}%.</span>${fc}</p><p><strong>Next action:</strong> ${top?`<a href="#forecast?bin=${top.id}">open ${esc(top.id)} (${esc(top.site)}) in Forecasting</a>`: 'no bin needs urgent action right now.'} — and the source for every number here is labelled in its card below: ${live?'live DSNY tonnage':'labelled sample tonnage (live feed unreachable)'} plus the demo fleet.</p>`;
}
function wiStageAction(title, detail, actionKey){
  const ul=$('#wiStaged'); if(!ul) return;
  const li=document.createElement('li'); li.className='staged-item';
  li.innerHTML=`<strong>${esc(title)}</strong><p class="muted small">${esc(detail)}</p><div class="controls"><button class="btn primary" data-approve>Approve</button><button class="btn" data-discard>Discard</button></div>`;
  li.querySelector('[data-approve]').addEventListener('click',()=>{
    if(actionKey==='open-urgent'){const inp=$('#binSearch'); if(inp){inp.value=''; inp.dispatchEvent(new Event('input'));} location.hash='#bins';}
    else if(actionKey==='nav-bins'){location.hash='#bins';}
    else if(actionKey==='save-view'){const name=prompt('Name for this saved view?'); if(name){const views=wiSavedViews(); views.push({name:name.trim(),role:wiRole(),hash:location.hash||'#dashboard'}); try{localStorage.setItem('wip_saved_views',JSON.stringify(views));}catch(e){} wiRenderSavedViews();}}
    else if(actionKey==='export-urgent'){const data=JSON.stringify(fleet.filter(b=>b.fill>=80),null,2); const a=document.createElement('a'); a.href=URL.createObjectURL(new Blob([data],{type:'application/json'})); a.download='urgent-bins.json'; a.click(); URL.revokeObjectURL(a.href);}
    li.remove(); wiStagedNote();
    const conf=$('#wiStagedConfirm');
    if(actionKey==='export-urgent'&&conf) conf.textContent='Approved — urgent-bins.json downloaded in this browser.';
    if(actionKey==='save-view'&&conf) conf.textContent='Approved — view saved. Find it under Saved views on the Dashboard.';
    if(actionKey==='open-urgent'&&conf) conf.textContent='Approved — opening Bins & Routes.';
    if(actionKey==='nav-bins'&&conf) conf.textContent='Approved — opening Bins & Routes, where you make the change yourself. The assistant executed nothing.';
  });
  li.querySelector('[data-discard]').addEventListener('click',()=>{li.remove(); wiStagedNote();});
  ul.appendChild(li); wiStagedNote();
  const note=$('#wiStagedNote'); if(note) note.textContent='Staged actions wait for your Approve click. Nothing here has been executed yet.';
}
function wiStagedNote(){const ul=$('#wiStaged'); const note=$('#wiStagedNote'); if(ul&&note&&!ul.children.length) note.textContent='No staged actions yet. Try in chat: "stage an export of the urgent bins", "stage saving this view", or "stage a route change".';}
function wiStageFromChat(q){
  const l=q.toLowerCase();
  if(/export.*urgent|urgent.*export/.test(l)){wiStageAction('Export urgent bins as JSON','Source: demo fleet, bins at 80% or above right now. Approve to download urgent-bins.json in this browser.','export-urgent'); return true;}
  if(/save.*view|stage.*view/.test(l)){wiStageAction('Save this view','Saves the current view + role preset to Saved views in this browser. Approve, then name it.','save-view'); return true;}
  if(/open.*urgent|show.*urgent/.test(l)){wiStageAction('Open urgent bins','Navigates to Bins & Routes. No bin is changed by this action.','open-urgent'); return true;}
  if(/delete|remove.*bin|reassign|change.*route|actuat/.test(l)){wiStageAction('High-risk change — NOT executed by the assistant','You asked for a bin/route change. The assistant will never delete bins, reassign a fleet, or change a route from chat. Approving this only opens the Bins view, where you make the change yourself, with the full fleet in front of you.','nav-bins'); return true;}
  return false;
}


/* ---------- Round 2 overhaul: Cmd-K, annotations, (PWA shell in sw.js/manifest.json) ---------- */
function cmdkItems(){
  const views=[['Dashboard','#dashboard'],['Live NYC Data','#live'],['Bins & Routes','#bins'],['Forecasting','#forecast'],['Knowledge Graph','#graph'],['Contamination','#contamination'],['Connect','#connect'],['Assistant','#assistant']];
  const items=views.map(([label,hash])=>({label,hint:'View',run:hash}));
  fleet.forEach(b=>items.push({label:`${b.id} — ${b.site}, ${b.borough} · ${b.fill}%`,hint:'Bin forecast',run:`#forecast?bin=${b.id}`}));
  items.push({label:'Stage export of urgent bins',hint:'Staged action (approval queue)',run:'stage:export'});
  items.push({label:'Stage saving this view',hint:'Staged action (approval queue)',run:'stage:save'});
  items.push({label:'Diagnose the app',hint:'Assistant',run:'#assistant'});
  return items;
}
let cmdkList=[], cmdkSel=0, cmdkLastFocus=null;
function cmdkRender(){
  const q=($('#cmdkInput')?.value||'').toLowerCase().trim();
  const words=q?q.split(/\s+/):[];
  cmdkList=cmdkItems().filter(it=>words.every(w=>it.label.toLowerCase().includes(w))).slice(0,12);
  cmdkSel=0;
  const ul=$('#cmdkResults'); if(!ul) return;
  ul.innerHTML=cmdkList.length?cmdkList.map((it,i)=>`<li class="${i===cmdkSel?'sel':''}" data-i="${i}"><strong>${esc(it.label)}</strong> <span class="muted small">${esc(it.hint)}</span></li>`).join(''):'<li class="muted small">No matches. Try a view name, a bin id, or "stage".</li>';
  $$('#cmdkResults li[data-i]').forEach(li=>li.addEventListener('click',()=>cmdkActivate(+li.dataset.i)));
}
function cmdkOpen(){const d=$('#cmdk'); if(!d) return; cmdkLastFocus=document.activeElement; d.classList.remove('hidden'); cmdkRender(); const inp=$('#cmdkInput'); if(inp) inp.focus();}
function cmdkClose(){const d=$('#cmdk'); if(!d) return; d.classList.add('hidden'); if(cmdkLastFocus&&cmdkLastFocus.focus) cmdkLastFocus.focus();}
function cmdkActivate(i){
  const it=cmdkList[i]; if(!it) return;
  cmdkClose();
  if(it.run==='stage:export'){location.hash='#assistant'; setTimeout(()=>{wiStageAction('Export urgent bins as JSON','Source: demo fleet, bins at 80% or above right now. Approve to download urgent-bins.json in this browser.','export-urgent');},50); return;}
  if(it.run==='stage:save'){location.hash='#assistant'; setTimeout(()=>{wiStageAction('Save this view','Saves the current view + role preset to Saved views in this browser. Approve, then name it.','save-view');},50); return;}
  location.hash=it.run;
}
function wiInitCmdK(){
  $('#cmdkBtn')?.addEventListener('click',cmdkOpen);
  $('#cmdkInput')?.addEventListener('input',cmdkRender);
  $('#cmdkInput')?.addEventListener('keydown',e=>{
    if(e.key==='ArrowDown'){e.preventDefault(); cmdkSel=Math.min(cmdkSel+1, Math.max(0,cmdkList.length-1)); $$('#cmdkResults li').forEach((li,j)=>li.classList.toggle('sel',j===cmdkSel));}
    else if(e.key==='ArrowUp'){e.preventDefault(); cmdkSel=Math.max(0,cmdkSel-1); $$('#cmdkResults li').forEach((li,j)=>li.classList.toggle('sel',j===cmdkSel));}
    else if(e.key==='Enter'){e.preventDefault(); cmdkActivate(cmdkSel);}
    else if(e.key==='Escape'){cmdkClose();}
  });
  $('#cmdk')?.addEventListener('click',e=>{if(e.target.id==='cmdk') cmdkClose();});
  document.addEventListener('keydown',e=>{
    if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==='k'){e.preventDefault(); const d=$('#cmdk'); if(d&&!d.classList.contains('hidden')) cmdkClose(); else cmdkOpen();}
    else if(e.key==='Escape'){const d=$('#cmdk'); if(d&&!d.classList.contains('hidden')) cmdkClose();}
  });
}
function wiAnnoLoad(){try{return JSON.parse(localStorage.getItem('wip_annotations')||'[]');}catch(e){return [];}}
function wiAnnoRender(){
  const sel=$('#annoTarget'); if(sel&&!sel.options.length){
    const opts=[['Dashboard','#dashboard'],...VIEWS.filter(v=>v!=='dashboard').map(v=>[v.charAt(0).toUpperCase()+v.slice(1),'#'+v]),...fleet.map(b=>[`${b.id} — ${b.site}`,'#forecast?bin='+b.id])];
    sel.innerHTML=opts.map(([label,hash])=>`<option value="${hash}">${esc(label)}</option>`).join('');
  }
  const ul=$('#annoList'); if(!ul) return;
  const filt=$('#annoFilter')?.value||'all';
  let items=wiAnnoLoad().map((a,i)=>({...a,_i:i})).reverse();
  if(filt==='dashboard') items=items.filter(a=>a.target==='#dashboard');
  if(filt==='bins') items=items.filter(a=>a.target.startsWith('#forecast?bin='));
  ul.innerHTML=items.length?items.map((a)=>{const idx=a._i; return `<li class="staged-item"><strong>${esc(a.targetLabel)}</strong> <span class="muted small">${esc(new Date(a.time).toLocaleString())} · You (this browser)</span><p>${esc(a.text)}</p><div class="controls"><a class="btn" href="${esc(a.target)}">Open pinned view →</a><button class="btn" data-del="${idx}">Delete</button></div></li>`;}).join(''):'<li class="muted small">No annotations yet in this browser.</li>';
  $$('#annoList [data-del]').forEach(b=>b.addEventListener('click',()=>{const all=wiAnnoLoad(); all.splice(+b.dataset.del,1); try{localStorage.setItem('wip_annotations',JSON.stringify(all));}catch(e){} wiAnnoRender();}));
}
function wiInitAnno(){
  $('#annoAddBtn')?.addEventListener('click',()=>{
    const text=($('#annoText')?.value||'').trim(); if(!text) return;
    const sel=$('#annoTarget'); const target=sel?sel.value:'#dashboard'; const targetLabel=sel?sel.options[sel.selectedIndex]?.text||target:target;
    const all=wiAnnoLoad(); all.push({text,target,targetLabel,time:new Date().toISOString()});
    try{localStorage.setItem('wip_annotations',JSON.stringify(all));}catch(e){}
    const inp=$('#annoText'); if(inp) inp.value='';
    wiAnnoRender();
  });
  $('#annoFilter')?.addEventListener('change',wiAnnoRender);
  wiAnnoRender();
}


/* ---------- Round 4: generative AI layout (approval-first, no model on-page) ----------
   How it works: the user's goal text is matched against LAYOUT_INTENTS
   (a published registry of intents -> dashboard card orders). The match
   produces a PREVIEW with a reason; nothing moves until Apply is clicked,
   and Reset restores the role layout. A future AI service plugs in by
   replacing window.WIPLayout.generate with a model call that returns
   {order, reason} — preview/approval/reset are unchanged. This is the
   deliberate opposite of opaque algorithmic reshuffling: the user asks,
   sees the proposed order, and approves it. */
const LAYOUT_INTENTS=[
  {id:'urgent', label:'Urgent response', keywords:['urgent','route','response','emergency','dispatch','critical'], order:['Urgent bins','Fleet fill by borough','Live tonnage','Forecast trend','Tonnage by borough','Tonnage mix','Fill heatmap','At a glance','The loop']},
  {id:'executive', label:'Executive summary', keywords:['executive','summary','overview','management','briefing','board'], order:['Live tonnage','Tonnage by borough','Tonnage mix','Urgent bins','Fleet fill by borough','Forecast trend','Fill heatmap','At a glance','The loop']},
  {id:'analyst', label:'Analyst evidence', keywords:['analyst','evidence','forecast','trend','data','analysis'], order:['Forecast trend','Tonnage mix','Live tonnage','Tonnage by borough','Fleet fill by borough','Urgent bins','Fill heatmap','At a glance','The loop']},
  {id:'crew', label:'Field crew focus', keywords:['crew','field','collection','driver','route crew','on the road'], order:['Urgent bins','Fill heatmap','Fleet fill by borough','Live tonnage','Forecast trend','Tonnage by borough','Tonnage mix','At a glance','The loop']},
  {id:'depot', label:'Depot capacity', keywords:['depot','capacity','fleet','yard'], order:['Fleet fill by borough','Live tonnage','Tonnage by borough','Urgent bins','Forecast trend','Fill heatmap','At a glance','Tonnage mix','The loop']},
];
const LAYOUT_CARDS=['Urgent bins','Fleet fill by borough','Live tonnage','Tonnage by borough','Forecast trend','Tonnage mix','Fill heatmap','At a glance','The loop'];
function wiLayoutGenerate(goal){
  const g=(goal||'').toLowerCase();
  let best=null, bestScore=0;
  LAYOUT_INTENTS.forEach(it=>{
    const score=it.keywords.filter(k=>g.includes(k)).length;
    if(score>bestScore){bestScore=score; best=it;}
  });
  if(!best){
    const roleOrder=(ROLES[wiRole()]||ROLES.dispatcher).order;
    return {order:roleOrder.slice(), reason:'No intent keyword matched your goal, so the preview starts from your current role layout. Add a word like "urgent", "executive", "forecast", or "crew" and generate again.', intent:'(none matched)'};
  }
  const order=best.order.slice();
  LAYOUT_CARDS.forEach(c=>{if(!order.includes(c)) order.push(c);});
  return {order:order, reason:`Matched intent "${best.label}" from your words (${best.keywords.filter(k=>g.includes(k)).join(', ')}). Card order below is the proposal — nothing has moved yet.`, intent:best.label};
}
function wiApplyLayoutOrder(order){
  const grid=document.querySelector('.dash-grid'); if(!grid) return;
  const cards=$$('.dash-grid .dash-card');
  cards.forEach(card=>{
    const h=card.querySelector('h2')?.textContent||'';
    const idx=order.findIndex(o=>h.startsWith(o));
    card.style.order=idx>=0?idx:99;
    card.classList.toggle('role-focus', idx===0);
  });
  const sorted=[...cards].sort((a,b)=>(+a.style.order)-(+b.style.order));
  sorted.forEach(c=>grid.appendChild(c));
}
let wiPendingLayout=null;
function wiInitLayout(){
  const reg=$('#layoutRegistry');
  if(reg) reg.innerHTML=LAYOUT_INTENTS.map(it=>`<strong>${esc(it.label)}</strong> — keywords: ${esc(it.keywords.join(', '))} → order: ${esc(it.order.join(' · '))}`).join('<br>');
  $('#layoutGenerate')?.addEventListener('click',()=>{
    const goal=$('#layoutGoal')?.value||'';
    const gen=wiLayoutGenerate(goal); wiPendingLayout=gen.order;
    const prev=$('#layoutPreview'); if(!prev) return;
    prev.innerHTML=`<p><strong>Proposed layout (${esc(gen.intent)}):</strong> ${esc(gen.reason)}</p><ol>${gen.order.map(o=>`<li>${esc(o)}</li>`).join('')}</ol><div class="controls"><button class="btn primary" id="layoutApply" type="button">Apply this layout</button></div>`;
    $('#layoutApply')?.addEventListener('click',()=>{
      wiApplyLayoutOrder(wiPendingLayout);
      try{localStorage.setItem('wip_custom_layout',JSON.stringify({goal:goal, order:wiPendingLayout, time:new Date().toISOString()}));}catch(e){}
      prev.innerHTML=`<p><strong>Applied.</strong> Dashboard cards are now in the generated order, and the layout is saved in this browser. Use Reset to return to your role layout.</p>`;
    });
  });
  $('#layoutReset')?.addEventListener('click',()=>{
    try{localStorage.removeItem('wip_custom_layout');}catch(e){}
    wiApplyRole(wiRole());
    const prev=$('#layoutPreview'); if(prev) prev.innerHTML='<p class="muted small">Reset to your role layout.</p>';
  });
}
window.WIPLayout={intents:LAYOUT_INTENTS, cards:LAYOUT_CARDS, generate:wiLayoutGenerate, apply:wiApplyLayoutOrder, reset:()=>wiApplyRole(wiRole())};

/* ---------- boot ---------- */
try{renderBins(); loadDashboard(); loadLive(); loadKG(); route(); wiInitRoles();}catch(e){const j=document.getElementById('jsBuild'); if(j) j.textContent+=' · BOOT ERROR: '+e.message;}
try{wiInitCmdK(); const j=document.getElementById('jsBuild'); if(j) j.textContent+=' · CmdK bound';}catch(e){const j=document.getElementById('jsBuild'); if(j) j.textContent+=' · CmdK ERROR: '+e.message;}
try{wiInitAnno(); const j=document.getElementById('jsBuild'); if(j) j.textContent+=' · Anno bound';}catch(e){const j=document.getElementById('jsBuild'); if(j) j.textContent+=' · Anno ERROR: '+e.message;}
try{wiInitLayout(); const j=document.getElementById('jsBuild'); if(j) j.textContent+=' · Layout bound';}catch(e){const j=document.getElementById('jsBuild'); if(j) j.textContent+=' · Layout ERROR: '+e.message;}

/* ---------- City Overview: KPI row, alerts, charts — same data as dashRender ---------- */
function renderOverview(agg, live){
  const urgent=fleet.filter(b=>b.fill>=80).sort((a,b)=>b.fill-a.fill);
  const watch=fleet.filter(b=>b.fill>=70&&b.fill<80).sort((a,b)=>b.fill-a.fill);
  const avg=fleet.length?fleet.reduce((s,b)=>s+b.fill,0)/fleet.length:0;
  const totals={refuse:0,paper:0,mgp:0,organics:0};
  agg.forEach(r=>{totals.refuse+=r.refuse; totals.paper+=r.paper; totals.mgp+=r.mgp; totals.organics+=r.organics;});
  const totalT=totals.refuse+totals.paper+totals.mgp+totals.organics;
  const orgShare=totalT?Math.round(totals.organics/totalT*100):0;
  $('#ovKpiUrgent').textContent=urgent.length+(urgent.length===1?' bin':' bins');
  $('#ovKpiUrgentSub').textContent=urgent.length?`Highest: ${urgent[0].id} at ${urgent[0].fill}% · of ${fleet.length} demo bins`:`No bin at 80% or above · of ${fleet.length} demo bins`;
  $('#ovKpiFill').textContent=Math.round(avg)+' /100';
  $('#ovKpiOrganics').textContent=orgShare+'%';
  $('#ovKpiOrganicsSub').textContent=live?`of live tonnage · ${agg.month}`:'of sample tonnage · live feed unreachable';
  $('#ovKpiTonnage').textContent=fmt(totalT)+' t';
  $('#ovKpiTonnageSub').textContent=live?`latest month · LIVE · ${agg.month}`:'latest month · SAMPLE · live feed unreachable';
  const top=urgent[0]||fleet[0];
  const alerts=[];
  urgent.slice(0,4).forEach(b=>alerts.push({t:'Now',dot:'red',html:`<strong>${esc(b.id)}</strong> urgent at ${b.fill}% — ${esc(b.site)}, ${esc(b.borough)} · <a href="#forecast?bin=${b.id}">Forecast →</a>`}));
  watch.slice(0,2).forEach(b=>alerts.push({t:'Watch',dot:'amber',html:`<strong>${esc(b.id)}</strong> approaching urgent at ${b.fill}% — ${esc(b.site)} · <a href="#forecast?bin=${b.id}">Forecast →</a>`}));
  if(top){const a=analyse(historyFor(top)); const h=a.toFull===Infinity?null:Math.round(a.toFull);
    alerts.push({t:h==null?'Steady':'in ~'+h+' h',dot:h==null?'teal':'amber',html:`Forecast: <strong>${esc(top.id)}</strong> ${h==null?'shows no rising trend':'fills in about '+h+' hours'} (slope ${a.slope.toFixed(2)}/h, R² ${a.r2.toFixed(2)}) · <a href="#forecast?bin=${top.id}">Full forecast →</a>`});}
  alerts.push({t:live?'Live':'Sample',dot:live?'teal':'grey',html:live?`DSNY tonnage feed reachable — ${agg.month}, ${fmt(totalT)} t across boroughs.`:'DSNY tonnage feed unreachable — dashboard shows the labelled sample.'});
  $('#ovAlertsBadge').textContent=alerts.length+' alerts';
  $('#ovAlerts').innerHTML=alerts.map(a=>`<li><span class="ov-alert-time">${esc(a.t)}</span><span class="ov-alert-dot ${a.dot}"></span><span>${a.html}</span></li>`).join('');
  const maxB=Math.max(...agg.map(r=>r.refuse+r.paper+r.mgp+r.organics),1);
  $('#ovBoroughBadge').textContent=live?('LIVE · '+agg.month):'SAMPLE';
  $('#ovBoroughBars').innerHTML=agg.map(r=>{const t=r.refuse+r.paper+r.mgp+r.organics; return `<div class="ov-bar-row"><span>${esc(r.borough)}</span><span class="bar"><i style="width:${Math.round(t/maxB*100)}%"></i></span><span>${fmt(t)} t</span></div>`;}).join('');
  if(top){
    const pts=historyFor(top);
    const X=i=>20+i/(pts.length-1)*480, Y=v=>160-v/100*140;
    const line=pts.map((p,i)=>`${i?'L':'M'}${X(i).toFixed(1)},${Y(p.fill).toFixed(1)}`).join(' ');
    $('#ovTrendSvg').innerHTML=`<path d="${line} L${X(pts.length-1).toFixed(1)},160 L20,160 Z" fill="rgba(45,212,191,.16)" stroke="none"/><path d="${line}" fill="none" stroke="#2dd4bf" stroke-width="2.5"/>`;
    $('#ovTrendNote').innerHTML=`<strong>${esc(top.id)}</strong> — ${esc(top.site)}, ${esc(top.borough)} · now ${top.fill}%. Demo fill series, same as the Forecasting view.`;
  }
  const hours=urgent.map(b=>{const a=analyse(historyFor(b)); return {b, h:a.toFull};}).sort((x,y)=>(x.h===Infinity?1e9:x.h)-(y.h===Infinity?1e9:y.h));
  const maxH=Math.max(...hours.filter(x=>x.h!==Infinity).map(x=>x.h),1);
  $('#ovHoursBars').innerHTML=hours.length?hours.map(({b,h})=>`<div class="ov-bar-row"><span>${esc(b.id)}</span><span class="bar"><i class="${b.fill>=90?'high':''}" style="width:${h===Infinity?8:Math.max(8,Math.round(h/maxH*100))}%"></i></span><span>${h===Infinity?'steady':'~'+Math.round(h)+' h'}</span></div>`).join(''):'<p class="muted small">No urgent bins right now.</p>';
}
