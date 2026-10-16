// Preklad webu do zvoleného jazyka (EN, DE, PL, HU).
// 1. Texty ovládania podľa ručného slovníka (src/i18n/slovnik.ts).
// 2. Ostatné texty strojovo cez /api/preklad (Workers AI); preklady sa ukladajú do localStorage a cache servera.
// Neprekladá sa: [translate="no"] / .notranslate (mená, ulice, názvy miest), skripty, grafy (canvas) a bunky dátových tabuliek.
import { SLOVNIK, PORADIE } from '../i18n/slovnik';

export const jazyk = (): string => document.documentElement.lang || 'sk';
const idx = () => (PORADIE as readonly string[]).indexOf(jazyk());

/** Ručný preklad z dictionára (alebo pôvodný text, ak nie je). */
export function tr(text: string): string {
  const i = idx();
  if (i < 0) return text;
  return SLOVNIK[text.trim()]?.[i] ?? text;
}

const MAX_STROJOVO = 900; // textov na jednu stránku
const PISMENA = /\p{L}{2,}/u;
const PRESKOC = 'script,style,noscript,code,pre,textarea,svg,canvas,select,option,datalist,.notranslate,.leaflet-control-attribution,kbd';
const ATRIBUTY = ['placeholder', 'title', 'aria-label'] as const;

let cache: Record<string, string> = {};
const KLUC = () => `preklad:${jazyk()}`;
function nacitajCache() { try { cache = JSON.parse(localStorage.getItem(KLUC()) ?? '{}'); } catch { cache = {}; } }
let ukladanie = 0;
function ulozCache() {
  clearTimeout(ukladanie);
  ukladanie = window.setTimeout(() => {
    try { localStorage.setItem(KLUC(), JSON.stringify(cache)); }
    catch { cache = {}; try { localStorage.removeItem(KLUC()); } catch { /* plné úložisko */ } }
  }, 400);
}

const prelozene = new WeakMap<Node, string>(); // uzol → text, ktorý sme doň zapísali
let strojovo = 0;
const fronta = new Map<string, { uzly: Set<Text>; atr: Set<[Element, string]> }>();

function zakazane(el: Element | null): boolean {
  if (!el) return true;
  if (el.closest(PRESKOC)) return true;
  // skrytý obsah (zatvorené panely) sa preloží, až keď sa zobrazí
  if (el.closest('[hidden]')) return true;
  const t = el.closest('[translate]');
  if (t && t.getAttribute('translate') === 'no') return true;
  // dátové tabuľky (čísla, mená) – len hlavičky
  if (el.closest('tbody') && !el.closest('th')) return true;
  return false;
}

function zarad(text: string, uzol?: Text, atr?: [Element, string]) {
  const k = text.trim();
  if (k.length > 1200) return;
  let z = fronta.get(k);
  if (!z) { if (strojovo >= MAX_STROJOVO) return; strojovo++; z = { uzly: new Set(), atr: new Set() }; fronta.set(k, z); }
  if (uzol) z.uzly.add(uzol);
  if (atr) z.atr.add(atr);
}

function nahrad(uzol: Text, povodny: string, preklad: string) {
  // zachová medzery okolo textu
  const m = povodny.match(/^(\s*)[\s\S]*?(\s*)$/)!;
  const novy = m[1] + preklad + m[2];
  prelozene.set(uzol, novy);
  if (uzol.nodeValue !== novy) uzol.nodeValue = novy;
}

function spracujText(uzol: Text) {
  const v = uzol.nodeValue ?? '';
  if (prelozene.get(uzol) === v) return;
  if (!PISMENA.test(v) || zakazane(uzol.parentElement)) return;
  const k = v.trim();
  const i = idx();
  const ručne = SLOVNIK[k]?.[i];
  if (ručne) return nahrad(uzol, v, ručne);
  if (cache[k]) return nahrad(uzol, v, cache[k]);
  // texty ďaleko pod obrazovkou preložíme, až keď sa k nim používateľ priblíži
  const el = uzol.parentElement!;
  if (el.getBoundingClientRect().top > innerHeight * 1.5) { sleduj(el); return; }
  zarad(k, uzol);
}

let pozorovatel: IntersectionObserver | null = null;
const sledovane = new WeakSet<Element>();
function sleduj(el: Element) {
  if (sledovane.has(el)) return;
  sledovane.add(el);
  pozorovatel ??= new IntersectionObserver((zaznamy) => {
    let nieco = false;
    for (const z of zaznamy) {
      if (!z.isIntersecting) continue;
      pozorovatel!.unobserve(z.target);
      sledovane.delete(z.target);
      z.target.childNodes.forEach((n) => { if (n.nodeType === Node.TEXT_NODE) { const t = n as Text; const k = (t.nodeValue ?? '').trim(); if (cache[k]) nahrad(t, t.nodeValue!, cache[k]); else if (PISMENA.test(k)) zarad(k, t); } });
      nieco = true;
    }
    if (nieco) odosli();
  }, { rootMargin: '100% 0px' });
  pozorovatel.observe(el);
}

function spracujAtributy(el: Element) {
  if (zakazane(el)) return;
  for (const a of ATRIBUTY) {
    const v = el.getAttribute(a);
    if (!v || !PISMENA.test(v) || (el as any).__prelozene?.[a] === v) continue;
    const ručne = SLOVNIK[v.trim()]?.[idx()] ?? cache[v.trim()];
    if (ručne) { el.setAttribute(a, ručne); ((el as any).__prelozene ??= {})[a] = ručne; }
    else zarad(v, undefined, [el, a]);
  }
}

