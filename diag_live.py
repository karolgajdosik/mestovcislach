import requests, re, json
U="https://query.wikidata.org/sparql"; H={"User-Agent":"mestovcislach.sk (info@mestovcislach.sk)","Accept":"application/sparql-results+json"}
q="""SELECT ?cls ?clsLabel (COUNT(?o) AS ?n) WHERE { ?o wdt:P17 wd:Q214; wdt:P782 ?lau; wdt:P31 ?cls. SERVICE wikibase:label { bd:serviceParam wikibase:language "sk,en". } } GROUP BY ?cls ?clsLabel ORDER BY DESC(?n) LIMIT 15"""
r=requests.get(U,params={"query":q},headers=H,timeout=120).json()
for b in r["results"]["bindings"]: print(b["cls"]["value"].split("/")[-1], b["clsLabel"]["value"], b["n"]["value"])
best=[b for b in r["results"]["bindings"] if 120<=int(b["n"]["value"])<=160]
for b in best:
    c=b["cls"]["value"].split("/")[-1]
    q2=f"SELECT ?lau WHERE {{ ?o wdt:P31 wd:{c}; wdt:P782 ?lau. }}"
    r2=requests.get(U,params={"query":q2},headers=H,timeout=120).json()
    kody=sorted({m.group(0) for x in r2["results"]["bindings"] for m in [re.search(r"\d{6}",x["lau"]["value"])] if m})
    print("TRIEDA",c,len(kody)); print("KODY",",".join(kody))
print("HOTOVO")
