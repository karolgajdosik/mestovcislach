"""STATdata – kocky so zonáciou „Obce“ (e_nuts15). Bežný opendata CSV obce nemá, treba filtrovaný endpoint
/opendata/cube/dataset/<kocka>/rows/<dim,ASC,all~…>/columns/<čas,ASC,all>/context/<dim,ASC,all>.
Dimenzia v „context“ sa do CSV nedostane – preto tam dávame len dimenziu s jedinou položkou (jednotka/ukazovateľ),
všetky ostatné idú do riadkov."""

from __future__ import annotations

import csv
import io
import zipfile

from spolocne import s

B = "https://statdata.statistics.sk/public/api/dc"
H = {"Accept": "application/json"}


def polozky(kocka: str, dim_id: str) -> list:
    r = s.get(f"{B}/public/{dim_id}/{kocka}/dimensionItemsInCube", headers=H, timeout=120)
    r.raise_for_status()
    j = r.json()
    return j if isinstance(j, list) else j.get("items") or j.get("content") or []


def riadky_obce(kocka: str) -> list[dict]:
    info = s.get(f"{B}/public/{kocka}/info", headers=H, timeout=60).json()
    dims = info["dimensions"]
    cas = next(d["acronym"] for d in dims if d["type"] == "TIME")
    ostatne = [d for d in dims if d["acronym"] not in (cas, "e_nuts15") and d["type"] != "GEO" or d["acronym"] == "e_nuts14"]
    ostatne = [d for d in dims if d["acronym"] != cas and d["acronym"] != "e_nuts15"]
    jedine = [d for d in ostatne if d["type"] != "GEO" and len(polozky(kocka, d["id"])) == 1]
    if not jedine:
        raise RuntimeError(f"{kocka}: žiadna dimenzia s jednou položkou do kontextu")
    ctx = next((d for d in jedine if d["acronym"] == "e_unit"), jedine[0])
    rows = ["e_nuts15"] + [d["acronym"] for d in ostatne if d is not ctx]
    url = (f"{B}/opendata/cube/dataset/{kocka}/rows/" + "~".join(f"{a},ASC,all" for a in rows)
           + f"/columns/{cas},ASC,all/context/{ctx['acronym']},ASC,all")
    r = s.get(url, params={"type": "CSV", "lang": "SK"}, timeout=900)
    r.raise_for_status()
    c = r.content
    if c[:2] == b"PK":
        z = zipfile.ZipFile(io.BytesIO(c))
        c = z.read(z.namelist()[0])
    out = list(csv.DictReader(io.StringIO(c.decode("utf-8-sig", "replace"))))
    for x in out:
        x["_cas"] = x.get(cas, "")
    return out
