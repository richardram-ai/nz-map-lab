# Ruahine: fetch the park-wide and focus-block vector layers into layers/ (one GeoJSON per layer).
# Park-wide: DOC boundary, tracks, huts, campsites, roads; Herenga ā Nuku tracks and public access land.
# Focus block: iNaturalist sightings. Park-wide: iNaturalist conifer (Pinaceae) sightings.
# Run from a working folder: python3 ruahine_fetch.py <out_dir>
import json, sys, os, urllib.request, urllib.parse, time
from shapely.geometry import shape, mapping, box
from shapely.ops import unary_union
from shapely import set_precision
OUT = sys.argv[1] if len(sys.argv) > 1 else 'layers'
os.makedirs(OUT, exist_ok=True)
CFG = json.load(open(os.path.join(os.path.dirname(__file__), '..', 'config', 'site.json')))
PB = CFG['area']['bounds']; FB = CFG['area']['focus']['bounds']
PBOX = box(PB['west'], PB['south'], PB['east'], PB['north'])
FBOX = box(FB['west'], FB['south'], FB['east'], FB['north'])
DOC = 'https://services1.arcgis.com/3JjYDyG3oajxU6HO/arcgis/rest/services/'
WA = 'https://services2.arcgis.com/b5ADKIcWivL5vNaV/arcgis/rest/services/'

def get(u, tries=4):
    for t in range(tries):
        try:
            req = urllib.request.Request(u, headers={'User-Agent': 'nz-map-lab (richardram-ai/nz-map-lab)'})
            with urllib.request.urlopen(req, timeout=120) as r: return json.load(r)
        except Exception as e:
            err = e; time.sleep(2 + t * 3)
    raise err

def arcgis(url, where='1=1', bbox=PB, fields='*'):
    feats, off = [], 0
    while True:
        q = dict(where=where, geometry=f"{bbox['west']},{bbox['south']},{bbox['east']},{bbox['north']}", geometryType='esriGeometryEnvelope',
                 inSR=4326, spatialRel='esriSpatialRelIntersects', outFields=fields, outSR=4326, f='geojson', resultOffset=off, resultRecordCount=1000)
        d = get(url + '/query?' + urllib.parse.urlencode(q))
        fs = d.get('features', []); feats += fs
        if len(fs) < 1000 and not d.get('exceededTransferLimit'): break
        off += len(fs)
    return feats

def write(name, feats):
    p = os.path.join(OUT, name + '.geojson')
    json.dump({'type': 'FeatureCollection', 'features': feats}, open(p, 'w'), separators=(',', ':'), ensure_ascii=False)
    print(f'{name:22s} {len(feats):5d} {os.path.getsize(p)//1024:6d} KB')

def keep(feats, props, clip=None, simplify=0.00002, rename=None):
    out = []
    for f in feats:
        if not f.get('geometry'): continue
        g = shape(f['geometry'])
        if clip is not None: g = g.intersection(clip)
        if g.is_empty: continue
        if simplify and g.geom_type not in ('Point', 'MultiPoint'): g = g.simplify(simplify, preserve_topology=True)
        pr = {(rename or {}).get(k, k): f['properties'].get(k) for k in props}
        out.append({'type': 'Feature', 'properties': pr, 'geometry': mapping(set_precision(g, 1e-6))})
    return out

# ---- Park boundary (DOC Public Conservation Land)
park = arcgis(DOC + 'DOC_Public_Conservation_Land/FeatureServer/0', where="Name='Ruahine Forest Park'")
write('doc_park', keep(park, ['Name', 'Recorded_Area'], simplify=0.0002, rename={'Name': 'name', 'Recorded_Area': 'ha'}))
PARK = unary_union([shape(f['geometry']) for f in park])
NEAR = PARK.buffer(0.03)  # about 3 km round the park: access roads and tracks leading in

# ---- DOC tracks, huts, campsites, roads
write('doc_tracks', keep(arcgis(DOC + 'DOC_Tracks_Open_Data/FeatureServer/0'), ['TechObjectName', 'ObjectType', 'SubObjectType', 'GISStatusStr'], clip=NEAR,
      rename={'TechObjectName': 'name', 'ObjectType': 'type', 'SubObjectType': 'kind', 'GISStatusStr': 'status'}))
