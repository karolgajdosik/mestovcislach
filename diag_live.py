import subprocess, sys, json, re, io, zipfile, csv, requests
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", "scripts/requirements.txt", "openpyxl"])
HB = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/130 Safari/537.36"}
def odkazy(u):
    r = requests.get(u, headers=HB, timeout=60)
    return r.status_code, sorted(set(re.findall(r'href="([^"#]+)"', r.text)))
for u in ["https://volby.statistics.sk/ref/ref2023/", "https://volby.statistics.sk/osk/osk2022/sk/", "https://volby.statistics.sk/oso/oso2022/sk/"]:
    st, o = odkazy(u); print("IDX", u, st, o[:60])
    for x in o:
        if re.search(r"download|stiahn|subor|files|data", x, re.I) and not x.endswith(".css"):
            uu = requests.compat.urljoin(u, x)
            try:
                st2, o2 = odkazy(uu); print("   SUB", uu, st2, [y for y in o2 if re.search(r"\.(csv|zip|xlsx)", y, re.I)][:20])
            except Exception as e: print("   SUB", uu, e)
z = zipfile.ZipFile(io.BytesIO(requests.get("https://volby.statistics.sk/nrsr/nrsr2020/files/NRSR_2020_SK_csv.zip", headers=HB, timeout=300).content))
for n in ["NRSR_2020_SK_tab02e.csv", "NRSR_2020_SK_tab03f.csv", "NRSR_2020_SK_tab0a.csv"]:
    t = z.read(n).decode("utf-8-sig", "replace") if True else ""
    try: t = z.read(n).decode("utf-8-sig")
    except UnicodeDecodeError: t = z.read(n).decode("cp1250")
    print("NR", n, t.split("\n")[0][:400]); print("   ", t.split("\n")[1][:300])
import openpyxl
z = zipfile.ZipFile(io.BytesIO(requests.get("https://volby.statistics.sk/prez/prez2019/files/PRE_2019_KOLO1_xlsx.zip", headers=HB, timeout=300).content))
for n in ["PRE_2019_KOLO1_tab02d.xlsx", "PRE_2019_KOLO1_tab02e.xlsx", "PRE_2019_KOLO1_tab03e.xlsx", "PRE_2019_KOLO1_tab03f.xlsx", "PRE_2019_KOLO1_tab01.xlsx"]:
    wb = openpyxl.load_workbook(io.BytesIO(z.read(n)), read_only=True)
    ws = wb.worksheets[0]; rows = list(ws.iter_rows(max_row=6, values_only=True))
    print("PR", n, ws.max_row, [r for r in rows])
qq = """PREFIX dcat:<http://www.w3.org/ns/dcat#> PREFIX dct:<http://purl.org/dc/terms/>
SELECT ?ds ?u ?f WHERE { ?ds dcat:distribution ?d . OPTIONAL{?d dcat:downloadURL ?u} OPTIONAL{?d dct:format ?f} FILTER(REGEX(STR(?ds), "14fae22e-96ff|f2b3af7a-b4d4|1277119c-0c20")) } LIMIT 40"""
r = requests.get("https://data.slovensko.sk/api/sparql", params={"query": qq}, headers={"Accept": "application/sparql-results+json"}, timeout=120)
urls = []
for x in r.json()["results"]["bindings"]:
    u = x.get("u", {}).get("value"); print("RAD", x["ds"]["value"].rsplit("/",1)[-1][:12], u, x.get("f",{}).get("value","")[-12:]); urls.append(u)
for u in [u for u in urls if u][:4]:
    try:
        r = requests.get(u, headers=HB, timeout=300, stream=True)
        head = next(r.iter_content(3000))
        print("RAH", u, r.status_code, r.headers.get("content-type"), r.headers.get("content-length"), head[:600])
        r.close()
    except Exception as e: print("RAH", u, e)
print("HOTOVO")
