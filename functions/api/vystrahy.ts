// Cloudflare Pages Function: platné výstrahy SHMÚ pre Bratislavu (cez MeteoAlarm, formát CAP).
// MeteoAlarm nemá CORS, preto ho načítame tu a vrátime len to, čo web potrebuje (cache 10 min).

import MESTA from '../../src/mesta.json';

const FEED = 'https://feeds.meteoalarm.org/api/v1/warnings/feeds-slovakia';
const CACHE_S = 600;
const UROVNE: Record<string, string> = { yellow: '1. stupeň', orange: '2. stupeň', red: '3. stupeň' };

const jeBratislava = (a: any) =>
  /^Bratislava/i.test(a.areaDesc ?? '') || (a.geocode ?? []).some((g: any) => /^SK10\d$/.test(g.value ?? ''));
// Oblasť výstrahy patrí mestu, ak je to jeho okres („Košice I“, „Okres Žilina“)
const vMeste = (okresy: string[]) => (a: any) => okresy.includes(String(a.areaDesc ?? '').replace(/^Okres\s+/i, '').trim());

export function spracuj(feed: any, okresy?: string[]) {
  const patri = okresy ? vMeste(okresy) : jeBratislava;
  const teraz = Date.now();
  const ba: any[] = [];
  const inde = new Set<string>();
  for (const w of feed.warnings ?? []) {
    const alert = w.alert ?? {};
    if (alert.msgType === 'Cancel' || alert.status !== 'Actual') continue;
    for (const info of alert.info ?? []) {
      if (!String(info.language ?? '').startsWith('sk')) continue;
      if (info.expires && Date.parse(info.expires) < teraz) continue;
      const uroven = String((info.parameter ?? []).find((p: any) => p.valueName === 'awareness_level')?.value ?? '');
      const farba = uroven.split(';')[1]?.trim() ?? '';
      if (!UROVNE[farba]) continue; // zelená / bez výstrahy
      const oblasti = (info.area ?? []).filter(patri).map((a: any) => a.areaDesc);
      if (!oblasti.length) {
        inde.add(info.event);
        continue;
      }
      ba.push({
        udalost: info.event,
        nadpis: info.headline ?? '',
        popis: info.description ?? '',
        pokyny: info.instruction ?? '',
        farba,
        stupen: UROVNE[farba],
        od: info.onset ?? info.effective ?? null,
        do: info.expires ?? null,
        oblasti,
      });
    }
  }
  // Rovnaká výstraha pre viac okresov Bratislavy → jedna položka
  const zlucene = new Map<string, any>();
  for (const v of ba) {
    const k = [v.udalost, v.farba, v.od, v.do].join('|');
    const e = zlucene.get(k);
    if (e) e.oblasti = [...new Set([...e.oblasti, ...v.oblasti])];
    else zlucene.set(k, v);
  }
  const poradie = ['red', 'orange', 'yellow'];
  return {
    vystrahy: [...zlucene.values()].sort((a, b) => poradie.indexOf(a.farba) - poradie.indexOf(b.farba) || String(a.od).localeCompare(String(b.od))),
    inde_na_slovensku: [...inde],
    zdroj: { nazov: 'SHMÚ cez MeteoAlarm (EUMETNET)', url: 'https://www.shmu.sk/sk/?page=987' },
    nacitane: new Date().toISOString(),
  };
}

export const onRequestGet = async (ctx: any) => {
  const cache = (caches as any).default as Cache;
  const slug = new URL(ctx.request.url).searchParams.get('mesto') ?? 'bratislava';
  const okresy = slug === 'bratislava' ? undefined : (MESTA as any[]).find((m) => m.slug === slug)?.okresy;
  const kluc = new Request(new URL(`/api/vystrahy?mesto=${slug}`, ctx.request.url).toString());
  const ulozene = await cache.match(kluc);
  if (ulozene) return ulozene;
  try {
    const r = await fetch(FEED, { headers: { 'User-Agent': 'mestovcislach.sk (github.com/karolgajdosik/mestovcislach)' } });
    if (!r.ok) throw new Error(`MeteoAlarm HTTP ${r.status}`);
    const data = spracuj(await r.json(), okresy);
    const odpoved = new Response(JSON.stringify(data), {
      headers: { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': `public, max-age=${CACHE_S}` },
    });
    ctx.waitUntil(cache.put(kluc, odpoved.clone()));
    return odpoved;
  } catch (e: any) {
    return new Response(JSON.stringify({ chyba: String(e?.message ?? e) }), {
      status: 502, headers: { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' },
    });
  }
};
