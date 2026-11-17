import requests, json
H={"Origin":"https://mestovcislach.sk","User-Agent":"Mozilla/5.0 (compatible; mestovcislach.sk; info@mestovcislach.sk)"}
B="https://zbgis.skgeodesy.sk/zbgis/rest/services/Ortofoto/MapServer"
try:
    r=requests.get(B+"?f=json",headers=H,timeout=40); print("info",r.status_code,"ACAO=",r.headers.get("access-control-allow-origin"))
    j=r.json(); ti=j.get("tileInfo") or {}
    print("wkid",j.get("spatialReference"),"singleFused",j.get("singleFusedMapCache"),"rows",ti.get("rows"),"lods",[(l["level"],round(l["resolution"],3)) for l in ti.get("lods",[])][:25],"origin",ti.get("origin"))
    print("copyright",j.get("copyrightText"),"layers",[l.get("name") for l in j.get("layers",[])][:10], "caps",j.get("capabilities"), "export?", "exportTilesAllowed" in j)
except Exception as e: print("ERR",e)
for u in [B+"/tile/16/22662/35576", B+"/export?bbox=1904000,6131000,1906000,6133000&bboxSR=3857&imageSR=3857&size=512,512&format=jpg&f=image"]:
    try:
        r=requests.get(u,headers=H,timeout=40); print(u[-60:],r.status_code,r.headers.get("content-type"),len(r.content),"ACAO=",r.headers.get("access-control-allow-origin"))
    except Exception as e: print("ERR",u[-40:],e)
print("HOTOVO")
