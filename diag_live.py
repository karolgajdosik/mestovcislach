import subprocess, sys, json
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", "scripts/requirements.txt"])
sys.path.insert(0, "scripts")
from statdata_obce import polozky, B, H
from spolocne import s
for k in ["om7103rr", "om7052rr", "cr3805qr"]:
    info = s.get(f"{B}/public/{k}/info", headers=H, timeout=60).json()
    print("==", k, info["nameSk"], info.get("timePeriodTo"))
    for d in info["dimensions"]:
        if d["type"] == "GEO": continue
        p = polozky(k, d["id"])
        print("  ", d["acronym"], d["type"], len(p), json.dumps(p[:2], ensure_ascii=False)[:300])
        if len(p) < 40: print("     ", [x.get("nameSk") or x.get("name") for x in p])
print("HOTOVO")
