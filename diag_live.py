import sys; sys.path.insert(0,"scripts")
import subprocess; subprocess.run([sys.executable,"-m","pip","install","-q","requests"])
import statdata as sd
for k in ("om7101rr","om7002rr"):
    rows=sd.riadky(k); ys=sorted({r["e_year"] for r in rows}); print(k,ys[:2],ys[-3:])
    print([ (r["e_year"],r["hodnota"]) for r in rows if r.get("e_nuts15",r.get("e_nuts14"))in("Bratislava I-V","Bratislavský kraj") and r["e_year"]>="2023"])
import requests
r=requests.get("https://statdata.statistics.sk/public/api/dc/public/om7101rr/info",timeout=60); print(r.status_code,r.text[:1500])
print("HOTOVO")
