import urllib.request, time, json
time.sleep(240)
for u in ["/manifest.webmanifest","/sw.js","/offline/","/icon-512.png","/apple-touch-icon.png"]:
    try:
        r=urllib.request.urlopen("https://mestovcislach.sk"+u,timeout=30)
        b=r.read()
        print(u, r.status, r.headers.get("content-type"), r.headers.get("cache-control"), len(b))
    except Exception as e: print(u,"ERR",e)
h=urllib.request.urlopen("https://mestovcislach.sk/",timeout=30).read().decode()
print("manifest link:", 'rel="manifest"' in h, "sw reg:", "serviceWorker" in h)
