import requests,zipfile,io,csv
B="https://statdata.statistics.sk/public/api/dc"
for i in range(3101,3125):
    k=f"pr{i}rr"
    r=requests.get(f"{B}/public/{k}/info",timeout=40)
    if r.status_code==200:
        j=r.json(); print(k,j.get("nameSk"),j.get("timePeriodTo"),j.get("zonation"))
for u in ["https://gis.geocloud.gov.sk/geoserver/uvz/ows?service=WFS&version=2.0.0&request=GetCapabilities","https://gis.geocloud.gov.sk/geoserver/mpsvrsr/ows?service=WFS&version=2.0.0&request=GetCapabilities"]:
    try: r=requests.get(u,timeout=60); print(u[:60],r.status_code,len(r.content))
    except Exception as e: print(u[:60],type(e).__name__,str(e)[:150])
print("HOTOVO")
