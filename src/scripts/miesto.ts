// Fotka, ktorá sa nenačíta, zmizne (namiesto inline onerror – CSP nepovoľuje inline skripty)
if (typeof document !== 'undefined') document.addEventListener('error', (e) => {
  const t = e.target as HTMLElement;
  if (t instanceof HTMLImageElement && t.closest('.mf-foto')) t.closest('.mf-foto')!.remove();
}, true);

// Podrobnosti o mieste z OpenStreetMap pre okno na mape: adresa, otváracie hodiny, web, Wikipédia, fotka.

export type Detail = {
  id?: string; // n123 / w123 / r123
  a?: string; // adresa
  h?: string; // opening_hours (formát OSM)
  w?: string; // web
  wp?: string; // Wikipédia
  f?: string; // fotka (Wikimedia Commons)
  typ?: string;
  op?: string; // prevádzkovateľ
  kap?: string; // kapacita (nabíjacie miesta)
  pop?: string; // popis
};

const esc = (t: string) => t.replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]!);
const DNI = ['Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su'];
const DNI_SK: Record<string, string> = { Mo: 'Po', Tu: 'Ut', We: 'St', Th: 'Št', Fr: 'Pi', Sa: 'So', Su: 'Ne', PH: 'sviatky', SH: 'prázdniny' };

/** Otváracie hodiny v čitateľnej podobe (po slovensky, každé pravidlo na samostatnom riadku). */
export function hodinyText(h: string): string[] {
  if (h.trim() === '24/7') return ['nonstop'];
  return h.split(';').map((r) => r.trim()).filter(Boolean).map((r) =>
    r.replace(/\b(Mo|Tu|We|Th|Fr|Sa|Su|PH|SH)\b/g, (d) => DNI_SK[d])
      .replace(/\b(off|closed)\b/g, 'zatvorené').replace(/24\/7/, 'nonstop').replace(/-/g, '–'));
}

