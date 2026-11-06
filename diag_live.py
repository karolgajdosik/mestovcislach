import requests
h = requests.get("https://mestovcislach.sk/banskobystricky-kraj/banska-stiavnica/banska-stiavnica/", timeout=60).text
for t in ["Na čo obec minula peniaze", "Pamiatky", "územia európskeho významu", "turistických trás", "Testovanie 9", "autobusových zastávok", "obyvateľov na km²"]:
    print(t, t in h)
print("HOTOVO")
