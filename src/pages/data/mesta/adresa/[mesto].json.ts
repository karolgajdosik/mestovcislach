// Podklady pre stránku „Moja adresa“: miesta s polohou podľa kategórií, hranice mestských častí,
// pri Bratislave aj spádové obvody ZŠ, zvolení zástupcovia podľa MČ a stavebné zámery (EIA) podľa MČ.
// Všetko sa počíta až v prehliadači – na server sa poloha neposiela.
import fs from 'node:fs';
import path from 'node:path';
import type { APIRoute } from 'astro';
import { MESTA } from '../../../../mesta';
import { mapaMesta } from '../../../../lib/mapa';

export function getStaticPaths() {
  return MESTA.filter((m) => m.aktivne).map((m) => ({ params: { mesto: m.slug } }));
}

const citaj = (...p: string[]) => {
  const f = path.join(process.cwd(), ...p);
  return fs.existsSync(f) ? JSON.parse(fs.readFileSync(f, 'utf-8')) : null;
};
const r5 = (x: number) => Math.round(x * 1e5) / 1e5;
// zjednodušenie hraníc (každý n-tý bod), aby súbor ostal malý
const zjednodus = (g: any) => {
  const kruh = (k: number[][]) => { const n = Math.max(1, Math.floor(k.length / 300)); return k.filter((_, i) => i % n === 0 || i === k.length - 1).map(([a, b]) => [r5(a), r5(b)]); };
  if (g.type === 'Polygon') return { type: 'Polygon', coordinates: g.coordinates.map(kruh) };
  if (g.type === 'MultiPolygon') return { type: 'MultiPolygon', coordinates: g.coordinates.map((p: number[][][]) => p.map(kruh)) };
  return null;
};

type Kat = { id: string; nazov: string; mapa: string; body: [number, number, string, string?][] };

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

function kategorieMesta(slug: string): Kat[] {
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

function kategorieBA(): Kat[] {
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

// zvolení zástupcovia podľa MČ (Bratislava: starosta MČ a mestskí poslanci z obvodu, len meno a strana)
function zastupcoviaBA() {
  const d = citaj('data', 'komunalne-bratislava.json');
  const v = (d?.volby ?? []).filter((x: any) => x.oso).sort((a: any, b: any) => b.id.localeCompare(a.id))[0];
  if (!v) return null;
  const mc: Record<string, any> = {};
  for (const s of v.oso.starostovia ?? []) {
    const z = s.kandidati?.find((k: any) => k.zvoleny);
    mc[s.nazov] = { starosta: z ? { meno: z.meno, strany: z.strany } : null, poslanci: [] };
  }
  for (const p of v.oso.mestske_zastupitelstvo?.zvoleni ?? []) {
    for (const n of String(p.obvod).split(', ')) (mc[n] ??= { starosta: null, poslanci: [] }).poslanci.push({ meno: p.meno, strany: p.strany });
  }
  return { rok: v.id, priebezne: !!v.spracovanie?.priebezne, mc };
}

function eiaBA() {
  const d = citaj('public', 'data', 'eia.json');
  if (!d) return null;
  const mc: Record<string, any[]> = {};
  for (const z of d.zamery) {
    if (String(z.ukoncene) === 'True' || z.ukoncene === true) continue;
    const casti: string[] = Array.isArray(z.mc) ? z.mc : String(z.mc ?? '').replace(/[[\]']/g, '').split(',').map((s) => s.trim()).filter(Boolean);
    for (const c of casti) (mc[c] ??= []).push({ nazov: String(z.nazov).replace(/^"|"$/g, ''), stav: z.stav, od: z.od, id: z.id });
  }
  for (const k of Object.keys(mc)) mc[k].sort((a, b) => String(b.od).localeCompare(String(a.od)));
  return mc;
}

export const GET: APIRoute = ({ params }) => {
  const m = MESTA.find((x) => x.slug === params.mesto)!;
  const ba = m.slug === 'bratislava';
  const hranice = ba ? citaj('data', 'hranice-bratislava.geojson') : mapaMesta(m.slug)?.hranice;
  const mc = hranice?.features
    ?.filter((f: any) => ['Polygon', 'MultiPolygon'].includes(f.geometry?.type))
    .map((f: any) => ({ n: f.properties?.nazov ?? f.properties?.n, g: zjednodus(f.geometry) }))
    .filter((x: any) => x.n && x.g) ?? [];
  const telo = {
    mesto: m.nazov, slug: m.slug, stred: (m as any).stred,
    kategorie: ba ? kategorieBA() : kategorieMesta(m.slug),
    mestske_casti: mc.length > 1 ? mc : [],
    ...(ba ? { obvody_zs: '/data/obvody-zs-bratislava.geojson', zastupcovia: zastupcoviaBA(), eia_mc: eiaBA() } : {}),
  };
  return new Response(JSON.stringify(telo), { headers: { 'Content-Type': 'application/json' } });
};
