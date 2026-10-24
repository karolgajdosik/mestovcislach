// Spoločná sada ukazovateľov krajských miest (hodnota pre každé mesto) – pre „Porovnaj dve mestá“ a „Súboj miest“.
// Zdroje: data/mesta/porovnanie.json (zber_mesta.py) a Urban Audit ŠÚ SR (data/mesta/temy.json → mestske).
import fs from 'node:fs';
import path from 'node:path';
import { MESTA } from '../mesta';

export type Ukazovatel = {
  id: string; nazov: string; tema: string; jednotka: string; des: number;
  lepsie: 'viac' | 'menej' | null; // čo je pre obyvateľa lepšie (null = neutrálne)
  hodnoty: Record<string, number>; rok: string; zdroj: string;
  otazka: string; // „Ktoré mesto má viac …?“ – pre súboj
};

const citaj = (...p: string[]) => {
  const f = path.join(process.cwd(), ...p);
  return fs.existsSync(f) ? JSON.parse(fs.readFileSync(f, 'utf-8')) : null;
};

let cache: Ukazovatel[] | null = null;
export function ukazovatele(): Ukazovatel[] {
  if (cache) return cache;
  const akt = MESTA.filter((m) => m.aktivne).map((m) => m.slug);
  const por: any[] = citaj('data', 'mesta', 'porovnanie.json')?.mesta ?? [];
  const out: Ukazovatel[] = [];
  const zPor = (k: string) => Object.fromEntries(por.filter((x) => x[k] != null && akt.includes(x.slug)).map((x) => [x.slug, x[k]]));
  const rokPor = por.find((x) => x.rok)?.rok ?? '';
  const P = (id: string, k: string, nazov: string, tema: string, jednotka: string, des: number, lepsie: Ukazovatel['lepsie'], otazka: string, zdroj = 'ŠÚ SR', rok = rokPor) => {
    const h = zPor(k);
    if (Object.keys(h).length >= 6) out.push({ id, nazov, tema, jednotka, des, lepsie, hodnoty: h, rok, zdroj, otazka });
  };
  P('obyvatelia', 'obyvatelia', 'Obyvatelia', 'Ľudia', '', 0, null, 'Ktoré mesto má viac obyvateľov?');
  P('zmena10', 'zmena10', 'Zmena počtu obyvateľov za 10 rokov', 'Ľudia', ' %', 1, 'viac', 'Ktoré mesto za 10 rokov viac rástlo (alebo menej ubúdalo)?');
  P('seniori', 'seniori', 'Seniori 65+', 'Ľudia', ' %', 1, null, 'Kde je väčší podiel seniorov nad 65 rokov?', 'Sčítanie 2021', '');
  P('deti', 'deti', 'Deti do 14 rokov', 'Ľudia', ' %', 1, null, 'Kde je väčší podiel detí do 14 rokov?', 'Sčítanie 2021', '');
  P('vs', 'vs', 'Vysokoškolsky vzdelaní', 'Ľudia', ' %', 1, 'viac', 'Kde je viac vysokoškolsky vzdelaných ľudí?', 'Sčítanie 2021', '');
  P('pdu', 'pdu', 'Nezamestnanosť (PDU)', 'Práca', ' %', 2, 'menej', 'Kde je vyššia nezamestnanosť?', 'ÚPSVaR', '');
  P('ucast', 'ucast_komunalne', 'Účasť v komunálnych voľbách', 'Voľby', ' %', 1, 'viac', 'Kde bola vyššia účasť v komunálnych voľbách?', 'ŠÚ SR – voľby', '');
  P('byty10', 'byty_10r', 'Dokončené byty ročne (priemer 10 r.)', 'Bývanie', '', 0, 'viac', 'Kde sa ročne dokončí viac bytov?', 'ŠÚ SR – za okresy mesta', '');
  P('vlastne', 'vlastne_byty', 'Byty vo vlastníctve', 'Bývanie', ' %', 1, null, 'Kde je väčší podiel bytov vo vlastníctve?', 'Sčítanie 2021', '');

  // Urban Audit – posledný rok ukazovateľa
  const UA = citaj('data', 'mesta', 'temy.json')?.mestske;
  const U = (id: string, popis: string, nazov: string, tema: string, jednotka: string, des: number, lepsie: Ukazovatel['lepsie'], otazka: string) => {
    const k = Object.entries<string>(UA?.popisy ?? {}).find(([, p]) => p === popis)?.[0];
    if (!k) return;
    const h: Record<string, number> = {}; let rok = '';
    for (const s of akt) {
      const rad = UA.mesta?.[s]?.[k]; if (!rad) continue;
      const y = Object.keys(rad).sort().pop()!; h[s] = rad[y]; if (y > rok) rok = y;
    }
    if (Object.keys(h).length >= 6) out.push({ id, nazov, tema, jednotka, des, lepsie, hodnoty: h, rok, zdroj: 'ŠÚ SR – Urban Audit', otazka });
  };
  U('byt-m2', 'Priemerná cena za kúpu bytu za m2', 'Cena bytu za m²', 'Bývanie', ' €', 0, 'menej', 'Kde je drahší štvorcový meter bytu?');
  U('auta', 'Registrované súkromné osobné autá k 1.1. na 1000 obyvateľov', 'Osobné autá na 1000 obyvateľov', 'Doprava', '', 0, null, 'Kde pripadá viac áut na 1000 obyvateľov?');
  U('cyklo', 'Dĺžka cyklistickej siete', 'Dĺžka cyklistickej siete', 'Doprava', ' km', 0, 'viac', 'Ktoré mesto má dlhšiu sieť cyklotrás?');
  U('listok', 'Cena kombinovaného mesačného lístka na všetky druhy verejnej dopravy v centre v okruhu 5-10 km', 'Mesačný lístok MHD', 'Doprava', ' €', 1, 'menej', 'Kde je drahší mesačný lístok na MHD?');
  U('voda', 'Cena za m3 vody v domácnostiach – Euro', 'Cena vody za m³', 'Život', ' €', 2, 'menej', 'Kde platia domácnosti viac za kubík vody?');
  U('odpad', 'Množstvo komunálneho odpadu – kg na osobu', 'Komunálny odpad na osobu', 'Život', ' kg', 0, 'menej', 'Kde vyprodukuje človek viac komunálneho odpadu?');
  U('turisti', 'Prenocovania v ubytovacích zariadeniach cestovného ruchu na obyvateľa', 'Prenocovania turistov na obyvateľa', 'Život', '', 1, null, 'Kam chodí viac turistov (prenocovania na obyvateľa)?');
  U('bazeny', 'Počet verejných bazénov (vnútorných aj vonkajších, okrem prírodných pláží)', 'Verejné bazény', 'Život', '', 0, 'viac', 'Ktoré mesto má viac verejných bazénov?');
  U('jasle', 'Deti do 4 rokov v predškolských zariadeniach na 1000 detí do 4 rokov', 'Deti do 4 r. v jasliach a škôlkach (na 1000)', 'Život', '', 0, 'viac', 'Kde chodí do jaslí a škôlky viac malých detí?');
  cache = out;
  return out;
}

export const formatuj = (u: Pick<Ukazovatel, 'des' | 'jednotka'>, v: number | null | undefined) =>
  v == null ? '–' : `${v.toLocaleString('sk-SK', { minimumFractionDigits: u.des, maximumFractionDigits: u.des })}${u.jednotka}`;
