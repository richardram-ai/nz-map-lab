/**
 * NZ Map Lab – shared annotations store.
 * Paste into the Google Sheet's Extensions > Apps Script, set TOKEN, then Deploy > New deployment > Web app
 * (Execute as: Me, Who has access: Anyone). Only requests carrying TOKEN are answered,
 * and only the Cloudflare function knows TOKEN.
 * Deleting an annotation marks the row "yes" in the deleted column rather than removing it, so nothing is lost.
 * Photos: the Cloudflare function sends a copy of each photo here; it is saved to the "NZ Map Lab photos"
 * Drive folder and listed on the Photos tab. The map itself shows photos from Cloudflare R2.
 */
const TOKEN = 'PASTE_TOKEN_HERE';
const SHEET_NAME = 'Annotations';
const HEADERS = ['id', 'title', 'category', 'note', 'added_by', 'added', 'geometry_type', 'geometry', 'deleted', 'photos', 'details'];
const PHOTO_SHEET = 'Photos';
const PHOTO_HEADERS = ['photo_id', 'drive_link', 'taken', 'lat', 'lon', 'added_by', 'uploaded'];
const PHOTO_FOLDER = 'NZ Map Lab photos';

function sheet_() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sh = ss.getSheetByName(SHEET_NAME);
  if (!sh) {
    sh = ss.insertSheet(SHEET_NAME);
    sh.appendRow(HEADERS);
    sh.setFrozenRows(1);
    sh.getRange(1, 1, 1, HEADERS.length).setFontWeight('bold');
  } else if (sh.getLastColumn() < HEADERS.length) {
    // Upgrade an existing tab: add the new column headings.
    sh.getRange(1, 1, 1, HEADERS.length).setValues([HEADERS]).setFontWeight('bold');
  }
  return sh;
}

function photoSheet_() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sh = ss.getSheetByName(PHOTO_SHEET);
  if (!sh) {
    sh = ss.insertSheet(PHOTO_SHEET);
    sh.appendRow(PHOTO_HEADERS);
    sh.setFrozenRows(1);
    sh.getRange(1, 1, 1, PHOTO_HEADERS.length).setFontWeight('bold');
  }
  return sh;
}

/** The Drive folder that holds copies of every photo. Created on first use, next to nothing else in My Drive. */
function photoFolder_() {
  const props = PropertiesService.getScriptProperties();
  const id = props.getProperty('PHOTO_FOLDER_ID');
  if (id) { try { return DriveApp.getFolderById(id); } catch (e) {} }
  const found = DriveApp.getFoldersByName(PHOTO_FOLDER);
  const folder = found.hasNext() ? found.next() : DriveApp.createFolder(PHOTO_FOLDER);
  props.setProperty('PHOTO_FOLDER_ID', folder.getId());
  return folder;
}

function features_() {
  const rows = sheet_().getDataRange().getValues().slice(1);
  const parse = (v, d) => { try { return v ? JSON.parse(v) : d; } catch (e) { return d; } };
  const features = [];
  rows.forEach(r => {
    if (!r[0] || String(r[8]).toLowerCase() === 'yes') return;
    let geometry;
    try { geometry = JSON.parse(r[7]); } catch (e) { return; }
    features.push({
      type: 'Feature',
      geometry: geometry,
      properties: { id: String(r[0]), title: String(r[1]), cat: String(r[2]), note: String(r[3]), by: String(r[4]),
        added: r[5] instanceof Date ? r[5].toISOString() : String(r[5]),
        photos: parse(r[9], []), meta: parse(r[10], {}) },
    });
  });
  return { type: 'FeatureCollection', features: features };
}

function out_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}

function doGet(e) {
  if (!e || !e.parameter || e.parameter.token !== TOKEN) return out_({ error: 'Not allowed' });
  return out_(features_());
}

function doPost(e) {
  let body;
  try { body = JSON.parse(e.postData.contents); } catch (err) { return out_({ error: 'Bad request' }); }
  if (body.token !== TOKEN) return out_({ error: 'Not allowed' });
  const lock = LockService.getScriptLock();
  lock.waitLock(10000);
  try {
    const sh = sheet_();
    if (body.action === 'add') {
      (body.features || []).forEach(f => {
        const p = f.properties || {};
        sh.appendRow([p.id, p.title, p.cat, p.note, p.by, p.added, f.geometry.type, JSON.stringify(f.geometry), '',
          JSON.stringify(p.photos || []), JSON.stringify(p.meta || {})]);
      });
    } else if (body.action === 'photo') {
      const blob = Utilities.newBlob(Utilities.base64Decode(body.data), body.mime || 'image/jpeg', body.name || (body.id + '.jpg'));
      const file = photoFolder_().createFile(blob);
      file.setDescription('NZ Map Lab photo ' + body.id + (body.by ? ' by ' + body.by : ''));
      photoSheet_().appendRow([body.id, file.getUrl(), body.taken || '', body.lat === '' ? '' : body.lat, body.lon === '' ? '' : body.lon, body.by || '', new Date()]);
      return out_({ ok: true, fileId: file.getId() });
    } else if (body.action === 'delete') {
      const ids = sh.getRange(2, 1, Math.max(sh.getLastRow() - 1, 1), 1).getValues().map(r => String(r[0]));
      const i = ids.indexOf(String(body.id));
      if (i < 0) return out_({ error: 'Annotation not found' });
      sh.getRange(i + 2, 9).setValue('yes');
    } else {
      return out_({ error: 'Unknown action' });
    }
  } finally {
    lock.releaseLock();
  }
  return out_(features_());
}

/** Run once from the editor: creates or upgrades the tabs, creates the Drive photo folder, and approves access. */
function setup() { sheet_(); photoSheet_(); photoFolder_(); }
