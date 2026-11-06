import re, requests
s = requests.Session(); s.headers["User-Agent"] = "Mozilla/5.0 mestovcislach.sk"
for f in ["controllers.js", "directives.js", "views-parts.js", "views-layouts.js", "rozpocet.js"]:
    c = s.get("https://rozpocet.sk/web/app/" + f, timeout=60).text
    for m in list(re.finditer(r"[Kk]lasifikaci", c))[:4]:
        print("==", f, c[max(0, m.start()-250):m.start()+250].replace("\n", " "))
    print("HREF", f, sorted(set(re.findall(r'#/[a-zA-Z0-9_/\-{}.:+\'"]{3,80}', c)))[:30])
print("HOTOVO")
