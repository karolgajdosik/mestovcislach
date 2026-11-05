import re, io, json, requests
H = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/130 Safari/537.36"}
r = requests.get("https://www.upsvr.gov.sk/statistiky/nezamestnanost-mesacne-statistiky/2026.html?page_id=1254", headers=H, timeout=60)
i = r.text.find("Mesačné štatistiky miest a obcí")
print(r.text[i-1500:i+300])
r = requests.get("https://statdata.statistics.sk/public/api/dc/opendata/cubes/all", headers=H, timeout=120)
print("cubes", r.status_code, len(r.text))
try:
    j = r.json()
    items = j if isinstance(j, list) else j.get("data") or j.get("items") or list(j.values())[0]
    print(type(items), len(items)); print(json.dumps(items[0], ensure_ascii=False)[:600])
    for c in items:
        t = json.dumps(c, ensure_ascii=False)
        if re.search(r"odpad|nezamest|uchádza|škol|žiak|materské", t, re.I) and re.search(r"obc|obce|LAU|mest", t, re.I):
            print("  ", t[:300])
except Exception as e:
    print("ERR", e, r.text[:500])
print("HOTOVO")
