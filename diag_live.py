# Obsah balíkov OSO/OSK 2026 – názvy súborov, počty riadkov a hlavičky (bez hodnôt s menami).
import io, zipfile, requests, subprocess, sys
from openpyxl import load_workbook
s = requests.Session(); s.headers["User-Agent"] = "mestovcislach.sk diag"
for u in ("https://volbysr.sk/oso/files/OSO2026_SK_xlsx.zip", "https://volbysr.sk/osk/files/OSK2026_SK_xlsx.zip", "https://volbysr.sk/oso/files/OSO2026_SK_csv.zip"):
    r = s.get(u, timeout=120); print(u, r.status_code, r.headers.get("Last-Modified"), len(r.content))
    if r.status_code != 200 or not u.endswith("xlsx.zip"): continue
    zf = zipfile.ZipFile(io.BytesIO(r.content))
    for n in zf.namelist():
        rows = list(load_workbook(io.BytesIO(zf.read(n)), read_only=True).worksheets[0].iter_rows(values_only=True))
        hl = next((r_ for r_ in rows[:10] if r_ and sum(1 for x in r_ if x) >= 3), rows[0] if rows else ())
        print("  ", n, "riadkov", len(rows), "| hlavička:", [str(x)[:30] for x in hl if x][:12])
subprocess.run("git fetch -q --depth=1 origin main && git checkout origin/main -- data scripts src/mesta.json", shell=True)
sys.path.insert(0, "scripts")
import zber_komunalne as zk
t, u = zk.stiahni(["https://volbysr.sk/oso/files/OSO2026_SK_csv.zip", "https://volbysr.sk/oso/files/OSO2026_SK_xlsx.zip"])
print("zber číta tabuľky:", sorted(t) if t else None)
if t and t.get("tab0a"):
    print("kandidáti na primátora BA:", sum(1 for r in t["tab0a"] if zk.kod(r["OBEC"]) == zk.MESTO), "| stĺpce tab0a:", [k for k in t["tab0a"][0] if k not in ("MENO", "PRIEZVISKO", "TITUL")])
