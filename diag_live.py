import requests, datetime, time, re
d = datetime.date(2026, 7, 10); out = []
dni = [d + datetime.timedelta(i) for i in range(12)] + [datetime.date(2026, m, x) for m in (8, 9, 10) for x in (3, 4, 5, 10)] + [datetime.date(2026, 10, x) for x in range(25, 33) if x <= 31] + [datetime.date(2026, 11, 2), datetime.date(2026, 5, 7), datetime.date(2026, 5, 9), datetime.date(2026, 5, 11)]
for x in dni:
    r = requests.get(f"https://www.crz.gov.sk/export/{x}.zip", timeout=60)
    out.append(f"{x} {x.strftime('%a')} {r.status_code} {len(r.content)}")
    time.sleep(1)
print("\n".join(out))
r = requests.get("https://www.crz.gov.sk/export/2026-07-17.zip", timeout=60); print(re.sub(r"<[^>]+>", " ", r.text))
r = requests.get("https://www.crz.gov.sk/otvorene-data/", timeout=60); print(r.status_code); print(sorted(set(re.findall(r'href="([^"]*(?:export|zip|xml|data)[^"]*)"', r.text)))[:40])
print("HOTOVO")
