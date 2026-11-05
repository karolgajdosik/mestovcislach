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


def riadky_obce(kocka: str, rokov: int | None = None, vyber: dict[str, list[str]] | None = None) -> list[dict]:
    """rokov = len posledných N rokov (filter na serveri, menší súbor); časová dimenzia musí byť e_year.
    vyber = {dimenzia: [názvy položiek]} – na serveri sa stiahnu len tieto položky (napr. pohlavie a vek „Spolu“)."""
    info = s.get(f"{B}/public/{kocka}/info", headers=H, timeout=60).json()
    dims = info["dimensions"]
    cas = next(d["acronym"] for d in dims if d["type"] == "TIME")
    ostatne = [d for d in dims if d["acronym"] != cas and d["acronym"] != "e_nuts15"]
    jedine = [d for d in ostatne if d["type"] != "GEO" and len(polozky(kocka, d["id"])) == 1]
    if jedine:
        ctx = next((d for d in jedine if d["acronym"] == "e_unit"), jedine[0])
    else:  # jednotka je daná ukazovateľom – v CSV budú prázdne („.“) kombinácie, volajúci ich vynechá
        ctx = next((d for d in ostatne if d["acronym"] == "e_unit"), None)
        if not ctx:
            raise RuntimeError(f"{kocka}: žiadna dimenzia vhodná do kontextu")
    casy = "all"
    if rokov and cas == "e_year":
        do = int(str(info.get("timePeriodTo") or "")[:4] or 0)
        casy = ",".join(str(r) for r in range(do - rokov + 1, do + 1)) if do else "all"
    rows = ["e_nuts15"] + [d["acronym"] for d in ostatne if d is not ctx]
    filt: dict[str, str] = {}
    for d in ostatne:
        if vyber and d["acronym"] in vyber:
            pol = {(x.get("nameSk") or "").strip(): x.get("acronym") for x in polozky(kocka, d["id"])}
            akr = [pol[n] for n in vyber[d["acronym"]] if pol.get(n)]
            if len(akr) != len(vyber[d["acronym"]]):
                raise RuntimeError(f"{kocka}/{d['acronym']}: položky {vyber[d['acronym']]} nie sú medzi {list(pol)[:20]}")
            filt[d["acronym"]] = ",".join(akr)
    url = (f"{B}/opendata/cube/dataset/{kocka}/rows/" + "~".join(f"{a},ASC,{filt.get(a, 'all')}" for a in rows)
           + f"/columns/{cas},ASC,{casy}/context/{ctx['acronym']},ASC,all")
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
