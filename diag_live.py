import requests, math
def tile(lat,lon,z):
    n=2**z; x=int((lon+180)/360*n); y=int((1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*n); return x,y
H={"Origin":"https://mestovcislach.sk","User-Agent":"Mozilla/5.0 (compatible; mestovcislach.sk; info@mestovcislach.sk)"}
for z in (12,14,15,16,17):
    x,y=tile(48.1435,17.1077,z)
    u=f"https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless_3857/default/g/{z}/{y}/{x}.jpg"
    r=requests.get(u,headers=H,timeout=30); print(z,r.status_code,r.headers.get("content-type"),len(r.content),"ACAO=",r.headers.get("access-control-allow-origin"))
r=requests.get("https://tiles.maps.eox.at/wmts/1.0.0/WMTSCapabilities.xml",timeout=60).text
import re
i=r.find("<ows:Identifier>s2cloudless_3857</ows:Identifier>"); print(r[max(0,i-600):i+100].replace("\n"," ")[:800])
print("HOTOVO")
