import requests,time
for pokus in range(12):
    r=requests.get("https://mestovcislach.sk/bratislavsky-kraj/pezinok/pezinok/",timeout=30)
    if r.status_code==200: break
    time.sleep(60)
print("čakanie",pokus)
for u in ["/","/bratislavsky-kraj/","/bratislavsky-kraj/pezinok/","/bratislavsky-kraj/pezinok/pezinok/","/bratislavsky-kraj/pezinok/pezinok/kviz/","/presovsky-kraj/bardejov/becherov/","/kosicky-kraj/","/data/obce.json","/data/hladanie.json"]:
    t=time.time(); x=requests.get("https://mestovcislach.sk"+u,timeout=30); print(u,x.status_code,len(x.content),round(time.time()-t,2), "Nájdite svoju obec" in x.text if u=="/" else "")
print("HOTOVO")
