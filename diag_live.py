import requests
H={"User-Agent":"Mozilla/5.0 (compatible; mestovcislach.sk; info@mestovcislach.sk)","Origin":"https://mestovcislach.sk"}
bbox="2073000,6224000,2075000,6226000"  # Prievidza približne (EPSG:3857)
for n,u in [
 ("ortofoto WMS 3857","https://zbgisws.skgeodesy.sk/zbgis_ortofoto_wms/service.svc/get?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS=1&STYLES=&CRS=EPSG:3857&BBOX="+bbox+"&WIDTH=256&HEIGHT=256&FORMAT=image/jpeg"),
 ("ortofoto WMS caps","https://zbgisws.skgeodesy.sk/zbgis_ortofoto_wms/service.svc/get?SERVICE=WMS&REQUEST=GetCapabilities"),
 ("terrarium","https://s3.amazonaws.com/elevation-tiles-prod/terrarium/12/2283/1414.png"),
 ("openfreemap style","https://tiles.openfreemap.org/styles/liberty"),
]:
    try:
        r=requests.get(u,headers=H,timeout=60)
        print(n,r.status_code,r.headers.get("content-type"),len(r.content),"ACAO=",r.headers.get("access-control-allow-origin"))
        if "caps" in n:
            import re; print("  vrstvy:",re.findall(r"<Name>([^<]+)</Name>",r.text)[:10], "3857" in r.text)
    except Exception as e: print(n,"ERR",e)
print("HOTOVO")
