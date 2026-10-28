import requests,re,html
h=requests.get("https://egov.presov.sk/Default.aspx?NavigationState=440:0:",timeout=40).text
for m in re.finditer(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>',h,re.S):
    if re.search('rozpo|TU|20\d\d',m.group(0),re.I): print(html.unescape(m.group(1))[:150],"|",re.sub('<[^>]+>','',m.group(2)).strip()[:50])
txt=re.sub(r'\s+',' ',re.sub('<[^>]+>',' ',h))
for y in ("2026","2027"):
    for mm in re.finditer(y,txt): print(y,"…",txt[max(0,mm.start()-80):mm.start()+80])
print("selects:",re.findall(r'<select[^>]*name="([^"]+)"',h), re.findall(r'<option[^>]*>(20\d\d)</option>',h)[:10])
print("HOTOVO")
