import re, requests, json, time
s = requests.Session(); s.headers["User-Agent"] = "Mozilla/5.0 mestovcislach.sk"
A = "https://rozpocet.sk/rest/api/"
c = s.get("https://rozpocet.sk/web/app/directives.js", timeout=60).text
for m in list(re.finditer(r"basAPIKlasifikacieSAM\(", c))[:3]: print("KL", c[max(0,m.start()-300):m.start()+200].replace("\n"," "))
for p in ["rozpocet/rozpocetSamOrg/804045/2025/4", "rozpocet/rozpocetSamOrg/804045/2024/4",
          "rozpocet/klasifikacie/sk/FK/804045/2024?uroven=CELKOVY", "rozpocet/klasifikacie/sk/SAM/804045/2024?uroven=CELKOVY"]:
    try:
        r = s.get(A + p, timeout=90); print("API", p, r.status_code, r.text[:1500].replace("\n"," "))
    except Exception as e: print("ERR", p, e)
    time.sleep(1)
print("HOTOVO")
