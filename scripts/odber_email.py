"""E-mailové upozornenia cez Brevo (Sendinblue SAS, Francúzsko – dáta v EÚ).

Odberatelia sa prihlasujú na webe (functions/api/odber.ts) s dvojitým potvrdením (double opt-in) – e-mailové adresy
sú len v Breve, nikdy v tomto repozitári. Každý kanál upozornení (/kanal/<kluc>.xml) má v Breve vlastný zoznam.

  python scripts/odber_email.py nastavenie  – vytvorí priečinok, zoznamy a šablónu potvrdenia (ak chýbajú)
                                             → public/data/odber-brevo.json (len čísla zoznamov a šablóny, nič tajné)
  python scripts/odber_email.py rozosli     – ráno pošle každému zoznamu s odberateľmi súhrn noviniek z kanála
                                             (stavby, zmluvy, výstrahy) od posledného rozoslania; ak nič nové, nepošle nič.
                                             Sledovanie dodávateľov (zoznam „dodavatel“, atribút ICO): každému odberateľovi
                                             zvlášť (transakčný e-mail) nové zmluvy sledovaných firiem s mestami z CRZ
                                             (data/zmluvy-mesta), s odkazom na odhlásenie (functions/api/odhlasit.ts).
                                             Stav (len časy a posledné ID zmluvy) v data/odber-stav.json.

Potrebuje premennú BREVO_API_KEY (GitHub secret). Bez nej skončí bez chyby.
GDPR: nevypisovať e-mailové adresy ani mená odberateľov do logov.
"""

from __future__ import annotations

import hashlib
import hmac
import html
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

import requests

from spolocne import DATA, KOREN, spusti

API = "https://api.brevo.com/v3"
WEB = "https://mestovcislach.sk"
ODOSIELATEL = {"name": "mestovčíslach.sk", "email": "upozornenia@mestovcislach.sk"}
ODPOVED = "info@mestovcislach.sk"
PRIECINOK = "mestovcislach.sk"
SABLONA = "mestovcislach – potvrdenie odberu"
MAPA = KOREN / "public" / "data" / "odber-brevo.json"
STAV = DATA / "odber-stav.json"
TYPY = "stavby,zmluvy,vystrahy"  # „Na cestách“ sa mení priebežne – patrí na web, nie do ranného e-mailu
CASTI = ["Staré Mesto", "Ružinov", "Vrakuňa", "Podunajské Biskupice", "Nové Mesto", "Rača", "Vajnory", "Karlova Ves", "Dúbravka", "Lamač",
         "Devín", "Devínska Nová Ves", "Záhorská Bystrica", "Petržalka", "Jarovce", "Rusovce", "Čunovo"]
MESTA = json.loads((KOREN / "src" / "mesta.json").read_text(encoding="utf-8"))


def slug(t: str) -> str:
    import unicodedata
    return re.sub(r"\s+", "-", "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn").lower())


def kanaly() -> dict[str, str]:
    """kľúč kanála → názov (BA: celé mesto a 17 MČ, ostatné krajské mestá)."""
    k = {"bratislava": "Bratislava"}
    k.update({slug(c): f"Bratislava – {c}" for c in CASTI})
    k.update({m["slug"]: m["nazov"] for m in MESTA if m.get("aktivne") and not m.get("plne")})
    k["dodavatel"] = "Sledovanie dodávateľov"
    return k


class Brevo:
    def __init__(self, kluc: str):
        self.s = requests.Session()
        self.s.headers.update({"api-key": kluc, "accept": "application/json", "content-type": "application/json"})

    def __call__(self, metoda: str, cesta: str, **kw):
        r = self.s.request(metoda, API + cesta, timeout=60, **kw)
        if r.status_code >= 400:
            raise RuntimeError(f"Brevo {metoda} {cesta}: HTTP {r.status_code} {r.text[:300]}")
        return r.json() if r.content else {}

    def vsetko(self, cesta: str, kluc: str) -> list[dict]:
        out, offset = [], 0
        while True:
            d = self("GET", cesta, params={"limit": 50, "offset": offset})
            dav = d.get(kluc) or []
            out += dav
            if len(dav) < 50:
                return out
            offset += 50


