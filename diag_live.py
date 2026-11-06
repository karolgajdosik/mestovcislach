import subprocess, sys; subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", "scripts/requirements.txt"])
import re, requests, io, zipfile, json
sys.path.insert(0, "scripts")
s = requests.Session(); s.headers["User-Agent"] = "Mozilla/5.0 (compatible; mestovcislach.sk)"
def g(u, **k):
    try: return s.get(u, timeout=90, **k)
    except Exception as e: print("ERR", u, str(e)[:150]); return None
r = g("https://sdi.eea.europa.eu/webdav/datastore/public/")
if r is not None:
    print("EEA", r.status_code, [m for m in re.findall(r'href="([^"]+)"', r.text) if "ied" in m.lower() or "eprtr" in m.lower()][:20])
for v in ["eea_t_ied-eprtr_p_2007-2022_v11_r00", "eea_t_ied-eprtr_p_2007-2023_v12_r00", "eea_t_ied-eprtr_p_2007-2023_v13_r00"]:
    r = g(f"https://sdi.eea.europa.eu/webdav/datastore/public/{v}/")
    if r is not None: print("EEADIR", v, r.status_code, re.findall(r'href="([^"]+)"', r.text)[:30])
# geology services
def walk(folder):
    r = g(f"https://ags.geology.sk/arcgis/rest/services/{folder}?f=json")
    try: return r.json().get("services", [])
    except Exception: return []
for f in ["Atlasy", "GeologickeMapy", "MapovyPortal", "TematickeAplikacie", "WebServices", "wgs_atlasy", "wgs_geologickeMapy", "Geofond", "wgs_geofond", "Zranitelnost", "Monitoring"]:
    sv = walk(f)
    hit = [x["name"] for x in sv if re.search(r"svah|zosuv|deform|geohaz|rizik|radon", x["name"], re.I)]
    print("GEO", f, len(sv), hit[:10])
# cdb
for u in ["https://www.cdb.sk/sk/statisticke-udaje/Celostatne-scitanie-dopravy.alej", "https://www.cdb.sk/sk/Celostatne-scitanie-dopravy.alej", "https://www.cdb.sk/sk/Mapa-stranky.alej"]:
    r = g(u)
    if r is not None:
        print("CDB", u, r.status_code, [m for m in re.findall(r'href="([^"]+)"', r.text) if re.search(r"scitan|xls|zip|2022", m, re.I)][:20])
# RPO
r = g("https://api.statistics.sk/rpo/v1/search", params={"fullName": "Technické služby Detva"})
print("RPO", r.status_code if r is not None else None, (r.text[:1500] if r is not None else ""))
# om7101rr
from statdata_obce import B, H, polozky
i = s.get(f"{B}/public/om7101rr/info", headers=H, timeout=60).json()
for d in i["dimensions"]:
    if d["acronym"] in ("e_indic", "e_year", "e_unit"):
        it = [x.get("nameSk") for x in polozky("om7101rr", d["id"])]
        print("OM7101", d["acronym"], len(it), it[:6], it[-3:])
# OSO candidates
r = g("https://volby.statistics.sk/oso/oso2022/files/OSO2022_SK_csv.zip")
z = zipfile.ZipFile(io.BytesIO(r.content))
for n in ["OSO2022_SK_tab0ad.csv", "OSO2022_SK_tab0bd.csv", "OSO2022_SK_tab0c.csv", "OSO2022_SK_tab0dd.csv", "OSO2022_SK_tab02ad.csv", "OSO2022_SK_tab_info.csv"]:
    print("  HEAD", n, z.read(n)[:350].decode("utf-8", "replace").replace("\n", " | ").replace("\r", ""))
print("HOTOVO")
