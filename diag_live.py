import subprocess, sys, traceback
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", "scripts/requirements.txt"])
sys.path.insert(0, "scripts")
import zber_komunalne as zk, zber_mesta as zm
t, _ = zk.stiahni(zm.KOMUNALNE[1][1])
print("má", all(t.get(x) for x in ("tab0a","tab05")))
m = [x for x in zm.MESTA if x["slug"]=="nitra"][0]
obec = next((zk.kod(r["OBEC"]) for r in t.get("tab0d", []) if zm.norm(r.get("NOBEC", "")) == m["nazov"]), None)
print("obec", obec)
try:
    kand = [r for r in t["tab0a"] if zk.kod(r["OBEC"]) == obec]; print("kand", len(kand))
    hl = [r for r in t["tab05"] if zk.kod(r["OBEC"]) == obec]; print("hl", len(hl))
    zvol = {k[1] for k in zk.zvoleni(t, "tab05", lambda r: (zk.kod(r["OBEC"]), zk.kod(r["PC_HL"]))) if k[0] == obec}; print("zvol", zvol)
    strany = zk.strany_mapa(t)
    pr = zk.vysledky_kandidatov(hl, kand, strany, lambda r: zk.kod(r["PC_HL"]), lambda r: True, zvol or None); print("pr", [(x["meno"], x["podiel"], x["zvoleny"]) for x in pr[:2]])
    zvp = {(k[1], k[2]) for k in zk.zvoleni(t, "tab08", lambda r: (zk.kod(r["OBEC"]), zk.kod(r.get("VOOBEC", "")), zk.kod(r["PC_HL"]))) if k[0] == obec}; print("zvolení poslanci", len(zvp))
    print("ucast", zk.ucast(t["tab02b"], {obec})); print("sprac", zk.spracovanie(t, obec))
    print(zk.primator_po_mc(t, obec, m["nazov"], strany)[1])
    ke = [x for x in zm.MESTA if x["slug"]=="kosice"][0]; ok = "599981"
    mcv, kon = zk.primator_po_mc(t, ok, ke["nazov"], strany); print("KE MČ", len(mcv), kon, [(x["nazov"], x["ucast"], x["poradie"][0]["meno"], x["poradie"][0]["podiel"]) for x in mcv[:4]])
except Exception: traceback.print_exc()
print("tab05_agg príklad:", {k: v for k, v in t["tab05_agg"][0].items() if k in ("OBEC","PC_HL","P_HL","POZNAMKA")})
print("HOTOVO")
