// Sviatky, dni pracovného pokoja, zákaz predaja, školské prázdniny podľa kraja a meniny.
// Čisté funkcie – používa ich build (Kalendar.astro) aj prehliadač (aktuálny dátum návštevníka).
//
// Sviatky: zákon č. 241/1993 Z. z. v znení od 29. 10. 2026 – § 1 štátne sviatky, § 2 dni pracovného pokoja,
//   § 2 ods. 3: 1. 9., 28. 10. a 17. 11. nie sú dňami pracovného pokoja; § 4b: v roku 2026 nie sú 8. 5. a 15. 9.
// Zákaz predaja: § 94 ods. 5 Zákonníka práce (od 1. 11. 2025): 1. 1., Veľký piatok, Veľkonočná nedeľa,
//   24. 12. od 12:00, 25. 12., 26. 12. (výnimky: čerpacie stanice, lekárne, letiská, stanice, nemocnice…).
// Prázdniny: data/prazdniny.json (harmonogram MŠVVaM SR).
import PRAZDNINY from '../../data/prazdniny.json';
import MENINY from '../../data/meniny.json';

export type Sviatok = { d: string; nazov: string; statny: boolean; volno: boolean; obchody: '' | 'zatvorené' | 'zatvorené od 12:00'; pozn?: string };
export type Obdobie = { nazov: string; od: string; do: string; navrat: string; kraje?: string[] };

const p2 = (n: number) => String(n).padStart(2, '0');
export const iso = (d: Date) => `${d.getFullYear()}-${p2(d.getMonth() + 1)}-${p2(d.getDate())}`;
const zIso = (s: string) => new Date(Number(s.slice(0, 4)), Number(s.slice(5, 7)) - 1, Number(s.slice(8, 10)));
const plus = (s: string, dni: number) => { const d = zIso(s); d.setDate(d.getDate() + dni); return iso(d); };

/** Veľkonočná nedeľa (gregoriánsky kalendár, anonymný algoritmus). */
export function velkaNoc(y: number): string {
  const a = y % 19, b = Math.floor(y / 100), c = y % 100, d = Math.floor(b / 4), e = b % 4;
  const f = Math.floor((b + 8) / 25), g = Math.floor((b - f + 1) / 3), h = (19 * a + b - d - g + 15) % 30;
  const i = Math.floor(c / 4), k = c % 4, l = (32 + 2 * e + 2 * i - h - k) % 7, m = Math.floor((a + 11 * h + 22 * l) / 451);
  const mes = Math.floor((h + l - 7 * m + 114) / 31), den = ((h + l - 7 * m + 114) % 31) + 1;
  return `${y}-${p2(mes)}-${p2(den)}`;
}

