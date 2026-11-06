import re, requests, json
s = requests.Session(); s.headers["User-Agent"] = "Mozilla/5.0 mestovcislach.sk"
c = s.get("https://rozpocet.sk/web/app/controllers.js", timeout=60).text
for k in ["getRozpocetSamOrg(", "getRozpoctySamOrg(", "getRozpocetSumarSamOrg(", "getPodurovnovePolozky("]:
    for m in re.finditer(re.escape(k), c):
        print("==", k, c[max(0, m.start()-250):m.start()+350].replace("\n", " ")); break
t = s.get("https://rozpocet.sk/web/app/services.js", timeout=60).text
i = t.find("getPodurovnovePolozky:"); print("SVC", t[i:i+1200])
i = t.find("getRozpocetSumarSamOrg:"); print("SVC2", t[i:i+700])
A = "https://rozpocet.sk/rest/api/"
for p in ["rozpocet/rozpocetSamOrg/804045/2024/SK", "rozpocet/rozpoctySamOrg/804045/2024/SKU/FK/SK"]:
    r = s.get(A + p, timeout=90); print("API", p, r.status_code, r.text[:600])
print("HOTOVO")
