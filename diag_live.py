import requests, zipfile, io
H={"User-Agent":"Mozilla/5.0 (mestovcislach diag)"}
W="https://mestovcislach.sk"
r=requests.get("https://volbysr.sk/oso/files/OSO2026_SK_xlsx.zip",headers=H,timeout=120)
print("balík", r.headers.get("last-modified"), sorted(zipfile.ZipFile(io.BytesIO(r.content)).namelist()))
for u in ["/","/porovnanie/","/bratislava/volby/","/bratislava/zastupitelstvo/"]+[f"/{s}/volby/" for s in ["trnava","nitra","trencin","zilina","banska-bystrica","presov","kosice"]]+[f"/{s}/zastupitelstvo/" for s in ["kosice","nitra"]]:
    t=requests.get(W+u,headers=H,timeout=30); print(u, t.status_code, "Priebežné" in t.text, "100 %" in t.text or "Konečné" in t.text)
print("HOTOVO")
