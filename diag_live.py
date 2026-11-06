import re, requests, json
s = requests.Session(); s.headers["User-Agent"] = "Mozilla/5.0 mestovcislach.sk"
for f in ["controllers.js", "directives.js", "rozpocet.js", "views-parts.js", "views-layouts.js", "app.js"]:
    c = s.get("https://rozpocet.sk/web/app/" + f, timeout=60).text
    for k in ["basAPIKlasifikacieSAM(", "getPodurovnovePolozky(", "getRozpocetSamOrg(", "getRozpoctySamOrg(", "getRozpocetSumarSamOrg(", "hladajObec"]:
        for m in list(re.finditer(re.escape(k), c))[:2]:
            print("==", f, k, c[max(0, m.start()-200):m.start()+300].replace("\n", " "))
print("HOTOVO")