/** Čas v Bratislave: deň v týždni (0 = pondelok) a minúty od polnoci. */
function teraz(): { den: number; min: number } {
  const p = new Intl.DateTimeFormat('en-GB', { timeZone: 'Europe/Bratislava', weekday: 'short', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' }).formatToParts(new Date());
  const g = (k: string) => p.find((x) => x.type === k)!.value;
  return { den: DNI.indexOf(g('weekday').slice(0, 2)), min: Number(g('hour')) * 60 + Number(g('minute')) };
}

const min = (t: string) => { const [h, m] = t.split(':').map(Number); return h * 60 + m; };
const hhmm = (m: number) => `${Math.floor(m / 60) % 24}:${String(m % 60).padStart(2, '0')}`;

/**
 * Je teraz otvorené? Zvláda bežné zápisy („Mo-Fr 08:00-18:00; Sa 09:00-12:00; Su off“).
 * Pri zložitejších pravidlách (mesiace, týždne, východ slnka…) vráti null – vtedy len zobrazíme text.
 */
export function otvorene(h: string): { otvorene: boolean; do?: string; od?: string } | null {
  const s = h.trim();
  if (s === '24/7') return { otvorene: true };
  if (/["|]|sunrise|sunset|dawn|dusk|week|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|\[|\+/.test(s)) return null;
  const rozvrh: [number, number][][] = Array.from({ length: 7 }, () => []); // dni bez pravidla sú podľa OSM zatvorené
  for (const pravidlo of s.split(';').map((r) => r.trim()).filter(Boolean)) {
    const m = pravidlo.match(/^((?:(?:Mo|Tu|We|Th|Fr|Sa|Su|PH)(?:-(?:Mo|Tu|We|Th|Fr|Sa|Su))?,?\s*)+)?\s*(.*)$/);
    if (!m) return null;
    const dniText = (m[1] ?? 'Mo-Su').replace(/\s/g, '');
    const casy = m[2].trim();
    const dni = new Set<number>();
    for (const cast of dniText.split(',').filter(Boolean)) {
      if (cast === 'PH') continue; // sviatky nepoznáme
      const [a, b] = cast.split('-');
      const i = DNI.indexOf(a), j = b ? DNI.indexOf(b) : i;
      if (i < 0 || j < 0) return null;
      for (let k = i; ; k = (k + 1) % 7) { dni.add(k); if (k === j) break; }
    }
    if (dniText === 'PH') continue;
    let intervaly: [number, number][] = [];
    if (/^(off|closed)$/.test(casy)) intervaly = [];
    else {
      for (const iv of casy.split(',')) {
        const t = iv.trim().match(/^(\d{1,2}:\d{2})-(\d{1,2}:\d{2})$/);
        if (!t) return null;
        intervaly.push([min(t[1]), min(t[2])]);
      }
    }
    for (const d of dni) rozvrh[d] = intervaly;
  }
  const { den, min: m } = teraz();
  const dnes = rozvrh[den];
  const vcera = rozvrh[(den + 6) % 7];
  // Interval cez polnoc zo včerajška (napr. 22:00–02:00)
  for (const [a, b] of vcera ?? []) if (b <= a && m < b) return { otvorene: true, do: hhmm(b) };
  for (const [a, b] of dnes) {
    const koniec = b <= a ? b + 1440 : b;
    if (m >= a && m < koniec) return { otvorene: true, do: hhmm(koniec) };
  }
  const dalsi = dnes.map(([a]) => a).filter((a) => a > m).sort((x, y) => x - y)[0];
  return { otvorene: false, od: dalsi != null ? hhmm(dalsi) : undefined };
}

/** HTML okna na mape pre miesto z OSM. */
export function popupMiesta(nazov: string, kategoria: string, d: Detail = {}): string {
  const r: string[] = [];
  if (d.f) {
    r.push(`<a href="${esc(d.f.replace(/\?width=\d+$/, ''))}" target="_blank" rel="noopener" class="mf-foto"><img src="${esc(d.f)}" alt="" loading="lazy"></a>`);
  }
  r.push(`<strong class="mf-nazov" translate="no">${esc(nazov || kategoria)}</strong>`);
  r.push(`<span class="mf-kat">${esc([d.typ || kategoria, d.op && d.op !== nazov ? d.op : ''].filter(Boolean).join(' · '))}</span>`);
  if (d.a) r.push(`<span class="mf-adr" translate="no">${esc(d.a)}</span>`);
  if (d.kap) r.push(`<span>Nabíjacie miesta: ${esc(d.kap)}</span>`);
  if (d.pop) r.push(`<span class="mf-kat">${esc(d.pop)}</span>`);
  if (d.h) {
    const o = otvorene(d.h);
    if (o) r.push(o.otvorene
      ? `<span class="mf-otv ano">● Teraz otvorené${o.do ? ` do ${o.do}` : ''}</span>`
      : `<span class="mf-otv nie">● Teraz zatvorené${o.od ? `, otvára o ${o.od}` : ''}</span>`);
    r.push(`<span class="mf-hod">${hodinyText(d.h).map(esc).join('<br>')}</span>`);
  }
  const odkazy = [
    d.w && `<a href="${esc(d.w)}" target="_blank" rel="noopener">Web</a>`,
    d.wp && `<a href="${esc(d.wp)}" target="_blank" rel="noopener">Wikipédia</a>`,
    d.id && `<a href="https://www.openstreetmap.org/${({ n: 'node', w: 'way', r: 'relation' } as any)[d.id[0]]}/${d.id.slice(1)}" target="_blank" rel="noopener" title="Chýba alebo nesedí údaj? Dá sa opraviť v OpenStreetMap.">OSM</a>`,
  ].filter(Boolean);
  if (odkazy.length) r.push(`<span class="mf-odkazy">${odkazy.join(' · ')}</span>`);
  if (d.f) r.push(`<span class="mf-zdroj">Foto: Wikimedia Commons</span>`);
  return `<div class="mf">${r.join('')}</div>`;
}
