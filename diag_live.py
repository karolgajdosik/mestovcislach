import sys, time, json
sys.path.insert(0, "scripts")
t0 = time.time()
import zber_obce_wiki_osm as z
try:
    z.osm()
    d = json.load(open("data/obce/osm.json"))
    for k in ["510483", "511994", "528595", "582000", "598186"]:
        print(k, d["obce"].get(k))
    for n in ("Bratislava", "Košice"):
        print(n, d["obce"].get(z.MESTA.get(n)))
except Exception as e:
    print("CHYBA", type(e).__name__, str(e)[:300])
print("cas", round(time.time() - t0))
print("HOTOVO")
