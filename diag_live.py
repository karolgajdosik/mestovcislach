import requests, time
H={"User-Agent":"Mozilla/5.0 (mestovcislach diag)"}
W="https://mestovcislach.sk"
for i in range(40):
    x=requests.get(W+"/data/dodavatelia.json",headers=H,timeout=30).json()
    if len(x) > 6000: break
    time.sleep(30)
print("dodávateľov", len(x), "s Bratislavou", sum(1 for r in x if 'bratislava' in r[5]), "s Košicami", sum(1 for r in x if 'kosice' in r[5]))
h=requests.get(W+"/presov/",headers=H,timeout=30).text
print("menu skupiny:", "bocne-skupina" in h, "Doprava" in h)
print("volby stránka:", requests.get(W+"/kosice/volby/",headers=H,timeout=30).status_code)
print("HOTOVO")
