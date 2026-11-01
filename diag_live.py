import subprocess,sys,json
subprocess.run([sys.executable,"-m","pip","install","-q","-r","scripts/requirements.txt"])
p=subprocess.run([sys.executable,"scripts/zber_rozpocty.py"],capture_output=True,text=True,timeout=1200); print(p.stdout[-2500:],p.stderr[-800:])
d=json.load(open("data/zasadnutia-ustanovujuce-2026.json"))
for s,v in d["mesta"].items():
    for x in v[:4]: print("  ",s,x["termin"],x["nazov"][:90],x["url"][:90])
print("HOTOVO")
