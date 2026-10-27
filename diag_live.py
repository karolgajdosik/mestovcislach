import requests,time,json,re
time.sleep(200)
for u,k in [("https://mestovcislach.sk/trnava/","Rýchle odpovede"),("https://mestovcislach.sk/trnava/","Zima"),("https://mestovcislach.sk/rozpocty-2027/","Rozpočty miest"),("https://mestovcislach.sk/kosice/zastupitelstvo/","Prvé kroky"),("https://mestovcislach.sk/trnava/kalendar/","ustanovujúceho")]:
    t=requests.get(u+"?v=4",timeout=60).text; print(u,k in t)
r=requests.get("https://api.open-meteo.com/v1/forecast?latitude=48.37&longitude=17.58&daily=temperature_2m_max,temperature_2m_min,snowfall_sum,weather_code&forecast_days=7&timezone=Europe%2FBratislava",timeout=30)
print("open-meteo",r.status_code,r.json()["daily"]["temperature_2m_min"])
print("HOTOVO")
