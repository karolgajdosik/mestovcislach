import os, subprocess, shutil
os.makedirs("diag", exist_ok=True); os.makedirs("data/mesta", exist_ok=True)
subprocess.run(["pip","install","-q","-r","scripts/requirements.txt"])
r=subprocess.run(["python","scripts/zber_casti_osm.py"],capture_output=True,text=True)
print(r.stdout[-3000:]); print(r.stderr[-3000:])
if os.path.exists("data/mesta/casti-osm.json"): shutil.copy("data/mesta/casti-osm.json","diag/casti-osm.json")
print("HOTOVO")
