# Builds the Ruahine map page (index.html) from the shared template (scripts/template.html).
# Replaces the parts that are specific to the Palmerston North test square: header, base maps, layers, timeline years,
# drawing form (adds the wilding-area task), findings. Data: layers/*.geojson and lidar/ from ruahine_fetch.py and ruahine_rasters.py.
# Usage: python3 ruahine_page.py <work_dir>   (writes scripts/template-ruahine.html and index.html in the repo)
import json, os, sys, base64, glob, shutil
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
WORK = sys.argv[1] if len(sys.argv) > 1 else '.'
T = open(os.path.join(REPO, 'scripts', 'template.html')).read().split('\n')
CFG = json.load(open(os.path.join(REPO, 'config', 'site.json')))
LINES = {}   # 1-based line ranges in template.html -> replacement text
def rep(a, b, text): LINES[(a, b)] = text

def find(s, start=0):
    for i in range(start, len(T)):
        if s in T[i]: return i + 1
    raise SystemExit('Template changed: could not find ' + s)
def block(start_marker, end_marker):
    a = find(start_marker); b = find(end_marker, a - 1); return a, b

# ---------- header
a = find('<title>'); rep(a, a, '<title>Ruahine Map Lab</title>')
a, b = block('<header>', '</header>')
rep(a, b, '''<header>
  <div class="lede">
    <h3>Mapping project · Ruahine test group</h3>
    <h1>Ruahine Map Lab</h1>
    <p>Walking access across <a href="https://www.doc.govt.nz/parks-and-recreation/places-to-go/manawatu-whanganui/places/ruahine-forest-park/" target="_blank" rel="noopener">Ruahine Forest Park</a> (95,000&nbsp;ha), and a detailed block at the end of Kashmir Road, Ashley Clinton, where wilding pines are being cleared. The block has aerial photos from 1980 to 2025–26 and 2023–24 LiDAR. Draw the work area and the parts that are cleared, not yet cleared or growing back; field records come from <a href="/add/">the phone form</a>.</p>
  </div>
  <dl class="details">
    <dt>Document Name</dt><dd>Ruahine Map Lab</dd>
    <dt>Author</dt><dd>Richard Ram</dd>
    <dt>Date</dt><dd>26.10.26</dd>
  </dl>
</header>''')

# ---------- base map choices
a, b = block('<div class="basebar no-print"', '</div>')
rep(a, b, '''    <div class="basebar no-print" role="radiogroup" aria-label="Base map">
      <span class="hint">Base map:</span>
      <label><input type="radio" name="base" id="base-aerial" value="aerial" checked> Aerial photo (year below)</label>
      <label><input type="radio" name="base" id="base-topo" value="topo"> Topo map</label>
      <label><input type="radio" name="base" id="base-sat" value="sat"> Satellite, 10 m</label>
      <label><input type="radio" name="base" id="base-ofm" value="ofm"> Street map</label>
      <span class="hint" style="margin-left:auto;display:flex;gap:6px"><button type="button" id="go-focus">Kashmir Road block</button><button type="button" id="go-park">Whole park</button></span>
    </div>''')
a = find('aria-label="Map of the 1 km test square"')
T[a - 1] = T[a - 1].replace('Map of the 1 km test square', 'Map of Ruahine Forest Park and the Kashmir Road block')

# ---------- drawing bar hint
a = find('<span class="lbl">Add your own:</span>'); T[a - 1] = T[a - 1].replace('Add your own:', 'Draw:')

# ---------- annotation form: a task (wilding area) or a plain note
a, b = block('<form class="annform" id="annform" hidden>', '</form>')
rep(a, b, '''      <form class="annform" id="annform" hidden>
        <label>Record type<select id="a-task"></select></label>
        <label>Title<input id="a-title" maxlength="80" placeholder="Optional for a wilding area"></label>
        <div id="a-fields" style="display:flex;flex-direction:column;gap:6px"></div>
        <label id="a-cat-wrap">Category<select id="a-cat"></select></label>
        <label>Note<textarea id="a-note" rows="2" maxlength="400"></textarea></label>
        <label id="a-by-wrap" hidden>Your name<input id="a-by" maxlength="60" autocomplete="name"></label>
        <p class="hint" id="a-msg" role="status"></p>
        <div class="row" style="display:flex;gap:6px"><button class="primary" type="submit">Save</button><button type="button" id="a-discard">Discard</button></div>
      </form>''')
a = find('<h3>Your annotations</h3>'); T[a - 1] = T[a - 1].replace('Your annotations', 'Records and wilding areas')

# ---------- findings sections
a = find('<h2>What the square told us</h2>') - 1   # the <section> line
b = find('</section>', find('<h2>Knowledge gaps to research</h2>'))
rep(a, b, '''<section>
  <h2>The wilding pine work</h2>
  <p>Totals from the areas drawn on the map. Draw the whole work area first, then the parts inside it that are cleared, not yet cleared, or have pines coming back.</p>
  <div class="cols" id="tally"></div>
</section>

<section class="pagebreak">
  <h2>Layer by layer</h2>
  <p>Who publishes each layer and the terms you can reuse it under. Park‑wide layers cover the forest park and about 3&nbsp;km around it; the LiDAR, the older aerial photos and the species sightings cover the Kashmir Road block only.</p>
  <div class="tablewrap"><table id="ltable"><thead><tr><th>Layer</th><th>Publisher</th><th>Licence</th><th style="text-align:right">Features</th><th>Covers</th><th>What it tells you</th></tr></thead><tbody></tbody></table></div>
</section>

<section>
  <h2>Open questions</h2>
  <ul class="gaps">
    <li><b>The real work area</b><span>The Kashmir Road block is a provisional box round the road end. Once the work area is drawn, the block (and the offline download) can be fitted to it.</span></li>
    <li><b>Herenga ā Nuku licence</b><span>The <a href="https://www.herengaanuku.govt.nz" target="_blank" rel="noopener">Herenga ā Nuku</a> site states CC BY 4.0, but its track and access‑land services carry no licence text. Confirm before the map is made public.</span></li>
    <li><b>Two regions, two sets of aerials</b><span>Each aerial year joins the Hawke's Bay survey (east) with the nearest Manawatū‑Whanganui survey (west), over the 2025–26 satellite. The years don't always match: west is 2015–16 for “2014” and 2024 for “2025”, and there's no western survey for 2019.</span></li>
    <li><b>LiDAR predates the harvest</b><span>Both Hawke's Bay LiDAR flights (2020–21 and 2023–24) were before DOC's 2024–25 harvest, so LiDAR can't show the clearance yet. The 2025–26 aerial does.</span></li>
    <li><b>Plant list</b><span>The phone form's plant list is a starter list for the eastern Ruahine foothills. Replace it with the group's list and the names they use.</span></li>
    <li><b>Offline in the field</b><span>Open the phone form with signal, tap “Save the map for offline use”, and let the photo helper download once. After that the form, map tiles for the block and species suggestions work without signal.</span></li>
  </ul>
</section>''')

