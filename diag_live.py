import requests
s=requests.Session(); s.headers["User-Agent"]="mestovcislach-diag"
Q=["""PREFIX dcat:<http://www.w3.org/ns/dcat#> PREFIX dct:<http://purl.org/dc/terms/>
SELECT ?ds ?d ?u ?f WHERE { ?ds dcat:distribution ?d . OPTIONAL{?d dcat:downloadURL ?u} OPTIONAL{?d dcat:accessURL ?a} OPTIONAL{?d dct:format ?f} FILTER(CONTAINS(STR(?ds),"ebeeedf1")) } LIMIT 50""",
"""PREFIX dcat:<http://www.w3.org/ns/dcat#> PREFIX dct:<http://purl.org/dc/terms/>
SELECT ?ds ?t ?u WHERE { ?ds dct:title ?t . ?ds dcat:distribution ?d . ?d dcat:downloadURL ?u . FILTER(CONTAINS(LCASE(STR(?t)),"gtfs") || CONTAINS(LCASE(STR(?u)),"gtfs")) } LIMIT 50""",
"""SELECT ?p ?o WHERE { ?s ?p ?o . FILTER(CONTAINS(STR(?s),"ebeeedf1")) } LIMIT 60"""]
for q in Q:
    for m in ("get","post"):
        try:
            r=(s.get if m=="get" else s.post)("https://data.slovensko.sk/api/sparql",**({"params":{"query":q}} if m=="get" else {"data":{"query":q}}),headers={"Accept":"application/sparql-results+json"},timeout=90)
            print(m,r.status_code); print(r.text[:3000]); break
        except Exception as e: print(m,e)
print("HOTOVO")
