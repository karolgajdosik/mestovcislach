// Všetky obce SR (scripts/zber_obce.py → data/obce/): zoznam s krajom a okresom, profily obcí, mapa krajov a okresov.
// Krajské mestá (src/mesta.json, aktivne) majú vlastné bohaté stránky – odkazy na ne vedú tam.
import fs from 'node:fs';
import path from 'node:path';
import { MESTA } from '../mesta';

export type ObecZoznam = { kod: string; nazov: string; kraj: string; okres: string; url: string; obyvatelia: number | null; poloha: [number, number] | null; starosta: string | null };
export type Kandidat = { meno: string; strany: string; hlasy: number; podiel: number; zvoleny: boolean };
export type Obec = {
  kod: string; nazov: string; kraj: string; okres: string; slug: string; kraj_slug: string; okres_slug: string; poloha: [number, number] | null;
  poslancov_volenych: number | null; obyvatelia: Record<string, number>; scitanie: Record<string, Record<string, number>>;
  volby2026: null | { ucast: { zapisani: number; volili: number; ucast_pct: number } | null; starosta: Kandidat[]; kandidatov: number;
    poslanci: { meno: string; strany: string; hlasy: number; obvod_c: number }[]; mandaty: { strany: string; mandaty: number }[]; obvodov: number };
};

const citaj = (...p: string[]) => {
  const f = path.join(process.cwd(), ...p);
  try { return fs.existsSync(f) ? JSON.parse(fs.readFileSync(f, 'utf-8')) : null; } catch { return null; }
};
export const slugify = (t: string) => t.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');

let _z: ObecZoznam[] | null = null;
export const zoznam = (): ObecZoznam[] => (_z ??= citaj('data', 'obce', 'zoznam.json')?.obce ?? []);
const _k = new Map<string, Obec[]>();
export const obceKraja = (ks: string): Obec[] => {
  if (!_k.has(ks)) _k.set(ks, citaj('data', 'obce', `${ks}.json`)?.obce ?? []);
  return _k.get(ks)!;
};
let _m: any;
export const mapaSR = () => (_m ??= citaj('data', 'obce', 'mapa.json'));

/** krajské mesto s vlastnými stránkami → jeho adresa (inak null) */
export const webMesta = (nazov: string) => {
  const m = MESTA.find((x) => x.aktivne && x.nazov === nazov);
  return m ? `/${m.slug}` : null;
};
export const odkaz = (o: { nazov: string; url: string }) => webMesta(o.nazov) ?? o.url;
export const posledne = (rad: Record<string, number>): [string, number] | null => {
  const r = Object.keys(rad ?? {}).sort();
  return r.length ? [r[r.length - 1], rad[r[r.length - 1]]] : null;
};
export const zmena10 = (rad: Record<string, number>): number | null => {
  const p = posledne(rad);
  if (!p) return null;
  const pred = rad[String(Number(p[0]) - 10)];
  return pred ? Math.round((1000 * (p[1] - pred)) / pred) / 10 : null;
};

export type Kraj = { nazov: string; slug: string; obyvatelia: number; obci: number; okresy: Okres[] };
export type Okres = { nazov: string; slug: string; kraj: string; kraj_slug: string; obyvatelia: number; obci: number; obce: ObecZoznam[] };
let _kraje: Kraj[] | null = null;
export function kraje(): Kraj[] {
  if (_kraje) return _kraje;
  const k = new Map<string, Kraj>();
  for (const o of zoznam()) {
    const [, ks, os] = o.url.split('/');
    const kr = k.get(ks) ?? { nazov: o.kraj, slug: ks, obyvatelia: 0, obci: 0, okresy: [] };
    k.set(ks, kr);
    let ok = kr.okresy.find((x) => x.slug === os);
    if (!ok) { ok = { nazov: o.okres, slug: os, kraj: o.kraj, kraj_slug: ks, obyvatelia: 0, obci: 0, obce: [] }; kr.okresy.push(ok); }
    ok.obce.push(o); ok.obci++; ok.obyvatelia += o.obyvatelia ?? 0;
    kr.obci++; kr.obyvatelia += o.obyvatelia ?? 0;
  }
  const PORADIE = ['bratislavsky-kraj', 'trnavsky-kraj', 'trenciansky-kraj', 'nitriansky-kraj', 'zilinsky-kraj', 'banskobystricky-kraj', 'presovsky-kraj', 'kosicky-kraj'];
  _kraje = [...k.values()].sort((a, b) => PORADIE.indexOf(a.slug) - PORADIE.indexOf(b.slug));
  for (const kr of _kraje) kr.okresy.sort((a, b) => a.nazov.localeCompare(b.nazov, 'sk'));
  return _kraje;
}

