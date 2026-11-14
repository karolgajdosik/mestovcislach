import subprocess, sys; subprocess.run([sys.executable, "-m", "pip", "install", "-q", "pyarrow"])
import re, requests, io
s = requests.Session(); s.headers["User-Agent"] = "Mozilla/5.0 (compatible; mestovcislach.sk)"
B = "https://www.minv.sk/lnisdn/statistika/20260218_011722.691_2025-12-MS/statistika/"
r = s.get(B + "index-public.html", timeout=60); r.encoding = "utf-8"
al = re.findall(r"href='([^']+\.html)' title='([^']+)'", r.text)
okr = [(h, t.replace("\n", " / ")) for h, t in al if re.search(r"Územie: (Okres|okres)", t)]
print("ALL", len(al), "OKRES", len(okr)); print(okr[:6])
pref = sorted({h.split("/")[1] for h, _ in okr}); print("PREF", pref)
if okr:
    h = next((h for h, t in okr if "od začiatku roka" in t and "všetky DN" in t), okr[0][0])
    x = s.get(B + h, timeout=60); x.encoding = "utf-8"
    print("OKRPAGE", h, re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " | ", x.text))[:1500])
import pyarrow.parquet as pq
x = s.get("https://eeadmz1batchservice02.blob.core.windows.net/airquality-p-e1a/SK/SPO-SK0004A_00005_100.parquet", timeout=120)
t = pq.read_table(io.BytesIO(x.content)); print("PQ", t.num_rows, t.schema)
d = t.to_pydict(); print({k: d[k][:3] for k in d})
print("min/max", min(d["Start"]), max(d["Start"]))
print("HOTOVO")
