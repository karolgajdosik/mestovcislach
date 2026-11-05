import re, io, json, requests, openpyxl
H = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/130 Safari/537.36"}
r = requests.get("https://www.upsvr.gov.sk/statistiky/mesacne-statistiky-miest-a-obci.html?page_id=1009850", headers=H, timeout=60)
odk = re.findall(r'href="([^"]+)"[^>]*>([^<]*)<', r.text)
cand = [(u, t.strip()) for u, t in odk if re.search(r"\.(xlsx?|csv|zip|json)", u, re.I) or "page_id=10098" in u]
for x in cand[:40]: print(x)
x = next((u for u, t in cand if re.search(r"\.(xlsx?|csv|zip)", u, re.I)), None)
if x:
    if x.startswith("/"): x = "https://www.upsvr.gov.sk" + x
    f = requests.get(x, headers=H, timeout=120); print("file", x, f.status_code, len(f.content), f.content[:4])
    if f.content[:2] == b"PK" and x.lower().endswith(("xlsx", "xls")):
        wb = openpyxl.load_workbook(io.BytesIO(f.content), read_only=True, data_only=True)
        print(wb.sheetnames)
        for ws in wb.worksheets[:3]:
            for i, row in enumerate(ws.iter_rows(values_only=True)):
                if i > 14: break
                print("  ", [c for c in row][:14])
# STATdata sections search for odpad
r = requests.get("https://statdata.statistics.sk/public/api/dc/public/sections/expandAll", headers=H, timeout=120)
print("sections", r.status_code, len(r.text))
if r.ok:
    t = r.text
    for m in re.finditer(r'"(?:code|publicId|dataCubeId|kod)"\s*:\s*"([a-z]{2}\d{4}[a-z]{2})"[^{}]{0,400}', t):
        s = m.group(0)
        if re.search(r"odpad|uchádz|nezamest|škôl|žiak|materskej", s, re.I): print("  ", s[:250])
print("HOTOVO")
