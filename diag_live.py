import subprocess, sys; subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", "scripts/requirements.txt"])
import re, requests, json
s = requests.Session(); s.headers["User-Agent"] = "Mozilla/5.0 (compatible; mestovcislach.sk)"
r = s.get("https://sdi.eea.europa.eu/webdav/datastore/public/eea_t_ied-eprtr_p_2007-2022_v11_r00/", timeout=90)
tok = re.findall(r"datashare/s/([A-Za-z0-9]+)", r.text); print("TOK", tok[:3])
if tok:
    t = tok[0]
    p = s.request("PROPFIND", "https://sdi.eea.europa.eu/datashare/public.php/webdav/", auth=(t, ""), headers={"Depth": "infinity"}, timeout=120)
    print("PROPFIND", p.status_code, re.findall(r"<d:href>([^<]+)</d:href>", p.text)[:60], re.findall(r"<d:getcontentlength>(\d+)", p.text)[:60])
A = "https://ags.geology.sk/arcgis/rest/services/"
for sv in ["wgs_atlasy/zosuvy_SR_50_wgs", "Geofond/zosuvy_vect", "WebServices/RADON", "Zranitelnost/riziko", "wgs_atlasy/nachylnostUzemiaNaSvahovePohyby_SR_50_wgs"]:
    try:
        j = s.get(A + sv + "/MapServer?f=json", timeout=60).json()
        print("SV", sv, [(l["id"], l["name"]) for l in j.get("layers", [])][:12], j.get("spatialReference"), j.get("maxRecordCount"))
        for l in j.get("layers", [])[:4]:
            lj = s.get(A + sv + f"/MapServer/{l['id']}?f=json", timeout=60).json()
            c = s.get(A + sv + f"/MapServer/{l['id']}/query", params={"where": "1=1", "returnCountOnly": "true", "f": "json"}, timeout=60).json()
            print("   L", l["id"], l["name"], lj.get("geometryType"), [f["name"] for f in lj.get("fields", [])][:14], c)
    except Exception as e: print("SVERR", sv, e)
print("HOTOVO")
