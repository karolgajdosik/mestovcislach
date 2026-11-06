import subprocess, sys, json, re, collections, requests
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", "scripts/requirements.txt"])
sys.path.insert(0, "scripts")
from statdata_obce import riadky_obce
rr = riadky_obce("pl5001rr", rokov=1)
print("pl5001rr riadkov", len(rr), list(rr[0].keys()))
c = collections.Counter(x["e_nuts15"].strip() for x in rr)
print("uzemi", len(c), list(c.items())[:15])
for x in [x for x in rr if x["e_nuts15"].strip().startswith(("Vígľaš", "Brezany"))][:40]: print("  ", {a: b.strip()[:35] for a, b in x.items()})
HB = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/130 Safari/537.36"}
r = requests.get("https://www.minv.sk/?statistika-kriminality-v-slovenskej-republike-za-rok-2026-1", headers=HB, timeout=60)
print("MV2026", r.status_code, sorted(set(re.findall(r'href="([^"]+swift_data[^"]+)"', r.text)))[:20])
r = requests.get("https://www.minv.sk/?statistika_kriminality_v_slovenskej_republike_za_rok_2024_xml", headers=HB, timeout=60)
odk = sorted(set(re.findall(r'href="([^"]+swift_data[^"]+)"', r.text)))
dec = [o for o in odk if "12_december" in o and "1xml" in o] or odk[-6:]
print("MV2024 dec", dec)
x = requests.get("https://www.minv.sk" + dec[0], headers=HB, timeout=60).text
print(len(x)); print(x[:2500])
print("okresy?", len(set(re.findall(r"(?:OR PZ|Okres|okres)[^<]{0,40}", x))), list(set(re.findall(r"(?:OR PZ|Okres|okres)[^<]{0,40}", x)))[:10])
print("HOTOVO")
