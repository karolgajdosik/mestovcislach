# Opakovanie zlyhaných zberov (ŠÚ SR) – len chybové riadky a súhrn, bez osobných údajov.
import subprocess, requests
subprocess.run("pip install -q shapely pyarrow", shell=True)
subprocess.run("git fetch -q --depth=1 origin main && git checkout origin/main -- data scripts src/mesta.json public/data", shell=True)
for u in ("https://data.statistics.sk/api/v2/dataset/om7101rr/SK010/2024/U/val", "https://volby.statistics.sk/opendata/", "https://volbysr.sk/oso/sk/", "https://volbysr.sk/oso/files/OSO2026_SK_xlsx.zip"):
    try:
        r = requests.get(u, timeout=60, headers={"User-Agent": "mestovcislach.sk diag"}); print(u, r.status_code, r.headers.get("content-type"), len(r.content), r.headers.get("Last-Modified"))
    except Exception as e: print(u, type(e).__name__, str(e)[:120])
for skript in ("zber_obyvatelstvo.py", "zber_volby.py", "zber_byvanie.py"):
    p = subprocess.run(["python", f"scripts/{skript}"], capture_output=True, text=True, timeout=1500)
    vystup = (p.stdout + p.stderr).splitlines()
    chyby = [l for l in vystup if any(x in l for x in ("Error", "error", "CHYBA", "Traceback", "::warning", "::error", "HTTP", "Exception"))]
    print(f"\n== {skript}: návratový kód {p.returncode}")
    print("\n".join(l[:300] for l in (chyby[-15:] or vystup[-5:])))
