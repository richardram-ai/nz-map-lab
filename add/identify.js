// Species suggestions from a photo, using the Aotearoa Species Classifier (TAIAO, University of Waikato).
// Runs entirely on the phone. The model (about 79 MB) and the ONNX Runtime engine (about 22 MB) are downloaded
// once and kept in this phone's storage, so suggestions also work without signal.
// Model licence: CC BY-NC 4.0. See /models/asc-small-v1/README.md.
(function () {
  const BASE = '/models/asc-small-v1/';
  const ORT = '/add/ort/';
  const CACHE = 'nzml-model-asc-small-v1';
  let manifest = null, labels = null, session = null, backend = '', loading = null;

  async function getManifest() {
    if (manifest) return manifest;
    const r = await cachedFetch(BASE + 'manifest.json');
    manifest = await r.json();
    return manifest;
  }
  // Network first for small files would break offline use, so everything here is cache first.
  async function cachedFetch(url, onBytes) {
    const c = await caches.open(CACHE);
    let res = await c.match(url);
    if (res) return res;
    res = await fetch(url);
    if (!res.ok) throw new Error('Download failed (' + res.status + ')');
    if (onBytes && res.body) {
      const reader = res.body.getReader(), chunks = [];
      for (;;) { const { done, value } = await reader.read(); if (done) break; chunks.push(value); onBytes(value.length); }
      const blob = new Blob(chunks);
      await c.put(url, new Response(blob, { headers: { 'Content-Type': 'application/octet-stream' } }));
      return new Response(blob);
    }
    await c.put(url, res.clone());
    return res;
  }

  async function downloaded() {
    try {
      const m = await getManifest(), c = await caches.open(CACHE);
      for (const p of [...m.parts, m.labels]) if (!(await c.match(BASE + p))) return false;
      for (const f of ['ort-wasm-simd-threaded.jsep.wasm', 'ort-wasm-simd-threaded.jsep.mjs', 'ort.webgpu.min.js'])
        if (!(await caches.match(ORT + f))) return false;
      return true;
    } catch (e) { return false; }
  }

  function loadScript(src) {
    return new Promise((ok, fail) => {
      if (window.ort) return ok();
      const s = document.createElement('script'); s.src = src; s.onload = ok; s.onerror = () => fail(new Error('Could not load the identification engine')); document.head.appendChild(s);
    });
  }

  // Download (first time) and start the model. onProgress(fraction, text).
  function load(onProgress = () => {}) {
    if (session) return Promise.resolve();
    if (loading) return loading;
    loading = (async () => {
      const m = await getManifest();
      // The engine: fetch through the cache so it is kept for offline use.
      const engine = ['ort.webgpu.min.js', 'ort-wasm-simd-threaded.jsep.mjs', 'ort-wasm-simd-threaded.jsep.wasm'];
      const c = await caches.open(CACHE);
      const total = m.bytes + 22.2e6; let got = 0;
      const tick = n => { got += n; onProgress(Math.min(1, got / total), `Downloading ${Math.round(got / 1e6)} of ${Math.round(total / 1e6)} MB`); };
      for (const f of engine) {
        if (!(await caches.match(ORT + f))) { const r = await fetch(ORT + f); if (!r.ok) throw new Error('Download failed'); const b = await r.blob(); tick(b.size); await c.put(ORT + f, new Response(b, { headers: { 'Content-Type': r.headers.get('Content-Type') || '' } })); }
        else tick(f.endsWith('.wasm') ? 21.66e6 : 0.2e6);
      }
      const parts = [];
      for (const p of m.parts) parts.push(new Uint8Array(await (await cachedFetch(BASE + p, tick)).arrayBuffer()));
      labels = await (await cachedFetch(BASE + m.labels)).json();
      onProgress(1, 'Starting the identification helper…');
      const bytes = new Uint8Array(m.bytes); let o = 0; for (const p of parts) { bytes.set(p, o); o += p.length; }
      await loadScript(ORT + 'ort.webgpu.min.js');
      ort.env.wasm.wasmPaths = location.origin + ORT;
      ort.env.wasm.numThreads = self.crossOriginIsolated ? Math.min(4, navigator.hardwareConcurrency || 2) : 1;
      const tries = navigator.gpu ? [['webgpu'], ['wasm']] : [['wasm']];
      let err;
      for (const eps of tries) {
        try { session = await ort.InferenceSession.create(bytes, { executionProviders: eps, graphOptimizationLevel: 'all' }); backend = eps[0]; break; }
        catch (e) { err = e; }
      }
      if (!session) throw err || new Error('The identification helper could not start on this phone');
    })();
    loading.catch(() => { loading = null; });
    return loading;
  }

  // Resize so the shorter side is 416 px with an antialiased bilinear (triangle) filter, the same method as the
  // torchvision resize used in training, then take the centre 384 × 384, scale to [-1, 1], lay out as 1 × 3 × 384 × 384.
  // Only the rows and columns inside the crop are computed.
  function weights(inSize, outSize, first, count) {
    const scale = inSize / outSize, fs = Math.max(scale, 1), support = fs, W = [];
    for (let o = first; o < first + count; o++) {
      const centre = (o + 0.5) * scale;
      const lo = Math.max(Math.floor(centre - support + 0.5), 0), hi = Math.min(Math.floor(centre + support + 0.5), inSize);
      const w = []; let sum = 0;
      for (let k = lo; k < hi; k++) { const v = Math.max(0, 1 - Math.abs((k - centre + 0.5) / fs)); w.push(v); sum += v; }
      W.push({ lo, w: w.map(v => v / sum) });
    }
    return W;
  }
  async function toTensor(blob) {
    const bmp = await createImageBitmap(blob, { imageOrientation: 'from-image' });
    const w = bmp.width, h = bmp.height;
    const cv = new OffscreenCanvas(w, h), g = cv.getContext('2d', { willReadFrequently: true });
    g.drawImage(bmp, 0, 0); const px = g.getImageData(0, 0, w, h).data;
    const short = Math.min(w, h), rw = w <= h ? 416 : Math.floor(416 * w / h), rh = h <= w ? 416 : Math.floor(416 * h / w);
    const cx = Math.floor((rw - 384) / 2), cy = Math.floor((rh - 384) / 2);
    const WX = weights(w, rw, cx, 384), WY = weights(h, rh, cy, 384);
    // vertical pass over the needed rows, all columns
    const tmp = new Float32Array(384 * w * 3);
    for (let y = 0; y < 384; y++) { const { lo, w: ws } = WY[y];
      for (let x = 0; x < w; x++) { let r = 0, gg = 0, b = 0;
        for (let k = 0; k < ws.length; k++) { const q = ((lo + k) * w + x) * 4, f = ws[k]; r += px[q] * f; gg += px[q + 1] * f; b += px[q + 2] * f; }
        const t = (y * w + x) * 3; tmp[t] = r; tmp[t + 1] = gg; tmp[t + 2] = b; } }
    // horizontal pass over the needed columns
    const n = 384 * 384, out = new Float32Array(3 * n);
    for (let y = 0; y < 384; y++) for (let x = 0; x < 384; x++) { const { lo, w: ws } = WX[x]; let r = 0, gg = 0, b = 0;
      for (let k = 0; k < ws.length; k++) { const t = (y * w + lo + k) * 3, f = ws[k]; r += tmp[t] * f; gg += tmp[t + 1] * f; b += tmp[t + 2] * f; }
      const i = y * 384 + x, cl = v => Math.min(255, Math.max(0, Math.round(v)));
      out[i] = cl(r) / 127.5 - 1; out[n + i] = cl(gg) / 127.5 - 1; out[2 * n + i] = cl(b) / 127.5 - 1; }
    return new ort.Tensor('float32', out, [1, 3, 384, 384]);
  }

  // Returns the five most likely species: [{sci, common, maori, p, mpi}], p as 0–1.
  async function identify(blob) {
    await load();
    const m = await getManifest(), t0 = performance.now();
    const out = await session.run({ [m.input.name]: await toTensor(blob) });
    const z = out[m.output].data, T = 1 / m.temperature;
    let max = -Infinity; for (let i = 0; i < z.length; i++) if (z[i] > max) max = z[i];
    const e = new Float64Array(z.length); let sum = 0;
    for (let i = 0; i < z.length; i++) { e[i] = Math.exp((z[i] - max) * T); sum += e[i]; }
    const idx = [...e.keys()].sort((a, b) => e[b] - e[a]).slice(0, 5);
    return {
      ms: Math.round(performance.now() - t0), backend,
      top: idx.map(i => { const L = labels[i]; return { sci: L[0], common: L[1], maori: L[2], mpi: L[3], p: e[i] / sum }; }),
    };
  }

  async function size() { const m = await getManifest(); return m.bytes + 22.2e6; }

  window.NZID = { load, identify, downloaded, size, credit: 'Aotearoa Species Classifier (TAIAO, University of Waikato)', link: 'https://github.com/Waikato/aotearoa-species-classifier', model: 'asc-small-onnx-384-v1.0' };
})();