export function sviatky(y: number): Sviatok[] {
  const vn = velkaNoc(y);
  const bez2026 = y === 2026 ? { volno: false, pozn: 'v roku 2026 výnimočne nie je dňom pracovného pokoja' } : { volno: true };
  const s: Sviatok[] = [
    { d: `${y}-01-01`, nazov: 'Deň vzniku Slovenskej republiky', statny: true, volno: true, obchody: 'zatvorené' },
    { d: `${y}-01-06`, nazov: 'Zjavenie Pána (Traja králi)', statny: false, volno: true, obchody: '' },
    { d: plus(vn, -2), nazov: 'Veľký piatok', statny: false, volno: true, obchody: 'zatvorené' },
    { d: vn, nazov: 'Veľkonočná nedeľa', statny: false, volno: true, obchody: 'zatvorené', pozn: 'nedeľa' },
    { d: plus(vn, 1), nazov: 'Veľkonočný pondelok', statny: false, volno: true, obchody: '' },
    { d: `${y}-05-01`, nazov: 'Sviatok práce', statny: false, volno: true, obchody: '' },
    { d: `${y}-05-08`, nazov: 'Deň víťazstva nad fašizmom', statny: false, obchody: '', ...bez2026 },
    { d: `${y}-07-05`, nazov: 'Sviatok svätého Cyrila a svätého Metoda', statny: true, volno: true, obchody: '' },
    { d: `${y}-08-29`, nazov: 'Výročie Slovenského národného povstania', statny: true, volno: true, obchody: '' },
    { d: `${y}-09-01`, nazov: 'Deň Ústavy Slovenskej republiky', statny: true, volno: false, obchody: '' },
    { d: `${y}-09-15`, nazov: 'Sedembolestná Panna Mária', statny: false, obchody: '', ...bez2026 },
    { d: `${y}-10-28`, nazov: 'Deň vzniku samostatného česko-slovenského štátu', statny: true, volno: false, obchody: '' },
    { d: `${y}-11-01`, nazov: 'Sviatok Všetkých svätých', statny: false, volno: true, obchody: '' },
    { d: `${y}-11-17`, nazov: 'Deň boja za slobodu a demokraciu', statny: true, volno: false, obchody: '' },
    { d: `${y}-12-24`, nazov: 'Štedrý deň', statny: false, volno: true, obchody: 'zatvorené od 12:00' },
    { d: `${y}-12-25`, nazov: 'Prvý sviatok vianočný', statny: false, volno: true, obchody: 'zatvorené' },
    { d: `${y}-12-26`, nazov: 'Druhý sviatok vianočný', statny: false, volno: true, obchody: 'zatvorené' },
  ];
  return s.sort((a, b) => a.d.localeCompare(b.d));
}

/** Sviatky od dnes (vrátane) – tento a budúci rok. */
export const nasledujuce = (dnes: string, n = 99): Sviatok[] => {
  const y = Number(dnes.slice(0, 4));
  return [...sviatky(y), ...sviatky(y + 1)].filter((s) => s.d >= dnes).slice(0, n);
};

export const prazdninyKraja = (kraj: string): (Obdobie & { skolsky_rok: string })[] =>
  (PRAZDNINY.roky as { skolsky_rok: string; obdobia: Obdobie[] }[])
    .flatMap((r) => r.obdobia.filter((o) => !o.kraje || o.kraje.includes(kraj)).map((o) => ({ ...o, skolsky_rok: r.skolsky_rok })))
    .sort((a, b) => a.od.localeCompare(b.od));

export function stavPrazdnin(kraj: string, dnes: string) {
  const vsetky = prazdninyKraja(kraj);
  const teraz = vsetky.find((o) => o.od <= dnes && dnes <= o.do) ?? null;
  const dalsie = vsetky.find((o) => o.od > dnes) ?? null;
  return { teraz, dalsie, vsetky };
}

export const PRAZDNINY_ZDROJ = PRAZDNINY.zdroj;

/** „dnes“, „zajtra“, „o 3 dni“, „o 12 dní“. */
export function kedy(dnes: string, d: string): string {
  const n = Math.round((zIso(d).getTime() - zIso(dnes).getTime()) / 864e5);
  if (n === 0) return 'dnes';
  if (n === 1) return 'zajtra';
  if (n === 2) return 'pozajtra';
  return `o ${n} ${n >= 2 && n <= 4 ? 'dni' : 'dní'}`;
}

const DNI = ['nedeľa', 'pondelok', 'utorok', 'streda', 'štvrtok', 'piatok', 'sobota'];
const DNI_K = ['ne', 'po', 'ut', 'st', 'št', 'pi', 'so'];
export const den = (s: string) => DNI[zIso(s).getDay()];
export const datum = (s: string, rok = false) => { const d = zIso(s); return `${DNI_K[d.getDay()]} ${d.getDate()}. ${d.getMonth() + 1}.${rok ? ` ${d.getFullYear()}` : ''}`; };
export const rozsah = (od: string, doo: string) => {
  const a = zIso(od), b = zIso(doo);
  if (od === doo) return `${a.getDate()}. ${a.getMonth() + 1}. ${a.getFullYear()}`;
  const r = a.getFullYear() === b.getFullYear();
  return `${a.getDate()}. ${a.getMonth() + 1}.${r ? '' : ` ${a.getFullYear()}`} – ${b.getDate()}. ${b.getMonth() + 1}. ${b.getFullYear()}`;
};
export const vikend = (s: string) => [0, 6].includes(zIso(s).getDay());
export const zajtra = (s: string) => plus(s, 1);

