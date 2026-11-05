import re, io, requests, openpyxl
H = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/130 Safari/537.36"}
r = requests.get("https://www.upsvr.gov.sk/statistiky/mesacne-statistiky-miest-a-obci.html?page_id=1009850", headers=H, timeout=60)
roky = sorted(set(re.findall(r'href="(https://www\.upsvr\.gov\.sk/statistiky/mesacne-statistiky-miest-a-obci/(\d{4})\.html\?page_id=\d+)"', r.text)), key=lambda x: x[1])
print(roky)
u = roky[-1][0]
r = requests.get(u, headers=H, timeout=60)
subory = re.findall(r'href="([^"]*mesta_a_o[^"]*\.xlsx?)"', r.text)
print(subory)
f = requests.get(subory[0] if subory[0].startswith("http") else "https://www.upsvr.gov.sk" + subory[0], headers=H, timeout=120)
wb = openpyxl.load_workbook(io.BytesIO(f.content), read_only=True, data_only=True)
print(wb.sheetnames)
for ws in wb.worksheets[:4]:
    print("== ", ws.title)
    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i > 12: break
        print("  ", [c for c in row if c is not None][:16])
print("HOTOVO")
