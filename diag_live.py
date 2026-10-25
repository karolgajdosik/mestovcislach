import subprocess, sys, traceback, json
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", "scripts/requirements.txt"])
sys.path.insert(0, "scripts")
import zber_komunalne as zk
t, url = zk.stiahni(["https://volbysr.sk/oso/files/OSO2026_SK_xlsx.zip"])
print("tabuľky:", {k: len(v) for k, v in t.items()})
print("tab05_agg stĺpce:", list(t["tab05_agg"][0].keys()) if t.get("tab05_agg") else None)
print("tab02b stĺpce:", list(t["tab02b"][0].keys()))
try:
    o = zk.spracuj_oso(t, {})
    p = o["primator"]; print("BA primátor", [(k["meno"], k["podiel"], k["zvoleny"]) for k in p["kandidati"][:2]], "MČ", len(p["mestske_casti"]), "okrsky", p.get("okrsky_priradene"), "MsZ", o["mestske_zastupitelstvo"]["poslancov"], "starostovia", len(o["starostovia"]))
    print("mandáty", o["mestske_zastupitelstvo"]["mandaty"][:4])
    print("MČ pomer:", [(m["nazov"], m.get("ucast"), m["poradie"][0]["podiel"]) for m in p["mestske_casti"][:5]])
except Exception:
    traceback.print_exc()
r = subprocess.run([sys.executable, "scripts/zber_mesta.py", "komunalne"], capture_output=True, text=True)
print("\n".join(l for l in r.stdout.splitlines() if "komunálne" in l or "MČ" in l or "::" in l), r.stderr[-1500:])
for s in ["nitra","kosice","presov"]:
    d = json.load(open(f"data/mesta/{s}.json"))["komunalne"]["2026"]
    print(s, d.get("spracovanie"), "poslancov", d.get("zastupitelstvo", {}).get("poslancov"), [(k["meno"], k["podiel"], k["zvoleny"]) for k in d["primator"][:2]], "MČ", len(d.get("mestske_casti", [])))
r = subprocess.run([sys.executable, "scripts/zber_komunalne.py"], capture_output=True, text=True); print("BA rc", r.returncode, r.stdout[-800:], r.stderr[-1500:])
print("HOTOVO")
