import os, subprocess, shutil
os.makedirs("diag", exist_ok=True); os.makedirs("data/mesta", exist_ok=True)
subprocess.run(["pip","install","-q","-r","scripts/requirements.txt"])
r=subprocess.run(["python","scripts/zber_skoly_mesta.py"],capture_output=True,text=True)
print(r.stdout[-4000:]); print(r.stderr[-3000:])
if os.path.exists("data/mesta/skoly.json"): shutil.copy("data/mesta/skoly.json","diag/skoly.json")
print("HOTOVO")
