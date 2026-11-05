import subprocess,sys,json
subprocess.run([sys.executable,"-m","pip","install","-q","-r","scripts/requirements.txt"])
p=subprocess.run([sys.executable,"scripts/zber_obce_vlaky.py"],capture_output=True,text=True)
print(p.stdout[-3000:]); print(p.stderr[-3000:])
try:
    d=json.load(open("data/obce/vlaky.json"))
    o=d["obce"]; print("den",d["den"],"obci",len(o))
    for k in ["509574","514292","511218","528595","599981"]:
        print(k,o.get(k))
    print("top",sorted(((sum(n for _,n in v),k,v[:2]) for k,v in o.items()),reverse=True)[:8])
except Exception as e: print("chyba",e)
print("HOTOVO")
