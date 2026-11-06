import subprocess, sys, json, time
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", "scripts/requirements.txt"])
sys.path.insert(0, "scripts")
sys.argv = ["x", "5"]
import zber_obce_rozpocet as r
try:
    oid = r.org_id({"nazov": "Vígľaš", "kod": "518921"}, 2025); print("oid", oid)
    print("EKP", r.get(f"rozpocet/polozkyRozpocetuFilterSamOrg/SK/{oid}/2025/SAM/false/EKP?EKP=111,121,133,200,300").get("payload", [])[:6])
    print("EKV", r.polozky(oid, 2025, "EKV", r.VYDAVKY))
    print("SUM", r.get(f"rozpocet/rozpocetSamOrg/{oid}/2025/4")["payload"]["KVARTAL4"])
    r.main(); d = json.load(open("data/obce/rozpocet.json")); print(list(d["obce"].items())[:3])
except Exception as e:
    import traceback; traceback.print_exc()
t = time.time()
import zber_obce_t9 as t9
try:
    s = t9.relacia(); rok = t9.najnovsi_rok(s); print("T9 rok", rok)
    x = t9.tabulka(s, rok, "55", "6"); print(len(x), x[:3])
    x = t9.tabulka(s, rok, "53", "8"); print("mjl KE", len(x), x[:2])
except Exception as e:
    import traceback; traceback.print_exc()
print("cas", round(time.time() - t))
print("HOTOVO")
