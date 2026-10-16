// Kanál upozornení (Atom) pre mestskú časť alebo celé mesto: /kanal/<mestska-cast>.xml
// Bez registrácie a bez osobných údajov – čítačka si kanál stiahne sama.
// Obsah: uzávierky a poruchy na cestách (živo z mesta), zámery v posudzovaní EIA/SEA
// a väčšie zmluvy mestskej časti (Centrálny register zmlúv, len právnické osoby).
// Parameter ?typ=cesty,stavby,zmluvy obmedzí obsah.
import { uzavierky, poruchy, type Obmedzenie } from '../../src/scripts/uzavierky';

const CASTI = ['Staré Mesto', 'Ružinov', 'Vrakuňa', 'Podunajské Biskupice', 'Nové Mesto', 'Rača', 'Vajnory', 'Karlova Ves', 'Dúbravka', 'Lamač',
  'Devín', 'Devínska Nová Ves', 'Záhorská Bystrica', 'Petržalka', 'Jarovce', 'Rusovce', 'Čunovo'];
const slug = (t: string) => t.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/\s+/g, '-');
const WEB = 'https://mestovcislach.sk';
const CACHE_S = 1800;
const MIN_ZMLUVA = 10000;
const DNI = 120; // stavby a zmluvy za posledné 4 mesiace

const x = (s: unknown) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&apos;' })[c]!)
  // znaky nepovolené v XML 1.0
  .replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F]/g, '');
const iso = (d: string | number) => new Date(d).toISOString();
const den = (d: string | number) => new Date(d).toLocaleDateString('sk-SK', { day: 'numeric', month: 'numeric', year: 'numeric', timeZone: 'Europe/Bratislava' });
const eur = (n: number) => `${Math.round(n).toLocaleString('sk-SK')} €`;

type Polozka = { id: string; nazov: string; text: string; odkaz: string; cas: string; kategoria: string };

