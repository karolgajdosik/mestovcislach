// Service worker mestovcislach.sk: rýchlejšie opakované načítanie a základné stránky aj bez internetu.
// Stránky a dáta: najprv sieť (vždy aktuálne výsledky, napr. počas volieb), pri výpadku uložená verzia.
// Skripty, štýly a obrázky s hašom v názve: z vyrovnávacej pamäte. Ukladá sa len do zariadenia, nič sa neposiela.
const VERZIA = 'v1';
const STRANKY = `stranky-${VERZIA}`, ZDROJE = `zdroje-${VERZIA}`;
const OFFLINE = '/offline/';

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(STRANKY).then((c) => c.addAll(['/', OFFLINE])).then(() => self.skipWaiting()));
});
self.addEventListener('activate', (e) => {
  e.waitUntil(caches.keys().then((k) => Promise.all(k.filter((n) => ![STRANKY, ZDROJE].includes(n)).map((n) => caches.delete(n)))).then(() => self.clients.claim()));
});

const orez = async (nazov, max) => {
  const c = await caches.open(nazov);
  const k = await c.keys();
  for (const r of k.slice(0, Math.max(0, k.length - max))) await c.delete(r);
};

self.addEventListener('fetch', (e) => {
  const r = e.request;
  const u = new URL(r.url);
  if (r.method !== 'GET' || u.origin !== location.origin) return;
  if (/^\/(api|kanal|vlozit)\//.test(u.pathname) || u.pathname === '/sw.js') return;

  // nemenné zdroje (hash v názve) a obrázky: najprv pamäť
  if (u.pathname.startsWith('/_astro/') || u.pathname.startsWith('/img/') || u.pathname.startsWith('/og/') || /\.(woff2?|png|svg|webp|jpg)$/.test(u.pathname)) {
    e.respondWith(caches.open(ZDROJE).then(async (c) => {
      const z = await c.match(r);
      if (z) return z;
      const o = await fetch(r);
      if (o.ok) { c.put(r, o.clone()); orez(ZDROJE, 200); }
      return o;
    }));
    return;
  }

  // stránky a dáta: najprv sieť, pri výpadku uložená verzia (stránky → inak stránka „ste offline“)
  const stranka = r.mode === 'navigate';
  if (stranka || u.pathname.startsWith('/data/')) {
    e.respondWith((async () => {
      try {
        const o = await fetch(r);
        if (o.ok && !u.search) { const c = await caches.open(STRANKY); c.put(r, o.clone()); orez(STRANKY, 60); }
        return o;
      } catch {
        const z = await caches.match(r, { ignoreSearch: true });
        if (z) return z;
        if (stranka) return (await caches.match(OFFLINE)) || Response.error();
        return Response.error();
      }
    })());
  }
});
