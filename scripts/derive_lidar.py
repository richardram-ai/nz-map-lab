import rasterio, numpy as np, json
from rasterio import features
from rasterio.warp import transform as wtrans, reproject, Resampling, transform_bounds
from rasterio.transform import from_bounds as tfb
from scipy.ndimage import gaussian_filter, binary_opening, binary_dilation
from skimage import measure
from shapely.geometry import shape, mapping, box, LineString
from shapely.ops import transform as stransform, unary_union
from shapely import set_precision
import pyproj
from PIL import Image
W,S,E,N=175.613645,-40.354261,175.625433,-40.345252
BOX=box(W,S,E,N)
to4326=pyproj.Transformer.from_crs(2193,4326,always_xy=True).transform
to2193=pyproj.Transformer.from_crs(4326,2193,always_xy=True).transform
dem_r=rasterio.open('dem.tif'); dem=dem_r.read(1).astype('float32'); T=dem_r.transform
dsm=rasterio.open('dsm.tif').read(1).astype('float32')
nod=(dem<-1000)|(dsm<-1000)
dem[nod]=np.nan
# --- contours
sm=gaussian_filter(np.nan_to_num(dem,nan=np.nanmedian(dem)),2.5)
feats=[]
for lv in np.arange(29.5,35.6,0.5):
    for c in measure.find_contours(sm,lv):
        if len(c)<15: continue
        xs,ys=rasterio.transform.xy(T,c[:,0],c[:,1])
        g=stransform(to4326,LineString(list(zip(xs,ys)))).simplify(0.000008).intersection(BOX)
        if g.is_empty: continue
        feats.append({"type":"Feature","properties":{"elev":round(float(lv),1),"major":bool(abs(lv-round(lv))<0.01)},"geometry":mapping(set_precision(g,1e-6))})
json.dump({"type":"FeatureCollection","features":feats},open('/home/claude/map/layers/lidar_contours.geojson','w'),separators=(',',':'))
print('contours',len(feats))
# --- canopy
bl=json.load(open('/home/claude/map/layers/osm_buildings.geojson'))['features']
bpolys=[stransform(to2193,shape(f['geometry'])).buffer(2) for f in bl]
bmask=features.rasterize([(p,1) for p in bpolys],out_shape=dem.shape,transform=T,fill=0).astype(bool)
chm=dsm-np.nan_to_num(dem,nan=0)
veg=(chm>3)&(~bmask)&(~nod)
veg=binary_opening(veg,iterations=1)
boxn=stransform(to2193,BOX)
inbox=features.rasterize([(boxn,1)],out_shape=dem.shape,transform=T,fill=0).astype(bool)
cover=veg[inbox].mean()*100
print('canopy cover % of square (>3m, excl OSM buildings):',round(cover,1))
cls=np.zeros(dem.shape,np.uint8); cls[veg&(chm<=8)]=1; cls[veg&(chm>8)&(chm<=15)]=2; cls[veg&(chm>15)]=3
cf=[]
for geom,val in features.shapes(cls,mask=cls>0,transform=T):
    g=shape(geom)
    if g.area<6: continue
    g=stransform(to4326,g.simplify(0.7)).intersection(BOX)
    if g.is_empty: continue
    cf.append({"type":"Feature","properties":{"band":int(val),"label":{1:'3–8 m',2:'8–15 m',3:'over 15 m'}[int(val)]},"geometry":mapping(set_precision(g,1e-6))})
json.dump({"type":"FeatureCollection","features":cf},open('/home/claude/map/layers/lidar_canopy.geojson','w'),separators=(',',':'))
print('canopy polys',len(cf), 'max chm',float(np.nanmax(np.where(veg,chm,np.nan))))
json.dump({"cover":round(float(cover),1),"elev_min":float(np.nanmin(dem[inbox])),"elev_max":float(np.nanmax(dem[inbox]))},open('stats.json','w'))
# --- elevation tint + hillshade, warped to web mercator over exact box
x0,y0=pyproj.Transformer.from_crs(4326,3857,always_xy=True).transform(W,S); x1,y1=pyproj.Transformer.from_crs(4326,3857,always_xy=True).transform(E,N)
w=1000; h=int(round(w*(y1-y0)/(x1-x0)))
dst=np.full((h,w),np.nan,np.float32); dT=tfb(x0,y0,x1,y1,w,h)
reproject(np.nan_to_num(dem,nan=-9999),dst,src_transform=T,src_crs='EPSG:2193',dst_transform=dT,dst_crs='EPSG:3857',resampling=Resampling.bilinear,src_nodata=-9999,dst_nodata=np.nan)
z=dst; lo,hi=np.nanpercentile(z,1),np.nanpercentile(z,99)
gy,gx=np.gradient(np.nan_to_num(z,nan=np.nanmedian(z)))
px=(x1-x0)/w
slope=np.arctan(3*np.hypot(gx,gy)/px); asp=np.arctan2(-gx,gy)
az,alt=np.radians(315),np.radians(45)
hs=np.sin(alt)*np.cos(slope)+np.cos(alt)*np.sin(slope)*np.cos(az-asp)
t=np.clip((z-lo)/(hi-lo),0,1)
# ramp: low = blue-green, high = sand
stops=np.array([[0,(46,110,150)],[0.35,(120,170,150)],[0.7,(214,206,160)],[1,(196,150,100)]],dtype=object)
r=np.interp(t,[s[0] for s in stops],[s[1][0] for s in stops]);g=np.interp(t,[s[0] for s in stops],[s[1][1] for s in stops]);b=np.interp(t,[s[0] for s in stops],[s[1][2] for s in stops])
shade=0.55+0.45*np.clip(hs,0,1)
img=np.dstack([r*shade,g*shade,b*shade]).clip(0,255).astype(np.uint8)
Image.fromarray(img).save('/home/claude/map/lidar/elev.jpg',quality=78)
print('elev range shown',lo,hi)
