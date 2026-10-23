# Make a built-in image of the 1 km square from a LINZ historical aerial survey (nz-imagery bucket, EPSG:2193 COGs),
# reprojected to Web Mercator with the same box and size as the existing imagery/aerial-YYYY.jpg files.
import json, sys, math, urllib.request, concurrent.futures as cf
import numpy as np, rasterio
from rasterio.vrt import WarpedVRT
from rasterio.enums import Resampling
from rasterio.transform import from_bounds
from rasterio.merge import merge
from PIL import Image
BASE='https://nz-imagery.s3.ap-southeast-2.amazonaws.com/'
survey, out = sys.argv[1], sys.argv[2]
W,S,E,N=175.613645,-40.354261,175.625433,-40.345252
SIZE=(2198,2204)
def merc(lon,lat): return lon*20037508.342789244/180, math.log(math.tan((90+lat)*math.pi/360))*20037508.342789244/math.pi
mx0,my0=merc(W,S); mx1,my1=merc(E,N)
col=json.load(urllib.request.urlopen(BASE+survey+'rgb/2193/collection.json'))
items=[l['href'] for l in col['links'] if l['rel']=='item']
def bbox(h):
    u=BASE+survey+'rgb/2193/'+h.lstrip('./')
    for t in range(5):
        try: j=json.load(urllib.request.urlopen(u,timeout=30)); return u, j['bbox']
        except Exception as e: err=e
    raise err
hits=[]
with cf.ThreadPoolExecutor(8) as ex:
    for u,b in ex.map(bbox,items):
        if b[0]<E and b[2]>W and b[1]<N and b[3]>S: hits.append(u.replace('.json','.tiff'))
print(len(items),'items,',len(hits),'cover the square:',[h.split('/')[-1] for h in hits])
dst_t=from_bounds(mx0,my0,mx1,my1,*SIZE)
acc=np.zeros((3,SIZE[1],SIZE[0]),np.float32); cnt=np.zeros((SIZE[1],SIZE[0]),np.float32)
for h in hits:
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR',CPL_VSIL_CURL_ALLOWED_EXTENSIONS='.tiff'):
        with rasterio.open('/vsicurl/'+h) as src:
            with WarpedVRT(src,crs='EPSG:3857',transform=dst_t,width=SIZE[0],height=SIZE[1],resampling=Resampling.bilinear) as v:
                a=v.read(indexes=[1,2,3]).astype(np.float32)
                m=v.read_masks(1)>0 if src.count<4 else v.read(4)>0
                m&=a.sum(0)>0
                acc[:,m]+=a[:,m]; cnt[m]+=1
img=np.where(cnt>0,acc/np.maximum(cnt,1),240).clip(0,255).astype(np.uint8)
print('filled %.1f%%'%(100*(cnt>0).mean()))
Image.fromarray(img.transpose(1,2,0)).save(out,quality=80,optimize=True,progressive=True)
