// Keeps the phone form working with poor or no signal.
// The page and its libraries are cached; recently viewed map tiles are cached; saving uses the page's own queue.
const SHELL = 'nzml-shell-v5', TILES = 'nzml-tiles-v1', MAX_TILES = 400;
const SHELL_URLS = ['/add/', '/add/identify.js', '/config/site.json', '/add/manifest.webmanifest', '/add/icon-192.png',
  'https://cdnjs.cloudflare.com/ajax/libs/maplibre-gl/4.7.1/maplibre-gl.js',
  'https://cdnjs.cloudflare.com/ajax/libs/maplibre-gl/4.7.1/maplibre-gl.css',
  'https://cdn.jsdelivr.net/npm/exifr@7.1.3/dist/full.umd.js'];
self.addEventListener('install', e => { e.waitUntil(caches.open(SHELL).then(c => c.addAll(SHELL_URLS)).then(() => self.skipWaiting())); });
self.addEventListener('activate', e => { e.waitUntil(self.clients.claim()); });
self.addEventListener('fetch', e => {
  const req = e.request; if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.pathname.startsWith('/api/')) return;               // always live
  if (url.pathname.startsWith('/linz/')) {                     // map tiles: cache first, keep a few hundred
    e.respondWith(caches.open(TILES).then(async c => {
      const hit = await c.match(req); if (hit) return hit;
      const res = await fetch(req); if (res.ok) { c.put(req, res.clone()); c.keys().then(k => { if (k.length > MAX_TILES) c.delete(k[0]); }); }
      return res;
    }));
    return;
  }
  if (url.pathname === '/add/identify.js') { // the helper script: network first so fixes arrive
    e.respondWith(fetch(req).then(res => { const copy = res.clone(); caches.open(SHELL).then(c => c.put(req, copy)); return res; }).catch(() => caches.match(req)));
    return;
  }
  if (url.pathname === '/add/' || url.pathname === '/add' || url.pathname === '/add/index.html' || url.pathname === '/config/site.json') { // page and settings: network first
    const key = url.pathname === '/config/site.json' ? '/config/site.json' : '/add/';
    e.respondWith(fetch(req).then(res => { const copy = res.clone(); caches.open(SHELL).then(c => c.put(key, copy)); return res; }).catch(() => caches.match(key)));
    return;
  }
  e.respondWith(caches.match(req).then(hit => hit || fetch(req)));
});
