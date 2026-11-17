import subprocess, sys as _s; subprocess.run([_s.executable,"-m","pip","install","-q","shapely","pyproj"],check=False)
import requests
s=requests.Session(); s.headers.update({"User-Agent":"mestovcislach.sk (info@mestovcislach.sk) zber pamiatok"})
subory=["Dóm svätej Alžbety, Košice.jpg","Bratislava Old Town Hall.jpg"]
r=s.post("https://commons.wikimedia.org/w/api.php",data={"action":"query","format":"json","prop":"imageinfo","iiprop":"url|extmetadata","iiurlwidth":480,"titles":"|".join("File:"+f for f in subory)},timeout=60)
print(r.status_code, r.text[:300])
import re
r=requests.get("https://query.wikidata.org/sparql",params={"query":'SELECT ?img WHERE { wd:Q853472 wdt:P18 ?img }'},headers={"User-Agent":"mestovcislach.sk (info@mestovcislach.sk)","Accept":"application/sparql-results+json"},timeout=60).json()
print(r["results"]["bindings"])
print("HOTOVO")
