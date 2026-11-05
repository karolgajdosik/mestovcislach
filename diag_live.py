import subprocess, sys, json, re, time, collections, requests
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", "scripts/requirements.txt"])
sys.path.insert(0, "scripts")
from statdata_obce import riadky_obce
SP = {"e_sex": ["Spolu"], "e_age": ["Spolu"]}
for k, v in [("om7809rr", SP), ("om7806rr", SP), ("pl5001rr", {"e_soiltype": ["Spolu"]})]:
    t0 = time.time()
    try:
        rr = riadky_obce(k, rokov=1, vyber=v)
        print("==", k, len(rr), "s", round(time.time() - t0), list(rr[0].keys()))
        for x in [x for x in rr if x["e_nuts15"].startswith("Vígľaš")][:14]: print("   V", {a: b.strip()[:40] for a, b in x.items() if a != "e_nuts15"})
    except Exception as e: print("==", k, "CHYBA", str(e)[:300])
HH = {"User-Agent": "mestovcislach.sk (info@mestovcislach.sk)"}
for nm, base, typ in [("NP", "https://www.sopsr.sk/geoserver/sz/chranene_uzemia_np_s_op/ows", None), ("VCHU", "https://www.sopsr.sk/geoserver/chranene_objekty/chranene_uzemia_vchu/ows", None), ("CHVU", "https://www.sopsr.sk/geoserver/chranene_objekty/chranene_uzemia_chvu/ows", None)]:
    try:
        cap = requests.get(base, params={"service": "WFS", "version": "2.0.0", "request": "GetCapabilities"}, headers=HH, timeout=90).text
        tn = re.findall(r"<(?:wfs:)?Name>([^<]+)</(?:wfs:)?Name>", cap)
        print(nm, "typy", tn[:6])
        r = requests.get(base, params={"service": "WFS", "version": "2.0.0", "request": "GetFeature", "typeNames": tn[0], "outputFormat": "application/json", "srsName": "EPSG:4326", "count": 3}, headers=HH, timeout=180)
        j = r.json(); f = j["features"]
        print(nm, r.status_code, j.get("totalFeatures") or j.get("numberMatched"), [ {k: str(v)[:40] for k, v in x["properties"].items()} for x in f[:3]], f[0]["geometry"]["type"], str(f[0]["geometry"]["coordinates"])[:80])
    except Exception as e: print(nm, "CHYBA", str(e)[:200])
try:
    r = requests.get("https://gis.geocloud.gov.sk/geoserver/mpsvrsr/ows", params={"service": "WFS", "version": "2.0.0", "request": "GetFeature", "typeNames": "mpsvrsr:crpss", "outputFormat": "application/json", "srsName": "EPSG:4326"}, headers=HH, timeout=300)
    j = r.json(); f = j["features"]
    print("CRPSS", r.status_code, len(f), "kluce", list(f[0]["properties"].keys()))
    for kk in f[0]["properties"]:
        c = collections.Counter(str(x["properties"].get(kk))[:50] for x in f)
        if len(c) < 60: print("   ", kk, len(c), c.most_common(25))
        else: print("   ", kk, len(c), "rôznych")
    print("   geom", sum(1 for x in f if x.get("geometry")))
except Exception as e: print("CRPSS CHYBA", str(e)[:300])
HB = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/130 Safari/537.36"}
for u in ["https://www.minv.sk/?statistika-kriminality-v-slovenskej-republike-csv", "https://www.minv.sk/?statistika-kriminality-v-slovenskej-republike-za-rok-2026-1", "https://www.minv.sk/?statistika_kriminality_v_slovenskej_republike_za_rok_2024_xml"]:
    try:
        r = requests.get(u, headers=HB, timeout=60)
        odk = sorted(set(re.findall(r'href="([^"]+\.(?:csv|xml|xls|xlsx|zip)[^"]*)"', r.text, re.I)))
        print("MV", u, len(odk), odk[:30])
    except Exception as e: print("MV", u, e)
print("HOTOVO")
