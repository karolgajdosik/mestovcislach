import subprocess,sys,json
subprocess.run([sys.executable,"-m","pip","install","-q","-r","scripts/requirements.txt"])
for rok in ("2026","2027"):
    p=subprocess.run([sys.executable,"scripts/zber_rozpocty.py",rok],capture_output=True,text=True,timeout=900)
    print(rok, p.stdout[-1500:], p.stderr[-500:])
    try:
        d=json.load(open(f"data/rozpocty-{rok}.json"))
        for s,v in d["mesta"].items():
            for x in v["dokumenty"][:3]: print("  ",s,x["druh"],x["zverejnene"],x["nazov"][:70])
    except Exception as e: print(e)
import requests
for u in ["https://www.presov.sk","https://www.presov.sk/rozpocet-mesta.html","https://www.presov.sk/uradna-tabula.html","https://www.banskabystrica.sk/samosprava/rozpocet-mesta/","https://bratislava.sk/mesto-bratislava/transparentne-mesto/rozpocet"]:
    try:
        r=requests.get(u,timeout=30,headers={"User-Agent":"Mozilla/5.0"}); import re
        print(u,r.status_code,len(r.text),[m for m in re.findall(r'href="([^"]+)"',r.text) if re.search("rozpo|tabul",m,re.I)][:8])
    except Exception as e: print(u,e)
print("HOTOVO")
