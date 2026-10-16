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
  const vrstvy = [
    ...(portal?.vrstvy ?? []).map((v: any) => ({ ...v, zdroj: portal.zdroj })),
    ...(osm?.vrstvy ?? []).map((v: any) => ({ ...v, zdroj: OSM })),
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
export const maSamospravu = (slug: string) => fs.existsSync(path.join(process.cwd(), 'data', 'mesta', `samosprava-${slug}.json`));
