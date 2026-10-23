// Grafy na vloženie do iných webov.
// Bežná stránka: pri každej karte s grafom (canvas) tlačidlo „Vložiť“ → kód <iframe> na /vlozit/<stránka>?g=<id>.
// Vložená stránka (html.vlozene, data-vlozit=<id>): ukáže sa len daná karta + odkaz na zdroj.

const WEB = 'https://mestovcislach.sk';
const slug = (s: string) => s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 50);

/** Karty s grafom a ich stabilné id (id prvku, inak z nadpisu karty; pri zhode s poradovým číslom). */
function kartyGrafov(): [HTMLElement, string][] {
  const karty = new Set<HTMLElement>();
  document.querySelectorAll<HTMLCanvasElement>('main canvas').forEach((c) => {
    const k = c.closest<HTMLElement>('section, .card');
    if (k && !k.closest('.mapa-app, .leaflet-container')) karty.add(k);
  });
  const pouzite = new Map<string, number>();
  return [...karty].map((k) => {
    const nadpis = k.querySelector('h2, h3')?.textContent?.trim() ?? 'graf';
    let id = k.id || 'g-' + slug(nadpis);
    const n = pouzite.get(id) ?? 0;
    pouzite.set(id, n + 1);
    if (n) id += '-' + (n + 1);
    return [k, id];
  });
}

function vlozenyRezim(id: string) {
  const ciel = kartyGrafov().find(([, i]) => i === id)?.[0];
  const main = document.querySelector('main');
  if (!ciel || !main) {
    if (main) main.innerHTML = `<p style="padding:16px">Graf sa nenašiel. <a href="${location.pathname.replace(/^\/vlozit/, '')}">Otvoriť stránku na mestovcislach.sk</a></p>`;
    return;
  }
  // skryť všetko okrem cesty od <main> k cieľovej karte
  let el: HTMLElement = ciel;
  while (el && el !== main) {
    const rodic = el.parentElement!;
    [...rodic.children].forEach((s) => { if (s !== el && s instanceof HTMLElement && s.tagName !== 'SCRIPT') s.style.display = 'none'; });
    el = rodic;
  }
  ciel.querySelectorAll('.vlozit-tl').forEach((b) => b.remove());
  const povodna = location.pathname.replace(/^\/vlozit/, '') || '/';
  const zdroj = document.createElement('p');
  zdroj.className = 'vlozit-zdroj';
  zdroj.innerHTML = `<a href="${WEB}${povodna}" target="_blank" rel="noopener">mesto<b>v</b>číslach.sk</a> – otvorené dáta o slovenských mestách`;
  ciel.after(zdroj);
}

function tlacidla() {
  const karty = kartyGrafov();
  if (!karty.length) return;
  let dialog: HTMLDialogElement | null = null;
  const otvor = (karta: HTMLElement, id: string) => {
    const nadpis = karta.querySelector('h2, h3')?.textContent?.trim() ?? 'Graf';
    const vyska = Math.min(900, Math.max(320, Math.round(karta.getBoundingClientRect().height) + 70));
    const cesta = location.pathname.replace(/\/$/, '');
    const kod = `<iframe src="${WEB}/vlozit${cesta}?g=${id}" title="${nadpis.replace(/"/g, '&quot;')} – mestovcislach.sk" width="100%" height="${vyska}" style="border:0;max-width:820px" loading="lazy"></iframe>`;
    if (!dialog) {
      dialog = document.createElement('dialog');
      dialog.className = 'vlozit-dialog';
      dialog.innerHTML = `<h2>Vložiť graf na web</h2><p class="vd-nadpis"></p><label for="vd-kod">Skopírujte kód a vložte ho do svojej stránky:</label>
        <textarea id="vd-kod" readonly rows="4"></textarea>
        <p class="vd-pozn">Graf sa bude sám aktualizovať. Uveďte, prosím, zdroj – odkaz je priamo pod grafom. Údaje sú otvorené (zdroj je uvedený pri grafe).</p>
        <div class="vd-akcie"><button type="button" class="vd-kopiruj">Kopírovať kód</button><button type="button" class="vd-zavriet">Zavrieť</button></div>`;
      document.body.append(dialog);
      dialog.querySelector('.vd-zavriet')!.addEventListener('click', () => dialog!.close());
      dialog.addEventListener('click', (e) => { if (e.target === dialog) dialog!.close(); });
      dialog.querySelector('.vd-kopiruj')!.addEventListener('click', async (e) => {
        const ta = dialog!.querySelector('textarea')!;
        try { await navigator.clipboard.writeText(ta.value); } catch { ta.select(); document.execCommand('copy'); }
        (e.target as HTMLButtonElement).textContent = 'Skopírované ✓';
      });
    }
    dialog.querySelector('.vd-nadpis')!.textContent = nadpis;
    dialog.querySelector('textarea')!.value = kod;
    (dialog.querySelector('.vd-kopiruj') as HTMLButtonElement).textContent = 'Kopírovať kód';
    dialog.showModal();
    dialog.querySelector('textarea')!.select();
  };
  for (const [karta, id] of karty) {
    const b = document.createElement('button');
    b.type = 'button';
    b.className = 'vlozit-tl';
    b.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m8 7-5 5 5 5M16 7l5 5-5 5"/></svg><span>Vložiť</span>';
    b.setAttribute('aria-label', `Vložiť graf na web: ${karta.querySelector('h2, h3')?.textContent?.trim() ?? ''}`);
    b.addEventListener('click', () => otvor(karta, id));
    karta.append(b);
  }
}

export function grafyNaVlozenie() {
  const id = document.documentElement.getAttribute('data-vlozit');
  const spusti = () => (id ? vlozenyRezim(id) : tlacidla());
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', spusti); else spusti();
}
