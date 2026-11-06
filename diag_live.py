import re, requests, json, io
s = requests.Session(); s.headers["User-Agent"] = "mestovcislach.sk (info@mestovcislach.sk)"
u = "http://dataportal.nucem.sk/Dataportal-web/web/vysledky/2025/testovanie/index.xhtml"
h = s.get(u, timeout=60).text
vs = re.findall(r'name="javax.faces.ViewState"[^>]*value="([^"]+)"', h)[0]
names = re.findall(r"'j_idt35:(j_idt\d+)'\},''\);return false\">([^<]*)", h)
print(names)
r = s.post(u, data={"j_idt35": "j_idt35", "j_idt35:j_idt36": "j_idt35:j_idt36", "javax.faces.ViewState": vs}, timeout=120)
print("POST", r.status_code, r.headers.get("content-type"), r.headers.get("content-disposition"), len(r.content))
if r.content[:4] in (b"\xd0\xcf\x11\xe0", b"PK\x03\x04"):
    import subprocess, sys
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "xlrd", "openpyxl"])
    import pandas as pd
    x = pd.read_excel(io.BytesIO(r.content), header=None)
    print(x.shape); print(x.head(8).to_string()[:3000])
t = s.get("https://rozpocet.sk/web/app/services.js", timeout=60).text
i = t.find("getPodurovnovePolozky"); print(t[i:i+900])
for q in ["rozpocet/polozkySumarPodurovni/SAM/210/2024/DESC/3?uroven=CELKOVY&EKV=SpoluV&ORG=11&ORG=23&ORG=22"]:
    r = s.get("https://rozpocet.sk/rest/api/" + q, timeout=120); print("API", r.status_code, r.text[:1500])
print("HOTOVO")
