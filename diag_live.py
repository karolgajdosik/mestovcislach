import sys; sys.path.insert(0,"scripts")
import subprocess; subprocess.run([sys.executable,"-m","pip","install","-q","requests"])
import statdata as sd
names={}
for r in sd.riadky("om7101rr"):
    if any(x in r["e_nuts15"] for x in ("Dubová","Jablonové","Radošovce","Chvojnica","Rohožník","Píla","Bratislava","Hradište")): names[(r["e_nuts14"],r["e_nuts15"])]=1
for k in sorted(names)[:40]: print(k)
print("HOTOVO")
