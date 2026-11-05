import requests, io, zipfile
H = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/130 Safari/537.36"}
B = "https://statdata.statistics.sk/public/api/dc"
for t in ["CSV", "JSON", "ODS"]:
    r = requests.get(f"{B}/opendata/cube/dataset/zp3804rr/download", params={"type": t, "lang": "SK"}, headers=H, timeout=300)
    print(t, r.status_code, len(r.content), r.content[:4])
    if r.content[:2] == b"PK":
        z = zipfile.ZipFile(io.BytesIO(r.content)); n = z.namelist(); print("  ", n, [z.getinfo(x).file_size for x in n])
        d = z.read(n[0])[:700]; print("  ", d.decode("utf-8", "replace").replace("\n", " | "))
for path in ["/opendata/cube/dataset/zp3804rr/rows/e_nuts15/columns/e_ewc/context/e_year", "/opendata/cube/dataset/download-url?dataCubePublicId=zp3804rr&type=CSV&lang=SK"]:
    r = requests.get(B + path, headers=H, timeout=300)
    print(path, r.status_code, len(r.content), r.text[:500].replace("\n", " "))
print("HOTOVO")
