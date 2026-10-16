// Témy krajských miest – školy, doprava, bezpečnosť, prostredie, kultúra (data/mesta/temy.json, scripts/zber_mesta_temy.py)
// a dlhodobá kvalita ovzdušia (data/mesta/ovzdusie.json, scripts/zber_ovzdusie_eea.py).
import fs from 'node:fs';
import path from 'node:path';

const citaj = (subor: string) => {
  const p = path.join(process.cwd(), 'data', 'mesta', subor);
  return fs.existsSync(p) ? JSON.parse(fs.readFileSync(p, 'utf-8')) : null;
};
let _temy: any, _ovz: any, _vlaky: any;
export const temy = () => (_temy ??= citaj('temy.json'));
export const ovzdusie = () => (_ovz ??= citaj('ovzdusie.json'));
export const vlaky = () => (_vlaky ??= citaj('vlaky.json'));

export type Rada = Record<string, number>;
/** Ukazovateľ „… – mestá“ (Urban Audit) podľa presného popisu, napr. „Priemerná cena za kúpu bytu za m2“. */
export function ua(slug: string, popis: string): Rada {
  const t = temy();
  if (!t?.mestske) return {};
  const kluc = Object.keys(t.mestske.popisy).find((k) => t.mestske.popisy[k] === popis);
  return (kluc && t.mestske.mesta?.[slug]?.[kluc]) || {};
}
export const posledny = (r: Rada | undefined): [string, number] | null => {
  const roky = Object.keys(r ?? {}).sort();
  return roky.length ? [roky[roky.length - 1], r![roky[roky.length - 1]]] : null;
};

/** Trestné činy kraja na 1 000 obyvateľov podľa rokov. */
export function kriminalita(kraj: string, druh = 'Trestné činy spolu'): Rada {
  const k = temy()?.kriminalita;
  const tc = k?.kraje?.[kraj]?.[druh] ?? {};
  const ob = k?.obyvatelia?.[kraj] ?? {};
  return Object.fromEntries(Object.keys(tc).filter((r) => ob[r]).sort().map((r) => [r, Math.round((10000 * tc[r]) / ob[r]) / 10]));
}

export const maZivot = (slug: string) => !!temy()?.skoly?.[slug] || !!ovzdusie()?.mesta?.[slug];
