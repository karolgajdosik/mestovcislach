// Podklady pre týždenník mesta (scripts/odber_email.py tyzdennik): novinky za 7 dní, termíny na mesiac,
// stav rozpočtu na budúci rok a otázka týždňa z kvízu. Len verejné údaje.
import fs from 'node:fs';
import path from 'node:path';
import type { APIRoute } from 'astro';
import { MESTA } from '../../../mesta';
import { novinky, TYPY_NOVINIEK } from '../../../lib/novinky';
import { kalendar } from '../../../lib/kalendar';
import { kviz } from '../../../lib/kviz';

export function getStaticPaths() {
  return MESTA.filter((m) => m.aktivne).map((m) => ({ params: { mesto: m.slug } }));
}
const plus = (d: string, n: number) => new Date(Date.parse(d) + n * 864e5).toISOString().slice(0, 10);

export const GET: APIRoute = ({ params }) => {
  const s = params.mesto!;
  const m = MESTA.find((x) => x.slug === s)!;
  const dnes = new Date().toISOString().slice(0, 10);
  const videne = new Set<string>();
  const nove = novinky(s, 200).filter((x) => x.datum >= plus(dnes, -7) && !videne.has(x.nazov) && !!videne.add(x.nazov))
    .slice(0, 25).map((x) => ({ datum: x.datum, typ: TYPY_NOVINIEK[x.typ], nazov: x.nazov, text: x.text ?? '', odkaz: x.odkaz }));
  const terminy = kalendar(s).filter((u) => (u.do ?? u.od) >= dnes && u.od <= plus(dnes, 31)).map((u) => ({ od: u.od, do: u.do, nazov: u.nazov, odkaz: u.odkaz }));
  // otázka týždňa: rovnaká celý týždeň (podľa čísla týždňa)
  const otazky = kviz(s).filter((q) => q.moznosti.length >= 3);
  const tyzden = Math.floor(Date.parse(dnes) / (7 * 864e5));
  const q = otazky.length ? otazky[tyzden % otazky.length] : null;
  let rozpocet: any = null;
  try {
    const rok = Number(dnes.slice(0, 4)) + 1;
    const rz = JSON.parse(fs.readFileSync(path.join(process.cwd(), 'data', `rozpocty-${rok}.json`), 'utf-8'));
    const dok = rz.mesta?.[s]?.dokumenty ?? [];
    rozpocet = { rok, dokumentov: dok.length, navrh: dok.some((d: any) => d.druh === 'návrh rozpočtu'), odkaz: `/rozpocty-${rok}#${s}` };
  } catch { /* bez údajov */ }
  return new Response(JSON.stringify({
    mesto: m.nazov, v: m.v, slug: s, datum: dnes, novinky: nove, terminy, rozpocet,
    otazka: q && { otazka: q.q, moznosti: q.moznosti, odkaz: `/${s}/kviz` },
  }), { headers: { 'Content-Type': 'application/json' } });
};
