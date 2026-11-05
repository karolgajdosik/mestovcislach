import re, json, requests
from concurrent.futures import ThreadPoolExecutor
H = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/130 Safari/537.36", "Accept": "application/json"}
B = "https://statdata.statistics.sk/public/api/dc"
kody = {}
for page in range(0, 40):
    try:
        j = requests.post(B + "/public/bulkDownload/search", json={"query": "", "page": page, "size": 100}, headers=H, timeout=90).json()
    except Exception as e:
        print("kat", e); break
    items = j.get("content") if isinstance(j, dict) else j
    if not items: break
    for it in items:
        s = json.dumps(it, ensure_ascii=False)
        k = re.search(r'"([a-z]{2}\d{4}[a-z]{2})"', s)
        nm = re.search(r'"(?:nameSk|title|name)"\s*:\s*"([^"]+)"', s)
        if k: kody[k.group(1)] = nm.group(1) if nm else s[:100]
    if isinstance(j, dict) and j.get("last"): break
print("kociek", len(kody))
KL = r"mzd|mzda|dôchod|krimin|trestn|dokonč|výstavb|bytov|dochádz|sociáln|nehod|dávk|hmotnej núdz|exekú|pobera|príspevk"
vyb = {k: n for k, n in kody.items() if re.search(KL, n, re.I)}
def info(k):
    try:
        t = requests.get(f"{B}/public/{k}/info", headers=H, timeout=60).json()
        geo = [d["acronym"] for d in t["dimensions"] if d["type"] == "GEO"]
        return k, geo, t.get("timePeriodTo")
    except Exception as e: return k, str(e)[:40], None
with ThreadPoolExecutor(8) as ex:
    for k, geo, tp in ex.map(info, sorted(vyb)):
        print("KOCKA", k, geo, tp, "|", vyb[k][:110])
# data.slovensko SPARQL
q = """PREFIX dcat:<http://www.w3.org/ns/dcat#> PREFIX dct:<http://purl.org/dc/terms/>
SELECT DISTINCT ?ds ?t WHERE { ?ds a dcat:Dataset ; dct:title ?t . FILTER(REGEX(STR(?t), "gtfs|dochádz|podiel.*dan|daň.*obc|sociálnych služieb|povod|chránen|pokryt|širokopás|kriminal|trestn|internet|cestovn.*poriad|autobus|záplav|natura", "i")) } LIMIT 300"""
try:
    r = requests.get("https://data.slovensko.sk/api/sparql", params={"query": q}, headers={"Accept": "application/sparql-results+json"}, timeout=120)
    for b in r.json()["results"]["bindings"]:
        print("NKOD", b["ds"]["value"].rsplit("/",1)[-1], "|", b["t"]["value"][:120])
except Exception as e: print("sparql", e)
for u in ["https://www.minv.sk/?statistika-kriminality-v-slovenskej-republike-xml", "https://www.minv.sk/?kriminalita-1", "https://www.mfsr.sk/sk/financie/verejne-financie/financie-uzemnej-samospravy/", "https://www.finance.gov.sk/sk/financie/verejne-financie/financie-uzemnej-samospravy/", "https://www.minzp.sk/voda/ochrana-pred-povodnami/", "https://www.svp.sk/sk/menu/tematicke-oblasti/ochrana-pred-povodnami/", "https://maps.sopsr.sk/", "https://ssad.statistics.sk/SSaD/?dl_id=400", "https://www.scitanie.sk/"]:
    try:
        r = requests.get(u, headers=H, timeout=60)
        odk = sorted(set(re.findall(r'href="([^"]+)"', r.text)))
        zaujim = [o for o in odk if re.search(r"xls|csv|zip|krimin|podiel|dan|povod|mapy|wfs|wms|rest|dochádz|dochadz|open", o, re.I)]
        print("URL", u, r.status_code, len(r.text), zaujim[:40])
    except Exception as e: print("URL", u, e)
q2 = '[out:json][timeout:120];area["ISO3166-1"="SK"][admin_level=2]->.sk;(relation[boundary=national_park](area.sk);relation[boundary=protected_area](area.sk););out tags;'
try:
    r = requests.post("https://overpass-api.de/api/interpreter", data={"data": q2}, timeout=200)
    from collections import Counter
    el = r.json()["elements"]; c = Counter((e["tags"].get("boundary"), e["tags"].get("protect_class"), e["tags"].get("protection_title")) for e in el)
    print("OSM chránené", len(el)); [print("  ", k, v) for k, v in c.most_common(25)]
except Exception as e: print("osm", e)
print("HOTOVO")
