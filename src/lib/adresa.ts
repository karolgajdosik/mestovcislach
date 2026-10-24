// Miesta s polohou podľa kategórií (lekárne, zastávky, školy…) – spoločné pre „Moja adresa“ a „Ktorá štvrť je pre mňa“.
import fs from 'node:fs';
import path from 'node:path';
import { mapaMesta } from './mapa';

export const citaj = (...p: string[]) => {
  const f = path.join(process.cwd(), ...p);
  return fs.existsSync(f) ? JSON.parse(fs.readFileSync(f, 'utf-8')) : null;
};
export const r5 = (x: number) => Math.round(x * 1e5) / 1e5;
// zjednodušenie hraníc (každý n-tý bod), aby súbor ostal malý
export const zjednodus = (g: any) => {
  const kruh = (k: number[][]) => { const n = Math.max(1, Math.floor(k.length / 300)); return k.filter((_, i) => i % n === 0 || i === k.length - 1).map(([a, b]) => [r5(a), r5(b)]); };
  if (g.type === 'Polygon') return { type: 'Polygon', coordinates: g.coordinates.map(kruh) };
  if (g.type === 'MultiPolygon') return { type: 'MultiPolygon', coordinates: g.coordinates.map((p: number[][][]) => p.map(kruh)) };
  return null;
};

export type Kat = { id: string; nazov: string; mapa: string; body: [number, number, string, string?][] };

// ostatné mestá: vrstvy mapy podľa názvu (portál mesta + OpenStreetMap)
const VYBER: [string, RegExp, string][] = [
  ['lekarne', /lekár/i, 'Lekáreň'],
  ['zastavky', /zastávk/i, 'Zastávka MHD'],
  ['ms', /^materské škol/i, 'Materská škola'],
  ['zs', /^základné(?! umel)|základné a stredné/i, 'Základná škola'],
  ['nemocnice', /nemocnic|poliklin/i, 'Nemocnica alebo poliklinika'],
  ['ihriska', /detské ihrisk/i, 'Detské ihrisko'],
  ['posty', /pošt/i, 'Pošta'],
  ['urady', /^úrady$/i, 'Úrad'],
  ['policia', /polícia/i, 'Polícia'],
  ['nabijanie', /nabíj/i, 'Nabíjacia stanica'],
];

export function kategorieMesta(slug: string): Kat[] {
  const d = mapaMesta(slug);
  if (!d) return [];
  const out: Kat[] = [];
  for (const [id, r, nazov] of VYBER) {
    const vs = d.vrstvy.filter((v: any) => v.typ === 'body' && r.test(v.nazov));
    if (!vs.length) continue;
    // ak má mesto vrstvu z portálu aj z OSM, prednosť má portál (je prvý)
    const v = vs[0];
    out.push({ id, nazov, mapa: `/${slug}/mapa#vrstva=${v.id}`, body: v.body.map((b: any[]) => [r5(b[0]), r5(b[1]), b[2], b[3]?.Adresa ?? b[3]?.adresa ?? (b[3]?.Linky ? `linky ${b[3].Linky}` : undefined)]) });
  }
  return out;
}

export function kategorieBA(): Kat[] {
  const out: Kat[] = [];
  const vyb = citaj('public', 'data', 'vybavenost-bratislava.json');
  const skoly = citaj('public', 'data', 'skoly-iedu.json');
  const doprava = citaj('data', 'doprava-bratislava.json');
  const vrstvy = citaj('public', 'data', 'vrstvy-bratislava.json');
  const z = (body: any[], kat: string) => body.filter((b) => b[2] === kat).map((b) => [r5(b[0]), r5(b[1]), b[3], b[4]?.a ?? undefined] as [number, number, string, string?]);
  if (vyb) out.push({ id: 'lekarne', nazov: 'Lekáreň', mapa: '/bratislava/mapa#tema=zdravie', body: z(vyb.body, 'lekarne') });
  if (doprava) out.push({ id: 'zastavky', nazov: 'Zastávka MHD', mapa: '/bratislava/mapa#tema=doprava', body: doprava.zastavky.map((s: any) => [r5(s.lat), r5(s.lon), s.nazov, s.linky?.length ? `linky ${s.linky.filter((l: string) => !l.startsWith('N')).slice(0, 8).join(', ')}` : undefined]) });
  if (skoly) {
    out.push({ id: 'ms', nazov: 'Materská škola', mapa: '/bratislava/mapa#skoly', body: z(skoly.body, 'ms') });
    out.push({ id: 'zs', nazov: 'Základná škola', mapa: '/bratislava/mapa#skoly', body: z(skoly.body, 'zs') });
  }
  if (vyb) out.push({ id: 'nemocnice', nazov: 'Nemocnica alebo poliklinika', mapa: '/bratislava/mapa#tema=zdravie', body: z(vyb.body, 'nemocnice') });
  if (vrstvy) {
    out.push({ id: 'sport', nazov: 'Športovisko alebo ihrisko', mapa: '/bratislava/mapa#sport', body: z(vrstvy.body, 'sportoviska') });
    out.push({ id: 'fontany', nazov: 'Pitná fontána', mapa: '/bratislava/mapa#fontany', body: z(vrstvy.body, 'fontany') });
  }
  if (vyb) out.push({ id: 'nabijanie', nazov: 'Nabíjacia stanica', mapa: '/bratislava/mapa#tema=doprava', body: z(vyb.body, 'nabijanie') });
  return out.filter((k) => k.body.length);
}


export const kategorie = (slug: string): Kat[] => (slug === 'bratislava' ? kategorieBA() : kategorieMesta(slug));
