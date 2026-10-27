"""Týždenný e-mail so štatistikami návštevnosti (Cloudflare Web Analytics) pre prevádzkovateľa webu.

Každý pondelok: návštevy za posledných 7 dní oproti predchádzajúcemu týždňu, návštevy po dňoch,
najčítanejšie stránky, odkiaľ ľudia prišli, zariadenia a krajiny. Web Analytics nepoužíva cookies
a neukladá IP adresy – sú to len súhrnné počty. Nič sa neukladá do repozitára.

Potrebuje GitHub secrets:
  CF_API_TOKEN       – Cloudflare API token s oprávnením Account › Account Analytics › Read
  BREVO_API_KEY      – odoslanie e-mailu (už nastavený)
  STATISTIKY_EMAIL   – (nepovinné) adresa príjemcu; predvolene info@mestovcislach.sk
Bez CF_API_TOKEN skončí bez chyby (len vypíše, že nie je nastavený).
"""

from __future__ import annotations

import html
import os
import sys
from datetime import date, timedelta

import requests

CF = "https://api.cloudflare.com/client/v4"
HOSTY = ["mestovcislach.sk", "www.mestovcislach.sk"]
ODOSIELATEL = {"name": "mestovčíslach.sk", "email": "upozornenia@mestovcislach.sk"}

DOTAZ = """query($a: String!, $f: AccountRumPageloadEventsAdaptiveGroupsFilter_InputObject!, $p: AccountRumPageloadEventsAdaptiveGroupsFilter_InputObject!) {
  viewer { accounts(filter: {accountTag: $a}) {
    spolu: rumPageloadEventsAdaptiveGroups(limit: 1, filter: $f) { count sum { visits } }
    pred: rumPageloadEventsAdaptiveGroups(limit: 1, filter: $p) { count sum { visits } }
    dni: rumPageloadEventsAdaptiveGroups(limit: 14, filter: $f, orderBy: [date_ASC]) { count sum { visits } dimensions { date } }
    stranky: rumPageloadEventsAdaptiveGroups(limit: 15, filter: $f, orderBy: [sum_visits_DESC]) { count sum { visits } dimensions { requestPath } }
    zdroje: rumPageloadEventsAdaptiveGroups(limit: 10, filter: $f, orderBy: [sum_visits_DESC]) { sum { visits } dimensions { refererHost } }
    zariadenia: rumPageloadEventsAdaptiveGroups(limit: 5, filter: $f, orderBy: [sum_visits_DESC]) { sum { visits } dimensions { deviceType } }
    krajiny: rumPageloadEventsAdaptiveGroups(limit: 5, filter: $f, orderBy: [sum_visits_DESC]) { sum { visits } dimensions { countryName } }
  } }
}"""


def cf(token: str, metoda: str, cesta: str, **kw) -> dict:
    r = requests.request(metoda, f"{CF}{cesta}", headers={"Authorization": f"Bearer {token}"}, timeout=60, **kw)
    r.raise_for_status()
    return r.json()


def ucet(token: str) -> str:
    if os.environ.get("CF_ACCOUNT_ID"):
        return os.environ["CF_ACCOUNT_ID"].strip()
    u = cf(token, "GET", "/accounts", params={"per_page": 5}).get("result") or []
    if not u:
        raise RuntimeError("Token nevidí žiadny Cloudflare účet – pridajte mu oprávnenie Account Analytics: Read.")
    return u[0]["id"]


def statistiky(token: str, a: str, od: date, do: date) -> dict:
    """Skúsi filter bez botov a len pre hlavnú doménu; ak ho API nepozná, postupne ho zjednoduší."""
    pod = od - timedelta(days=7)
    zaklady = [{"bot": 0, "requestHost_in": HOSTY}, {"requestHost_in": HOSTY}, {}]
    chyba = None
    for z in zaklady:
        f = {"date_geq": od.isoformat(), "date_leq": do.isoformat(), **z}
        p = {"date_geq": pod.isoformat(), "date_leq": (od - timedelta(days=1)).isoformat(), **z}
        d = cf(token, "POST", "/graphql", json={"query": DOTAZ, "variables": {"a": a, "f": f, "p": p}})
        if d.get("errors"):
            chyba = "; ".join(e.get("message", "") for e in d["errors"])
            continue
        return d["data"]["viewer"]["accounts"][0]
    raise RuntimeError(f"Cloudflare GraphQL: {chyba}")


def v(x: dict) -> int:
    return int((x.get("sum") or {}).get("visits") or 0)


def tabulka(nadpis: str, riadky: list[tuple[str, int]], spolu: int) -> str:
    if not riadky:
        return ""
    r = "".join(f'<tr><td style="padding:4px 8px;border-bottom:1px solid #eee">{html.escape(n)}</td>'
                f'<td style="padding:4px 8px;border-bottom:1px solid #eee;text-align:right">{c}</td>'
                f'<td style="padding:4px 8px;border-bottom:1px solid #eee;text-align:right;color:#666">{round(100 * c / spolu) if spolu else 0} %</td></tr>'
                for n, c in riadky)
    return f'<h3 style="margin:20px 0 6px">{nadpis}</h3><table style="border-collapse:collapse;width:100%;font-size:14px">{r}</table>'


