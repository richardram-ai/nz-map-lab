import json,glob,os,base64
s=open('template.html').read()
data={os.path.basename(f)[:-8]:json.load(open(f)) for f in glob.glob('layers/*.geojson')}
img={k:'data:image/jpeg;base64,'+base64.b64encode(open(f'lidar/{k2}.jpg','rb').read()).decode() for k,k2 in [('aerial','aerial'),('elev','elev')]}
st=json.load(open('lidar/stats.json'))
out=(s.replace('/*__MAPLIBRE_CSS__*/',open('maplibre.css').read())
      .replace('/*__DATA__*/{}',json.dumps(data,separators=(',',':'),ensure_ascii=False))
      .replace('/*__IMG__*/{}',json.dumps(img))
      .replace('/*__LIDAR__*/{}',json.dumps(st)))
open('sydney-street-map-lab.html','w').write(out); print(os.path.getsize('sydney-street-map-lab.html')//1024,'KB')
