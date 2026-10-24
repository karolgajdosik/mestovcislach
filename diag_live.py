import requests, time
H={"User-Agent":"Mozilla/5.0 (mestovcislach diag)"}
W="https://mestovcislach.sk"
for i in range(40):
    r=requests.get(W+"/dodavatelia/",headers=H,timeout=30)
    if r.status_code==200 and requests.get(W+"/data/odber-brevo.json",headers=H,timeout=30).json().get("zoznamy",{}).get("dodavatel"): break
    time.sleep(30)
for u in ["/bratislava/dosah/","/presov/dosah/","/kosice/kalendar/","/kosice/kalendar.ics","/porovnaj/","/suboj/","/dodavatelia/","/nitra/pribeh/","/data/novinky/kosice.json","/data/dodavatelia.json","/data/dodavatelia/31718914.json","/bratislava/dane/"]:
    r=requests.get(W+u,headers=H,timeout=30); print(u, r.status_code, r.headers.get("content-type"), len(r.content))
print("úvod má Môj prehľad:", "moj-prehlad" in requests.get(W+"/",headers=H,timeout=30).text)
r=requests.get(W+"/api/suboj?den=2026-10-24",headers=H,timeout=30); print("api/suboj GET", r.status_code)
r=requests.get(W+"/api/odhlasit?e=x%40y.sk&t="+"0"*64,headers=H,timeout=30); print("api/odhlasit zlý podpis", r.status_code)
r=requests.post(W+"/api/odber",json={"email":"test@example.invalid","kanal":"dodavatel","ico":"123","suhlas":True},headers=H,timeout=30); print("api/odber zlé IČO", r.status_code, r.json().get("sprava"))
r=requests.post(W+"/api/odber",json={"email":"x","kanal":"dodavatel","ico":"31718914","suhlas":True,"web":"bot"},headers=H,timeout=30); print("api/odber pasca", r.status_code)
print("HOTOVO")
