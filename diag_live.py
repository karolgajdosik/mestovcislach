import requests, re
H={"User-Agent":"Mozilla/5.0 (mestovcislach diag)"}
B="https://volbysr.sk/oso/"
js=re.sub(r"\s+"," ",requests.get(B+"js/functions.js",headers=H,timeout=60).text)
for f in ["function createTab06","function createTab07","function renderChart01","function getRadioButtonValue"]:
    i=js.find(f); print(f, js[i:i+1300]); print()
for p in ["json/graph01/500011.json","json/tab06e1/500011.json","json/tab06e2/500011.json","json/tab07/500011.json","json/graph02/500011.json","json/chart01/500011.json","json/graph01/528595.json","json/tab05/528595.json","json/tab07/582000.json"]:
    r=requests.get(B+p,headers=H,timeout=60); print(p, r.status_code, r.text[:600] if r.ok else "")
h=requests.get(B+"sk/vysledky_obce.html",headers=H,timeout=60); h.encoding="utf-8"
print("RADIO:", re.findall(r'name="tab06-radios"[^>]*value="([^"]+)"', h.text), re.findall(r'id="(tab0[67][^"]*)"', h.text))
print("HOTOVO")