/** Meniny (slovenský kalendár mien; 1. 1., 1. 5., 2. 11. a 25. 12. bez mena). */
export const meniny = (s: string): string[] => (MENINY as Record<string, string[]>)[s.slice(5)] ?? [];

export type Dlazdica = { hodnota: string; pozn: string; stav?: string };

/** Texty dlaždíc pre daný kraj a deň – rovnaké na serveri (záloha bez JS) aj v prehliadači. */
export function dlazdice(kraj: string, dnes: string): Record<'meniny' | 'sviatok' | 'obchody' | 'prazdniny', Dlazdica> {
  const zoz = (a: string[]) => a.length ? a.join(', ') : 'nikto (deň bez mena)';
  const mz = meniny(zajtra(dnes));
  const men: Dlazdica = { hodnota: zoz(meniny(dnes)), pozn: mz.length ? `zajtra ${mz.join(', ')}` : 'zajtra deň bez mena' };

  const dalsie = nasledujuce(dnes).filter((x) => x.nazov !== 'Veľkonočná nedeľa');
  const s = dalsie[0];
  let v: Sviatok | undefined;
  const typ = (x: Sviatok) => x.volno ? 'deň pracovného pokoja' : x.statny ? 'štátny sviatok, ale pracovný deň' : 'pracovný deň';
  const sv: Dlazdica = s.d === dnes
    ? { hodnota: s.nazov, pozn: `dnes · ${typ(s)}${s.pozn ? ` (${s.pozn})` : ''}`, stav: s.volno ? 'ok' : '' }
    : { hodnota: s.nazov, pozn: `${datum(s.d)} · ${kedy(dnes, s.d)} · ${typ(s)}${s.volno && vikend(s.d) ? ', pripadá na víkend' : ''}${s.pozn && !s.volno ? ` – ${s.pozn}` : ''}${!s.volno && (v = dalsie.find((x) => x.volno)) ? ` · najbližšie voľno ${datum(v.d)}` : ''}` };

  const z = nasledujuce(dnes).find((x) => x.obchody);
  const ob: Dlazdica = !z ? { hodnota: '–', pozn: '' } : z.d === dnes
    ? { hodnota: z.obchody === 'zatvorené' ? 'Dnes zatvorené' : 'Dnes od 12:00 zatvorené', pozn: `${z.nazov} · otvorené sú čerpacie stanice, lekárne, predajne na staniciach a letiskách`, stav: 'yellow' }
    : { hodnota: `${datum(z.d)} ${z.obchody === 'zatvorené' ? 'zatvorené' : 'od 12:00 zatvorené'}`, pozn: `${z.nazov} · ${kedy(dnes, z.d)} · v ostatné sviatky rozhoduje obchod sám` };

  const { teraz, dalsie: dp } = stavPrazdnin(kraj, dnes);
  const pr: Dlazdica = teraz
    ? { hodnota: `Teraz: ${teraz.nazov.toLowerCase()}`, pozn: `do ${datum(teraz.do)} · do školy ${datum(teraz.navrat)} (${kedy(dnes, teraz.navrat)})`, stav: 'ok' }
    : dp ? { hodnota: dp.nazov, pozn: `${rozsah(dp.od, dp.do)} · ${kedy(dnes, dp.od)}` }
    : { hodnota: '–', pozn: 'harmonogram ďalšieho školského roka zatiaľ nie je zverejnený' };
  return { meniny: men, sviatok: sv, obchody: ob, prazdniny: pr };
}
