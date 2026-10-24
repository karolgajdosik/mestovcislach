import requests, time
UA={"User-Agent":"mestovcislach.sk (github.com/karolgajdosik/mestovcislach)"}
S=["https://overpass-api.de/api/interpreter","https://overpass.private.coffee/api/interpreter"]
def op(q):
    for s in S:
        try:
            r=requests.post(s,data={"data":q},headers=UA,timeout=200)
            if r.ok: return r.json()
        except Exception as e: print("err",s,e)
for slug,rel in [('trnava',2204009),('nitra',2210192),('trencin',1799254),('zilina',1859537),('banska-bystrica',2265296),('presov',2320257)]:
    a=3600000000+rel
    for q in [f'[out:json][timeout:120];area({a})->.a;rel(area.a)[boundary=administrative][admin_level~"^(9|10|11)$"];out tags;',
              f'[out:json][timeout:120];area({a})->.a;rel(area.a)[boundary~"^(cadastral|census|place)$"];out tags;']:
        j=op(q)
        if not j: print(slug,"nic"); continue
        el=j.get("elements",[])
        print(slug, len(el), sorted({(e["tags"].get("admin_level") or e["tags"].get("boundary")) for e in el}), [e["tags"].get("name") for e in el][:30])
        time.sleep(2)
print("HOTOVO")
