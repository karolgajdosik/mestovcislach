import requests
s = requests.Session(); s.headers["User-Agent"] = "mestovcislach.sk diag"
for u in ("https://volby.statistics.sk/oso/oso2022/files/OSO2022_SK_csv.zip", "https://volby.statistics.sk/oso/oso2022/files/OSO2022_SK_xlsx.zip",
          "https://volby.statistics.sk/osk/osk2022/files/OSK2022_SK_csv.zip"):
    try:
        r = s.get("https://archive.org/wayback/available", params={"url": u}, timeout=60).json()
        snap = r.get("archived_snapshots", {}).get("closest")
        print(u, "→", snap and (snap["url"], snap["timestamp"], snap["status"]))
        if snap:
            raw = snap["url"].replace("/http", "id_/http", 1)
            z = s.get(raw, timeout=180); print("   stiahnuté", z.status_code, len(z.content), z.content[:2])
    except Exception as e: print(u, type(e).__name__, e)
print("HOTOVO")
