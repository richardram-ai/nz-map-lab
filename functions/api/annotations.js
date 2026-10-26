// Shared annotations, stored in a Google Sheet through a Google Apps Script web app.
// GET  /api/annotations          -> everyone can read the annotations (GeoJSON FeatureCollection)
// POST /api/annotations          -> add or delete; needs the X-Edit-Code header to match EDIT_CODE
// Cloudflare secrets: SHEET_URL (Apps Script web app address), SHEET_TOKEN (shared with the Apps Script), EDIT_CODE.

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

// The mapped area comes from area.bounds in the settings file.
function inArea([x, y], a) {
  return typeof x === 'number' && typeof y === 'number' && x >= a.west && x <= a.east && y >= a.south && y <= a.north;
}

// The organisation's settings (tasks, pick lists). Loaded from the site's own /config/site.json.
async function loadConfig(env, request) {
  try {
    const r = env.ASSETS ? await env.ASSETS.fetch(new URL('/config/site.json', request.url)) : null;
    return r && r.ok ? await r.json() : null;
  } catch { return null; }
}

// Check a task record's fields against the settings, and work out whether it needs an ID check.
function cleanTask(p, cfg, hasPhotos, ai) {
  const task = (cfg && cfg.tasks || []).find(t => t.id === p.task);
  if (!task) throw new Error('That task is not set up for this map.');
  const given = p.fields && typeof p.fields === 'object' ? p.fields : {};
  const fields = {}; let needsId = false;
  for (const fd of task.fields) {
    const v = given[fd.id];
    const empty = v === undefined || v === null || v === '' || (fd.type === 'list' && !(v && v.id));
    if (empty) { if (fd.required) throw new Error(`“${fd.label}” is needed.`); continue; }
    if (fd.type === 'list') {
      const list = (cfg.lists || {})[fd.list] || [];
      const other = v.id === 'other';
      const item = list.find(i => i.id === v.id);
      if (!item && !other) throw new Error(`“${fd.label}”: choose from the list.`);
      const conf = (cfg.identification && cfg.identification.confidence || []).map(c => c.id).includes(v.confidence) ? v.confidence : null;
      const sci = String(v.sci || '').trim().slice(0, 80);
      // A species not on the list counts as identified only when this field allows it, the photo helper suggested
      // exactly that species at or above the field's threshold, and the person picked it and is sure.
      const hit = ai && ai.field === fd.id && ai.chosen === sci && sci && (ai.top || []).find(t => t.sci === sci);
      const fromPhoto = other && v.photo === true && fd.unlisted_from_photo && hit && hit.p >= fd.unlisted_from_photo && conf === 'sure';
      fields[fd.id] = other
        ? { id: 'other', label: String(v.other || 'Not sure').trim().slice(0, 80) || 'Not sure', sci, confidence: conf || 'unsure', ...(fromPhoto ? { from_photo: true, not_on_list: true } : {}) }
        : { id: item.id, label: item.common, sci: item.sci || '', confidence: fd.confidence === false ? null : conf };
      if (fd.confidence !== false && ((other && !fromPhoto) || conf === 'unsure')) needsId = true;
    } else if (fd.type === 'choice') {
      if (!fd.options.includes(v)) throw new Error(`“${fd.label}”: choose one of the options.`);
      fields[fd.id] = v;
    } else if (fd.type === 'number') {
      const n = Number(v);
      if (!Number.isFinite(n) || n < (fd.min ?? -1e9) || n > (fd.max ?? 1e9)) throw new Error(`“${fd.label}” is out of range.`);
      fields[fd.id] = Math.round(n * 100) / 100;
    } else if (fd.type === 'yesno') {
      fields[fd.id] = v === true || v === 'yes';
    } else if (fd.type === 'date') {
      const d = String(v).trim();
      if (!/^\d{4}-\d{2}-\d{2}$/.test(d) || isNaN(Date.parse(d))) throw new Error(`“${fd.label}”: give a date.`);
      fields[fd.id] = d;
    } else {
      fields[fd.id] = String(v).trim().slice(0, fd.max || 200);
    }
  }
  if (needsId && cfg.identification && cfg.identification.photo_required_when_unsure && !hasPhotos)
    throw new Error('Add a photo so someone can check the identification.');
  return { task, fields, needsId };
}

