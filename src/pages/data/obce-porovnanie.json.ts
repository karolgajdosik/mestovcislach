// Kľúčové ukazovatele všetkých obcí pre porovnanie dvoch obcí (/porovnaj-obce/) – jeden kompaktný súbor,
// stránka ho načíta v prehliadači. Rovnaké zdroje a výpočty ako profil obce.
import type { APIRoute } from 'astro';
import { kraje, obceKraja, odkaz, posledne, zmena10, nezamInfo, pohybInfo, klimaInfo, rozpocetInfo, odpadInfo, uzemieInfo, wikiInfo, ovzdusieInfo } from '../../lib/obce';

const POLIA: [string, string, string][] = [
  // kľúč, popis, jednotka
  ['obyv', 'Obyvatelia', ''], ['z10', 'Zmena obyvateľov za 10 rokov', '%'], ['vek', 'Priemerný vek', 'r.'], ['deti', 'Deti do 14 rokov', '%'],
  ['sen', 'Ľudia nad 65 rokov', '%'], ['vs', 'Vysokoškolské vzdelanie', '%'], ['nez', 'Miera nezamestnanosti', '%'], ['uc', 'Účasť v komunálnych voľbách 2026', '%'],
  ['hus', 'Hustota obyvateľov', 'na km²'], ['vys', 'Nadmorská výška', 'm'], ['tep', 'Priemerná teplota', '°C'], ['zr', 'Zrážky za rok', 'mm'],
  ['vyd', 'Výdavky obce na obyvateľa', '€'], ['inv', 'Investície obce na obyvateľa', '€'], ['tri', 'Vytriedený komunálny odpad', '%'], ['pm10', 'Prach PM10 (najbližšia stanica)', 'µg/m³'],
];

const r1 = (x: number | null | undefined, d = 1) => (x == null || !Number.isFinite(x) ? null : Math.round(x * 10 ** d) / 10 ** d);
const pct = (t: Record<string, number> | undefined, f: (k: string) => boolean) => {
  const s = t?.Spolu;
  if (!t || !s) return null;
  return (100 * Object.entries(t).filter(([k]) => k !== 'Spolu' && f(k)).reduce((a, [, x]) => a + x, 0)) / s;
};

export const GET: APIRoute = () => {
  const nezI = nezamInfo(), pohI = pohybInfo(), kliI = klimaInfo(), rozI = rozpocetInfo(), odI = odpadInfo(), uzI = uzemieInfo(), wkI = wikiInfo(), ovzI = ovzdusieInfo();
  const obce: (string | number | null)[][] = [];
  for (const k of kraje()) for (const o of obceKraja(k.slug)) {
    const ob = posledne(o.obyvatelia)?.[1] ?? null;
    const uz = (uzI as any)?.obce?.[o.kod];
    const roz = (rozI as any)?.obce?.[o.kod]?.vy;
    const od = (odI as any)?.obce?.[o.kod];
    const odP = od ? od[Object.keys(od).sort().pop()!] : null;
    const kli = (kliI as any)?.obce?.[o.kod];
    const wk = (wkI as any)?.obce?.[o.kod];
    const vyd = roz && ob ? Object.values(roz as Record<string, number>).reduce((a, b) => a + b, 0) / ob : null;
    const h: Record<string, number | null> = {
      obyv: ob, z10: r1(zmena10(o.obyvatelia)), vek: r1((pohI as any)?.obce?.[o.kod]?.vek),
      deti: r1(pct(o.scitanie?.vek, (x) => x === '14 rokov alebo menej')), sen: r1(pct(o.scitanie?.vek, (x) => x === '65 rokov alebo viac')),
      vs: r1(pct(o.scitanie?.vzdelanie, (x) => /vysokoškolsk/i.test(x))), nez: r1((nezI as any)?.obce?.[o.kod]?.pdu),
      uc: r1(o.volby2026?.ucast?.ucast_pct), hus: uz && ob ? Math.round(ob / (uz.ha / 100)) : null, vys: wk?.[1] ?? null,
      tep: kli ? kli[0] : null, zr: kli ? kli[1] : null, vyd: vyd != null ? Math.round(vyd) : null,
      inv: roz?.investicie != null && ob ? Math.round(roz.investicie / ob) : null, tri: r1(odP?.triedene, 0), pm10: (ovzI as any)?.obce?.[o.kod]?.pm10?.[0] ?? null,
    };
    obce.push([o.kod, o.nazov, o.okres, odkaz(o), ...POLIA.map(([key]) => h[key] ?? null)]);
  }
  return new Response(JSON.stringify({ polia: POLIA, roky: { rozpocet: (rozI as any)?.rok ?? null, klima: (kliI as any)?.obdobie ?? null, ovzdusie: (ovzI as any)?.rok ?? null, nez: (nezI as any)?.mesiac ?? null }, obce }), { headers: { 'Content-Type': 'application/json' } });
};
