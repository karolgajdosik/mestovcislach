import subprocess, shutil, json
subprocess.run("pip install -q shapely pyarrow", shell=True)
subprocess.run("git fetch -q --depth=1 origin main && git checkout origin/main -- data scripts src/mesta.json", shell=True, check=True)
p = subprocess.run(["python", "scripts/zber_mhd_presov.py"], capture_output=True, text=True, timeout=900)
print(p.stdout[-1500:], p.stderr[-1500:], "kód", p.returncode)
shutil.copy("data/mesta/mhd-presov.json", "diag/mhd-presov.json")
d = json.load(open("data/mesta/mhd-presov.json")); print("spolu", d["spolu"], "deň", d["den"], "platnosť", d["platnost"])
print("HOTOVO")