# ---------- script: settings, constants, layers
a = find('const LIDAR = /*__LIDAR__*/{};')
b = find('const INATC=')
rep(a, b - 1, '''const LIDAR = /*__LIDAR__*/{};
const SITE_CFG = /*__CFG__*/{};
const AREA=SITE_CFG.area, FB=AREA.focus.bounds, PB=AREA.bounds;
const BOX=[[FB.west,FB.south],[FB.east,FB.north]];
const CENTER=[(FB.west+FB.east)/2,(FB.south+FB.north)/2];
const PARKBOX=[[176.0,-40.27],[176.36,-39.50]];
const BOXPOLY={type:"Feature",properties:{},geometry:{type:"Polygon",coordinates:[[[BOX[0][0],BOX[0][1]],[BOX[1][0],BOX[0][1]],[BOX[1][0],BOX[1][1]],[BOX[0][0],BOX[1][1]],[BOX[0][0],BOX[0][1]]]]}};

const PUB={
  doc:['Department of Conservation','https://www.doc.govt.nz','CC BY 4.0'],
  wa:['Herenga ā Nuku Aotearoa','https://www.herengaanuku.govt.nz','CC BY 4.0 on their site; not stated in the service'],
  inat:['iNaturalist NZ','https://inaturalist.nz','Per record, mostly CC BY‑NC'],
  linz:['Toitū Te Whenua LINZ','https://www.linz.govt.nz','CC BY 4.0'],
};''')
a = find('const LAYERS=[')
b = find("LAYERS.forEach(L=>{L.count=")
rep(a, b, '''// One table drives the map, the layer list and the findings table. lazy: loaded from /data/ the first time it is switched on.
const LAYERS=[
 {g:'Walking access',id:'doc_park',label:'Ruahine Forest Park',kind:'outline',color:'#2c7a4b',width:2.5,on:true,pub:'doc',cov:'Park',why:'DOC’s outline of the forest park (Public Conservation Land), 95,266 ha.'},
 {g:'Walking access',id:'wa_tracks',label:'Tracks (Herenga ā Nuku)',kind:'line',color:'#b8334a',width:2,on:true,pub:'wa',cov:'Park + 3 km',why:'National tracks dataset (pilot), with what each track is suitable for, dog rules and status. Mostly tramping tracks here.'},
 {g:'Walking access',id:'doc_tracks',label:'DOC tracks',kind:'line',color:'#8a5a3c',width:1.5,dash:true,on:false,pub:'doc',cov:'Park + 3 km',why:'DOC’s own track lines, with track type. Overlaps the Herenga ā Nuku tracks; useful where they differ.'},
 {g:'Walking access',id:'doc_huts',label:'Huts',kind:'circle',color:'#c47d14',r:5.5,on:true,pub:'doc',cov:'Park + 3 km',why:'DOC huts and bivvies, with hut type.'},
 {g:'Walking access',id:'doc_campsites',label:'Campsites',kind:'circle',color:'#1f8a8a',r:5,on:false,pub:'doc',cov:'Park + 3 km',why:'DOC campsites.'},
 {g:'Walking access',id:'doc_roads',label:'DOC roads',kind:'line',color:'#5f6b5a',width:2,on:false,pub:'doc',cov:'Park + 3 km',why:'Roads DOC manages, mostly road ends and car parks at the park edge.'},
 {g:'Walking access',id:'wa_access_land',label:'Public access conservation land',kind:'fill',color:'#2c7a4b',opacity:.12,outline:true,on:false,pub:'wa',cov:'Park + 3 km',why:'Conservation land the public can walk on, including stewardship areas beside the park.'},
 {g:'Walking access',id:'wa_reserves',label:'Reserves',kind:'fill',color:'#6a9c3a',opacity:.15,outline:true,on:false,pub:'wa',cov:'Park + 3 km',why:'Council and other reserves with public access.'},
 {g:'Walking access',id:'wa_road_parcels',label:'Unformed legal roads',kind:'fill',color:'#6a4c9c',opacity:.25,on:false,pub:'wa',cov:'Park + 3 km',why:'Road parcels, many unformed (“paper roads”). The public can walk them, which can give legal access to the park across farmland.'},
 {g:'Walking access',id:'wa_easements',label:'Walking access easements',kind:'line',color:'#6a4c9c',width:2.5,on:false,pub:'wa',cov:'Park + 3 km',why:'Legal walking easements across private land.'},
 {g:'Wilding pines',id:'inat_conifers',label:'Conifer sightings (iNaturalist)',kind:'circle',color:'#b8334a',r:5,on:false,pub:'inat',cov:'Park + 3 km',why:'Pines, Douglas fir and larch recorded by iNaturalist observers across the park. Few records, but a start on where wildings turn up.'},
 {g:'Kashmir Road block',id:'inat_obs',label:'Species sightings',kind:'circle',color:'#28699a',on:false,pub:'inat',cov:'Block',why:'All iNaturalist records in the block. Location is blurred for sensitive species.'},
 {g:'Kashmir Road block',id:'lidar_canopy',label:'Tree canopy, 2023–24',kind:'canopy',lazy:true,on:false,color:'#3f8f56',pub:'linz',cov:'Block',countText:'on demand',why:'Derived here: LiDAR surface height minus ground height, over 3 m, smoothed to 6 m. Shows the pine block’s height before the 2024–25 harvest. CANOPY% of the block was over 3 m.'},
 {g:'Kashmir Road block',id:'lidar_contours',label:'Contours, 20 m',kind:'contour',lazy:true,on:false,color:'#7a5a2c',pub:'linz',cov:'Block',countText:'on demand',why:'Generated here from the 2023–24 LiDAR ground model, 100 m contours bold.'},
 {g:'Kashmir Road block',id:'lidar_elev',label:'Ground height shading',kind:'image',on:false,color:'#78aa96',countText:'1 image',pub:'linz',cov:'Block',why:'Bare‑earth height from the 2023–24 Hawke’s Bay LiDAR with hillshade, ELEV_RANGE.'},
];
LAYERS.forEach(L=>{L.count=L.lazy?0:((DATA[L.id]||{}).features||[]).length; if(L.why)L.why=L.why.replace('CANOPY%',LIDAR.cover_pct+'%').replace('ELEV_RANGE',`${Math.round(LIDAR.elev_min)}–${Math.round(LIDAR.elev_max)} m above sea level`)});''')

