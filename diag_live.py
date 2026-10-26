import requests
H={"User-Agent":"Mozilla/5.0 (mestovcislach diag)"}
for u in ["https://mestovcislach.sk/kosice/volby","https://mestovcislach.sk/kosice/volby/","https://www.mestovcislach.sk/","http://mestovcislach.sk/","https://mestovcislach.sk/index.html","https://mestovcislach-sk.pages.dev/"]:
    try:
        r=requests.get(u,headers=H,timeout=30,allow_redirects=False); print(u, r.status_code, r.headers.get("location"), r.headers.get("x-robots-tag"))
    except Exception as e: print(u, "ERR", type(e).__name__)
print("HOTOVO")
