"""Triedenie datasetov data.bratislava.sk: čo web už používa, čo spracúva osobitný zber,
čo sa vynecháva (s dôvodom) a ktoré stĺpce sa nikdy nezverejňujú.

Kľúč = prvých 8 znakov ID položky (ArcGIS item id). Ostatné tabuľky do 20 000 riadkov
spracuje všeobecný import (zber_tabulky.py) do Katalógu dát (/data).
"""

# Datasety zobrazené priamo na stránkach webu (vlastné zbery)
NA_WEBE = {
    "bed5ccdb": ("/financie", "Príjmy mesta"), "e5a12556": ("/financie", "Príjmy podľa druhu"), "e59ddd92": ("/financie", "Výdavky mesta"),
    "0cd89fe5": ("/financie", "Výdavky podľa programov"), "71c76459": ("/financie", "Výsledok hospodárenia"),
    "dec22cd0": ("/financie", "Zmluvy magistrátu"), "8bd7889e": ("/financie", "Majetok – pozemky"),
    "08b48885": ("/prostredie", "PM10"), "c560d929": ("/prostredie", "Prekročenia PM10"), "7146fc00": ("/prostredie", "PM2,5"), "6e18d5a0": ("/prostredie", "Ozón"),
    "807a19f8": ("/prostredie", "Odpad na obyvateľa"), "561283d4": ("/prostredie", "Recyklácia"), "8afaff7c": ("/prostredie", "Skládkovanie"),
    "b000dfd7": ("/prostredie", "Výsadba stromov"),
    "aba12fd2": ("/doprava", "MHD – cestovné poriadky GTFS"), "34a7ec01": ("/doprava", "Prepravení cestujúci"),
    "39d5a295": ("/doprava", "Dopravné nehody"), "b72dc2a2": ("/doprava", "Nehody so zranením"), "7b5628f9": ("/doprava#premavka", "Sčítače áut"),
    "097b7c8b": ("/doprava#premavka", "Sčítače cyklistov"), "84ba9f28": ("/doprava#premavka", "Sčítače chodcov"),
    "08643896": ("/doprava#cyklo", "Stanice BAjk"),
    "f1aeacee": ("/vybavenost", "Zoznam ZŠ"), "3cca7b58": ("/vybavenost", "Zoznam MŠ 2026"),
    "ef5254fb": ("/vybavenost#spadova-skola", "Spádové obvody ZŠ"), "a6a832dd": ("/vybavenost#spadova-skola", "Spádové obvody MŠ 2026"),
    "4033a902": ("/volby#hlasovania", "Hlasovania poslancov"), "7b0fe912": ("/volby#hlasovania", "Zasadnutia zastupiteľstva"),
}

