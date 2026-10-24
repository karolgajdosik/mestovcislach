import requests, re
UA={"User-Agent":"mestovcislach.sk (github.com/karolgajdosik/mestovcislach)"}
def g(u):
    try:
        r=requests.get(u,headers=UA,timeout=40,allow_redirects=True); return r.status_code, r.url, r.headers.get('content-type',''), r.text if 'text' in r.headers.get('content-type','') or 'json' in r.headers.get('content-type','') else '', len(r.content)
    except Exception as e: return 0,u,'',str(e),0
for u in ["https://volbysr.sk","https://volbysr.sk/oso/sk/","https://volbysr.sk/oso/","https://www.volbysr.sk/","https://volbysr.sk/oso/files/OSO2026_SK_csv.zip","https://volbysr.sk/oso/files/OSO2026_SK_xlsx.zip","https://volbysr.sk/osk/files/OSK2026_SK_csv.zip","https://volbysr.sk/sk/","https://volbysr.sk/oso/sk/data.html","https://volbysr.sk/oso/sk/download.html","https://volbysr.sk/sk/data.html"]:
    s,ru,ct,t,n=g(u); print("==",u,s,ru,ct,n)
    links=sorted(set(re.findall(r'(?:href|src)="([^"#]+)"',t)))
    print("  linky:", [l for l in links if not l.endswith(('.css','.png','.svg','.ico','.woff2','.jpg'))][:60])
    if t and len(t)<3000: print("  text:", re.sub(r'\s+',' ',re.sub('<[^>]+>',' ',t))[:400])
print("HOTOVO")
