import subprocess, sys, json, re, io, zipfile, requests
HB = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/130 Safari/537.36"}
def dec(b):
    for e in ("utf-8-sig", "cp1250"):
        try: return b.decode(e)
        except UnicodeDecodeError: pass
for u in ["https://volby.statistics.sk/osk/osk2022/files/OSK2022_SK_csv.zip", "https://volby.statistics.sk/oso/oso2022/files/OSO2022_SK_csv.zip"]:
    z = zipfile.ZipFile(io.BytesIO(requests.get(u, headers=HB, timeout=300).content))
    print("ZIP", u, z.namelist())
    for n in z.namelist():
        if n.endswith(".csv"):
            t = dec(z.read(n)).split("\n"); print("   ", n, len(t), "|", t[0][:300], "|", t[1][:200] if len(t) > 1 else "")
for u in ["https://volby.statistics.sk/ref/ref2023/sk/index.html", "https://volby.statistics.sk/ref/ref2023/sk/subory_na_stiahnutie.html", "https://volby.statistics.sk/ref/ref2023/files/REF2023_SK_csv.zip", "https://volby.statistics.sk/ref/ref2023/files/REF_2023_SK_csv.zip", "https://volby.statistics.sk/ref/ref2023/sk/download.html"]:
    r = requests.get(u, headers=HB, timeout=60); print("REF", u, r.status_code, r.headers.get("content-type"), sorted(set(re.findall(r'href="([^"#]+)"', r.text)))[:40] if "html" in (r.headers.get("content-type") or "") else len(r.content))
qq = """PREFIX dcat:<http://www.w3.org/ns/dcat#> PREFIX dct:<http://purl.org/dc/terms/>
SELECT ?ds ?d ?u ?a ?f WHERE { ?ds dcat:distribution ?d . OPTIONAL{?d dcat:downloadURL ?u} OPTIONAL{?d dcat:accessURL ?a} OPTIONAL{?d dct:format ?f} FILTER(CONTAINS(STR(?ds), "14fae22e") || CONTAINS(STR(?ds), "f2b3af7a") || CONTAINS(STR(?ds), "eab8d2e5")) } LIMIT 40"""
r = requests.get("https://data.slovensko.sk/api/sparql", params={"query": qq}, headers={"Accept": "application/sparql-results+json"}, timeout=120)
bs = r.json()["results"]["bindings"]; print("RA n", len(bs))
for x in bs: print("RAD", x["ds"]["value"][-40:], x.get("u",{}).get("value"), x.get("a",{}).get("value","")[:150], x.get("f",{}).get("value","")[-12:])
for x in bs[:3]:
    u = x.get("u", {}).get("value") or x.get("a", {}).get("value")
    if not u: continue
    try:
        r = requests.get(u, headers=HB, timeout=300, stream=True); head = next(r.iter_content(1500))
        print("RAH", u, r.status_code, r.headers.get("content-type"), r.headers.get("content-length"), head[:500]); r.close()
    except Exception as e: print("RAH", u, e)
print("HOTOVO")
