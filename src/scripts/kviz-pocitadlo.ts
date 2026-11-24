// Anonymné počítadlo kvízov (functions/api/kviz.ts): „start“ pri prvej odpovedi, „koniec“ pri výsledku.
// Posiela len adresu kvízu a typ udalosti – nič o hráčovi ani jeho odpovediach.
const odoslane = new Set<string>();

export function zapocitaj(udalost: 'start' | 'koniec', opakovanie = 0) {
  const kluc = `${udalost}:${opakovanie}`;
  if (odoslane.has(kluc)) return;
  odoslane.add(kluc);
  const telo = JSON.stringify({ u: udalost, k: location.pathname });
  try {
    if (navigator.sendBeacon?.('/api/kviz', new Blob([telo], { type: 'application/json' }))) return;
    fetch('/api/kviz', { method: 'POST', body: telo, headers: { 'Content-Type': 'application/json' }, keepalive: true }).catch(() => {});
  } catch { /* počítadlo nie je dôležité */ }
}
