import subprocess,sys,json,time; subprocess.run([sys.executable,"-m","pip","install","-q","-r","scripts/requirements.txt"])
sys.path.insert(0,"scripts")
ica=json.load(open("data/obce/ico.json")); sub=dict(list(ica.items())[::100][:30]); json.dump(sub,open("data/obce/ico.json","w"))
import zber_hospodarenie_obce as h
h.CAS_MIN=8
t=time.time()
try: h.main()
except SystemExit: pass
print("cas",round(time.time()-t))
d=json.load(open("data/obce/hospodarenie.json"))["obce"]
for k,v in list(d.items())[:3]: print(k, json.dumps({x:v.get(x) for x in ("roky","chyba")},ensure_ascii=False)[:400])
print("roky", sorted({r for v in d.values() for r in v.get("roky",{})}), sum(1 for v in d.values() if v.get("roky")))
print("HOTOVO")
