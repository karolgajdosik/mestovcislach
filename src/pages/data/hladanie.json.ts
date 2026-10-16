// Index pre fulltextové vyhľadávanie v hlavičke (načíta sa až pri prvom otvorení vyhľadávania).
// Položka: [skupina, názov, popis, odkaz, kľúčové slová?]; pri miestach [skupina, názov, popis, '', kategória, lat, lon]
// a pri uliciach [skupina, ulica, mestská časť] – odkazy na mapu a spádovú školu skladá prehliadač (menší súbor).
import fs from 'node:fs';
import path from 'node:path';
import { maMapu, maSamospravu } from '../../lib/mapa';

const nacitaj = (subor: string, verejne = false) => {
  const p = path.join(process.cwd(), verejne ? 'public/data' : 'data', subor);
  return fs.existsSync(p) ? JSON.parse(fs.readFileSync(p, 'utf-8')) : null;
};

// Stránky a ich sekcie (odkaz, názov, popis, kľúčové slová)
const SEKCIE: [string, string, string, string][] = [
  ['/bratislava', 'Prehľad', 'Dnes v Bratislave, obyvatelia, rozcestník', 'úvod domov dnes'],
  ['/bratislava#dnes', 'Dnes v Bratislave', 'výstrahy, ovzdušie, Dunaj, uzávierky', 'výstraha búrka počasie dnes'],
  ['/bratislava/vystavba', 'Výstavba a bývanie', 'čo sa stavia, ceny bytov, nové byty', 'výstavba stavba developer projekt eia bývanie byty'],
  ['/bratislava/vystavba#co-sa-stavia', 'Čo sa stavia', 'zámery v posudzovaní EIA/SEA na mape', 'stavba zámer eia sea developer posudzovanie polyfunkčný rezidencia'],
  ['/bratislava/vystavba#ceny', 'Ceny bytov', 'index cien bývania v Bratislavskom kraji', 'cena byt nehnuteľnosť m2 hypotéka drahé'],
  ['/bratislava/vystavba#nove-byty', 'Koľko bytov pribúda', 'dokončené a začaté byty podľa okresov', 'nové byty dokončené výstavba bytov'],
  ['/bratislava/vystavba#mestske-byty', 'Mestské a nájomné byty', 'byty mesta, komunitné bývanie, príspevok', 'nájom nájomné byty obecné mestské komunitné'],
  ['/bratislava/upozornenia', 'Upozornenia', 'uzávierky, stavby a zmluvy vašej mestskej časti (RSS)', 'upozornenie notifikácie odber rss atom kanál novinky'],
  ['/bratislava/mestske-casti', 'Mestské časti', 'profily a porovnanie 17 častí', 'mestská časť štvrť porovnanie profil'],
  ['/bratislava/mapa', 'Mapa Bratislavy', 'všetky vrstvy na jednej mape', 'mapa vrstvy'],
  ['/bratislava/mapa#horucavy', 'Mapa horúčav', 'riziko horúčav, fontány, ochladzovacie miesta', 'teplo horúčava klíma leto'],
  ['/bratislava/mapa#klima', 'Klimatický atlas', 'riziko zmeny klímy, prívalové dažde', 'klíma zrážky dážď'],
  ['/bratislava/mapa#hustota', 'Hustota obyvateľov', 'obyvatelia na km² (sčítanie 2021)', 'hustota zaľudnenie'],
  ['/bratislava/mapa#hluk', 'Hluková mapa', 'hluk z ciest a priemyslu', 'hluk decibely'],
  ['/bratislava/mapa#sport', 'Športoviská na mape', 'ihriská, telocvične, kurty', 'šport ihrisko tenis futbal'],
  ['/bratislava/mapa#bezbarierove', 'Bezbariérové miesta', 'prístupnosť pre vozíčkarov', 'bezbariérovosť vozík'],
  ['/bratislava/mapa#podnety', 'Podnety obyvateľov na mape', 'čo ľudia hlásia magistrátu', 'podnet sťažnosť'],
  ['/bratislava/mapa#stromy', 'Vysadené stromy', 'výsadba stromov mestom', 'stromy zeleň výsadba'],
  ['/bratislava/obyvatelia', 'Obyvatelia', 'sčítanie 2021 podľa mestských častí', 'demografia vek vzdelanie národnosť náboženstvo byty domácnosti'],
  ['/bratislava/obyvatelia#prognoza', 'Prognóza obyvateľov do roku 2035', 'rast mestských častí, starnutie', 'prognóza budúcnosť rast starnutie'],
  ['/bratislava/obyvatelia#nezamestnanost', 'Nezamestnanosť', 'okresy Bratislava I–V mesačne', 'nezamestnanosť úrad práce uchádzači práca'],
  ['/bratislava/obyvatelia#index-rozvoja', 'Index regionálneho rozvoja', 'porovnanie mestských častí', 'rozvoj kvalita života'],
  ['/bratislava/volby', 'Voľby', 'parlamentné, európske, komunálne a krajské voľby', 'voľby výsledky účasť'],
  ['/bratislava/volby#komunalne', 'Komunálne voľby 2026', 'primátor, starostovia, poslanci, BSK', 'komunálne primátor starosta zastupiteľstvo župa kandidáti'],
  ['/bratislava/volby#hlasovania', 'Ako hlasovali poslanci', 'dochádzka a hlasovania mestského zastupiteľstva', 'hlasovanie poslanci dochádzka zastupiteľstvo uznesenie'],
  ['/bratislava/financie', 'Financie mesta', 'rozpočet, príjmy a výdavky', 'rozpočet peniaze príjmy výdavky dane'],
  ['/bratislava/financie#faktury', 'Faktúry, objednávky a zmluvy', 'magistrát, OLO, Marianum, MIB', 'faktúry objednávky dodávatelia'],
  ['/bratislava/financie#zmluvy-mc', 'Zmluvy a dotácie mestských častí', 'Centrálny register zmlúv, firmy z RPO', 'zmluvy dotácie granty crz mestská časť'],
  ['/bratislava/financie#dlh', 'Dlh mesta a mestských častí', 'úvery a dlhová služba', 'dlh úver zadlženie'],
  ['/bratislava/doprava', 'Doprava', 'uzávierky, premávka, MHD, cyklo', 'doprava'],
  ['/bratislava/doprava#naozivo', 'Uzávierky a rozkopávky dnes', 'naživo z ArcGIS mesta', 'uzávierka rozkopávka porucha obchádzka'],
  ['/bratislava/doprava#premavka', 'Kedy je najväčšia premávka', 'sčítače áut, cyklistov a chodcov', 'premávka zápcha špička sčítač'],
  ['/bratislava/doprava#csd', 'Celoštátne sčítanie dopravy', 'diaľnice a cesty v Bratislave', 'diaľnica D1 D2 obchvat intenzita'],
  ['/bratislava/doprava#doprava', 'MHD', 'zastávky, linky, cestujúci', 'mhd autobus električka trolejbus dpb'],
  ['/bratislava/doprava#cyklo', 'Cyklotrasy a BAjk', 'cyklistické trasy a zdieľané bicykle', 'cyklo bicykel bajk'],
  ['/bratislava/vybavenost', 'Vybavenosť', 'školy, škôlky, zdravotníctvo, nabíjanie', 'vybavenosť lekáreň ambulancia'],
  ['/bratislava/vybavenost#spadova-skola', 'Spádová škola podľa adresy', 'do ktorej ZŠ a MŠ patrí adresa', 'spádová škola rajón obvod zápis'],
  ['/bratislava/vybavenost#socialne', 'Jasle a sociálne služby', 'zariadenia pre seniorov, jasle, útulky', 'jasle seniori domov dôchodcov opatrovateľ'],
  ['/bratislava/prostredie', 'Životné prostredie', 'ovzdušie, odpad, zeleň, príroda', 'prostredie'],
  ['/bratislava/prostredie#dunaj', 'Dunaj naživo', 'vodný stav a predpoveď SHMÚ', 'dunaj hladina povodeň'],
  ['/bratislava/prostredie#morava', 'Morava naživo', 'Devínska Nová Ves, SHMÚ', 'morava hladina povodeň'],
  ['/bratislava/prostredie#ovzdusie-teraz', 'Ovzdušie teraz', 'index kvality ovzdušia zo staníc SHMÚ', 'ovzdušie smog prach pm10'],
  ['/bratislava/prostredie#hluk', 'Hluk', 'strategické hlukové mapy', 'hluk'],
  ['/bratislava/bezpecnost', 'Bezpečnosť', 'mestská polícia, priestupky, pokuty', 'polícia priestupok pokuta kriminalita'],
  ['/bratislava/bezpecnost#podnety', 'Podnety obyvateľov', 'čo ľudia hlásia magistrátu', 'podnet sťažnosť hlásenie'],
  ['/bratislava/katalog', 'Katalóg dát', 'všetky datasety Bratislavy', 'dáta datasety tabuľky csv'],
  ['/pristupnost', 'Vyhlásenie o prístupnosti', 'čítačky obrazovky, klávesnica, slabozrakí, WCAG', 'prístupnosť bezbariérový web wcag slabozraký nevidiaci'],
  ['/sukromie', 'Ochrana súkromia', 'cookies, osobné údaje, GDPR, kontakt', 'gdpr súkromie cookies osobné údaje kontakt'],
];

