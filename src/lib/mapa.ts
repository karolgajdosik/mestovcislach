// Mapa mesta = vrstvy z portálu otvorených dát mesta (mapa-<slug>.json, zber_mapa_mesta.py)
// + vrstvy z OpenStreetMap (mapa-osm-<slug>.json, zber_mapa_osm.py), ktoré portál nemá.
import fs from 'node:fs';
import path from 'node:path';

const citaj = (subor: string) => {
  const p = path.join(process.cwd(), 'public', 'data', 'mesta', subor);
  return fs.existsSync(p) ? JSON.parse(fs.readFileSync(p, 'utf-8')) : null;
};
const PORADIE = ['Zdravie', 'Školy', 'Doprava', 'Kultúra a turizmus', 'Šport a voľný čas', 'Príroda', 'Sociálne služby', 'Služby mesta'];
const OSM = 'https://www.openstreetmap.org/copyright';

export const maMapu = (slug: string) => ['mapa-', 'mapa-osm-'].some((p) => fs.existsSync(path.join(process.cwd(), 'public', 'data', 'mesta', `${p}${slug}.json`)));

export function mapaMesta(slug: string) {
  const portal = citaj(`mapa-${slug}.json`);
  const osm = citaj(`mapa-osm-${slug}.json`);
  if (!portal && !osm) return null;
  // zastávky z cestovného poriadku (GTFS) majú prednosť pred OSM – presné linky a počet odchodov
  const pm = path.join(process.cwd(), 'data', 'mesta', `mhd-${slug}.json`);
  const mhd = fs.existsSync(pm) ? JSON.parse(fs.readFileSync(pm, 'utf-8')) : null;
  const zastavkyGtfs = mhd && {
    id: 'mhd-zastavky', nazov: 'Zastávky MHD', skupina: 'Doprava', typ: 'body', zdroj: mhd.zdroj.url,
    body: mhd.zastavky.map((z: any) => [z.lat, z.lon, z.nazov, { Linky: z.linky.join(', '), 'Odchodov za pracovný deň': String(z.odchody) }]),
  };
  const vrstvy = [
    ...(portal?.vrstvy ?? []).map((v: any) => ({ ...v, zdroj: portal.zdroj })),
    ...(zastavkyGtfs ? [zastavkyGtfs] : []),
    ...(osm?.vrstvy ?? []).filter((v: any) => !(zastavkyGtfs && v.id === 'osm-zastavky')).map((v: any) => ({ ...v, zdroj: OSM })),
  ];
  const k = (s: string) => { const i = PORADIE.indexOf(s); return i < 0 ? (s.startsWith('Voľby') ? 99 : 50) : i; };
  vrstvy.sort((a, b) => k(a.skupina) - k(b.skupina)); // stabilné – poradie v skupine zostáva
  return {
    portal: portal?.zdroj ?? null,
    osm: !!osm,
    hranice: portal?.hranice ?? osm?.hranice ?? null,
    hranice_nazov: portal?.hranice ? 'Hranice mestských častí' : 'Hranica mesta',
    vrstvy,
  };
}

/** Má mesto stránku Samospráva (hlasovania, zmluvy a faktúry z portálu mesta – scripts/zber_samosprava_mesta.py)? */
export const maSamospravu = (slug: string) => ['samosprava', 'crz'].some((p) => fs.existsSync(path.join(process.cwd(), 'data', 'mesta', `${p}-${slug}.json`)));

/** Hospodárenie mesta (data/mesta/hospodarenie.json, scripts/zber_hospodarenie.py): účtovné závierky z RÚZ a dlh podľa MF SR. */
export function hospodarenie(slug: string) {
  const p = path.join(process.cwd(), 'data', 'mesta', 'hospodarenie.json');
  if (!fs.existsSync(p)) return null;
  const h = JSON.parse(fs.readFileSync(p, 'utf-8'));
  const roky: Record<string, any> = h.mesta?.[slug]?.roky ?? {};
  const dlh = Object.fromEntries(Object.entries<any>(h.dlh ?? {}).filter(([, v]) => v[slug]).map(([r, v]) => [r, v[slug]]));
  if (!Object.keys(roky).length) return null;
  const rok = Object.keys(roky).sort().pop()!;
  const rokDlh = Object.keys(dlh).sort().pop();
  return { zdroje: h.zdroje, roky, rok, posledny: roky[rok], dlh, rokDlh, dlhPosledny: rokDlh ? dlh[rokDlh] : null };
}
