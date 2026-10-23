# Kam sa presunuli otvorené dáta volieb ŠÚ SR? Len stavové kódy a odkazy.
import requests, re
s = requests.Session(); s.headers["User-Agent"] = "Mozilla/5.0 (mestovcislach.sk diag)"
def g(u):
    try:
        r = s.get(u, timeout=40, allow_redirects=True); return r
    except Exception as e: print(u, type(e).__name__); return None
for u in ["https://volby.statistics.sk/opendata/nrsr/2023/NRSR2023_SK_tab02d.csv", "https://volbysr.sk/opendata/nrsr/2023/NRSR2023_SK_tab02d.csv",
          "https://volby.statistics.sk/oso/oso2022/files/OSO2022_SK_csv.zip", "https://volby.statistics.sk/osk/osk2022/files/OSK2022_SK_csv.zip",
          "https://volby.statistics.sk/nrsr/nrsr2023/sk/", "https://volby.statistics.sk/", "https://volbysr.sk/", "https://volbysr.sk/opendata/",
          "https://volby.statistics.sk/opendata/eup/2024/EP2024_SK_tab02d.csv", "https://volbysr.sk/nrsr/nrsr2023/sk/", "https://volbysr.sk/oso/oso2022/files/OSO2022_SK_csv.zip"]:
    r = g(u)
    if r is not None:
        print(u, r.status_code, r.url if r.url != u else "", r.headers.get("content-type"), len(r.content))
        if "html" in (r.headers.get("content-type") or "") and r.status_code == 200 and u.endswith("/"):
            print("   ", sorted(set(h for h in re.findall(r'href="([^"]+)"', r.text) if "statistics" not in h or "volby" in h))[:50])
q = ('PREFIX dcat:<http://www.w3.org/ns/dcat#> PREFIX dct:<http://purl.org/dc/terms/> SELECT DISTINCT ?url WHERE { ?d dcat:downloadURL ?url . '
     'FILTER(CONTAINS(LCASE(STR(?url)),"nrsr2023") || CONTAINS(LCASE(STR(?url)),"oso2022") || CONTAINS(LCASE(STR(?url)),"ep2024")) } LIMIT 40')
try:
    r = s.get("https://data.slovensko.sk/api/sparql", params={"query": q}, headers={"Accept": "application/sparql-results+json"}, timeout=90).json()
    print("NKOD:", [b["url"]["value"] for b in r["results"]["bindings"]])
except Exception as e: print("NKOD", e)
