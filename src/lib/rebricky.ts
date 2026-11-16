// Rebríčky obcí z ukazovateľov (src/lib/ukazovatele.ts): slug stránky, kľúč, nadpis, popis vysokých/nízkych hodnôt.
// min = najmenší počet obyvateľov – pri malých obciach sú percentá a hodnoty na obyvateľa náhodné.
import { ukazovatele, POLIA, type Ukazovatele } from './ukazovatele-obci';

export interface Rebricek { slug: string; k: string; nadpis: string; hore: string; dole: string; min: number; desatiny: number; popis: string }
export const REBRICKY: Rebricek[] = [
  { slug: 'najvacsie-obce', k: 'obyv', nadpis: 'Najväčšie a najmenšie obce', hore: 'Najviac obyvateľov', dole: 'Najmenej obyvateľov', min: 0, desatiny: 0, popis: 'Počet obyvateľov k 31. 12. podľa Štatistického úradu SR.' },
  { slug: 'rast-obyvatelov', k: 'z10', nadpis: 'Najrýchlejšie rastúce a vyľudňujúce sa obce', hore: 'Najväčší rast za 10 rokov', dole: 'Najväčší pokles za 10 rokov', min: 300, desatiny: 1, popis: 'Zmena počtu obyvateľov za posledných 10 rokov v percentách.' },
  { slug: 'priemerny-vek', k: 'vek', nadpis: 'Najstaršie a najmladšie obce', hore: 'Najvyšší priemerný vek', dole: 'Najnižší priemerný vek', min: 300, desatiny: 1, popis: 'Priemerný vek obyvateľov podľa Štatistického úradu SR.' },
  { slug: 'deti', k: 'deti', nadpis: 'Obce s najviac a najmenej deťmi', hore: 'Najvyšší podiel detí do 14 rokov', dole: 'Najnižší podiel detí do 14 rokov', min: 300, desatiny: 1, popis: 'Podiel obyvateľov vo veku do 14 rokov podľa sčítania 2021.' },
  { slug: 'seniori', k: 'sen', nadpis: 'Obce s najviac a najmenej seniormi', hore: 'Najvyšší podiel ľudí nad 65 rokov', dole: 'Najnižší podiel ľudí nad 65 rokov', min: 300, desatiny: 1, popis: 'Podiel obyvateľov vo veku 65 a viac rokov podľa sčítania 2021.' },
  { slug: 'vysokoskolaci', k: 'vs', nadpis: 'Obce s najviac a najmenej vysokoškolákmi', hore: 'Najvyšší podiel vysokoškolákov', dole: 'Najnižší podiel vysokoškolákov', min: 300, desatiny: 1, popis: 'Podiel obyvateľov s vysokoškolským vzdelaním (sčítanie 2021, z obyvateľov 15+ podľa tabuľky vzdelania).' },
  { slug: 'nezamestnanost', k: 'nez', nadpis: 'Najvyššia a najnižšia nezamestnanosť', hore: 'Najvyššia miera nezamestnanosti', dole: 'Najnižšia miera nezamestnanosti', min: 300, desatiny: 1, popis: 'Podiel disponibilných uchádzačov o zamestnanie na obyvateľoch v produktívnom veku (ÚPSVaR, posledný mesiac).' },
  { slug: 'ucast-komunalne-volby-2026', k: 'uc', nadpis: 'Najvyššia a najnižšia účasť v komunálnych voľbách 2026', hore: 'Najvyššia účasť', dole: 'Najnižšia účasť', min: 300, desatiny: 1, popis: 'Účasť voličov v komunálnych voľbách 2026 (ŠÚ SR).' },
  { slug: 'najteplejsie-obce', k: 'tep', nadpis: 'Najteplejšie a najchladnejšie obce', hore: 'Najvyššia priemerná teplota', dole: 'Najnižšia priemerná teplota', min: 0, desatiny: 1, popis: 'Priemerná ročná teplota za posledných 10 rokov (reanalýza ERA5 cez Open-Meteo, prepočítaná na nadmorskú výšku obce).' },
  { slug: 'zrazky', k: 'zr', nadpis: 'Obce s najviac a najmenej zrážkami', hore: 'Najviac zrážok', dole: 'Najmenej zrážok', min: 0, desatiny: 0, popis: 'Priemerný ročný úhrn zrážok za posledných 10 rokov (ERA5 cez Open-Meteo, mriežka ~25 km).' },
  { slug: 'nadmorska-vyska', k: 'vys', nadpis: 'Najvyššie a najnižšie položené obce', hore: 'Najvyššia nadmorská výška', dole: 'Najnižšia nadmorská výška', min: 0, desatiny: 0, popis: 'Nadmorská výška obce podľa Wikidata.' },
  { slug: 'hustota', k: 'hus', nadpis: 'Najhustejšie a najredšie osídlené obce', hore: 'Najvyššia hustota', dole: 'Najnižšia hustota', min: 0, desatiny: 0, popis: 'Obyvatelia na km² rozlohy katastra (ŠÚ SR).' },
  { slug: 'investicie-obci', k: 'inv', nadpis: 'Obce s najvyššími investíciami na obyvateľa', hore: 'Najvyššie investície na obyvateľa', dole: 'Najnižšie investície na obyvateľa', min: 500, desatiny: 0, popis: 'Kapitálové výdavky obce za posledný ukončený rok na obyvateľa (MF SR – rozpocet.sk). Jeden veľký projekt môže rok výrazne zmeniť.' },
  { slug: 'triedenie-odpadu', k: 'tri', nadpis: 'Obce, ktoré najviac a najmenej triedia odpad', hore: 'Najvyššia miera triedenia', dole: 'Najnižšia miera triedenia', min: 300, desatiny: 0, popis: 'Podiel vytriedeného komunálneho odpadu (ŠÚ SR, posledný rok).' },
];

export const jednotka = (k: string) => POLIA.find(([x]) => x === k)?.[2] ?? '';

const CACHE = new Map<string, { p: Ukazovatele[]; idx: Map<string, number> }>();
function zorad(r: Rebricek) {
  let c = CACHE.get(r.slug);
  if (!c) {
    const p = ukazovatele().filter((x) => x.h[r.k] != null && (x.h.obyv ?? 0) >= r.min).sort((a, b) => (b.h[r.k]! - a.h[r.k]!) || a.o.nazov.localeCompare(b.o.nazov, 'sk'));
    c = { p, idx: new Map(p.map((x, i) => [x.o.kod, i])) };
    CACHE.set(r.slug, c);
  }
  return c;
}
export const poradie = (r: Rebricek): Ukazovatele[] => zorad(r).p;

/** Umiestnenia obce v rebríčkoch (do top N zhora alebo zdola) – pre profil obce. */
export function umiestnenia(kod: string, n = 20): { r: Rebricek; miesto: number; hore: boolean; spolu: number }[] {
  const out: { r: Rebricek; miesto: number; hore: boolean; spolu: number }[] = [];
  for (const r of REBRICKY) {
    const { p, idx } = zorad(r);
    const i = idx.get(kod);
    if (i == null) continue;
    if (i < n) out.push({ r, miesto: i + 1, hore: true, spolu: p.length });
    else if (p.length - i <= n) out.push({ r, miesto: p.length - i, hore: false, spolu: p.length });
  }
  return out;
}
