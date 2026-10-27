import requests
for u in ["http://mestovcislach.sk/","https://www.mestovcislach.sk/","https://mestovcislach.sk/trnava/volby","https://mestovcislach.pages.dev/","https://mestovcislach.sk/neexistuje/","https://mestovcislach.sk/sitemap.xml"]:
    try:
        r=requests.get(u,timeout=30,allow_redirects=False); print(u,r.status_code,r.headers.get("location"),r.headers.get("x-robots-tag"),r.headers.get("content-encoding"))
    except Exception as e: print(u,type(e).__name__)
r=requests.get("https://mestovcislach.sk/bratislava/volby/",headers={"Accept-Encoding":"br, gzip"},timeout=30,stream=True)
print("BA volby prenesené kB:",len(r.raw.read())//1000, r.headers.get("content-encoding"))
print("HOTOVO")
