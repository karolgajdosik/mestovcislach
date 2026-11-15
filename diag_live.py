import requests
for u in ["https://thumb.wikimedia.org/wikipedia/commons/thumb/7/7e/Coat_of_Arms_of_Prievidza.svg/500px-Coat_of_Arms_of_Prievidza.svg.png",
          "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7e/Coat_of_Arms_of_Prievidza.svg/500px-Coat_of_Arms_of_Prievidza.svg.png"]:
    try:
        r=requests.get(u,timeout=30,headers={"User-Agent":"Mozilla/5.0 (compatible; mestovcislach.sk; info@mestovcislach.sk)","Referer":"https://mestovcislach.sk/"})
        print(r.status_code,r.headers.get("content-type"),len(r.content),u[:40])
    except Exception as e: print("ERR",e)
print("HOTOVO")
