/* Waste Intelligence service worker — offline app shell for field crews.
   Caches the app shell (HTML/CSS/JS/data files) so the app opens offline.
   Live Socrata feeds are network-first and fall back to the cached shell +
   the app's labelled sample data when unreachable. No personal data, no
   citizen data, and no Groq key are cached: keys live in localStorage only
   and are never in a cacheable response. Bump CACHE on every shell change. */
const CACHE='wip-shell-overhaul10';
const SHELL=['./index.html','./styles.css?v=overhaul10','./app.js?v=overhaul10','./twin.js?v=twin2','./backend.js?v=backend2','./kg.json','./loops.json','./manifest.json','./icon.svg'];
self.addEventListener('install',e=>{e.waitUntil(caches.open(CACHE).then(c=>c.addAll(SHELL)).then(()=>self.skipWaiting()));});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim()));});
self.addEventListener('fetch',e=>{
  const url=new URL(e.request.url);
  if(url.hostname==='data.cityofnewyork.us'){
    e.respondWith(fetch(e.request).catch(()=>caches.match(e.request)));
    return;
  }
  if(e.request.method!=='GET') return;
  // Network-first for the app shell: a cache-first shell froze a stale
  // app.js after a push (the exact Round 2 failure). Offline still works
  // because a failed fetch falls back to the cache, then to index.html.
  e.respondWith(fetch(e.request).then(res=>{const copy=res.clone(); caches.open(CACHE).then(c=>c.put(e.request,copy)); return res;}).catch(()=>caches.match(e.request).then(hit=>hit||caches.match('./index.html'))));
});
