# Overenie primátora po MČ (2022, kópia z Internet Archive). Mená kandidátov nevypisujeme – len počty, podiely a zhodu.
import subprocess, sys, json, shutil
subprocess.run("pip install -q shapely pyarrow", shell=True)
subprocess.run("git fetch -q --depth=1 origin main && git checkout origin/main -- data scripts src/mesta.json", shell=True, check=True)
shutil.copy("test/zber_komunalne.py", "scripts/zber_komunalne.py"); shutil.copy("test/zber_mesta.py", "scripts/zber_mesta.py")
sys.path.insert(0, "scripts")
import zber_komunalne as zk, zber_mesta as zm
t, u = zk.stiahni(zm.KOMUNALNE[0][1]); print("zdroj:", u)
strany = zk.strany_mapa(t)
for mesto, kod_, nazov in (("bratislava", "582000", "Bratislava"), ("kosice", "599981", "Košice")):
    v, k = zk.primator_po_mc(t, kod_, nazov, strany)
    mc_ucast = {kk: zk.ucast(t["tab02b"], {kk}) for kk in {x["kod"] for x in v}}
    zhoda_volici = sum(1 for x in v if x["volili"] == mc_ucast[x["kod"]]["volili"])
    print(f"{nazov}: MČ {len(v)}, kontrola {k}, voliči sedia v {zhoda_volici}/{len(v)} MČ")
    if mesto == "bratislava":
        ref = {x["kod"]: x for x in json.load(open("data/komunalne-bratislava.json"))["volby"][0]["oso"]["primator"]["mestske_casti"]}
        rozdiel = [(x["nazov"], x["poradie"][0]["podiel"], ref[x["kod"]]["poradie"][0]["podiel"]) for x in v if abs(x["poradie"][0]["podiel"] - ref[x["kod"]]["poradie"][0]["podiel"]) > 0.05 or x["poradie"][0]["meno"] != ref[x["kod"]]["poradie"][0]["meno"]]
        print("  rozdiely oproti doterajšiemu výpočtu:", rozdiel)
    vitazi = {}
    for x in v: vitazi[x["poradie"][0]["meno"]] = vitazi.get(x["poradie"][0]["meno"], 0) + 1
    print("  počty vyhraných MČ (bez mien):", sorted(vitazi.values(), reverse=True), "| podiely víťazov:", [round(x["poradie"][0]["podiel"]) for x in v])
    print("  názvy MČ:", [x["nazov"] for x in v])
