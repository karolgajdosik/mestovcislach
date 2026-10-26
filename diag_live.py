import requests
for c in ["juh","sever","stare-mesto"]:
    try:
        r=requests.get(f"https://mestovcislach.sk/kosice/mestske-casti/{c}/",timeout=60); print(c,r.status_code,"Kto tu býva" in r.text,"Sčítanie" in r.text)
    except Exception as e: print(c,e)
print("HOTOVO")
