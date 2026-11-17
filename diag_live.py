import subprocess, sys as _s; subprocess.run([_s.executable,"-m","pip","install","-q","shapely","pyproj"],check=False)
import sys, json, runpy, pathlib
sys.path.insert(0, "scripts")
import zber_pamiatky_body as z
try:
    z.main()
except SystemExit: pass
d=json.load(open("data/obce/pamiatky-body.json"))
o=d["obce"]; print("obcí",len(o),"pamiatok",sum(len(v) for v in o.values()), "s textom", sum(1 for v in o.values() for x in v if x["t"]), "s fotkou", sum(1 for v in o.values() for x in v if x.get("f")))
for k in ["528595","599981","513881","599972","516643"]:
    if k in o: print(k, [(x["n"], x["t"][:90], bool(x.get("f"))) for x in o[k][:3]])
print("HOTOVO")
# 1794935575