# ---------- annotation store
a = find('const CATS={')
b = find('if(!ANN||!Array.isArray(ANN.features))')
rep(a, b, '''const CATS=Object.fromEntries((SITE_CFG.categories||[]).map(c=>[c.id,c.colour])); CATS.Example='#7d8883';
const CATLABEL=Object.fromEntries((SITE_CFG.categories||[]).map(c=>[c.id,c.label]));
const SKEY='ruahine-map-annotations-v1';
let ANN; let stored=true;
try{const s=localStorage.getItem(SKEY); ANN=s?JSON.parse(s):null}catch(e){stored=false}
if(!ANN||!Array.isArray(ANN.features)) ANN={type:'FeatureCollection',features:[]};''')

# ---------- map styles, map, overlays, startup
a = find('// ---------- map styles ----------')
b = find("document.querySelectorAll('input[name=base]').forEach(r=>r.addEventListener('change',()=>setBase(r.value)));")
rep(a, b, r'''// ---------- map styles ----------
// Aerial years come from LINZ through the site's tile function; the older surveys are single images of the block.
const IMGBOX=[[BOX[0][0],BOX[1][1]],[BOX[1][0],BOX[1][1]],[BOX[1][0],BOX[0][1]],[BOX[0][0],BOX[0][1]]];
const HISTS=AREA.historical_aerials||{};
const HIST=Object.keys(HISTS).filter(k=>!k.startsWith('_')).map(Number).sort((a,b)=>a-b);
const LINZY=Object.keys(AREA.linz_layers||{}).map(Number).sort((a,b)=>a-b);
const YEARS=[...HIST,...LINZY];
const YEARNOTE=Object.fromEntries([...HIST.map(y=>[y,HISTS[y].note]),...LINZY.map(y=>[y,(AREA.aerial_notes||{})[y]||String(y)])]);
const TILE=q=>location.origin+'/linz/aerial/{z}/{x}/{y}.png?'+q;
const BG=[{id:'bg',type:'background',paint:{'background-color':'#eef1ec'}}];
function yearStyle(y,canvasId){
  if(HIST.includes(y)) return {version:8,sources:{aer:{type:'canvas',canvas:canvasId,coordinates:IMGBOX,animate:false,attribution:'Aerial '+y+' © Toitū Te Whenua LINZ, CC BY 4.0'}},layers:[...BG,{id:'aer',type:'raster',source:'aer',paint:{'raster-fade-duration':0}}]};
  // Satellite underneath, then the western (Manawatū-Whanganui) survey, then the Hawke's Bay survey, so the whole park is covered.
  const west=(AREA.linz_layers_west||{})[y];
  const st={version:8,sources:{sat:{type:'raster',tiles:[TILE('src=sat')],tileSize:256,minzoom:8,maxzoom:15,attribution:'Satellite 2025–26 © Toitū Te Whenua LINZ, CC BY 4.0'},
    aer:{type:'raster',tiles:[TILE('year='+y)],tileSize:256,minzoom:10,maxzoom:21,attribution:'Aerial '+y+' © Toitū Te Whenua LINZ, CC BY 4.0'}},
    layers:[...BG,{id:'sat',type:'raster',source:'sat'}]};
  if(west){ st.sources.aerw={type:'raster',tiles:[TILE('year='+y+'&side=west')],tileSize:256,minzoom:10,maxzoom:21}; st.layers.push({id:'aerw',type:'raster',source:'aerw'}) }
  st.layers.push({id:'aer',type:'raster',source:'aer'});
  return st;
}
function rasterStyle(tiles,attr,max,min){return {version:8,sources:{r:{type:'raster',tiles:[tiles],tileSize:256,minzoom:min||0,maxzoom:max||19,attribution:attr}},layers:[...BG,{id:'r',type:'raster',source:'r'}]}}
let baseMode='aerial';
const imgReady={};
function drawImg(key){return new Promise(res=>{const im=new Image();im.onload=()=>{const c=document.getElementById('cv-'+key);c.width=im.naturalWidth;c.height=im.naturalHeight;c.getContext('2d').drawImage(im,0,0);imgReady[key]=true;res(true)};im.onerror=()=>res(false);im.src=IMG[key]})}
let yearA=LINZY[LINZY.length-1], yearB=HIST[0]||LINZY[0], comparing=false;
const map=new maplibregl.Map({container:'map',style:yearStyle(yearA,'cv-aerial'),bounds:BOX,fitBoundsOptions:{padding:12},maxBounds:[[PB.west-.05,PB.south-.05],[PB.east+.05,PB.north+.05]],minZoom:8,attributionControl:{compact:false},canvasContextAttributes:{preserveDrawingBuffer:true},preserveDrawingBuffer:true});
map.addControl(new maplibregl.NavigationControl({showCompass:false}),'top-right');
map.addControl(new maplibregl.ScaleControl({maxWidth:120,unit:'metric'}),'bottom-left');
const lazyLoaded={};
function vis(L){const c=document.getElementById('chk-'+L.id); return (c?c.checked:L.on)?'visible':'none'}
function addLayerFor(L){
  const v=vis(L);
  if(L.kind==='image'){ if(!imgReady.elev) return; map.addSource(L.id,{type:'canvas',canvas:'cv-elev',coordinates:IMGBOX,animate:false});
    map.addLayer({id:L.id,type:'raster',source:L.id,layout:{visibility:v},paint:{'raster-opacity':.85,'raster-fade-duration':0}},'box-line'); return }
  if(L.lazy&&v==='none'&&!lazyLoaded[L.id]) return;
  map.addSource(L.id,{type:'geojson',data:L.lazy?('/data/'+L.id+'.geojson'):(DATA[L.id]||{type:'FeatureCollection',features:[]}),attribution:PUB[L.pub][0]});
  if(L.lazy) lazyLoaded[L.id]=true;
  const before='box-line';
  if(L.kind==='contour') map.addLayer({id:L.id,type:'line',source:L.id,layout:{visibility:v,'line-join':'round'},paint:{'line-color':L.color,'line-width':['case',['get','major'],1.6,.7],'line-opacity':['case',['get','major'],.95,.6]}},before);
  else if(L.kind==='canopy') map.addLayer({id:L.id,type:'fill',source:L.id,layout:{visibility:v},paint:{'fill-color':['match',['get','band'],1,'#a6d78f',2,'#4fa15e','#1d5e31'],'fill-opacity':.55}},before);
  else if(L.kind==='fill'){ map.addLayer({id:L.id,type:'fill',source:L.id,layout:{visibility:v},paint:{'fill-color':L.color,'fill-opacity':L.opacity??.6}},before);
    if(L.outline) map.addLayer({id:L.id+'__o',type:'line',source:L.id,layout:{visibility:v},paint:{'line-color':L.color,'line-width':1}},before); }
  else if(L.kind==='outline'){ map.addLayer({id:L.id,type:'fill',source:L.id,layout:{visibility:v},paint:{'fill-color':L.color,'fill-opacity':0.01}},before);
    map.addLayer({id:L.id+'__o',type:'line',source:L.id,layout:{visibility:v},paint:{'line-color':L.color,'line-width':L.width||1.6}},before); }
  else if(L.kind==='line') map.addLayer({id:L.id,type:'line',source:L.id,layout:{visibility:v,'line-cap':'round','line-join':'round'},paint:{'line-color':L.color,'line-width':['interpolate',['linear'],['zoom'],9,(L.width||2)*.6,14,(L.width||2)*1.4],...(L.dash?{'line-dasharray':[2,2]}:{})}},before);
  else if(L.kind==='circle'){ const col = L.id==='inat_obs' ? ['match',['get','group'],...Object.entries(INATC).flat(),'#7d8883'] : L.color;
    map.addLayer({id:L.id,type:'circle',source:L.id,layout:{visibility:v},paint:{'circle-color':col,'circle-radius':L.r||4.5,'circle-stroke-color':'#ffffff','circle-stroke-width':1.2,'circle-opacity':.92}},before); }
}
function addOverlays(){
  map.addSource('box',{type:'geojson',data:BOXPOLY});
  map.addLayer({id:'box-line',type:'line',source:'box',paint:{'line-color':'#ffffff','line-width':2,'line-dasharray':[4,2]}});
  LAYERS.forEach(L=>{ if(!L.empty&&L.panel!==false) addLayerFor(L) });
  // records
  map.addSource('ann',{type:'geojson',data:annData()});
  const ccol=['match',['get','cat'],...Object.entries(CATS).flat(),'#b8334a'];
  map.addLayer({id:'ann-fill',type:'fill',source:'ann',filter:['==',['geometry-type'],'Polygon'],paint:{'fill-color':ccol,'fill-opacity':['match',['get','cat'],'Work area',.04,.28]}});
  map.addLayer({id:'ann-line',type:'line',source:'ann',filter:['!=',['geometry-type'],'Point'],paint:{'line-color':ccol,'line-width':['match',['get','cat'],'Work area',3.5,2.5],'line-dasharray':['match',['get','cat'],'Work area',['literal',[3,1.5]],['literal',[1,0]]]}});
  map.addLayer({id:'ann-pt',type:'circle',source:'ann',filter:['==',['geometry-type'],'Point'],paint:{'circle-radius':7,'circle-color':['case',['get','_needs'],'#ffffff',ccol],'circle-stroke-color':['case',['get','_needs'],ccol,'#ffffff'],'circle-stroke-width':['case',['get','_needs'],3,2]}});
  map.addSource('draft',{type:'geojson',data:{type:'FeatureCollection',features:[]}});
  map.addLayer({id:'draft-fill',type:'fill',source:'draft',filter:['==',['geometry-type'],'Polygon'],paint:{'fill-color':'#b8334a','fill-opacity':.12}});
  map.addLayer({id:'draft-line',type:'line',source:'draft',filter:['!=',['geometry-type'],'Point'],paint:{'line-color':'#b8334a','line-width':2,'line-dasharray':[2,1]}});
  map.addLayer({id:'draft-pt',type:'circle',source:'draft',filter:['==',['geometry-type'],'Point'],paint:{'circle-radius':4,'circle-color':'#b8334a'}});
}
map.on('style.load',()=>{addOverlays();applyTime()});
let userMoved=false;
map.on('movestart',e=>{ if(e.originalEvent) userMoved=true });
new ResizeObserver(()=>{ map.resize(); if(!userMoved) map.fitBounds(BOX,{padding:12,animate:false}) }).observe(document.getElementById('map'));
drawImg('elev').then(ok=>{ if(ok&&map.isStyleLoaded()&&!map.getSource('lidar_elev')) addLayerFor(LAYERS.find(l=>l.id==='lidar_elev')) });
document.getElementById('go-focus').addEventListener('click',()=>{userMoved=true;map.fitBounds(BOX,{padding:12})});
document.getElementById('go-park').addEventListener('click',()=>{userMoved=true;map.fitBounds(PARKBOX,{padding:12})});

// ---------- base switching ----------
const tilenote=document.getElementById('tilenote');
function setBase(mode){
  baseMode=mode; tilenote.hidden=true; map.setMaxZoom(22);
  if(mode==='aerial'){ setYearA(yearA); return }
  if(mode==='topo') map.setStyle(rasterStyle(TILE('src=topo'),'Topo50 © Toitū Te Whenua LINZ, CC BY 4.0',18,8),{diff:false});
  if(mode==='sat') map.setStyle(rasterStyle(TILE('src=sat'),'Satellite 2025–26 © Toitū Te Whenua LINZ, CC BY 4.0',15,8),{diff:false});
  if(mode==='ofm') tryVector();
}
function tryVector(){
  fetch('https://tiles.openfreemap.org/styles/positron').then(r=>r.json()).then(st=>{if(baseMode==='ofm'){map.setStyle(st,{diff:false})}}).catch(()=>showBlocked());
}
let blockedTimer;
function showBlocked(){clearTimeout(blockedTimer);blockedTimer=setTimeout(()=>{tilenote.textContent='Map tiles could not load. Either the LINZ key isn’t set up for this site yet (Cloudflare variable LINZ_KEY) or LINZ is not responding.';tilenote.hidden=false},600)}
map.on('error',e=>{ const st=e&&e.error&&e.error.status; if(st===502||st===503) showBlocked() });   // missing key or LINZ down; 403/404 at the edges are normal
document.querySelectorAll('input[name=base]').forEach(r=>r.addEventListener('change',()=>setBase(r.value)));''')

