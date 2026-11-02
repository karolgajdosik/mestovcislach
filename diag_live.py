import subprocess,sys,json,time,os
subprocess.run([sys.executable,"-m","pip","install","-q","-r","scripts/requirements.txt"])
t=time.time()
p=subprocess.run([sys.executable,"scripts/zber_obce.py"],capture_output=True,text=True,timeout=2400); print(p.returncode, round(time.time()-t)); print(p.stdout[-3000:]); print(p.stderr[-2500:])
try:
    z=json.load(open("data/obce/zoznam.json"))["obce"]
    print("bez obyv:",[ (x["nazov"],x["okres"]) for x in z if not x["obyvatelia"]][:30])
    print("bez polohy:",[ (x["nazov"],x["okres"]) for x in z if not x["poloha"]][:20])
    print("príklad",z[100])
    k=json.load(open("data/obce/trnavsky-kraj.json"))["obce"]; o=next(x for x in k if x["nazov"]=="Hlohovec"); print(json.dumps({kk:(v if kk!="volby2026" else {**v,"poslanci":v["poslanci"][:2]}) for kk,v in o.items() if kk!="obyvatelia"},ensure_ascii=False)[:1800])
    for f in os.listdir("data/obce"): print(f, os.path.getsize(f"data/obce/{f}"))
    m=json.load(open("data/obce/mapa.json")); print("mapa",len(m["kraje"]),len(m["okresy"]),[x["nazov"] for x in m["kraje"]])
except Exception as e: print("ERR",e)
print("HOTOVO")
