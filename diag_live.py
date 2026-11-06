import re, requests, json
s = requests.Session(); s.headers["User-Agent"] = "Mozilla/5.0 mestovcislach.sk"
A = "https://rozpocet.sk/rest/api/"
def g(p):
    try:
        r = s.get(A + p, timeout=90); print("API", p, r.status_code, r.text[:700].replace("\n"," ")); return r
    except Exception as e: print("ERR", p, e)
r = g("organizacie/hladajObec/" + requests.utils.quote("Vígľaš") + "/2024")
r = g("organizacie/hladajObec/" + requests.utils.quote("Vígľaš") + "/SK")
g("organizacie/podurovne/SK/SAM/3")
g("rozpocet/rozpoctySamKrajov/2024")
print("HOTOVO")
