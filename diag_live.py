import requests, time, re
U={"User-Agent":"diag"}
for i in range(30):
    r=requests.get("https://mestovcislach.sk/kosice/volby?v=%d"%time.time(),headers=U,timeout=30)
    if r.status_code==200 and "vb-stav" in r.text: break
    time.sleep(20)
print("kosice/volby", r.status_code, re.search(r"<title>([^<]*)",r.text).group(1))
s=requests.get("https://mestovcislach.sk/sitemap.xml",headers=U,timeout=30).text
print("sitemap volby:", len(re.findall(r"/[a-z-]+/volby<",s)))
print("HOTOVO")
