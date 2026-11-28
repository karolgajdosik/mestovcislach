import json, urllib.request, urllib.parse, re
UA={'User-Agent':'mestovcislach.sk (info@mestovcislach.sk)'}
def get(u): return json.load(urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=60))
# slovenská Wikipédia – Zoznam miest na Slovensku (wikitext)
for title in ['Zoznam_miest_na_Slovensku']:
    d=get(f'https://sk.wikipedia.org/w/api.php?action=parse&page={title}&prop=wikitext&format=json&formatversion=2')
    wt=d['parse']['wikitext']
    print(title,len(wt)); print(wt[:1500])
    open('diag/mesta_wikitext.txt','w').write(wt)
# Wikidata: obce SR s vlastnosťou "inštancia: mesto na Slovensku"
q='''SELECT ?kod ?itemLabel WHERE { ?item wdt:P31 wd:Q15649510 . OPTIONAL { ?item wdt:P782 ?kod } SERVICE wikibase:label { bd:serviceParam wikibase:language "sk". } }'''
try:
    r=get('https://query.wikidata.org/sparql?format=json&query='+urllib.parse.quote(q))
    rows=[(b.get('kod',{}).get('value'),b['itemLabel']['value']) for b in r['results']['bindings']]
    print('wikidata',len(rows),rows[:5])
    json.dump(rows,open('diag/mesta_wd.json','w'),ensure_ascii=False)
except Exception as e: print('wd chyba',e)
print('HOTOVO')
