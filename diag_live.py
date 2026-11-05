import requests, io, zipfile
H = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/130 Safari/537.36"}
B = "https://statdata.statistics.sk/public/api/dc"
for path in ["/opendata/cube/dataset/zp3804rr/rows/e_nuts15/columns/e_ewc/context/e_year?lang=SK", "/opendata/cube/dataset/zp3804rr/rows/e_nuts15/columns/e_year/context/e_ewc?lang=SK&type=CSV"]:
    r = requests.get(B + path, headers=H, timeout=300)
    print(path, r.status_code, len(r.content), r.headers.get("content-type"), r.content[:4])
    c = r.content
    if c[:2] == b"PK":
        z = zipfile.ZipFile(io.BytesIO(c)); n = z.namelist(); c = z.read(n[0]); print("  zip", n, len(c))
    print("  ", c[:1500].decode("utf-8", "replace").replace("\n", " | "))
print("HOTOVO")
