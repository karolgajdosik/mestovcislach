import subprocess, sys, json, os, shutil
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", "scripts/requirements.txt"])
r = subprocess.run([sys.executable, "scripts/zber_komunalne.py"], capture_output=True, text=True, timeout=1500); print("BA rc", r.returncode, r.stdout[-1500:], r.stderr[-2500:])
d = json.load(open("data/komunalne-bratislava.json")); v = [x for x in d["volby"] if x["id"] == "2026"][0]
o = v.get("oso", {}); k = v.get("osk", {})
print("MČ:", [(m.get("nazov"), m.get("ucast",{}).get("ucast_pct") if isinstance(m.get("ucast"),dict) else m.get("ucast")) for m in o.get("primator",{}).get("mestske_casti",[])][:4])
print("BSK:", [(x["meno"], x["podiel"], x.get("zvoleny")) for x in k.get("predseda",{}).get("kraj",{}).get("kandidati",[])[:2]], k.get("predseda",{}).get("kraj",{}).get("ucast"), "poslanci BA", k.get("poslanci_za_bratislavu",{}).get("poslancov"))
print("starostovia:", len(o.get("starostovia",[])), [(s["nazov"], s["miestne_zastupitelstvo"]["poslancov"]) for s in o.get("starostovia",[])][:4])
os.makedirs("diag/fin", exist_ok=True); shutil.copy("data/komunalne-bratislava.json", "diag/fin/komunalne-bratislava.json")
print("HOTOVO")
