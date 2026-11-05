import requests, io, zipfile, csv, collections
H = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/130 Safari/537.36"}
B = "https://statdata.statistics.sk/public/api/dc/opendata/cube/dataset/zp3804rr"
path = "/rows/e_nuts15,ASC,all~e_ewc,ASC,all/columns/e_year,ASC,all/context/e_indic,ASC,all~e_unit,ASC,all"
r = requests.get(B + path, params={"type": "CSV", "lang": "SK"}, headers=H, timeout=600)
print(r.status_code, len(r.content), r.headers.get("content-type"))
c = r.content
if c[:2] == b"PK":
    z = zipfile.ZipFile(io.BytesIO(c)); c = z.read(z.namelist()[0])
t = c.decode("utf-8-sig", "replace")
print(t[:800].replace("\n", " | "))
rows = list(csv.DictReader(io.StringIO(t)))
print(len(rows), list(rows[0].keys()) if rows else None)
if rows:
    for k in rows[0]:
        v = collections.Counter(x[k] for x in rows); print(k, len(v), list(v)[:8])
print("HOTOVO")
