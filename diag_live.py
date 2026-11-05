import re, io, json, requests
H = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/130 Safari/537.36"}
def g(u, **kw):
    try: return requests.get(u, headers={**H, **kw.pop("h", {})}, timeout=60, **kw)
    except Exception as e: print("ERR", u, str(e)[:150]); return None
# ÚPSVaR mesačný xlsx – hárky
import openpyxl
r = g("https://www.upsvr.gov.sk/buxus/docs/statistic/mesacne/2026/UoZaVPM_MS_2609.xlsx")
if r is not None and r.content[:2] == b"PK":
    wb = openpyxl.load_workbook(io.BytesIO(r.content), read_only=True)
    print("xlsx hárky:", wb.sheetnames)
r = g("https://www.upsvr.gov.sk/statistiky/nezamestnanost-mesacne-statistiky/2026.html?page_id=1254")
if r is not None:
    print(sorted(set(re.findall(r'href="([^"]*buxus/docs[^"]+)"', r.text)))[:60])
    print([t for t in re.findall(r">([^<]{8,120})<", r.text) if re.search(r"obc|obce|okres", t, re.I)][:30])
# ITMS 2014 s hlavičkami
for h in [{"Accept": "application/json"}, {"User-Agent": "curl/8.5.0", "Accept": "*/*"}]:
    r = g("https://opendata.itms2014.sk/v2/projekty/ukoncene?limit=1", h=h)
    if r is not None: print("itms", h, r.status_code, r.text[:200].replace("\n", " "))
# Kohesio
for u in ["https://kohesio.ec.europa.eu/api/facet/eu-countries?language=sk", "https://kohesio.ec.europa.eu/sk/data-download", "https://kohesio.ec.europa.eu/api/search/project?country=https%3A%2F%2Flinkedopendata.eu%2Fentity%2FQ218&language=sk&limit=1"]:
    r = g(u)
    if r is not None: print(u, r.status_code, r.text[:400].replace("\n", " "))
# CVTI adresár
r = g("https://www.cvtisr.sk/skolstvo/regionalne-skolstvo/adresar-skol.html?page_id=9599")
if r is not None:
    print([x for x in set(re.findall(r'href="([^"]+)"', r.text)) if re.search(r"adres|zoznam|skol.*\.(xls|csv|zip)", x, re.I)][:40])
# STATdata katalóg
r = g("https://statdata.statistics.sk/public/api/dc/v3/api-docs")
if r is not None and r.ok:
    print("statdata paths:", list(r.json().get("paths", {}))[:60])
print("HOTOVO")
