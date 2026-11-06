import subprocess, sys, json, re, requests, time
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", "scripts/requirements.txt"])
sys.path.insert(0, "scripts")
from statdata_obce import polozky, B, H
from spolocne import s
for k in ["om7006rr", "om7008rr", "om7101mr", "om7822rr", "om7823rr", "om7818rr", "om7820rr", "om7819rr", "om7817rr", "om7807rr", "om7808rr", "ku5003rr", "ku5005rr", "ku5006rr", "ku5011rr", "vh5003rr"]:
    try:
        info = s.get(f"{B}/public/{k}/info", headers=H, timeout=60).json()
        print("==", k, info.get("nameSk"), info.get("timePeriodTo"))
        for d in info["dimensions"]:
            if d["acronym"] in ("e_nuts15", "e_nuts14"): continue
            p = polozky(k, d["id"])
            nm = [(x.get("nameSk") or "")[:40] for x in p]
            print("  ", d["acronym"], d["type"], len(p), nm[-6:] if d["type"] == "TIME" else nm[:30])
    except Exception as e:
        print("==", k, "CHYBA", str(e)[:200])
HB = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/130 Safari/537.36"}
for u in ["https://volby.statistics.sk/opendata/", "https://volby.statistics.sk/", "https://volby.statistics.sk/ref/ref2023/sk/download.html", "https://volby.statistics.sk/nrsr/nrsr2020/sk/download.html", "https://volby.statistics.sk/prez/prez2019/sk/download.html", "https://volby.statistics.sk/osk/osk2022/sk/download.html", "https://volby.statistics.sk/oso/oso2022/sk/download.html", "https://volby.statistics.sk/kom/kom2022/sk/download.html", "https://volby.statistics.sk/prez/prez2024/sk/download.html"]:
    try:
        r = requests.get(u, headers=HB, timeout=60)
        odk = sorted(set(re.findall(r'href="([^"]+\.(?:csv|zip|xlsx)[^"]*)"', r.text, re.I)))
        print("VOL", u, r.status_code, len(r.text), odk[:25])
    except Exception as e: print("VOL", u, e)
q = """SELECT ?kod ?zm ?vys ?erb WHERE { ?o wdt:P7606 ?kod . OPTIONAL{?o wdt:P1249 ?zm} OPTIONAL{?o wdt:P2044 ?vys} OPTIONAL{?o wdt:P94 ?erb} }"""
try:
    r = requests.get("https://query.wikidata.org/sparql", params={"query": q, "format": "json"}, headers={"User-Agent": "mestovcislach.sk/1.0 (info@mestovcislach.sk)"}, timeout=120)
    b = r.json()["results"]["bindings"]
    print("WD", r.status_code, len(b), "zmienka", sum(1 for x in b if "zm" in x), "vyska", sum(1 for x in b if "vys" in x), "erb", sum(1 for x in b if "erb" in x)); print(b[:3])
except Exception as e: print("WD", e)
for prop in ["P7606", "P3832", "P782"]:
    try:
        r = requests.get("https://query.wikidata.org/sparql", params={"query": f"SELECT (COUNT(*) AS ?n) WHERE {{ ?o wdt:{prop} ?k . ?o wdt:P17 wd:Q214 }}", "format": "json"}, headers={"User-Agent": "mestovcislach.sk/1.0 (info@mestovcislach.sk)"}, timeout=120)
        print("WDprop", prop, r.json()["results"]["bindings"])
    except Exception as e: print("WDprop", prop, e)
q2 = '[out:json][timeout:300];area["ISO3166-1"="SK"][admin_level=2]->.sk;(nwr[shop=supermarket](area.sk);nwr[amenity=charging_station](area.sk);nwr[leisure=playground](area.sk);nwr[amenity~"^(restaurant|pub|cafe)$"](area.sk););out count;'
try:
    r = requests.post("https://overpass-api.de/api/interpreter", data={"data": q2}, timeout=400); print("OSM", r.status_code, r.text[:400])
except Exception as e: print("OSM", e)
qq = """PREFIX dcat:<http://www.w3.org/ns/dcat#> PREFIX dct:<http://purl.org/dc/terms/>
SELECT ?ds ?t ?u WHERE { ?ds dct:title ?t . ?ds dcat:distribution ?d . OPTIONAL{?d dcat:downloadURL ?u} FILTER(REGEX(STR(?t), "register adries|Register adries|RA - ", "i")) } LIMIT 40"""
try:
    r = requests.get("https://data.slovensko.sk/api/sparql", params={"query": qq}, headers={"Accept": "application/sparql-results+json"}, timeout=120)
    for b in r.json()["results"]["bindings"]: print("RA", b["ds"]["value"].rsplit("/",1)[-1][:14], b["t"]["value"][:70], b.get("u",{}).get("value","-")[:150])
except Exception as e: print("RA", e)
print("HOTOVO")
