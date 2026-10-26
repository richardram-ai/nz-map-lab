# Ruahine focus block: historical aerial images and LiDAR layers, from LINZ's open imagery and elevation stores on AWS (no key).
#   imagery/aerial-YYYY.jpg   older surveys cut to the focus block (Web Mercator, same box as area.focus.bounds)
#   layers/lidar_canopy.geojson   canopy over 3 m, banded, from the 2023–24 flight (the pines before the 2024–25 harvest)
#   layers/lidar_contours.geojson   20 m contours (100 m major) from the newer ground model
#   lidar/elev.jpg   ground height tint with hillshade, over the focus block; lidar/stats.json
# Usage: python3 ruahine_rasters.py <work_dir>
import json, sys, os, math, time, urllib.request, concurrent.futures as cf
import numpy as np, rasterio, pyproj
from rasterio.vrt import WarpedVRT
from rasterio.enums import Resampling
from rasterio.transform import from_bounds
from rasterio.crs import CRS
from rasterio import features
from scipy.ndimage import gaussian_filter, binary_opening
from skimage import measure
from shapely.geometry import shape, mapping, box, LineString
from shapely.ops import transform as stransform
from shapely import set_precision
from PIL import Image

WORK = sys.argv[1] if len(sys.argv) > 1 else '.'
for d in ('imagery', 'layers', 'lidar'): os.makedirs(os.path.join(WORK, d), exist_ok=True)
CFG = json.load(open(os.path.join(os.path.dirname(__file__), '..', 'config', 'site.json')))
FB = CFG['area']['focus']['bounds']; W, S, E, N = FB['west'], FB['south'], FB['east'], FB['north']
FBOX = box(W, S, E, N)
os.environ.update(GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR', CPL_VSIL_CURL_ALLOWED_EXTENSIONS='.tiff,.tif', GDAL_HTTP_MAX_RETRY='4', GDAL_HTTP_RETRY_DELAY='2')
to3857 = pyproj.Transformer.from_crs(4326, 3857, always_xy=True).transform
to2193 = pyproj.Transformer.from_crs(4326, 2193, always_xy=True).transform
to4326 = pyproj.Transformer.from_crs(2193, 4326, always_xy=True).transform

def items(base, prefix):
    col = json.load(urllib.request.urlopen(base + prefix + 'collection.json', timeout=60))
    hrefs = [l['href'] for l in col['links'] if l['rel'] == 'item']
    def bb(h):
        u = base + prefix + h.lstrip('./')
        for t in range(12):
            try: return u, json.load(urllib.request.urlopen(u, timeout=30))['bbox']
            except Exception: time.sleep(1 + t)
        raise RuntimeError('Could not read ' + u)   # a silently skipped tile leaves a hole in the mosaic
    with cf.ThreadPoolExecutor(8) as ex:
        return [u.replace('.json', '.tiff') for u, b in ex.map(bb, hrefs) if b[0] < E and b[2] > W and b[1] < N and b[3] > S]

def mosaic(urls, crs, bounds, size, bands, resampling=Resampling.average, dtype='float32', nodata=None):
    T = from_bounds(*bounds, *size)
    acc = np.full((len(bands), size[1], size[0]), np.nan, np.float32)
    def rd(u):
        with rasterio.open('/vsicurl/' + u) as src:
            with WarpedVRT(src, crs=crs, transform=T, width=size[0], height=size[1], resampling=resampling,
                           src_nodata=src.nodata if src.nodata is not None else nodata, dst_nodata=np.nan if src.dtypes[0].startswith('float') else 0) as v:
                a = v.read(bands, out_shape=(len(bands), size[1], size[0])).astype(np.float32)
                if not src.dtypes[0].startswith('float'): a[:, a.sum(0) == 0] = np.nan
                elif src.nodata is not None: a[a == src.nodata] = np.nan   # WarpedVRT fills outside the tile with the source nodata
                return a
    with cf.ThreadPoolExecutor(6) as ex:
        for a in ex.map(rd, urls):
            m = ~np.isnan(a[0]); acc[:, m] = a[:, m]
    return acc, T

# ---- Historical aerials, cut to the focus block in Web Mercator (about 2.5 m a pixel)
IMG = 'https://nz-imagery.s3.ap-southeast-2.amazonaws.com/'
x0, y0 = to3857(W, S); x1, y1 = to3857(E, N)
PXM = 2.5 / math.cos(math.radians((S + N) / 2))   # Mercator metres per ground 2.5 m
ISIZE = (int(round((x1 - x0) / PXM)), int(round((y1 - y0) / PXM)))
for year, h in (CFG['area'].get('historical_aerials') or {}).items():
    if year.startswith('_'): continue
    out = os.path.join(WORK, 'imagery', f'aerial-{year}.jpg')
    if os.path.exists(out): print('have', out); continue
    pre = 'hawkes-bay/' + h['survey'] + '/'
    sub = 'rgb/2193/'
    try: urls = items(IMG, pre + sub)
    except Exception:
        sub = 'rgbi/2193/'; urls = items(IMG, pre + sub)
    print(year, h['survey'], len(urls), 'tiles over the block')
    with rasterio.open('/vsicurl/' + urls[0]) as s0: nb = s0.count
    a, _ = mosaic(urls, CRS.from_epsg(3857), (x0, y0, x1, y1), ISIZE, [1, 2, 3] if nb >= 3 else [1])
    filled = (~np.isnan(a[0])).mean()
    a = np.nan_to_num(a, nan=235).clip(0, 255).astype(np.uint8)
    if a.shape[0] == 1: a = np.repeat(a, 3, 0)
    Image.fromarray(a.transpose(1, 2, 0)).save(out, quality=80, optimize=True, progressive=True)
    print('  ', out, ISIZE, f'{filled*100:.0f}% of the block covered', os.path.getsize(out) // 1024, 'KB')

# ---- LiDAR (NZTM, 2 m grid over the focus block plus a margin)
ELEV = 'https://nz-elevation.s3.ap-southeast-2.amazonaws.com/'
bx = stransform(to2193, FBOX).bounds
LB = (math.floor(bx[0]) - 20, math.floor(bx[1]) - 20, math.ceil(bx[2]) + 20, math.ceil(bx[3]) + 20)
RES = 2.0
LSIZE = (int((LB[2] - LB[0]) / RES), int((LB[3] - LB[1]) / RES))
def lidar(survey, kind):
    cache = os.path.join(WORK, 'lidar', f'{survey}_{kind}.npy')
    if os.path.exists(cache):
        a = np.load(cache); a[a < -1000] = np.nan; return a
    urls = items(ELEV, f'hawkes-bay/{survey}/{kind}_1m/2193/')
    print(survey, kind, len(urls), 'tiles')
    a, _ = mosaic(urls, CRS.from_epsg(2193), LB, LSIZE, [1], resampling=Resampling.average)
    a = a[0]; a[a < -1000] = np.nan
    np.save(cache, a); return a
LT = from_bounds(*LB, *LSIZE)
dem1, dsm1 = lidar('hawkes-bay_2023', 'dem'), lidar('hawkes-bay_2023', 'dsm')
inbox = features.rasterize([(stransform(to2193, FBOX), 1)], out_shape=dem1.shape, transform=LT, fill=0).astype(bool)

def polys(mask_by_val, labels, simplify=2.0, min_area=40):
    out = []
    cls = mask_by_val
    for geom, val in features.shapes(cls, mask=cls > 0, transform=LT):
        g = shape(geom)
        if g.area < min_area: continue
        g = stransform(to4326, g.simplify(simplify)).intersection(FBOX)
        if g.is_empty: continue
        out.append({'type': 'Feature', 'properties': {'band': int(val), 'label': labels[int(val)]}, 'geometry': mapping(set_precision(g, 1e-6))})
    return out
def save(name, feats):
    p = os.path.join(WORK, 'layers', name + '.geojson')
    json.dump({'type': 'FeatureCollection', 'features': feats}, open(p, 'w'), separators=(',', ':'))
    print(f'{name:22s} {len(feats):5d} {os.path.getsize(p)//1024:6d} KB')

BANDS = {1: '3–8 m', 2: '8–15 m', 3: 'over 15 m'}
# One canopy layer, from the 2023–24 flight (before the 2024–25 harvest; the 2020–21 flight adds little).
chm = dsm1 - dem1
veg = binary_opening(np.nan_to_num(chm, nan=0) > 3, iterations=1)
cls = np.zeros(chm.shape, np.uint8); cls[veg & (chm <= 8)] = 1; cls[veg & (chm > 8) & (chm <= 15)] = 2; cls[veg & (chm > 15)] = 3
# For the map, smooth the bands to a 6 m grid (the most common band in each 3 × 3 block) so the layer stays small.
from scipy.ndimage import median_filter
sm_cls = median_filter(cls, size=3)[::3, ::3]
LT_save = LT; LT = rasterio.transform.Affine(LT.a * 3, LT.b, LT.c, LT.d, LT.e * 3, LT.f)
save('lidar_canopy', polys(sm_cls, BANDS, simplify=4.0, min_area=300))
LT = LT_save
ok = inbox & ~np.isnan(chm)
stats = {'cover_pct': round(float(veg[ok].mean() * 100), 1), 'tall_ha': round(float((cls[ok] == 3).sum() * RES * RES / 1e4), 1), 'flown': '2023–24'}

# Contours from the newer ground model
z = dem1.copy(); med = np.nanmedian(z); sm = gaussian_filter(np.nan_to_num(z, nan=med), 3)
lo, hi = np.nanpercentile(z[inbox], 0.5), np.nanpercentile(z[inbox], 99.5)
feats = []
for lv in np.arange(math.ceil(lo / 20) * 20, hi, 20):
    for c in measure.find_contours(sm, lv):
        if len(c) < 30: continue
        xs, ys = rasterio.transform.xy(LT, c[:, 0], c[:, 1])
        g = stransform(to4326, LineString(list(zip(xs, ys)))).simplify(0.00004).intersection(FBOX)
        if g.is_empty: continue
        feats.append({'type': 'Feature', 'properties': {'elev': int(lv), 'major': bool(lv % 100 == 0)}, 'geometry': mapping(set_precision(g, 1e-6))})
save('lidar_contours', feats)
stats.update(elev_min=round(float(np.nanmin(z[inbox])), 1), elev_max=round(float(np.nanmax(z[inbox])), 1))

# Ground height tint with hillshade, warped to Web Mercator over the focus block
from rasterio.warp import reproject
w = 1600; h = int(round(w * (y1 - y0) / (x1 - x0)))
dst = np.full((h, w), np.nan, np.float32); dT = from_bounds(x0, y0, x1, y1, w, h)
reproject(np.nan_to_num(dem1, nan=-9999), dst, src_transform=LT, src_crs='EPSG:2193', dst_transform=dT, dst_crs='EPSG:3857',
          resampling=Resampling.bilinear, src_nodata=-9999, dst_nodata=np.nan)
zz = dst; lo, hi = np.nanpercentile(zz, 1), np.nanpercentile(zz, 99)
gy, gx = np.gradient(np.nan_to_num(zz, nan=np.nanmedian(zz)))
px = (x1 - x0) / w * math.cos(math.radians((S + N) / 2))
slope = np.arctan(np.hypot(gx, gy) / px); asp = np.arctan2(-gx, gy)
az, alt = np.radians(315), np.radians(40)
hs = np.sin(alt) * np.cos(slope) + np.cos(alt) * np.sin(slope) * np.cos(az - asp)
t = np.clip((zz - lo) / (hi - lo), 0, 1)
st = [0, .35, .7, 1]; cols = [(70, 120, 90), (130, 170, 120), (214, 200, 150), (180, 150, 120)]
rgb = [np.interp(t, st, [c[i] for c in cols]) for i in range(3)]
shade = 0.35 + 0.65 * np.clip(hs, 0, 1)
img = np.dstack([c * shade for c in rgb]).clip(0, 255).astype(np.uint8)
Image.fromarray(img).save(os.path.join(WORK, 'lidar', 'elev.jpg'), quality=78)
json.dump(stats, open(os.path.join(WORK, 'lidar', 'stats.json'), 'w'))
print(stats)
