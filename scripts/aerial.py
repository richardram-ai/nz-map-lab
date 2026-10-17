import math, io, urllib.request, concurrent.futures as cf, sys
from PIL import Image
K=sys.argv[1]; z=int(sys.argv[2]); LAYER=sys.argv[4] if len(sys.argv)>4 else "119050"; OUT=sys.argv[5] if len(sys.argv)>5 else "aerial.jpg"
W,S,E,N=175.613645,-40.354261,175.625433,-40.345252
n=2**z
def px(lon,lat):
    return (lon+180)/360*n*256, (1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*n*256
x0,y0=px(W,N); x1,y1=px(E,S)
tx0,ty0,tx1,ty1=int(x0//256),int(y0//256),int(x1//256),int(y1//256)
def get(t):
    x,y=t; u=f"https://tiles-{'abcd'[(x+y)%4]}.data-cdn.linz.govt.nz/services;key={K}/tiles/v4/layer={LAYER}/EPSG:3857/{z}/{x}/{y}.png"
    return t, Image.open(io.BytesIO(urllib.request.urlopen(u,timeout=60).read())).convert('RGB')
canvas=Image.new('RGB',((tx1-tx0+1)*256,(ty1-ty0+1)*256),(240,240,240))
with cf.ThreadPoolExecutor(12) as ex:
    for (x,y),im in ex.map(get,[(x,y) for x in range(tx0,tx1+1) for y in range(ty0,ty1+1)]):
        canvas.paste(im,((x-tx0)*256,(y-ty0)*256))
crop=canvas.crop((round(x0-tx0*256),round(y0-ty0*256),round(x1-tx0*256),round(y1-ty0*256)))
print(crop.size)
crop.save(OUT,quality=int(sys.argv[3]),optimize=True,progressive=True)
