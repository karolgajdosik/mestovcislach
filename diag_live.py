# DNS TXT záznamy domény (overenie Google/Bing) – len typ záznamu, nie hodnoty tokenov.
import requests
for meno in ("mestovcislach.sk", "www.mestovcislach.sk"):
    for typ in ("TXT", "CNAME"):
        r = requests.get("https://cloudflare-dns.com/dns-query", params={"name": meno, "type": typ}, headers={"accept": "application/dns-json"}, timeout=30).json()
        for a in r.get("Answer", []):
            d = a["data"].strip('"')
            druh = "google-site-verification" if "google-site-verification" in d else "bing (ms=)" if d.lower().startswith("ms=") else "spf" if d.startswith("v=spf") else d[:40]
            print(meno, typ, druh)
r = requests.get("https://mestovcislach.sk/BingSiteAuth.xml", timeout=30); print("BingSiteAuth.xml", r.status_code)
