import requests, time
for i in range(30):
    h=requests.get("https://mestovcislach.sk/?v=%d"%time.time(),headers={"User-Agent":"diag"},timeout=30).text
    if "data-rz" in h: break
    time.sleep(20)
print("rozcestník:", "data-rz-cesta" in h, "pokračovať:", "data-rz-pokracuj" in h)
print("HOTOVO")
