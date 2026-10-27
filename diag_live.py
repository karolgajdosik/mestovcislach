import requests,re
for u in ["https://mestovcislach.sk/","https://mestovcislach.sk/volby-2026/","https://mestovcislach.pages.dev/"]:
    try:
        t=requests.get(u,timeout=60).text
        print(u, "cloudflareinsights" in t, re.findall(r'data-cf-beacon=.{0,80}',t)[:1])
    except Exception as e: print(u,e)
print("HOTOVO")
