import subprocess, sys; subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", "scripts/requirements.txt"])
import re, requests, json
sys.path.insert(0, "scripts")
s = requests.Session(); s.headers["User-Agent"] = "Mozilla/5.0 (compatible; mestovcislach.sk)"
def g(u, **k):
    try: return s.get(u, timeout=60, **k)
    except Exception as e: print("ERR", u, str(e)[:120]); return None
def links(u, pat, n=30):
    r = g(u)
    if r is None: return None
    print("==", u, r.status_code, len(r.text))
    for m in sorted(set(re.findall(r'href="([^"]+)"', r.text))):
        if re.search(pat, m, re.I): print("  ", m[:200]); n -= 1
        if n <= 0: break
    return r
# a) UPSVR years
import zber_obce_temy as zt
r = g(zt.UPSVR_OBCE)
roky = sorted(set(re.findall(r'href="(https://www\.upsvr\.gov\.sk/statistiky/mesacne-statistiky-miest-a-obci/(\d{4})\.html\?page_id=\d+)"', r.text)), key=lambda x: x[1])
print("ROKY", [x[1] for x in roky])
for url, rok in roky[:1] + roky[len(roky)//2:len(roky)//2+1]:
    t = g(url).text
    print("  ", rok, [u for u in re.findall(r'href="([^"]+\.xlsx?)"', t)][:14])
# b) STATdata MČ names
from statdata_obce import riadky_obce
rr = riadky_obce("om7101rr", rokov=1, vyber={"e_sex": ["Spolu"]})
nm = sorted({x.get("e_nuts15", "").strip() for x in rr if re.search("Bratislava|Košice", x.get("e_nuts15", "") + x.get("e_nuts14", ""))})
print("MC", len(nm), nm[:50])
# c) NIVAM maturita
for u in ["https://dataportal.nucem.sk/Dataportal-web/web/vysledky/index.xhtml", "https://dataportal.nucem.sk/Dataportal-web/web/vysledky/2025/maturita/index.xhtml"]:
    r = links(u, r"matur|vysledky/20")
    if r is not None and "maturita" in u: print("  links35", re.findall(r"'j_idt\d+:(j_idt\d+)':'j_idt\d+:j_idt\d+'\},''\);return false\">([^<]*)<", r.text)[:20])
# e) STATdata search byty
from statdata_obce import B, H
try:
    r = s.post(f"{B}/public/api/dc/public/bulkDownload/search", json={"searchText": "dokončené byty"}, headers=H, timeout=60)
    print("SEARCH", r.status_code, r.text[:1500])
except Exception as e: print("SEARCH ERR", e)
# h) nehody
links("https://www.minv.sk/lnisdn/statistika/20260218_011722.691_2025-12-MS/statistika/index-public.html", r"okres|rocn|dn", 60)
# i) NRO
links("https://www.upsvr.gov.sk/", r"najmenej|nro|rozvinut")
# f) SP
links("https://www.socpoist.sk/", r"statist|dochod")
# j) Wikidata counts
q = """SELECT (COUNT(DISTINCT ?o) AS ?n) (COUNT(DISTINCT ?e) AS ?erb) (COUNT(DISTINCT ?f) AS ?foto) (COUNT(DISTINCT ?p) AS ?part) WHERE { ?o wdt:P17 wd:Q214; wdt:P782 ?lau . OPTIONAL{?o wdt:P94 ?e} OPTIONAL{?o wdt:P18 ?f} OPTIONAL{?o wdt:P190 ?p} }"""
r = s.get("https://query.wikidata.org/sparql", params={"query": q, "format": "json"}, timeout=120)
print("WD", r.json()["results"]["bindings"])
print("HOTOVO")
