import sys, subprocess
from collections import defaultdict
subprocess.run(["pip","install","-q","-r","scripts/requirements.txt"])
sys.path.insert(0,"scripts")
import zber_komunalne as z
t,_=z.stiahni(["https://web.archive.org/web/20241201215347id_/https://volby.statistics.sk/oso/oso2022/files/OSO2022_SK_csv.zip"])
KE=next(z.kod(r["OBEC"]) for r in t["tab0d"] if r.get("NOBEC","").strip()=="Košice")
u=defaultdict(list)
for r in t["tab02b"]:
    if z.kod(r["OBEC"])==KE: u[(z.kod(r["VOOBEC"]),z.kod(r["OKRSOK"]))].append(int(z.cislo(r["P_HL_STA"])))
rows=[r for r in t["tab05"] if z.kod(r["OBEC"])==KE]
seq=defaultdict(list)
for r in rows: seq[(z.kod(r["VOOBEC"]),z.kod(r["OKRSOK"]))].append((z.kod(r["PC_HL"]),int(z.cislo(r["P_HL"]))))
pocet=0
for k,v in u.items():
    if len(v)>1 and pocet<6:
        pocet+=1
        print("K",k,"STA",v,"riadkov",len(seq[k]),"kand:",[pc for pc,_ in seq[k]][:30])
        print("   hlasy:",[h for _,h in seq[k]][:30])
print("spolu STA mesto", sum(sum(v) for v in u.values()), "tab05 súčet", sum(h for v in seq.values() for _,h in v))
print("kľúče len v tab05:", [k for k in seq if k not in u][:10], "len v tab02b:", [k for k in u if k not in seq][:10])
print("HOTOVO")
