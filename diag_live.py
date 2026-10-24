import requests, re
H={"User-Agent":"Mozilla/5.0 (mestovcislach diag)"}
B="https://volbysr.sk/oso/sk/"
h=requests.get(B,headers=H,timeout=60); h.encoding="utf-8"; t=h.text
print("skripty:", re.findall(r'<script[^>]*src="([^"]+)"', t))
print("odkazy html:", sorted(set(re.findall(r'href="([^"#]+\.html)"', t))))
inline=re.findall(r'<script[^>]*>(.*?)</script>', t, re.S)
for s in inline:
    for m in re.findall(r'["\']([^"\']*(?:json|data|files|api)[^"\']*)["\']', s): print("inline url:", m[:150])
for src in re.findall(r'<script[^>]*src="([^"]+)"', t):
    if 'jquery' in src or 'idsk' in src: continue
    u=requests.compat.urljoin(B,src); js=requests.get(u,headers=H,timeout=60).text
    print("JS", src, len(js), sorted(set(re.findall(r'["\']([^"\'\s]*(?:\.json|/data/|/files/|api)[^"\'\s]*)["\']', js)))[:30])
for p in ["https://volbysr.sk/oso/sk/vysledky_obce.html","https://volbysr.sk/oso/sk/obce.html","https://volbysr.sk/oso/sk/vysledky_hlasovania.html","https://volbysr.sk/oso/sk/suhrnne_vysledky.html","https://volbysr.sk/oso/data/","https://volbysr.sk/oso/files/"]:
    r=requests.get(p,headers=H,timeout=30); print(p, r.status_code, len(r.text))
print("HOTOVO")
