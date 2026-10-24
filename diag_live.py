import subprocess, sys, os, shutil, json
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", "scripts/requirements.txt"])
code = "import sys; sys.path.insert(0,'scripts'); import zber_data_bratislava as z; z.zber_zmluvy()"
r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=1200); print("BA rc", r.returncode, r.stdout[-500:], r.stderr[-800:])
r = subprocess.run([sys.executable, "scripts/zber_samosprava_mesta.py"], capture_output=True, text=True, timeout=1200); print("KE rc", r.returncode, r.stdout[-500:], r.stderr[-800:])
os.makedirs("diag/ine", exist_ok=True)
for f in os.listdir("data/zmluvy-ine"):
    shutil.copy(f"data/zmluvy-ine/{f}", f"diag/ine/{f}")
    d = json.load(open(f"data/zmluvy-ine/{f}")); print(f, len(d["zmluvy"]), "IČO", len({z['ico'] for z in d['zmluvy']}))
print("HOTOVO")
