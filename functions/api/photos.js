// Photo upload for the phone form and desktop map.
// POST /api/photos  (body: the JPEG, header X-Edit-Code) -> { id, url }
// Stores the photo in the R2 bucket bound as PHOTOS, then copies it to the organisation's
// Google Drive folder through the Apps Script (in the background, so the phone doesn't wait).

const MAX_BYTES = 4 * 1024 * 1024; // photos are shrunk on the phone to well under this

const json = (obj, status = 200) => new Response(JSON.stringify(obj), {
  status, headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' },
});

function toBase64(buf) {
  const bytes = new Uint8Array(buf); let s = '';
  for (let i = 0; i < bytes.length; i += 0x8000) s += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
  return btoa(s);
}

async function copyToDrive(env, id, buf, meta) {
  if (!env.SHEET_URL || !env.SHEET_TOKEN) return;
  try {
    await fetch(env.SHEET_URL, {
      method: 'POST', redirect: 'follow', headers: { 'Content-Type': 'text/plain' },
      body: JSON.stringify({ token: env.SHEET_TOKEN, action: 'photo', id, name: id + '.jpg', mime: 'image/jpeg', data: toBase64(buf), ...meta }),
    });
  } catch (e) { /* the R2 copy is the one the map uses; a missed Drive copy is not fatal */ }
}

export async function onRequestPost({ request, env, waitUntil }) {
  if (!env.PHOTOS) return json({ error: 'Photo storage is not set up yet.' }, 503);
  if (!env.EDIT_CODE || (request.headers.get('X-Edit-Code') || '') !== env.EDIT_CODE) return json({ error: 'That editing code is not right.' }, 403);
  const type = (request.headers.get('Content-Type') || '').split(';')[0];
  if (type !== 'image/jpeg') return json({ error: 'Photos must be sent as JPEG.' }, 415);
  const buf = await request.arrayBuffer();
  if (buf.byteLength < 1000 || buf.byteLength > MAX_BYTES) return json({ error: 'That photo is too small or too large.' }, 413);
  const head = new Uint8Array(buf, 0, 3);
  if (head[0] !== 0xFF || head[1] !== 0xD8 || head[2] !== 0xFF) return json({ error: 'That file is not a JPEG photo.' }, 415);

  const id = crypto.randomUUID();
  const num = v => (v === null || v === '' || isNaN(Number(v)) ? '' : Number(v));
  const meta = {
    taken: String(request.headers.get('X-Photo-Taken') || '').slice(0, 32),
    lat: num(request.headers.get('X-Photo-Lat')),
    lon: num(request.headers.get('X-Photo-Lon')),
    by: (() => { try { return decodeURIComponent(request.headers.get('X-By') || '').slice(0, 60); } catch { return ''; } })(),
  };
  await env.PHOTOS.put(id + '.jpg', buf, {
    httpMetadata: { contentType: 'image/jpeg' },
    customMetadata: { taken: meta.taken, lat: String(meta.lat), lon: String(meta.lon), by: meta.by, uploaded: new Date().toISOString() },
  });
  const drive = copyToDrive(env, id, buf, meta);
  if (typeof waitUntil === 'function') waitUntil(drive); else await drive;
  return json({ id, url: '/photos/' + id + '.jpg' });
}
