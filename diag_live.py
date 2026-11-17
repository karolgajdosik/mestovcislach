import requests
U="https://query.wikidata.org/sparql"; H={"User-Agent":"mestovcislach.sk (info@mestovcislach.sk)","Accept":"application/sparql-results+json"}
q="""SELECT (COUNT(DISTINCT ?o) AS ?n) WHERE { ?o wdt:P17 wd:Q214; wdt:P782 ?lau; wdt:P10 ?v. }"""
print("obce s videom (P10):", requests.get(U,params={"query":q},headers=H,timeout=120).json()["results"]["bindings"][0]["n"]["value"])
q2="""SELECT ?oLabel ?v WHERE { ?o wdt:P17 wd:Q214; wdt:P782 ?lau; wdt:P10 ?v. SERVICE wikibase:label { bd:serviceParam wikibase:language "sk". } } LIMIT 15"""
for b in requests.get(U,params={"query":q2},headers=H,timeout=120).json()["results"]["bindings"]: print(" ", b["oLabel"]["value"], b["v"]["value"].split("/")[-1][:70])
# Commons: videá v kategóriách niekoľkých miest
A="https://commons.wikimedia.org/w/api.php"
for kat in ["Prievidza","Bojnice","Banská Štiavnica","Petržalka","Trenčín"]:
    r=requests.get(A,params={"action":"query","list":"search","srsearch":f'filetype:video incategory:"{kat}"',"srnamespace":6,"srlimit":50,"format":"json"},headers=H,timeout=60).json()
    n=r.get("query",{}).get("searchinfo",{}).get("totalhits")
    r2=requests.get(A,params={"action":"query","list":"search","srsearch":f'filetype:video deepcat:"{kat}"',"srnamespace":6,"srlimit":5,"format":"json"},headers=H,timeout=60).json()
    print(kat,"videí v kategórii:",n,"vrátane podkategórií:",r2.get("query",{}).get("searchinfo",{}).get("totalhits"), [x["title"][5:60] for x in r2.get("query",{}).get("search",[])[:3]])
print("HOTOVO")
