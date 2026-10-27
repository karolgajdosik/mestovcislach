// Kalendár mesta na odber (ICS): dôležité termíny pre obyvateľov (zápis do ZŠ, prihlášky do MŠ a na SŠ, daňové
// priznanie k dani z nehnuteľností), zasadnutia zastupiteľstva (z hlasovaní, ktoré web zbiera) a voľby.
// Zasadnutia pribudnú v kalendári samy, keď sa objavia v dátach mesta.
import fs from 'node:fs';
import path from 'node:path';
import { novinky } from './novinky';

export type Udalost = { id: string; od: string; do?: string; nazov: string; popis: string; odkaz: string; typ: 'termin' | 'zastupitelstvo' | 'volby'; pripomienka?: boolean };

const plus = (d: string, n: number) => new Date(Date.parse(d) + n * 864e5).toISOString().slice(0, 10);

/** celoštátne termíny pre obyvateľov (rovnaké v každom meste), pre tento a budúci rok */
function terminy(slug: string, rok: number): Udalost[] {
  return [
    { id: `dzn-${rok}`, od: `${rok}-01-31`, nazov: 'Daňové priznanie k dani z nehnuteľností', popis: 'Posledný deň na podanie priznania, ak ste v minulom roku nadobudli, predali alebo zmenili nehnuteľnosť (byt, dom, pozemok, garáž). Podáva sa mestu, v Bratislave cez mesto.', odkaz: `/${slug}/dane`, typ: 'termin', pripomienka: true },
    { id: `ss-${rok}`, od: `${rok}-02-20`, nazov: 'Prihlášky na stredné školy – posledný deň', popis: 'Deviataci podávajú prihlášky na stredné školy (elektronicky cez ePrihlášky alebo cez základnú školu).', odkaz: `/${slug}/skoly`, typ: 'termin', pripomienka: true },
    { id: `zs-${rok}`, od: `${rok}-04-01`, do: `${rok}-04-30`, nazov: 'Zápis do 1. ročníka základných škôl', popis: 'Zápis budúcich prvákov prebieha od 1. do 30. apríla; konkrétne dni určuje škola alebo mesto.', odkaz: `/${slug}/skoly`, typ: 'termin', pripomienka: true },
    { id: `ms-${rok}`, od: `${rok}-05-01`, do: `${rok}-05-31`, nazov: 'Prihlášky do materských škôl', popis: 'Prihlášky do materských škôl sa podávajú od 1. do 31. mája; konkrétne dni určuje škôlka.', odkaz: `/${slug}/skoly`, typ: 'termin', pripomienka: true },
  ];
}

