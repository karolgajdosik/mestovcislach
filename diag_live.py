import subprocess, sys, json, re, requests
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", "scripts/requirements.txt"])
import xml.etree.ElementTree as ET
HB = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/130 Safari/537.36"}
x = requests.get("https://www.minv.sk/swift_data/source/policia/statistiky_2024/12_december/1statistika_podla_druhu_kriminality_1_31.12.2024.xml", headers=HB, timeout=90).content
ns = {"ss": "urn:schemas-microsoft-com:office:spreadsheet"}
root = ET.fromstring(x)
for ws in root.findall("ss:Worksheet", ns)[:40]:
    rows = ws.findall(".//ss:Row", ns)
    vals = [[(c.find("ss:Data", ns).text if c.find("ss:Data", ns) is not None else "") for c in r.findall("ss:Cell", ns)] for r in rows]
    print("SHEET", ws.get("{urn:schemas-microsoft-com:office:spreadsheet}Name"), len(rows))
for ws in root.findall("ss:Worksheet", ns)[:2]:
    rows = ws.findall(".//ss:Row", ns)
    for r in rows[:30]:
        print("  ", [ (c.find("ss:Data", ns).text or "")[:30] if c.find("ss:Data", ns) is not None else "" for c in r.findall("ss:Cell", ns)][:14])
r = requests.get("https://www.minv.sk/?statistika-kriminality-v-slovenskej-republike-za-rok-2025-1", headers=HB, timeout=60)
print("MV2025", sorted(set(re.findall(r'href="([^"]+swift_data[^"]+)"', r.text)))[-8:])
subprocess.run([sys.executable, "scripts/zber_obce_vrstvy.py"])
subprocess.run([sys.executable, "scripts/zber_obce_statdata.py", "uzemie", "obyvatelia"])
o = json.load(open("data/obce/uzemie.json")); print("uzemie", len(o["obce"]), o["obce"].get("518921"))
o = json.load(open("data/obce/obyvatelia.json")); print("obyv", o["obce"].get("518921"))
o = json.load(open("data/obce/chranene.json")); print("chranene", len(o["obce"]), [(k, v) for k, v in o["obce"].items() if k in ("560103", "518921", "511218")][:3])
o = json.load(open("data/obce/socialne.json")); print("soc", len(o["obce"]), o.get("stav"), o["obce"].get("518921"), o["obce"].get("508438"))
print("HOTOVO")
