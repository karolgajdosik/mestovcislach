import re, io, csv, json, zipfile, collections, requests
H = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/130 Safari/537.36"}
B = "https://statdata.statistics.sk/public/api/dc"
def stiahni(kod):
    info = requests.get(f"{B}/public/{kod}/info", headers={**H, "Accept": "application/json"}, timeout=60).json()
    dims = [d["acronym"] for d in info["dimensions"]]
    geo = next(d["acronym"] for d in info["dimensions"] if d["type"] == "GEO" and d["acronym"] == "e_nuts15")
    cas = next(d["acronym"] for d in info["dimensions"] if d["type"] == "TIME")
    ine = [d for d in dims if d not in (geo, cas)]
    rows = "~".join(f"{d},ASC,all" for d in [geo] + ine[:-1])
    ctx = f"{ine[-1]},ASC,all"
    u = f"{B}/opendata/cube/dataset/{kod}/rows/{rows}/columns/{cas},ASC,all/context/{ctx}"
    r = requests.get(u, params={"type": "CSV", "lang": "SK"}, headers=H, timeout=900)
    c = r.content
    if c[:2] == b"PK":
        z = zipfile.ZipFile(io.BytesIO(c)); c = z.read(z.namelist()[0])
    return info, ine, list(csv.DictReader(io.StringIO(c.decode("utf-8-sig", "replace"))))
for kod in ["om7103rr", "om7052rr", "om7811rr", "om7815rr", "om7816rr", "om7813rr", "om7821rr", "og3805rr", "og3808rr", "zd5001rr", "cr3805qr", "ik5001rr", "ku5008rr"]:
    try:
        info, ine, rr = stiahni(kod)
    except Exception as e:
        print(kod, "ERR", str(e)[:200]); continue
    print(f"== {kod} {info['nameSk'][:70]} | {info.get('timePeriodTo')} | riadkov {len(rr)} | stĺpce {list(rr[0].keys()) if rr else None} | context {ine[-1]}")
    if not rr: continue
    for k in rr[0]:
        if k in ("hodnota", "e_nuts15"): continue
        v = collections.Counter(x[k] for x in rr); print("   ", k, len(v), [x[:60] for x in list(v)[:14]])
    vz = [x for x in rr if x["e_nuts15"].startswith("Vígľaš")][:12]
    for x in vz: print("    V:", {k: v[:50] for k, v in x.items() if k != "e_nuts15"})
print("HOTOVO")
