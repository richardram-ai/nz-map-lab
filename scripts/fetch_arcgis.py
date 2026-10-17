import json, sys, urllib.request, urllib.parse, os, re, html
S,N,W,E = -40.354261,-40.345252,175.613645,175.625433
PN="https://services.arcgis.com/Fv0Tvc98QEDvQyjL/arcgis/rest/services/"
HZ="https://services1.arcgis.com/VuN78wcRdq1Oj69W/arcgis/rest/services/"
EG="https://services.arcgis.com/XTtANUDT8Va4DLwI/ArcGIS/rest/services/"
svcs = {
 "pncc":[ "PARKS_NotableTrees","PARKS_Reserves","DISTRICTPLAN_PlanningZones","DISTRICTPLAN_FLOODPRONEAREAS","PNCC_District_Plan_DISTRICTPLAN_Ponding_Areas","DISTRICTPLAN_Overlays","DISTRICTPLAN_HeritageSites","PROPERTY_Parcels","PARKS_WALKCYCLE","NZVD2016_STORM_MAINS","STORM_CATCHMENT","PARKS_PLAYGROUNDS","TRANSPORT_CYCLENETWORK"],
 "hz":["Modelled_wet_extents_data_from_flood_plain_mapping_analysis","NaturalHazards_ObservedFloodingExtent","Liquefaction_Susceptibility","S_MAP_HorizonsRC","LandParcelMapData","OpenData_GroundwaterBore2","Horizons_Stream_Gauges","Public_OnePlan","Soils_Inventory_used_for_Local_Maps"],
 "eg":["New_Zealand_Land_Cover"]}
base={"pncc":PN,"hz":HZ,"eg":EG}
def get(u):
    with urllib.request.urlopen(u, timeout=90) as r: return json.load(r)
out={}
os.makedirs("raw",exist_ok=True)
for k,lst in svcs.items():
  for s in lst:
    u=base[k]+s+"/FeatureServer"
    try: meta=get(u+"?f=json")
    except Exception as e: print("ERR",s,e); continue
    lic=re.sub("<[^>]+>"," ",html.unescape(meta.get("licenseInfo") or meta.get("copyrightText") or "")).strip()
    for L in meta.get("layers",[]):
      q=dict(geometry=f"{W},{S},{E},{N}",geometryType="esriGeometryEnvelope",inSR=4326,spatialRel="esriSpatialRelIntersects",outFields="*",outSR=4326,f="geojson",resultRecordCount=4000)
      try: gj=get(u+f"/{L['id']}/query?"+urllib.parse.urlencode(q))
      except Exception as e: print("ERR",s,L['name'],e); continue
      n=len(gj.get("features",[]))
      name=f"{k}__{s}__{L['id']}"
      print(f"{n:5d}  {k} {s} / {L['name']}")
      if n:
        json.dump(gj,open(f"raw/{name}.geojson","w"))
        out[name]=dict(service=u,layer=L['name'],count=n,licence=lic[:300],copyright=meta.get("copyrightText",""))
json.dump(out,open("raw/_index.json","w"),indent=1)
