import subprocess, sys, os, shutil, json
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", "scripts/requirements.txt"])
r = subprocess.run([sys.executable, "scripts/zber_odchody.py"], capture_output=True, text=True, timeout=1500)
print("rc", r.returncode); print(r.stdout[-3000:]); print(r.stderr[-2000:])
os.makedirs("diag/odchody", exist_ok=True)
for f in os.listdir("data/odchody"):
    shutil.copy(f"data/odchody/{f}", f"diag/odchody/{f}")
    print(f, os.path.getsize(f"data/odchody/{f}"))
print("HOTOVO")
