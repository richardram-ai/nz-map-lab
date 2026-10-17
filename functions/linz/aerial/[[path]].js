// Serves LINZ aerial photo tiles for the test area, adding the LINZ Data Service key on the server.
// The key lives in the Cloudflare Pages secret LINZ_KEY, never in the page or this repository.
// Route: /linz/aerial/{z}/{x}/{y}.png

const LAYER = 119050; // Palmerston North 0.1m Urban Aerial Photos (2024)
// Only serve tiles around the test square, so the endpoint can't be used as a free tile server for all of NZ.
const AREA = { west: 175.598, south: -40.364, east: 175.641, north: -40.335 };
const MIN_Z = 12, MAX_Z = 21;

function tileRange(z) {
  const n = 2 ** z;
  const x = lon => Math.floor((lon + 180) / 360 * n);
  const y = lat => Math.floor((1 - Math.asinh(Math.tan(lat * Math.PI / 180)) / Math.PI) / 2 * n);
  return { x0: x(AREA.west), x1: x(AREA.east), y0: y(AREA.north), y1: y(AREA.south) };
}

export async function onRequestGet({ params, env }) {
  const parts = Array.isArray(params.path) ? params.path : [];
  if (parts.length !== 3) return new Response('Not found', { status: 404 });
  const z = Number(parts[0]), x = Number(parts[1]), y = Number(String(parts[2]).replace(/\.png$/, ''));
  if (![z, x, y].every(Number.isInteger) || z < MIN_Z || z > MAX_Z) return new Response('Bad tile', { status: 400 });
  const r = tileRange(z);
  if (x < r.x0 || x > r.x1 || y < r.y0 || y > r.y1) return new Response('Outside the mapped area', { status: 403 });
  if (!env.LINZ_KEY) return new Response('LINZ_KEY is not set in Cloudflare. Names this deploy can see: ' + Object.keys(env || {}).map(k => JSON.stringify(k)).join(', '), { status: 503 });

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
