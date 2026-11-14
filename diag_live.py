import subprocess, sys; subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", "scripts/requirements.txt", "xlrd"])
import re, requests, json, io
sys.path.insert(0, "scripts")
s = requests.Session(); s.headers["User-Agent"] = "Mozilla/5.0 (compatible; mestovcislach.sk)"
from statdata_obce import B, H
for k in ["st3801rr", "st3802rr", "st3803rr", "st3804rr", "st3805rr", "st3806rr", "st3807rr", "st3808rr", "st3809rr", "st3810rr", "st2001rr", "st2003rr"]:
    try:
        i = s.get(f"{B}/public/{k}/info", headers=H, timeout=60)
        if i.status_code != 200: print("ST", k, i.status_code); continue
        i = i.json(); print("ST", k, (i.get("nameSk") or i.get("name") or "")[:110], [d["acronym"] for d in i["dimensions"]])
    except Exception as e: print("ST ERR", k, e)
# minv nehody tables
r = s.get("https://www.minv.sk/lnisdn/statistika/20260218_011722.691_2025-12-MS/statistika/index-public.html", timeout=60)
t = r.text
txt = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " | ", t))
for m in re.finditer(r"okres", txt, re.I):
    print("NEH", txt[max(0, m.start()-150):m.start()+120]); break
hrefs = re.findall(r'href="([^"]+)"', t)
print("NEHREF", len(hrefs), sorted({re.sub(r"-[^/]*\.html$", "", h) for h in hrefs})[:60])
# SP statistiky
r = s.get("https://www.socpoist.sk/socialne-poistenie/statistiky?ref=2434", timeout=60)
print("SP", r.status_code, [h for h in re.findall(r'href="([^"]+)"', r.text) if re.search(r"statist|xls|okres|dochod", h, re.I)][:40])
# NRO
for u in ["https://www.upsvr.gov.sk/sluzby-zamestnanosti/nastroje-aktivnej-politiky-trhu-prace/zoznam-najmenej-rozvinutych-okresov.html?page_id=13310",
          "https://www.upsvr.gov.sk/najmenej-rozvinute-okresy.html", "https://www.mirri.gov.sk/sekcie/regionalny-rozvoj/najmenej-rozvinute-okresy/"]:
    try:
        r = s.get(u, timeout=60); print("NRO", u, r.status_code, len(r.text), [h for h in re.findall(r'href="([^"]+)"', r.text) if re.search(r"najmenej|nro|rozvinut", h, re.I)][:15])
    except Exception as e: print("NRO ERR", u, e)
# maturita xls columns
import zber_obce_t9 as t9
u = "https://dataportal.nucem.sk/Dataportal-web/web/vysledky/2025/maturita/index.xhtml"
ss = t9.relacia(); h = ss.get(u, timeout=60).text
vs = re.search(r'name="javax.faces.ViewState"[^>]*value="([^"]+)"', h).group(1)
links = re.findall(r"'(j_idt\d+):(j_idt\d+)':'j_idt\d+:j_idt\d+'\},''\);return false\">([^<]*)<", h)
for f, lid, n in links:
    if n.strip() in ("Matematika", "Slovenský jazyk a literatúra", "Anglický jazyk úroveň B2"):
        r = ss.post(u, data={f: f, f"{f}:{lid}": f"{f}:{lid}", "javax.faces.ViewState": vs}, headers={"Referer": u}, timeout=300)
        import xlrd
        try:
            sh = xlrd.open_workbook(file_contents=r.content).sheet_by_index(0)
            print("MAT", n, sh.nrows, sh.row_values(0)[:30]); print("   ", sh.row_values(1)[:30])
        except Exception as e: print("MAT ERR", n, r.status_code, r.content[:100], e)
print("HOTOVO")
