import subprocess, sys; subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", "scripts/requirements.txt"])
import json, time, traceback, requests
sys.path.insert(0, "scripts")
r = requests.head("https://sdi.eea.europa.eu/datashare/s/sptXqwkQr5g7Bp5/download", allow_redirects=True, timeout=60)
print("EEA HEAD", r.status_code, r.headers.get("content-length"), r.headers.get("content-type"), r.headers.get("content-disposition"))
import zber_obce_vrstvy as v, zber_obce_volby as vo, zber_obce_statdata as st, zber_obce_klima as kl
for name, f in [("geologia", v.geologia), ("starosta2022", vo.starosta2022), ("historia", st.historia)]:
    t = time.time()
    try:
        f(); d = json.load(open(f"data/obce/{name}.json"))
        print(name, "OK", round(time.time() - t), {k: d["obce"].get(k) for k in ["518921", "516643", "582000", "599981"]})
    except Exception:
        traceback.print_exc()
kl.BUNIEK_NA_BEH = 2
try:
    kl.main(); d = json.load(open("data/obce/klima.json")); print("klima", len(d["obce"]), list(d["obce"].items())[:3])
except Exception: traceback.print_exc()
print("HOTOVO")
