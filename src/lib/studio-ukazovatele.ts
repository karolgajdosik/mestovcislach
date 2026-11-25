// Dátové štúdio – všetky ukazovatele obcí rozdelené do tematických oblastí.
// Prvých 16 kľúčov je zhodných s POLIA (ukazovatele-obci.ts), aby staré odkazy (?u=nez…) fungovali.
// Pravidlo: chýbajúci údaj = null (nie nula), okrem „počtov zariadení“, kde zdroj eviduje všetky zariadenia a
// obec, ktorá v ňom nie je, ich naozaj nemá (školy, pošty, lekári, vlaky, pamiatky, chránené územia).
// GDPR: len súhrnné čísla za obec – žiadne mená ani údaje o fyzických osobách.
import { ukazovatele } from './ukazovatele-obci';
import {
  posledne, nezamInfo, pohybInfo, obyvateliaInfo, vekInfo, historiaInfo, sodb2Info, byvanieInfo, firmyInfo, hospodarenieObce, rozpocetInfo,
  zmluvyInfo, uzemieInfo, wikiInfo, geologiaInfo, chraneneInfo, pamiatkyInfo, klimaInfo, ovzdusieInfo, odpadInfo, osmInfo, sluzbyInfo, skolyInfo,
  vlakyInfo, trasyInfo, turizmusInfo, volbyInfo, kulturaInfo,
} from './obce';

export type Pole = { k: string; n: string; j: string; d: number; z: string; p?: string };
export type Oblast = { id: string; n: string; popis: string; polia: Pole[] };