/** vzdialenosť v km */
export const km = (a: [number, number], b: [number, number]) => {
  const r = Math.PI / 180, dLat = (b[0] - a[0]) * r, dLon = (b[1] - a[1]) * r;
  const x = Math.sin(dLat / 2) ** 2 + Math.cos(a[0] * r) * Math.cos(b[0] * r) * Math.sin(dLon / 2) ** 2;
  return 12742 * Math.asin(Math.sqrt(x));
};

// ---- SVG mapa (jednoduchá projekcia – Slovensko je malé) ----
const LON0 = 16.8, LON1 = 22.6, LAT0 = 47.7, LAT1 = 49.65, KX = Math.cos((48.7 * Math.PI) / 180);
export const SIRKA = 1000, VYSKA = Math.round((SIRKA * (LAT1 - LAT0)) / ((LON1 - LON0) * KX));
export const bod = (lon: number, lat: number): [number, number] => [Math.round(((lon - LON0) / (LON1 - LON0)) * SIRKA * 10) / 10, Math.round(((LAT1 - lat) / (LAT1 - LAT0)) * VYSKA * 10) / 10];
export function cesta(geom: any): string {
  const kruh = (r: number[][]) => r.map(([lon, lat], i) => `${i ? 'L' : 'M'}${bod(lon, lat).join(',')}`).join('') + 'Z';
  const poly = (p: number[][][]) => p.map(kruh).join('');
  if (!geom) return '';
  return geom.type === 'Polygon' ? poly(geom.coordinates) : geom.type === 'MultiPolygon' ? geom.coordinates.map(poly).join('') : '';
}
/** okresy kraja – podľa toho, kde leží väčšina obcí okresu */
export function okresyMapy(): { nazov: string; slug: string; kraj_slug: string; d: string }[] {
  const m = mapaSR();
  if (!m) return [];
  const okresy = kraje().flatMap((k) => k.okresy);
  return (m.okresy ?? []).map((x: any) => {
    const n = String(x.nazov).replace(/^okres\s+/i, '');
    const n2 = n.replace(/\s+[IV]+$/, ''); // Bratislava I – V, Košice I – IV = jedno mesto
    const ok = okresy.find((o) => o.nazov === n) ?? okresy.find((o) => slugify(o.nazov) === slugify(n)) ?? okresy.find((o) => o.nazov === n2);
    return ok ? { nazov: ok.nazov, slug: ok.slug, kraj_slug: ok.kraj_slug, d: cesta(x.geom) } : null;
  }).filter(Boolean);
}
export function krajeMapy(): { nazov: string; slug: string; d: string }[] {
  const m = mapaSR();
  return (m?.kraje ?? []).map((x: any) => ({ nazov: x.nazov, slug: slugify(x.nazov), d: cesta(x.geom) }));
}

/** obce s podstránkami (poslanci, kvíz) – od 5 000 obyvateľov */
export const VACSIE_OD = 5000;
export const jeVacsia = (o: Obec) => (posledne(o.obyvatelia)?.[1] ?? 0) >= VACSIE_OD;
export const urlObce = (o: Obec) => `/${o.kraj_slug}/${o.okres_slug}/${o.slug}`;
export const idPoslanca = (meno: string) => meno.split(/[\s,]+/).filter((s) => s && !s.includes('.') && !/^(PhD|MBA|LL|MPH|MPA|DiS|CSc|ArtD|MSc|et)$/i.test(s)).join(' ')
  .normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