# Datasety, ktoré spracuje osobitný zber (veľké alebo mapové) – (stránka, popis, zber)
OSOBITNE = {
    # financie – faktúry, objednávky, zmluvy (súhrny podľa dodávateľov a rokov, bez fyzických osôb)
    "7f719a61": ("/financie#faktury", "Faktúry magistrátu", "zber_faktury.py"), "e3a9501c": ("/financie#faktury", "Objednávky magistrátu", "zber_faktury.py"),
    "6b2c7034": ("/financie#faktury", "Faktúry OLO", "zber_faktury.py"), "cb90eb53": ("/financie#faktury", "Objednávky OLO", "zber_faktury.py"),
    "a5068dd4": ("/financie#faktury", "Zmluvy OLO", "zber_faktury.py"), "bd9ee647": ("/financie#faktury", "Faktúry Marianum", "zber_faktury.py"),
    "b50effaa": ("/financie#faktury", "Zmluvy Marianum", "zber_faktury.py"), "8cb2a28c": ("/financie#faktury", "Faktúry MIB", "zber_faktury.py"),
    # bezpečnosť – udalosti mestskej polície (súhrny podľa MČ, ulíc, druhov a rokov)
    "2566d894": ("/bezpecnost", "Priestupky podľa druhu 2017–2022", "zber_bezpecnost.py"), "22a2a9f6": ("/bezpecnost", "Podozrenia z trestných činov", "zber_bezpecnost.py"),
    "45348130": ("/bezpecnost", "Ostatné udalosti", "zber_bezpecnost.py"), "d3d71db2": ("/bezpecnost", "Priestupky a výška pokút", "zber_bezpecnost.py"),
    # podnety občanov
    "96b70a02": ("/bezpecnost#podnety", "Podnety občanov magistrátu", "zber_bezpecnost.py"),
    # mapové vrstvy
    "ccaa77c5": ("/mapa", "Bezbariérovosť", "zber_vrstvy.py"), "226e7387": ("/mapa", "Pitné fontány", "zber_vrstvy.py"),
    "ffc00f30": ("/mapa", "Športoviská", "zber_vrstvy.py"), "5242099b": ("/mapa", "Služby pre ľudí bez domova", "zber_vrstvy.py"),
    "9d318577": ("/mapa", "Vysadené stromy od 2019", "zber_vrstvy.py"), "0ce440f8": ("/mapa", "Starostlivosť o dreviny", "zber_vrstvy.py"),
    
    "48b41105": ("/mapa", "Chovné a veterinárne zariadenia", "zber_vrstvy.py"),
    "45f653d4": ("/mapa#horucavy", "Ochladzovacie miesta (Ochlaď sa!)", "zber_vrstvy.py"), "a8ef3fba": ("/mapa", "Fixpointy na zber injekčných striekačiek", "zber_vrstvy.py"),
    "17666d9d": ("/mapa", "Debarierizované chodníky", "zber_vrstvy.py"),
    "7a8c8bd7": ("/mapa", "Klimatický atlas – citlivosť budov na zrážky", "zber_klima.py"), "367d0139": ("/mapa", "Klimatický atlas – citlivosť celková", "zber_klima.py"),
    "8eedf533": ("/mapa", "Klimatický atlas – citlivosť na horúčavy", "zber_klima.py"), "575142ec": ("/mapa", "Klimatický atlas – riziko horúčav", "zber_klima.py"),
    "be617c15": ("/mapa", "Klimatický atlas – riziko celkové", "zber_klima.py"), "074fc4b3": ("/mapa", "Klimatický atlas – riziko pre dopravu", "zber_klima.py"),
    "61a9db38": ("/mapa", "Klimatický atlas – riziko zrážok pre budovy", "zber_klima.py"), "7e67f27f": ("/mapa", "Dostupnosť kúpalísk", "zber_klima.py"),
    "ffe51d79": ("/mapa", "Hustota obyvateľov (štvorce 1 km)", "zber_klima.py"),
    "81ff5b48": ("/mapa", "Klimatický atlas – citlivosť dopravnej infraštruktúry na zrážky", "zber_klima.py"),
    "f99f75fb": ("/mapa", "Klimatický atlas – kapacita budov na zrážky", "zber_klima.py"),
    # dlhé časové rady – súhrn po mesiacoch
    "bc6f1d93": ("/katalog", "Cyklosčítač Berg (mesačne)", "zber_tabulky.py"), "0de0dba7": ("/katalog", "Cyklosčítač Viedenská (mesačne)", "zber_tabulky.py"),
}

