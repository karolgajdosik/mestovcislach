import re, requests, json
s = requests.Session(); s.headers["User-Agent"] = "mestovcislach.sk (info@mestovcislach.sk)"
def g(u, **k):
    try:
        r = s.get(u, timeout=60, **k); return r
    except Exception as e:
        print("ERR", u, str(e)[:150]); return None
def links(u, pat):
    r = g(u)
    if r is None: return
    print("==", u, r.status_code, len(r.text))
    for m in sorted(set(re.findall(r'href="([^"]+)"', r.text))):
        if re.search(pat, m, re.I): print("  ", m[:200])
links("https://opendata.mfsr.sk/", r"obc|rozpo|fin|show")
links("https://opendata.mfsr.sk/mi/opendata", r"obc|rozpo|fin|show")
links("https://www.apa.sk/", r"prijim|zoznam|zverej")
links("https://www.apa.sk/zoznam-prijimatelov", r"xls|csv|zip|prijim|rok")
links("https://www.nivam.sk/", r"testovanie|vysledk")
links("https://skoly.ineko.sk/", r"data|csv|xls|stiah")
links("https://www.datacentrum.sk/", r"open|data|ris|sam")
# SOP layers
r = g("https://www.sopsr.sk/geoserver/ows", params={"service":"WFS","request":"GetCapabilities","version":"2.0.0"})
if r is not None:
    print("SOP", r.status_code); print(sorted(set(re.findall(r"<(?:wfs:)?Name>([^<]+)</", r.text)))[:200])
# STATdata og3805rr legal forms
B="https://data.statistics.sk/api/v2"
try:
    import sys; sys.path.insert(0,"scripts")
    from statdata_obce import B, H, polozky
    info = s.get(f"{B}/public/og3805rr/info", headers=H, timeout=60).json()
    for d in info["dimensions"]:
        if "legal" in d["acronym"]:
            print("og3805rr forms:", [x.get("nameSk") for x in polozky("og3805rr", d["id"])])
except Exception as e: print("STAT ERR", e)
# Wikidata NKP
q = """SELECT ?d ?dl (COUNT(?x) AS ?n) WHERE { ?x wdt:P17 wd:Q214; wdt:P1435 ?d . ?d rdfs:label ?dl FILTER(lang(?dl)="sk") } GROUP BY ?d ?dl ORDER BY DESC(?n) LIMIT 15"""
r = s.get("https://query.wikidata.org/sparql", params={"query": q, "format": "json"}, timeout=120)
for b in r.json()["results"]["bindings"]: print("WD", b["d"]["value"], b["dl"]["value"], b["n"]["value"])
print("HOTOVO")
