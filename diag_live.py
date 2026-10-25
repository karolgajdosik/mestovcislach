import requests, time, re
H={"User-Agent":"Mozilla/5.0 (mestovcislach diag)"}
for i in range(30):
    t=requests.get("https://mestovcislach.sk/bratislava/volby/",headers=H,timeout=30).text
    if "64,4" in t or "64,36" in t: break
    time.sleep(30)
print("BA 64,4 %:", "64,4" in t)
h=requests.get("https://mestovcislach.sk/",headers=H,timeout=30).text
print("úvod:", re.sub(r"<[^>]+>"," ",h[h.find('volby-2026-uvod'):h.find('volby-2026-uvod')+3000]).split()[:80])
print("HOTOVO")
