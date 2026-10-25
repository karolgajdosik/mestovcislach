import subprocess, sys, traceback, json
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", "scripts/requirements.txt"])
sys.path.insert(0, "scripts")
import zber_komunalne as zk, zber_mesta as zm
t, url = zk.stiahni(["https://volbysr.sk/oso/files/OSO2026_SK_xlsx.zip"])
print("tab0d príklad:", [ (r.get("OBEC"), r.get("NOBEC")) for r in t["tab0d"] if "Nitra" in str(r.get("NOBEC"))][:3])
print("MESTA nazvy:", [m["nazov"] for m in zm.MESTA])
print("norm:", [zm.norm(r.get("NOBEC","")) for r in t["tab0d"][:3]])
try:
    v = zm.komunalne({})
    print({s: (list(x.keys()), (x.get("2026") or {}).get("zastupitelstvo", {}).get("poslancov")) for s, x in v.items()})
except Exception: traceback.print_exc()
osk, u = zk.stiahni(["https://volbysr.sk/osk/files/OSK2026_SK_xlsx.zip"])
print("OSK tabuľky:", {k: len(v) for k, v in osk.items()})
try: zk.spracuj_osk(osk, {})
except Exception: traceback.print_exc()
print("HOTOVO")
