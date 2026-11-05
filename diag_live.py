import subprocess, sys, io, re, collections
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", "scripts/requirements.txt"])
sys.path.insert(0, "scripts")
import requests, openpyxl
import statdata as sd
H = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/130 Safari/537.36"}
f = requests.get("https://www.upsvr.gov.sk/buxus/docs/statistic/mesta_a_oibce_-_mesacne/2026/UoZobce_MS_2609.xlsx", headers=H, timeout=120)
wb = openpyxl.load_workbook(io.BytesIO(f.content), read_only=True, data_only=True)
ws = wb["Ciselniky_19"]
for i, row in enumerate(ws.iter_rows(values_only=True)):
    if i < 25 or i % 400 == 0: print("cis", [c for c in row if c is not None][:8])
rows = [r for r in wb["Tab01_3"].iter_rows(values_only=True)]
print("tab01 rows", len(rows)); print(rows[-6:])
print([r for r in rows if r and any(isinstance(c, str) and "Zlaté" in c for c in r)][:3])
for kocka in ["zp3804rr", "sv5001rr", "sv5002rr"]:
    rr = sd.riadky(kocka)
    print(kocka, len(rr), list(rr[0].keys()))
    for x in rr[:3]: print("   ", x)
    for k in rr[0]:
        if k != "hodnota":
            vals = collections.Counter(x[k] for x in rr)
            print("   ", k, len(vals), list(vals)[:12])
print("HOTOVO")