# ---------- layer panel: lazy layers load when ticked
a = find("row.querySelector('input').addEventListener('change',e=>{")
rep(a, a + 3, '''    row.querySelector('input').addEventListener('change',e=>{
      const v=e.target.checked?'visible':'none';
      if(L.lazy&&!lazyLoaded[L.id]&&e.target.checked){ addLayerFor(L); return }
      [L.id,L.id+'__o'].forEach(id=>{if(map.getLayer(id))map.setLayoutProperty(id,'visibility',v)});
    });''')
a = find("if(L.id==='lidar_canopy'){const lg")
T[a - 1] = T[a - 1].replace("if(L.id==='lidar_canopy')", "if(L.kind==='canopy')")

# ---------- popups
a = find('function popupHTML(id,p){')
b = find('return `<span class="src">${src}</span><b>${esc(b)}</b>${x}`;', a) + 1
rep(a, b, r'''function popupHTML(id,p){
  const L=LAYERS.find(l=>l.id===id); const src=L?esc(L.label)+' · '+esc(PUB[L.pub][0]):'';
  let b='',x='';
  const yn=(k,v)=>v&&v!=='Unknown'?`${k}: ${esc(v)}<br>`:'';
  switch(id){
    case 'inat_obs': case 'inat_conifers': b=p.name; x=`<i>${esc(p.sci)}</i><br>${esc(p.date)} · ${esc(p.grade==='research'?'Research grade':p.grade==='needs_id'?'Needs ID':'Casual')}${p.obscured?'<br>Location blurred':''}<br>Licence: ${esc((p.lic||'none').toUpperCase())}<br><a href="${esc(p.url)}" target="_blank" rel="noopener">Open on iNaturalist</a>`;break;
    case 'wa_tracks': b=p.name||'Track'; x=yn('Walking',p.walk)+yn('Biking',p.bike)+yn('Horses',p.horse)+yn('Vehicles',p.vehicle)+yn('Dogs',p.dogs)+yn('Status',p.status)+(p.conditions?esc(p.conditions):'');break;
    case 'doc_tracks': b=p.name||'DOC track'; x=esc(p.kind||p.type||'');break;
    case 'doc_huts': b=String(p.name||'Hut').replace(/\s*\(H\)\s*$/,''); x=esc(p.kind||'');break;
    case 'doc_campsites': case 'doc_roads': b=p.name||L.label; x=esc(p.kind||'');break;
    case 'doc_park': b='Ruahine Forest Park'; x='Conservation park, '+Number(p.ha||95266).toLocaleString('en-NZ')+' ha';break;
    case 'wa_access_land': case 'wa_reserves': b=p.common_name||p.paa_type||'Public access land'; x=[p.paa_type,p.managed_by?'Managed by '+p.managed_by:'',p.public_access==='yes'?'Public access':''].filter(Boolean).map(esc).join('<br>');break;
    case 'wa_road_parcels': b='Legal road'; x=(p.managed_by?'Managed by '+esc(p.managed_by)+'<br>':'')+'Open to walk even where it isn’t formed. Check the line on the ground before crossing farmland.';break;
    case 'wa_easements': b=p.common_name||'Walking access easement'; x=esc(p.managed_by||'');break;
    case 'lidar_contours': b='Ground height '+p.elev+' m'; x='Above sea level, from 2023–24 LiDAR';break;
    case 'lidar_canopy': b='Canopy '+p.label+' tall'; x='From 2023–24 LiDAR, before the 2024–25 harvest';break;
    default: b=id;
  }
  return `<span class="src">${src}</span><b>${esc(b)}</b>${x}`;
}''')
a = find("const CLICK_ORDER=[")
T[a - 1] = "const CLICK_ORDER=['ann-pt','ann-line','ann-fill','doc_huts','doc_campsites','inat_conifers','inat_obs','wa_easements','wa_tracks','doc_tracks','doc_roads','lidar_contours','lidar_canopy','wa_road_parcels','wa_reserves','wa_access_land','doc_park'];"
a = find("const ids=CLICK_ORDER.filter(id=>map.getLayer(id)&&map.getLayoutProperty(id,'visibility')!=='none'&&![")
T[a - 1] = "  const ids=CLICK_ORDER.filter(id=>map.getLayer(id)&&map.getLayoutProperty(id,'visibility')!=='none'&&!['doc_park','wa_access_land','wa_reserves','lidar_canopy'].includes(id));"

