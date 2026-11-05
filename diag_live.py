import subprocess, sys, json, re, requests
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", "scripts/requirements.txt"])
sys.path.insert(0, "scripts")
from statdata_obce import polozky, B, H
from spolocne import s
for k in ["pl5001rr", "om7809rr", "om7804rr", "om7805rr", "om7806rr", "om7803rr", "np3110rr", "st3802rr", "so3801rr"]:
    try:
        info = s.get(f"{B}/public/{k}/info", headers=H, timeout=60).json()
        print("==", k, info.get("nameSk"), info.get("timePeriodTo"))
        for d in info["dimensions"]:
            if d["acronym"] in ("e_nuts15",): continue
            p = polozky(k, d["id"])
            nm = [ (x.get("nameSk") or x.get("name") or "")[:45] + "=" + str(x.get("code") or x.get("id") or x.get("itemCode") or "") for x in p]
            print("  ", d["acronym"], d["type"], len(p), nm[:40] if d["type"] != "GEO" else nm[:3], json.dumps(p[0], ensure_ascii=False)[:200] if p and d["acronym"] == "e_sex" else "")
    except Exception as e:
        print("==", k, "CHYBA", str(e)[:300])
q = """PREFIX dcat:<http://www.w3.org/ns/dcat#> PREFIX dct:<http://purl.org/dc/terms/>
SELECT ?ds ?u ?a ?f WHERE { ?ds dcat:distribution ?d . OPTIONAL{?d dcat:downloadURL ?u} OPTIONAL{?d dcat:accessURL ?a} OPTIONAL{?d dct:format ?f}
FILTER(REGEX(STR(?ds), "%s")) } LIMIT 200"""
ids = "6f2013e6b2800b105bf86a5cbce75bd2|800b336412a333e0d2bcb7eedb992d79|61696b7f67316a6201429f111b6f209d|c10f72217f8773929ba306c9b906b0f5|13b335f700dbcef502158c17a87377df|cd220677ed982cf4f7c0f809bacc9b57|115cdd805d934c59c50451920229301e|2b82e36d8b7092741ebae8130942606c|dfe0f7ae0bd38d4a2a58097234d92cfc|0a67c44167ad0b15f20b385072000516|4728aea4-ab8a-40ab-98db-ad32afe40041"
try:
    r = requests.get("https://data.slovensko.sk/api/sparql", params={"query": q % ids}, headers={"Accept": "application/sparql-results+json"}, timeout=120)
    for b in r.json()["results"]["bindings"]:
        print("DIST", b["ds"]["value"].rsplit("/",1)[-1][:12], "|", b.get("u",{}).get("value","-")[:170], "|", b.get("a",{}).get("value","-")[:120], "|", b.get("f",{}).get("value","")[-25:])
except Exception as e: print("sparql", e)
HH = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/130 Safari/537.36"}
try:
    r = requests.get("https://www.minv.sk/?statistika-kriminality-v-slovenskej-republike-xml", headers=HH, timeout=60)
    print("MV", sorted(set(re.findall(r'href="(/\?[^"]*(?:[Ss]tatistik|krimin|mapy-trest)[^"]*)"', r.text)))[:50])
except Exception as e: print("MV", e)
print("HOTOVO")