// Kategórie miest, ktoré do vyhľadávania nedávame (veľa bodov s rovnakým názvom)
const BEZ_MIEST = new Set(['Debarierizované chodníky', 'Fixpointy na zber injekčných striekačiek']);

export async function GET() {
  const polozky: (string | number)[][] = [];
  // krajské mestá a porovnanie
  const mesta = JSON.parse(fs.readFileSync(path.join(process.cwd(), 'src', 'mesta.json'), 'utf-8'));
  for (const m of mesta.filter((x: any) => x.aktivne && x.slug !== 'bratislava')) {
    polozky.push(['Stránky', m.nazov, `${m.kraj} – obyvatelia, voľby, práca, bývanie, stavby`, `/${m.slug}`, `mesto krajské ${m.v}`]);
    if (maSamospravu(m.slug)) polozky.push(['Stránky', `Samospráva – ${m.nazov}`, 'zmluvy, faktúry, objednávky, hlasovania poslancov', `/${m.slug}/samosprava`, `zmluvy faktúry dodávatelia poslanci hlasovanie zastupiteľstvo ${m.v}`]);
    if (maMapu(m.slug)) polozky.push(['Stránky', `Mapa – ${m.nazov}`, 'lekárne, nemocnice, školy, zastávky, ihriská, úrady', `/${m.slug}/mapa`, `mapa ${m.v} lekáreň nemocnica škola zastávka`]);
  }
  polozky.push(['Stránky', 'Porovnanie krajských miest', 'obyvatelia, vek, vzdelanie, nezamestnanosť, voľby, byty, ceny', '/porovnanie', 'porovnanie mestá krajské rebríček']);
  for (const [u, t, s, w] of SEKCIE) polozky.push(['Stránky', t, s, u, w]);

  // Mestské časti
  const scit = nacitaj('scitanie-bratislava.json');
  const casti: string[] = scit ? Object.keys(scit.temy?.vek?.mestske_casti ?? {}) : [];
  for (const mc of (casti.length ? casti : ['Staré Mesto', 'Ružinov', 'Vrakuňa', 'Podunajské Biskupice', 'Nové Mesto', 'Rača', 'Vajnory', 'Karlova Ves', 'Dúbravka', 'Lamač', 'Devín', 'Devínska Nová Ves', 'Záhorská Bystrica', 'Petržalka', 'Jarovce', 'Rusovce', 'Čunovo']))
    polozky.push(['Mestské časti', mc, 'profil: ľudia, voľby, peniaze, školy, bezpečnosť', `/bratislava/mestske-casti/${mc.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replace(/\s+/g, '-')}`, 'mestská časť mč']);

  // Katalóg dát
  for (const d of nacitaj('katalog-stav.json')?.datasety ?? []) {
    if (d.stav === 'vynechane') continue;
    polozky.push(['Katalóg dát', d.nazov, d.kategoria ?? '', d.kde ?? `/bratislava/katalog/${d.id}`]);
  }

  // Poslanci mestského zastupiteľstva (meno a klub – verejná funkcia)
  const hl = nacitaj('hlasovania-msz.json');
  const poslanci = new Map<string, string>();
  for (const [obd, o] of Object.entries<any>(hl?.obdobia ?? {}).sort()) for (const p of o.poslanci ?? []) poslanci.set(p.meno, `poslanec/poslankyňa MsZ ${o.nazov} · ${p.klub}`);
  for (const [m, s] of poslanci) polozky.push(['Poslanci', m, s, `/bratislava/volby?poslanec=${encodeURIComponent(m)}#hlasovania`, 'poslanec poslankyňa zastupiteľstvo']);

  // Miesta (rovnaký zoznam ako pre asistenta)
  const asistent = await import('./asistent.json.ts');
  const dataAsistenta = await (await asistent.GET({} as any)).json();
  for (const m of dataAsistenta.miesta ?? []) {
    if (BEZ_MIEST.has(m.k) || !m.n) continue;
    polozky.push(['Miesta', m.n, [m.typ && m.typ !== m.k ? m.typ : null, m.a, m.c].filter(Boolean).join(' · '), '', m.k, m.lat, m.lon]);
  }

  // Ulice → spádová škola
  const raj = nacitaj('rajonizacia-bratislava.json', true);
  for (const [mc, ulice] of Object.entries<any>(raj?.ulice ?? {})) for (const u of Object.keys(ulice))
    polozky.push(['Ulice', u, mc]);

  // Firmy a organizácie – najväčší partneri mesta a mestských častí
  const firmy = new Map<string, string>();
  const zmc = nacitaj('zmluvy-mc.json');
  for (const [mc, v] of Object.entries<any>(zmc?.mestske_casti ?? {})) for (const p of v.najvacsi_partneri ?? []) if (!firmy.has(p.nazov)) firmy.set(p.nazov, `zmluvy: ${mc === 'Hlavné mesto' ? 'hlavné mesto' : mc}${p.ico ? ` · IČO ${p.ico}` : ''}|/bratislava/financie#zmluvy-mc`);
  for (const d of nacitaj('faktury-bratislava.json')?.datasety ?? []) for (const p of (d.dodavatelia_posledne_3_roky ?? []).slice(0, 25)) if (!firmy.has(p.nazov)) firmy.set(p.nazov, `${d.typ} – ${d.organizacia}${p.ico ? ` · IČO ${p.ico}` : ''}|/bratislava/financie#faktury`);
  // zámery v posudzovaní EIA (prebiehajúce a za posledné 3 roky)
  const eia = nacitaj('eia.json', true);
  const hranica = new Date(Date.now() - 3 * 365 * 864e5).toISOString().slice(0, 10);
  for (const z of eia?.zamery ?? []) {
    if (z.ukoncene && z.zmena < hranica) continue;
    polozky.push(['Čo sa stavia', z.nazov, `${z.mc.join(', ') || 'Bratislava'} · ${z.ukoncene ? 'posudzovanie skončené' : 'práve sa posudzuje'}`, `/bratislava/vystavba?stav=&q=${encodeURIComponent(z.nazov.slice(0, 40))}#co-sa-stavia`, `stavba zámer ${z.navrhovatel ?? ''}`]);
  }
  for (const [n, v] of firmy) { const [s, u] = v.split('|'); polozky.push(['Firmy a organizácie', n, s, u]); }

  return new Response(JSON.stringify({ polozky }), { headers: { 'Content-Type': 'application/json; charset=utf-8' } });
}
