// Profily mestských častí pre mestá, ktoré sa skladajú z mestských častí (Košice; Bratislava má vlastné, bohatšie profily).
// Zdroje: data/mesta/<slug>.json (obyvatelia.casti, casti.*.scitanie/volby, komunalne.*.mestske_casti) a src/lib/stvrte.ts (dostupnosť).
import fs from 'node:fs';
import path from 'node:path';
import { stvrte } from './stvrte';

export type Ukazovatel = { hodnota: number | null; mesto: number | null; poradie: number | null };
export type Volba = { ucast: number | null; ucastPor: number | null; strany: { nazov: string; podiel: number }[] };
export type ProfilCasti = {
  slug: string; n: string;
  pocet: number | null; rok: string | null; rady: [string, number][]; zmena10: Ukazovatel; km2: number | null; hustota: Ukazovatel;
  sklad: Record<'seniori' | 'deti' | 'vs' | 'vlastne' | 'najom', Ukazovatel>;
  narodnost: { nazov: string; podiel: number }[];
  volby: Record<string, Volba & { nazov: string }>;
  komunalne: { rok: string; ucast: number | null; ucastPor: number | null; poradie: { meno: string; strany: string; podiel: number }[] }[];
  dostupnost: { id: string; nazov: string; m: number | null; pocet: number; poradie: number | null }[];
};
export type CastiMesta = { slug: string; casti: ProfilCasti[]; pocet: number; mesto: Record<string, number | null> };

const slugify = (n: string) => n.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
const cache = new Map<string, CastiMesta | null>();
const pct = (t: Record<string, number> | undefined, f: (k: string) => boolean) => {
  if (!t) return null;
  const spolu = t.Spolu || Object.entries(t).filter(([k]) => k !== 'Spolu').reduce((a, [, v]) => a + v, 0);
  if (!spolu) return null;
  return Math.round((1000 * Object.entries(t).filter(([k]) => k !== 'Spolu' && f(k)).reduce((a, [, v]) => a + v, 0)) / spolu) / 10;
};
const SKLAD: Record<string, [string, (k: string) => boolean]> = {
  seniori: ['vek', (k) => k === '65 rokov alebo viac'],
  deti: ['vek', (k) => k === '14 rokov alebo menej'],
  vs: ['vzdelanie', (k) => /vysokoškolsk/i.test(k)],
  vlastne: ['byty_vlastnictvo', (k) => /^(vlastný byt|byt vo vlastnom)/.test(k)],
  najom: ['byty_vlastnictvo', (k) => /nájme|obecný/.test(k)],
};
const KRATKO: Record<string, string> = { lekarne: 'Lekáreň', zastavky: 'Zastávka MHD', ms: 'Materská škola', zs: 'Základná škola', nemocnice: 'Nemocnica / poliklinika', ihriska: 'Detské ihrisko', posty: 'Pošta', urady: 'Úrad', policia: 'Polícia', nabijanie: 'Nabíjanie áut', sport: 'Šport a ihriská', fontany: 'Pitná fontána' };

/** poradie hodnoty medzi všetkými (1 = najvyššia; pri vzdialenostiach 1 = najbližšie) */
function poradie(hodnoty: (number | null)[], v: number | null, vzostupne = false) {
  if (v == null) return null;
  return hodnoty.filter((x) => x != null && (vzostupne ? x < v : x > v)).length + 1;
}

