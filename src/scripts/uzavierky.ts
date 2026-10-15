// Aktuálne uzávierky, rozkopávky a poruchy na cestách v Bratislave – živo zo služieb mesta (ArcGIS, CORS povolené).
// Sťahujeme len vybrané polia: žiadne mená, telefóny, e-maily ani interné poznámky.

const BASE = 'https://services8.arcgis.com/pRlN1m0su5BYaFAS/arcgis/rest/services/';
const ROZKOPAVKY = BASE + 'Rozkopavky_CSO_view/FeatureServer/0';
const PORUCHY = BASE + 'survey123_603d6cb3f848490c818062302c2c43a8_results/FeatureServer/0';

export type Obmedzenie = {
  typ: 'uzavierka' | 'porucha';
  lat: number;
  lon: number;
  nadpis: string;
  adresa: string;
  cast: string;
  druh: string;
  od: number | null;
  do: number | null; // uzávierka: termín finálnej úpravy; porucha: dátum sprejazdnenia
  uzavierka?: string; // úplná / čiastočná / žiadna
  vplyv?: string[];
  kto?: string;
  info?: string;
  planovana?: boolean;
};

export const ZDROJE = { uzavierky: ROZKOPAVKY, poruchy: PORUCHY };

const VPLYV: Record<string, string> = { Auta: 'autá', Chodci: 'chodci', Cyklisti: 'cyklisti', Verejna_doprava: 'MHD' };
const SKRATKY: [RegExp, string][] = [
  [/^Bratislavsk[áa] vod[áa]rensk/i, 'Bratislavská vodárenská spoločnosť'],
  [/^Z[áa]padoslovensk[áa] distrib/i, 'Západoslovenská distribučná'],
  [/^Dopravn[ýy] podnik/i, 'Dopravný podnik Bratislava'],
  [/^SPP/i, 'SPP – distribúcia'],
  [/^Slovak Telekom/i, 'Slovak Telekom'],
  [/^MH Tepl/i, 'MH Teplárenský holding'],
];
const skrat = (s: string) => SKRATKY.find(([r]) => r.test(s))?.[1] ?? s;
// Firma alebo inštitúcia (nie fyzická osoba) – inak investora nezobrazujeme.
const PRAVNICKA = /(s\.\s?r\.\s?o|a\.\s?s\.|spol\.|k\.\s?s\.|v\.\s?o\.\s?s|družstvo|zložka|úrad|mesto|mestská časť|obec|n\.\s?o\.|š\.\s?p\.|ministerstvo|správa|podnik|inc\.|ltd|gmbh)/i;
// Odstráni prípadné telefóny a e-maily z voľného textu.
const bezKontaktov = (s: string) =>
  s.replace(/[\w.+-]+@[\w-]+\.[\w.]+/g, '').replace(/(\+?\d[\d\s/]{7,}\d)/g, '').replace(/\s{2,}/g, ' ').trim();

// Polnoc dnešného dňa v Bratislave ako UTC čas pre dotaz (aby sa zobrazilo aj to, čo končí dnes).
function dnes(posun = 0): string {
  const d = new Date();
  d.setHours(0, 0, 0, 0);
  d.setDate(d.getDate() + posun);
  return d.toISOString().slice(0, 19).replace('T', ' ');
}

async function query(url: string, params: Record<string, string>) {
  const q = new URLSearchParams({ f: 'json', outSR: '4326', returnGeometry: 'true', resultRecordCount: '1000', ...params });
  const r = await fetch(`${url}/query?${q}`);
  const j = await r.json();
  if (j.error) throw new Error(j.error.message);
  return j.features as { attributes: any; geometry?: { x: number; y: number } }[];
}

let domeny: Promise<Record<string, Record<string, string>>> | null = null;
function nazvyDomen() {
  domeny ??= fetch(`${ROZKOPAVKY}?f=json`).then((r) => r.json()).then((j) => {
    const out: Record<string, Record<string, string>> = {};
    for (const f of j.fields ?? []) {
      if (f.domain?.codedValues) out[f.name] = Object.fromEntries(f.domain.codedValues.map((c: any) => [c.code, c.name]));
    }
    return out;
  }).catch(() => ({}));
  return domeny;
}

