import json, urllib.request
UA={'User-Agent':'mestovcislach.sk (info@mestovcislach.sk)','Accept':'application/json'}
def get(u):
    return json.load(urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=30))
d=get('https://api.statistics.sk/rpo/v1/search?identifier=52966593')
for e in d.get('results',[]):
    nm=[x.get('value') for x in e.get('fullNames',[]) if not x.get('validTo')]
    ad=[x for x in e.get('addresses',[]) if not x.get('validTo')]
    a=ad[0] if ad else {}
    adresa=f"{a.get('street','')} {a.get('buildingNumber') or a.get('regNumber') or ''}, {a.get('postalCodes',[''])[0] if a.get('postalCodes') else ''} {a.get('municipality',{}).get('value','')}".strip()
    print('NAZOV',nm,'| ICO',[x.get('value') for x in e.get('identifiers',[])],'| SIDLO',adresa,'| VZNIK',e.get('establishment'),'| ZANIK',e.get('termination'),'| FORMA',[x.get('value') for x in e.get('legalForms',[]) if not x.get('validTo')])
print('HOTOVO')
