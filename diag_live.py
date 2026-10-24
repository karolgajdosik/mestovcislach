import requests, re, json
H={"User-Agent":"Mozilla/5.0 (mestovcislach diag)"}
B="https://volbysr.sk/oso/"
h=requests.get(B+"sk/vysledky_obce.html",headers=H,timeout=60); h.encoding="utf-8"
s=[x for x in re.findall(r'<script[^>]*>(.*?)</script>', h.text, re.S) if "graph01" in x][0]
s=re.sub(r"\s+"," ",s); i=s.find("select: function"); print("HANDLER:", s[i:i+2500])
g=requests.get(B+"select/graph01.json",headers=H,timeout=60).json()
print("graph01 počet", len(g), g[:2])
mesta=[x for x in g if any(n in str(x.get('label','')) for n in ['Nitra','Trnava','Trenčín','Žilina','Banská Bystrica','Prešov','Košice','Bratislava'])]
print("MESTA:", [ (x.get('label'), x.get('value'), x.get('okres')) for x in mesta][:60])
print("HOTOVO")
