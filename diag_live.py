import requests
H={"User-Agent":"Mozilla/5.0 (mestovcislach diag)"}
for u in ["/manifest.webmanifest","/sw.js","/offline/","/icon-512.png","/apple-touch-icon.png"]:
    r=requests.get("https://mestovcislach.sk"+u,headers=H,timeout=30)
    print(u, r.status_code, r.headers.get("content-type"), r.headers.get("cache-control"), len(r.content))
h=requests.get("https://mestovcislach.sk/",headers=H,timeout=30).text
print("manifest link:", 'rel="manifest"' in h, "sw reg:", "serviceWorker" in h)
