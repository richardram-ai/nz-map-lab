import rasterio, numpy as np
from rasterio.windows import from_bounds
from rasterio.warp import transform_bounds
W,S,E,N=175.613645,-40.354261,175.625433,-40.345252
for kind in ['dem','dsm']:
    u=f"/vsicurl/https://nz-elevation.s3.ap-southeast-2.amazonaws.com/manawatu-whanganui/palmerston-north_2018/{kind}_1m/2193/BM34_10000_0304.tiff"
    with rasterio.open(u) as src:
        b=transform_bounds('EPSG:4326',src.crs,W,S,E,N)
        b=(b[0]-30,b[1]-30,b[2]+30,b[3]+30)
        win=from_bounds(*b,transform=src.transform).round_offsets().round_lengths()
        a=src.read(1,window=win); t=src.window_transform(win)
        prof=src.profile; prof.update(width=a.shape[1],height=a.shape[0],transform=t,tiled=False,compress='deflate')
        prof.pop('blockxsize',None);prof.pop('blockysize',None)
        with rasterio.open(f'{kind}.tif','w',**prof) as dst: dst.write(a,1)
        v=a[a!=src.nodata] if src.nodata is not None else a
        print(kind,a.shape,src.crs,src.nodata,float(v.min()),float(v.max()),float(np.median(v)))