function cleanFeature(f, cfg) {
  const g = f && f.geometry;
  if (!g || !TYPES.includes(g.type)) throw new Error('Only points, lines and areas can be saved.');
  const pts = g.type === 'Point' ? [g.coordinates] : g.type === 'LineString' ? g.coordinates : (g.coordinates || [])[0];
  if (!Array.isArray(pts) || pts.length < 1 || pts.length > 500) throw new Error('That shape has too many or too few points.');
  if (!pts.every(p => Array.isArray(p) && inArea(p, cfg.area.bounds))) throw new Error('Annotations must be inside the mapped area.');
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
  let ai = null;
  // Suggestions from the on-phone species classifier, kept so a reviewer can see what it proposed.
  if (m.ai && typeof m.ai === 'object' && Array.isArray(m.ai.top)) {
    ai = {
      model: str(m.ai.model, 60), field: str(m.ai.field, 40), backend: str(m.ai.backend, 10), ms: num(m.ai.ms, 0, 600000),
      top: m.ai.top.slice(0, 5).map(t => ({ sci: str(t && t.sci, 80), common: str(t && t.common, 80), p: num(t && t.p, 0, 1) })),
      chosen: m.ai.chosen == null ? null : str(m.ai.chosen, 80),
    };
  }
  let taskInfo = null;
  if (p.task) taskInfo = cleanTask(p, cfg, photos.length > 0, ai);
  const meta = {
    accuracy_m: num(m.accuracy_m, 0, 100000),
    position: ['gps', 'moved', 'photo', 'map'].includes(m.position) ? m.position : null,
    captured: str(m.captured, 32),
    altitude_m: num(m.altitude_m, -500, 9000),
    heading: num(m.heading, 0, 360),
    device: str(m.device, 60),
    via: ['phone', 'desktop', 'import'].includes(m.via) ? m.via : null,
  };
  if (ai) meta.ai = ai;
  if (taskInfo) {
    meta.task = taskInfo.task.id;
    meta.fields = taskInfo.fields;
    meta.review = { status: taskInfo.needsId ? 'needs-id' : 'unreviewed' };
  }
  const cats = (cfg && cfg.categories || []).map(c => c.id);
  const catOk = c => CATS.includes(c) || cats.includes(c);
  // A choice field can set the category (sets_category), e.g. a wilding area's status picks Cleared or Regrowth.
  let taskCat = taskInfo && taskInfo.task.category;
  if (taskInfo) for (const fd of taskInfo.task.fields) {
    const v = taskInfo.fields[fd.id];
    if (fd.sets_category && typeof v === 'string' && fd.sets_category[v]) taskCat = fd.sets_category[v];
  }
  const cat = taskCat && catOk(taskCat) ? taskCat : (catOk(p.cat) ? p.cat : 'Observation');
  return {
    type: 'Feature',
    geometry,
    properties: {
      id: crypto.randomUUID(),
      title: str(p.title, 80) || 'Untitled',
      cat,
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

// ---- Review: confirm, correct or set aside a record's identification (used by /review/).
function titleFor(task, fields, title) {
  return (task.title || '{title}').replace(/\{(\w+)\}/g, (m, id) => {
    const fd = task.fields.find(f => f.id === id); const v = fields[id];
    if (!fd || v === undefined || v === null || v === '') return id === 'title' ? title || '' : '';
    if (fd.type === 'list') { if (v.id === 'other') return v.label + (v.confidence === 'sure' ? '' : ' (unconfirmed)'); return fd.title_uses === 'id' ? v.id : v.label; }
    if (fd.type === 'yesno') return v ? 'Yes' : 'No';
    return String(v);
  }).replace(/\s+/g, ' ').replace(/[:×(]\s*\)?\s*$/, '').trim().slice(0, 80) || title || 'Untitled';
}
async function review(env, cfg, body) {
  const id = String(body.id || '');
  if (!/^[A-Za-z0-9-]{4,64}$/.test(id)) throw new Error('That record id is not valid.');
  const all = await callSheet(env);
  const f = (all.features || []).find(x => x.properties.id === id);
  if (!f) throw new Error('That record was not found.');
  const meta = { ...(f.properties.meta || {}) };
  const task = (cfg.tasks || []).find(t => t.id === meta.task);
  if (!task) throw new Error('Only records made with a task can be reviewed here.');
  const fields = { ...(meta.fields || {}) };
  const decision = String(body.decision || '');
  const by = String(body.by || '').trim().slice(0, 60);
  if (!by) throw new Error('Add your name so others know who reviewed it.');
  const before = {};
  const listFields = task.fields.filter(fd => fd.type === 'list' && fd.confidence !== false);
  if (decision === 'confirm') {
    listFields.forEach(fd => { if (fields[fd.id]) fields[fd.id] = { ...fields[fd.id], confidence: 'sure' }; });
  } else if (decision === 'correct') {
    const given = body.fields && typeof body.fields === 'object' ? body.fields : {};
    for (const fd of listFields) {
      const v = given[fd.id]; if (!v) continue;
      const list = (cfg.lists || {})[fd.list] || [];
      before[fd.id] = fields[fd.id] ? { label: fields[fd.id].label, sci: fields[fd.id].sci || '' } : null;
      if (v.id === 'other') {
        const label = String(v.label || '').trim().slice(0, 80), sci = String(v.sci || '').trim().slice(0, 80);
        if (!label && !sci) throw new Error(`“${fd.label}”: give a name.`);
        fields[fd.id] = { id: 'other', label: label || sci, sci, confidence: 'sure', not_on_list: true, by_reviewer: true };
      } else {
        const item = list.find(i => i.id === v.id);
        if (!item) throw new Error(`“${fd.label}”: choose from the list.`);
        fields[fd.id] = { id: item.id, label: item.common, sci: item.sci || '', confidence: 'sure' };
      }
    }
    if (!Object.keys(before).length) throw new Error('Choose the correct species first.');
  } else if (decision !== 'cannot' && decision !== 'reopen') {
    throw new Error('Unknown review decision.');
  }
  const status = decision === 'cannot' ? 'cannot-id' : decision === 'reopen' ? 'needs-id' : 'confirmed';
  meta.fields = fields;
  meta.review = { status, by, at: new Date().toISOString(), ...(decision === 'correct' ? { changed: true, before } : {}),
    ...(body.note ? { note: String(body.note).trim().slice(0, 200) } : {}),
    history: [...((meta.review && meta.review.history) || []), ...(meta.review && meta.review.at ? [{ status: meta.review.status, by: meta.review.by, at: meta.review.at }] : [])].slice(-10) };
  const title = decision === 'cannot' || decision === 'reopen' ? f.properties.title : titleFor(task, fields, f.properties.title);
  return callSheet(env, { action: 'update', id, title, meta });
}

export async function onRequestPost({ request, env }) {
  if (!configured(env)) return json({ error: 'Shared annotations are not set up yet.' }, 503);
  if ((request.headers.get('X-Edit-Code') || '') !== env.EDIT_CODE) return json({ error: 'That editing code is not right.' }, 403);
  let body; try { body = await request.json(); } catch { return json({ error: 'The request was not valid.' }, 400); }
  try {
    if (body.action === 'add') {
      const list = Array.isArray(body.features) ? body.features : [];
      if (!list.length || list.length > 50) return json({ error: 'Send between 1 and 50 annotations at a time.' }, 400);
      const cfg = await loadConfig(env, request);
      if (!cfg || !cfg.area || !cfg.area.bounds) return json({ error: 'The settings file (config/site.json) is missing its area.' }, 503);
      return json(await callSheet(env, { action: 'add', features: list.map(f => cleanFeature(f, cfg)) }));
    }
    if (body.action === 'review') {
      const cfg = await loadConfig(env, request);
      if (!cfg) return json({ error: 'The settings file could not be read.' }, 503);
      return json(await review(env, cfg, body));
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
