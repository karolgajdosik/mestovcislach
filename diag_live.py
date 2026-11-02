import requests
for d in ["2026-05-07","2026-05-08","2026-05-09","2026-05-11","2026-10-30"]:
    r=requests.get(f"https://www.crz.gov.sk/export/{d}.zip",timeout=120,headers={"User-Agent":"mestovcislach.sk"}); print(d,r.status_code,len(r.content),r.text[:120] if r.status_code!=200 else "")
print("HOTOVO")