// k = kľúč, n = názov, j = jednotka, d = desatinné miesta, z = zdroj (krátko, s rokom), p = poznámka
export const OBLASTI: Oblast[] = [
  { id: 'obyvatelia', n: 'Obyvatelia', popis: 'počet, vek, narodení, sťahovanie', polia: [
    { k: 'obyv', n: 'Obyvatelia', j: '', d: 0, z: 'ŠÚ SR, 2025' },
    { k: 'z10', n: 'Zmena obyvateľov za 10 rokov', j: '%', d: 1, z: 'ŠÚ SR, 2015 – 2025' },
    { k: 'z93', n: 'Zmena obyvateľov od roku 1993', j: '%', d: 1, z: 'ŠÚ SR, 1993 – 2025' },
    { k: 'hus', n: 'Hustota obyvateľov', j: 'na km²', d: 0, z: 'ŠÚ SR, 2025' },
    { k: 'vek', n: 'Priemerný vek', j: 'r.', d: 1, z: 'ŠÚ SR, 2025' },
    { k: 'vekz', n: 'Zmena priemerného veku za 10 rokov', j: 'r.', d: 1, z: 'ŠÚ SR, 2015 – 2025' },
    { k: 'star', n: 'Index starnutia', j: 'seniorov na 100 detí', d: 0, z: 'ŠÚ SR, 2025' },
    { k: 'deti', n: 'Deti do 14 rokov', j: '%', d: 1, z: 'Sčítanie 2021' },
    { k: 'sen', n: 'Ľudia nad 65 rokov', j: '%', d: 1, z: 'Sčítanie 2021' },
    { k: 'zeny', n: 'Podiel žien', j: '%', d: 1, z: 'ŠÚ SR, 2025' },
    { k: 'nar', n: 'Narodení ročne', j: 'na 1 000 obyv.', d: 1, z: 'ŠÚ SR, priemer 2021 – 2025' },
    { k: 'zom', n: 'Zomrelí ročne', j: 'na 1 000 obyv.', d: 1, z: 'ŠÚ SR, priemer 2021 – 2025' },
    { k: 'prir', n: 'Prirodzený prírastok ročne', j: 'na 1 000 obyv.', d: 1, z: 'ŠÚ SR, priemer 2021 – 2025' },
    { k: 'mig', n: 'Saldo sťahovania ročne', j: 'na 1 000 obyv.', d: 1, z: 'ŠÚ SR, priemer 2021 – 2025' },
    { k: 'cudz', n: 'Cudzí štátni príslušníci', j: '%', d: 1, z: 'Sčítanie 2021' },
  ] },
  { id: 'spolocnost', n: 'Vzdelanie a spoločnosť', popis: 'vzdelanie, národnosť, viera, domácnosti', polia: [
    { k: 'vs', n: 'Vysokoškolské vzdelanie', j: '%', d: 1, z: 'Sčítanie 2021' },
    { k: 'sm', n: 'Stredoškolské s maturitou', j: '%', d: 1, z: 'Sčítanie 2021', p: 'ľudia od 15 rokov' },
    { k: 'sbm', n: 'Stredoškolské bez maturity', j: '%', d: 1, z: 'Sčítanie 2021', p: 'ľudia od 15 rokov' },
    { k: 'zakl', n: 'Len základné vzdelanie', j: '%', d: 1, z: 'Sčítanie 2021', p: 'ľudia od 15 rokov' },
    { k: 'narsk', n: 'Slovenská národnosť', j: '%', d: 1, z: 'Sčítanie 2021' },
    { k: 'narine', n: 'Iná ako slovenská národnosť', j: '%', d: 1, z: 'Sčítanie 2021', p: 'vrátane nezistenej' },
    { k: 'rkc', n: 'Rímskokatolícke vyznanie', j: '%', d: 1, z: 'Sčítanie 2021' },
    { k: 'bezv', n: 'Bez náboženského vyznania', j: '%', d: 1, z: 'Sčítanie 2021' },
    { k: 'dom', n: 'Priemerná veľkosť domácnosti', j: 'osôb', d: 2, z: 'Sčítanie 2021' },
    { k: 'jedn', n: 'Jednočlenné domácnosti', j: '%', d: 1, z: 'Sčítanie 2021' },
    { k: 'domd', n: 'Domácnosti s deťmi', j: '%', d: 1, z: 'Sčítanie 2021' },
  ] },
  { id: 'praca', n: 'Práca a podnikanie', popis: 'nezamestnanosť, firmy, živnostníci', polia: [
    { k: 'nez', n: 'Miera nezamestnanosti', j: '%', d: 1, z: 'ÚPSVaR, október 2026' },
    { k: 'nezr', n: 'Zmena nezamestnanosti za rok', j: 'p. b.', d: 1, z: 'ÚPSVaR, október 2025 → október 2026' },
    { k: 'uoz', n: 'Uchádzači o zamestnanie', j: '', d: 0, z: 'ÚPSVaR, október 2026' },
    { k: 'akt', n: 'Ekonomicky aktívni', j: '%', d: 1, z: 'Sčítanie 2021' },
    { k: 'doch', n: 'Dôchodcovia', j: '%', d: 1, z: 'Sčítanie 2021' },
    { k: 'firmy', n: 'Firmy (ziskové právnické osoby)', j: 'na 1 000 obyv.', d: 1, z: 'ŠÚ SR, 2025' },
    { k: 'zivn', n: 'Živnostníci', j: 'na 1 000 obyv.', d: 1, z: 'ŠÚ SR, 2025' },
    { k: 'nezisk', n: 'Neziskové organizácie', j: 'na 1 000 obyv.', d: 1, z: 'ŠÚ SR, 2025' },
    { k: 'firmyz', n: 'Zmena počtu firiem za 10 rokov', j: '%', d: 0, z: 'ŠÚ SR, 2015 – 2025', p: 'len obce s aspoň 5 firmami v roku 2015' },
  ] },
  { id: 'financie', n: 'Peniaze obce', popis: 'rozpočet, majetok, dlhy, zmluvy', polia: [
    { k: 'vyd', n: 'Výdavky obce na obyvateľa', j: '€', d: 0, z: 'MF SR, 2025' },
    { k: 'inv', n: 'Investície obce na obyvateľa', j: '€', d: 0, z: 'MF SR, 2025' },
    { k: 'invp', n: 'Podiel investícií vo výdavkoch', j: '%', d: 1, z: 'MF SR, 2025' },
    { k: 'mzdy', n: 'Mzdy zamestnancov obce na obyvateľa', j: '€', d: 0, z: 'MF SR, 2025' },
    { k: 'dan', n: 'Daňové príjmy na obyvateľa', j: '€', d: 0, z: 'Register účtovných závierok, posledný rok' },
    { k: 'trans', n: 'Prijaté dotácie a transfery na obyvateľa', j: '€', d: 0, z: 'Register účtovných závierok, posledný rok' },
    { k: 'vysl', n: 'Hospodársky výsledok na obyvateľa', j: '€', d: 0, z: 'Register účtovných závierok, posledný rok' },
    { k: 'maj', n: 'Majetok obce na obyvateľa', j: '€', d: 0, z: 'Register účtovných závierok, posledný rok' },
    { k: 'zav', n: 'Záväzky obce na obyvateľa', j: '€', d: 0, z: 'Register účtovných závierok, posledný rok' },
    { k: 'uver', n: 'Bankové úvery na obyvateľa', j: '€', d: 0, z: 'Register účtovných závierok, posledný rok' },
    { k: 'hot', n: 'Peniaze na účtoch na obyvateľa', j: '€', d: 0, z: 'Register účtovných závierok, posledný rok' },
    { k: 'zml', n: 'Zverejnené zmluvy za rok', j: '', d: 0, z: 'CRZ, 2025' },
    { k: 'zmlo', n: 'Objem zmlúv na obyvateľa', j: '€', d: 0, z: 'CRZ, 2025' },
    { k: 'nfp', n: 'Eurofondy a dotácie (NFP) na obyvateľa', j: '€', d: 0, z: 'CRZ, od 2025' },
  ] },
  { id: 'byvanie', n: 'Bývanie', popis: 'byty, kanalizácia, plyn, kúrenie', polia: [
    { k: 'byty', n: 'Byty na 1 000 obyvateľov', j: '', d: 0, z: 'Sčítanie 2021' },
    { k: 'm2', n: 'Priemerná plocha bytu', j: 'm²', d: 0, z: 'Sčítanie 2021' },
    { k: 'izby', n: 'Priemerný počet izieb', j: '', d: 1, z: 'Sčítanie 2021' },
    { k: 'vlast', n: 'Byty vo vlastníctve', j: '%', d: 1, z: 'Sčítanie 2021' },
    { k: 'najom', n: 'Nájomné byty', j: '%', d: 1, z: 'Sčítanie 2021' },
    { k: 'nove', n: 'Domy postavené od roku 2001', j: '%', d: 1, z: 'Sčítanie 2021' },
    { k: 'stare', n: 'Domy postavené do roku 1945', j: '%', d: 1, z: 'Sčítanie 2021' },
    { k: 'kanal', n: 'Napojenie na kanalizáciu', j: '%', d: 1, z: 'Sčítanie 2021' },
    { k: 'zumpa', n: 'Žumpa', j: '%', d: 1, z: 'Sčítanie 2021' },
    { k: 'vodovod', n: 'Verejný vodovod', j: '%', d: 1, z: 'Sčítanie 2021' },
    { k: 'plyn', n: 'Plyn v dome', j: '%', d: 1, z: 'Sčítanie 2021' },
    { k: 'teplaren', n: 'Diaľkové kúrenie (tepláreň)', j: '%', d: 1, z: 'Sčítanie 2021' },
    { k: 'pevne', n: 'Kúrenie drevom, uhlím a pevným palivom', j: '%', d: 1, z: 'Sčítanie 2021' },
    { k: 'voda', n: 'Spotreba pitnej vody', j: 'l na osobu a deň', d: 0, z: 'ŠÚ SR, 2025' },
  ] },
  { id: 'vybavenost', n: 'Služby a vybavenosť', popis: 'školy, lekári, obchody, doprava', polia: [
    { k: 'ms', n: 'Materské školy', j: '', d: 0, z: 'MŠVVaM SR, 2026/27', p: 'vrátane spojených škôl „ZŠ s MŠ“' },
    { k: 'zs', n: 'Základné školy', j: '', d: 0, z: 'MŠVVaM SR, 2026/27' },
    { k: 'ziaci', n: 'Žiaci základných škôl', j: '', d: 0, z: 'MŠVVaM SR, 2026/27' },
    { k: 'ss', n: 'Stredné školy', j: '', d: 0, z: 'MŠVVaM SR, 2026/27' },
    { k: 'vseob', n: 'Ambulancie všeobecných lekárov', j: '', d: 0, z: 'ŠÚ SR, 2024' },
    { k: 'zubar', n: 'Zubné ambulancie', j: '', d: 0, z: 'ŠÚ SR, 2024' },
    { k: 'lekarne', n: 'Lekárne', j: '', d: 0, z: 'ŠÚ SR, 2024' },
    { k: 'posta', n: 'Pošty', j: '', d: 0, z: 'ŠÚ SR, 2025' },
    { k: 'potr', n: 'Potraviny a obchody', j: '', d: 0, z: 'OpenStreetMap, 2026' },
    { k: 'jedlo', n: 'Reštaurácie, kaviarne a bufety', j: '', d: 0, z: 'OpenStreetMap, 2026' },
    { k: 'ihr', n: 'Detské ihriská', j: '', d: 0, z: 'OpenStreetMap, 2026' },
    { k: 'sport', n: 'Športoviská', j: '', d: 0, z: 'OpenStreetMap, 2026' },
    { k: 'zast', n: 'Zastávky verejnej dopravy', j: '', d: 0, z: 'OpenStreetMap, 2026' },
    { k: 'bankom', n: 'Bankomaty', j: '', d: 0, z: 'OpenStreetMap, 2026' },
    { k: 'nabij', n: 'Nabíjačky elektromobilov', j: '', d: 0, z: 'OpenStreetMap, 2026' },
    { k: 'vlaky', n: 'Vlaky v pracovný deň', j: '', d: 0, z: 'ŽSR, november 2026', p: 'najvyťaženejšia stanica v obci' },
    { k: 'cyklo', n: 'Cyklotrasy', j: 'km', d: 1, z: 'OpenStreetMap, 2026' },
    { k: 'turist', n: 'Turistické trasy', j: 'km', d: 1, z: 'OpenStreetMap, 2026' },
  ] },
  { id: 'uzemie', n: 'Územie a príroda', popis: 'rozloha, lesy, pôda, výška, pamiatky', polia: [
    { k: 'rozl', n: 'Rozloha katastra', j: 'km²', d: 1, z: 'ÚGKK SR, 2025' },
    { k: 'vys', n: 'Nadmorská výška', j: 'm', d: 0, z: 'Wikidata' },
    { k: 'les', n: 'Lesy', j: '%', d: 1, z: 'ÚGKK SR, 2025' },
    { k: 'orna', n: 'Orná pôda', j: '%', d: 1, z: 'ÚGKK SR, 2025' },
    { k: 'ttp', n: 'Lúky a pasienky', j: '%', d: 1, z: 'ÚGKK SR, 2025' },
    { k: 'vin', n: 'Vinice', j: '%', d: 1, z: 'ÚGKK SR, 2025' },
    { k: 'vodp', n: 'Vodné plochy', j: '%', d: 1, z: 'ÚGKK SR, 2025' },
    { k: 'zastp', n: 'Zastavané plochy', j: '%', d: 1, z: 'ÚGKK SR, 2025' },
    { k: 'zastr', n: 'Rast zastavaných plôch od 2015', j: '%', d: 1, z: 'ÚGKK SR, 2015 – 2025' },
    { k: 'chran', n: 'Chránené územia (európske a maloplošné)', j: '', d: 0, z: 'ŠOP SR' },
    { k: 'zosuv', n: 'Zosuvy pôdy', j: '', d: 0, z: 'ŠGÚDŠ' },
    { k: 'pam', n: 'Pamiatkové objekty', j: '', d: 0, z: 'Wikidata / Pamiatkový úrad SR' },
    { k: 'zmienka', n: 'Prvá písomná zmienka', j: 'rok', d: 0, z: 'Wikidata' },
  ] },
  { id: 'klima', n: 'Klíma a ovzdušie', popis: 'teplota, zrážky, mrazy, prach', polia: [
    { k: 'tep', n: 'Priemerná teplota', j: '°C', d: 1, z: 'Open-Meteo (ERA5), 2016 – 2025' },
    { k: 'zr', n: 'Zrážky za rok', j: 'mm', d: 0, z: 'Open-Meteo (ERA5), 2016 – 2025' },
    { k: 'mraz', n: 'Mrazové dni za rok', j: 'dní', d: 0, z: 'Open-Meteo (ERA5), 2016 – 2025' },
    { k: 'leto', n: 'Letné dni (od 25 °C)', j: 'dní', d: 0, z: 'Open-Meteo (ERA5), 2016 – 2025' },
    { k: 'trop', n: 'Tropické dni (od 30 °C)', j: 'dní', d: 1, z: 'Open-Meteo (ERA5), 2016 – 2025' },
    { k: 'snez', n: 'Dni so snehovou pokrývkou', j: 'dní', d: 0, z: 'Open-Meteo (ERA5), 2016 – 2025' },
    { k: 'pm10', n: 'Prach PM10 (najbližšia stanica)', j: 'µg/m³', d: 1, z: 'SHMÚ, 2025', p: 'len obce do 15 km od stanice' },
    { k: 'pm25', n: 'Jemný prach PM2,5 (najbližšia stanica)', j: 'µg/m³', d: 1, z: 'SHMÚ, 2025', p: 'len obce do 15 km od stanice' },
    { k: 'no2', n: 'Oxid dusičitý NO₂ (najbližšia stanica)', j: 'µg/m³', d: 1, z: 'SHMÚ, 2025', p: 'len obce do 15 km od stanice' },
  ] },
  { id: 'odpad', n: 'Odpad', popis: 'triedenie, množstvo, bioodpad', polia: [
    { k: 'tri', n: 'Vytriedený komunálny odpad', j: '%', d: 0, z: 'ŠÚ SR, 2025' },
    { k: 'kg', n: 'Komunálny odpad na obyvateľa', j: 'kg', d: 0, z: 'ŠÚ SR, 2025' },
    { k: 'kgz', n: 'Zmesový odpad na obyvateľa', j: 'kg', d: 0, z: 'ŠÚ SR, 2025' },
    { k: 'bio', n: 'Bioodpad v komunálnom odpade', j: '%', d: 1, z: 'ŠÚ SR, 2025' },
    { k: 'triz', n: 'Zmena triedenia od 2021', j: 'p. b.', d: 1, z: 'ŠÚ SR, 2021 – 2025' },
  ] },
  { id: 'volby', n: 'Voľby', popis: 'účasť v jednotlivých voľbách', polia: [
    { k: 'uc', n: 'Účasť v komunálnych voľbách 2026', j: '%', d: 1, z: 'ŠÚ SR, 2026' },
    { k: 'uc22', n: 'Účasť v komunálnych voľbách 2022', j: '%', d: 1, z: 'ŠÚ SR, 2022' },
    { k: 'ucn23', n: 'Účasť v parlamentných voľbách 2023', j: '%', d: 1, z: 'ŠÚ SR, 2023' },
    { k: 'ucn20', n: 'Účasť v parlamentných voľbách 2020', j: '%', d: 1, z: 'ŠÚ SR, 2020' },
    { k: 'ucp24', n: 'Účasť v prezidentských voľbách 2024 (2. kolo)', j: '%', d: 1, z: 'ŠÚ SR, 2024' },
    { k: 'ucep24', n: 'Účasť vo voľbách do Európskeho parlamentu 2024', j: '%', d: 1, z: 'ŠÚ SR, 2024' },
    { k: 'ucr23', n: 'Účasť v referende 2023', j: '%', d: 1, z: 'ŠÚ SR, 2023' },
    { k: 'kand', n: 'Kandidáti na starostu 2026', j: '', d: 0, z: 'ŠÚ SR, 2026' },
  ] },
  { id: 'turizmus', n: 'Cestovný ruch', popis: 'ubytovanie, lôžka, vyťaženosť', polia: [
    { k: 'lozka', n: 'Lôžka v ubytovacích zariadeniach', j: '', d: 0, z: 'ŠÚ SR, posledný rok', p: 'len obce, za ktoré ŠÚ SR údaje zverejňuje' },
    { k: 'lozkap', n: 'Lôžka na 1 000 obyvateľov', j: '', d: 0, z: 'ŠÚ SR, posledný rok', p: 'len obce, za ktoré ŠÚ SR údaje zverejňuje' },
    { k: 'ubyt', n: 'Ubytovacie zariadenia', j: '', d: 0, z: 'ŠÚ SR, posledný rok', p: 'len obce, za ktoré ŠÚ SR údaje zverejňuje' },
    { k: 'vyuz', n: 'Využitie lôžok', j: '%', d: 1, z: 'ŠÚ SR, posledný rok', p: 'len obce, za ktoré ŠÚ SR údaje zverejňuje' },
  ] },
];

