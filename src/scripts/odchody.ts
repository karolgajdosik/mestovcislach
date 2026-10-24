// Najbližšie odchody MHD v prehliadači: z kalendára služieb (index mesta) a odchodov zo zastávky.
// Údaje: /data/odchody/<mesto>.json (zastávky, linky, kalendár) a /data/odchody/<mesto>/<id>.json (odchody).

export type Index = {
  zdroj: { nazov: string; url: string; licencia: string; upravene: string | null };
  platnost: [string, string];
  linky: [string, string, string, string][];
  zastavky: { id: string; n: string; lat: number; lon: number; l: number[] }[];
  kalendar: Record<string, number[]>;
  typicke: Record<string, string>;
};
export type Zast = { smery: string[]; odchody: [number, number, number, string][] };
export type Odchod = { min: number; linka: number; smer: string; za: number; nahradny: boolean };

const indexy = new Map<string, Promise<Index>>();
export const nacitajIndex = (slug: string) => {
  if (!indexy.has(slug)) indexy.set(slug, fetch(`/data/odchody/${slug}.json`).then((r) => { if (!r.ok) throw new Error(String(r.status)); return r.json(); }));
  return indexy.get(slug)!;
};
const zastavky = new Map<string, Promise<Zast>>();
export const nacitajZastavku = (slug: string, id: string) => {
  const k = `${slug}/${id}`;
  if (!zastavky.has(k)) zastavky.set(k, fetch(`/data/odchody/${slug}/${id}.json`).then((r) => { if (!r.ok) throw new Error(String(r.status)); return r.json(); }));
  return zastavky.get(k)!;
};

// čas v Bratislave (aj keď má zariadenie iné časové pásmo)
export function teraz(): { datum: Date; min: number } {
  const p = Object.fromEntries(new Intl.DateTimeFormat('en-GB', { timeZone: 'Europe/Bratislava', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' }).formatToParts(new Date()).map((x) => [x.type, x.value]));
  return { datum: new Date(Date.UTC(+p.year, +p.month - 1, +p.day)), min: +p.hour * 60 + +p.minute };
}
const kluc = (d: Date) => d.toISOString().slice(0, 10).replace(/-/g, '');
const posun = (d: Date, n: number) => new Date(d.getTime() + n * 864e5);

// sviatky (len pre náhradný poriadok mimo platnosti GTFS; v platnosti rozhoduje kalendár dopravcu)
function sviatok(d: Date) {
  const md = d.toISOString().slice(5, 10);
  if (['01-01', '01-06', '05-01', '05-08', '07-05', '08-29', '09-15', '11-01', '12-24', '12-25', '12-26'].includes(md)) return true;
  const y = d.getUTCFullYear(), a = y % 19, b = Math.floor(y / 100), c = y % 100, dd = Math.floor(b / 4), e = b % 4, f = Math.floor((b + 8) / 25), g = Math.floor((b - f + 1) / 3);
  const h = (19 * a + b - dd - g + 15) % 30, i = Math.floor(c / 4), k = c % 4, l = (32 + 2 * e + 2 * i - h - k) % 7, m = Math.floor((a + 11 * h + 22 * l) / 451);
  const mes = Math.floor((h + l - 7 * m + 114) / 31), den = ((h + l - 7 * m + 114) % 31) + 1;
  const vn = Date.UTC(y, mes - 1, den);
  return d.getTime() === vn - 2 * 864e5 || d.getTime() === vn + 864e5;
}

/** služby, ktoré premávajú v daný deň; nahradny = deň mimo platnosti cestovného poriadku */
export function sluzby(ix: Index, d: Date): { s: Set<number>; nahradny: boolean } {
  const k = kluc(d);
  if (ix.kalendar[k]) return { s: new Set(ix.kalendar[k]), nahradny: false };
  const w = sviatok(d) ? 7 : ((d.getUTCDay() + 6) % 7) + 1;
  return { s: new Set(ix.kalendar[ix.typicke[String(w)]] ?? []), nahradny: true };
}

/** najbližšie odchody od teraz (vrátane spojov po polnoci z predchádzajúceho dňa) */
export function dalsie(ix: Index, z: Zast, n = 10, filter?: (linka: number) => boolean): Odchod[] {
  const { datum, min } = teraz();
  const out: Odchod[] = [];
  // včera (časy nad 24:00), dnes, zajtra
  for (const [dPosun, odpocet] of [[-1, 1440], [0, 0], [1, -1440]] as const) {
    const den = posun(datum, dPosun);
    const { s, nahradny } = sluzby(ix, den);
    for (const [l, h, sv, c] of z.odchody) {
      if (!s.has(sv) || (filter && !filter(l))) continue;
      let t = 0;
      for (const x of c.split(',')) {
        t += +x;
        const m = t - odpocet;
        if (m >= min && m < min + 24 * 60) out.push({ min: m, linka: l, smer: z.smery[h], za: m - min, nahradny });
      }
    }
  }
  out.sort((a, b) => a.min - b.min || a.linka - b.linka);
  return out.slice(0, n);
}

export const hodina = (m: number) => { const x = ((m % 1440) + 1440) % 1440; return `${Math.floor(x / 60)}:${String(x % 60).padStart(2, '0')}`; };
export const vzdialenost = (a: number, b: number, c: number, d: number) => {
  const R = 6371000, r = Math.PI / 180;
  const x = Math.sin(((c - a) * r) / 2) ** 2 + Math.cos(a * r) * Math.cos(c * r) * Math.sin(((d - b) * r) / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(x));
};
const hx = (s: unknown) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]!));
export { hx };

