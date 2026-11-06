import requests, time, json
s = requests.Session(); s.headers["User-Agent"] = "Mozilla/5.0 mestovcislach.sk"
A = "https://rozpocet.sk/rest/api/rozpocet/"
for p in ["polozkyRozpocetuFilterSamOrg/SK/804045/2025/SAM/false/FK?FK=01,02,03,04,05,06,07,08,09,10",
          "polozkyRozpocetuFilterSamOrg/SK/804045/2025/SAM/false/EKV?EKV=610,620,630,640,650,690,710,720,810",
          "rozpocetSumarSamOrg/804045/2025/12?EKV=VYD&FK=09&ORG=02&ORG=11&ORG=23&ORG=22&DRH=81&DRH=101",
          "rozpocetSumarSamOrg/804045/2025/12?EKV=VYD&ORG=02&ORG=11&ORG=23&ORG=22&DRH=81&DRH=101"]:
    try:
        r = s.get(A + p, timeout=90); print("API", p, r.status_code, r.text[:1800].replace("\n"," "))
    except Exception as e: print("ERR", p, e)
    time.sleep(1)
print("HOTOVO")
