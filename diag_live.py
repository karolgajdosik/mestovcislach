import subprocess, sys, os, shutil
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", "scripts/requirements.txt"])
r=subprocess.run([sys.executable, "scripts/volby_priebezne.py"], capture_output=True, text=True); print(r.stdout, r.stderr[-1500:])
r=subprocess.run([sys.executable, "scripts/zber_komunalne.py"], capture_output=True, text=True); print("BA", r.returncode, r.stdout[-1200:], r.stderr[-1500:])
r=subprocess.run([sys.executable, "scripts/zber_mesta.py", "komunalne"], capture_output=True, text=True); print("MESTA", r.returncode, "\n".join(l for l in r.stdout.splitlines() if "2026" in l or "::" in l), r.stderr[-1500:])
os.makedirs("diag/vp/mesta", exist_ok=True)
shutil.copy("data/komunalne-bratislava.json","diag/vp/komunalne-bratislava.json")
for f in os.listdir("data/mesta"):
    if f.endswith(".json") and not f.startswith(("crz","samosprava","casti","mhd","temy","skoly","firmy","hospodarenie","ovzdusie","vlaky")): shutil.copy(f"data/mesta/{f}", f"diag/vp/mesta/{f}")
print("HOTOVO")
