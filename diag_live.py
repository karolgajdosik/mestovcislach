import requests, zipfile, io, csv, json
H={"User-Agent":"Mozilla/5.0"}
def info(name, url):
    try:
        r=requests.get(url,headers=H,timeout=300)
        print("==",name, r.status_code, r.headers.get("content-type"), len(r.content))
        z=zipfile.ZipFile(io.BytesIO(r.content))
        print(" súbory:", [(i.filename,i.file_size) for i in z.infolist()][:25])
        names=z.namelist()
        def tab(n):
            m=[x for x in names if x.endswith(n)]
            return list(csv.DictReader(io.StringIO(z.read(m[0]).decode("utf-8-sig",errors="replace")))) if m else []
        cal=tab("calendar.txt"); cd=tab("calendar_dates.txt")
        if cal: print(" calendar:", min(c["start_date"] for c in cal), max(c["end_date"] for c in cal), len(cal))
        if cd: print(" calendar_dates:", min(c["date"] for c in cd), max(c["date"] for c in cd), len(cd))
        st=tab("stops.txt"); print(" stops", len(st), "stop_times rows ~", sum(1 for _ in io.StringIO(z.read([x for x in names if x.endswith('stop_times.txt')][0]).decode('utf-8-sig',errors='replace'))) if any(x.endswith('stop_times.txt') for x in names) else 0)
        ag=tab("agency.txt"); print(" agency", [a.get("agency_name") for a in ag])
        if not cal and not cd: print(" hlavičky:", {n: z.read(n)[:200] for n in names[:6]})
    except Exception as e: print(name,"ERR",e)
info("KE", "https://www.arcgis.com/sharing/rest/content/items/ba941d7bc56a462684a261d4f35ce17d/data")
info("BA", "https://www.arcgis.com/sharing/rest/content/items/aba12fd2cbac4843bc7406151bc66106/data")
info("PO", "https://www.arcgis.com/sharing/rest/content/items/f1033ca6c2f4461d9aba285e1c7cb079/data")
r=requests.get("https://www.arcgis.com/sharing/rest/search",params={"q":"GTFS AND (Slovakia OR MHD OR cestovný)","num":50,"f":"json"},headers=H,timeout=60).json()
for it in r.get("results",[]): print("AGOL", it["id"], it["owner"], it["title"], it["type"], it.get("modified"))
for q in ["GTFS","cestovný poriadok MHD"]:
    try:
        r=requests.get("https://data.slovensko.sk/api/action/package_search",params={"q":q,"rows":30},headers=H,timeout=60)
        print("NKOD", q, r.status_code)
        for p in r.json()["result"]["results"]: print("  ", p["name"], "|", p.get("title"), "|", (p.get("organization") or {}).get("title"))
    except Exception as e: print("NKOD ERR", q, e)
print("HOTOVO")
