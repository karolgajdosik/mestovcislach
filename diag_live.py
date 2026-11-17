import requests, math
def tile(lat,lon,z):
    n=2**z; x=int((lon+180)/360*n); y=int((1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*n); return x,y
H={"Origin":"https://mestovcislach.sk","User-Agent":"Mozilla/5.0 (compatible; mestovcislach.sk; info@mestovcislach.sk)"}
for z in (13,16,18,19):
    x,y=tile(48.1435,17.1077,z)
    for host in ("ofmozaika","ofmozaika2c"):
        u=f"https://{host}.tiles.freemap.sk/{z}/{x}/{y}.jpg"
        try:
            r=requests.get(u,headers=H,timeout=30); print(host,z,r.status_code,r.headers.get("content-type"),len(r.content),"ACAO=",r.headers.get("access-control-allow-origin"),"cache=",r.headers.get("cache-control"))
        except Exception as e: print(host,z,"ERR",e)
print("HOTOVO")