function prejdi(koren: Node) {
  if (koren.nodeType === Node.TEXT_NODE) { spracujText(koren as Text); return; }
  if (!(koren instanceof Element) && !(koren instanceof DocumentFragment) && koren !== document) return;
  if (koren instanceof Element) spracujAtributy(koren);
  const w = document.createTreeWalker(koren, NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT);
  let n: Node | null;
  while ((n = w.nextNode())) {
    if (n.nodeType === Node.TEXT_NODE) spracujText(n as Text);
    else spracujAtributy(n as Element);
  }
}

let posielam = false;
async function odosli() {
  if (posielam || !fronta.size) return;
  posielam = true;
  try {
    while (fronta.size) {
      const davka = [...fronta.entries()].slice(0, 50);
      davka.forEach(([k]) => fronta.delete(k));
      let preklady: string[] = [];
      try {
        const r = await fetch('/api/preklad', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ jazyk: jazyk(), texty: davka.map(([k]) => k) }) });
        preklady = r.ok ? (await r.json()).preklady ?? [] : [];
      } catch { /* bez prekladu ostane slovenčina */ }
      davka.forEach(([k, z], i) => {
        const p = preklady[i];
        if (!p) return;
        cache[k] = p;
        z.uzly.forEach((u) => { if (u.isConnected && (u.nodeValue ?? '').trim() === k) nahrad(u, u.nodeValue!, p); });
        z.atr.forEach(([el, a]) => { if (el.getAttribute(a)?.trim() === k) { el.setAttribute(a, p); ((el as any).__prelozene ??= {})[a] = p; } });
      });
      ulozCache();
      document.documentElement.classList.remove('prekladam');
    }
  } finally {
    posielam = false;
  }
}

/** Preloží zoznam textov (slovník → cache → /api/preklad) a vráti mapu originál → preklad. */
async function prelozTexty(texty: string[]): Promise<Map<string, string>> {
  const vysl = new Map<string, string>();
  const chyba: string[] = [];
  for (const t of new Set(texty.map((x) => x.trim()).filter((x) => PISMENA.test(x)))) {
    const r = SLOVNIK[t]?.[idx()] ?? cache[t];
    if (r) vysl.set(t, r); else chyba.push(t);
  }
  for (let i = 0; i < chyba.length; i += 50) {
    try {
      const davka = chyba.slice(i, i + 50);
      const r = await fetch('/api/preklad', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ jazyk: jazyk(), texty: davka }) });
      const p: string[] = r.ok ? (await r.json()).preklady ?? [] : [];
      davka.forEach((t, j) => { if (p[j]) { vysl.set(t, p[j]); cache[t] = p[j]; } });
    } catch { /* ostane slovenčina */ }
  }
  ulozCache();
  return vysl;
}

// Grafy Chart.js kreslia text na plátno – preložíme ich popisky, legendu a nadpis priamo v grafe.
async function prelozGrafy() {
  if (!document.querySelector('canvas')) return;
  const { Chart } = await import('chart.js');
  const graf = async (ch: any) => {
    if (ch.$prelozeny) return;
    ch.$prelozeny = true;
    const lab: unknown[] = ch.data?.labels ?? [];
    const ds: any[] = ch.data?.datasets ?? [];
    const titul = ch.options?.plugins?.title;
    const texty = [...lab.filter((x): x is string => typeof x === 'string'), ...ds.map((d) => d.label).filter((x) => typeof x === 'string'), ...(typeof titul?.text === 'string' ? [titul.text] : [])];
    if (!texty.length) return;
    const m = await prelozTexty(texty);
    if (!m.size) return;
    const p = (x: unknown) => (typeof x === 'string' ? m.get(x.trim()) ?? x : x);
    if (ch.data.labels) ch.data.labels = lab.map(p);
    ds.forEach((d) => { if (typeof d.label === 'string') d.label = p(d.label); });
    if (typeof titul?.text === 'string') titul.text = p(titul.text);
    ch.update('none');
  };
  Object.values((Chart as any).instances ?? {}).forEach(graf);
  Chart.register({ id: 'preklad-webu', afterInit: (ch: any) => { setTimeout(() => graf(ch), 0); } });
}

export function spustiPreklad() {
  if (jazyk() === 'sk' || idx() < 0) return;
  nacitajCache();
  prejdi(document.body);
  document.title = tr(document.title);
  odosli();
  prelozGrafy();
  setTimeout(() => document.documentElement.classList.remove('prekladam'), fronta.size ? 2500 : 0);
  // nový obsah (výsledky hľadania, okná na mape, živé údaje…) prekladáme priebežne
  let casovac = 0;
  const cakajuce = new Set<Node>();
  new MutationObserver((zmeny) => {
    for (const z of zmeny) {
      if (z.type === 'characterData') cakajuce.add(z.target);
      else if (z.type === 'attributes') cakajuce.add(z.target);
      else z.addedNodes.forEach((n) => cakajuce.add(n));
    }
    clearTimeout(casovac);
    casovac = window.setTimeout(() => {
      cakajuce.forEach((n) => n.isConnected && prejdi(n));
      cakajuce.clear();
      odosli();
    }, 120);
  }).observe(document.body, { childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: [...ATRIBUTY, 'hidden'] });
}
