// Stránka obce: zbaľovanie dlhých zoznamov, obsah sekcií (čipy) so zvýraznením aktuálnej sekcie
// a „naposledy pozreté obce“ pre hlavnú stránku (len v tomto prehliadači).

/** Zoznamy a tabuľky s data-zbal="N" ukazujú prvých N položiek (skrýva CSS pri html.js); tu pribudne tlačidlo. */
export function zbalovanie(): void {
  document.querySelectorAll<HTMLElement>('[data-zbal]').forEach((el) => {
    const n = Number(el.dataset.zbal);
    const spolu = el.children.length;
    if (!n || spolu <= n) return;
    const tl = document.createElement('button');
    tl.type = 'button';
    tl.className = 'ob-viac';
    const text = () => (el.classList.contains('rozbalene') ? 'Zobraziť menej' : `Zobraziť všetko (${spolu})`);
    tl.textContent = text();
    tl.setAttribute('aria-expanded', 'false');
    tl.addEventListener('click', () => {
      const bolo = el.classList.contains('rozbalene');
      el.classList.toggle('rozbalene');
      tl.textContent = text();
      tl.setAttribute('aria-expanded', String(!bolo));
      if (bolo) (el.closest('section') ?? el).scrollIntoView({ block: 'start' });
    });
    // za tabuľku (jej obal), nie do tbody
    const za = el.tagName === 'TBODY' ? (el.closest('.ob-obal') ?? el.closest('table')!) : el;
    za.after(tl);
  });
}

