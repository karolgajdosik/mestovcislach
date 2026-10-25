import requests, time
H={"User-Agent":"Mozilla/5.0 (mestovcislach diag)"}
W="https://mestovcislach.sk"
for i in range(30):
    t=requests.get(W+"/bratislava/volby/",headers=H,timeout=30).text
    if "Vagač" in t: break
    time.sleep(30)
print("BA starostovia:", "Vagač" in t, "Chren" in t)
for s in ["trnava","trencin","nitra","zilina","banska-bystrica","presov","kosice"]:
    t=requests.get(f"{W}/{s}/volby/",headers=H,timeout=30).text
    print(s, "Konečné" in t or "zvolený" in t, "Priebežné" in t)
r=requests.get(W+"/og/volby-trnava.png",headers=H,timeout=30); print("og trnava", r.status_code, len(r.content))
print("HOTOVO")
