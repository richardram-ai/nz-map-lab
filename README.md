# NZ Map Lab

A test of what free public New Zealand data can be layered on a map, and how an organisation can add its own notes on top. The test area is a 1 km square centred on 16 Sydney Street, Palmerston North.

Live site: https://nz-map-lab.pages.dev

## What's here

| Path | What it is |
|---|---|
| `index.html` | The map. One self-contained page: data, aerial photo and elevation image are built in. Only MapLibre GL JS loads from cdnjs. |
| `data/` | Each layer as GeoJSON, clipped to the square, for use in QGIS or other tools. |
| `imagery/` | Aerial photos for each year (2013, 2015, 2017, 2018, 2022; 2024 is built into the page) and the 2018 LiDAR elevation shading. |
| `scripts/` | The Python scripts that fetched, clipped and derived the data, plus the page template. Paths in them point to the original working folder. |

## Layers and sources

| Layer | Publisher | Licence |
|---|---|---|
| Buildings, roads, paths, parks, mapped trees | [OpenStreetMap contributors](https://www.openstreetmap.org/copyright) | ODbL 1.0 |
| Species sightings | [iNaturalist NZ](https://inaturalist.nz) observers | Per record, mostly CC BY-NC |
| Notable trees, District Plan zones, parcels, heritage, playgrounds, cycle network, stormwater pipes and catchments | [Palmerston North City Council](https://www.pncc.govt.nz) | CC BY 4.0 |
| 200-year flood model | [Horizons Regional Council](https://www.horizons.govt.nz) | CC BY 4.0 |
| Liquefaction, groundwater bore, water management areas, S-map soils | [Horizons Regional Council](https://www.horizons.govt.nz) | Not stated in the service |
| Land cover (LCDB) | [Manaaki Whenua – Landcare Research](https://www.landcareresearch.co.nz), served by [Eagle Technology](https://www.eagle.co.nz) | CC BY 4.0 |
| Aerial photos 2012–13, 2015, 2017, 2018, 2022 (12.5 cm) and 2024 (10 cm), Palmerston North urban | [Toitū Te Whenua LINZ](https://www.linz.govt.nz) | CC BY 4.0 |
| LiDAR 2018 (DEM and DSM, 1 m), contours and tree canopy derived from it | [Toitū Te Whenua LINZ](https://www.linz.govt.nz), via the open elevation store on AWS | CC BY 4.0 |

Data downloaded 17 October 2026. The groundwater bore owner's name was removed from the source data.

## Keys

No API keys are stored in this repository. On the hosted site, the "LINZ full-detail photo" option loads tiles through `functions/linz/aerial/[[path]].js`, a Cloudflare Pages Function that adds the LINZ Data Service key from the Cloudflare secret `LINZ_KEY`. It only serves tiles around the test square. When the page is opened as a file from a computer, it asks for a key instead and keeps it in that browser only.

## Annotations

On the hosted site, annotations are shared through a Google Sheet:

- `functions/api/annotations.js` (Cloudflare Pages Function) lets anyone read them and lets people with the editing code add or delete them. It checks every shape is inside the mapped area, and accepts photos and phone details (GPS accuracy, time captured, device).
- `google-sheet/apps-script.gs` runs on the Sheet and only answers requests that carry the private token. Deleted annotations are marked in a `deleted` column rather than removed.
- Cloudflare secrets: `SHEET_URL` (the Apps Script web app address), `SHEET_TOKEN` (the same token as in the Apps Script) and `EDIT_CODE`.

When the Sheet isn't set up, or the page is opened as a file, annotations are saved in the viewer's browser instead.

## Phone form and photos

- `add/` is the phone form (`/add/`): GPS position with accuracy, drag-to-adjust pin, category buttons, up to 3 photos, and a queue that holds records on the phone until there is signal. It can be added to the home screen.
- **Walk a boundary** (October 2026): instead of a pin, record an area by walking round its edge. The phone keeps a point every few metres when the GPS fix is within 25 m, *Corner here* marks sharp corners, *Pause* stops recording, and *Finish the area* simplifies the line (corners kept) and closes it. The walk is kept on the phone until saved, so it survives a reload or no signal, and the screen is kept awake while walking where the phone allows. Saved as an area with the walk's point count, perimeter and area in the record's details.
- **Save the map for offline use** saves the aerial tiles of the square (to zoom 18, set in `area.offline.max_zoom`) and the photo helper; saved tiles are never trimmed.
- Ported from the Ruahine branch: date fields and `sets_category` in `/api/annotations`; tasks marked `desktop_only` are hidden on the phone; the phone map uses the latest aerial year in the settings; the tile function also serves `?src=` layers from `area.base_layers` and `&side=west`; embeds take the latest year from the settings; Apps Script `setup()` makes the token and backups prune only their own sheet's copies.
- Photos are shrunk to 1,600 px on the phone. Their time taken and GPS position are read first; everything else embedded in the file is dropped.
- `functions/api/photos.js` stores each photo in the Cloudflare R2 bucket bound as `PHOTOS`, and copies it to the "NZ Map Lab photos" Google Drive folder through the Apps Script (listed on the Sheet's Photos tab). `functions/photos/[name].js` serves photos to the map.
