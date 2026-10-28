// Profily poslancov mestských zastupiteľstiev (zvolení v posledných komunálnych voľbách): meno, strana, obvod, hlasy,
// či mandát obhájili a – ak boli poslancami aj v minulom období – ako hlasovali (dochádzka, zhoda s väčšinou a klubom).
// Hlasovania: Bratislava data/hlasovania-msz.json, Košice data/mesta/samosprava-kosice.json. Žiadne kontakty ani iné údaje.
import fs from 'node:fs';
import path from 'node:path';
import { obdobia, bezTitulov, type Poslanec } from './zastupitelstvo';

export type Hlasovanie = { obdobie: string; klub: string; hlasovani: number; pritomnost: number; zhoda_s_vacsinou: number | null; zhoda_s_klubom: number | null; za: number; proti: number; zdrzal: number };
export type Profil = Poslanec & {
  id: string; rok: string; obdobie: string; poradieVObvode: number | null; vObvode: number;
  obhajil: boolean | null; predHlasy: number | null; hlasovania: Hlasovanie[]; poslancov: number;
};

const citaj = (...p: string[]) => {
  const f = path.join(process.cwd(), ...p);
  try { return fs.existsSync(f) ? JSON.parse(fs.readFileSync(f, 'utf-8')) : null; } catch { return null; }
};
export const idMena = (meno: string) => bezTitulov(meno).normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');

/** hlasovania podľa období – kľúč = meno bez titulov (malými) */
function hlasovaniaMesta(slug: string): Map<string, Hlasovanie[]> {
  const out = new Map<string, Hlasovanie[]>();
  const pridaj = (nazov: string, poslanci: any[]) => {
    for (const p of poslanci ?? []) {
      if (!p?.meno || !p.hlasovani) continue;
      const k = bezTitulov(p.meno);
      const zoz = out.get(k) ?? [];
      zoz.push({ obdobie: nazov, klub: p.klub ?? '', hlasovani: p.hlasovani, pritomnost: p.pritomnost, zhoda_s_vacsinou: p.zhoda_s_vacsinou ?? null, zhoda_s_klubom: p.zhoda_s_klubom ?? null, za: p.za ?? 0, proti: p.proti ?? 0, zdrzal: p.zdrzal ?? 0 });
      out.set(k, zoz);
    }
  };
  if (slug === 'bratislava') {
    const d = citaj('data', 'hlasovania-msz.json');
    for (const o of Object.values<any>(d?.obdobia ?? {})) pridaj(o.nazov, o.poslanci);
  } else {
    const d = citaj('data', 'mesta', `samosprava-${slug}.json`)?.hlasovania;
    for (const [k, o] of Object.entries<any>(d?.obdobia ?? {})) pridaj(o.nazov ?? k, o.poslanci);
  }
  for (const v of out.values()) v.sort((a, b) => b.obdobie.localeCompare(a.obdobie));
  return out;
}

const cache = new Map<string, Profil[]>();
export function profily(slug: string): Profil[] {
  if (cache.has(slug)) return cache.get(slug)!;
  const vsetky = obdobia(slug).filter((o) => !o.priebezne && o.poslancov > 0);
  const n = vsetky[0];
  if (!n) { cache.set(slug, []); return []; }
  const s = vsetky.find((o) => o.rok < n.rok);
  const pred = new Map((s?.poslanci ?? []).map((p) => [bezTitulov(p.meno), p]));
  const hl = hlasovaniaMesta(slug);
  const obdobie = `${n.rok}–${Number(n.rok) + 4}`;
  const videne = new Map<string, number>();
  const out = n.poslanci.map((p) => {
    let id = idMena(p.meno);
    const c = (videne.get(id) ?? 0) + 1;
    videne.set(id, c);
    if (c > 1) id = `${id}-${c}`;
    const vObv = n.poslanci.filter((x) => x.obvod === p.obvod);
    const por = p.obvod ? vObv.slice().sort((a, b) => (b.hlasy ?? 0) - (a.hlasy ?? 0)).findIndex((x) => x === p) + 1 : null;
    const k = bezTitulov(p.meno);
    return {
      ...p, id, rok: n.rok, obdobie, poradieVObvode: por, vObvode: vObv.length, poslancov: n.poslancov,
      obhajil: s ? pred.has(k) : null, predHlasy: pred.get(k)?.hlasy ?? null, hlasovania: hl.get(k) ?? [],
    };
  });
  cache.set(slug, out);
  return out;
}
