import subprocess, sys; subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", "scripts/requirements.txt"])
import re, requests, io, html
s = requests.Session(); s.headers["User-Agent"] = "Mozilla/5.0 (compatible; mestovcislach.sk)"
# vozidla
r = s.get("https://www.minv.sk/?celkovy-pocet-evidovanych-vozidiel-v-sr", timeout=60)
pairs = re.findall(r'href="(/\?celkovy-pocet-evidovanych-vozidiel-v-sr&amp;subor=\d+)"[^>]*>([^<]+)<', r.text)
ok = [(h, t) for h, t in pairs if "okres" in t.lower()]
print("VOZ okres", ok[:5])
if ok:
    u = "https://www.minv.sk" + html.unescape(ok[0][0])
    x = s.get(u, timeout=120); print("VOZDL", x.status_code, x.headers.get("content-type"), len(x.content), x.content[:4])
    import openpyxl
    try:
        wb = openpyxl.load_workbook(io.BytesIO(x.content), read_only=True, data_only=True)
        for ws in wb.worksheets[:3]:
            rows = list(ws.iter_rows(values_only=True, max_row=12)); print("  SHEET", ws.title, ws.max_row, ws.max_column)
            for rr in rows: print("    ", [c for c in rr][:14])
    except Exception as e: print("VOZ ERR", e)
# nehody listing
r = s.get("https://www.minv.sk/lnisdn/statistika/", timeout=60); print("LIST", r.status_code, len(r.text), re.findall(r'href="([^"]*-12-MS[^"]*)"', r.text)[-5:])
B = "https://www.minv.sk/lnisdn/statistika/20260218_011722.691_2025-12-MS/statistika/"
r = s.get(B + "index-public.html", timeout=60); r.encoding = "utf-8"
ok = re.findall(r"href='(mesacna/dkvr/dkvr-[^']+\.html)' title='([^']+)'", r.text)
print("DKVR", len(ok), ok[:3], ok[-3:])
okr = [o for o in ok if "okres" in o[1].lower()]
if okr:
    x = s.get(B + okr[0][0], timeout=60); x.encoding = "utf-8"
    print("OKR", okr[0], re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " | ", x.text))[:1800])
# EEA metadata + parquet
for u in ["https://discomap.eea.europa.eu/map/fme/metadata/PanEuropean_metadata.csv", "https://eeadmz1-downloads-webapp.azurewebsites.net/content/documentation/How_To_Downloads.pdf"]:
    try:
        x = s.get(u, timeout=120); print("META", u, x.status_code, len(x.content), x.text[:300].replace("\n", " | "))
    except Exception as e: print("META ERR", u, e)
import pyarrow.parquet as pq
x = s.get("https://eeadmz1batchservice02.blob.core.windows.net/airquality-p-e1a/SK/SPO-SK0004A_00005_100.parquet", timeout=120)
t = pq.read_table(io.BytesIO(x.content)).to_pandas(); print("PQ", t.shape, list(t.columns)); print(t.head(3).to_string()); print(t["Start"].min(), t["Start"].max())
print("HOTOVO")
