/**
 * NZ Map Lab – shared annotations store.
 * Paste into the Google Sheet's Extensions > Apps Script, run setup (it makes the token, or set TOKEN yourself), then Deploy > New deployment > Web app
 * (Execute as: Me, Who has access: Anyone). Only requests carrying TOKEN are answered,
 * and only the Cloudflare function knows TOKEN.
 * Deleting an annotation marks the row "yes" in the deleted column rather than removing it, so nothing is lost.
 * The review screen updates a record's title and details columns in place (action 'update').
 * Deleted records are moved to the Deleted tab so the Annotations tab only holds live records.
 * Backups: run installBackupTrigger() once for a weekly dated copy of the spreadsheet in the "NZ Map Lab backups" folder.
 * Photos: the Cloudflare function sends a copy of each photo here; it is saved to the "NZ Map Lab photos"
 * Drive folder and listed on the Photos tab. The map itself shows photos from Cloudflare R2.
 */
const TOKEN = 'PASTE_TOKEN_HERE';   // leave as is to use the token setup() creates (Project Settings > Script properties > TOKEN)
function token_() {
  if (TOKEN && TOKEN !== 'PASTE_TOKEN_HERE') return TOKEN;
  return PropertiesService.getScriptProperties().getProperty('TOKEN') || '';
}
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

/** Deleted records are moved to the "Deleted" tab (with the time they were moved), so the main tab holds
 *  only live records. Nothing is lost: to restore one, move its row back to the Annotations tab and clear "deleted". */
const DELETED_SHEET = 'Deleted';
function deletedSheet_() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sh = ss.getSheetByName(DELETED_SHEET);
  if (!sh) {
    sh = ss.insertSheet(DELETED_SHEET);
    sh.appendRow(HEADERS.concat(['moved_to_deleted']));
    sh.setFrozenRows(1);
    sh.getRange(1, 1, 1, HEADERS.length + 1).setFontWeight('bold');
  }
  return sh;
}
function moveDeleted_(sh) {
  const last = sh.getLastRow(); if (last < 2) return 0;
  const rows = sh.getRange(2, 1, last - 1, HEADERS.length).getValues();
  const del = deletedSheet_(), now = new Date(); let moved = 0;
  for (let r = rows.length - 1; r >= 0; r--) {
    if (String(rows[r][8]).toLowerCase() !== 'yes') continue;
    del.appendRow(rows[r].concat([now]));
    sh.deleteRow(r + 2); moved++;
  }
  return moved;
}
/** Run once from the editor to move rows already marked deleted. */
function tidyDeleted() { const n = moveDeleted_(sheet_()); Logger.log(n + ' deleted rows moved to the Deleted tab'); }

/** Weekly backup: a dated copy of this spreadsheet in the "NZ Map Lab backups" Drive folder, keeping the last 12.
 *  Run installBackupTrigger() once from the editor to schedule it (Sundays, 2–3 am). Older copies go to the Drive bin. */
const BACKUP_FOLDER = 'NZ Map Lab backups', BACKUPS_KEPT = 12;
function weeklyBackup() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const found = DriveApp.getFoldersByName(BACKUP_FOLDER);
  const folder = found.hasNext() ? found.next() : DriveApp.createFolder(BACKUP_FOLDER);
  const stamp = Utilities.formatDate(new Date(), ss.getSpreadsheetTimeZone(), 'yyyy-MM-dd');
  DriveApp.getFileById(ss.getId()).makeCopy(ss.getName() + ' backup ' + stamp, folder);
  // Only this spreadsheet's own copies count towards the 12, so two groups can share the folder safely.
  const mine = ss.getName() + ' backup ';
  const files = []; const it = folder.getFiles(); while (it.hasNext()) { const f = it.next(); if (f.getName().indexOf(mine) === 0) files.push(f); }
  files.sort((a, b) => b.getDateCreated() - a.getDateCreated()).slice(BACKUPS_KEPT).forEach(f => f.setTrashed(true));
}
function installBackupTrigger() {
  ScriptApp.getProjectTriggers().filter(t => t.getHandlerFunction() === 'weeklyBackup').forEach(t => ScriptApp.deleteTrigger(t));
  ScriptApp.newTrigger('weeklyBackup').timeBased().onWeekDay(ScriptApp.WeekDay.SUNDAY).atHour(2).create();
  weeklyBackup();
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
  if (!e || !e.parameter || e.parameter.token !== token_() || !token_()) return out_({ error: 'Not allowed' });
  return out_(features_());
}

function doPost(e) {
  let body;
  try { body = JSON.parse(e.postData.contents); } catch (err) { return out_({ error: 'Bad request' }); }
  if (body.token !== token_() || !token_()) return out_({ error: 'Not allowed' });
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
      moveDeleted_(sh);
    } else if (body.action === 'update') {
      // Used by the review screen: replaces a record's title and details (task fields, review status).
      const ids = sh.getRange(2, 1, Math.max(sh.getLastRow() - 1, 1), 1).getValues().map(r => String(r[0]));
      const i = ids.indexOf(String(body.id));
      if (i < 0) return out_({ error: 'Annotation not found' });
      if (typeof body.title === 'string') sh.getRange(i + 2, 2).setValue(body.title);
      if (body.meta && typeof body.meta === 'object') sh.getRange(i + 2, 11).setValue(JSON.stringify(body.meta));
    } else {
      return out_({ error: 'Unknown action' });
    }
  } finally {
    lock.releaseLock();
  }
  return out_(features_());
}

/** Run once from the editor: creates or upgrades the tabs, creates the Drive photo folder, and approves access. */
function setup() {
  sheet_(); photoSheet_(); photoFolder_();
  // A long random token, made here so it never has to be typed or pasted into chat. Copy it from
  // Project Settings > Script properties into the Cloudflare secret SHEET_TOKEN.
  const props = PropertiesService.getScriptProperties();
  if (TOKEN === 'PASTE_TOKEN_HERE' && !props.getProperty('TOKEN'))
    props.setProperty('TOKEN', Utilities.getUuid().replace(/-/g, '') + Utilities.getUuid().replace(/-/g, ''));
  Logger.log('Set up. The token is in Project Settings > Script properties > TOKEN.');
}