# ---------- drawing form with tasks
a = find("const form=document.getElementById('annform'), cat=document.getElementById('a-cat');")
rep(a, a + 1, r'''const form=document.getElementById('annform'), cat=document.getElementById('a-cat'), taskSel=document.getElementById('a-task');
cat.innerHTML=Object.keys(CATS).filter(c=>c!=='Example').map(c=>`<option value="${esc(c)}">${esc(CATLABEL[c]||c)}</option>`).join('');
// Desktop tasks: those marked desktop_only (drawn areas). Their fields are checked by the server like phone records.
const DTASKS=(SITE_CFG.tasks||[]).filter(t=>t.desktop_only);
taskSel.innerHTML=DTASKS.map(t=>`<option value="${esc(t.id)}">${esc(t.label)}</option>`).join('')+'<option value="">Note (title and category only)</option>';
function renderTaskFields(){
  const t=DTASKS.find(x=>x.id===taskSel.value), box=document.getElementById('a-fields');
  document.getElementById('a-cat-wrap').hidden=!!t;
  box.innerHTML=!t?'':t.fields.map(fd=>{
    const id='tf-'+fd.id, lab=esc(fd.label)+(fd.required?'':' <span class="hint">(optional)</span>');
    if(fd.type==='choice') return `<label>${lab}<select id="${id}">${fd.required?'':'<option value=""></option>'}${fd.options.map(o=>`<option>${esc(o)}</option>`).join('')}</select></label>`;
    if(fd.type==='date') return `<label>${lab}<input type="date" id="${id}"></label>`;
    if(fd.type==='number') return `<label>${lab}<input type="number" id="${id}" min="${fd.min??''}" max="${fd.max??''}"></label>`;
    return `<label>${lab}<input id="${id}" maxlength="${fd.max||80}"></label>`;
  }).join('');
}
taskSel.addEventListener('change',renderTaskFields);
function taskTitle(t,fields,fallback){
  return (t.title||'{title}').replace(/\{(\w+)\}/g,(m,k)=>k==='title'?fallback:(fields[k]??'')).replace(/[:×(]\s*\)?\s*$/,'').replace(/:\s*$/,'').trim()||fallback||t.label;
}''')
a = find("form.hidden=false; document.getElementById('a-title').value='';")
T[a - 1] = T[a - 1].replace("form.hidden=false;", "form.hidden=false; taskSel.value=(keep==='area'&&DTASKS.length)?DTASKS[0].id:''; renderTaskFields();")
a = find("form.addEventListener('submit',e=>{")
b = find("addFeatures([f]).then(ok=>", a) + 1
rep(a, b, r'''form.addEventListener('submit',e=>{
  e.preventDefault(); if(!pending) return;
  const byv=document.getElementById('a-by').value.trim(); try{localStorage.setItem('map-by',byv)}catch(e){}
  const t=DTASKS.find(x=>x.id===taskSel.value), titleIn=document.getElementById('a-title').value.trim();
  const props={id:'a'+Date.now().toString(36),cat:cat.value,note:document.getElementById('a-note').value.trim(),by:byv,added:new Date().toISOString().slice(0,10)};
  if(t){
    const fields={};
    for(const fd of t.fields){ const el=document.getElementById('tf-'+fd.id); const v=el?el.value.trim():'';
      if(!v){ if(fd.required){amsg.textContent=`“${fd.label}” is needed.`;el&&el.focus();return} continue }
      fields[fd.id]=fd.type==='number'?Number(v):v; }
    props.task=t.id; props.fields=fields; props.meta={via:'desktop'};
    const sc=(t.fields.find(fd=>fd.sets_category)||{}).sets_category; props.cat=(sc&&sc[fields.status])||t.category||props.cat;
    props.title=taskTitle(t,{...fields,name:fields.name||titleIn},titleIn)||'Untitled';
    props.meta.task=t.id; props.meta.fields=fields;
  } else props.title=titleIn||'Untitled';
  if(!props.title) props.title='Untitled';
  const f={type:'Feature',properties:props,geometry:pending};
  const btn=form.querySelector('button[type=submit]'); btn.disabled=true;
  addFeatures([f]).then(ok=>{ btn.disabled=false; if(!ok) return; pending=null; form.hidden=true; verts=[]; setDraft(); cancelDraw(); });
});''')

