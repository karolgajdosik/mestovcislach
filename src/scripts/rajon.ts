// Vyhľadanie spádovej ZŠ a MŠ podľa adresy (rajonizácia mesta Bratislava).
// Používa ho stránka /vybavenost aj asistent (functions/api/asistent.ts).

export type Rajonizacia = {
  zs: { nazov: string; adresa: string; web: string; typ: string }[];
  ms: { nazov: string; adresa: string }[];
  ulice: Record<string, Record<string, [string, string, number | null, number | null][]>>;
};

export type Vysledok = {
  mc: string;
  ulica: string;
  cislo: string | null;
  presne: boolean; // číslo sa našlo presne
  zs: Rajonizacia['zs'][number][];
  ms: Rajonizacia['ms'][number][];
};

export const norm = (s: string) =>
  s.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '')
    .replace(/\bnam(\.|estie)\s*/g, 'namestie ').replace(/\bul(\.|ica)\s*/g, '')
    .replace(/[^a-z0-9]+/g, ' ').trim();

/** Rozdelí text na ulicu a číslo: „Romanova 12“, „Mlynské nivy 3104/11“, „Hlavná 5A, Rača“. */
export function rozdel(text: string): { ulica: string; cislo: string | null; mc: string | null } {
  let t = text.trim();
  let mc: string | null = null;
  const ciarka = t.split(',');
  if (ciarka.length > 1) { t = ciarka[0]; mc = ciarka.slice(1).join(',').trim() || null; }
  const m = t.match(/^(.*?\D)\s*(\d+[a-z]?(?:\s*\/\s*\d+[a-z]?)?)\s*$/i);
  return m ? { ulica: m[1].trim(), cislo: m[2].replace(/\s+/g, ''), mc } : { ulica: t, cislo: null, mc };
}

function unikatne<T>(idx: (number | null)[], zoznam: T[]): T[] {
  return [...new Set(idx.filter((i): i is number => i != null))].map((i) => zoznam[i]);
}

/** Nájde ulice (presná zhoda názvu, inak začiatok, inak obsahuje) a k nim spádové školy. */
export function najdi(d: Rajonizacia, ulica: string, cislo: string | null, mc: string | null = null, max = 6): Vysledok[] {
  const q = norm(ulica);
  if (q.length < 3) return [];
  const qmc = mc ? norm(mc) : null;
  const kandidati: { mc: string; ulica: string; skore: number }[] = [];
  for (const [m, ulice] of Object.entries(d.ulice)) {
    if (qmc && !norm(m).includes(qmc)) continue;
    for (const u of Object.keys(ulice)) {
      const n = norm(u);
      const skore = n === q ? 3 : n.startsWith(q) ? 2 : n.includes(q) ? 1 : 0;
      if (skore) kandidati.push({ mc: m, ulica: u, skore });
    }
  }
  if (!kandidati.length) return [];
  const najlepsie = Math.max(...kandidati.map((k) => k.skore));
  const vybrane = kandidati.filter((k) => k.skore === najlepsie).sort((a, b) => a.ulica.localeCompare(b.ulica, 'sk')).slice(0, max);

  const vsetky = vybrane.map(({ mc: m, ulica: u }) => {
    const adresy = d.ulice[m][u];
    let zhoda = adresy;
    let presne = false;
    if (cislo) {
      const c = cislo.toLowerCase();
      const [a, b] = c.split('/');
      const eq = (x: string, y: string) => x.toLowerCase() === y;
      const bezPismena = (x: string) => x.replace(/[a-z]$/i, '');
      const pokusy = b
        ? [(r: any) => eq(r[0], a) && eq(r[1], b), (r: any) => eq(r[1], b), (r: any) => eq(r[0], a)]
        : [(r: any) => eq(r[1], c), (r: any) => eq(r[0], c), (r: any) => bezPismena(r[1]) === bezPismena(c)];
      for (const p of pokusy) {
        const z = adresy.filter(p);
        if (z.length) { zhoda = z; presne = true; break; }
      }
    }
    return {
      mc: m, ulica: u, cislo, presne,
      zs: unikatne(zhoda.map((r) => r[2]), d.zs),
      ms: unikatne(zhoda.map((r) => r[3]), d.ms),
    };
  });
  // Ulica vo viacerých mestských častiach: ak sa číslo niekde našlo presne, ostatné nezobrazuj
  return vsetky.some((v) => v.presne) ? vsetky.filter((v) => v.presne) : vsetky;
}

/** Zoznam ulíc pre našepkávač (unikátne názvy). */
export const zoznamUlic = (d: Rajonizacia) =>
  [...new Set(Object.values(d.ulice).flatMap((u) => Object.keys(u)))].sort((a, b) => a.localeCompare(b, 'sk'));
