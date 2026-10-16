// Živé údaje o Bratislave pre lištu pod hlavičkou a úvodnú stránku.
// Každý zdroj sa v rámci stránky stiahne raz a na 5 minút sa uloží do sessionStorage,
// aby sa pri prechode medzi stránkami nesťahoval znova.
import { uzavierky, poruchy } from './uzavierky';

const PLATNOST = 5 * 60 * 1000;
const bezi: Record<string, Promise<any>> = {};

function zCache<T>(kluc: string, nacitaj: () => Promise<T>): Promise<T> {
  return (bezi[kluc] ??= (async () => {
    try {
      const ulozene = JSON.parse(sessionStorage.getItem('zive:' + kluc) ?? 'null');
      if (ulozene && Date.now() - ulozene.t < PLATNOST) return ulozene.d as T;
    } catch { /* sessionStorage nemusí byť dostupné */ }
    const d = await nacitaj();
    try { sessionStorage.setItem('zive:' + kluc, JSON.stringify({ t: Date.now(), d })); } catch { /* nevadí */ }
    return d;
  })());
}

const json = async (url: string) => {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${url}: ${r.status}`);
  return r.json();
};

// Počasie: Open-Meteo (CC BY 4.0, bez kľúča, CORS povolené)
const POCASIE: Record<number, string> = {
  0: 'jasno', 1: 'prevažne jasno', 2: 'polojasno', 3: 'zamračené', 45: 'hmla', 48: 'hmla s námrazou',
  51: 'mrholenie', 53: 'mrholenie', 55: 'silné mrholenie', 56: 'mrznúce mrholenie', 57: 'mrznúce mrholenie',
  61: 'slabý dážď', 63: 'dážď', 65: 'silný dážď', 66: 'mrznúci dážď', 67: 'mrznúci dážď',
  71: 'slabé sneženie', 73: 'sneženie', 75: 'silné sneženie', 77: 'snehové zrná',
  80: 'prehánky', 81: 'prehánky', 82: 'silné prehánky', 85: 'snehové prehánky', 86: 'snehové prehánky',
  95: 'búrka', 96: 'búrka s krúpami', 99: 'búrka s krúpami',
};
export const pocasie = (stred: [number, number] = [48.1486, 17.1077]) => zCache(`pocasie:${stred.join(',')}`, async () => {
  const d = await json(`https://api.open-meteo.com/v1/forecast?latitude=${stred[0]}&longitude=${stred[1]}&current=temperature_2m,weather_code,wind_speed_10m&daily=temperature_2m_max,temperature_2m_min&forecast_days=1&timezone=Europe%2FBratislava`);
  return {
    teplota: Math.round(d.current.temperature_2m),
    stav: POCASIE[d.current.weather_code] ?? '',
    vietor: Math.round(d.current.wind_speed_10m),
    max: Math.round(d.daily.temperature_2m_max[0]),
    min: Math.round(d.daily.temperature_2m_min[0]),
  };
});

export const vystrahy = (mesto = 'bratislava') => zCache(`vystrahy:${mesto}`, () => json(`/api/vystrahy${mesto === 'bratislava' ? '' : `?mesto=${mesto}`}`));
export const dunaj = (rieka = 'dunaj') => zCache(`rieka:${rieka}`, async () => {
  const d = await json(`/api/dunaj${rieka === 'dunaj' ? '' : `?rieka=${rieka}`}`);
  // pre lištu netreba celé rady meraní
  return { ...d, merane: undefined, predpoved: undefined };
});
export const ovzdusie = (mesto = 'bratislava') => zCache(`ovzdusie:${mesto}`, async () => {
  const d = await json(`/api/ovzdusie${mesto === 'bratislava' ? '' : `?mesto=${mesto}`}`);
  return { ...d, stanice: d.stanice?.map((s: any) => ({ ...s, rad: undefined })) };
});
export const farbaOvzdusia = (stupen?: number) => (stupen === 1 ? 'ok' : stupen === 2 ? 'yellow' : stupen === 3 ? 'orange' : stupen === 4 ? 'red' : '');

export const cesty = () => zCache('cesty', async () => {
  const [u, p] = await Promise.allSettled([uzavierky(), poruchy()]);
  if (u.status === 'rejected' && p.status === 'rejected') throw new Error('ArcGIS nedostupný');
  const uz = u.status === 'fulfilled' ? u.value.filter((o) => !o.planovana) : [];
  return {
    uzavierky: uz.length,
    uplne: uz.filter((o) => o.uzavierka === 'úplná').length,
    poruchy: p.status === 'fulfilled' ? p.value.length : 0,
  };
});

export const stupenDunaja = (d: any): number | undefined => [3, 2, 1].find((s) => d.spa?.[s] && d.stav >= d.spa[s]);

// Krátky názov javu z výstrahy SHMÚ („Výstraha pred hmlou“ → „hmla“)
const JAVY: [RegExp, string][] = [
  [/hml/i, 'hmla'], [/búrk/i, 'búrky'], [/vetr|víchric/i, 'vietor'], [/dažď|zrážk/i, 'dážď'], [/sneh(?!ov)|snežen/i, 'sneženie'],
  [/záve|jazyk/i, 'záveje'], [/poľadovic|námraz/i, 'poľadovica'], [/vysok.*tepl|horúč/i, 'horúčavy'], [/nízk.*tepl|mráz/i, 'mráz'],
  [/povod/i, 'povodeň'], [/lavín/i, 'lavíny'], [/požiar/i, 'požiare'],
];
export const javVystrahy = (udalost: string) => JAVY.find(([r]) => r.test(udalost))?.[1] ?? udalost;