const jas = (h: string) => {
  const c = h.replace('#', '').match(/../g)!.map((x) => parseInt(x, 16) / 255).map((v) => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4));
  return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
};
const kontrast = (a: string, b: string) => { try { const [x, y] = [jas(a), jas(b)].sort((p, q) => q - p); return (x + 0.05) / (y + 0.05); } catch { return 21; } };
const tmavsia = (h: string, k: number) => '#' + h.replace('#', '').match(/../g)!.map((x) => { const v = parseInt(x, 16); return Math.round(Math.max(0, Math.min(255, k < 0 ? v * (1 + k) : v + (255 - v) * k))).toString(16).padStart(2, '0'); }).join('');

/** značka linky (farba z GTFS, inak podľa druhu) */
export function znacka(ix: Index, l: number) {
  const [n, druh, farba, text] = ix.linky[l] ?? ['?', 'autobus', '', ''];
  let bg = farba ? `#${farba}` : druh === 'električka' ? '#c62828' : druh === 'trolejbus' ? '#2e7d32' : '#1565c0';
  const fg = text ? `#${text}` : '#ffffff';
  // farby dopravcu stmaviť, ak by text nebol dosť čitateľný (kontrast aspoň 4,5 : 1)
  for (let i = 0; i < 6 && kontrast(bg, fg) < 4.5; i++) bg = tmavsia(bg, fg === '#ffffff' || /^#?f/i.test(fg) ? -0.12 : 0.12);
  return `<span class="linka" style="--lb:${bg};--lf:${fg}" title="${hx(druh)}">${hx(n)}</span>`;
}

/** HTML zoznam odchodov */
export function zoznam(ix: Index, o: Odchod[]) {
  if (!o.length) return '<p class="od-nic">V najbližších 24 hodinách odtiaľto podľa cestovného poriadku nič nepremáva.</p>';
  return `<ol class="od-zoznam">${o.map((x) => `<li>${znacka(ix, x.linka)}<span class="od-smer">${hx(x.smer)}</span><span class="od-cas"><b>${x.za <= 0 ? 'teraz' : x.za < 60 ? `${x.za} min` : hodina(x.min)}</b>${x.za > 0 && x.za < 60 ? `<small>${hodina(x.min)}</small>` : ''}</span></li>`).join('')}</ol>`;
}
