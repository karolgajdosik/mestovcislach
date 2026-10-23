import requests, time
s = requests.Session(); s.headers["User-Agent"] = "Mozilla/5.0 (mestovcislach.sk diag)"
for i in range(40):
    if 'id="mhd"' in s.get("https://mestovcislach.sk/presov/zivot/", timeout=30).text: break
    time.sleep(15)
testy = [("https://mestovcislach.sk/presov/zivot/", 'id="mhd"'), ("https://mestovcislach.sk/kosice/", 'volby-mapa'), ("https://mestovcislach.sk/bratislava/volby/", 'volby-mapa'),
         ("https://mestovcislach.sk/data/mesta/mapa/presov.json", 'mhd-zastavky'), ("https://mestovcislach.sk/presov/adresa/", 'ad-form'),
         ("https://mestovcislach.sk/bratislava/", 'Moja adresa'), ("https://mestovcislach.sk/sukromie/", 'Nominatim')]
for u, hľadaj in testy:
    r = s.get(u, timeout=30); print(u, r.status_code, hľadaj, hľadaj in r.text)
print("HOTOVO")
