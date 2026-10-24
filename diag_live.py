import subprocess, sys, os, shutil, time
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", "scripts/requirements.txt"])
t=time.time()
r = subprocess.run([sys.executable, "scripts/zber_odchody.py"], capture_output=True, text=True, timeout=3000)
print("rc", r.returncode, "čas", round(time.time()-t)); print(r.stdout[-3000:]); print(r.stderr[-2000:])
os.makedirs("diag/dosah", exist_ok=True)
for f in os.listdir("data/dosah"):
    shutil.copy(f"data/dosah/{f}", f"diag/dosah/{f}"); print(f, os.path.getsize(f"data/dosah/{f}"))
print("HOTOVO")
