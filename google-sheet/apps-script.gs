/**
 * NZ Map Lab – shared annotations store.
 * Paste into the Google Sheet's Extensions > Apps Script, set TOKEN, then Deploy > New deployment > Web app
 * (Execute as: Me, Who has access: Anyone). Only requests carrying TOKEN are answered,
 * and only the Cloudflare function knows TOKEN.
 * Deleting an annotation marks the row "yes" in the deleted column rather than removing it, so nothing is lost.
 */
const TOKEN = 'PASTE_TOKEN_HERE';
const SHEET_NAME = 'Annotations';
const HEADERS = ['id', 'title', 'category', 'note', 'added_by', 'added', 'geometry_type', 'geometry', 'deleted'];

function sheet_() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sh = ss.getSheetByName(SHEET_NAME);
  if (!sh) {
    sh = ss.insertSheet(SHEET_NAME);
    sh.appendRow(HEADERS);
    sh.setFrozenRows(1);
    sh.getRange(1, 1, 1, HEADERS.length).setFontWeight('bold');
  }
  return sh;
}

function features_() {
  const rows = sheet_().getDataRange().getValues().slice(1);
  const features = [];
  rows.forEach(r => {
    if (!r[0] || String(r[8]).toLowerCase() === 'yes') return;
    let geometry;
    try { geometry = JSON.parse(r[7]); } catch (e) { return; }
    features.push({
      type: 'Feature',
      geometry: geometry,
      properties: { id: String(r[0]), title: String(r[1]), cat: String(r[2]), note: String(r[3]), by: String(r[4]),
        added: r[5] instanceof Date ? r[5].toISOString() : String(r[5]) },
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
        sh.appendRow([p.id, p.title, p.cat, p.note, p.by, p.added, f.geometry.type, JSON.stringify(f.geometry), '']);
      });
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

/** Run once from the editor to create the Annotations tab and approve access. */
function setup() { sheet_(); }