export const VSETKY_POLIA: Pole[] = OBLASTI.flatMap((o) => o.polia);

const num = (x: unknown): number | null => (typeof x === 'number' && Number.isFinite(x) ? x : null);
const r = (x: number | null | undefined, d = 1) => (x == null || !Number.isFinite(x) ? null : Math.round(x * 10 ** d) / 10 ** d);
const naObyv = (x: unknown, ob: number | null, k = 1) => { const v = num(x); return v != null && ob ? (v / ob) * k : null; };
const posl = <T,>(o: Record<string, T> | undefined | null): T | null => { if (!o) return null; const k = Object.keys(o).sort(); return k.length ? o[k[k.length - 1]] : null; };
const podiel = (zoz: [string, number][] | undefined, f: (n: string) => boolean) => { if (!zoz) return null; const t = zoz.find(([n]) => f(n)); return t ? t[1] : null; };

export type RiadokStudia = { kod: string; n: string; okres: string; kraj: string; url: string; lat: number | null; lon: number | null; h: Record<string, number | null> };
let CACHE: RiadokStudia[] | null = null;

export function riadkyStudia(): RiadokStudia[] {
  if (CACHE) return CACHE;
  const nez = nezamInfo()?.obce ?? {}, poh = pohybInfo()?.obce ?? {}, oby = obyvateliaInfo()?.obce ?? {}, vek = vekInfo()?.obce ?? {}, his = historiaInfo()?.obce ?? {};
  const so2 = sodb2Info()?.obce ?? {}, byv = byvanieInfo()?.obce ?? {}, fir = firmyInfo()?.obce ?? {}, roz = rozpocetInfo()?.obce ?? {}, zml = zmluvyInfo()?.obce ?? {};
  const uz = uzemieInfo()?.obce ?? {}, wk = wikiInfo()?.obce ?? {}, geo = geologiaInfo()?.obce ?? {}, chr = chraneneInfo()?.obce ?? {}, pam = pamiatkyInfo()?.obce ?? {};
  const kli = klimaInfo()?.obce ?? {}, ovz = ovzdusieInfo()?.obce ?? {}, odp = odpadInfo()?.obce ?? {}, osmI = osmInfo(), osm = osmI?.obce ?? {}, slu = sluzbyInfo()?.obce ?? {};
  const sk = skolyInfo()?.obce ?? {}, vla = vlakyInfo()?.obce ?? {}, tra = trasyInfo()?.obce ?? {}, tur = turizmusInfo()?.obce ?? {}, vol = volbyInfo(), kul = kulturaInfo();
  const OSM = (osmI?.kategorie ?? []) as string[];
  const osmI_ = (kat: string) => OSM.indexOf(kat);
  const maSluzby = Object.keys(slu).length > 0, maSkoly = Object.keys(sk).length > 0, maVlaky = Object.keys(vla).length > 0;

  CACHE = ukazovatele().map(({ o, kraj, url, h: z }) => {
    const k = o.kod, ob = z.obyv;
    const h: Record<string, number | null> = { ...z };
    // obyvatelia
    const hs = his[k] as number[] | undefined;
    h.z93 = hs && hs.length > 1 && hs[0] ? r((100 * (hs[hs.length - 1] - hs[0])) / hs[0]) : null;
    const p = poh[k];
    h.vekz = p?.vek != null && p?.vek10 != null ? r(p.vek - p.vek10) : null;
    h.star = num(p?.starnutie);
    const v = vek[k];
    if (v?.m && v?.z) { const m = v.m.reduce((a: number, b: number) => a + b, 0), zz = v.z.reduce((a: number, b: number) => a + b, 0); h.zeny = m + zz ? r((100 * zz) / (m + zz)) : null; }
    const rad = p?.rad ? Object.keys(p.rad).sort().slice(-5).map((y) => p.rad[y] as [number, number, number]) : [];
    if (rad.length && ob) {
      const s = rad.reduce((a, x) => [a[0] + x[0], a[1] + x[1], a[2] + x[2]], [0, 0, 0]).map((x) => (x / rad.length / ob) * 1000);
      h.nar = r(s[0]); h.zom = r(s[1]); h.prir = r(s[0] - s[1]); h.mig = r(s[2]);
    }
    const s2 = so2[k];
    h.cudz = num(s2?.cudzinci?.[1]);
    // spoločnosť
    const ob2 = oby[k];
    h.sm = num(ob2?.vzd?.sm); h.sbm = num(ob2?.vzd?.sbm); h.zakl = num(ob2?.vzd?.zakl);
    const sl = podiel(ob2?.nar, (n) => n === 'Slovenská');
    h.narsk = ob2?.nar ? (sl ?? 0) : null; h.narine = h.narsk != null ? r(100 - h.narsk) : null;
    h.rkc = podiel(ob2?.nab, (n) => n === 'rímskokatolícke'); h.bezv = podiel(ob2?.nab, (n) => n === 'bez náboženského vyznania');
    h.dom = num(s2?.dom?.priem); h.jedn = num(s2?.dom?.jedn); h.domd = num(s2?.dom?.deti);
    // práca
    const nz = nez[k];
    const nr = nz?.rad ? Object.keys(nz.rad).sort() : [];
    if (nr.length >= 13) { const a = nz.rad[nr[nr.length - 1]], b = nz.rad[nr[nr.length - 13]]; h.nezr = a != null && b != null ? r(a - b) : null; } else h.nezr = null;
    h.uoz = num(nz?.uoz);
    h.akt = num(s2?.ekon?.aktivni); h.doch = num(s2?.ekon?.dochodcovia);
    const f = fir[k]; const fp = posl<number[]>(f);
    h.firmy = r(naObyv(fp?.[0], ob, 1000)); h.nezisk = r(naObyv(fp?.[1], ob, 1000)); h.zivn = r(naObyv(fp?.[2], ob, 1000));
    const f15 = f?.['2015'];
    h.firmyz = f15 && fp && f15[0] >= 5 ? r((100 * (fp[0] - f15[0])) / f15[0], 0) : null;
    // peniaze
    const rz = roz[k]?.vy as Record<string, number> | undefined;
    const vydS = rz ? Object.values(rz).reduce((a, b) => a + b, 0) : 0;
    h.invp = rz && vydS ? r((100 * (rz.investicie ?? 0)) / vydS) : null;
    h.mzdy = r(naObyv(rz?.mzdy, ob), 0);
    const hos = hospodarenieObce(k); const hp = posl(hos ?? undefined) as Record<string, number> | null;
    h.dan = r(naObyv(hp?.danove_vynosy, ob), 0); h.trans = r(naObyv(hp?.transfery_prijate, ob), 0); h.vysl = r(naObyv(hp?.vysledok, ob), 0);
    h.maj = r(naObyv(hp?.majetok, ob), 0); h.zav = r(naObyv(hp?.zavazky, ob), 0); h.uver = r(naObyv(hp?.bankove_uvery, ob), 0); h.hot = r(naObyv(hp?.financne_ucty, ob), 0);
    const zm = zml[k];
    h.zml = zm ? (zm.roky?.['2025']?.[0] ?? 0) : null; h.zmlo = zm ? r(naObyv(zm.roky?.['2025']?.[1] ?? 0, ob), 0) : null;
    h.nfp = zm ? r(naObyv(zm.nfp?.[1] ?? 0, ob), 0) : null;
    // bývanie
    const b = byv[k];
    h.byty = r(naObyv(b?.bytov, ob, 1000), 0); h.m2 = num(s2?.byty?.m2); h.izby = num(s2?.byty?.izby); h.vlast = num(s2?.byty?.vlastne); h.najom = num(s2?.byty?.najom);
    h.nove = b?.vek_domov ? r(b.vek_domov[3] + b.vek_domov[4]) : null; h.stare = num(b?.vek_domov?.[0]);
    h.kanal = num(b?.kanal); h.zumpa = num(b?.zumpa); h.vodovod = num(b?.vodovod); h.plyn = num(b?.plyn);
    h.teplaren = num(b?.kurenie?.[0]); h.pevne = num(s2?.byty?.energia?.pevne);
    const vd = kul?.voda?.[k]; const vl = vd != null && ob ? Math.round((vd * 1e6) / 365 / ob) : null;
    h.voda = vl != null && vl > 20 && vl < 400 ? vl : null;
    // vybavenosť
    const skT = sk[k]?.typy ?? {};
    h.ms = maSkoly ? (skT.ms?.[0] ?? 0) + ((sk[k]?.zoznam ?? []) as [string, string][]).filter(([n, t]) => t === 'zs' && /s MŠ/.test(n)).length : null; h.zs = maSkoly ? (skT.zs?.[0] ?? 0) : null; h.ziaci = maSkoly ? (skT.zs?.[1] ?? 0) : null; h.ss = maSkoly ? (skT.ss?.[0] ?? 0) : null;
    const zd = slu[k]?.zdravie ?? {};
    h.vseob = maSluzby ? (zd.vseob ?? 0) : null; h.zubar = maSluzby ? (zd.zubar ?? 0) : null; h.lekarne = maSluzby ? (zd.lekarne ?? 0) : null; h.posta = maSluzby ? (slu[k]?.posta ?? 0) : null;
    const os = osm[k] as number[] | undefined;
    const oc = (kat: string) => (os && osmI_(kat) >= 0 ? num(os[osmI_(kat)]) : null);
    h.potr = oc('potraviny'); h.jedlo = oc('jedlo'); h.ihr = oc('ihriska'); h.sport = oc('sport'); h.zast = oc('zastavky'); h.bankom = oc('bankomaty'); h.nabij = oc('nabijacky');
    h.vlaky = maVlaky ? (vla[k]?.[0]?.[1] ?? 0) : null;
    h.cyklo = num(tra[k]?.[0]) ?? (Object.keys(tra).length ? 0 : null); h.turist = num(tra[k]?.[1]) ?? (Object.keys(tra).length ? 0 : null);
    // územie
    const u = uz[k];
    h.rozl = u?.ha ? r(u.ha / 100, 2) : null;
    h.les = u ? (u.p?.les ?? 0) : null; h.orna = u ? (u.p?.orna ?? 0) : null; h.ttp = u ? (u.p?.ttp ?? 0) : null; h.vin = u ? (u.p?.vin ?? 0) : null;
    h.vodp = u ? (u.p?.voda ?? 0) : null; h.zastp = u ? (u.p?.zast ?? 0) : null;
    h.zastr = u?.zast && u.zast[1] ? r((100 * (u.zast[2] - u.zast[1])) / u.zast[1]) : null;
    const ch = chr[k]; h.chran = (ch?.uev?.length ?? 0) + (ch?.mchu?.length ?? 0);
    h.zosuv = geo[k] ? (geo[k].n ?? 0) : null;
    h.pam = pam[k]?.n ?? 0;
    h.zmienka = num(wk[k]?.[0]);
    // klíma, ovzdušie
    const kl = kli[k] as number[] | undefined;
    h.mraz = num(kl?.[2]); h.leto = num(kl?.[3]); h.trop = num(kl?.[4]); h.snez = num(kl?.[5]);
    h.pm25 = num(ovz[k]?.pm25?.[0]); h.no2 = num(ovz[k]?.no2?.[0]);
    // odpad
    const od = odp[k] as Record<string, { t: number; triedene: number; bio: number; kg?: number; kg_zmes?: number }> | undefined;
    const op = posl(od);
    h.kg = num(op?.kg); h.kgz = num(op?.kg_zmes); h.bio = op?.t ? r((100 * op.bio) / op.t) : null;
    h.triz = od?.['2021'] && op ? r(op.triedene - od['2021'].triedene) : null;
    // voľby
    const vo = vol?.volby ?? {}, uc = vol?.ucast ?? {};
    h.uc22 = num(uc.oso2022?.obce?.[k]); h.ucr23 = num(uc.ref2023?.obce?.[k]);
    h.ucn23 = num(vo.nrsr2023?.obce?.[k]?.[0]); h.ucn20 = num(vo.nrsr2020?.obce?.[k]?.[0]); h.ucp24 = num(vo.prez2024_2?.obce?.[k]?.[0]); h.ucep24 = num(vo.ep2024?.obce?.[k]?.[0]);
    h.kand = o.volby2026 ? num(o.volby2026.kandidatov) : null;
    // cestovný ruch
    const t = posl(tur[k]) as { lozok?: number; zariadeni?: number; vyuzitie?: number } | null;
    h.lozka = num(t?.lozok); h.lozkap = r(naObyv(t?.lozok, ob, 1000), 0); h.ubyt = num(t?.zariadeni); h.vyuz = num(t?.vyuzitie);
    return { kod: k, n: o.nazov, okres: o.okres, kraj, url, lat: o.poloha?.[0] ?? null, lon: o.poloha?.[1] ?? null, h };
  });
  return CACHE;
}