# Vynechané datasety a dôvod
VYNECHANE = {
    "81c4f202": "Surové GPS záznamy polohy električiek jednej linky v októbri 2017–2019 (476 tisíc riadkov) – jednorazová analytická vzorka bez prínosu pre obyvateľov; aktuálnu MHD máme z cestovných poriadkov.",
    "c529f24c": "Záznamy o jednotlivých osobách pozitívnych na Covid-19 (pohlavie, mestská časť, dátum) – citlivé zdravotné údaje o jednotlivcoch; nezverejňujeme ani v anonymizovanej podobe.",
    "9d734ed0": "Staršia verzia (rajonizácia MŠ 2025) – web používa novšiu rajonizáciu MŠ 2026.",
    "89825507": "Staršia verzia evidencie pozemkov (2019) – web používa majetok mesta k 31. 12. 2025.",
    "b485f865": "Staršia verzia evidencie pozemkov (2020) – web používa majetok mesta k 31. 12. 2025.",
    "6908f880": "Staršia verzia (zoznam MŠ 2025) – web používa zoznam MŠ 2026.",
    "1607632e": "Mesačné čerpanie rozpočtu len za rok 2021 (57 tisíc riadkov po položkách) – jednorazový rok; rozpočet za všetky roky máme zo záverečných účtov.",
    "14464afe": "Anglická verzia datasetu „Zoznam zastávok turistických autobusov v roku 2025“ – používame slovenskú.",
    "f1daafc7": "Hranice mestských častí – web používa vlastné hranice (rovnaké územie); duplicitné.",
    "55ce5137": "Funkčné plochy územného plánu (Shapefile, veľké polygóny s právnymi kódmi) – na mape by bez výkladu zavádzali; odkazujeme na mestský geoportál.",
    "c676285f": "Zameranie verejnej zelene – 302 tisíc bodov (jednotlivé stromy a kry) je pre web príliš veľa; na mape ukazujeme výsadbu od 2019 a ošetrované dreviny.",
    # dotazníkové prieskumy – surové odpovede respondentov
    "7e2f4bb0": "Surové odpovede dotazníka (Grössling) s voľným textom respondentov – riziko osobných údajov vo voľných odpovediach; vyhodnotenie zverejňuje mesto pri projekte.",
    "fab84720": "Surové odpovede dotazníka (Krížna) s voľným textom respondentov – riziko osobných údajov vo voľných odpovediach.",
    "5b4161fd": "Surové odpovede dotazníka (Rohlík) s voľným textom respondentov – riziko osobných údajov vo voľných odpovediach.",
    "e6075311": "Surové odpovede dotazníka (Mudrochova) s voľným textom respondentov – riziko osobných údajov vo voľných odpovediach.",
    "e96386be": "Surové odpovede dotazníka (Sad Janka Kráľa) s voľným textom respondentov – riziko osobných údajov vo voľných odpovediach.",
    "389b1498": "Surové odpovede dotazníka (Trhovisko Miletičova) s voľným textom respondentov – riziko osobných údajov vo voľných odpovediach.",
    "9eae31bf": "Surové odpovede dotazníka (Vrančovičova) s voľným textom respondentov – riziko osobných údajov vo voľných odpovediach.",
}

# Stĺpce, ktoré sa nikdy nezverejnia (osobné a kontaktné údaje fyzických osôb, interné identifikátory)
STLPCE_VZDY_PREC = r"^(objectid\d*|fid|oid|shape__area|shape__length|globalid|karta)$"
# Pri týchto datasetoch ide o zoznamy osôb vo verejnej funkcii – meno a funkcia ostávajú, kontakty a bydlisko nie
STLPCE_PREC = {
    "b440d389": ["Telefónny_kontakt", "Emailový_kontakt"],
    "9428dac0": ["Telefónny_kontakt", "Emailový_kontakt"],
    "52716173": ["PSČ", "Mesto", "Ulica", "E_mail", "Telefónne_číslo"],
    "dc4cfc3b": [],
    "0b7b1704": ["KONTAKT"],  # kontaktná osoba organizácie
    # staré zmluvy magistrátu: Meno/Priezvisko/Funkcia = zamestnanec mesta; adresa dodávateľa môže byť bydlisko živnostníka
    "e5913475": ["Meno", "Priezvisko", "Funkcia", "Ulica", "PSČ", "Miesto"],
    "3a6d0c8a": ["Meno", "Priezvisko", "Funkcia", "Ulica", "PSČ", "Miesto"],
    # register sociálnych služieb BSK: mená štatutárov a zodpovedných zástupcov
    "46175339": ["Meno_a_priezvisko_štatutárneho_", "Meno_a_priezvisko_zodpovedného_"],
}
# Riadky, ktoré sa vynechajú (fyzické osoby): dataset -> (stĺpec, pravidlo)
#   "ico" = vynechať riadky bez IČO;  "pravnicka" = vynechať, ak názov vyzerá ako meno a priezvisko osoby
RIADKY_PREC = {
    "e5913475": ("IČO", "ico"), "3a6d0c8a": ("IČO", "ico"),
    "46175339": ("Poskytovateľ", "pravnicka"),
}
# Všeobecný import: tieto názvy stĺpcov sa vyhodia vždy, keď nejde o organizáciu (telefón/e-mail osoby)
STLPCE_KONTAKT = r"(telef|mail|mobil)"
DATASETY_S_KONTAKTMI_ORGANIZACII = {"49ce2adc", "dc09aeac", "29546b1d", "5242099b", "226e7387"}  # linky pomoci, terénne služby, úradné hodiny – kontakty organizácií
MAX_RIADKOV = 20000