# ---------- timeline years
a = find('// ---------- timeline ----------')
b = find('// --- compare (swipe) map')
rep(a, b, r'''// ---------- timeline ----------
const LOCAL_YEARS={};
function loadYearImg(y){
  if(LOCAL_YEARS[y]) return Promise.resolve(LOCAL_YEARS[y]);
  return new Promise((res,rej)=>{const im=new Image();im.onload=()=>{LOCAL_YEARS[y]=im;res(im)};im.onerror=()=>rej(new Error('Could not load the '+y+' photo'));im.src=HISTS[y].image});
}
function paint(canvasId,im){const c=document.getElementById(canvasId);c.width=im.naturalWidth;c.height=im.naturalHeight;c.getContext('2d').drawImage(im,0,0)}
async function setYearA(y){
  yearA=y; renderYears();
  if(baseMode!=='aerial'){ baseMode='aerial'; document.getElementById('base-aerial').checked=true }
  const old=HIST.includes(y);
  try{ if(old) paint('cv-aerial',await loadYearImg(y)); }catch(e){tilenote.textContent=e.message;tilenote.hidden=false;return}
  map.setMaxZoom(old?17.5:22);
  if(old&&!userMoved) map.fitBounds(BOX,{padding:12,animate:false});
  map.setStyle(yearStyle(y,'cv-aerial'),{diff:false});
  if(old) tilenote.textContent='The '+y+' photo covers the Kashmir Road block only.', tilenote.hidden=false; else tilenote.hidden=true;
  updateTags();
}
// --- compare (swipe) map''')
a = find('const IMGBOX2=()=>IMGBOX;')
b = find('function syncMap2()')
rep(a, b - 1, r'''function map2Style(){return yearStyle(yearB,'cv-b')}
async function setYearB(y){
  yearB=y; renderYears();
  try{ if(HIST.includes(y)) paint('cv-b',await loadYearImg(y));
    if(map2) map2.setStyle(map2Style(),{diff:false});
  }catch(e){tilenote.textContent=e.message;tilenote.hidden=false}
  updateTags();
}''')
a = find("    try{paint('cv-b',await loadYearImg(yearB))}catch(e){}")
T[a - 1] = "    try{ if(HIST.includes(yearB)) paint('cv-b',await loadYearImg(yearB)) }catch(e){}"
a = find("  let h=YEARS.map(y=>`${y===HIST[0]?'<span class=\"histlab\">Historical</span>':''}${y===2013?'<span class=\"sep\"></span>':''}")
T[a - 1] = T[a - 1].replace("${y===2013?'<span class=\"sep\"></span>':''}", "${y===LINZY[0]&&HIST.length?'<span class=\"sep\"></span>':''}").replace("(baseMode==='aerial'||baseMode==='linz')", "baseMode==='aerial'")
a = find("document.querySelectorAll('input[name=base]').forEach(r=>r.addEventListener('change',()=>{ renderYears();")
T[a - 1] = "document.querySelectorAll('input[name=base]').forEach(r=>r.addEventListener('change',()=>{ renderYears(); if(comparing&&r.value!=='aerial') toggleCompare() }));"

