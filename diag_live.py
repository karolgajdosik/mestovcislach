import requests, re, html
from urllib.parse import urljoin
H={"User-Agent":"Mozilla/5.0 (mestovcislach.sk)"}
MESTA={"bratislava":"https://zastupitelstvo.bratislava.sk/zasadnutia/","trnava":"https://www.trnava.sk","nitra":"https://www.nitra.sk","trencin":"https://www.trencin.sk","zilina":"https://www.zilina.sk","banska-bystrica":"https://www.banskabystrica.sk","presov":"https://www.presov.sk","kosice":"https://www.kosice.sk"}
DAT=re.compile(r"(\d{1,2})\.\s?(\d{1,2})\.\s?(2026|2027)")
for m,u in MESTA.items():
    try:
        r=requests.get(u,headers=H,timeout=40); t=r.text
        print("==",m,r.status_code,len(t))
        if m=="bratislava":
            print(sorted(set(re.findall(r"zasadnutie-(\d{8})",t)))[-8:]); continue
        links=sorted({urljoin(r.url,h) for h,txt in re.findall(r'href="([^"]+)"[^>]*>(.*?)</a>',t,re.S) if re.search(r"zastupite|zasadnut|rokovan",h+txt,re.I)})[:12]
        print(" odkazy:", links)
        for l in links[:6]:
            try:
                x=requests.get(l,headers=H,timeout=40).text
                ctx=[html.unescape(re.sub(r"<[^>]+>"," ",x[max(0,mm.start()-120):mm.end()+40])).split() for mm in DAT.finditer(x)]
                ctx=[" ".join(c)[-160:] for c in ctx if any(re.search(r"zasadnut|rokovan|zastupite",w,re.I) for w in c)]
                if ctx: print("  ",l, ctx[:6])
            except Exception as e: print("  ERR",l,e)
    except Exception as e: print(m,"ERR",e)
print("HOTOVO")
