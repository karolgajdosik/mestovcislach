// Dodávatelia miest z Centrálneho registra zmlúv (data/zmluvy-mesta/<rok>.json, scripts/zber_zmluvy_mesta.py):
// len právnické osoby s IČO (zmluvy s fyzickými osobami zber ukladá bez mena a IČO). Mestá: tie bez vlastného portálu.
import fs from 'node:fs';
import path from 'node:path';
import { MESTA } from '../mesta';

export type Zmluva = { id: string; d: string; m: string; s: number; pr: string; url: string };
export type Dodavatel = { ico: string; nazov: string; pocet: number; suma: number; posledna: string; mesta: Record<string, number>; zmluvy: Zmluva[] };

let cache: Map<string, Dodavatel> | null = null;
export function dodavatelia(): Map<string, Dodavatel> {
  if (cache) return cache;
  const dir = path.join(process.cwd(), 'data', 'zmluvy-mesta');
  const out = new Map<string, Dodavatel>();
  if (fs.existsSync(dir)) for (const f of fs.readdirSync(dir).filter((x) => /^20\d\d\.json$/.test(x)).sort()) {
    const zz = JSON.parse(fs.readFileSync(path.join(dir, f), 'utf-8'));
    for (const z of Object.values<any>(zz)) {
      if (!z.ico || !z.p) continue;
      const d = out.get(z.ico) ?? { ico: z.ico, nazov: z.p, pocet: 0, suma: 0, posledna: '', mesta: {}, zmluvy: [] };
      d.pocet++; d.suma += z.s || 0; d.mesta[z.m] = (d.mesta[z.m] ?? 0) + 1;
      if (z.d >= d.posledna) { d.posledna = z.d; d.nazov = z.p; }
      d.zmluvy.push({ id: z.id, d: z.d, m: z.m, s: z.s || 0, pr: z.pr || '', url: `https://www.crz.gov.sk/zmluva/${z.id}/` });
      out.set(z.ico, d);
    }
  }
  // Bratislava (magistrát, data.bratislava.sk) a Košice (opendata.kosice.sk): data/zmluvy-ine/<mesto>.json
  const ine = path.join(process.cwd(), 'data', 'zmluvy-ine');
  if (fs.existsSync(ine)) for (const f of fs.readdirSync(ine).filter((x) => x.endsWith('.json'))) {
    for (const z of JSON.parse(fs.readFileSync(path.join(ine, f), 'utf-8')).zmluvy ?? []) {
      if (!z.ico || !z.p) continue;
      const d = out.get(z.ico) ?? { ico: z.ico, nazov: z.p, pocet: 0, suma: 0, posledna: '', mesta: {}, zmluvy: [] };
      d.pocet++; d.suma += z.s || 0; d.mesta[z.m] = (d.mesta[z.m] ?? 0) + 1;
      if (z.d >= d.posledna) { d.posledna = z.d; d.nazov = z.p; }
      d.zmluvy.push({ id: z.id, d: z.d, m: z.m, s: z.s || 0, pr: z.pr || '', url: z.url || '' });
      out.set(z.ico, d);
    }
  }
  for (const d of out.values()) d.zmluvy.sort((a, b) => b.d.localeCompare(a.d));
  cache = out;
  return out;
}
export const nazovMesta = (slug: string) => MESTA.find((m) => m.slug === slug)?.nazov ?? slug;
export const mestaCrz = () => {
  const ine = path.join(process.cwd(), 'data', 'zmluvy-ine');
  const maIne = (s: string) => fs.existsSync(path.join(ine, `${s}.json`));
  return MESTA.filter((m) => m.aktivne && ((m as any).ico && !['bratislava', 'kosice'].includes(m.slug) || maIne(m.slug))).map((m) => m.nazov);
};
