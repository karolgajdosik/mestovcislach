import requests,re
for u in ["https://mestovcislach.sk/volby-2026/","https://mestovcislach.sk/"]:
    r=requests.get(u,timeout=60); t=r.text
    print(u,r.status_code,"Nové vedenie miest" in t, "priemerný vek" in t, re.findall(r"(\d+,\d) roka",t)[:1], re.findall(r"(\d+) z (\d+)</b>",t)[:1])
print("HOTOVO")
