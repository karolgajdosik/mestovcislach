// Odchody MHD (scripts/zber_odchody.py → data/odchody/<mesto>.json): Bratislava a Prešov z GTFS.
import fs from 'node:fs';
import path from 'node:path';

export type Zastavka = { id: string; n: string; lat: number; lon: number; l: number[] };
export type OdchodyMesta = {
  zdroj: { nazov: string; url: string; licencia: string; upravene: string | null };
  platnost: [string, string];
  linky: [string, string, string, string][]; // názov, druh, farba, farba textu
  smery: string[];
  zastavky: Zastavka[];
  kalendar: Record<string, number[]>; // YYYYMMDD → indexy služieb
  typicke: Record<string, string>; // 1 (pondelok) … 7 → YYYYMMDD
  odchody: Record<string, [number, number, number, string][]>; // linka, smer, služba, časy (delty v minútach)
};

const cache = new Map<string, OdchodyMesta | null>();
export function odchody(slug: string): OdchodyMesta | null {
  if (!cache.has(slug)) {
    const p = path.join(process.cwd(), 'data', 'odchody', `${slug}.json`);
    cache.set(slug, fs.existsSync(p) ? JSON.parse(fs.readFileSync(p, 'utf-8')) : null);
  }
  return cache.get(slug)!;
}
export const maOdchody = (slug: string) => fs.existsSync(path.join(process.cwd(), 'data', 'odchody', `${slug}.json`));
