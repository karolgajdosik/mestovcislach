import sys, json, subprocess
subprocess.run(["pip","install","-q","-r","scripts/requirements.txt"])
X="https://web.archive.org/web/20241201215347id_/https://volby.statistics.sk/oso/oso2022/files/OSO2022_SK_xlsx.zip"
sys.path.insert(0,"scripts")
import zber_mesta as zm
zm.KOMUNALNE=[("2026",[X])]
v=zm.komunalne(None)
for s in ["bratislava","presov","kosice"]:
    a=v[s]["2026"]["zastupitelstvo"]["mandaty"]; b=json.load(open(f"data/mesta/{s}.json"))["komunalne"]["2022"]["zastupitelstvo"]["mandaty"]
    A={m["strany"]:m["mandaty"] for m in a}; B={m["strany"]:m["mandaty"] for m in b}
    print(s, "len XLSX:", {k:v for k,v in A.items() if B.get(k)!=v}); print(s, "len CSV:", {k:v for k,v in B.items() if A.get(k)!=v})
print("HOTOVO")
