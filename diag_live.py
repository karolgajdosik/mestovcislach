import requests
for c in ["juh","sever","stare-mesto"]:
    try:
        r=requests.get(f"https://mestovcislach.sk/kosice/mestske-casti/{c}/?v=2",timeout=60); print(c,r.status_code,r.headers.get("cf-cache-status"),r.headers.get("age"),r.headers.get("last-modified"),"Kto tu býva" in r.text,"Sčítanie" in r.text)
    except Exception as e: print(c,e)
print("HOTOVO")
