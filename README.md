# NZ Map Lab — Ruahine branch

**This branch is the first test group's map: Ruahine Forest Park, with a detailed block at the end of Kashmir Road, Ashley Clinton, for wilding pine work.** Cloudflare Pages publishes it at https://ruahine.nz-map-lab.pages.dev. The main branch keeps the Palmerston North test square.

What differs from main:

| | |
|---|---|
| `config/site.json` | Park bounds, `area.focus` (the Kashmir Road block), `area.boundary`, Hawke's Bay aerial years, `area.base_layers` (Topo50, 10 m satellite), tasks for wilding pines, starter plant and conifer lists. |
| `index.html` | Built by `scripts/ruahine_page.py` from the shared `scripts/template.html` (copy in `scripts/template-ruahine.html`). Aerial years load as LINZ tiles through the site; 1980, 1995–96 and 2006 are images of the block. Topo and satellite bases; walking-access layers; a wilding-area form and totals. |
| `scripts/ruahine_fetch.py` | DOC park, tracks, huts, campsites, roads; Herenga ā Nuku tracks and public access land; iNaturalist sightings (block) and conifers (park). |
| `scripts/ruahine_rasters.py` | Older aerials cut to the block, and LiDAR canopy, contours and height shading (2023–24 Hawke's Bay LiDAR). |
| `functions/linz/aerial` | Also serves `?src=topo` and `?src=sat` (layers named in `area.base_layers`), from zoom 8. |
| `functions/api/annotations.js` | Date fields, and a choice field can set the record's category (`sets_category`). Worth merging to main. |
| `story/` | A scrolling story page (Mapbox GL JS, after the mapbox/storytelling template): park, walking access, Kashmir Road, aerials 1980–2025, and the group's drawn wilding areas live from the records. Token from the Cloudflare secret `MAPBOX_TOKEN` via `functions/api/mapbox-token.js` (a URL-restricted public token). |
| `add/` | Hides desktop-only tasks, uses the latest aerial year, and adds "Save the map for offline use" (aerial tiles for the block to zoom 17, plus the photo helper). Worth merging to main. |

Rebuild: `python3 scripts/ruahine_fetch.py WORK/layers && python3 scripts/ruahine_rasters.py WORK && python3 scripts/ruahine_page.py WORK`.

Data downloaded 26 October 2026: [Department of Conservation](https://www.doc.govt.nz) (CC BY 4.0); [Herenga ā Nuku Aotearoa](https://www.herengaanuku.govt.nz) (CC BY 4.0 stated on their site, not in the services); [iNaturalist NZ](https://inaturalist.nz) observers (per record); [Toitū Te Whenua LINZ](https://www.linz.govt.nz) aerials, Topo50, satellite and LiDAR (CC BY 4.0).

---

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
- Photos are shrunk to 1,600 px on the phone. Their time taken and GPS position are read first; everything else embedded in the file is dropped.
- `functions/api/photos.js` stores each photo in the Cloudflare R2 bucket bound as `PHOTOS`, and copies it to the "NZ Map Lab photos" Google Drive folder through the Apps Script (listed on the Sheet's Photos tab). `functions/photos/[name].js` serves photos to the map.
