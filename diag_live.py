import requests
U="https://query.wikidata.org/sparql"; H={"User-Agent":"mestovcislach.sk (info@mestovcislach.sk)","Accept":"application/sparql-results+json"}
def q(s): return requests.get(U,params={"query":s},headers=H,timeout=180).json()["results"]["bindings"]
r=q("""SELECT (COUNT(DISTINCT ?p) AS ?n) (COUNT(DISTINCT ?obec) AS ?obce) WHERE { ?p wdt:P17 wd:Q214; wdt:P1435 ?d; wdt:P625 ?c. OPTIONAL { ?p wdt:P131 ?obec. } }""")
print("pamiatky s ochranou a súradnicami:",r[0]["n"]["value"],"administratívnych celkov:",r[0]["obce"]["value"])
r=q("""SELECT (COUNT(DISTINCT ?p) AS ?n) WHERE { ?p wdt:P17 wd:Q214; wdt:P1435 ?d; wdt:P625 ?c. ?a schema:about ?p; schema:isPartOf <https://sk.wikipedia.org/>. }""")
print("z toho so slovenským článkom na Wikipédii:",r[0]["n"]["value"])
r=q("""SELECT (COUNT(DISTINCT ?p) AS ?n) WHERE { ?p wdt:P17 wd:Q214; wdt:P1435 ?d; wdt:P625 ?c; wdt:P18 ?img. }""")
print("s fotkou:",r[0]["n"]["value"])
for obec in ["Q25409","Q1780","Q194225"]:  # Prievidza, Bratislava?, Bojnice
    r=q(f"""SELECT ?pLabel (COUNT(?l) AS ?sl) WHERE {{ ?p wdt:P17 wd:Q214; wdt:P1435 ?d; wdt:P625 ?c; wdt:P131* wd:{obec}. OPTIONAL {{ ?l schema:about ?p }} SERVICE wikibase:label {{ bd:serviceParam wikibase:language "sk". }} }} GROUP BY ?pLabel ORDER BY DESC(?sl) LIMIT 6""")
    print(obec, [x["pLabel"]["value"] for x in r])
print("HOTOVO")
