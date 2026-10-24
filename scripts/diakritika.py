"""Doplnenie diakritiky do názvov stĺpcov a mestských častí v tabuľkách mesta.

Veľa tabuliek data.bratislava.sk má stĺpce ako POCET_OBYVATELOV alebo hodnoty „Petrzalka“.
Pre čitateľnosť ich na webe zobrazujeme s diakritikou (len známe slová, inak bez zmeny).
"""

from __future__ import annotations

import re
import unicodedata

SLOVA = {
    "pocet": "počet", "mestska": "mestská", "cast": "časť", "statne": "štátne", "sukromne": "súkromné", "cirkevne": "cirkevné",
    "uzemie": "územie", "obyvatelov": "obyvateľov", "priemerny": "priemerný", "migracne": "migračné", "ostatne": "ostatné",
    "vzdelanie": "vzdelanie", "zriadovatel": "zriaďovateľ", "scenar": "scenár", "dlzka": "dĺžka", "trzby": "tržby", "region": "región",
    "zivota": "života", "pracovny": "pracovný", "trzba": "tržba", "mesiacov": "mesiacov", "cas": "čas", "sluzby": "služby",
    "naklady": "náklady", "prirastok": "prírastok", "pricina": "príčina", "smrti": "smrti", "uhrnna": "úhrnná", "financne": "finančné",
    "denni": "denní", "externi": "externí", "plodnosti": "plodnosti", "funkcia": "funkcia", "podnikov": "podnikov",
    "ziaci": "žiaci", "stupen": "stupeň", "studia": "štúdia", "vynosy": "výnosy", "domacnosti": "domácnosti", "ostatni": "ostatní",
    "cinnost": "činnosť", "priestupky": "priestupky", "deti": "deti", "pristahovania": "prisťahovania", "navstevnost": "návštevnosť",
    "uchadzacov": "uchádzačov", "pracovnikov": "pracovníkov", "doch": "doch.", "ustanoveny": "ustanovený", "plny": "plný",
    "uvazok": "úväzok", "kratsi": "kratší", "prijmov": "príjmov", "starnutia": "starnutia", "priemyslu": "priemyslu", "ekon": "ekon.",
    "zataz": "zaťaž.", "dopravne": "dopravné", "uhradene": "uhradené", "skola": "škola", "umrtnosti": "úmrtnosti", "prirodzeny": "prirodzený",
    "bytov": "bytov", "prispevky": "príspevky", "pokuty": "pokuty", "prispevok": "príspevok", "skoly": "školy", "ucitelia": "učitelia",
    "pedagogicki": "pedagogickí", "asistenti": "asistenti", "plodnost": "plodnosť", "stahovania": "sťahovania", "vodne": "vodné",
    "stocne": "stočné", "zrazky": "zrážky", "aktivacia": "aktivácia", "vlastnych": "vlastných", "vykonov": "výkonov",
    "hospodarskej": "hospodárskej", "cinnosti": "činnosti", "studentov": "študentov", "migracie": "migrácie", "vytriedeny": "vytriedený",
    "vekova": "veková", "materialu": "materiálu", "energii": "energií", "dane": "dane", "poplatky": "poplatky", "opravne": "opravné",
    "polozky": "položky", "hospodarsku": "hospodársku", "splatna": "splatná", "odlozena": "odložená", "dan": "daň", "prispevku": "príspevku",
    "pozadovana": "požadovaná", "schvalena": "schválená", "ziskova": "zisková", "stratova": "stratová", "indikator": "indikátor",
    "datum": "dátum", "alkoholu": "alkoholu", "kultura": "kultúra", "neuhradene": "neuhradené", "vysoka": "vysoká",
    "absolventov": "absolventov", "zamestnanost": "zamestnanosť", "zariadenie": "zariadenie", "klubu": "klubu", "odchadzka": "odchádzka",
    "zam": "zam.", "skol": "škôl", "ini": "iní", "prevadzkovatelia": "prevádzkovatelia", "vlastnici": "vlastníci", "verejneho": "verejného",
    "nazov": "názov", "zriadovatela": "zriaďovateľa", "obyvatelia": "obyvatelia", "nezamestnanost": "nezamestnanosť", "zakaznici": "zákazníci",
    "policajta": "policajta", "integrovani": "integrovaní", "vystahovania": "vysťahovania", "spolocnost": "spoločnosť", "ziadatelia": "žiadatelia",
    "celkovy": "celkový", "objednavky": "objednávky", "vydavky": "výdavky", "stoloch": "stoloch", "pokut": "pokút", "rozvodovost": "rozvodovosť",
    "energeticke": "energetické", "specificka": "špecifická", "fakturovanej": "fakturovanej", "lozkova": "lôžková", "vydavkov": "výdavkov",
    "badatelia": "bádatelia", "odkial": "odkiaľ", "blokova": "bloková", "objektivna": "objektívna", "zodpovednost": "zodpovednosť",
    "zahranicnej": "zahraničnej", "zmesovy": "zmesový", "ostatny": "ostatný", "nakladov": "nákladov", "spolocnosti": "spoločnosti",
    "zasadnutie": "zasadnutie", "poradie": "poradie", "hlasovania": "hlasovania", "cislo": "číslo", "vymera": "výmera", "terenu": "terénu",
    "uzemny": "územný", "plan": "plán", "vzdialenost": "vzdialenosť", "mapovania": "mapovania", "cistota": "čistota", "verejny": "verejný",
    "pozivanie": "požívanie", "verejnosti": "verejnosti", "zriadovana": "zriaďovaná", "nezriadovana": "nezriaďovaná",
    "pristahovanych": "prisťahovaných", "vystahovanych": "vysťahovaných", "chmelnice": "chmeľnice", "najazdene": "najazdené",
    "cisticka": "čistička", "odpadovych": "odpadových", "vod": "vôd", "cistej": "čistej", "matiek": "matiek", "migracny": "migračný",
    "migracna": "migračná", "efektivnost": "efektívnosť", "aktivnych": "aktívnych", "obce": "obce", "verejnym": "verejným",
    "zasobovani": "zásobovaní", "pitnou": "pitnou", "socialne": "sociálne", "vyznania": "vyznania", "vynosov": "výnosov",
    "bytovej": "bytovej", "hovorov": "hovorov", "korupcia": "korupcia", "sprenevera": "sprenevera", "nadzemne": "nadzemné",
    "podzemne": "podzemné", "sachty": "šachty", "kanalizacne": "kanalizačné", "vodomerne": "vodomerné", "rozlisenia": "rozlíšenia",
    "pocet_": "počet", "zmena": "zmena", "obdobie": "obdobie", "priemerna": "priemerná", "koncentracia": "koncentrácia",
    "limitna": "limitná", "hodnota": "hodnota", "monitoracia": "monitorovacia", "monitorovacia": "monitorovacia", "stanica": "stanica",
    "prekroceni": "prekročení", "prekrocenim": "prekročením", "dni": "dní", "zdrav": "zdrav.", "podiel": "podiel", "vek": "vek",
    "rok": "rok", "okres": "okres", "spolu": "spolu", "pohlavie": "pohlavie", "odvetvie": "odvetvie", "kraj": "kraj", "typ": "typ",
    "skupina": "skupina", "mesiac": "mesiac", "trieda": "trieda", "osobach": "osobách", "sluzieb": "služieb", "ubytovanie": "ubytovanie",
    "pozn": "pozn.", "obyvatel": "obyvateľ", "hodiny": "hodiny", "rozloha": "rozloha", "lokality": "lokality", "vzorky": "vzorky",
    "analyzy": "analýzy", "meranie": "meranie", "krajina": "krajina", "prace": "práce", "opravy": "opravy", "realizoval": "realizoval",
    "vozidla": "vozidlá", "kamery": "kamery", "bezpecnostne": "bezpečnostné", "parkoviska": "parkoviská", "tabulke": "tabuli",
    "domovy": "domovy", "mladeze": "mládeže", "ubytovani": "ubytovaní", "jedalne": "jedálne", "stravnici": "stravníci",
    "projektovana": "projektovaná", "ubytovane": "ubytované", "zariadenia": "zariadenia", "vlakove": "vlakové", "miestove": "miestové",
    "kilometre": "kilometre", "prostriedok": "prostriedok", "autobusy": "autobusy", "elektricky": "električky", "trolejbusy": "trolejbusy",
}
MESTSKE_CASTI = ["Staré Mesto", "Podunajské Biskupice", "Ružinov", "Vrakuňa", "Nové Mesto", "Rača", "Vajnory", "Devínska Nová Ves", "Dúbravka",
                 "Karlova Ves", "Devín", "Lamač", "Záhorská Bystrica", "Čunovo", "Jarovce", "Petržalka", "Rusovce", "Bratislava"]


def ascii(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn").lower()


HODNOTY = {ascii(m): m for m in MESTSKE_CASTI} | {ascii(f"Bratislava - {m}"): f"Bratislava - {m}" for m in MESTSKE_CASTI} | \
          {ascii(f"Bratislava-{m}"): f"Bratislava-{m}" for m in MESTSKE_CASTI}


def nazov_stlpca(t: str) -> str:
    """„Pocet obyvatelov“ → „Počet obyvateľov“ (len ak názov nemá žiadnu diakritiku)."""
    if re.search(r"[áäčďéíĺľňóôŕšťúýž]", t, re.I):
        return t
    slova = [SLOVA.get(w.lower(), w) if w.isalpha() else w for w in re.split(r"(\W+)", t)]
    vysl = "".join(slova)
    return vysl[:1].upper() + vysl[1:]


def hodnota(v):
    if isinstance(v, str) and not re.search(r"[áäčďéíĺľňóôŕšťúýž]", v, re.I):
        return HODNOTY.get(ascii(v.strip()), v)
    return v
