# Test volebnej noci: ročník 2026 podstrčíme ako XLSX balík 2022 (rovnaký formát ako zverejňuje volbysr.sk)
# a porovnáme s uloženými výsledkami 2022 (z CSV). Vypisujú sa len počty a zhody, nie mená.
import sys, json, subprocess, re
subprocess.run(["pip","install","-q","-r","scripts/requirements.txt"])
X="https://web.archive.org/web/20241201215347id_/https://volby.statistics.sk/oso/oso2022/files/OSO2022_SK_xlsx.zip"
sys.path.insert(0,"scripts")
import zber_mesta as zm
zm.KOMUNALNE=[("2026",[X])]
v=zm.komunalne(None)
for s,k in v.items():
    a=k.get("2026"); b=json.load(open(f"data/mesta/{s}.json"))["komunalne"]["2022"]
    if not a: print(s,"CHYBA: nič"); continue
    pa=next((x for x in a["primator"] if x["zvoleny"]),None); pb=next((x for x in b["primator"] if x["zvoleny"]),None)
    print(s, "primátor zhoda:", pa and pb and pa["meno"]==pb["meno"] and abs(pa["podiel"]-pb["podiel"])<0.01,
          "| účasť", a["ucast"], b["ucast"], "| poslancov", a["zastupitelstvo"]["poslancov"], b["zastupitelstvo"]["poslancov"],
          "| mená poslancov zhoda:", {p["meno"] for p in a["zastupitelstvo"]["poslanci"]}=={p["meno"] for p in b["zastupitelstvo"]["poslanci"]},
          "| mandáty zhoda:", sorted((m["strany"],m["mandaty"]) for m in a["zastupitelstvo"]["mandaty"])==sorted((m["strany"],m["mandaty"]) for m in b["zastupitelstvo"]["mandaty"]),
          "| MČ", len(a.get("mestske_casti") or []), len(b.get("mestske_casti") or []), "| spracovanie", a["spracovanie"])
# Bratislava: zber_komunalne s XLSX
t=open("scripts/zber_komunalne.py").read()
t=t.replace('"oso": ["https://volbysr.sk/oso/files/OSO2026_SK_csv.zip", "https://volbysr.sk/oso/files/OSO2026_SK_xlsx.zip"]', f'"oso": ["{X}"]')
open("scripts/zber_komunalne.py","w").write(t)
r=subprocess.run(["python","scripts/zber_komunalne.py"],capture_output=True,text=True); print(re.sub(r"(primátor|predseda BSK): [^0-9]*", r"\1: ", r.stdout)[-1500:], r.stderr[-1500:])
d=json.load(open("data/komunalne-bratislava.json"))["volby"]
a=next(x for x in d if x["id"]=="2026"); b=next(x for x in d if x["id"]=="2022")
if a.get("oso"):
    print("BA stav", a.get("stav"), "| primátor zhoda", [k["meno"] for k in a["oso"]["primator"]["kandidati"] if k["zvoleny"]]==[k["meno"] for k in b["oso"]["primator"]["kandidati"] if k["zvoleny"]],
      "| MsZ", len(a["oso"]["mestske_zastupitelstvo"]["zvoleni"]), len(b["oso"]["mestske_zastupitelstvo"]["zvoleni"]),
      "| obvody zhoda", sorted((p["obvod"],p["meno"]) for p in a["oso"]["mestske_zastupitelstvo"]["zvoleni"])==sorted((p["obvod"],p["meno"]) for p in b["oso"]["mestske_zastupitelstvo"]["zvoleni"]),
      "| starostovia", len(a["oso"].get("starostovia") or []), "| MČ", len(a["oso"]["primator"].get("mestske_casti") or []))
else: print("BA 2026 bez oso", a.get("stav"))
print("HOTOVO")
