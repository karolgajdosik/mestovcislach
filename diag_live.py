import re, json, requests
from concurrent.futures import ThreadPoolExecutor
H = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/130 Safari/537.36", "Accept": "application/json"}
B = "https://statdata.statistics.sk/public/api/dc"
print(requests.get(f"{B}/public/zp3804rr/info", headers=H, timeout=60).text[:1500])
kody = {}
for page in range(0, 40):
    r = requests.post(B + "/public/bulkDownload/search", json={"query": "", "page": page, "size": 100}, headers=H, timeout=90)
    j = r.json()
    items = j.get("content") if isinstance(j, dict) else j
    if page == 0: print("keys", list(j.keys()) if isinstance(j, dict) else type(j), json.dumps(items[0], ensure_ascii=False)[:400])
    if not items: break
    for it in items:
        s = json.dumps(it, ensure_ascii=False)
        k = re.search(r'"([a-z]{2}\d{4}[a-z]{2})"', s)
        if k: kody[k.group(1)] = it
    if isinstance(j, dict) and j.get("last"): break
print("kociek", len(kody))
def info(k):
    try: return k, requests.get(f"{B}/public/{k}/info", headers=H, timeout=60).text
    except Exception: return k, ""
with ThreadPoolExecutor(8) as ex:
    for k, t in ex.map(info, sorted(kody)):
        if re.search(r'"(?:nameSk|name)"\s*:\s*"Obce"', t) or "e_nuts15" in t:
            nm = re.search(r'"(?:nameSk|title)"\s*:\s*"([^"]+)"', json.dumps(kody[k], ensure_ascii=False))
            print("OBCE", k, "|", nm.group(1) if nm else "")
print("HOTOVO")
