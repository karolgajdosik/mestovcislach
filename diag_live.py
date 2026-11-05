import subprocess,sys,json,time
subprocess.run([sys.executable,"-m","pip","install","-q","-r","scripts/requirements.txt"])
t0=time.time()
p=subprocess.run([sys.executable,"scripts/zber_obce_vlaky.py"],capture_output=True,text=True)
print(p.stdout[-2500:]); print(p.stderr[-1500:]); print("trvanie",round(time.time()-t0))
try:
    d=json.load(open("data/obce/vlaky.json")); o=d["obce"]
    NM={x["kod"]:x["nazov"] for x in json.load(open("data/obce/zoznam.json"))["obce"]}
    print("den",d["den"],"obci",len(o))
    for k in ["560103","517402","599981","582000","500488","515680"]: print(NM.get(k),o.get(k))
except Exception as e: print("chyba",e)
sys.path.insert(0,"scripts")
import statdata_obce as SD, inspect
print([n for n in dir(SD) if not n.startswith("_")])
for k,d in [("om7103rr","e_indic"),("om7811rr","e_canal"),("om7815rr","e_gas"),("om7816rr","e_watsup"),("om7821rr","e_heat"),("om7813rr","e_periodconren")]:
    try: print(k,d,[p if isinstance(p,str) else (p.get("name") or p) for p in SD.polozky(k,d)][:40])
    except Exception as e: print(k,d,"chyba",e)
rows=SD.riadky_obce("om7103rr",rokov=2)
print(len(rows)); print(rows[:3])
print(sorted({r.get("e_indic") for r in rows})[:40])
for k in ["om7811rr","om7815rr"]:
    rr=[r for r in SD.riadky_obce(k) if "Tisovec" in str(r) and r.get("e_buildtype","").strip()=="Spolu"]
    for r in rr[:12]: print(k,r)
print("HOTOVO")
