import requests, zipfile, io, os
H={"User-Agent":"Mozilla/5.0"}
r=requests.get("https://www.arcgis.com/sharing/rest/content/items/ba941d7bc56a462684a261d4f35ce17d/data",headers=H,timeout=300)
z=zipfile.ZipFile(io.BytesIO(r.content))
os.makedirs("diag/ke",exist_ok=True)
for n in z.namelist():
    t=z.read(n).decode("cp1250",errors="replace")
    open(f"diag/ke/{n}","w").write(t if n!="ZASSPOJE.TXT" else "".join(t.splitlines(True)[:3000]))
m=requests.get("https://www.arcgis.com/sharing/rest/content/items/ba941d7bc56a462684a261d4f35ce17d",params={"f":"json"},headers=H,timeout=60).json()
print({k:m.get(k) for k in ("title","modified","snippet","licenseInfo")})
print("HOTOVO")
