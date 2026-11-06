import requests
for u in ["https://mestovcislach.sk/banskobystricky-kraj/detva/viglas/", "https://mestovcislach.sk/presovsky-kraj/poprad/vysoke-tatry/"]:
    t = requests.get(u, timeout=60, headers={"User-Agent": "mestovcislach-diag"}).text
    print(u, {i: (f'id="{i}"' in t) for i in ["vzdelanie", "kataster", "okres-cisla", "sluzby"]}, "32,0 km" in t, "TANAP" in t)
print("HOTOVO")