POTVRDENIE = """<!doctype html><html lang="sk"><body style="margin:0;background:#f6f6f4;font-family:Arial,Helvetica,sans-serif;color:#1d1d1f">
<div style="max-width:560px;margin:0 auto;padding:28px 20px">
<p style="font-size:20px;font-weight:800;margin:0 0 20px">mesto<span style="color:#c8102e">v</span>číslach.sk</p>
<div style="background:#fff;border:1px solid #e2e2de;border-radius:12px;padding:22px">
<h1 style="font-size:20px;margin:0 0 12px">Potvrďte odber upozornení</h1>
<p style="line-height:1.55;margin:0 0 18px">Niekto (pravdepodobne vy) zadal túto adresu na webe mestovcislach.sk, aby dostával upozornenia – ranný súhrn noviniek (stavebné zámery, väčšie zmluvy, výstrahy SHMÚ) alebo nové zmluvy sledovanej firmy s mestami. Odber začne až po potvrdení.</p>
<p style="margin:0 0 18px"><a href="{{ doubleoptin }}" style="display:inline-block;background:#c8102e;color:#fff;text-decoration:none;font-weight:700;padding:12px 20px;border-radius:10px">Potvrdiť odber</a></p>
<p style="line-height:1.55;margin:0;color:#5f6368;font-size:13px">Ak ste o odber nežiadali, e-mail ignorujte – bez potvrdenia vám nič posielať nebudeme. Odhlásiť sa dá kedykoľvek jedným klikom v každom e-maile.</p>
</div>
<p style="color:#5f6368;font-size:12px;line-height:1.5;margin:16px 4px 0">mestovcislach.sk · otvorené dáta o slovenských mestách · <a href="https://mestovcislach.sk/sukromie" style="color:#5f6368">Ochrana súkromia</a></p>
</div></body></html>"""


