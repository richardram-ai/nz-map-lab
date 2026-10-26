// Serves LINZ aerial photo tiles for the test area, adding the LINZ Data Service key on the server.
// The key lives in the Cloudflare Pages secret LINZ_KEY, never in the page or this repository.
// Route: /linz/aerial/{z}/{x}/{y}.png?year=2013 (defaults to the latest year)
//        /linz/aerial/{z}/{x}/{y}.png?src=topo or ?src=sat for the layers named in area.base_layers

// The area and the LINZ layer for each year come from the settings file (area.bounds, area.linz_layers).
// Tiles are only served inside the area, so the endpoint can't be used as a free tile server for all of NZ.
const MIN_Z = 8, MAX_Z = 21;

let cached = null, cachedAt = 0;
async function loadArea(env, request) {
  if (cached && Date.now() - cachedAt < 300000) return cached;
  try {
    const r = env.ASSETS ? await env.ASSETS.fetch(new URL('/config/site.json', request.url)) : null;
    const cfg = r && r.ok ? await r.json() : null;
    if (cfg && cfg.area && cfg.area.bounds) { cached = cfg.area; cachedAt = Date.now(); }
  } catch {}
  return cached;
}

function tileRange(z, AREA) {
  const n = 2 ** z;
  const x = lon => Math.floor((lon + 180) / 360 * n);
  const y = lat => Math.floor((1 - Math.asinh(Math.tan(lat * Math.PI / 180)) / Math.PI) / 2 * n);
  return { x0: x(AREA.west), x1: x(AREA.east), y0: y(AREA.north), y1: y(AREA.south) };
}

export async function onRequestGet({ params, env, request }) {
  const parts = Array.isArray(params.path) ? params.path : [];
  if (parts.length !== 3) return new Response('Not found', { status: 404 });
  const z = Number(parts[0]), x = Number(parts[1]), y = Number(String(parts[2]).replace(/\.png$/, ''));
  if (![z, x, y].every(Number.isInteger) || z < MIN_Z || z > MAX_Z) return new Response('Bad tile', { status: 400 });
  const area = await loadArea(env, request);
  if (!area) return new Response('The settings file (config/site.json) is missing its area', { status: 503 });
  const r = tileRange(z, area.bounds);
  if (x < r.x0 || x > r.x1 || y < r.y0 || y > r.y1) return new Response('Outside the mapped area', { status: 403 });
  if (!env.LINZ_KEY) return new Response('LINZ_KEY is not set in Cloudflare', { status: 503 });

  const qs = new URL(request.url).searchParams;
  const layers = area.linz_layers || {}, extra = area.base_layers || {};
  let LAYER;
  if (qs.get('src')) {
    LAYER = extra[qs.get('src')];
    if (!LAYER || String(qs.get('src')).startsWith('_')) return new Response('No such map layer', { status: 404 });
  } else {
    const years = Object.keys(layers).map(Number).sort();
    const year = Number(qs.get('year')) || years[years.length - 1];
    LAYER = layers[year];
    if (!LAYER) return new Response('No aerial photos for that year', { status: 404 });
  }
  const sub = 'abcd'[(x + y) % 4];
  const url = `https://tiles-${sub}.data-cdn.linz.govt.nz/services;key=${env.LINZ_KEY}/tiles/v4/layer=${LAYER}/EPSG:3857/${z}/${x}/${y}.png`;
  const upstream = await fetch(url, { cf: { cacheEverything: true, cacheTtl: 2592000 } });
  if (!upstream.ok) return new Response('LINZ returned ' + upstream.status, { status: 502 });
  return new Response(upstream.body, {
    headers: {
      'Content-Type': upstream.headers.get('Content-Type') || 'image/png',
      'Cache-Control': 'public, max-age=2592000',
      'Access-Control-Allow-Origin': '*',
    },
  });
}
