import requests,re
for u in ["https://mestovcislach.sk/bratislavsky-kraj/senec/senec/","https://mestovcislach.sk/nitriansky-kraj/nitra/aleksince/"]:
    h=requests.get(u,timeout=60).text; i=h.find('id="eia"')
    print(u, i, re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',h[i:i+2500]))[:700] if i>0 else "")
print("HOTOVO")
