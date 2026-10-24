import requests, re
H={"User-Agent":"Mozilla/5.0 (mestovcislach diag)"}
B="https://volbysr.sk/oso/"
js=re.sub(r"\s+"," ",requests.get(B+"js/functions.js",headers=H,timeout=60).text)
i=js.find("function showCommuneResults"); print("SCR:", js[i:i+3000])
print("HOTOVO")
