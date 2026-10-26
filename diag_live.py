import subprocess, sys, requests
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", "scripts/requirements.txt"])
sys.path.insert(0, "scripts")
import zber_komunalne as zk
t, _ = zk.stiahni(["https://volbysr.sk/oso/files/OSO2026_SK_xlsx.zip"])
print("tab0b:", list(t["tab0b"][0].keys()))
print("tab0a:", list(t["tab0a"][0].keys()))
print("tab08_agg:", list(t["tab08_agg"][0].keys()))
print("tab12c:", list(t["tab12c"][0].keys()))
print("tab07x:", t["tab07x"][:3])
H={"User-Agent":"Mozilla/5.0"}
for u in ["https://data.statistics.sk/api/v2/collection?lang=sk","https://statdata.statistics.sk/public/api/dc/opendata/cube/dataset/om7803rr/download?type=CSV&lang=SK"]:
    try:
        r=requests.get(u,headers=H,timeout=60,allow_redirects=False); print(u[:60], r.status_code, r.headers.get("location"), len(r.content))
    except Exception as e: print(u[:60], "ERR", type(e).__name__)
print("HOTOVO")