export function castiMesta(slug: string): CastiMesta | null {
  if (cache.has(slug)) return cache.get(slug)!;
  const p = path.join(process.cwd(), 'data', 'mesta', `${slug}.json`);
  const d = fs.existsSync(p) ? JSON.parse(fs.readFileSync(p, 'utf-8')) : null;
  const obyv: Record<string, Record<string, number>> = d?.obyvatelia?.casti ?? {};
  const mena = Object.keys(obyv);
  if (mena.length < 3) { cache.set(slug, null); return null; }
  const st = stvrte(slug);
  const roky = d.obyvatelia.roky as Record<string, number>;
  const posl = Object.keys(roky).sort().at(-1)!;
  const zak = mena.map((n) => {
    const r = obyv[n];
    const rok = Object.keys(r).sort().at(-1) ?? null;
    const pocet = rok ? r[rok] : null;
    const pred = rok ? r[String(Number(rok) - 10)] : null;
    const km2 = st?.casti.find((c) => c.n === n)?.km2 ?? null;
    const sc = d.casti?.[n]?.scitanie ?? {};
    const sklad = Object.fromEntries(Object.entries(SKLAD).map(([k, [tema, f]]) => [k, pct(sc[tema], f)]));
    return { n, rok, pocet, zmena10: pocet && pred ? Math.round((1000 * (pocet / pred - 1))) / 10 : null, km2, hustota: pocet && km2 ? Math.round(pocet / km2) : null, sklad, sc };
  });
  const mestoSklad = Object.fromEntries(Object.entries(SKLAD).map(([k, [tema, f]]) => [k, pct(d.scitanie?.[tema], f)]));
  const mPred = roky[String(Number(posl) - 10)];
  const mesto = {
    pocet: roky[posl], zmena10: mPred ? Math.round(1000 * (roky[posl] / mPred - 1)) / 10 : null,
    km2: st ? Math.round(st.casti.reduce((a, c) => a + c.km2, 0) * 10) / 10 : null,
    ...mestoSklad,
  } as Record<string, number | null>;
  mesto.hustota = mesto.pocet && mesto.km2 ? Math.round(mesto.pocet / mesto.km2) : null;
  const ukaz = (v: number | null, vsetky: (number | null)[], m: number | null): Ukazovatel => ({ hodnota: v, mesto: m, poradie: poradie(vsetky, v) });

  // voľby do NR SR / EP a komunálne podľa častí
  const kom = Object.entries(d.komunalne ?? {}).sort(([a], [b]) => a.localeCompare(b));
  const volbyIds = ['nrsr2023', 'ep2024'];
  const volbaVsetky = (id: string) => mena.map((n) => d.casti?.[n]?.volby?.[id]?.ucast ?? null);
  const komCast = (k: any, n: string) => (k.mestske_casti ?? []).find((x: any) => x.nazov === n);

  const casti: ProfilCasti[] = zak.map((z) => {
    const dost = st?.casti.find((c) => c.n === z.n);
    const nar = z.sc.narodnost as Record<string, number> | undefined;
    const narSpolu = nar ? nar.Spolu || 0 : 0;
    return {
      slug: slugify(z.n), n: z.n, pocet: z.pocet, rok: z.rok,
      rady: Object.entries(obyv[z.n]).filter(([r]) => Number(r) >= 1996).sort(([a], [b]) => a.localeCompare(b)),
      zmena10: ukaz(z.zmena10, zak.map((x) => x.zmena10), mesto.zmena10), km2: z.km2,
      hustota: ukaz(z.hustota, zak.map((x) => x.hustota), mesto.hustota),
      sklad: Object.fromEntries(Object.keys(SKLAD).map((k) => [k, ukaz(z.sklad[k], zak.map((x) => x.sklad[k]), mesto[k])])) as ProfilCasti['sklad'],
      narodnost: narSpolu ? Object.entries(nar!).filter(([k]) => !/^(Spolu|Nezistená)$/.test(k)).map(([nazov, v]) => ({ nazov, podiel: Math.round((1000 * v) / narSpolu) / 10 })).filter((x) => x.podiel >= 1).slice(0, 4) : [],
      volby: Object.fromEntries(volbyIds.filter((id) => d.casti?.[z.n]?.volby?.[id]).map((id) => {
        const v = d.casti[z.n].volby[id];
        return [id, { nazov: d.volby?.[id]?.nazov ?? id, ucast: v.ucast, ucastPor: poradie(volbaVsetky(id), v.ucast), strany: v.strany.slice(0, 5) }];
      })),
      komunalne: kom.map(([rok, k]: [string, any]) => {
        const c = komCast(k, z.n);
        if (!c) return null;
        const vsetky = mena.map((n) => komCast(k, n)?.ucast ?? null);
        const spolu = c.poradie.reduce((a: number, x: any) => a + x.hlasy, 0) || 1;
        return { rok, ucast: c.ucast ?? null, ucastPor: poradie(vsetky, c.ucast ?? null), poradie: c.poradie.slice(0, 4).map((x: any) => ({ meno: x.meno, strany: x.strany, podiel: Math.round((1000 * x.hlasy) / spolu) / 10 })) };
      }).filter(Boolean) as ProfilCasti['komunalne'],
      dostupnost: (st?.kat ?? []).map((k) => ({
        id: k.id, nazov: KRATKO[k.id] ?? k.nazov, m: dost?.d[k.id] ?? null, pocet: dost?.pocet[k.id] ?? 0,
        poradie: poradie(st!.casti.map((c) => c.d[k.id]), dost?.d[k.id] ?? null, true),
      })),
    };
  }).sort((a, b) => (b.pocet ?? 0) - (a.pocet ?? 0));
  const out = { slug, casti, pocet: casti.length, mesto };
  cache.set(slug, out);
  return out;
}