export async function uzavierky(): Promise<Obmedzenie[]> {
  const t = dnes();
  const [features, dom] = await Promise.all([
    query(ROZKOPAVKY, {
      where: `zobrazovanie='Zobrazovat' AND termin_finalnej_upravy >= TIMESTAMP '${t}' AND datum_vzniku <= TIMESTAMP '${dnes(15)}'`,
      outFields: 'adresa_rozkopavky,mestska_cast,mestska_cast_other,investor,ine_investor,druh_rozkopavky,datum_vzniku,termin_finalnej_upravy,uzavierka,predmet_nadpis,informacie,vplyv_obmedzenia',
    }),
    nazvyDomen(),
  ]);
  const teraz = Date.now();
  return features.filter((f) => f.geometry).map(({ attributes: a, geometry: g }) => {
    let kto = a.investor === 'other' ? (a.ine_investor ?? '') : (dom.investor?.[a.investor] ?? a.investor ?? '');
    if (kto && !PRAVNICKA.test(kto)) kto = '';
    return {
      typ: 'uzavierka' as const,
      lat: g!.y, lon: g!.x,
      nadpis: (a.predmet_nadpis ?? '').trim() || 'Uzávierka',
      adresa: (a.adresa_rozkopavky ?? '').replace(/, \d{3} \d{2}, Bratislava [IV]+, Bratislava$/, ''),
      cast: a.mestska_cast === 'other' ? (a.mestska_cast_other ?? '') : (a.mestska_cast ?? ''),
      druh: (a.druh_rozkopavky ?? '').replace(/_/g, ' ').split(',').join(', '),
      od: a.datum_vzniku, do: a.termin_finalnej_upravy,
      uzavierka: a.uzavierka ?? '',
      vplyv: (a.vplyv_obmedzenia ?? '').split(',').map((v: string) => VPLYV[v]).filter(Boolean),
      kto: skrat(kto.trim()),
      info: a.informacie ? bezKontaktov(a.informacie) : '',
      planovana: a.datum_vzniku > teraz,
    };
  });
}

export async function poruchy(): Promise<Obmedzenie[]> {
  const t = dnes();
  const features = await query(PORUCHY, {
    where: `datum_sprejazdnenia >= TIMESTAMP '${t}' AND datum_vzniku_poruchy <= CURRENT_TIMESTAMP`,
    outFields: 'adresa,mestska_cast,mestska_cast_other,vlastnik_spravca_vedenia,druh_vedenia,datum_vzniku_poruchy,datum_sprejazdnenia,predmet_nadpis',
  });
  return features.filter((f) => f.geometry).map(({ attributes: a, geometry: g }) => ({
    typ: 'porucha' as const,
    lat: g!.y, lon: g!.x,
    nadpis: (a.predmet_nadpis ?? '').trim().replace(/^./, (c: string) => c.toUpperCase()) || 'Porucha',
    adresa: a.adresa ?? '',
    cast: a.mestska_cast === 'other' ? (a.mestska_cast_other ?? '') : (a.mestska_cast ?? ''),
    druh: a.druh_vedenia ?? '',
    od: a.datum_vzniku_poruchy, do: a.datum_sprejazdnenia,
    kto: skrat(a.vlastnik_spravca_vedenia ?? ''),
  }));
}

export const den = (ms: number | null) => (ms ? new Date(ms).toLocaleDateString('sk-SK', { day: 'numeric', month: 'numeric', year: 'numeric' }) : '?');
const esc = (s: string) => s.replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]!);

export function popup(o: Obmedzenie): string {
  const riadky = [`<strong>${esc(o.nadpis)}</strong>`];
  if (o.adresa) riadky.push(esc(o.adresa) + (o.cast ? ` · ${esc(o.cast)}` : ''));
  if (o.typ === 'uzavierka') {
    riadky.push(`${o.planovana ? 'Plánovaná od' : 'Od'} ${den(o.od)} do ${den(o.do)}${o.uzavierka && o.uzavierka !== 'žiadna' ? ` · ${o.uzavierka} uzávierka` : ''}`);
    if (o.vplyv?.length) riadky.push('Obmedzuje: ' + o.vplyv.join(', '));
    if (o.kto) riadky.push('Investor: ' + esc(o.kto));
    if (o.info) riadky.push(`<span style="opacity:.8">${esc(o.info.length > 400 ? o.info.slice(0, 400) + '…' : o.info)}</span>`);
  } else {
    riadky.push(`Porucha od ${den(o.od)}, sprejazdnenie do ${den(o.do)}`);
    if (o.druh) riadky.push('Vedenie: ' + esc(o.druh.toLowerCase()) + (o.kto ? ` (${esc(o.kto)})` : ''));
  }
  return `<div style="max-width:300px">${riadky.join('<br>')}</div>`;
}
