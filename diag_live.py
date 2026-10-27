import requests,re,html
UA={"User-Agent":"Mozilla/5.0 (mestovcislach.sk)"}
WEB={"bratislava":"https://bratislava.sk","trnava":"https://www.trnava.sk","trencin":"https://trencin.sk","nitra":"https://nitra.sk","zilina":"https://zilina.sk","banska-bystrica":"https://www.banskabystrica.sk","presov":"https://www.presov.sk","kosice":"https://www.kosice.sk"}
for s,u in WEB.items():
    try:
        r=requests.get(u+"/wp-json/wp/v2/media?search=rozpo&per_page=5",headers=UA,timeout=40)
        wp=r.status_code==200 and r.text.startswith("[")
        tit=[html.unescape(x["title"]["rendered"])[:60]+" "+x["date"][:10] for x in r.json()] if wp else []
        print(s,"WP",wp,r.status_code,tit[:5])
        h=requests.get(u,headers=UA,timeout=40).text
        links=sorted({(m.group(1),re.sub(r"<[^>]+>","",m.group(2)).strip()[:40]) for m in re.finditer(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>',h,re.S) if re.search(r"rozpo|financ|ekonom|uradna|úradná",m.group(1)+m.group(2),re.I)})
        print("   ",links[:8])
    except Exception as e: print(s,"CHYBA",type(e).__name__,str(e)[:100])
print("HOTOVO")
