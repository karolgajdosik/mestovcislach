import subprocess, sys; subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", "scripts/requirements.txt"])
import json
sys.path.insert(0, "scripts")
import zber_obce_t9 as t9
t9.main(); d = json.load(open("data/obce/t9.json")); print(d["rok"], d["sr"], d["obce"].get("518921"), d["obce"].get("515680"))
print("HOTOVO")
