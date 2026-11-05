import subprocess, sys, json, collections
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", "scripts/requirements.txt"])
sys.path.insert(0, "scripts")
from statdata_obce import riadky_obce, B, H
from spolocne import s
for k in sys.argv[1:] or ["pl5001rr", "om7809rr", "om7804rr", "om7805rr", "om7806rr", "om7803rr"]:
    try:
        info = s.get(f"{B}/public/{k}/info", headers=H, timeout=60).json()
        print("==", k, info.get("nameSk"), info.get("timePeriodTo"), [(d["acronym"], d["type"]) for d in info["dimensions"]])
        rr = riadky_obce(k, rokov=1)
        print("   riadkov", len(rr), "stlpce", list(rr[0].keys()) if rr else None)
        for c in (rr[0] if rr else {}):
            if c in ("hodnota", "e_nuts15"): continue
            v = collections.Counter(x[c].strip() for x in rr)
            print("   ", c, len(v), [x[:70] for x in list(v)[:45]])
        for x in [x for x in rr if x["e_nuts15"].startswith("Vígľaš")][:60]:
            print("    V:", {a: b.strip()[:50] for a, b in x.items() if a not in ("e_nuts15",)})
    except Exception as e:
        print("==", k, "CHYBA", str(e)[:300])
import io, zipfile, csv, requests, re
HH = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/130 Safari/537.36"}
def okresna(kod):
    info = s.get(f"{B}/public/{kod}/info", headers=H, timeout=60).json()
    dims = [d for d in info["dimensions"]]
    cas = next(d["acronym"] for d in dims if d["type"] == "TIME")
    ine = [d["acronym"] for d in dims if d["acronym"] != cas]
    rows = "~".join(f"{d},ASC,all" for d in ine[:-1]); ctx = f"{ine[-1]},ASC,all"
    u = f"{B}/opendata/cube/dataset/{kod}/rows/{rows}/columns/{cas},ASC,all/context/{ctx}"
    r = requests.get(u, params={"type": "CSV", "lang": "SK"}, headers=HH, timeout=600); c = r.content
    if c[:2] == b"PK": z = zipfile.ZipFile(io.BytesIO(c)); c = z.read(z.namelist()[0])
    rr = list(csv.DictReader(io.StringIO(c.decode("utf-8-sig", "replace"))))
    print("== OKRES", kod, info.get("nameSk"), info.get("timePeriodTo"), "ctx", ine[-1], "riadkov", len(rr), list(rr[0].keys()) if rr else r.status_code)
    for c_ in (rr[0] if rr else {}):
        v = collections.Counter(x[c_].strip() for x in rr); print("   ", c_, len(v), [x[:60] for x in list(v)[:30]])
    for x in [x for x in rr if "Detva" in json.dumps(x, ensure_ascii=False)][:20]: print("    D:", {a: b.strip()[:40] for a, b in x.items()})
for k in ["np3110rr", "st3802rr", "so3801rr"]:
    try: okresna(k)
    except Exception as e: print("OKRES", k, "CHYBA", str(e)[:200])
q = """PREFIX dcat:<http://www.w3.org/ns/dcat#> PREFIX dct:<http://purl.org/dc/terms/>
SELECT ?ds ?u ?f ?pub WHERE { ?ds dcat:distribution ?d . OPTIONAL{?d dcat:downloadURL ?u} OPTIONAL{?d dcat:accessURL ?a} OPTIONAL{?d dct:format ?f} OPTIONAL{?ds dct:publisher ?pub}
FILTER(REGEX(STR(?ds), "%s")) } LIMIT 200"""
ids = "6f2013e6b2800b105bf86a5cbce75bd2|800b336412a333e0d2bcb7eedb992d79|61696b7f67316a6201429f111b6f209d|c10f72217f8773929ba306c9b906b0f5|13b335f700dbcef502158c17a87377df|cd220677ed982cf4f7c0f809bacc9b57|115cdd805d934c59c50451920229301e|2b82e36d8b7092741ebae8130942606c|dfe0f7ae0bd38d4a2a58097234d92cfc|0a67c44167ad0b15f20b385072000516|4728aea4-ab8a-40ab-98db-ad32afe40041"
try:
    r = requests.get("https://data.slovensko.sk/api/sparql", params={"query": q % ids}, headers={"Accept": "application/sparql-results+json"}, timeout=120)
    for b in r.json()["results"]["bindings"]:
        print("DIST", b["ds"]["value"].rsplit("/",1)[-1][:12], b.get("u",{}).get("value","-")[:160], b.get("f",{}).get("value","")[-20:], b.get("pub",{}).get("value","")[-40:])
except Exception as e: print("sparql", e)
q3 = """PREFIX dcat:<http://www.w3.org/ns/dcat#> SELECT ?ds ?a WHERE { ?ds dcat:distribution ?d . ?d dcat:accessURL ?a . FILTER(REGEX(STR(?ds), "%s")) } LIMIT 100"""
try:
    r = requests.get("https://data.slovensko.sk/api/sparql", params={"query": q3 % ids}, headers={"Accept": "application/sparql-results+json"}, timeout=120)
    for b in r.json()["results"]["bindings"]: print("ACC", b["ds"]["value"].rsplit("/",1)[-1][:12], b["a"]["value"][:160])
except Exception as e: print("sparql3", e)
r = requests.get("https://www.minv.sk/?statistika-kriminality-v-slovenskej-republike-xml", headers=HH, timeout=60)
print("MV", sorted(set(re.findall(r'href="(/\?[^"]*(?:[Ss]tatistik|krimin|mapy-trest)[^"]*)"', r.text)))[:40])
print("HOTOVO")
