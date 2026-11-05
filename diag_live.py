import requests,re
for u in ["https://mestovcislach.sk/banskobystricky-kraj/rimavska-sobota/tisovec/","https://mestovcislach.sk/presovsky-kraj/poprad/vysoke-tatry/"]:
    t=requests.get(u,timeout=60,headers={"User-Agent":"mestovcislach-diag"}).text
    print(u,{i:(f'id="{i}"' in t) for i in ["pohyb","byvanie","volby-celostatne","firmy","sluzby"]}, "Sťahovanie" in t, "staníc a zastávok" in t, "OĽANO A PRIATELIA</" in t)
print("HOTOVO")