// Vysvetlivky – jedna veta ku každému ukazovateľu (zobrazí sa pod nadpisom v štúdiu a vo výbere).
export const OPISY: Record<string, string> = {
  obyv: 'Počet ľudí s trvalým pobytom v obci k 31. decembru.',
  z10: 'O koľko percent sa zmenil počet obyvateľov za posledných 10 rokov. Kladné číslo = obec rastie.',
  z93: 'Zmena počtu obyvateľov od vzniku Slovenskej republiky.',
  hus: 'Koľko obyvateľov pripadá na jeden kilometer štvorcový katastra obce.',
  vek: 'Priemerný vek všetkých obyvateľov obce.',
  vekz: 'O koľko rokov sa zvýšil (alebo znížil) priemerný vek za 10 rokov – ukazuje, ako rýchlo obec starne.',
  star: 'Počet ľudí nad 65 rokov na 100 detí do 14 rokov. Nad 100 = seniorov je viac ako detí.',
  deti: 'Podiel detí vo veku 0 – 14 rokov na všetkých obyvateľoch.',
  sen: 'Podiel ľudí vo veku 65 a viac rokov na všetkých obyvateľoch.',
  zeny: 'Podiel žien na všetkých obyvateľoch.',
  nar: 'Koľko detí sa ročne narodí na 1 000 obyvateľov (priemer 5 rokov, aby malé obce nekolísali).',
  zom: 'Koľko ľudí ročne zomrie na 1 000 obyvateľov (priemer 5 rokov).',
  prir: 'Narodení mínus zomrelí na 1 000 obyvateľov. Záporné číslo = viac úmrtí ako narodení.',
  mig: 'Prisťahovaní mínus odsťahovaní na 1 000 obyvateľov. Kladné číslo = do obce sa viac ľudí sťahuje.',
  cudz: 'Podiel obyvateľov, ktorí nemajú slovenské štátne občianstvo.',
  vs: 'Podiel ľudí s vysokoškolským vzdelaním (bakalár a vyššie) medzi obyvateľmi od 15 rokov.',
  sm: 'Podiel ľudí s úplným stredným vzdelaním s maturitou.',
  sbm: 'Podiel ľudí so stredným vzdelaním bez maturity (vyučení).',
  zakl: 'Podiel ľudí, ktorí majú len základné vzdelanie.',
  narsk: 'Podiel obyvateľov, ktorí sa pri sčítaní prihlásili k slovenskej národnosti.',
  narine: 'Podiel obyvateľov s inou ako slovenskou národnosťou (maďarská, rómska, česká… aj nezistená).',
  rkc: 'Podiel obyvateľov, ktorí sa prihlásili k Rímskokatolíckej cirkvi.',
  bezv: 'Podiel obyvateľov bez náboženského vyznania.',
  dom: 'Koľko ľudí v priemere žije v jednej domácnosti.',
  jedn: 'Podiel domácností, v ktorých žije jeden človek.',
  domd: 'Podiel domácností, v ktorých žijú nezaopatrené deti.',
  nez: 'Podiel evidovaných nezamestnaných na ekonomicky aktívnych obyvateľoch (podľa ÚPSVaR).',
  nezr: 'O koľko percentuálnych bodov sa zmenila nezamestnanosť za posledný rok. Záporné číslo = zlepšenie.',
  uoz: 'Počet ľudí evidovaných na úrade práce ako uchádzači o zamestnanie.',
  akt: 'Podiel obyvateľov, ktorí pracujú alebo si prácu hľadajú.',
  doch: 'Podiel obyvateľov, ktorí poberajú starobný alebo invalidný dôchodok a nepracujú.',
  firmy: 'Počet obchodných spoločností (s. r. o., a. s. …) so sídlom v obci na 1 000 obyvateľov.',
  zivn: 'Počet živnostníkov (SZČO) so sídlom v obci na 1 000 obyvateľov.',
  nezisk: 'Počet občianskych združení, nadácií a iných neziskových organizácií na 1 000 obyvateľov.',
  firmyz: 'O koľko percent sa zmenil počet firiem so sídlom v obci za 10 rokov.',
  vyd: 'Všetky výdavky obce za rok (mzdy, služby, investície, splátky…) v prepočte na jedného obyvateľa.',
  inv: 'Koľko obec za rok preinvestovala (stavby, rekonštrukcie, nákup majetku) na jedného obyvateľa.',
  invp: 'Aká časť výdavkov obce išla na investície. Vyššie číslo = obec viac buduje.',
  mzdy: 'Mzdy a odvody zamestnancov obce (úrad, škôlky, školy) na jedného obyvateľa.',
  dan: 'Príjmy obce z daní – najmä podielová daň od štátu a daň z nehnuteľností – na obyvateľa.',
  trans: 'Peniaze, ktoré obec dostala od štátu, VÚC či z EÚ (dotácie, transfery) na obyvateľa.',
  vysl: 'Výnosy mínus náklady obce za rok na obyvateľa. Záporné číslo = obec hospodárila so stratou.',
  maj: 'Hodnota všetkého majetku obce (budovy, cesty, pozemky, peniaze) na obyvateľa.',
  zav: 'Všetky dlhy a nezaplatené záväzky obce (úvery, faktúry…) na obyvateľa.',
  uver: 'Nesplatené bankové úvery obce na obyvateľa.',
  hot: 'Peniaze, ktoré má obec na bankových účtoch a v pokladni, na obyvateľa.',
  zml: 'Počet zmlúv, ktoré obec zverejnila v Centrálnom registri zmlúv za rok.',
  zmlo: 'Súčet hodnôt zverejnených zmlúv obce za rok na obyvateľa.',
  nfp: 'Hodnota zmlúv o nenávratnom finančnom príspevku (eurofondy, štátne dotácie) na obyvateľa.',
  byty: 'Počet bytov a rodinných domov na 1 000 obyvateľov.',
  m2: 'Priemerná obytná plocha jedného bytu alebo domu.',
  izby: 'Priemerný počet obytných miestností v byte alebo dome.',
  vlast: 'Podiel bytov a domov, ktoré obyvatelia vlastnia.',
  najom: 'Podiel bytov a domov, v ktorých ľudia bývajú v nájme.',
  nove: 'Podiel obývaných domov postavených v roku 2001 a neskôr.',
  stare: 'Podiel obývaných domov postavených do roku 1945.',
  kanal: 'Podiel bytov a domov napojených na verejnú kanalizáciu.',
  zumpa: 'Podiel bytov a domov, ktoré majú žumpu alebo septik.',
  vodovod: 'Podiel bytov a domov napojených na verejný vodovod.',
  plyn: 'Podiel bytov a domov s prípojkou plynu.',
  teplaren: 'Podiel bytov vykurovaných z teplárne (diaľkové kúrenie).',
  pevne: 'Podiel domácností, ktoré kúria drevom, uhlím alebo iným pevným palivom.',
  voda: 'Koľko litrov pitnej vody z verejného vodovodu spotrebuje jeden obyvateľ za deň.',
  ms: 'Počet materských škôl v obci (aj tých, ktoré sú spojené so základnou školou).',
  zs: 'Počet základných škôl v obci.',
  ziaci: 'Počet žiakov, ktorí navštevujú základné školy v obci.',
  ss: 'Počet stredných škôl (gymnáziá, odborné školy) v obci.',
  vseob: 'Počet ambulancií všeobecných lekárov pre dospelých a pre deti.',
  zubar: 'Počet zubných ambulancií.',
  lekarne: 'Počet lekární a výdajní liekov.',
  posta: 'Počet pôšt v obci.',
  potr: 'Počet obchodov s potravinami a supermarketov zapísaných v OpenStreetMap.',
  jedlo: 'Počet reštaurácií, kaviarní, bufetov a pizzerií v OpenStreetMap.',
  ihr: 'Počet detských ihrísk v OpenStreetMap.',
  sport: 'Počet športovísk (ihriská, telocvične, kúpaliská) v OpenStreetMap.',
  zast: 'Počet zastávok autobusov, električiek a vlakov v OpenStreetMap.',
  bankom: 'Počet bankomatov v OpenStreetMap.',
  nabij: 'Počet nabíjacích staníc pre elektromobily v OpenStreetMap.',
  vlaky: 'Koľko vlakov zastaví v pracovný deň na najvyťaženejšej stanici v obci.',
  cyklo: 'Dĺžka značených cyklotrás v katastri obce.',
  turist: 'Dĺžka značených turistických chodníkov v katastri obce.',
  rozl: 'Celková rozloha katastrálneho územia obce.',
  vys: 'Nadmorská výška stredu obce.',
  les: 'Podiel lesov na rozlohe katastra.',
  orna: 'Podiel ornej pôdy (polia) na rozlohe katastra.',
  ttp: 'Podiel trvalých trávnych porastov (lúky a pasienky) na rozlohe katastra.',
  vin: 'Podiel viníc na rozlohe katastra.',
  vodp: 'Podiel vodných plôch (rieky, jazerá, nádrže) na rozlohe katastra.',
  zastp: 'Podiel zastavaných plôch (domy, cesty, dvory) na rozlohe katastra.',
  zastr: 'O koľko percent sa od roku 2015 zväčšili zastavané plochy – ukazuje, ako rýchlo sa v obci stavia.',
  chran: 'Počet chránených území (európske územia Natura 2000 a maloplošné chránené územia) v katastri.',
  zosuv: 'Počet zaevidovaných zosuvov pôdy v katastri obce.',
  pam: 'Počet zapísaných pamiatkových objektov (kostoly, kaštiele, domy…) v obci.',
  zmienka: 'Rok, z ktorého pochádza najstaršia známa písomná zmienka o obci.',
  tep: 'Priemerná ročná teplota vzduchu za posledných 10 rokov.',
  zr: 'Priemerné množstvo zrážok za rok (dážď aj sneh) za posledných 10 rokov.',
  mraz: 'Priemerný počet dní v roku, keď teplota klesne pod 0 °C.',
  leto: 'Priemerný počet dní v roku s teplotou aspoň 25 °C.',
  trop: 'Priemerný počet dní v roku s teplotou aspoň 30 °C.',
  snez: 'Priemerný počet dní v roku, keď leží sneh.',
  pm10: 'Priemerná ročná koncentrácia prachových častíc PM10 na najbližšej meracej stanici. Limit EÚ je 40, odporúčanie WHO 15.',
  pm25: 'Priemerná ročná koncentrácia jemného prachu PM2,5 na najbližšej stanici. Limit EÚ je 25, odporúčanie WHO 5.',
  no2: 'Priemerná ročná koncentrácia oxidu dusičitého (najmä z dopravy) na najbližšej stanici. Limit EÚ je 40.',
  tri: 'Aká časť komunálneho odpadu sa vytriedila (papier, plasty, sklo, bioodpad…).',
  kg: 'Koľko kilogramov komunálneho odpadu vyprodukuje jeden obyvateľ za rok.',
  kgz: 'Koľko kilogramov zmesového (netriedeného) odpadu pripadá na obyvateľa za rok.',
  bio: 'Podiel biologicky rozložiteľného odpadu (tráva, lístie, kuchynský odpad) na všetkom komunálnom odpade.',
  triz: 'O koľko percentuálnych bodov sa zlepšilo (alebo zhoršilo) triedenie odpadu od roku 2021.',
  uc: 'Aká časť voličov prišla voliť v komunálnych voľbách 2026.',
  uc22: 'Aká časť voličov prišla voliť v komunálnych voľbách 2022.',
  ucn23: 'Aká časť voličov prišla voliť v parlamentných voľbách 2023.',
  ucn20: 'Aká časť voličov prišla voliť v parlamentných voľbách 2020.',
  ucp24: 'Aká časť voličov prišla voliť v 2. kole prezidentských volieb 2024.',
  ucep24: 'Aká časť voličov prišla voliť vo voľbách do Európskeho parlamentu 2024.',
  ucr23: 'Aká časť voličov prišla hlasovať v referende 2023.',
  kand: 'Koľko kandidátov sa uchádzalo o post starostu alebo primátora v roku 2026.',
  lozka: 'Počet lôžok v hoteloch, penziónoch a iných ubytovacích zariadeniach.',
  lozkap: 'Počet lôžok v ubytovacích zariadeniach na 1 000 obyvateľov – ukazuje, nakoľko je obec turistická.',
  ubyt: 'Počet hotelov, penziónov a iných ubytovacích zariadení.',
  vyuz: 'Aká časť lôžok bola v priemere počas roka obsadená.',
};