export const onRequestGet = async (ctx: any) => {
  const { request, env, params } = ctx;
  const kluc = String(params.mc ?? '').replace(/\.(xml|atom|rss)$/, '');
  const mc = CASTI.find((c) => slug(c) === kluc) ?? null;
  if (!mc && kluc !== 'bratislava') return new Response('Neznáma mestská časť', { status: 404, headers: { 'Content-Type': 'text/plain; charset=utf-8' } });

  const url = new URL(request.url);
  const typy = new Set((url.searchParams.get('typ') ?? 'cesty,stavby,zmluvy').split(',').map((t) => t.trim()));
  const cache = (caches as any).default;
  const kluCache = new Request(`${url.origin}/kanal/${kluc}.xml?typ=${[...typy].sort().join(',')}`);
  const ulozene = await cache.match(kluCache);
  if (ulozene) return ulozene;

  const asset = async (cesta: string) => {
    try {
      const r = await env.ASSETS.fetch(new URL(cesta, request.url));
      return r.ok ? await r.json() : null;
    } catch { return null; }
  };
  const hranica = new Date(Date.now() - DNI * 864e5).toISOString().slice(0, 10);
  const polozky: Polozka[] = [];
  const vMc = (cast: string) => !mc || slug(cast ?? '').includes(slug(mc));

  if (typy.has('cesty')) {
    const [u, p] = await Promise.all([uzavierky().catch(() => [] as Obmedzenie[]), poruchy().catch(() => [] as Obmedzenie[])]);
    for (const o of [...u, ...p].filter((o) => vMc(o.cast))) {
      const druh = o.typ === 'porucha' ? 'Porucha' : o.planovana ? 'Plánovaná uzávierka' : o.uzavierka === 'úplná' ? 'Úplná uzávierka' : 'Uzávierka';
      polozky.push({
        id: `cesty-${o.typ}-${o.lat.toFixed(5)}-${o.lon.toFixed(5)}-${o.od ?? ''}`,
        nazov: `${druh}: ${o.adresa || o.nadpis}`,
        text: [o.nadpis, o.druh, o.od ? `od ${den(o.od)}` : '', o.do ? `do ${den(o.do)}` : '', o.vplyv?.length ? `obmedzenie: ${o.vplyv.join(', ')}` : '', o.kto ? `kto: ${o.kto}` : '', mc ? '' : o.cast].filter(Boolean).join(' · '),
        odkaz: `${WEB}/mapa#miesto&${new URLSearchParams({ lat: String(o.lat), lon: String(o.lon), n: o.adresa || o.nadpis })}`,
        cas: iso(o.od ?? Date.now()),
        kategoria: 'Na cestách',
      });
    }
  }
  if (typy.has('stavby')) {
    const eia = await asset('/data/eia.json');
    for (const z of eia?.zamery ?? []) {
      if (z.zmena < hranica || (mc && !z.mc.includes(mc))) continue;
      polozky.push({
        id: `eia-${z.id}-${z.zmena}`,
        nazov: `${z.ukoncene ? 'Posudzovanie skončilo' : z.od && z.od >= hranica && z.od === z.posledny_dokument ? 'Nový zámer' : 'Zámer'}: ${z.nazov}`,
        text: [`Stav: ${z.stav}`, z.mc.join(', '), z.navrhovatel ? `navrhovateľ ${z.navrhovatel}` : '', z.ucel ? z.ucel.slice(0, 400) : ''].filter(Boolean).join(' · '),
        odkaz: `${eia.web}${z.seo}`,
        cas: iso(z.zmena),
        kategoria: 'Čo sa stavia',
      });
    }
  }
  if (typy.has('zmluvy')) {
    for (const c of mc ? [mc] : []) {
      const d = await asset(`/data/zmluvy-mc/${slug(c)}.json`);
      for (const [id, datum, partner, ico, predmet, suma] of d?.zmluvy ?? []) {
        if (datum < hranica || !(suma >= MIN_ZMLUVA)) continue;
        polozky.push({
          id: `crz-${id}`,
          nazov: `Zmluva ${eur(suma)}: ${partner}`,
          text: [predmet, ico ? `IČO ${ico}` : '', `zverejnená ${den(datum)}`].filter(Boolean).join(' · '),
          odkaz: `https://www.crz.gov.sk/zmluva/${id}/`,
          cas: iso(datum),
          kategoria: 'Zmluvy',
        });
      }
    }
  }

  polozky.sort((a, b) => b.cas.localeCompare(a.cas));
  const vyber = polozky.slice(0, 150);
  const nazov = `${mc ?? 'Bratislava'} – upozornenia | mestovcislach.sk`;
  const self = `${WEB}/kanal/${kluc}.xml${url.search}`;
  const xml = `<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xml:lang="sk">
  <title>${x(nazov)}</title>
  <subtitle>${x(`Uzávierky na cestách, čo sa stavia a väčšie zmluvy – ${mc ?? 'celá Bratislava'}. Otvorené dáta, bez registrácie.`)}</subtitle>
  <id>${x(self)}</id>
  <link rel="self" href="${x(self)}"/>
  <link rel="alternate" href="${WEB}/upozornenia"/>
  <updated>${vyber[0]?.cas ?? new Date().toISOString()}</updated>
  <author><name>mestovcislach.sk</name></author>
${vyber.map((p) => `  <entry>
    <id>${x(`${WEB}/kanal/${p.id}`)}</id>
    <title>${x(p.nazov)}</title>
    <link href="${x(p.odkaz)}"/>
    <updated>${p.cas}</updated>
    <category term="${x(p.kategoria)}"/>
    <summary>${x(p.text)}</summary>
  </entry>`).join('\n')}
</feed>
`;
  const odpoved = new Response(xml, {
    headers: { 'Content-Type': 'application/atom+xml; charset=utf-8', 'Cache-Control': `public, max-age=${CACHE_S}`, 'Access-Control-Allow-Origin': '*' },
  });
  ctx.waitUntil?.(cache.put(kluCache, odpoved.clone()));
  return odpoved;
};
