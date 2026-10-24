import requests, re
H={"User-Agent":"Mozilla/5.0 (mestovcislach diag)"}
B="https://volbysr.sk/oso/"
js=re.sub(r"\s+"," ",requests.get(B+"js/functions.js",headers=H,timeout=60).text)
for f in ["function fillBoxes","function createTab05"]:
    i=js.find(f); print(f, js[i:i+1600]); print()
for c in ["500011","582000","599981","524140"]:
    for p in [f"json/graph01/{c}.json", f"json/tab05/{c}.json", f"json/tab05.json"]:
        r=requests.get(B+p,headers=H,timeout=60); print(p, r.status_code, r.text[:700] if r.ok else "")
print("HOTOVO")