def nastavenie(b: Brevo) -> int:
    priecinky = b.vsetko("/contacts/folders", "folders")
    pr = next((p for p in priecinky if p["name"] == PRIECINOK), None) or b("POST", "/contacts/folders", json={"name": PRIECINOK})
    pr_id = pr["id"]
    zoznamy = {z["name"]: z["id"] for z in b.vsetko("/contacts/lists", "lists")}
    mapa = {"zoznamy": {}, "nazvy": {}}
    for k, nazov in kanaly().items():
        meno = f"Upozornenia – {nazov}"
        if meno not in zoznamy:
            zoznamy[meno] = b("POST", "/contacts/lists", json={"name": meno, "folderId": pr_id})["id"]
            print(f"  nový zoznam: {meno}")
        mapa["zoznamy"][k] = zoznamy[meno]
        mapa["nazvy"][k] = nazov
    atributy = {a["name"] for a in (b("GET", "/contacts/attributes").get("attributes") or [])}
    for atr in ("KANAL", "ICO"):
        if atr not in atributy:
            b("POST", f"/contacts/attributes/normal/{atr}", json={"type": "text"})
            print(f"  nový atribút: {atr}")
    sablony = b("GET", "/smtp/templates", params={"limit": 1000}).get("templates") or []
    s = next((t for t in sablony if t["name"] == SABLONA), None)
    telo = {"templateName": SABLONA, "subject": "Potvrďte odber upozornení z mestovcislach.sk", "htmlContent": POTVRDENIE,
            "sender": ODOSIELATEL, "replyTo": ODPOVED, "isActive": True, "tag": "optin"}
    if s:
        b("PUT", f"/smtp/templates/{s['id']}", json=telo)
        mapa["sablona"] = s["id"]
    else:
        mapa["sablona"] = b("POST", "/smtp/templates", json=telo)["id"]
        print("  nová šablóna potvrdenia")
    MAPA.write_text(json.dumps(mapa, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"Brevo: {len(mapa['zoznamy'])} zoznamov, šablóna {mapa['sablona']}")
    return 0


def novinky(kluc: str, od: datetime) -> list[dict]:
    r = requests.get(f"{WEB}/kanal/{kluc}.xml", params={"typ": TYPY}, timeout=60, headers={"User-Agent": "mestovcislach.sk odber"})
    r.raise_for_status()
    ns = {"a": "http://www.w3.org/2005/Atom"}
    out = []
    for e in ET.fromstring(r.content).findall("a:entry", ns):
        cas = datetime.fromisoformat(e.findtext("a:updated", "", ns).replace("Z", "+00:00"))
        if cas <= od:
            continue
        kat = e.find("a:category", ns)
        out.append({"nazov": e.findtext("a:title", "", ns), "text": e.findtext("a:summary", "", ns), "odkaz": (e.find("a:link", ns).get("href") if e.find("a:link", ns) is not None else WEB),
                    "kategoria": kat.get("term") if kat is not None else "", "cas": cas})
    return sorted(out, key=lambda x: x["cas"], reverse=True)


def email(nazov: str, kluc: str, polozky: list[dict]) -> str:
    h = html.escape
    skupiny: dict[str, list[dict]] = {}
    for p in polozky:
        skupiny.setdefault(p["kategoria"] or "Novinky", []).append(p)
    upoz = f"{WEB}/{'bratislava' if kluc != 'bratislava' and kluc in {slug(c) for c in CASTI} else kluc}/upozornenia"
    bloky = "".join(
        f'<h2 style="font-size:15px;text-transform:uppercase;letter-spacing:.05em;color:#5f6368;margin:22px 0 8px">{h(k)} ({len(v)})</h2>'
        + "".join(f'<div style="border-top:1px solid #e2e2de;padding:10px 0"><a href="{h(p["odkaz"])}" style="color:#1d1d1f;font-weight:700;text-decoration:none">{h(p["nazov"])}</a>'
                  f'<p style="margin:4px 0 0;color:#5f6368;font-size:14px;line-height:1.5">{h(p["text"][:300])}</p></div>' for p in v[:15])
        + (f'<p style="font-size:13px;margin:6px 0 0"><a href="{upoz}" style="color:#c8102e">a ďalšie ({len(v) - 15})</a></p>' if len(v) > 15 else "")
        for k, v in skupiny.items())
    return f"""<!doctype html><html lang="sk"><body style="margin:0;background:#f6f6f4;font-family:Arial,Helvetica,sans-serif;color:#1d1d1f">
<div style="max-width:620px;margin:0 auto;padding:24px 18px">
<p style="font-size:20px;font-weight:800;margin:0 0 16px">mesto<span style="color:#c8102e">v</span>číslach.sk</p>
<div style="background:#fff;border:1px solid #e2e2de;border-radius:12px;padding:20px">
<h1 style="font-size:21px;margin:0 0 4px">Čo je nové: {h(nazov)}</h1>
<p style="color:#5f6368;margin:0">{len(polozky)} {'novinka' if len(polozky) == 1 else 'novinky' if len(polozky) < 5 else 'noviniek'} od posledného súhrnu</p>
{bloky}
<p style="margin:22px 0 0"><a href="{upoz}" style="color:#c8102e;font-weight:700">Všetko na webe</a></p>
</div>
<p style="color:#5f6368;font-size:12px;line-height:1.5;margin:16px 4px 0">Tento súhrn dostávate, lebo ste si ho objednali na mestovcislach.sk. Údaje pochádzajú z verejných zdrojov (Enviroportál, Centrálny register zmlúv, SHMÚ).<br>
<a href="{{{{ unsubscribe }}}}" style="color:#5f6368">Odhlásiť sa</a> · <a href="{WEB}/sukromie" style="color:#5f6368">Ochrana súkromia</a></p>
</div></body></html>"""


def rozosli(b: Brevo) -> int:
    if not MAPA.exists():
        print("Brevo ešte nie je nastavené (chýba public/data/odber-brevo.json) – spustite najprv 'nastavenie'.")
        return 0
    mapa = json.loads(MAPA.read_text(encoding="utf-8"))
    stav = json.loads(STAV.read_text(encoding="utf-8")) if STAV.exists() else {}
    teraz = datetime.now(timezone.utc)
    pocty = {z["id"]: z.get("uniqueSubscribers", z.get("totalSubscribers", 0)) for z in b.vsetko("/contacts/lists", "lists")}
    poslane = 0
    for kluc, lid in mapa["zoznamy"].items():
        if kluc == "dodavatel":
            continue
        odberatelov = pocty.get(lid, 0)
        # prvý súhrn pre nový kanál: novinky za posledný deň
        od = datetime.fromisoformat(stav[kluc]) if kluc in stav else teraz - timedelta(days=1)
        if not odberatelov:
            stav[kluc] = teraz.isoformat(timespec="seconds")
            continue
        try:
            nove = novinky(kluc, od)
        except Exception as e:  # noqa: BLE001
            print(f"::warning title=Odber {kluc}::kanál nedostupný: {e}")
            continue
        if not nove:
            stav[kluc] = teraz.isoformat(timespec="seconds")
            continue
        nazov = mapa["nazvy"].get(kluc, kluc)
        kampan = b("POST", "/emailCampaigns", json={
            "name": f"Súhrn {nazov} {teraz:%Y-%m-%d}", "subject": f"Čo je nové: {nazov} ({len(nove)})",
            "sender": ODOSIELATEL, "replyTo": ODPOVED, "htmlContent": email(nazov, kluc, nove), "recipients": {"listIds": [lid]},
            "inlineImageActivation": False, "mirrorActive": False})
        b("POST", f"/emailCampaigns/{kampan['id']}/sendNow")
        stav[kluc] = teraz.isoformat(timespec="seconds")
        poslane += odberatelov
        print(f"  {nazov}: {len(nove)} noviniek → {odberatelov} odberateľov")
    if "dodavatel" in mapa["zoznamy"]:
        try:
            poslane += dodavatelia(b, mapa["zoznamy"]["dodavatel"], pocty.get(mapa["zoznamy"]["dodavatel"], 0), stav)
        except Exception as e:  # noqa: BLE001
            print(f"::warning title=Odber dodávateľov::{type(e).__name__}: {e}")
    STAV.write_text(json.dumps(dict(sorted(stav.items())), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"Rozoslané e-mailov: {poslane}")
    return 0


# ---------- sledovanie dodávateľov ----------
NAZVY_MIEST = {m["slug"]: m["nazov"] for m in MESTA}


def token(email: str, kluc: str) -> str:
    """Podpis odkazu na odhlásenie (overuje functions/api/odhlasit.ts rovnakým kľúčom)."""
    return hmac.new(kluc.encode(), f"odhlasit:{email.strip().lower()}".encode(), hashlib.sha256).hexdigest()


def nove_zmluvy(od_id: int) -> tuple[list[dict], int]:
    """Zmluvy s IČO (len právnické osoby) s ID väčším ako od_id; vráti aj najväčšie ID."""
    out, naj = [], od_id
    for f in sorted((DATA / "zmluvy-mesta").glob("20*.json")):
        for z in json.loads(f.read_text(encoding="utf-8")).values():
            try:
                i = int(z["id"])
            except (TypeError, ValueError):
                continue
            naj = max(naj, i)
            if i > od_id and z.get("ico") and z.get("p"):
                out.append(z)
    return out, naj


def nove_zmluvy_ine(od: str) -> tuple[list[dict], str]:
    """Bratislava a Košice (data/zmluvy-ine): zmluvy so zverejnením/podpisom po dátume od; vráti aj najnovší dátum."""
    out, naj = [], od
    for f in sorted((DATA / "zmluvy-ine").glob("*.json")):
        for z in json.loads(f.read_text(encoding="utf-8")).get("zmluvy", []):
            naj = max(naj, z["d"])
            if z["d"] > od and z.get("ico") and z.get("p"):
                out.append(z)
    return out, naj


def email_dodavatel(zmluvy: list[dict], odhlasit: str) -> str:
    h = html.escape
    eur = lambda n: f"{round(n or 0):,} €".replace(",", " ")  # noqa: E731
    riadky = "".join(
        f'<div style="border-top:1px solid #e2e2de;padding:10px 0"><a href="{h(z.get("url") or f"https://www.crz.gov.sk/zmluva/{z['id']}/")}" style="color:#1d1d1f;font-weight:700;text-decoration:none">{h(z["p"])}</a>'
        f'<p style="margin:4px 0 0;color:#5f6368;font-size:14px;line-height:1.5">{h(NAZVY_MIEST.get(z["m"], z["m"]))} · {h(z["d"])} · {eur(z["s"]) if z["s"] else "suma neuvedená"}<br>{h((z.get("pr") or "")[:250])}</p></div>'
        for z in zmluvy[:30])
    return f"""<!doctype html><html lang="sk"><body style="margin:0;background:#f6f6f4;font-family:Arial,Helvetica,sans-serif;color:#1d1d1f">
<div style="max-width:620px;margin:0 auto;padding:24px 18px">
<p style="font-size:20px;font-weight:800;margin:0 0 16px">mesto<span style="color:#c8102e">v</span>číslach.sk</p>
<div style="background:#fff;border:1px solid #e2e2de;border-radius:12px;padding:20px">
<h1 style="font-size:21px;margin:0 0 4px">Nové zmluvy sledovaných firiem</h1>
<p style="color:#5f6368;margin:0 0 8px">{len(zmluvy)} {'nová zmluva' if len(zmluvy) == 1 else 'nové zmluvy' if len(zmluvy) < 5 else 'nových zmlúv'} s mestami (Centrálny register zmlúv, otvorené dáta Bratislavy a Košíc)</p>
{riadky}
<p style="margin:22px 0 0"><a href="{WEB}/dodavatelia" style="color:#c8102e;font-weight:700">Sledovať ďalšiu firmu</a></p>
</div>
<p style="color:#5f6368;font-size:12px;line-height:1.5;margin:16px 4px 0">Tento e-mail dostávate, lebo ste si na mestovcislach.sk zapli sledovanie dodávateľov.<br>
<a href="{h(odhlasit)}" style="color:#5f6368">Odhlásiť sa zo sledovania</a> · <a href="{WEB}/sukromie" style="color:#5f6368">Ochrana súkromia</a></p>
</div></body></html>"""


def dodavatelia(b: Brevo, lid: int, odberatelov: int, stav: dict) -> int:
    od_id = int(stav.get("dodavatel_posledne_id", 0) or 0)
    od_den = stav.get("dodavatel_posledny_den_ine", "")
    zmluvy, naj = nove_zmluvy(od_id)
    ine, naj_den = nove_zmluvy_ine(od_den or "9999")
    if od_den:
        zmluvy += ine
    else:  # prvý beh pre BA/KE: len zapamätať najnovší dátum
        _, naj_den = nove_zmluvy_ine("")
    stav["dodavatel_posledny_den_ine"] = naj_den
    if not od_id:  # prvý beh: len zapamätať, kde sme, nič neposielať
        stav["dodavatel_posledne_id"] = str(naj)
        return 0
    if not zmluvy or not odberatelov:
        stav["dodavatel_posledne_id"] = str(naj)
        return 0
    po_ico: dict[str, list[dict]] = {}
    for z in zmluvy:
        po_ico.setdefault(z["ico"], []).append(z)
    kluc = os.environ["BREVO_API_KEY"].strip()
    poslane, offset = 0, 0
    while True:
        d = b("GET", f"/contacts/lists/{lid}/contacts", params={"limit": 500, "offset": offset})
        kontakty = d.get("contacts") or []
        for k in kontakty:
            if k.get("emailBlacklisted"):
                continue
            ico = [i for i in str((k.get("attributes") or {}).get("ICO", "")).split(",") if re.fullmatch(r"\d{8}", i)]
            moje = sorted((z for i in ico for z in po_ico.get(i, [])), key=lambda z: z["d"], reverse=True)
            if not moje:
                continue
            adresa = k["email"]  # nikdy nevypisovať
            odkaz = f"{WEB}/api/odhlasit?e={requests.utils.quote(adresa)}&t={token(adresa, kluc)}"
            b("POST", "/smtp/email", json={
                "sender": ODOSIELATEL, "replyTo": {"email": ODPOVED}, "to": [{"email": adresa}],
                "subject": f"Nové zmluvy: {moje[0]['p'][:60]}" + (f" a ďalšie ({len(moje)})" if len(moje) > 1 else ""),
                "htmlContent": email_dodavatel(moje, odkaz), "tags": ["dodavatel"]})
            poslane += 1
        if len(kontakty) < 500:
            break
        offset += 500
    stav["dodavatel_posledne_id"] = str(naj)
    print(f"  Sledovanie dodávateľov: {len(zmluvy)} nových zmlúv, odoslaných e-mailov: {poslane}")
    return poslane


def main() -> int:
    kluc = os.environ.get("BREVO_API_KEY", "").strip()
    if not kluc:
        print("BREVO_API_KEY nie je nastavený – e-mailové upozornenia sú vypnuté.")
        return 0
    b = Brevo(kluc)
    return nastavenie(b) if sys.argv[1:2] == ["nastavenie"] else rozosli(b)


if __name__ == "__main__":
    spusti(main, "E-mailové upozornenia (Brevo)")
