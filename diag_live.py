import requests,time
s=requests.Session(); s.headers["User-Agent"]="mestovcislach.sk (info@mestovcislach.sk)"
B=[("Barca",48.6905,21.2622),("Bytčica",49.2101,18.7237),("Danielov Dom",49.124,20.235),("Devínska N.Ves",48.208,16.979),("Andač",48.382,17.967)]
for n,la,lo in B:
    q=f'[out:json][timeout:60];is_in({la},{lo})->.a;area.a[boundary=administrative][admin_level~"^(8|9|10)$"];out tags;'
    for ep in ["https://overpass-api.de/api/interpreter","https://overpass.kumi.systems/api/interpreter"]:
        try:
            r=s.post(ep,data={"data":q},timeout=90); print(n,ep,r.status_code)
            for e in r.json()["elements"]:
                t=e["tags"]; print("   ",t.get("admin_level"),t.get("name"),{k:v for k,v in t.items() if "ref" in k or "code" in k})
            break
        except Exception as e: print(n,ep,e)
    time.sleep(2)
print("HOTOVO")
