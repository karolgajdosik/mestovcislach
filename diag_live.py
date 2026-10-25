import subprocess, sys, traceback, json
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", "scripts/requirements.txt"])
sys.path.insert(0, "scripts")
import zber_komunalne as zk
t, url = zk.stiahni(["https://volbysr.sk/oso/files/OSO2026_SK_xlsx.zip"])
print("tabuľky:", {k: len(v) for k, v in t.items()})
for k, v in sorted(t.items()):
    if v: print(k, list(v[0].keys())[:14])
try:
    nm = {}
    zk.spracuj_oso(t, nm)
except Exception:
    traceback.print_exc()
d = json.load(open("data/mesta/nitra.json"))["komunalne"]["2026"]
print("nitra 2026 v repe:", d.get("spracovanie"), d.get("zastupitelstvo", {}).get("poslancov"))
r = subprocess.run([sys.executable, "scripts/zber_mesta.py", "komunalne"], capture_output=True, text=True)
d = json.load(open("data/mesta/nitra.json"))["komunalne"]["2026"]
print("nitra 2026 po zbere:", d.get("spracovanie"), d.get("zastupitelstvo", {}).get("poslancov"), [(k["meno"], k["podiel"]) for k in d["primator"][:2]])
k = json.load(open("data/mesta/kosice.json"))["komunalne"]["2026"]; print("KE MČ:", len(k.get("mestske_casti", [])), k.get("spracovanie"))
print("HOTOVO")
