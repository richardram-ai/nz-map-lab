import json, os
from shapely.geometry import shape, mapping, box
from shapely import set_precision
D="/home/claude/map/data/"; R=D+"raw/"; O="/home/claude/map/layers/"
S,N,W,E = -40.354261,-40.345252,175.613645,175.625433
BOX=box(W,S,E,N)
def rnd(g):
    return set_precision(g, 1e-6)
def write(name, feats):
    json.dump({"type":"FeatureCollection","features":feats}, open(O+name+".geojson","w"), separators=(",",":"))
    print(name, len(feats), os.path.getsize(O+name+".geojson")//1024, "KB")
def arc(fn, keep, clip=True, rename=None):
    d=json.load(open(R+fn+".geojson")); out=[]
    for f in d["features"]:
        g=shape(f["geometry"])
        if clip: g=g.intersection(BOX)
        if g.is_empty: continue
        p={ (rename or {}).get(k,k): f["properties"].get(k) for k in keep }
        out.append({"type":"Feature","properties":p,"geometry":mapping(rnd(g))})
    return out
write("pncc_notable_trees", arc("pncc__PARKS_NotableTrees__0",["COMMON_NAME","BOTANICAL_NAME"],clip=False))
write("pncc_heritage", arc("pncc__DISTRICTPLAN_HeritageSites__0",["TYPE","BLDG_OBJECT"],clip=False))
write("pncc_playgrounds", arc("pncc__PARKS_PLAYGROUNDS__0",["PLAYGROUND_NAME","PLAYGROUND_CAT"],clip=False))
write("pncc_zones", arc("pncc__DISTRICTPLAN_PlanningZones__0",["ZONE"]))
write("pncc_parcels", arc("pncc__PROPERTY_Parcels__0",["PAR_ID","FEATURE_CODE","STATUS"]))
write("pncc_storm_mains", arc("pncc__NZVD2016_STORM_MAINS__0",["LOCATION","DIAMETER","MATERIAL","OWNER"]))
write("pncc_storm_catchment", arc("pncc__STORM_CATCHMENT__0",["NAME"]))
write("pncc_cycle", arc("pncc__TRANSPORT_CYCLENETWORK__0",["ROAD_NAME","FAC_TYPE_DESC","STATUS"]))
write("hz_flood200", arc("hz__Modelled_wet_extents_data_from_flood_plain_mapping_analysis__14",["gridcode"]))
write("hz_liquefaction", arc("hz__Liquefaction_Susceptibility__0",["LiquefactionSusceptibilityClass"]))
write("hz_smap", arc("hz__S_MAP_HorizonsRC__0",["SMU"]))
write("hz_bore", arc("hz__OpenData_GroundwaterBore2__1",["BoreID","Depth","Elevation","SWL"],clip=False))
write("hz_water_area", arc("hz__Public_OnePlan__3",["SurfaceWaterManageSubareaName","SurfaceWaterManageSubareaCode","Description"]))
write("lcdb", arc("eg__New_Zealand_Land_Cover__0",["Name_2023","Name_2018","Name_2001","Name_1996"]))
# OSM
o=json.load(open(D+"osm.json")); trees=[];roads=[];green=[];bld=[];paths=[];water=[]
for e in o["elements"]:
    t=e.get("tags",{})
    if e["type"]=="node":
        if t.get("natural")=="tree":
            trees.append({"type":"Feature","properties":{"species":t.get("species") or t.get("species:en") or t.get("genus") or t.get("leaf_type") or "", "osm":f"https://www.openstreetmap.org/node/{e['id']}"},"geometry":{"type":"Point","coordinates":[round(e["lon"],6),round(e["lat"],6)]}})
        continue
    if "geometry" not in e: continue
    coords=[(p["lon"],p["lat"]) for p in e["geometry"]]
    closed=len(coords)>3 and coords[0]==coords[-1]
    from shapely.geometry import Polygon, LineString
    g=Polygon(coords) if closed else LineString(coords)
    g=g.intersection(BOX)
    if g.is_empty: continue
    feat=lambda p:{"type":"Feature","properties":p,"geometry":mapping(rnd(g))}
    if "building" in t and closed: bld.append(feat({"building":t["building"]}))
    elif (t.get("landuse") in ("grass","recreation_ground","meadow","forest") or t.get("leisure") in ("park","garden","pitch","playground") or t.get("natural") in ("wood","scrub","grassland")) and closed:
        green.append(feat({"type":t.get("leisure") or t.get("landuse") or t.get("natural"),"name":t.get("name","")}))
    elif t.get("highway") in ("footway","path","pedestrian","cycleway","steps"): paths.append(feat({"type":t["highway"]}))
    elif t.get("highway") in ("trunk","trunk_link","primary","secondary","tertiary","residential","unclassified","living_street","service"): roads.append(feat({"type":t["highway"],"name":t.get("name","")}))
    elif "waterway" in t: water.append(feat({"type":t["waterway"],"name":t.get("name","")}))
write("osm_trees",trees); write("osm_green",green); write("osm_buildings",bld); write("osm_paths",paths); write("osm_roads",roads); write("osm_water",water)
# iNat
obs=[]
for fn in ["inat.json","inat2.json"]:
    for r in json.load(open(D+fn))["results"]:
        if not r.get("location"): continue
        la,lo=map(float,r["location"].split(","))
        tx=r.get("taxon") or {}
        obs.append({"type":"Feature","properties":{"name":tx.get("preferred_common_name") or tx.get("name") or "Unknown","sci":tx.get("name",""),"group":tx.get("iconic_taxon_name") or "Other","date":r.get("observed_on"),"grade":r.get("quality_grade"),"native":None,"obscured":r.get("obscured"),"url":r.get("uri"),"lic":r.get("license_code")},"geometry":{"type":"Point","coordinates":[round(lo,6),round(la,6)]}})
write("inat_obs",obs)
