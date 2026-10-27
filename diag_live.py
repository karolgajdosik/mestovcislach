import subprocess,sys; subprocess.run([sys.executable,"-m","pip","install","-q","-r","scripts/requirements.txt"])
sys.path.insert(0,"scripts")
from collections import defaultdict, Counter
try:
    import zber_komunalne as zk
    t,u=zk.stiahni(["https://volbysr.sk/oso/files/OSO2026_SK_xlsx.zip"])
    for mesto,pred in (("582000","Bratislava"),("599981","Košice")):
        uz=t["tab0d"]; rows=t["tab02b"]
        mc={zk.kod(r["OBEC"]): r["NOBEC"].split(" - ",1)[1].strip() for r in uz if zk.kod(r["OBEC"])!=mesto and (r.get("NOBEC") or "").startswith(pred+" - ")}
        c=lambda r,k: int(zk.cislo(r[k]))
        mcrows=[r for r in rows if zk.kod(r["OBEC"]) in mc]
        city=[r for r in rows if zk.kod(r["OBEC"])==mesto]
        # mapovanie: zhoda P_ZAP,P_ZUC + platné lístky pre zastupiteľstvo
        L="počet platných hlasovacích lístkov odovzdaných pre voľby do zastupiteľstva"
        key=lambda r:(c(r,"P_ZAP"),c(r,"P_ZUC"),c(r,L))
        idx=defaultdict(list)
        for r in mcrows: idx[key(r)].append(zk.kod(r["OBEC"]))
        res=defaultdict(Counter); amb=0; none=0
        for r in city:
            k=idx.get(key(r),[])
            if len(set(k))==1: res[zk.kod(r["VOOBEC"])][mc[k[0]]]+=1
            elif k: amb+=1
            else: none+=1
        print(pred,"nejasné",amb,"nenájdené",none)
        for o in sorted(res,key=int): print("  obvod",o,dict(res[o]))
        # alternatíva: MČ okrsky majú VOOBEC? (obvod mesta v riadku MČ)
        print("  MČ riadky VOOBEC príklady",Counter((mc[zk.kod(r["OBEC"])],zk.kod(r["VOOBEC"])) for r in mcrows).most_common(40))
except Exception:
    import traceback; print(traceback.format_exc()[-1500:])
print("HOTOVO")
