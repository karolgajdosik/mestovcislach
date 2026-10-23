import subprocess, sys, shutil
from collections import Counter, defaultdict
subprocess.run("pip install -q shapely pyarrow", shell=True)
subprocess.run("git fetch -q --depth=1 origin main && git checkout origin/main -- data scripts src/mesta.json", shell=True, check=True)
shutil.copy("test/zber_komunalne.py", "scripts/zber_komunalne.py"); shutil.copy("test/zber_mesta.py", "scripts/zber_mesta.py")
sys.path.insert(0, "scripts")
import zber_komunalne as zk, zber_mesta as zm
t, u = zk.stiahni(zm.KOMUNALNE[0][1])
KE = "599981"
mc = {zk.kod(r["OBEC"]): r["NOBEC"] for r in t["tab0d"] if (r.get("NOBEC") or "").startswith("Košice - ")}
print("MČ v tab0d:", len(mc))
riadky_mc = [r for r in t["tab02b"] if zk.kod(r["OBEC"]) in mc]
riadky_ke = [r for r in t["tab02b"] if zk.kod(r["OBEC"]) == KE]
print("okrskov MČ spolu:", len(riadky_mc), "| okrskov mesta:", len(riadky_ke))
print("okrsky po MČ:", {mc[k].split(' - ')[1]: v for k, v in Counter(zk.kod(r["OBEC"]) for r in riadky_mc).items()})
print("stĺpce tab02b:", list(riadky_ke[0].keys()))
# zhoda podľa (zap, zuc) vs (okrsok, zap, zuc)
a = Counter((int(zk.cislo(r["P_ZAP"])), int(zk.cislo(r["P_ZUC"]))) for r in riadky_mc)
b = Counter((zk.kod(r["OKRSOK"]), int(zk.cislo(r["P_ZAP"])), int(zk.cislo(r["P_ZUC"]))) for r in riadky_mc)
for nazov, kl, cnt in (("zap+zuc", lambda r: (int(zk.cislo(r["P_ZAP"])), int(zk.cislo(r["P_ZUC"]))), a),
                       ("okrsok+zap+zuc", lambda r: (zk.kod(r["OKRSOK"]), int(zk.cislo(r["P_ZAP"])), int(zk.cislo(r["P_ZUC"]))), b)):
    st = Counter("jedno" if cnt.get(kl(r), 0) == 1 else "viac" if cnt.get(kl(r), 0) > 1 else "žiadne" for r in riadky_ke)
    print(nazov, dict(st))
# okrsky malých MČ: ich počty voličov existujú v meste?
for kk, n in mc.items():
    rr = [r for r in riadky_mc if zk.kod(r["OBEC"]) == kk]
    if len(rr) <= 2:
        print(n.split(" - ")[1], [(zk.kod(r["OKRSOK"]), zk.kod(r.get("VOOBEC","")), int(zk.cislo(r["P_ZAP"])), int(zk.cislo(r["P_ZUC"]))) for r in rr],
              "v meste:", [(zk.kod(x["VOOBEC"]), zk.kod(x["OKRSOK"])) for x in riadky_ke if (int(zk.cislo(x["P_ZAP"])), int(zk.cislo(x["P_ZUC"]))) in {(int(zk.cislo(r["P_ZAP"])), int(zk.cislo(r["P_ZUC"]))) for r in rr}])
# poradie riadkov tab05 mesta: bloky po okrskoch súvislé?
bloky = []; pred = None
for r in t["tab05"]:
    if zk.kod(r["OBEC"]) != KE: continue
    k = (zk.kod(r["VOOBEC"]), zk.kod(r["OKRSOK"]))
    if k != pred: bloky.append(k); pred = k
print("blokov tab05 mesta:", len(bloky), "| unikátnych kľúčov:", len(set(bloky)))
print("poradie tab02b vs tab05 blokov rovnaké:", [(zk.kod(r["VOOBEC"]), zk.kod(r["OKRSOK"])) for r in riadky_ke] == bloky)
