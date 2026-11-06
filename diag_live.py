import subprocess, sys, json, collections
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", "scripts/requirements.txt"])
sys.path.insert(0, "scripts")
import zber_obce_statdata as Z
t = Z.tabulka("pl5001rr", "e_landuse", "e_soiltype", rokov=1)
c = collections.Counter()
for kod, d in list(t.items()):
    rok = max(k[0] for k in d)
    c[("ma_spolu" if d.get((rok, "Spolu", "Spolu")) else "bez_spolu", rok)] += 1
print(c)
bez = [(k, sorted(d)[:6]) for k, d in t.items() if not d.get((max(x[0] for x in d), "Spolu", "Spolu"))][:3]
print(bez)
subprocess.run([sys.executable, "scripts/zber_okresy_statdata.py"])
o = json.load(open("data/obce/okresy.json")); print({k: (list(o[k].get("Detva", {}).items())[-3:], list(o[k].get("Bratislava", {}).items())[-2:], list(o[k].get("SR", {}).items())[-2:]) for k in ("mzda", "byty")})
print("HOTOVO")
