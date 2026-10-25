import requests, zipfile, io
H={"User-Agent":"Mozilla/5.0 (mestovcislach diag)"}
for u in ["https://volbysr.sk/oso/files/OSO2026_SK_xlsx.zip","https://volbysr.sk/osk/files/OSK2026_SK_xlsx.zip"]:
    r=requests.get(u,headers=H,timeout=120); print(u.split('/')[-1], r.headers.get("last-modified"), sorted(zipfile.ZipFile(io.BytesIO(r.content)).namelist()))
for p in ["oso/json/tab06e1/500011.json","oso/json/tab07/500011.json","oso/json/tab07/582000.json","oso/json/dateSK.json","osk/json/dateSK.json"]:
    r=requests.get("https://volbysr.sk/"+p,headers=H,timeout=60); print(p, r.status_code, r.text[:200] if r.ok else "")
print("HOTOVO")
