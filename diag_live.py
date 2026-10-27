import subprocess,sys; subprocess.run([sys.executable,"-m","pip","install","-q","-r","scripts/requirements.txt"])
sys.path.insert(0,"scripts")
from collections import defaultdict, Counter
try:
    import zber_komunalne as zk
    t,u=zk.stiahni(["https://volbysr.sk/oso/files/OSO2026_SK_xlsx.zip"])
    for mesto,pred in (("582000","Bratislava"),("599981","Košice")):
        uz=t["tab0d"]
        mc={zk.kod(r["OBEC"]): r["NOBEC"].split(" - ",1)[1].strip() for r in uz if zk.kod(r["OBEC"])!=mesto and (r.get("NOBEC") or "").startswith(pred+" - ")}
        rows=t["tab02b"]
        city=[r for r in rows if zk.kod(r["OBEC"])==mesto]
        print(pred,"MČ",len(mc),"okrskov mesta",len(city),"obvody",sorted({zk.kod(r.get("VOOBEC","")) for r in city},key=lambda x:int(x or 0)))
        print("  tab0b obvody:",Counter(zk.kod(r["VOOBEC"]) for r in t["tab0b"] if zk.kod(r["OBEC"])==mesto).most_common(30))
        # MČ okrsky count vs city
        print("  okrskov MČ spolu",sum(1 for r in rows if zk.kod(r["OBEC"]) in mc))
        # tab0d: does it list VOOBEC per MČ?
        print("  tab0d stĺpce",list(uz[0].keys()))
        print("  tab02b stĺpce",list(rows[0].keys()))
        break
except Exception:
    import traceback; print(traceback.format_exc()[-1500:])
print("HOTOVO")
