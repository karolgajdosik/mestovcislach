import requests, json
H = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/130 Safari/537.36"}
q = """SELECT (COUNT(?p) AS ?n) WHERE { ?p <https://linkedopendata.eu/prop/direct/P35> <https://linkedopendata.eu/entity/Q9934> ; <https://linkedopendata.eu/prop/direct/P32> <https://linkedopendata.eu/entity/Q218> . }"""
for u in ["https://query.linkedopendata.eu/bigdata/namespace/wdq/sparql", "https://query.linkedopendata.eu/sparql"]:
    try:
        r = requests.get(u, params={"query": q}, headers={**H, "Accept": "application/sparql-results+json"}, timeout=120)
        print(u, r.status_code, r.text[:400])
    except Exception as e:
        print(u, e)
for u in ["https://cohesiondata.ec.europa.eu/api/views/metadata/v1?limit=5", "https://data.europa.eu/api/hub/search/search?q=kohesio&limit=5", "https://www.itms2014.sk/", "https://opendata.itms2014.sk/swagger/", "https://www.eurofondy.gov.sk/"]:
    try:
        r = requests.get(u, headers=H, timeout=60); print(u, r.status_code, r.text[:300].replace("\n", " "))
    except Exception as e:
        print(u, str(e)[:150])
print("HOTOVO")