def main() -> int:
    token = os.environ.get("CF_API_TOKEN", "").strip()
    brevo = os.environ.get("BREVO_API_KEY", "").strip()
    if not token:
        print("CF_API_TOKEN nie je nastavený – týždenný e-mail so štatistikami je vypnutý.")
        return 0
    do = date.today() - timedelta(days=1)
    od = do - timedelta(days=6)
    s = statistiky(token, ucet(token), od, do)
    spolu, pred = v((s["spolu"] or [{}])[0]), v((s["pred"] or [{}])[0])
    zobrazenia = int(((s["spolu"] or [{}])[0]).get("count") or 0)
    zmena = f"{'+' if spolu >= pred else '−'}{abs(round(100 * (spolu - pred) / pred))} % oproti predchádzajúcemu týždňu" if pred else "prvý týždeň merania"
    dni = [(date.fromisoformat(x["dimensions"]["date"]).strftime("%a %d. %m.").replace("Mon", "po").replace("Tue", "ut").replace("Wed", "st").replace("Thu", "št").replace("Fri", "pi").replace("Sat", "so").replace("Sun", "ne"), v(x)) for x in s["dni"]]
    naj = max(dni, key=lambda x: x[1]) if dni else None
    stranky = [(x["dimensions"]["requestPath"] or "/", v(x)) for x in s["stranky"]]
    zdroje = [((x["dimensions"]["refererHost"] or "priamo / správy").replace("www.", ""), v(x)) for x in s["zdroje"]]
    zariadenia = [({"desktop": "počítač", "mobile": "mobil", "tablet": "tablet"}.get(x["dimensions"]["deviceType"], x["dimensions"]["deviceType"] or "iné"), v(x)) for x in s["zariadenia"]]
    krajiny = [(x["dimensions"]["countryName"] or "neznáma", v(x)) for x in s["krajiny"]]

    maxd = max([c for _, c in dni] or [1]) or 1
    graf = "".join(f'<tr><td style="padding:2px 8px;font-size:13px;white-space:nowrap">{d}</td><td style="padding:2px 0;width:100%">'
                   f'<div style="background:#c8102e;height:12px;border-radius:6px;width:{max(2, round(100 * c / maxd))}%"></div></td>'
                   f'<td style="padding:2px 8px;font-size:13px;text-align:right">{c}</td></tr>' for d, c in dni)
    obdobie = f"{od.day}. {od.month}. – {do.day}. {do.month}. {do.year}"
    telo = f"""<div style="font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;max-width:640px;margin:0 auto;color:#1b1e23">
<h2 style="margin:0 0 4px">Návštevnosť mestovcislach.sk</h2><p style="margin:0 0 16px;color:#666">{obdobie}</p>
<p style="font-size:28px;font-weight:700;margin:0">{spolu} návštev</p>
<p style="margin:4px 0 16px;color:#444">{zmena} · {zobrazenia} zobrazení stránok{f' · najviac v deň {naj[0]} ({naj[1]})' if naj and naj[1] else ''}</p>
<table style="border-collapse:collapse;width:100%">{graf}</table>
{tabulka('Najčítanejšie stránky (vstupné)', stranky, spolu)}
{tabulka('Odkiaľ prišli', zdroje, spolu)}
{tabulka('Zariadenia', zariadenia, spolu)}
{tabulka('Krajiny', krajiny, spolu)}
<p style="margin-top:24px;font-size:12px;color:#888">Cloudflare Web Analytics (bez cookies, bez robotov). „Priamo / správy“ sú aj odkazy poslané cez WhatsApp, Messenger či e-mail.</p></div>"""
    print(f"{obdobie}: {spolu} návštev ({zmena}); stránky {len(stranky)}, zdroje {len(zdroje)}")
    if "--nahlad" in sys.argv or not brevo:
        print("Náhľad bez odoslania." if brevo else "BREVO_API_KEY chýba – e-mail sa neodošle.")
        return 0
    prijemca = os.environ.get("STATISTIKY_EMAIL", "").strip() or "info@mestovcislach.sk"
    r = requests.post("https://api.brevo.com/v3/smtp/email", headers={"api-key": brevo, "accept": "application/json"}, timeout=60, json={
        "sender": ODOSIELATEL, "to": [{"email": prijemca}], "subject": f"Návštevnosť {obdobie}: {spolu} návštev ({zmena.split(' oproti')[0]})",
        "htmlContent": telo, "tags": ["statistiky"]})
    r.raise_for_status()
    print("E-mail odoslaný.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # noqa: BLE001
        detail = ""
        if isinstance(e, requests.HTTPError) and e.response is not None:
            detail = f" ({e.response.request.method} {e.response.url.split('?')[0]}: {e.response.text[:300]})"
        sprava = f"{type(e).__name__}: {e}{detail}".replace("%", "%25").replace("\r", "").replace("\n", "%0A")
        print(f"::error title=Štatistiky::{sprava}")
        sys.exit(1)
