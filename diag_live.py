import subprocess,sys; subprocess.run([sys.executable,"-m","pip","install","-q","-r","scripts/requirements.txt"])
import sys,time,traceback
sys.path.insert(0,"scripts")
try:
    import zber_mesta as zm
except Exception as e:
    print("IMPORT",e); print("HOTOVO"); raise SystemExit
for tema,(k,st) in zm.SCITANIE.items():
    t=time.time()
    try:
        r=zm.s.get(zm.STATDATA.format(k),timeout=600); print(tema,k,r.status_code,len(r.content),r.content[:2],round(time.time()-t))
    except Exception as e: print(tema,k,"CHYBA",type(e).__name__,str(e)[:200],round(time.time()-t))
try:
    v=zm.scitanie(); print("OK",{s:list(x) for s,x in v.items()}); print("KE casti",len(zm.CASTI.get("kosice",{})),"BA",len(zm.CASTI.get("bratislava",{})))
except Exception: print(traceback.format_exc()[-800:])
print("HOTOVO")
