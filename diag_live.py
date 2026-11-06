import re, requests, json, subprocess, sys
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", "scripts/requirements.txt"])
s = requests.Session(); s.headers["User-Agent"] = "mestovcislach.sk (info@mestovcislach.sk)"
def g(u, **k):
    try:
        r = s.get(u, timeout=60, **k); return r
    except Exception as e:
        print("ERR", u, str(e)[:150]); return None
def show(u, pat=None, n=600):
    r = g(u)
    if r is None: return None
    print("==", u, r.status_code, r.headers.get("content-type"), len(r.content))
    if pat:
        for m in sorted(set(re.findall(r'(?:href|src)="([^"]+)"', r.text))):
            if re.search(pat, m, re.I): print("  ", m[:200])
    else:
        print(r.text[:n].replace("\n", " "))
    return r
r = show("https://rozpocet.sk/web/", r"\.js|api")
for js in re.findall(r'src="([^"]+\.js)"', r.text if r is not None else ""):
    u = js if js.startswith("http") else "https://rozpocet.sk/web/" + js.lstrip("/")
    t = g(u)
    if t is not None:
        print("JS", u, len(t.text), sorted(set(re.findall(r'["\'](/?api/[A-Za-z0-9_/\-{}.]+)', t.text)))[:60])
show("https://vysledky.nucem.sk/", r"t9|testovanie|skol|api|\.js|xls|csv")
show("https://www.apa.sk/", r"zverej|prijima|platb")
show("https://www.apa.sk/zoznam-prijimatelov-financnych-prostriedkov")
for ns in ["chranene_objekty", "sz", "natura", "uev"]:
    r = g(f"https://www.sopsr.sk/geoserver/{ns}/ows", params={"service":"WFS","request":"GetCapabilities","version":"1.1.0"})
    if r is not None:
        print("SOP", ns, r.status_code, sorted(set(re.findall(r"<Name>([^<]+)</Name>", r.text)))[:80])
sys.path.insert(0, "scripts")
from statdata_obce import B, H, polozky
info = s.get(f"{B}/public/og3805rr/info", headers=H, timeout=60).json()
for d in info["dimensions"]:
    if "legal" in d["acronym"]:
        print("og3805rr forms:", [x.get("nameSk") for x in polozky("og3805rr", d["id"])])
print("HOTOVO")