export function kalendar(slug: string): Udalost[] {
  const dnes = new Date().toISOString().slice(0, 10);
  const rok = Number(dnes.slice(0, 4));
  const out: Udalost[] = [...terminy(slug, rok), ...terminy(slug, rok + 1)];
  // zasadnutia zastupiteľstva a voľby za posledný rok (z „Čo je nové“)
  for (const n of novinky(slug, 400)) {
    if (n.typ === 'zastupitelstvo') out.push({ id: `msz-${n.datum}`, od: n.datum, nazov: 'Zasadnutie mestského zastupiteľstva', popis: [n.nazov.replace(/^Zasadnutie zastupiteľstva:\s*/, ''), n.text].filter(Boolean).join('. '), odkaz: n.odkaz, typ: 'zastupitelstvo' });
    if (n.typ === 'volby') out.push({ id: `volby-${n.datum}`, od: n.datum, nazov: n.nazov, popis: n.text, odkaz: n.odkaz, typ: 'volby' });
  }
  if (!out.some((u) => u.id === 'volby-2026-10-24')) out.push({ id: 'volby-2026-10-24', od: '2026-10-24', nazov: 'Komunálne a regionálne voľby', popis: 'Voľby primátora, poslancov mestského zastupiteľstva a orgánov samosprávneho kraja (7:00 – 20:00).', odkaz: `/${slug}${slug === 'bratislava' ? '/volby' : '/volby'}`, typ: 'volby' });
  // nové zastupiteľstvo 2026 – 2030: ustanovujúce zasadnutie do 30 dní od volieb (§ 12 ods. 1 zákona č. 369/1990 Zb.),
  // kým mesto nezverejní skutočný termín (prvé zasadnutie po voľbách v dátach)
  if (!out.some((u) => u.typ === 'zastupitelstvo' && u.od > '2026-10-24' && u.od <= '2026-11-23'))
    out.push({ id: 'ustanovujuce-2026', od: '2026-11-23', nazov: 'Najneskorší termín ustanovujúceho zasadnutia zastupiteľstva', popis: 'Nové mestské zastupiteľstvo sa musí zísť do 30 dní od volieb; primátor a poslanci na ňom zložia sľub. Presný dátum určí doterajší primátor.', odkaz: `/${slug}/zastupitelstvo`, typ: 'zastupitelstvo' });
  // rozpočet na budúci rok: zverejnený návrh (scripts/zber_rozpocty.py) a termín schválenia do konca roka
  const rRok = rok + 1;
  try {
    const rz = JSON.parse(fs.readFileSync(path.join(process.cwd(), 'data', `rozpocty-${rRok}.json`), 'utf-8'));
    const navrh = (rz.mesta?.[slug]?.dokumenty ?? []).filter((d: any) => d.druh === 'návrh rozpočtu').map((d: any) => d.zverejnene || d.videne_od).sort()[0];
    if (navrh && rRok === 2027) out.push({ id: `navrh-rozpoctu-${rRok}`, od: navrh, nazov: `Zverejnený návrh rozpočtu na rok ${rRok}`, popis: 'Mesto zverejnilo návrh rozpočtu – najmenej 15 dní sa k nemu môžu vyjadriť obyvatelia, potom ho schvaľuje zastupiteľstvo.', odkaz: `/rozpocty-${rRok}#${slug}`, typ: 'termin' });
  } catch { /* zatiaľ bez údajov */ }
  if (rRok === 2027) out.push({ id: `rozpocet-${rRok}`, od: `${rok}-12-31`, nazov: `Posledný deň na schválenie rozpočtu na rok ${rRok}`, popis: 'Ak zastupiteľstvo rozpočet neschváli do konca roka, mesto od januára hospodári v rozpočtovom provizóriu (mesačne najviac 1/12 vlaňajších výdavkov).', odkaz: `/rozpocty-${rRok}#${slug}`, typ: 'termin' });
  // termíny len od dnešného dňa o rok dozadu do ~14 mesiacov dopredu
  const min = plus(dnes, -400), max = plus(dnes, 430);
  return out.filter((u) => (u.do ?? u.od) >= min && u.od <= max).sort((a, b) => a.od.localeCompare(b.od));
}

// --- ICS (RFC 5545) ---
const esc = (s: string) => s.replace(/\\/g, '\\\\').replace(/;/g, '\\;').replace(/,/g, '\\,').replace(/\r?\n/g, '\\n');
function zloz(riadok: string) {
  // riadky max. 75 bajtov (UTF-8), pokračovanie začína medzerou
  const out: string[] = [];
  let akt = '', bajty = 0;
  for (const ch of riadok) {
    const b = new TextEncoder().encode(ch).length;
    if (bajty + b > (out.length ? 74 : 75)) { out.push(akt); akt = ''; bajty = 0; }
    akt += ch; bajty += b;
  }
  out.push(akt);
  return out.join('\r\n ');
}
const d8 = (d: string) => d.replace(/-/g, '');

export function ics(slug: string, nazovMesta: string, udalosti: Udalost[], web = 'https://mestovcislach.sk') {
  const teraz = new Date().toISOString().replace(/[-:]/g, '').replace(/\.\d+Z$/, 'Z');
  const r = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//mestovcislach.sk//Kalendar mesta//SK', 'CALSCALE:GREGORIAN', 'METHOD:PUBLISH',
    `X-WR-CALNAME:${esc(`${nazovMesta} – termíny a zastupiteľstvo`)}`, 'X-WR-TIMEZONE:Europe/Bratislava', 'REFRESH-INTERVAL;VALUE=DURATION:P1D', 'X-PUBLISHED-TTL:P1D'];
  for (const u of udalosti) {
    r.push('BEGIN:VEVENT', `UID:${u.id}-${slug}@mestovcislach.sk`, `DTSTAMP:${teraz}`, `DTSTART;VALUE=DATE:${d8(u.od)}`, `DTEND;VALUE=DATE:${d8(plus(u.do ?? u.od, 1))}`,
      `SUMMARY:${esc(u.nazov)}`, `DESCRIPTION:${esc(`${u.popis}\n\n${web}${u.odkaz}`)}`, `URL:${web}${u.odkaz}`, 'TRANSP:TRANSPARENT');
    if (u.pripomienka) r.push('BEGIN:VALARM', 'ACTION:DISPLAY', `DESCRIPTION:${esc(u.nazov)}`, 'TRIGGER:-P1D', 'END:VALARM');
    r.push('END:VEVENT');
  }
  r.push('END:VCALENDAR');
  return r.map(zloz).join('\r\n') + '\r\n';
}
