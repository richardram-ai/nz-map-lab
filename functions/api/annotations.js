// Shared annotations, stored in a Google Sheet through a Google Apps Script web app.
// GET  /api/annotations          -> everyone can read the annotations (GeoJSON FeatureCollection)
// POST /api/annotations          -> add or delete; needs the X-Edit-Code header to match EDIT_CODE
// Cloudflare secrets: SHEET_URL (Apps Script web app address), SHEET_TOKEN (shared with the Apps Script), EDIT_CODE.

const AREA = { west: 175.598, south: -40.364, east: 175.641, north: -40.335 };
const CATS = ['Observation', 'Planting', 'Pest or weed', 'Issue'];
const TYPES = ['Point', 'LineString', 'Polygon'];

const json = (obj, status = 200) => new Response(JSON.stringify(obj), {
  status, headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' },
});

function configured(env) { return env.SHEET_URL && env.SHEET_TOKEN && env.EDIT_CODE; }

async function callSheet(env, payload) {
  const init = payload
    ? { method: 'POST', headers: { 'Content-Type': 'text/plain' }, body: JSON.stringify({ ...payload, token: env.SHEET_TOKEN }), redirect: 'follow' }
    : { redirect: 'follow' };
  const url = payload ? env.SHEET_URL : `${env.SHEET_URL}?token=${encodeURIComponent(env.SHEET_TOKEN)}`;
  const r = await fetch(url, init);
  const text = await r.text();
  let data; try { data = JSON.parse(text); } catch { throw new Error('The Google Sheet did not answer with data. Check the Apps Script is deployed for "Anyone".'); }
  if (data.error) throw new Error('Google Sheet: ' + data.error);
  return data;
}

function inArea([x, y]) {
  return typeof x === 'number' && typeof y === 'number' && x >= AREA.west && x <= AREA.east && y >= AREA.south && y <= AREA.north;
}

function cleanFeature(f) {
  const g = f && f.geometry;
  if (!g || !TYPES.includes(g.type)) throw new Error('Only points, lines and areas can be saved.');
  const pts = g.type === 'Point' ? [g.coordinates] : g.type === 'LineString' ? g.coordinates : (g.coordinates || [])[0];
  if (!Array.isArray(pts) || pts.length < 1 || pts.length > 500) throw new Error('That shape has too many or too few points.');
  if (!pts.every(p => Array.isArray(p) && inArea(p))) throw new Error('Annotations must be inside the mapped area.');
  const round = p => [Math.round(p[0] * 1e6) / 1e6, Math.round(p[1] * 1e6) / 1e6];
  const geometry = g.type === 'Point' ? { type: 'Point', coordinates: round(g.coordinates) }
    : g.type === 'LineString' ? { type: 'LineString', coordinates: pts.map(round) }
    : { type: 'Polygon', coordinates: [pts.map(round)] };
  const p = f.properties || {};
  const str = (v, n) => String(v ?? '').trim().slice(0, n);
  const num = (v, lo, hi) => (typeof v === 'number' && isFinite(v) && v >= lo && v <= hi ? Math.round(v * 1e6) / 1e6 : null);
  // Photos must be ones uploaded through /api/photos.
  const photos = (Array.isArray(p.photos) ? p.photos : []).slice(0, 3)
    .filter(ph => ph && /^\/photos\/[0-9a-f-]{36}\.jpg$/.test(ph.url))
    .map(ph => ({ url: ph.url, caption: str(ph.caption, 120), taken: str(ph.taken, 32), lat: num(ph.lat, -90, 90), lon: num(ph.lon, -180, 180) }));
  // Details captured automatically by the phone form.
  const m = p.meta || {};
  const meta = {
    accuracy_m: num(m.accuracy_m, 0, 100000),
    position: ['gps', 'moved', 'photo', 'map'].includes(m.position) ? m.position : null,
    captured: str(m.captured, 32),
    altitude_m: num(m.altitude_m, -500, 9000),
    heading: num(m.heading, 0, 360),
    device: str(m.device, 60),
    via: ['phone', 'desktop', 'import'].includes(m.via) ? m.via : null,
  };
  return {
    type: 'Feature',
    geometry,
    properties: {
      id: crypto.randomUUID(),
      title: str(p.title, 80) || 'Untitled',
      cat: CATS.includes(p.cat) ? p.cat : 'Observation',
      note: str(p.note, 400),
      by: str(p.by, 60),
      added: new Date().toISOString(),
      photos,
      meta,
    },
  };
}

export async function onRequestGet({ env }) {
  if (!configured(env)) return json({ error: 'Shared annotations are not set up yet.' }, 503);
  try { return json(await callSheet(env)); } catch (e) { return json({ error: e.message }, 502); }
}

export async function onRequestPost({ request, env }) {
  if (!configured(env)) return json({ error: 'Shared annotations are not set up yet.' }, 503);
  if ((request.headers.get('X-Edit-Code') || '') !== env.EDIT_CODE) return json({ error: 'That editing code is not right.' }, 403);
  let body; try { body = await request.json(); } catch { return json({ error: 'The request was not valid.' }, 400); }
  try {
    if (body.action === 'add') {
      const list = Array.isArray(body.features) ? body.features : [];
      if (!list.length || list.length > 50) return json({ error: 'Send between 1 and 50 annotations at a time.' }, 400);
      return json(await callSheet(env, { action: 'add', features: list.map(cleanFeature) }));
    }
    if (body.action === 'delete') {
      const id = String(body.id || '');
      if (!/^[A-Za-z0-9-]{4,64}$/.test(id)) return json({ error: 'That annotation id is not valid.' }, 400);
      return json(await callSheet(env, { action: 'delete', id }));
    }
    return json({ error: 'Unknown action.' }, 400);
  } catch (e) {
    return json({ error: e.message }, e.message.startsWith('Google Sheet') ? 502 : 400);
  }
}
