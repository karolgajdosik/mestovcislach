import requests,re
h=requests.get("https://datacube.statistics.sk/",timeout=30).text
print(re.findall(r'<title>(.*?)</title>',h,re.S)[:1]); print(sorted(set(re.findall(r'https?://[a-z0-9.\-]*statistics\.sk[^"\' )<]*',h)))[:30])
for u in ["https://datacube.statistics.sk/api/v2/collection?lang=sk","https://datacube.statistics.sk/api/v2/dataset/sp3801qr/SK0,SK010/all/all/all/all?lang=sk","https://data.statistics.sk/api/v2/collection?lang=sk"]:
    try: x=requests.get(u,timeout=40); print(u,x.status_code,x.headers.get("content-type"),x.text[:200])
    except Exception as e: print(u,type(e).__name__)
print("HOTOVO")