write('doc_huts', keep(arcgis(DOC + 'DOC_Huts_Open_Data/FeatureServer/0'), ['TechObjectName', 'ObjectType', 'SubObjectType', 'GISStatusStr'], clip=NEAR,
      rename={'TechObjectName': 'name', 'ObjectType': 'type', 'SubObjectType': 'kind', 'GISStatusStr': 'status'}))
write('doc_campsites', keep(arcgis(DOC + 'DOC_Campsites_Open_Data/FeatureServer/0'), ['TechObjectName', 'ObjectType', 'SubObjectType'], clip=NEAR,
      rename={'TechObjectName': 'name', 'ObjectType': 'type', 'SubObjectType': 'kind'}))
write('doc_roads', keep(arcgis(DOC + 'DOC_Roads_Open_Data/FeatureServer/0'), ['TechObjectName', 'ObjectType', 'SubObjectType'], clip=NEAR,
      rename={'TechObjectName': 'name', 'ObjectType': 'type', 'SubObjectType': 'kind'}))

# ---- Herenga ā Nuku: national tracks and public access land
tr = arcgis(WA + 'National_Tracks_Dataset_Pilot/FeatureServer/0')
# Coded values from the service's field domains, so popups read in words.
dom = {f['name']: {str(c['code']): c['name'] for c in f['domain'].get('codedValues', [])}
       for f in get(WA + 'National_Tracks_Dataset_Pilot/FeatureServer/0?f=json')['fields'] if f.get('domain')}
for f in tr:
    for k, m in dom.items():
        v = f['properties'].get(k)
        if v is not None and str(v) in m: f['properties'][k] = m[str(v)]
write('wa_tracks', keep(tr, ['Name', 'Walk', 'Bike', 'OffRoadVehicle', 'Horse', 'DogAccess', 'ConditionsOfUse', 'Status', 'Locality'], clip=NEAR,
      rename={'Name': 'name', 'Walk': 'walk', 'Bike': 'bike', 'OffRoadVehicle': 'vehicle', 'Horse': 'horse', 'DogAccess': 'dogs', 'ConditionsOfUse': 'conditions', 'Status': 'status', 'Locality': 'locality'}))
for lid, name in [(4, 'wa_access_land'), (3, 'wa_reserves'), (1, 'wa_road_parcels'), (2, 'wa_easements')]:
    fs = arcgis(WA + f'Public_Access_Areas/FeatureServer/{lid}')
    props = list((fs[0]['properties'] if fs else {}).keys())
    want = [k for k in ('common_name', 'paa_type', 'paa_class', 'public_access', 'managed_by', 'statutory_purpose', 'appellation') if k in props]
    write(name, keep(fs, want, clip=NEAR, simplify=0.00003))

# ---- iNaturalist: all sightings in the focus block, conifers across the park
def inat(params, clipgeom):
    out, page = [], 1
    while True:
        q = dict(params, per_page=200, page=page, order_by='observed_on')
        d = get('https://api.inaturalist.org/v1/observations?' + urllib.parse.urlencode(q))
        for o in d['results']:
            if not o.get('geojson'): continue
            g = shape(o['geojson'])
            if not clipgeom.contains(g): continue
            t = o.get('taxon') or {}
            out.append({'type': 'Feature', 'properties': {
                'name': t.get('preferred_common_name') or t.get('name') or 'Unknown', 'sci': t.get('name') or '',
                'group': t.get('iconic_taxon_name') or 'Other', 'date': o.get('observed_on') or '', 'grade': o.get('quality_grade'),
                'obscured': bool(o.get('obscured')), 'lic': o.get('license_code') or '', 'url': o.get('uri')},
                'geometry': mapping(set_precision(g, 1e-6))})
        if page * 200 >= d['total_results'] or page >= 25: break
        page += 1; time.sleep(1)
    return out
f = FB
write('inat_obs', inat(dict(nelat=f['north'], nelng=f['east'], swlat=f['south'], swlng=f['west']), FBOX))
p = PB
write('inat_conifers', inat(dict(nelat=p['north'], nelng=p['east'], swlat=p['south'], swlng=p['west'], taxon_id=47562), NEAR))  # 47562 = Pinaceae (pines, Douglas fir, larches)
