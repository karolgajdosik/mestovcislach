import subprocess, sys; subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", "scripts/requirements.txt"])
import re, requests, io, zipfile, json
sys.path.insert(0, "scripts")
s = requests.Session(); s.headers["User-Agent"] = "Mozilla/5.0 (compatible; mestovcislach.sk)"
def g(u, **k):
    try:
        r = s.get(u, timeout=60, **k); return r
    except Exception as e:
        print("ERR", u, str(e)[:150]); return None
def links(u, pat, n=40):
    r = g(u)
    if r is None: return
    print("==", u, r.status_code, len(r.text))
    for m in sorted(set(re.findall(r'href="([^"]+)"', r.text))):
        if re.search(pat, m, re.I): print("  ", m[:220]); n -= 1
        if n <= 0: break
links("https://www.apa.sk/", r"prijim|zverej|opendata|otvoren")
links("https://www.uvo.gov.sk/", r"otvoren|opendata|api|data")
r = g("https://datahub.ekosystem.slovensko.digital/api/data/vvo/notices/sync"); print("DH", r.status_code if r is not None else None, (r.text[:300] if r is not None else ""))
links("https://www.ssc.sk/sk/cestna-databanka/celostatne-scitanie-dopravy.ssc", r"scitan|xls|zip|csv|2022|mapa")
for u in ["https://ags.geology.sk/arcgis/rest/services?f=json", "https://apl.geology.sk/arcgis/rest/services?f=json", "https://gis.geology.sk/arcgis/rest/services?f=json"]:
    r = g(u); print("GEO", u, r.status_code if r is not None else None, (r.text[:500] if r is not None else ""))
# STATdata population long series
from statdata_obce import B, H
for k in ["om7102rr", "om7002rr", "om7001rr", "om7101rr", "om7103rr"]:
    try:
        i = s.get(f"{B}/public/{k}/info", headers=H, timeout=60).json()
        print("STAT", k, i.get("nameSk", "")[:120], [(d["acronym"], d.get("type")) for d in i["dimensions"]], i.get("timeRange") or i.get("periodFrom"), i.get("periodTo"))
    except Exception as e: print("STAT ERR", k, e)
# OSO2022 zip
r = g("https://volby.statistics.sk/oso/oso2022/files/OSO2022_SK_csv.zip")
if r is not None and r.content[:2] == b"PK":
    z = zipfile.ZipFile(io.BytesIO(r.content)); print("OSO", z.namelist())
    for n in z.namelist():
        if re.search(r"tab0[3-9]", n): print("  HEAD", n, z.read(n)[:400].decode("utf-8", "replace").replace("\n", " | "))
# Open-Meteo
r = g("https://archive-api.open-meteo.com/v1/archive", params={"latitude": 48.55, "longitude": 19.33, "start_date": "2016-01-01", "end_date": "2025-12-31", "daily": "temperature_2m_mean,temperature_2m_max,temperature_2m_min,precipitation_sum,snowfall_sum", "models": "era5", "timezone": "Europe/Bratislava"})
print("OM", r.status_code if r is not None else None, (r.text[:300] if r is not None else ""))
print("HOTOVO")
