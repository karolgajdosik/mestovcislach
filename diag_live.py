import requests,re
UA={"User-Agent":"Mozilla/5.0"}
h=requests.get("https://www.presov.sk",headers=UA,timeout=40).text
print(len(h)); print(h[:1500])
print("scripts:",re.findall(r'<script[^>]+src="([^"]+)"',h)[:10])
for u in ["https://www.presov.sk/api","https://www.presov.sk/sitemap.xml","https://www.presov.sk/robots.txt","https://www.presov.sk/wp-json/","https://www.presov.sk/uradna-tabula","https://www.presov.sk/portal/","https://egov.presov.sk","https://www.presov.sk/rozpocet-mesta-presov.html"]:
    try:
        r=requests.get(u,headers=UA,timeout=30); print(u,r.status_code,r.headers.get("content-type"),len(r.text),r.text[:200].replace("\n"," "))
    except Exception as e: print(u,type(e).__name__)
print("HOTOVO")
