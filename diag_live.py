import subprocess, sys, re, io, zipfile, csv
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", "scripts/requirements.txt"])
sys.path.insert(0, "scripts")
from spolocne import s
def g(u, **kw):
    try:
        r = s.get(u, timeout=90, **kw); return r
    except Exception as e:
        print("ERR", u, str(e)[:120]); return None
# prezident 2024
for u in ["https://volby.statistics.sk/prez/prez2024/sk/", "https://volby.statistics.sk/prez/prez2024/sk/index.html", "https://volby.statistics.sk/prez/prez2024/", "https://volby.statistics.sk/tree-sk.html", "https://volby.statistics.sk/opendata/prez/2024/PREZ2024_1K_SK_tab02d.csv", "https://volby.statistics.sk/opendata/prez/2024/PREZ2024_SK_tab02d.csv"]:
    r = g(u)
    if r is not None:
        print(u, r.status_code, len(r.text), sorted(set(x for x in re.findall(r'(?:href|src)="([^"]+)"', r.text) if re.search(r"prez|PREZ|\.csv|\.zip|xlsx", x)))[:40])
# STATdata – filter rokov
B = "https://statdata.statistics.sk/public/api/dc/opendata/cube/dataset/om7052rr"
for cols in ["e_year,ASC,2024,2025", "e_year,ASC,2025", "e_year,ASC,2024|2025", "e_year,DESC,all"]:
    u = f"{B}/rows/e_nuts15,ASC,all~e_indic,ASC,all~e_sex,ASC,all/columns/{cols}/context/e_unit,ASC,all"
    r = g(u, params={"type": "CSV", "lang": "SK"})
    if r is None: continue
    c = r.content
    if c[:2] == b"PK":
        z = zipfile.ZipFile(io.BytesIO(c)); c = z.read(z.namelist()[0])
    rows = list(csv.DictReader(io.StringIO(c.decode("utf-8-sig", "replace")))) if r.ok else []
    print(cols, r.status_code, len(rows), sorted({x.get("e_year") for x in rows})[:6], r.text[:150] if not r.ok else "")
    v = [x for x in rows if x["e_nuts15"].strip() == "Vígľaš" and x["e_sex"] == "Spolu"][:12]
    for x in v: print("   ", x)
# distribučky
for u in ["https://www.zsdis.sk/Uvod/Odstavky", "https://www.zsdis.sk/odstavky", "https://www.ssd.sk/odstavky", "https://www.ssd.sk/planovane-odstavky", "https://www.vsds.sk/odstavky", "https://www.vsds.sk/planovane-odstavky"]:
    r = g(u, allow_redirects=True)
    if r is not None:
        print(u, r.status_code, r.url, len(r.text), re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", r.text))[:300])
        print("   ", sorted(set(x for x in re.findall(r'(?:href|src|data-url|action)="([^"]+)"', r.text) if re.search(r"odstav|prerus|api|json|xml|rss", x, re.I)))[:30])
# ŽSR GTFS
r = g("https://www.zsr.sk/files/pre-cestujucich/cestovny-poriadok/gtfs/gtfs.zip")
if r is not None:
    print("gtfs", r.status_code, len(r.content), r.content[:2])
    if r.content[:2] == b"PK":
        z = zipfile.ZipFile(io.BytesIO(r.content)); print([(n, z.getinfo(n).file_size) for n in z.namelist()])
        print(z.read("stops.txt")[:600].decode("utf-8", "replace"))
        print(z.read("calendar.txt")[:300].decode("utf-8", "replace") if "calendar.txt" in z.namelist() else "")
print("HOTOVO")
