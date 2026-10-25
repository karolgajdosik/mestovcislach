import requests, time
H={"User-Agent":"Mozilla/5.0 (mestovcislach diag)"}
W="https://mestovcislach.sk"
for i in range(30):
    t=requests.get(W+"/kosice/zastupitelstvo/",headers=H,timeout=30).text
    if "2026–2030" in t: break
    time.sleep(30)
print("KE zastupiteľstvo 2026–2030:", "2026–2030" in t)
for u in ["/bratislava/volby/","/porovnanie/","/nitra/zastupitelstvo/","/kosice/volby/"]:
    t=requests.get(W+u,headers=H,timeout=30).text; print(u, "Konečné" in t or "2026–2030" in t or "obhájil" in t)
print("HOTOVO")
