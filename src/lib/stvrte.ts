// „Ktorá štvrť je pre mňa“: pre každú mestskú časť / štvrť priemerná vzdialenosť k najbližšej lekárni, zastávke, škole…
// Počíta sa pri builde na mriežke bodov (~250 m) v obývanej časti územia (do 700 m od zastávky MHD), aby lesy a polia
// nezhoršovali výsledok veľkých častí. Zdroje bodov: rovnaké ako „Moja adresa“ (src/lib/adresa.ts).
import { citaj, kategorie } from './adresa';
import { mapaMesta } from './mapa';

type Ring = number[][];
type Poly = Ring[];
export type Stvrt = { n: string; km2: number; body: number; d: Record<string, number | null>; pocet: Record<string, number> };
export type StvrteMesta = { druh: string; zdroj: string; priblizne?: boolean; kat: { id: string; nazov: string }[]; casti: Stvrt[]; geo: Record<string, any> };

function casti(slug: string): { druh: string; zdroj: string; priblizne?: boolean; casti: { n: string; g: any }[] } | null {
  if (slug === 'bratislava') {
    const h = citaj('data', 'hranice-bratislava.geojson');
    return h ? { druh: 'mestské časti', zdroj: 'hranice mestských častí', casti: h.features.map((f: any) => ({ n: f.properties.nazov, g: f.geometry })) } : null;
  }
  const h = mapaMesta(slug)?.hranice;
  const mc = h?.features?.filter((f: any) => ['Polygon', 'MultiPolygon'].includes(f.geometry?.type)) ?? [];
  if (mc.length > 1) return { druh: 'mestské časti', zdroj: 'hranice mestských častí', casti: mc.map((f: any) => ({ n: f.properties.n ?? f.properties.nazov, g: f.geometry })) };
  const o = citaj('data', 'mesta', 'casti-osm.json')?.mesta?.[slug];
  return o ? { druh: o.druh, zdroj: 'OpenStreetMap', priblizne: !!o.priblizne, casti: o.casti } : null;
}

const polygony = (g: any): Poly[] => (g.type === 'Polygon' ? [g.coordinates] : g.type === 'MultiPolygon' ? g.coordinates : []);
function vnutri(x: number, y: number, p: Poly) {
  let in_ = false;
  for (const [ri, r] of p.entries()) {
    let c = false;
    for (let i = 0, j = r.length - 1; i < r.length; j = i++) {
      const [xi, yi] = r[i], [xj, yj] = r[j];
      if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) c = !c;
    }
    if (ri === 0) { if (!c) return false; in_ = true; } else if (c) return false; // diera
  }
  return in_;
}

export function stvrte(slug: string): StvrteMesta | null {
  const c = casti(slug);
  const kat = kategorie(slug).filter((k) => k.body.length >= 3);
  if (!c || c.casti.length < 3 || !kat.length) return null;
  const zast = kat.find((k) => k.id === 'zastavky')?.body ?? [];
  const lat0 = (c.casti[0].g.type === 'Polygon' ? c.casti[0].g.coordinates[0][0][1] : c.casti[0].g.coordinates[0][0][0][1]);
  const kx = 111320 * Math.cos((lat0 * Math.PI) / 180), ky = 110540;
  const dist = (lat: number, lon: number, b: number[]) => Math.hypot((lon - b[1]) * kx, (lat - b[0]) * ky);
  const najblizsi = (lat: number, lon: number, body: any[]) => { let m = Infinity; for (const b of body) { const d = dist(lat, lon, b); if (d < m) m = d; } return m; };
  const KROK = 250;
  const out: Stvrt[] = [];
  for (const cast of c.casti) {
    const pp = polygony(cast.g);
    if (!pp.length) continue;
    const vsetky = pp.flatMap((p) => p[0]);
    const lons = vsetky.map((v) => v[0]), lats = vsetky.map((v) => v[1]);
    const [x0, x1, y0, y1] = [Math.min(...lons), Math.max(...lons), Math.min(...lats), Math.max(...lats)];
    const dx = KROK / kx, dy = KROK / ky;
    const mriezka: [number, number][] = [];
    let spolu = 0;
    for (let y = y0 + dy / 2; y < y1; y += dy) for (let x = x0 + dx / 2; x < x1; x += dx) {
      if (!pp.some((p) => vnutri(x, y, p))) continue;
      spolu++;
      if (!zast.length || najblizsi(y, x, zast) <= 700) mriezka.push([y, x]);
    }
    if (!mriezka.length) continue;
    const d: Record<string, number | null> = {}, pocet: Record<string, number> = {};
    for (const k of kat) {
      let s = 0;
      for (const [y, x] of mriezka) s += najblizsi(y, x, k.body);
      d[k.id] = Math.round(s / mriezka.length / 10) * 10;
      pocet[k.id] = k.body.filter((b) => pp.some((p) => vnutri(b[1], b[0], p))).length;
    }
    out.push({ n: cast.n, km2: Math.round((spolu * KROK * KROK) / 1e5) / 10, body: mriezka.length, d, pocet });
  }
  if (out.length < 3) return null;
  // geometria pre mapu na stránke (zjednodušená)
  const geo = Object.fromEntries(c.casti.filter((x) => out.some((o) => o.n === x.n)).map((x) => [x.n, x.g]));
  return { druh: c.druh, zdroj: c.zdroj, priblizne: c.priblizne, kat: kat.map((k) => ({ id: k.id, nazov: k.nazov })), casti: out.sort((a, b) => a.n.localeCompare(b.n, 'sk')), geo };
}
