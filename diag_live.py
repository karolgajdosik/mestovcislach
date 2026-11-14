import re, requests, io
s = requests.Session(); s.headers["User-Agent"] = "Mozilla/5.0 (compatible; mestovcislach.sk)"
B = "https://www.minv.sk/lnisdn/statistika/20260218_011722.691_2025-12-MS/statistika/"
for p in ["mesacna/dnvr/dnvr-SR.html", "mesacna/dzor/dzor-SR.html"]:
    r = s.get(B + p, timeout=60); r.encoding = "utf-8"
    tx = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " | ", r.text))
    print("==", p, r.status_code, tx[:1500]); print("  HREF", sorted(set(re.findall(r'href="([^"]+)"', r.text)))[:40])
r = s.get(B + "index-public.html", timeout=60); r.encoding = "utf-8"
print("IDX hrefs sample", [h for h in re.findall(r'href="([^"]+)"', r.text)][:5], len(re.findall(r"\.html", r.text)))
i = r.text.find("územné okresy"); print("IDXSEG", re.sub(r"\s+", " ", r.text[i:i+3000]))
r = s.get("https://www.minv.sk/?celkovy-pocet-evidovanych-vozidiel-v-sr", timeout=60)
tx = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", r.text)); j = tx.find("okres"); print("VOZTXT", tx[j-500:j+800] if j >= 0 else "no okres")
print("VOZSUB", [h for h in re.findall(r'href="([^"]+)"', r.text) if "subor" in h][:20])
for ds in [1, 2, 3]:
    try:
        r = s.post("https://eeadmz1-downloads-api-appservice.azurewebsites.net/ParquetFile/urls", json={"countries": ["SK"], "cities": [], "pollutants": ["PM10"], "dataset": ds, "source": "Api"}, timeout=120)
        print("EEA", ds, r.status_code, len(r.text), r.text[:300].replace("\n", " "))
    except Exception as e: print("EEA ERR", e)
print("HOTOVO")
