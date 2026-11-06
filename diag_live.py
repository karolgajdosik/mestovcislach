import subprocess, sys; subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", "scripts/requirements.txt"])
import re, time, json
sys.path.insert(0, "scripts")
import zber_obce_t9 as t9
s = t9.relacia()
x = t9.tabulka(s, 2025, "55", "6"); print("BB mat", len(x), x[-2:])
t = time.time()
try:
    t9.main(); d = json.load(open("data/obce/t9.json")); print(d["rok"], d["sr"], len(d["obce"]), d["obce"].get("518921"), d["obce"].get("515833"))
except Exception:
    import traceback; traceback.print_exc()
print("cas", round(time.time() - t))
print("HOTOVO")
