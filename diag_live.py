import subprocess, sys; subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", "scripts/requirements.txt"])
import re, requests, json, io
s = requests.Session(); s.headers["User-Agent"] = "Mozilla/5.0 (compatible; mestovcislach.sk)"
# SP xlsx
import openpyxl
u = "https://www.socpoist.sk/sites/default/files/2026-02/%C5%A0tatistick%C3%A9%20%C3%BAdaje%20z%20oblasti%20d%C3%B4chodkov%C3%A9ho%20poistenia%20rok%202025.xlsx"
r = s.get(u, timeout=120); print("SP", r.status_code, len(r.content))
try:
    wb = openpyxl.load_workbook(io.BytesIO(r.content), read_only=True, data_only=True)
    for ws in wb.worksheets:
        rows = list(ws.iter_rows(values_only=True, max_row=8))
        txt = " ".join(str(c) for row in rows for c in row if c)[:200]
        okres = any("okres" in str(c).lower() or "Bardejov" in str(c) for row in ws.iter_rows(values_only=True, max_row=200) for c in row if c)
        print("  SHEET", ws.title, okres, txt)
except Exception as e: print("SP ERR", e)
# nehody: sko section
r = s.get("https://www.minv.sk/lnisdn/statistika/20260218_011722.691_2025-12-MS/statistika/index-public.html", timeout=60)
r.encoding = "utf-8"
t = r.text
i = t.find('id="rozc-sko"'); seg = t[i:i+20000] if i >= 0 else ""
print("SKO", len(seg), re.findall(r'href="([^"]+)"[^>]*>([^<]{0,60})', seg)[:40])
seg2 = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " | ", seg))[:2500]; print("SKOTXT", seg2)
# NRO
r = s.get("https://mirri.gov.sk/sekcie/regionalny-rozvoj-2/najmenej-rozvinute-okresy/okresy/", timeout=60)
print("NRO", r.status_code, sorted(set(re.findall(r'/najmenej-rozvinute-okresy/okresy/([a-z-]+)/', r.text))))
tx = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", r.text)); j = tx.find("zoznam"); print("NROTXT", tx[j:j+800] if j >= 0 else tx[:300])
# vozidla
for u in ["https://www.minv.sk/?statistiky-20", "https://www.minv.sk/?celkovy-pocet-evidovanych-vozidiel-v-sr"]:
    try:
        r = s.get(u, timeout=60); print("VOZ", u, r.status_code, [h for h in re.findall(r'href="([^"]+)"', r.text) if re.search(r"vozid|xls|statist", h, re.I)][:25])
    except Exception as e: print("VOZ ERR", e)
# EEA AQ
try:
    r = s.post("https://eeadmz1-downloads-api-appservice.azurewebsites.net/ParquetFile/urls", json={"countries": ["SK"], "cities": [], "pollutants": ["PM10"], "dataset": 1, "source": "Api", "dateTimeStart": "2025-01-01T00:00:00Z", "dateTimeEnd": "2025-12-31T23:59:59Z", "aggregationType": "day"}, timeout=120)
    print("EEA", r.status_code, r.text[:600])
except Exception as e: print("EEA ERR", e)
try:
    r = s.get("https://discomap.eea.europa.eu/App/AQViewer/download?fqn=Airquality_Dissem.b2g.AirQualityStatistics&f=csv&filter=Country%3D%27Slovakia%27", timeout=120)
    print("EEA2", r.status_code, r.headers.get("content-type"), r.text[:500])
except Exception as e: print("EEA2 ERR", e)
print("HOTOVO")
