import subprocess, sys, shutil
from datetime import datetime, timedelta, timezone
subprocess.run("pip install -q shapely pyarrow", shell=True)
subprocess.run("git fetch -q --depth=1 origin main && git checkout origin/main -- scripts src/mesta.json data", shell=True, check=True)
shutil.copy("test/odber_email.py", "scripts/odber_email.py")
sys.path.insert(0, "scripts")
import odber_email as o
od = datetime.now(timezone.utc) - timedelta(days=7)
for k in ("bratislava", "ruzinov", "kosice", "zilina"):
    n = o.novinky(k, od)
    kat = {}
    for p in n: kat[p["kategoria"]] = kat.get(p["kategoria"], 0) + 1
    html = o.email(o.kanaly()[k], k, n)
    print(k, "noviniek za 7 dní:", len(n), kat, "| HTML", len(html), "znakov, odhlásenie:", "{{ unsubscribe }}" in html)
shutil.copy("scripts/odber_email.py", "diag/x.py") if False else None
open("diag/ukazka.html", "w").write(o.email("Bratislava – Ružinov", "ruzinov", o.novinky("ruzinov", od)))
print("HOTOVO")
