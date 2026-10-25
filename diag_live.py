import subprocess, sys, traceback, json, os, shutil
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", "scripts/requirements.txt"])
sys.path.insert(0, "scripts")
import zber_komunalne as zk
osk, u = zk.stiahni(["https://volbysr.sk/osk/files/OSK2026_SK_xlsx.zip"])
for k in ("tab06", "tab0a", "tab0d", "tab09", "tab0b"):
    print(k, list(osk[k][0].keys())[:16] if osk.get(k) else None)
r = subprocess.run([sys.executable, "scripts/zber_mesta.py", "komunalne"], capture_output=True, text=True, timeout=1500)
print("\n".join(l for l in r.stdout.splitlines() if "komunálne" in l or "MČ" in l or "::" in l), r.stderr[-1500:])
for s in ["bratislava","nitra","kosice","presov","trnava"]:
    d = json.load(open(f"data/mesta/{s}.json"))["komunalne"]["2026"]
    print(s, d.get("spracovanie"), "poslancov", d.get("zastupitelstvo", {}).get("poslancov"), [(k["meno"], k["podiel"], k["zvoleny"]) for k in d["primator"][:2]], "MČ", len(d.get("mestske_casti", [])), d.get("zastupitelstvo",{}).get("mandaty", [])[:2])
ke = json.load(open("data/mesta/kosice.json"))["komunalne"]["2026"].get("mestske_casti", [])
print("KE MČ:", [(m.get("nazov"), m.get("ucast"), m["poradie"][0]["meno"], m["poradie"][0]["podiel"]) for m in ke][:25])
os.makedirs("diag/fin/mesta", exist_ok=True)
for f in os.listdir("data/mesta"):
    if f.endswith(".json") and f.split(".")[0] in ["bratislava","trnava","nitra","trencin","zilina","banska-bystrica","presov","kosice","porovnanie"]: shutil.copy(f"data/mesta/{f}", f"diag/fin/mesta/{f}")
print("HOTOVO")
