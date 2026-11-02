"""E-mail prevádzkovateľovi pri zmene výsledku automatickej kontroly (kontrola.yml): nový problém alebo „všetko opäť funguje“.

  python scripts/kontrola_email.py problemy.md    – zoznam problémov (Markdown, riadky „- …“)
  python scripts/kontrola_email.py --ok           – všetko opäť funguje
Príjemca: STATISTIKY_EMAIL (GitHub secret) alebo info@mestovcislach.sk. Bez BREVO_API_KEY skončí bez chyby.
"""

from __future__ import annotations

import html
import os
import re
import sys

import requests

ODOSIELATEL = {"name": "mestovčíslach.sk – kontrola", "email": "upozornenia@mestovcislach.sk"}


def main() -> int:
    kluc = os.environ.get("BREVO_API_KEY", "").strip()
    if not kluc:
        print("BREVO_API_KEY chýba – e-mail sa neposiela.")
        return 0
    beh = os.environ.get("BEH_URL", "")
    if sys.argv[1:2] == ["--ok"]:
        predmet = "Web mestovcislach.sk: všetko opäť funguje"
        telo = "<p>Automatická kontrola už nenašla žiadny problém – zdroje aj zbery dát fungujú.</p>"
    else:
        riadky = [r[2:] for r in open(sys.argv[1], encoding="utf-8").read().splitlines() if r.startswith("- ")]
        if not riadky:
            return 0
        md = lambda x: re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html.escape(x))  # noqa: E731
        md2 = lambda x: re.sub(r"\((https://[^)\s]+)\)", r'(<a href="\1">detail</a>)', md(x))  # noqa: E731
        predmet = f"Web mestovcislach.sk: {len(riadky)} {'problém' if len(riadky) == 1 else 'problémy' if len(riadky) < 5 else 'problémov'}"
        telo = "<p>Automatická kontrola webu našla:</p><ul>" + "".join(f"<li>{md2(r)}</li>" for r in riadky) + "</ul>" \
               "<p>Ak ide o výpadok zdroja (úrad, mesto), zvyčajne sa napraví sám. Keď to bude v poriadku, príde ďalší e-mail.</p>"
    obsah = f"""<div style="font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;max-width:620px;margin:0 auto;color:#1b1e23">
<h2 style="margin:0 0 12px">{html.escape(predmet)}</h2>{telo}
{f'<p style="font-size:13px;color:#666"><a href="{html.escape(beh)}">Beh kontroly</a></p>' if beh else ''}</div>"""
    prijemca = os.environ.get("STATISTIKY_EMAIL", "").strip() or "info@mestovcislach.sk"
    r = requests.post("https://api.brevo.com/v3/smtp/email", headers={"api-key": kluc, "accept": "application/json"}, timeout=60,
                      json={"sender": ODOSIELATEL, "to": [{"email": prijemca}], "subject": predmet, "htmlContent": obsah, "tags": ["kontrola"]})
    r.raise_for_status()
    print("E-mail odoslaný.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
