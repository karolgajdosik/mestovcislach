import subprocess,sys,json
subprocess.run([sys.executable,"-m","pip","install","-q","-r","scripts/requirements.txt"])
p=subprocess.run([sys.executable,"scripts/zber_obce_vlaky.py"],capture_output=True,text=True)
print(p.stdout[-4000:]); print(p.stderr[-2000:])
try:
    d=json.load(open("data/obce/vlaky.json")); o=d["obce"]
    NM={x["kod"]:x["nazov"] for x in json.load(open("data/obce/zoznam.json"))["obce"]}
    print("den",d["den"],"obci",len(o))
    for k in ["560103","517402","599981","582000","500488","514292"]: print(NM.get(k),o.get(k))
    c=json.load(open("data/obce/vlaky_stanice.json")); print("cache",len(c),"prazdnych",sum(1 for v in c.values() if not v))
except Exception as e: print("chyba",e)
print("HOTOVO")
