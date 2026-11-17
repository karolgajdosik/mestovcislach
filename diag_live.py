import requests,json
d=json.load(open("data/obce/obrazky.json")) if False else None
for u in ["https://thumb.wikimedia.org/wikipedia/commons/thumb/7/7e/Coat_of_Arms_of_Prievidza.svg/500px-Coat_of_Arms_of_Prievidza.svg.png",
          "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7e/Coat_of_Arms_of_Prievidza.svg/1280px-Coat_of_Arms_of_Prievidza.svg.png"]:
    r=requests.get(u,headers={"Origin":"https://mestovcislach.sk","User-Agent":"mestovcislach.sk (info@mestovcislach.sk)"},timeout=30,allow_redirects=False)
    print(r.status_code,"ACAO=",r.headers.get("access-control-allow-origin"),r.headers.get("location","")[:80],u[:40])
print("HOTOVO")
