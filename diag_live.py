import subprocess,sys,json,base64,zlib
subprocess.run([sys.executable,"-m","pip","install","-q","-r","scripts/requirements.txt"])
sys.path.insert(0,"scripts")
import zber_obce as z
try:
    mp=z.mapa(); print("kraje",len(mp["kraje"]),"okresy",len(mp["okresy"]))
    d=json.dumps({"zdroj":"© prispievatelia OpenStreetMap (ODbL)",**mp},ensure_ascii=False,separators=(",",":"))
    print("B64START"); print(base64.b64encode(zlib.compress(d.encode(),9)).decode()); print("B64END")
except Exception as e:
    import traceback; traceback.print_exc()
print("HOTOVO")
