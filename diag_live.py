import requests,time
time.sleep(180)
r=requests.get("https://mestovcislach.sk/api/sutaz",timeout=30); print("API GET",r.status_code,r.text[:200])
r=requests.post("https://mestovcislach.sk/api/sutaz",json={"tyzden":"1999-W01","mesto":"trnava","body":3},timeout=30); print("POST zlý týždeň",r.status_code)
for u in ["https://mestovcislach.sk/sutaz/","https://mestovcislach.sk/kosice/poslanci/marek-fedorocko/","https://mestovcislach.sk/trnava/poslanci/eva-nemcovska/"]:
    t=requests.get(u,timeout=30); print(u,t.status_code)
print("HOTOVO")