/** id poslancov v poradí zoznamu; menovci dostanú -2, -3 … */
export const idsPoslancov = (poslanci: { meno: string }[]) => {
  const v = new Map<string, number>();
  return poslanci.map((p) => { const id = idPoslanca(p.meno); const c = (v.get(id) ?? 0) + 1; v.set(id, c); return c > 1 ? `${id}-${c}` : id; });
};
export const vacsieObce = () => kraje().flatMap((k) => obceKraja(k.slug)).filter((o) => jeVacsia(o) && !webMesta(o.nazov));

export type OtazkaObce = { q: string; moznosti: string[]; spravna: number; vysv: string };
/** Kvíz o obci – otázky z údajov obce a jej okresu (zamiešanie odpovedí v prehliadači). */
export function kvizObce(o: Obec): OtazkaObce[] {
  const out: OtazkaObce[] = [];
  const fmt = (n: number) => n.toLocaleString('sk-SK');
  const des = (n: number) => n.toLocaleString('sk-SK', { maximumFractionDigits: 1 });
  const p = posledne(o.obyvatelia);
  const okres = obceKraja(o.kraj_slug).filter((x) => x.okres_slug === o.okres_slug);
  const zaokr = (n: number) => { const r = n >= 20000 ? 1000 : n >= 5000 ? 100 : 10; return Math.round(n / r) * r; };
  const varianty = (v: number, k: number[], f: (x: number) => string) => {
    const m = [v, ...k.map((x) => v * x)].map(f);
    return [...new Set(m)].length === m.length ? m : null;
  };
  if (p) {
    const m = varianty(p[1], [0.6, 1.45, 2.1], (x) => fmt(zaokr(x)));
    if (m) out.push({ q: `Koľko obyvateľov má ${o.nazov}?`, moznosti: m, spravna: 0, vysv: `K 31. 12. ${p[0]} tu žilo ${fmt(p[1])} obyvateľov.` });
  }
  const z = zmena10(o.obyvatelia);
  if (z != null) {
    const mozn = ['Vzrástol o viac ako 5 %', 'Vzrástol o 0 – 5 %', 'Klesol o 0 – 5 %', 'Klesol o viac ako 5 %'];
    const sp = z > 5 ? 0 : z >= 0 ? 1 : z > -5 ? 2 : 3;
    out.push({ q: `Ako sa za posledných 10 rokov zmenil počet obyvateľov – ${o.nazov}?`, moznosti: mozn, spravna: sp, vysv: `Zmena za 10 rokov: ${z > 0 ? '+' : ''}${des(z)} %.` });
  }
  const sc = o.scitanie;
  const podiel = (t: string, f: (k: string) => boolean) => sc?.[t]?.Spolu ? (100 * Object.entries(sc[t]).filter(([k]) => k !== 'Spolu' && f(k)).reduce((a, [, x]) => a + x, 0)) / sc[t].Spolu : null;
  const sen = podiel('vek', (k) => k === '65 rokov alebo viac');
  if (sen != null) {
    const m = varianty(sen, [0.55, 1.6, 2.2], (x) => `${Math.round(x)} %`);
    if (m) out.push({ q: `Aký podiel obyvateľov – ${o.nazov} – má 65 a viac rokov?`, moznosti: m, spravna: 0, vysv: `Podľa sčítania 2021 je to ${des(sen)} %.` });
  }
  const vs = podiel('vzdelanie', (k) => /vysokoškolsk/i.test(k));
  if (vs != null && vs > 2) {
    const m = varianty(vs, [0.5, 1.7, 2.5], (x) => `${Math.round(x)} %`);
    if (m) out.push({ q: `Koľko percent obyvateľov – ${o.nazov} – má vysokoškolské vzdelanie?`, moznosti: m, spravna: 0, vysv: `Podľa sčítania 2021 je to ${des(vs)} %.` });
  }
  const v = o.volby2026;
  const bt = (m: string) => m.split(/[\s,]+/).filter((s) => s && !s.includes('.') && !/^(PhD|MBA|LL|MPH|MPA|DiS|CSc|ArtD|MSc)$/i.test(s)).join(' ');
  if (v && v.starosta.length >= 2) {
    const k = v.starosta.slice(0, 4);
    out.push({ q: `Kto vyhral voľbu starostu/primátora – ${o.nazov} – v roku 2026?`, moznosti: k.map((x) => bt(x.meno)), spravna: Math.max(0, k.findIndex((x) => x.zvoleny)),
      vysv: `Zvolený(-á) bol(a) ${bt(k.find((x) => x.zvoleny)?.meno ?? k[0].meno)} so ziskom ${des(k.find((x) => x.zvoleny)?.podiel ?? k[0].podiel)} % hlasov.` });
  }
  if (v?.ucast) {
    const m = varianty(v.ucast.ucast_pct, [0.6, 1.35, 1.7], (x) => `${Math.round(Math.min(x, 95))} %`);
    if (m) out.push({ q: `Aká bola účasť v komunálnych voľbách 2026 – ${o.nazov}?`, moznosti: m, spravna: 0, vysv: `Voliť prišlo ${des(v.ucast.ucast_pct)} % voličov.` });
  }
  if (v && v.poslanci.length >= 5) {
    const n = v.poslanci.length;
    out.push({ q: `Koľko poslancov má zastupiteľstvo – ${o.nazov}?`, moznosti: [n, n + 6, Math.max(3, n - 4), n + 12].map(String), spravna: 0, vysv: `V komunálnych voľbách 2026 sa volilo ${n} poslancov.` });
  }
  const vac = okres.filter((x) => posledne(x.obyvatelia)).sort((a, b) => posledne(b.obyvatelia)![1] - posledne(a.obyvatelia)![1]).slice(0, 4);
  if (vac.length === 4) out.push({ q: `Ktorá obec je najväčšia v okrese ${o.okres}?`, moznosti: vac.map((x) => x.nazov), spravna: 0, vysv: `${vac[0].nazov} má ${fmt(posledne(vac[0].obyvatelia)![1])} obyvateľov.` });
  if (o.poloha) {
    const bl = okres.filter((x) => x.kod !== o.kod && x.poloha).map((x) => ({ x, d: km(o.poloha!, x.poloha!) })).sort((a, b) => a.d - b.d);
    if (bl.length >= 8) out.push({ q: `Ktorá obec leží najbližšie k obci ${o.nazov}?`, moznosti: [bl[0], bl[3], bl[5], bl[7]].map((y) => y.x.nazov), spravna: 0, vysv: `${bl[0].x.nazov} je vzdušnou čiarou ${des(bl[0].d)} km.` });
  }
  return out;
}

