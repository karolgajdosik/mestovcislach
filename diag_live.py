import subprocess,sys,json,base64,zlib
subprocess.run([sys.executable,"-m","pip","install","-q","-r","scripts/requirements.txt"])
sys.path.insert(0,"scripts")
import zber_obce as z
try:
    p=z.polohy(); print("polohy",len(p))
    print("B64START"); print(base64.b64encode(zlib.compress(json.dumps(p).encode(),9)).decode()); print("B64END")
except Exception:
    import traceback; traceback.print_exc()
print("HOTOVO")
