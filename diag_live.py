import requests, re, html
H={"User-Agent":"Mozilla/5.0 (mestovcislach.sk)"}
U={"bratislava":["https://zastupitelstvo.bratislava.sk/zasadnutia/"],
 "nitra":["https://nitra.sk/kalendar-zasadnuti-organov-mesta/"],
 "trencin":["https://trencin.sk/samosprava/mestske-zastupitelstvo/","https://trencin.sk/samosprava/mestske-zastupitelstvo/zasadnutia/"],
 "zilina":["https://zilina.sk/mesto-zilina/sprava-mesta/volene-organy/poslanci/mestske-zastupitelstvo/"],
 "banska-bystrica":["https://www.banskabystrica.sk/samosprava/zasadnutia/"],
 "presov":["https://www.presov.sk/mestske-zastupitelstvo.html","https://www.presov.sk/zasadnutia-mestskeho-zastupitelstva.html","https://www.presov.sk"],
 "kosice":["https://www.kosice.sk/mesto/samosprava/mestske-zastupitelstvo","https://www.kosice.sk/mesto/samosprava/mestske-zastupitelstvo/rokovania"]}
DAT=re.compile(r"(\d{1,2})\.\s?(\d{1,2})\.\s?(2026|2027)")
for m,us in U.items():
    for u in us:
        try:
            r=requests.get(u,headers=H,timeout=40); t=html.unescape(re.sub(r"\s+"," ",re.sub(r"<[^>]+>"," ",r.text)))
            print("==",m,u,r.status_code,len(t))
            for mm in list(DAT.finditer(t))[:14]: print("   ", t[max(0,mm.start()-90):mm.end()+25])
            if m=="presov": print("  odkazy:", sorted(set(re.findall(r'href="([^"]*(?:zastup|zasadn|rokovan)[^"]*)"', r.text, re.I)))[:10])
        except Exception as e: print(m,u,"ERR",e)
print("HOTOVO")
