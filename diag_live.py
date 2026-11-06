import requests
h = requests.get("https://mestovcislach.sk/banskobystricky-kraj/detva/viglas/", timeout=60).text
for t in ["Veková pyramída", "Domácnosti, byty a práca", "Staršie voľby", "Účasť v ďalších hlasovaniach", "Podľa OpenStreetMap", "prvá písomná zmienka", "nadmorská výška"]:
    print(t, t in h)
print("HOTOVO")
