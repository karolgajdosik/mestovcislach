import subprocess, sys, collections
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", "scripts/requirements.txt"])
sys.path.insert(0, "scripts")
from statdata_obce import riadky_obce
for kod in ["om7103rr", "om7052rr", "om7811rr", "om7815rr", "om7816rr", "om7813rr", "om7821rr", "zd5001rr", "cr3805qr"]:
    try:
        rr = riadky_obce(kod)
    except Exception as e:
        print(kod, "ERR", str(e)[:300]); continue
    print(f"== {kod} riadkov {len(rr)} stĺpce {list(rr[0].keys())}")
    for k in rr[0]:
        if k in ("hodnota", "e_nuts15", "e_nuts14", "_cas"): continue
        v = collections.Counter(x[k].strip() for x in rr); print("   ", k, len(v), [x[:55] for x in list(v)[:25]])
    print("    časy:", sorted({x["_cas"] for x in rr})[-6:])
    vz = [x for x in rr if x["e_nuts15"].strip() == "Vígľaš" and x["_cas"] == max(y["_cas"] for y in rr)][:30]
    for x in vz: print("    V:", {k: v.strip()[:45] for k, v in x.items() if k not in ("e_nuts15", "e_nuts14", "_cas")})
print("HOTOVO")
