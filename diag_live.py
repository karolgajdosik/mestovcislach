import subprocess, shutil, os, json
subprocess.run(["pip","install","-q","-r","scripts/requirements.txt"])
r=subprocess.run(["python","scripts/zber_mesta.py","komunalne"],capture_output=True,text=True); print(r.stdout[-1500:]); print(r.stderr[-800:])
os.makedirs("diag",exist_ok=True); shutil.copy("data/mesta/kosice.json","diag/kosice.json")
d=json.load(open("data/mesta/kosice.json"))["komunalne"]["2022"]["mestske_casti"]
print([(c["nazov"][:10], len(c["poradie"]), c["poradie"][0]["podiel"]) for c in d])
print("HOTOVO")
