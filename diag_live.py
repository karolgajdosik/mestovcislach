import requests,time
r=requests.get("https://mestovcislach.sk/api/sutaz",timeout=30).json(); print("súťaž",r)
for u in ["https://data.statistics.sk/api/v2/collection?lang=sk","https://data.statistics.sk/","https://datacube.statistics.sk/"]:
    try: x=requests.get(u,timeout=25); print(u,x.status_code,len(x.content))
    except Exception as e: print(u,type(e).__name__)
for u in ["/","/trnava/","/bratislava/","/sutaz/","/rozpocty-2027/","/volby-2026/","/kosice/zastupitelstvo/","/api/vystrahy","/api/ovzdusie?mesto=trnava","/api/dunaj"]:
    t=time.time(); x=requests.get("https://mestovcislach.sk"+u,timeout=30); print(u,x.status_code,round(time.time()-t,2))
print("HOTOVO")
