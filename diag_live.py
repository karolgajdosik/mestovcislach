import requests
H={"User-Agent":"Mozilla/5.0"}
for c in ["nrsr/2023/NRSR2023_SK","eup/2024/EP2024_SK"]:
    for t in ["tab02d","tab03e","tab01"]:
        u=f"https://web.archive.org/web/2025id_/https://volby.statistics.sk/opendata/{c}_{t}.csv"
        try:
            r=requests.get(u,headers=H,timeout=120); print(u, r.status_code, len(r.content), r.content[:80])
        except Exception as e: print(u,"ERR",e)
print("HOTOVO")
