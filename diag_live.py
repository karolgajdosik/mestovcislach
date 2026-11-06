import subprocess, sys; subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", "scripts/requirements.txt"])
import sys, json, time
sys.path.insert(0, "scripts")
import zber_obce_volby as v, zber_obce_statdata as st
for c in ["xlsx:https://volby.statistics.sk/prez/prez2019/files/PRE_2019_KOLO1_xlsx.zip"]:
    try:
        u, h, sr = v.tabulky(c)
        print("ucast", len(u), list(u[0].keys())[:8]); print("hlasy", len(h), list(h[0].keys())[:8]); print("sr", list(sr.items())[:6])
    except Exception as e:
        print("CHYBA volby", type(e).__name__, e)
t=time.time()
try:
    st.vek(); d=json.load(open("data/obce/vek.json")); print(d["rok"], len(d["obce"]), d["obce"].get("518921"))
except Exception as e:
    import traceback; traceback.print_exc()
print("cas", round(time.time()-t))
print("HOTOVO")
