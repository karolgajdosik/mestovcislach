import subprocess, sys, json
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", "scripts/requirements.txt"])
sys.path.insert(0, "scripts")
import zber_obce_temy as t
from spolocne import DATA
for m in ("nezamestnanost", "odpad", "skoly"):
    try:
        getattr(t, m)()
        d = json.loads((DATA / "obce" / f"{m}.json").read_text())
        o = d["obce"]; k = "518921"
        print(m, {kk: vv for kk, vv in d.items() if kk not in ("obce", "okresy")}, len(o))
        print("  Vígľaš:", json.dumps(o.get(k), ensure_ascii=False)[:500])
        if "okresy" in d: print("  okres Detva:", d["okresy"].get("Detva"))
    except Exception as e:
        import traceback; traceback.print_exc()
print("HOTOVO")
