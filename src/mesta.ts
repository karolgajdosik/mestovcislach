// Mestá webu (spoločná konfigurácia so zberačmi: src/mesta.json).
// Každé mesto má stránky pod /<slug>/… ; plne = celý web mesta (Bratislava),
// ostatné majú prehľad z celoštátnych zdrojov (src/pages/[mesto]/index.astro).
import zoznam from './mesta.json';

export type Mesto = {
  slug: string;
  nazov: string;
  v: string; // „v Bratislave“ – lokál pre texty
  kraj: string;
  nuts3: string;
  okresy: string[];
  stred: [number, number];
  rieka?: string;
  aktivne: boolean;
  plne?: boolean;
  popis?: string;
};

export const MESTA = zoznam as Mesto[];
export const PREDVOLENE = 'bratislava';

/** Mesto podľa cesty (/kosice/… → Košice); na spoločných stránkach predvolené mesto. */
export function mestoZCesty(cesta: string): Mesto {
  const prvy = cesta.split('/').filter(Boolean)[0] ?? '';
  return MESTA.find((m) => m.slug === prvy && m.aktivne) ?? MESTA.find((m) => m.slug === PREDVOLENE)!;
}

/** Je stránka spoločná pre všetky mestá (úvod, porovnanie, súkromie, prístupnosť)? */
export const jeSpolocna = (cesta: string) => !MESTA.some((m) => m.aktivne && (cesta === `/${m.slug}` || cesta.startsWith(`/${m.slug}/`)));
