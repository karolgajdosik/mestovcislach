import subprocess,sys; subprocess.run([sys.executable,"-m","pip","install","-q","-r","scripts/requirements.txt"])
sys.path.insert(0,"scripts")
import zber_obce as zo, zber_komunalne as zk, difflib
from collections import defaultdict
t,_=zk.stiahni(zo.OSO)
uz={}
for r in t["tab0d"]:
    n=zo.norm(r.get("NOBEC"))
    if not zo.je_mc(n): uz[zk.kod(r["OBEC"])]=(zo.norm(r.get("názov okresu") or r.get("NOKRES")),n)
print("tab0d stĺpce",list(t["tab0d"][0].keys()))
ob=zo.obyvatelia()
okresy_ob=defaultdict(list)
for (o,n) in ob: okresy_ob[o].append(n)
miss=[(o,n) for o,n in uz.values() if (o,n) not in ob]
print("chýba",len(miss))
okv=set(o for o,_ in uz.values()); oks=set(okresy_ob)
print("okresy len vo voľbách",sorted(okv-oks)[:20]); print("okresy len v STATdata",sorted(oks-okv)[:20])
for o,n in miss[:40]:
    print("  ",o,"|",n,"→",difflib.get_close_matches(n,okresy_ob.get(o,[]),2,0.6))
print("HOTOVO")
