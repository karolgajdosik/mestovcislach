import subprocess, sys, json, re, io, zipfile, requests
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", "scripts/requirements.txt", "openpyxl"])
sys.path.insert(0, "scripts")
from spolocne import s
HB = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/130 Safari/537.36"}
WH = {"User-Agent": "mestovcislach.sk/1.0 (info@mestovcislach.sk)"}
q = """SELECT ?o ?lau ?zm ?vys ?erb WHERE { ?o wdt:P17 wd:Q214 ; wdt:P782 ?lau . OPTIONAL{?o wdt:P1249 ?zm} OPTIONAL{?o wdt:P2044 ?vys} OPTIONAL{?o wdt:P94 ?erb} }"""
r = requests.get("https://query.wikidata.org/sparql", params={"query": q, "format": "json"}, headers=WH, timeout=180)
b = r.json()["results"]["bindings"]
print("WD", len(b), "zm", sum("zm" in x for x in b), "vys", sum("vys" in x for x in b), "erb", sum("erb" in x for x in b))
for x in b[:6]: print("  ", {k: v["value"][:90] for k, v in x.items()})
import collections
print("  lau formy", collections.Counter(re.sub(r"\d", "9", x["lau"]["value"]) for x in b).most_common(5))
r = requests.get("https://volby.statistics.sk/", headers=HB, timeout=60)
print("HOME", sorted(set(re.findall(r'href="([^"#]+)"', r.text)))[:80])
for u in ["https://volby.statistics.sk/ref/ref2023/sk/download.html", "https://volby.statistics.sk/referendum/ref2023/sk/download.html", "https://volby.statistics.sk/ref/2023/sk/download.html", "https://volby.statistics.sk/osk/vuc2022/sk/download.html", "https://volby.statistics.sk/kom/kom2022/sk/data02.html", "https://volby.statistics.sk/oso/oso2022/sk/download.html", "https://volby.statistics.sk/osk/osk2022/sk/data01.html", "https://volby.statistics.sk/vuc/vuc2022/sk/download.html", "https://volby.statistics.sk/oso2022/sk/download.html"]:
    try:
        r = requests.get(u, headers=HB, timeout=60); print("VOL", u, r.status_code, sorted(set(re.findall(r'href="([^"]+\.(?:csv|zip|xlsx)[^"]*)"', r.text, re.I)))[:12])
    except Exception as e: print("VOL", u, e)
z = zipfile.ZipFile(io.BytesIO(requests.get("https://volby.statistics.sk/nrsr/nrsr2020/files/NRSR_2020_SK_csv.zip", headers=HB, timeout=300).content))
print("NRSR2020", z.namelist()[:30])
import openpyxl
z = zipfile.ZipFile(io.BytesIO(requests.get("https://volby.statistics.sk/prez/prez2019/files/PRE_2019_KOLO1_xlsx.zip", headers=HB, timeout=300).content))
print("PREZ2019", z.namelist()[:30])
q2 = '[out:json][timeout:300];area["ISO3166-1"="SK"][admin_level=2]->.sk;nwr[shop=supermarket](area.sk);out count;'
try:
    r = s.post("https://overpass-api.de/api/interpreter", data={"data": q2}, timeout=400); print("OSM", r.status_code, r.text[:300])
except Exception as e: print("OSM", e)
qq = """PREFIX dcat:<http://www.w3.org/ns/dcat#> PREFIX dct:<http://purl.org/dc/terms/>
SELECT DISTINCT ?ds ?t WHERE { ?ds dct:title ?t . FILTER(REGEX(STR(?t), "^Register adries", "i")) } LIMIT 60"""
r = requests.get("https://data.slovensko.sk/api/sparql", params={"query": qq}, headers={"Accept": "application/sparql-results+json"}, timeout=120)
for x in r.json()["results"]["bindings"]: print("RA", x["ds"]["value"].rsplit("/",1)[-1][:40], x["t"]["value"][:90])
print("HOTOVO")