/** Obsah stránky: kliknutie posunie na sekciu tak, aby ju neprekryla hlavička ani pás čipov; aktuálna sekcia je zvýraznená. */
export function obsahStranky(): void {
  const nav = document.querySelector<HTMLElement>('.ob-obsah');
  if (!nav) return;
  // čip bez cieľa na stránke (sekcia bez údajov) sa odstráni
  nav.querySelectorAll<HTMLAnchorElement>('a[href^="#"]').forEach((a) => { if (!document.getElementById(a.hash.slice(1))) a.parentElement?.remove(); });
  nav.querySelectorAll('li.sep').forEach((s) => { if (!s.previousElementSibling || s.previousElementSibling.classList.contains('sep') || !s.nextElementSibling) s.remove(); });
  const odkazy = [...nav.querySelectorAll<HTMLAnchorElement>('a[href^="#"]')];
  const ciele = odkazy.map((a) => document.getElementById(a.hash.slice(1))).filter((x): x is HTMLElement => !!x);
  const hlavicka = document.querySelector<HTMLElement>('.top');
  const mobil = () => matchMedia('(max-width: 1099px)').matches;
  odkazy.forEach((a) => a.addEventListener('click', (e) => {
    const ciel = document.getElementById(a.hash.slice(1));
    if (!ciel) return;
    e.preventDefault();
    const y = ciel.getBoundingClientRect().top + scrollY;
    // pri posune nadol sa hlavička na mobile skryje, pri posune nahor ukáže
    const hore = (mobil() && y > scrollY ? 0 : hlavicka?.offsetHeight ?? 0) + nav.offsetHeight + 10;
    scrollTo({ top: Math.max(0, y - hore), behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
    // sekcie mimo obrazovky majú odhadnutú výšku (content-visibility) – po dobehnutí posunu sa poloha doladí
    const dolad = () => {
      const odchylka = ciel.getBoundingClientRect().top - ((hlavicka && !document.documentElement.classList.contains('hlavicka-skryta') ? hlavicka.offsetHeight : 0) + nav.offsetHeight + 10);
      if (Math.abs(odchylka) > 6) scrollBy({ top: odchylka, behavior: 'auto' });
    };
    if ('onscrollend' in window) addEventListener('scrollend', dolad, { once: true }); else setTimeout(dolad, 700);
    history.replaceState(null, '', a.hash);
  }));
  const zoznam = nav.querySelector('ul')!;
  let akt: HTMLAnchorElement | null = null;
  const oznac = () => {
    const hranica = (hlavicka?.getBoundingClientRect().bottom ?? 0) + nav.offsetHeight + 40;
    let i = -1;
    ciele.forEach((c, j) => { if (c.getBoundingClientRect().top <= hranica) i = j; });
    const a = i >= 0 ? odkazy.find((x) => x.hash === `#${ciele[i].id}`) ?? null : null;
    if (a === akt) return;
    akt?.removeAttribute('aria-current');
    akt = a;
    if (a) {
      a.setAttribute('aria-current', 'true');
      const l = a.offsetLeft - zoznam.offsetLeft - (zoznam.clientWidth - a.offsetWidth) / 2;
      zoznam.scrollTo({ left: l, behavior: 'auto' });
    }
  };
  let caka = false;
  addEventListener('scroll', () => { if (!caka) { caka = true; requestAnimationFrame(() => { caka = false; oznac(); }); } }, { passive: true });
  oznac();
}

/** Uloží obec do zoznamu naposledy pozretých (najviac 6) – hlavná stránka ho ukáže pri vyhľadávaní. */
export function ulozPoslednu(nazov: string, url: string, popis: string): void {
  try {
    const zoz: { n: string; u: string; p?: string }[] = JSON.parse(localStorage.getItem('obce-posledne') || '[]');
    const nove = [{ n: nazov, u: url, p: popis }, ...zoz.filter((x) => x.u !== url)].slice(0, 6);
    localStorage.setItem('obce-posledne', JSON.stringify(nove));
  } catch { /* bez úložiska */ }
}

/** Tlačidlo „Moja obec“ – uloží obec pre kartu na úvodnej stránke (len v tomto prehliadači). */
export function mojaObec(): void {
  const h = document.querySelector<HTMLElement>('.ob-hero');
  const tl = document.querySelector<HTMLButtonElement>('.ob-moja');
  if (!h || !tl) return;
  const citaj = () => { try { return JSON.parse(localStorage.getItem('moja-obec') || 'null'); } catch { return null; } };
  const stav = () => {
    const ano = citaj()?.u === h.dataset.url;
    tl.setAttribute('aria-pressed', String(ano));
    tl.textContent = ano ? '★ Moja obec' : '☆ Moja obec';
    tl.title = ano ? 'Uložená ako moja obec – zobrazí sa na úvodnej stránke. Kliknutím zrušíte.' : 'Uložiť ako moju obec – počasie, meniny a odkazy uvidíte na úvodnej stránke';
  };
  tl.addEventListener('click', () => {
    try {
      if (citaj()?.u === h.dataset.url) localStorage.removeItem('moja-obec');
      else localStorage.setItem('moja-obec', JSON.stringify({ n: h.dataset.nazov, u: h.dataset.url, okres: h.dataset.okres, kraj: h.dataset.kraj, poloha: h.dataset.poloha ? JSON.parse(h.dataset.poloha) : undefined }));
    } catch { /* bez úložiska */ }
    stav();
  });
  stav();
}

/** Tlač / PDF: pred tlačou rozbalí zoznamy a rozbaľovače, po tlači vráti pôvodný stav. */
export function tlac(): void {
  document.querySelector('.ob-tlac')?.addEventListener('click', () => print());
  let zatvorene: HTMLDetailsElement[] = [];
  addEventListener('beforeprint', () => {
    zatvorene = [...document.querySelectorAll<HTMLDetailsElement>('main details:not([open])')];
    zatvorene.forEach((d) => (d.open = true));
    document.documentElement.classList.add('tlacim');
  });
  addEventListener('afterprint', () => {
    zatvorene.forEach((d) => (d.open = false));
    document.documentElement.classList.remove('tlacim');
  });
}

/** Pri nadpise každej sekcie tlačidlo na zdieľanie odkazu priamo na ňu (na mobile systémové zdieľanie, inak kopírovanie). */
export function odkazySekcii(): void {
  document.querySelectorAll<HTMLElement>('main section.card[id] > h2:first-child, main .ob-dva[id] section.card > h2:first-child').forEach((h2) => {
    const sek = h2.closest<HTMLElement>('[id]');
    if (!sek?.id || h2.querySelector('.ob-zdielaj')) return;
    const b = document.createElement('button');
    b.type = 'button';
    b.className = 'ob-zdielaj';
    b.title = 'Odkaz na túto časť';
    b.setAttribute('aria-label', `Odkaz na časť ${h2.textContent?.trim() ?? ''}`);
    b.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M10 14a5 5 0 0 0 7 0l3-3a5 5 0 0 0-7-7l-1 1M14 10a5 5 0 0 0-7 0l-3 3a5 5 0 0 0 7 7l1-1"/></svg>';
    b.addEventListener('click', async () => {
      const url = `${location.origin}${location.pathname}#${sek.id}`;
      const nazov = `${document.querySelector('.ob-hero h1')?.textContent?.trim() ?? ''} – ${h2.textContent?.trim() ?? ''}`;
      try {
        if (navigator.share && matchMedia('(pointer: coarse)').matches) await navigator.share({ title: nazov, url });
        else { await navigator.clipboard.writeText(url); b.classList.add('ok'); b.title = 'Odkaz skopírovaný'; setTimeout(() => { b.classList.remove('ok'); b.title = 'Odkaz na túto časť'; }, 1800); }
      } catch { /* zrušené */ }
    });
    h2.append(b);
  });
}
