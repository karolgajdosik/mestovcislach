// „Čo je nové v meste“: novinky z dát, ktoré web už zbiera – stavebné zámery (EIA/SEA), väčšie zmluvy mesta
// (len právnické osoby s IČO), zasadnutia zastupiteľstva (názvy bodov hlasovania) a komunálne voľby.
import fs from 'node:fs';
import path from 'node:path';
import { obdobia } from './zastupitelstvo';

const bezTit = (m: string) => m.split(/[\s,]+/).filter((s) => s && !s.includes('.') && !/^(PhD|MBA|LL|MPH|MPA|DiS|CSc|ArtD|MSc)$/i.test(s)).join(' ');

export type Novinka = { datum: string; typ: 'stavby' | 'zmluvy' | 'zastupitelstvo' | 'volby'; nazov: string; text: string; odkaz: string };
export const TYPY_NOVINIEK: Record<Novinka['typ'], string> = { stavby: 'Čo sa stavia', zmluvy: 'Zmluvy mesta', zastupitelstvo: 'Zastupiteľstvo', volby: 'Voľby' };

const citaj = (...p: string[]) => {
  const f = path.join(process.cwd(), ...p);
  return fs.existsSync(f) ? JSON.parse(fs.readFileSync(f, 'utf-8')) : null;
};
const eur = (n: number) => `${Math.round(n).toLocaleString('sk-SK')} €`;
const bezUvodzoviek = (s: string) => String(s).replace(/^"+|"+$/g, '').trim();

export function novinky(slug: string, dni = 180): Novinka[] {
  const ba = slug === 'bratislava';
  const hranica = new Date(Date.now() - dni * 864e5).toISOString().slice(0, 10);
  const out: Novinka[] = [];

  // stavebné zámery v posudzovaní vplyvov na životné prostredie
  const eia = ba ? citaj('public', 'data', 'eia.json') : citaj('public', 'data', 'mesta', `eia-${slug}.json`);
  const stavbyOdkaz = ba ? '/bratislava/vystavba' : `/${slug}#stavby`;
  for (const z of eia?.zamery ?? []) {
    if (String(z.ukoncene) === 'True' || z.ukoncene === true) continue;
    const posl = z.posledny_dokument && z.posledny_dokument > (z.od ?? '') ? String(z.posledny_dokument).slice(0, 10) : null;
    const datum = posl ?? String(z.od ?? '').slice(0, 10);
    if (!datum || datum < hranica) continue;
    const nove = !posl || (z.od && z.od >= hranica && posl === z.od);
    out.push({
      datum, typ: 'stavby',
      nazov: `${nove ? 'Nový zámer' : 'Nový dokument k zámeru'}: ${bezUvodzoviek(z.nazov)}`,
      text: [z.stav, z.proces, Array.isArray(z.mc) && z.mc.length ? z.mc.join(', ') : ''].filter(Boolean).join(' · '),
      odkaz: z.seo && eia.web ? `${eia.web}${z.seo}` : stavbyOdkaz,
    });
  }

  // najväčšie zmluvy mesta za posledných 12 mesiacov (Centrálny register zmlúv / portál mesta)
  const zm = slug === 'kosice' ? citaj('data', 'mesta', 'samosprava-kosice.json')?.financie?.find((f: any) => f.typ === 'zmluvy')
    : citaj('data', 'mesta', `crz-${slug}.json`)?.zmluvy;
  for (const z of zm?.najvacsie_12_mesiacov ?? []) {
    if (!z.ico || !z.datum || z.datum < hranica) continue; // len právnické osoby s IČO
    out.push({
      datum: String(z.datum).slice(0, 10), typ: 'zmluvy',
      nazov: `Zmluva na ${eur(z.suma)}: ${z.dodavatel}`,
      text: String(z.popis ?? '').slice(0, 220),
      odkaz: z.url ?? `/${slug}/samosprava`,
    });
  }

  // zasadnutia zastupiteľstva (dátum, počet hlasovaní, prvé body programu)
  const hl = ba ? citaj('public', 'data', 'hlasovania-msz.json') : citaj('public', 'data', 'mesta', `hlasovania-${slug}-2022-2026.json`);
  if (hl?.hlasovania?.length) {
    const sedenia = new Map<string, string[]>();
    for (const h of hl.hlasovania) {
      const d = String(h[0]).slice(0, 10);
      if (d < hranica) continue;
      (sedenia.get(d) ?? sedenia.set(d, []).get(d)!).push(String(h[3]));
    }
    for (const [d, body] of sedenia) {
      const temy = [...new Set(body.map((b) => b.replace(/\s*\((?:iné|[^)]{0,40})\)\s*$/, '').replace(/^\d+[a-z]?\.\s*/, '')))]
        .filter((b) => !/overovateľ|návrhov\w* komisi|program rokovania|mandátov|otvorenie|záver/i.test(b)).slice(0, 4);
      out.push({
        datum: d, typ: 'zastupitelstvo',
        nazov: `Zasadnutie zastupiteľstva: ${body.length} hlasovaní`,
        text: temy.join(' · '),
        odkaz: ba ? '/bratislava/volby#hlasovania' : `/${slug}/samosprava#hlasovania`,
      });
    }
  }

  // komunálne voľby – výsledky (po spracovaní)
  const o = obdobia(slug)[0];
  if (o && Number(o.rok) >= 2026 && o.primator) {
    out.push({
      datum: '2026-10-24', typ: 'volby',
      nazov: o.priebezne ? `Komunálne voľby ${o.rok}: priebežne vedie ${bezTit(o.primator.meno)}` : `Komunálne voľby ${o.rok}: ${/(ová|á)$/.test(bezTit(o.primator.meno)) ? 'primátorkou' : 'primátorom'} je ${bezTit(o.primator.meno)}`,
      text: o.priebezne ? 'Sčítavajú sa hlasy.' : `Zvolených ${o.poslancov} poslancov.`,
      odkaz: `/${slug}/zastupitelstvo`,
    });
  }
  return out.sort((a, b) => b.datum.localeCompare(a.datum));
}
