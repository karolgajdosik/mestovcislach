// Mestá webu. Každé mesto má vlastné stránky pod /<slug>/… ; aktivne = stránky už existujú.
// Kódy (obec podľa ŠÚ SR, okresy NUTS/LAU) sa budú dopĺňať pri zapájaní celoštátnych zdrojov (etapa 2).
export type Mesto = {
  slug: string;
  nazov: string;
  v: string; // „v Bratislave“ – lokál pre texty
  kraj: string;
  aktivne: boolean;
  popis?: string;
};

export const MESTA: Mesto[] = [
  { slug: 'bratislava', nazov: 'Bratislava', v: 'v Bratislave', kraj: 'Bratislavský kraj', aktivne: true, popis: '17 mestských častí, 641 datasetov mesta, živé údaje' },
  { slug: 'trnava', nazov: 'Trnava', v: 'v Trnave', kraj: 'Trnavský kraj', aktivne: false },
  { slug: 'nitra', nazov: 'Nitra', v: 'v Nitre', kraj: 'Nitriansky kraj', aktivne: false },
  { slug: 'trencin', nazov: 'Trenčín', v: 'v Trenčíne', kraj: 'Trenčiansky kraj', aktivne: false },
  { slug: 'zilina', nazov: 'Žilina', v: 'v Žiline', kraj: 'Žilinský kraj', aktivne: false },
  { slug: 'banska-bystrica', nazov: 'Banská Bystrica', v: 'v Banskej Bystrici', kraj: 'Banskobystrický kraj', aktivne: false },
  { slug: 'presov', nazov: 'Prešov', v: 'v Prešove', kraj: 'Prešovský kraj', aktivne: false },
  { slug: 'kosice', nazov: 'Košice', v: 'v Košiciach', kraj: 'Košický kraj', aktivne: false },
];

export const PREDVOLENE = 'bratislava';

/** Mesto podľa cesty (/kosice/doprava → Košice); na spoločných stránkach predvolené mesto. */
export function mestoZCesty(cesta: string): Mesto {
  const prvy = cesta.split('/').filter(Boolean)[0] ?? '';
  return MESTA.find((m) => m.slug === prvy && m.aktivne) ?? MESTA.find((m) => m.slug === PREDVOLENE)!;
}

/** Je stránka spoločná pre všetky mestá (úvod, súkromie, prístupnosť)? */
export const jeSpolocna = (cesta: string) => !MESTA.some((m) => m.aktivne && (cesta === `/${m.slug}` || cesta.startsWith(`/${m.slug}/`)));
