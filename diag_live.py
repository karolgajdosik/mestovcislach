import sys, subprocess, requests
subprocess.run(["pip","install","-q","-r","scripts/requirements.txt"])
sys.path.insert(0,"scripts")
import zber_komunalne as z
X="https://web.archive.org/web/20241201215347id_/https://volby.statistics.sk/oso/oso2022/files/OSO2022_SK_csv.zip"
t,_=z.stiahni([X])
KE=next(z.kod(r["OBEC"]) for r in t["tab0d"] if r.get("NOBEC","").strip()=="Košice")
print("KE",KE)
u=[r for r in t["tab02b"] if z.kod(r["OBEC"])==KE]
print("tab02b stĺpce:", list(u[0].keys())); print("tab02b okrskov:", len(u))
for r in u[:12]: print("  U", z.kod(r.get("VOOBEC","")), z.kod(r["OKRSOK"]), r["P_ZAP"], r["P_ZUC"], {k:v for k,v in r.items() if k not in ("KRAJ","NKRAJ","OBEC","NOBEC","OKRES","OBVOD") and "P_" in k})
h=[r for r in t["tab05"] if z.kod(r["OBEC"])==KE]
print("tab05 stĺpce:", list(h[0].keys())); print("tab05 riadkov:", len(h))
for r in h[:30]: print("  H", z.kod(r.get("VOOBEC","")), z.kod(r["OKRSOK"]), z.kod(r["PC_HL"]), r["P_HL"])
# MČ riadky (obce MČ) – okrsky s P_ZAP
mc=[r for r in t["tab02b"] if r.get("NOBEC","").startswith("Košice - ")]
print("MČ okrskov:", len(mc)); 
for r in mc[:8]: print("  M", r["NOBEC"].split(' - ')[1][:15], z.kod(r.get("VOOBEC","")), z.kod(r["OKRSOK"]), r["P_ZAP"], r["P_ZUC"])
# sumy okrsku z tab05 podľa poradia
print("HOTOVO")