# ---------- date filter start
a = find('const M0=new Date(2013,8,1);')
T[a - 1] = "const M0=(()=>{const d=(DATA.inat_obs.features.map(f=>f.properties.date).filter(Boolean).sort()[0]||'2010-01-01');return new Date(+d.slice(0,4),+d.slice(5,7)-1,1)})();"

# ---------- embed
a = find("const EMBED_LAYERS=[")
T[a - 1] = "const EMBED_LAYERS=['doc_park','wa_tracks','doc_tracks','doc_huts','doc_campsites','wa_access_land','wa_road_parcels','wa_easements','inat_conifers','inat_obs','lidar_contours','lidar_canopy'];"
a = find("  if(baseMode==='aerial'||baseMode==='linz'){ q.set('base','aerial'); q.set('year',yearA) } else q.set('base','street');")
T[a - 1] = "  if(baseMode==='aerial'){ q.set('base','aerial'); q.set('year',yearA) } else q.set('base',baseMode==='ofm'?'topo':baseMode);"

# ---------- findings
a = find('// ---------- findings ----------')
b = find('</script>', a) - 1
rep(a, b, r'''// ---------- findings: wilding work totals from the drawn areas ----------
function ringArea(r){ // spherical polygon area in m² (good enough at this scale)
  let s=0; const R=6378137, rad=Math.PI/180;
  for(let i=0;i<r.length-1;i++){ const [x1,y1]=r[i],[x2,y2]=r[i+1]; s+=(x2-x1)*rad*(2+Math.sin(y1*rad)+Math.sin(y2*rad)) }
  return Math.abs(s*R*R/2);
}
function renderTally(){
  const by={}; ANN.features.filter(f=>f.geometry&&f.geometry.type==='Polygon').forEach(f=>{ const c=f.properties.cat; const a=ringArea(f.geometry.coordinates[0])/1e4; by[c]=by[c]||{ha:0,n:0}; by[c].ha+=a; by[c].n++ });
  const pts=ANN.features.filter(f=>f.properties.meta&&f.properties.meta.task==='wilding-found');
  const pines=pts.reduce((s,f)=>s+(+((f.properties.meta.fields||{}).count)||1),0);
  const card=(c,ha,txt)=>`<div><span class="k" style="color:${CATS[c]}">${ha.toLocaleString('en-NZ',{maximumFractionDigits:1})} ha</span><b>${esc(CATLABEL[c]||c)}</b><p>${txt}</p></div>`;
  const g=c=>by[c]||{ha:0,n:0};
  const wa=g('Work area'), cl=g('Cleared'), td=g('To do'), rg=g('Regrowth');
  const pct=wa.ha?` (${Math.round(cl.ha/wa.ha*100)}% of the work area)`:'';
  document.getElementById('tally').innerHTML= (wa.n||cl.n||td.n||rg.n)
   ? card('Work area',wa.ha,`${wa.n} outline${wa.n===1?'':'s'} drawn.`)+card('Cleared',cl.ha,`${cl.n} area${cl.n===1?'':'s'}${pct}.`)+card('To do',td.ha,`${td.n} area${td.n===1?'':'s'} still to clear.`)+card('Regrowth',rg.ha,`${rg.n} area${rg.n===1?'':'s'} with pines coming back. ${pines} pine${pines===1?'':'s'} recorded in the field.`)
   : `<div><b>Nothing drawn yet</b><p>Use Area under the map, choose “Wilding area” and a status. The totals appear here, and print with the page.</p></div>`;
}
const _ra=refreshAnnSource; refreshAnnSource=function(){ _ra(); renderTally() };
renderTally();
const inat=DATA.inat_obs.features.concat(DATA.inat_conifers.features), nc=inat.filter(f=>(f.properties.lic||'').includes('nc')).length;
const tb=document.querySelector('#ltable tbody');
LAYERS.forEach(L=>{
  const P=PUB[L.pub]; const lic=L.pub==='inat'?`<span class="lic-warn">${nc} of ${inat.length} are non‑commercial</span>`:(/not stated/i.test(P[2])?`<span class="lic-warn">${P[2]}</span>`:P[2]);
  const tr=document.createElement('tr');
  tr.innerHTML=`<td><b>${L.label}</b></td><td><a href="${P[1]}" target="_blank" rel="noopener">${P[0]}</a><br><span class="hint mono">${P[1].replace('https://','')}</span></td><td>${lic}</td><td class="num">${L.lazy?'on demand':(L.countText||L.count.toLocaleString('en-NZ'))}</td><td>${esc(L.cov)}</td><td>${L.why}</td>`;
  tb.appendChild(tr);
});
[['Aerial photos, '+LINZY.join(', '),'Hawke’s Bay rural aerial surveys (east) with the nearest Manawatū‑Whanganui survey (west), served full detail through the site.'],
 ['Aerial photos, '+HIST.join(', '),'Older surveys from the LINZ imagery archive, cut to the Kashmir Road block. 1980 shows no plantation; 1995 shows it newly planted.'],
 ['Topo map and 10 m satellite','NZ Topo50 (gridless) and the 2025–26 national satellite mosaic, for the whole park.']].forEach(([n,w])=>{
  const tr=document.createElement('tr'); tr.innerHTML=`<td><b>${n}</b></td><td><a href="https://www.linz.govt.nz" target="_blank" rel="noopener">Toitū Te Whenua LINZ</a><br><span class="hint mono">www.linz.govt.nz</span></td><td>CC BY 4.0</td><td class="num">tiles</td><td>${n.startsWith('Topo')?'Park':'Block / east'}</td><td>${w}</td>`; tb.appendChild(tr) });
{ const tr=document.createElement('tr');
  tr.innerHTML=`<td><b>Species suggestions (phone form)</b></td><td><a href="https://github.com/Waikato/aotearoa-species-classifier" target="_blank" rel="noopener">TAIAO, University of Waikato and University of Canterbury</a><br><span class="hint mono">github.com/Waikato/aotearoa-species-classifier</span></td><td><span class="lic-warn">CC BY-NC 4.0 (non‑commercial)</span></td><td class="num">14,991 species</td><td>Phone</td><td>Aotearoa Species Classifier. Suggests the most likely species from a photo, on the phone and without signal once downloaded. Knows the main wilding conifers. Used with permission from Prof. Eibe Frank.</td>`;
  tb.appendChild(tr); }
document.getElementById('attrib').innerHTML=`Data: <a href="https://www.doc.govt.nz" target="_blank" rel="noopener">Department of Conservation</a> (CC BY 4.0); <a href="https://www.herengaanuku.govt.nz" target="_blank" rel="noopener">Herenga ā Nuku Aotearoa, the Outdoor Access Commission</a>; sightings from <a href="https://inaturalist.nz" target="_blank" rel="noopener">iNaturalist NZ</a> observers under each record's licence. Downloaded ${new Date('2026-10-26').toLocaleDateString('en-NZ')}. Aerial photos, Topo50, satellite imagery and LiDAR © <a href="https://www.linz.govt.nz" target="_blank" rel="noopener">Toitū Te Whenua LINZ</a> (CC BY 4.0); LiDAR and older aerials via the LINZ open stores on AWS. Species suggestions in the phone form: the <a href="https://github.com/Waikato/aotearoa-species-classifier" target="_blank" rel="noopener">Aotearoa Species Classifier</a> by the TAIAO project (CC BY-NC 4.0), run with ONNX Runtime (MIT). Map built with MapLibre GL JS.`;''')

