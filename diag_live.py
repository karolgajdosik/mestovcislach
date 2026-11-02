import subprocess,sys; subprocess.run([sys.executable,"-m","pip","install","-q","-r","scripts/requirements.txt"])
import sys,json,time; sys.path.insert(0,"scripts")
import zber_eia_obce as e
try: e.main()
except SystemExit: pass
d=json.load(open("data/obce/eia.json"))["obce"]
print("eia obci",len(d),"sum",sum(v["spolu"] for v in d.values()),"aktivne",sum(v["aktivne"] for v in d.values()))
for k in list(d)[:2]: print(k,json.dumps(d[k],ensure_ascii=False)[:400])
import os; print("eia size",os.path.getsize("data/obce/eia.json"))
import zber_zmluvy_obce as z
z.MAX_RPO=80
zo=z.obce()[:40]
t=time.time(); ica=z.doplni_ica(zo); print("ico",len(ica),"/",len(zo),round(time.time()-t),"s", [o["nazov"] for o in zo if o["kod"] not in ica])
# CRZ sample 2 days with these
from datetime import date
zm={}; pi={i:k for k,i in ica.items()}
for dd in (date(2026,10,27),date(2026,10,28)):
    try: print(dd,z.spracuj_den(dd,pi,zm))
    except Exception as ex: print(dd,ex)
print(len(zm), list(zm.values())[:3])
print("HOTOVO")
