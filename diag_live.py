import requests, re
h=requests.get("https://zastupitelstvo.bratislava.sk/zasadnutia/",headers={"User-Agent":"mestovcislach.sk"},timeout=60).text
print(len(h)); print(re.findall(r'<option[^>]*value="(\d+)"[^>]*>([^<]{0,40})</option>',h)[:30]); print([m for m in re.findall(r'.{0,80}volObd.{0,80}',h)][:8])
print("HOTOVO")
