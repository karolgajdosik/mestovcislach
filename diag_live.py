import sys, subprocess
subprocess.run(["pip","install","-q","-r","scripts/requirements.txt"])
sys.path.insert(0,"scripts")
import zber_mesta as zm
for nazov, url in [("CSV","https://web.archive.org/web/20241201215347id_/https://volby.statistics.sk/oso/oso2022/files/OSO2022_SK_csv.zip"),("XLSX","https://web.archive.org/web/20241201215347id_/https://volby.statistics.sk/oso/oso2022/files/OSO2022_SK_xlsx.zip")]:
    zm.KOMUNALNE=[("2022",[url])]
    v=zm.komunalne(None)
    for s in ["kosice","bratislava"]:
        mc=v[s]["2022"].get("mestske_casti") or []
        pomery=[(c["nazov"][:12], round(sum(p["hlasy"] for p in c["poradie"])/max(c["volili"],1),2)) for c in mc]
        print(nazov, s, len(mc), "min pomer", min(p for _,p in pomery) if pomery else None, "max", max(p for _,p in pomery) if pomery else None)
        print("   ", pomery[:22])
print("HOTOVO")
