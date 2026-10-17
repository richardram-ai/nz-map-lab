# NZ Map Lab

A test of what free public New Zealand data can be layered on a map, and how an organisation can add its own notes on top. The test area is a 1 km square centred on 16 Sydney Street, Palmerston North.

Live site: https://nz-map-lab.pages.dev

## What's here

| Path | What it is |
|---|---|
| `index.html` | The map. One self-contained page: data, aerial photo and elevation image are built in. Only MapLibre GL JS loads from cdnjs. |
| `data/` | Each layer as GeoJSON, clipped to the square, for use in QGIS or other tools. |
| `imagery/` | The 2024 aerial photo and 2018 LiDAR elevation shading used in the page. |
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
| Aerial photo 2024 (Palmerston North 0.1 m urban) | [Toitū Te Whenua LINZ](https://www.linz.govt.nz) | CC BY 4.0 |
| LiDAR 2018 (DEM and DSM, 1 m), contours and tree canopy derived from it | [Toitū Te Whenua LINZ](https://www.linz.govt.nz), via the open elevation store on AWS | CC BY 4.0 |

Data downloaded 17 October 2026. The groundwater bore owner's name was removed from the source data.

## Keys

No API keys are stored in this repository. On the hosted site, the "LINZ full-detail photo" option loads tiles through `functions/linz/aerial/[[path]].js`, a Cloudflare Pages Function that adds the LINZ Data Service key from the Cloudflare secret `LINZ_KEY`. It only serves tiles around the test square. When the page is opened as a file from a computer, it asks for a key instead and keeps it in that browser only.

## Annotations

Annotations drawn on the map are saved in the viewer's browser. Use "Show as GeoJSON" to copy them out and "Load pasted GeoJSON" to bring them back in.