// Zmluvy z CRZ (scripts/zber_zmluvy_obce.py) a zámery EIA/SEA (scripts/zber_eia_obce.py) – podľa kódu obce.
export type ZmluvyObce = { roky: Record<string, [number, number]>; fo: [number, number]; partneri: [string, number, number][]; najvacsie: [string, string, number, string, string][] };
export type EiaObce = { spolu: number; aktivne: number; zamery: [string, string, string, string, string, string, boolean][] };
let _zm: { od: string; do: string; obce: Record<string, ZmluvyObce> } | null | undefined;
let _eia: { web: string; obce: Record<string, EiaObce> } | null | undefined;
export const zmluvyInfo = () => (_zm === undefined ? (_zm = citaj('data', 'obce', 'zmluvy.json')) : _zm);
export const zmluvyObce = (kod: string): ZmluvyObce | null => zmluvyInfo()?.obce?.[kod] ?? null;
export const eiaWeb = () => (_eia === undefined ? (_eia = citaj('data', 'obce', 'eia.json')) : _eia)?.web ?? 'https://www.enviroportal.sk/eia/detail/';
export const eiaObce = (kod: string): EiaObce | null => { eiaWeb(); return _eia?.obce?.[kod] ?? null; };
export const KAT_EIA: Record<string, string> = { plan: 'plán / koncepcia', odpady: 'odpady', doprava: 'doprava', energia: 'energetika', priemysel: 'priemysel a sklady', byvanie: 'bývanie a ubytovanie', voda: 'voda', obcianska: 'občianska vybavenosť', ine: 'iné' };
