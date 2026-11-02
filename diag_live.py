import requests,re
for u in ["https://mestovcislach.sk/presovsky-kraj/bardejov/becherov/","https://mestovcislach.sk/bratislavsky-kraj/pezinok/pezinok/"]:
    h=requests.get(u,timeout=60).text; i=h.find('id="zmluvy"')
    print(u, re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',h[i:i+5000]))[:1100] if i>0 else "NIE")
print("HOTOVO")
