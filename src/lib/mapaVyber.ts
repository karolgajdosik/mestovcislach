// Podklady pre kartu „Mapa mesta“ na prehľade mesta: náhľad (hranice + body vo forme SVG, počíta sa pri builde)
// a rýchle odkazy na najpraktickejšie vrstvy mapy (lekárne, zastávky, školy…).
import fs from 'node:fs';
import path from 'node:path';
import { mapaMesta } from './mapa';

export type Polozka = { nazov: string; href: string; pocet?: number; farba: number };
export type RychlaMapa = { href: string; sirka: number; vyska: number; obrysy: string[]; body: [number, number, number][]; polozky: Polozka[] };

// poradie dôležitosti pre bežného človeka; prvá zhoda podľa názvu vrstvy
const PRIORITY: [RegExp, string][] = [
  [/lekár/i, 'Lekárne'],
  [/zastávk/i, 'Zastávky MHD'],
  [/nemocnic|poliklin/i, 'Nemocnice'],
  [/^materské škol/i, 'Škôlky'],
  [/^základné(?! umel)|základné a stredné/i, 'Školy'],
  [/detské ihrisk/i, 'Ihriská'],
  [/^úrady$/i, 'Úrady'],
  [/pošt/i, 'Pošty'],
  [/turistick|hrady, kostoly/i, 'Pamiatky'],
  [/nabíj/i, 'Nabíjanie áut'],
];

// Bratislava má vlastnú mapu s témami (#tema=…)
const BA: [string, string][] = [
  ['tema=cesty', 'Na cestách dnes'],
  ['tema=zdravie', 'Lekárne a zdravie'],
  ['tema=doprava', 'MHD a bicykle'],
  ['skoly', 'Školy a obvody'],
  ['tema=stavby', 'Čo sa stavia'],
  ['horucavy', 'Horúčavy a fontány'],
  ['sport', 'Ihriská a šport'],
  ['tema=kultura', 'Kultúra a pamiatky'],
];

const SIRKA = 320;

/** GeoJSON → zoznam prstencov [[lon, lat], …] */
function prstence(g: any): number[][][] {
  if (!g) return [];
  if (g.type === 'FeatureCollection') return g.features.flatMap((f: any) => prstence(f.geometry));
  if (g.type === 'Feature') return prstence(g.geometry);
  if (g.type === 'Polygon') return g.coordinates;
  if (g.type === 'MultiPolygon') return g.coordinates.flat();
  // hranica z OpenStreetMap je súbor čiar (cesty relácie nie sú pospájané) – kreslíme ich ako obrys bez výplne
  if (g.type === 'MultiLineString') return g.coordinates;
  if (g.type === 'LineString') return [g.coordinates];
  return [];
}

function projekcia(kruhy: number[][][]) {
  const lon = kruhy.flat().map((p) => p[0]), lat = kruhy.flat().map((p) => p[1]);
  const [x0, x1, y0, y1] = [Math.min(...lon), Math.max(...lon), Math.min(...lat), Math.max(...lat)];
  const k = Math.cos(((y0 + y1) / 2) * (Math.PI / 180));
  const m = SIRKA / ((x1 - x0) * k || 1);
  const vyska = Math.round((y1 - y0) * m) || 200;
  const p = (lo: number, la: number): [number, number] => [Math.round((lo - x0) * k * m * 10) / 10, Math.round((y1 - la) * m * 10) / 10];
  const vnutri = (lo: number, la: number) => lo >= x0 && lo <= x1 && la >= y0 && la <= y1;
  return { p, vnutri, vyska };
}

const cesta = (kruh: number[][], p: (a: number, b: number) => [number, number]) => {
  // zjednodušenie: každý n-tý bod, aby SVG ostalo malé
  const krok = Math.max(1, Math.floor(kruh.length / 220));
  const body = kruh.filter((_, i) => i % krok === 0 || i === kruh.length - 1);
  const uzavrety = kruh.length > 3 && kruh[0][0] === kruh[kruh.length - 1][0] && kruh[0][1] === kruh[kruh.length - 1][1];
  return 'M' + body.map((b) => p(b[0], b[1]).join(',')).join('L') + (uzavrety ? 'Z' : '');
};

export function rychlaMapa(slug: string): RychlaMapa | null {
  if (slug === 'bratislava') {
    const f = path.join(process.cwd(), 'data', 'hranice-bratislava.geojson');
    const kruhy = fs.existsSync(f) ? prstence(JSON.parse(fs.readFileSync(f, 'utf-8'))) : [];
    if (!kruhy.length) return null;
    const { p, vyska } = projekcia(kruhy);
    return { href: '/bratislava/mapa', sirka: SIRKA, vyska, obrysy: kruhy.map((k) => cesta(k, p)), body: [],
      polozky: BA.map(([h, n], i) => ({ nazov: n, href: `/bratislava/mapa#${h}`, farba: i })) };
  }
  const d = mapaMesta(slug);
  if (!d) return null;
  const kruhy = prstence(d.hranice);
  const vybrane: any[] = [];
  for (const [r, nazov] of PRIORITY) {
    const v = d.vrstvy.find((x: any) => x.typ === 'body' && x.body?.length && r.test(x.nazov) && !vybrane.some((y) => y.v === x));
    if (v) vybrane.push({ v, nazov });
    if (vybrane.length === 8) break;
  }
  const polozky: Polozka[] = vybrane.map(({ v, nazov }, i) => ({ nazov, href: `/${slug}/mapa#vrstva=${v.id}`, pocet: v.body.length, farba: i }));
  if (!kruhy.length) return { href: `/${slug}/mapa`, sirka: SIRKA, vyska: 0, obrysy: [], body: [], polozky };
  const { p, vnutri, vyska } = projekcia(kruhy);
  // body prvých štyroch vrstiev ako „ochutnávka“ v náhľade (najviac ~500)
  const body: [number, number, number][] = [];
  vybrane.slice(0, 4).forEach(({ v }, i) => {
    const krok = Math.max(1, Math.ceil(v.body.length / 140));
    v.body.forEach((b: any[], j: number) => { if (j % krok === 0 && vnutri(b[1], b[0])) body.push([...p(b[1], b[0]), i]); });
  });
  return { href: `/${slug}/mapa`, sirka: SIRKA, vyska, obrysy: kruhy.map((k) => cesta(k, p)), body, polozky };
}
