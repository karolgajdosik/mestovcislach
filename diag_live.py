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
        idx=defaultdict(set)
        for r in mcrows: idx[c(r,"P_ZAP")].add(zk.kod(r["OBEC"]))
        hl=defaultdict(Counter)
        for r in city:
            k=idx.get(c(r,"P_ZAP"),set())
            for m in k: hl[m][zk.kod(r["VOOBEC"])]+=1/len(k)
        obv=defaultdict(list)
        for m,cn in hl.items():
            o,n=cn.most_common(1)[0]; tot=sum(cn.values())
            obv[o].append(f"{mc[m]}({n:.0f}/{tot:.0f}, okrskov {sum(1 for r in mcrows if zk.kod(r['OBEC'])==m)})")
        print(pred,"MČ bez zhody",[mc[m] for m in mc if m not in hl])
        velk=Counter(zk.kod(r["VOOBEC"]) for r in city)
        for o in sorted(obv,key=int): print("  obvod",o,"okrskov",velk[o],obv[o])
        # alternatíva: MČ okrsky majú VOOBEC? (obvod mesta v riadku MČ)
        pass #,Counter((mc[zk.kod(r["OBEC"])],zk.kod(r["VOOBEC"])) for r in mcrows).most_common(40))
except Exception:
    import traceback; print(traceback.format_exc()[-1500:])
print("HOTOVO")
