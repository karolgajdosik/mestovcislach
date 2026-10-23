import subprocess, sys, json, shutil
subprocess.run("pip install -q shapely pyarrow", shell=True)
subprocess.run("git fetch -q --depth=1 origin main && git checkout origin/main -- data scripts src/mesta.json", shell=True, check=True)
shutil.copy("test/zber_komunalne.py", "scripts/zber_komunalne.py"); shutil.copy("test/zber_mesta.py", "scripts/zber_mesta.py")
sys.path.insert(0, "scripts")
import zber_komunalne as zk, zber_mesta as zm
t, u = zk.stiahni(zm.KOMUNALNE[0][1])
strany = zk.strany_mapa(t)
for kod_, nazov in (("582000", "Bratislava"), ("599981", "Košice")):
    v, k = zk.primator_po_mc(t, kod_, nazov, strany)
    mc_u = {x["kod"]: zk.ucast(t["tab02b"], {x["kod"]}) for x in v}
    print(f"{nazov}: MČ {len(v)}, kontrola {k}, voliči sedia v {sum(1 for x in v if x['volili'] == mc_u[x['kod']]['volili'])}/{len(v)}",
          "| rozdiely voličov:", [(x["nazov"], x["volili"] - mc_u[x["kod"]]["volili"]) for x in v if x["volili"] != mc_u[x["kod"]]["volili"]])
    if nazov == "Bratislava":
        ref = {x["kod"]: x for x in json.load(open("data/komunalne-bratislava.json"))["volby"][0]["oso"]["primator"]["mestske_casti"]}
        print("  rozdiely BA:", [x["nazov"] for x in v if abs(x["poradie"][0]["podiel"] - ref[x["kod"]]["poradie"][0]["podiel"]) > 0.05])
    print("  súčet hlasov primátora po MČ:", sum(sum(p["hlasy"] for p in x["poradie"]) for x in v), "(len top 3)")