# ---------- apply, last range first
for (a, b) in sorted(LINES, reverse=True):
    T[a - 1:b] = LINES[(a, b)].split('\n')
out = '\n'.join(T)
open(os.path.join(REPO, 'scripts', 'template-ruahine.html'), 'w').write(out)

# ---------- assemble index.html
EAGER = [p for p in glob.glob(os.path.join(WORK, 'layers', '*.geojson')) if os.path.basename(p)[:-8] not in ('lidar_canopy', 'lidar_contours')]
data = {os.path.basename(p)[:-8]: json.load(open(p)) for p in EAGER}
img = {'elev': 'data:image/jpeg;base64,' + base64.b64encode(open(os.path.join(WORK, 'lidar', 'elev.jpg'), 'rb').read()).decode()}
st = json.load(open(os.path.join(WORK, 'lidar', 'stats.json')))
st['cover'] = st['cover_pct']
cfg_small = {k: CFG[k] for k in ('area', 'categories', 'tasks', 'lists') if k in CFG}
cfg_small['lists'] = {}   # pick lists aren't needed on the desktop map
page = (out.replace('/*__MAPLIBRE_CSS__*/', open(os.path.join(REPO, 'scripts', 'maplibre.css')).read())
           .replace('/*__DATA__*/{}', json.dumps(data, separators=(',', ':'), ensure_ascii=False))
           .replace('/*__IMG__*/{}', json.dumps(img))
           .replace('/*__LIDAR__*/{}', json.dumps(st))
           .replace('/*__CFG__*/{}', json.dumps(cfg_small, separators=(',', ':'), ensure_ascii=False)))
page = '<!doctype html>\n<html lang="en-NZ"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">\n' + page + '\n</html>'
open(os.path.join(REPO, 'index.html'), 'w').write(page)
print('index.html', os.path.getsize(os.path.join(REPO, 'index.html')) // 1024, 'KB')
# data/ and imagery/ for the embed, lazy layers and the timeline
for d in ('data', 'imagery'):
    for f in glob.glob(os.path.join(REPO, d, '*')): os.remove(f)
for p in glob.glob(os.path.join(WORK, 'layers', '*.geojson')): shutil.copy(p, os.path.join(REPO, 'data'))
for p in glob.glob(os.path.join(WORK, 'imagery', '*.jpg')): shutil.copy(p, os.path.join(REPO, 'imagery'))
shutil.copy(os.path.join(WORK, 'lidar', 'elev.jpg'), os.path.join(REPO, 'imagery', 'elev.jpg'))
