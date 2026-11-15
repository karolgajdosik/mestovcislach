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
