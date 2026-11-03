import requests
for u in ["https://www.crz.gov.sk/", "https://www.crz.gov.sk/export/2026-11-01.zip", "https://www.crz.gov.sk/export/2026-07-17.zip", "https://www.crz.gov.sk/export/2026-07-18.zip", "https://www.crz.gov.sk/export/2026-10-21.zip", "https://www.crz.gov.sk/export/2026-10-22.zip", "https://www.crz.gov.sk/export/2025-03-03.zip"]:
    for ua in ["Mozilla/5.0", "python-requests/2.32"]:
        try:
            r = requests.get(u, headers={"User-Agent": ua}, timeout=60)
            print(u, ua[:10], r.status_code, len(r.content), r.headers.get("server"), r.text[:80].replace("\n"," ") if r.status_code!=200 else "")
        except Exception as e:
            print(u, e)
print("HOTOVO")
