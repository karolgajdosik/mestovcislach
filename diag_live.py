import subprocess,sys,json
subprocess.run([sys.executable,"-m","pip","install","-q","-r","scripts/requirements.txt"])
sys.path.insert(0,"scripts")
import zber_obce_statdata as Z
Z.pohyb(); Z.byvanie()
p=json.load(open("data/obce/pohyb.json")); b=json.load(open("data/obce/byvanie.json"))
for k in ["515680","518921","508438"]:
    print(k,p["obce"].get(k)); print(k,b["obce"].get(k))
print({o:v for o,v in b["okresy"].items() if o in ("Banská Bystrica","Rimavská Sobota","Detva","Bratislava")})
print("HOTOVO")
