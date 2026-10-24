import requests, re
H={"User-Agent":"Mozilla/5.0"}
h=requests.get("https://zastupitelstvo.bratislava.sk/zasadnutia/",headers=H,timeout=60).text
d=sorted(set(re.findall(r'zasadnutie-(\d{8})', h)))
print("BA zasadnutia na 1. strane:", [x[4:]+'-'+x[2:4]+'-'+x[:2] for x in d][-12:])
# ďalšie typy (komisie?) – len počet odkazov s budúcim dátumom
print("text 'pripravované':", 'priprav' in h.lower(), len(h))
for u in ["https://www.kosice.sk/clanok/harmonogram-zasadnuti-mestskeho-zastupitelstva","https://www.kosice.sk/mesto/samosprava/mestske-zastupitelstvo","https://www.trnava.sk/sk/clanok/harmonogram-zasadnuti","https://www.zilina.sk/mestske-zastupitelstvo/","https://www.presov.sk/harmonogram-zasadnuti-mz.html"]:
    try:
        r=requests.get(u,headers=H,timeout=40); t=r.text
        print(u, r.status_code, len(t), re.findall(r'\d{1,2}\.\s?\d{1,2}\.\s?2026', t)[:12])
    except Exception as e: print(u,"ERR",type(e).__name__)
print("HOTOVO")
