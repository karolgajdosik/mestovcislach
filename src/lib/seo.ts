// Štruktúrované údaje schema.org (JSON-LD) – pomáhajú vyhľadávačom (aj Google Dataset Search) pochopiť obsah stránok.
const WEB = 'https://mestovcislach.sk';

export const webSite = () => ({
  '@type': 'WebSite',
  name: 'mestovčíslach.sk',
  alternateName: 'mestovcislach.sk',
  url: WEB + '/',
  inLanguage: 'sk',
  description: 'Otvorené dáta o slovenských krajských mestách prehľadne a so zdrojmi.',
});

// skratky aj plné názvy („Creative Commons Attribution 4.0 International License“ z portálu Košíc)
const LICENCIE: [RegExp, string][] = [
  [/CC[\s-]?BY[\s-]?NC[\s-]?SA[\s-]?4|Attribution[\s-]+NonCommercial[\s-]+ShareAlike[\s-]+4/i, 'https://creativecommons.org/licenses/by-nc-sa/4.0/'],
  [/CC[\s-]?BY[\s-]?NC[\s-]?4|Attribution[\s-]+NonCommercial[\s-]+4/i, 'https://creativecommons.org/licenses/by-nc/4.0/'],
  [/CC[\s-]?BY[\s-]?SA[\s-]?4|Attribution[\s-]+ShareAlike[\s-]+4/i, 'https://creativecommons.org/licenses/by-sa/4.0/'],
  [/CC[\s-]?BY[\s-]?4|Creative Commons Attribution 4/i, 'https://creativecommons.org/licenses/by/4.0/'],
  [/CC[\s-]?0|public domain/i, 'https://creativecommons.org/publicdomain/zero/1.0/'],
  [/ODbL/i, 'https://opendatacommons.org/licenses/odbl/1-0/'],
];

/** Dátum ako YYYY-MM-DD z ISO reťazca alebo časovej pečiatky (s alebo ms). */
const datum = (v: any): string | null => {
  if (v == null || v === '') return null;
  const n = typeof v === 'number' || /^\d+$/.test(String(v)) ? Number(v) : NaN;
  const d = Number.isNaN(n) ? new Date(String(v)) : new Date(n < 1e12 ? n * 1000 : n);
  return Number.isNaN(d.getTime()) ? null : d.toISOString().slice(0, 10);
};

/** Dataset z katalógu otvorených dát mesta. */
export function dataset(t: any, o: { url: string; json: string; mesto: string; vydavatel: string }) {
  const licencia = LICENCIE.find(([r]) => r.test(String(t.licencia ?? '')))?.[1];
  const popis = String(t.popis || `${t.nazov} – otvorené dáta mesta ${o.mesto}.`);
  return {
    '@type': 'Dataset',
    name: String(t.nazov).slice(0, 200),
    // Google vyžaduje popis s aspoň 50 znakmi
    description: popis.length >= 50 ? popis.slice(0, 5000) : `${popis} Tabuľka s grafom a stiahnutím v CSV, mesto ${o.mesto}.`,
    url: WEB + o.url,
    sameAs: t.zdroj || undefined,
    isAccessibleForFree: true,
    inLanguage: 'sk',
    ...(licencia ? { license: licencia } : {}),
    ...(datum(t.upravene) ? { dateModified: datum(t.upravene) } : {}),
    ...(t.kategoria ? { keywords: [t.kategoria, o.mesto, 'otvorené dáta'] } : { keywords: [o.mesto, 'otvorené dáta'] }),
    spatialCoverage: { '@type': 'Place', name: `${o.mesto}, Slovensko` },
    creator: { '@type': 'Organization', name: o.vydavatel },
    includedInDataCatalog: { '@type': 'DataCatalog', name: `Katalóg dát – ${o.mesto} – mestovčíslach.sk`, url: `${WEB}${o.url.replace(/[^/]+\/?$/, '')}` },
    distribution: [{ '@type': 'DataDownload', encodingFormat: 'application/json', contentUrl: WEB + o.json }],
  };
}
