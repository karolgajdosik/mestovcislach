import subprocess, sys; subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", "scripts/requirements.txt"])
import json, traceback
sys.path.insert(0, "scripts")
import zber_obce_t9 as t9
try:
    t9.maturita(t9.relacia()); d = json.load(open("data/obce/maturita.json")); print(d["rok"], d["sr"], len(d["obce"]), d["obce"].get("516643"))
except Exception: traceback.print_exc()
print("HOTOVO")
