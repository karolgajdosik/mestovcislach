import re, json, requests
H = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/130 Safari/537.36", "Accept": "application/json"}
B = "https://statdata.statistics.sk/public/api/dc"
naj = {}
for q in ["narodení obce", "zomrelí obce", "sťahovanie obce", "prirodzený prírastok", "priemerný vek", "vekové zloženie obce", "byty sčítanie 2021", "domy sčítanie 2021", "kanalizácia", "vodovod", "kúrenie", "zemný plyn", "ubytovacie zariadenia", "prenocovania", "právnické osoby", "podnikatelia fyzické osoby", "organizácie podľa právnej formy", "register organizácií"]:
    try:
        r = requests.post(B + "/public/bulkDownload/search", json={"query": q, "page": 0, "size": 60}, headers=H, timeout=90)
        j = r.json()
    except Exception as e:
        print("ERR", q, e); continue
    items = j.get("content") if isinstance(j, dict) else j
    for it in items or []:
        s = json.dumps(it, ensure_ascii=False)
        kod = re.search(r'"([a-z]{2}\d{4}[a-z]{2})"', s)
        nm = it.get("nameSk") or it.get("name") or re.search(r'"(?:nameSk|title|name)":\s*"([^"]+)"', s)
        if kod and kod.group(1) not in naj:
            naj[kod.group(1)] = (nm if isinstance(nm, str) else (nm.group(1) if nm else s[:120]), q)
print(len(naj))
for k, (n, q) in sorted(naj.items()):
    try:
        info = requests.get(f"{B}/public/{k}/info", headers=H, timeout=60).text
    except Exception:
        info = ""
    zon = "OBCE" if re.search(r"Obce|obce|LAU|e_nuts15", info) else ""
    print(k, zon, "|", str(n)[:110], "|", q)
# prezidentské voľby – súbory
for u in ["https://volby.statistics.sk/opendata/", "https://volby.statistics.sk/prez/prez2024/sk/data02.html", "https://volby.statistics.sk/prez/prez2024/sk/download.html"]:
    try:
        r = requests.get(u, headers=H, timeout=60); print(u, r.status_code, sorted(set(re.findall(r'href="([^"]+\.(?:csv|zip|xlsx))"', r.text)))[:40])
    except Exception as e: print(u, e)
print("HOTOVO")
