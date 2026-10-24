import requests, re, json
H={"User-Agent":"Mozilla/5.0 (mestovcislach diag)"}
J="https://volbysr.sk/oso/json/"
for n in ["tab01","tab02ax","tab02bx","tab04x","map00b","map01b","dateSK"]:
    r=requests.get(J+n+".json",headers=H,timeout=60)
    print(n, r.status_code, r.headers.get("last-modified"), len(r.content), r.text[:300].replace("\n"," "))
js=requests.get("https://volbysr.sk/oso/js/functions.js",headers=H,timeout=60).text
for m in re.finditer(r"json", js):
    s=js[max(0,m.start()-160):m.end()+60].replace("\n"," ")
    if "../json/" in s or "getJSON" in s or ".json" in s: print("--", s)
print("HOTOVO")
