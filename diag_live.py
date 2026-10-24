import requests, re
H={"User-Agent":"Mozilla/5.0 (mestovcislach diag)"}
h=requests.get("https://volbysr.sk/oso/sk/vysledky_obce.html",headers=H,timeout=60); h.encoding="utf-8"
for s in re.findall(r'<script[^>]*>(.*?)</script>', h.text, re.S):
    if s.strip(): print("INLINE:", re.sub(r"\s+"," ",s)[:1500])
print("SELECTY:", re.findall(r'<select[^>]*id="([^"]+)"', h.text))
js=requests.get("https://volbysr.sk/oso/js/functions.js",headers=H,timeout=60).text
for m in re.finditer(r"function (\w+)\(", js): pass
for name in ["loadSelect","createSelect","fillObec","obce","getObce"]:
    i=js.find(name)
    if i>=0: print(name, re.sub(r"\s+"," ",js[i:i+600]))
for m in re.finditer(r"\.\./select/[^'\"]*", js): print("SEL", m.group(0))
for m in re.finditer(r"getJSON\('([^']+)'", js): print("GJ", m.group(1))
print("HOTOVO")
