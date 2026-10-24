// Kvíz „Poznáš svoje mesto?“ – zásobník otázok generovaný pri builde z dát webu (ŠÚ SR vrátane Urban Audit,
// sčítanie 2021, ÚPSVaR, voľby, Digitálna mapa škôl, účtovné závierky, CRZ, mapa mesta, ŽSR, EEA, EIA).
// Prehliadač z neho pri každej hre náhodne vyberie 10 otázok (prednostne tie, ktoré hráč ešte nevidel)
// a zamieša poradie odpovedí. Nesprávne možnosti sú tu odvodené deterministicky (rovnaký build = rovnaký zásobník).
import { citaj } from './adresa';
import { MESTA } from '../mesta';
import { obdobia, skrat } from './zastupitelstvo';
import { hospodarenie, mapaMesta } from './mapa';

export type Graf =
  | { typ: 'stlpce'; nadpis: string; jednotka?: string; des?: number; polozky: { n: string; v: number; ja?: boolean }[] }
  | { typ: 'ciara'; nadpis: string; roky: string[]; hodnoty: number[]; pozn?: string };
export type Otazka = { id: string; q: string; moznosti: string[]; spravna: number; vysvetlenie: string; tema: string; graf?: Graf };

// deterministický generátor (mulberry32 zo zahašovaného textu)
const nahoda = (seed: string) => {
  let h = 1779033703 ^ seed.length;
  for (let i = 0; i < seed.length; i++) { h = Math.imul(h ^ seed.charCodeAt(i), 3432918353); h = (h << 13) | (h >>> 19); }
  let a = h >>> 0;
  return () => { a = (a + 0x6d2b79f5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
};
const zamiesaj = <T,>(a: T[], seed: string) => { const r = nahoda(seed); const b = a.slice(); for (let i = b.length - 1; i > 0; i--) { const j = Math.floor(r() * (i + 1)); [b[i], b[j]] = [b[j], b[i]]; } return b; };
const tis = (n: number) => Math.round(n).toLocaleString('sk-SK');
const des = (n: number, d = 1) => n.toLocaleString('sk-SK', { minimumFractionDigits: d, maximumFractionDigits: d });
const zaokr = (n: number) => { if (n < 20) return Math.round(n); const r = 10 ** Math.max(0, Math.floor(Math.log10(n)) - 1); return Math.round(n / r) * r; };
const AKT = MESTA.filter((m) => m.aktivne);
// skratka strany; dlhé koalície skrátené na prvé tri strany
const kr = (s: string) => { const p = skrat(s).split(' + '); return p.length > 3 ? `${p.slice(0, 3).join(' + ')} a ďalší` : p.join(' + '); };
const nazovMesta = (s: string) => MESTA.find((m) => m.slug === s)?.nazov ?? s;
const minuty = (x: number) => { const r = Math.round(x); return r < 60 ? `${r} min` : `${Math.floor(r / 60)} h ${String(r % 60).padStart(2, '0')} min`; };

export function kviz(slug: string): Otazka[] {
  const m = MESTA.find((x) => x.slug === slug)!;
  const C = m.nazov;
  const por: any[] = citaj('data', 'mesta', 'porovnanie.json')?.mesta ?? [];
  const ja = por.find((x) => x.slug === slug);
  const dm = citaj('data', 'mesta', `${slug}.json`) ?? {};
  const ot: Otazka[] = [];

  // ---------- pomocníci ----------
  const pridaj = (id: string, tema: string, q: string, spravna: string, zle: string[], vysvetlenie: string, graf?: Graf) => {
    const moznosti = [spravna, ...[...new Set(zle)].filter((z) => z && z !== spravna).slice(0, 3)];
    if (moznosti.length < 3) return;
    ot.push({ id, q, moznosti, spravna: 0, vysvetlenie, tema, ...(graf ? { graf } : {}) }); // poradie mieša prehliadač
  };
  /** číselná otázka: nesprávne možnosti ako násobky správnej hodnoty */
  const cislo = (id: string, tema: string, q: string, v: number, f: (x: number) => string, vysv: string, graf?: Graf, o: { max?: number; min?: number; zaokruhli?: boolean } = {}) => {
    if (v == null || !isFinite(v)) return;
    const nasobky = zamiesaj([0.45, 0.6, 0.72, 1.35, 1.6, 2, 2.6], `${slug}|${id}`);
    const uprav = (x: number) => (o.zaokruhli ? zaokr(x) : x);
    const spr = f(uprav(v));
    const zle: string[] = [];
    for (const k of nasobky) {
      const x = uprav(v * k);
      if ((o.max != null && x > o.max) || x < (o.min ?? 0)) continue;
      const t = f(x);
      if (t !== spr && !zle.includes(t)) zle.push(t);
      if (zle.length === 3) break;
    }
    pridaj(id, tema, q, spr, zle, vysv, graf);
  };
  /** stĺpce pre všetky mestá z mapy slug → hodnota */
  const stlpce = (hod: Record<string, number>, nadpis: string, jednotka = '', d = 1, zostupne = true): Graf => ({
    typ: 'stlpce', nadpis, jednotka, des: d,
    polozky: Object.entries(hod).filter(([, v]) => v != null && isFinite(v)).sort((a, b) => (zostupne ? b[1] - a[1] : a[1] - b[1]))
      .map(([s, v]) => ({ n: nazovMesta(s), v, ...(s === slug ? { ja: true } : {}) })),
  });
  /** porovnávacia otázka: ktoré z krajských miest má najviac / najmenej */
  const porovnaj = (id: string, tema: string, q: string, hod: Record<string, number>, max: boolean, jednotka: string, d: number, nadpis: string, vysv: (n: string, v: string) => string) => {
    const zor = Object.entries(hod).filter(([, v]) => v != null && isFinite(v)).sort((a, b) => (max ? b[1] - a[1] : a[1] - b[1]));
    if (zor.length < 5 || zor[0][1] === zor[1][1]) return;
    const zle = zamiesaj(zor.slice(1), id).slice(0, 3).map(([s]) => nazovMesta(s));
    const [s0, v0] = zor[0];
    pridaj(id, tema, q, nazovMesta(s0), zle, vysv(nazovMesta(s0), `${des(v0, d)}${jednotka}`) + (s0 !== slug && hod[slug] != null ? ` ${C}: ${des(hod[slug], d)}${jednotka}.` : ''), stlpce(hod, nadpis, jednotka, d, max));
  };
  const zPor = (k: string) => Object.fromEntries(por.filter((x) => x[k] != null).map((x) => [x.slug, x[k]]));
  const bezBA = (h: Record<string, number>) => Object.fromEntries(Object.entries(h).filter(([s]) => s !== 'bratislava'));
  // Urban Audit (ŠÚ SR) – posledný rok ukazovateľa podľa jeho popisu
  const UA = citaj('data', 'mesta', 'temy.json')?.mestske;
  const ua = (popis: string): { hod: Record<string, number>; rok: string } | null => {
    const k = Object.entries<string>(UA?.popisy ?? {}).find(([, p]) => p === popis)?.[0];
    if (!k) return null;
    const hod: Record<string, number> = {}; let rok = '';
    for (const s of AKT.map((x) => x.slug)) {
      const rad = UA.mesta?.[s]?.[k]; if (!rad) continue;
      const y = Object.keys(rad).sort().pop()!; hod[s] = rad[y]; if (y > rok) rok = y;
    }
    return Object.keys(hod).length >= 5 ? { hod, rok } : null;
  };
  const pct = (x: number, d = 1) => `${des(x, d)} %`;
  const eur = (x: number) => `${tis(x)} €`;

  // ---------- Obyvatelia ----------
  if (ja?.obyvatelia) cislo('obyv', 'Obyvatelia', `Koľko obyvateľov má ${C}?`, ja.obyvatelia, (x) => `približne ${tis(x)}`,
    `${C}: ${tis(ja.obyvatelia)} obyvateľov k 31. 12. ${ja.rok} (Štatistický úrad SR).`, stlpce(zPor('obyvatelia'), 'Obyvatelia krajských miest', '', 0), { zaokruhli: true });
  const rad = dm.obyvatelia?.roky ?? {};
  const roky = Object.keys(rad).sort().filter((r) => r >= '2012').slice(-14);
  const ciara: Graf | undefined = roky.length > 5 ? { typ: 'ciara', nadpis: `Počet obyvateľov ${roky[0]}–${roky.at(-1)}`, roky, hodnoty: roky.map((r) => rad[r]),
    ...(rad['2020'] && rad['2021'] && Math.abs(rad['2021'] / rad['2020'] - 1) > 0.012 ? { pozn: 'Skok v roku 2021 spôsobilo sčítanie obyvateľov – spresnilo, koľko ľudí v meste naozaj žije.' } : {}) } : undefined;
  if (ja?.zmena10 != null) {
    const f = (x: number) => `${x >= 0 ? 'pribudlo' : 'ubudlo'} asi ${des(Math.abs(x), 0)} %`;
    const v = ja.zmena10;
    pridaj('zmena10', 'Obyvatelia', `Ako sa za posledných 10 rokov zmenil počet obyvateľov – ${C}?`, f(v), [f(-v || 3), f(v + (v > 0 ? 9 : -6)), f(v > 0 ? 2 : 1), f(v - 4)],
      `Za 10 rokov ${v > 0 ? 'pribudlo' : 'ubudlo'} ${des(Math.abs(v))} % obyvateľov. ${v < 0 ? 'Väčšina krajských miest sa zmenšuje – ľudia sa sťahujú do okolitých obcí.' : 'Rastie najmä vďaka novej výstavbe.'}`, ciara);
  }
  const r93 = Object.keys(rad).sort()[0];
  if (r93 && r93 <= '1996' && ja?.obyvatelia) cislo('obyv93', 'Obyvatelia', `Koľko obyvateľov tu žilo v roku ${r93} (${C})?`, rad[r93], (x) => `približne ${tis(x)}`,
    `V roku ${r93} to bolo ${tis(rad[r93])}, dnes ${tis(ja.obyvatelia)} (${ja.obyvatelia > rad[r93] ? '+' : '−'}${des(Math.abs(100 * (ja.obyvatelia / rad[r93] - 1)), 0)} %).`, undefined, { zaokruhli: true });
  if (ja?.deti != null) cislo('deti', 'Obyvatelia', `Aký podiel obyvateľov – ${C} – tvoria deti do 14 rokov?`, ja.deti, (x) => pct(x, 0), `Deti do 14 rokov: ${pct(ja.deti)} obyvateľov.`, stlpce(zPor('deti'), 'Podiel detí do 14 rokov', ' %'), { max: 60 });
  if (ja?.seniori != null) cislo('seniori-c', 'Obyvatelia', `Aký podiel obyvateľov – ${C} – má 65 a viac rokov?`, ja.seniori, (x) => pct(x, 0), `Seniori 65+: ${pct(ja.seniori)} obyvateľov.`, stlpce(zPor('seniori'), 'Podiel obyvateľov 65+', ' %'), { max: 60 });
  porovnaj('naj-seniori', 'Obyvatelia', 'V ktorom krajskom meste je najvyšší podiel seniorov (65+)?', zPor('seniori'), true, ' %', 1, 'Podiel obyvateľov 65+', (n, v) => `${n} – ${v} obyvateľov má 65 a viac rokov.`);
  porovnaj('naj-deti', 'Obyvatelia', 'V ktorom krajskom meste je najvyšší podiel detí do 14 rokov?', zPor('deti'), true, ' %', 1, 'Podiel detí do 14 rokov', (n, v) => `${n} – deti tvoria ${v} obyvateľov.`);
  porovnaj('naj-rast', 'Obyvatelia', 'Ktorému krajskému mestu sa za posledných 10 rokov počet obyvateľov vyvíjal najlepšie?', zPor('zmena10'), true, ' %', 1, 'Zmena počtu obyvateľov za 10 rokov', (n, v) => `${n}: ${v}.`);
  porovnaj('naj-pokles', 'Obyvatelia', 'Ktoré krajské mesto za posledných 10 rokov stratilo percentuálne najviac obyvateľov?', zPor('zmena10'), false, ' %', 1, 'Zmena počtu obyvateľov za 10 rokov', (n, v) => `${n}: ${v}.`);
  porovnaj('najmensie', 'Obyvatelia', 'Ktoré krajské mesto má najmenej obyvateľov?', zPor('obyvatelia'), false, '', 0, 'Obyvatelia krajských miest', (n, v) => `${n} – ${v} obyvateľov.`);

  // ---------- Sčítanie 2021 ----------
  const sc = dm.scitanie;
  if (sc?.narodnost?.Spolu) {
    const nar = Object.entries<number>(sc.narodnost).filter(([k]) => !/Spolu|Slovenská|Nezistená|Iná/.test(k)).sort((a, b) => b[1] - a[1]);
    if (nar.length >= 4 && nar[0][1] > nar[1][1]) pridaj('narodnost', 'Sčítanie', `Ktorá národnosť je ${m.v} po slovenskej najčastejšia (sčítanie 2021)?`, nar[0][0], zamiesaj(nar.slice(1, 6).map(([k]) => k), slug + 'n'),
      `${nar[0][0]} národnosť: ${tis(nar[0][1])} ľudí (${pct((100 * nar[0][1]) / sc.narodnost.Spolu)}).`,
      { typ: 'stlpce', nadpis: 'Národnosti okrem slovenskej (sčítanie 2021)', des: 0, polozky: nar.slice(0, 6).map(([k, v], i) => ({ n: k, v, ...(i === 0 ? { ja: true } : {}) })) });
  }
  if (sc?.nabozenstvo?.Spolu) {
    const bez = sc.nabozenstvo['bez náboženského vyznania'];
    if (bez) cislo('bez-vyznania', 'Sčítanie', `Koľko percent obyvateľov – ${C} – je bez náboženského vyznania (sčítanie 2021)?`, (100 * bez) / sc.nabozenstvo.Spolu, (x) => pct(x, 0),
      `Bez vyznania: ${tis(bez)} ľudí, ${pct((100 * bez) / sc.nabozenstvo.Spolu)}. Na celom Slovensku je to približne 24 %.`, undefined, { max: 90 });
    const rk = Object.entries<number>(sc.nabozenstvo).find(([k]) => /^Rímskokatolícka/.test(k));
    if (rk) cislo('rimkat', 'Sčítanie', `Koľko percent obyvateľov – ${C} – sa hlási k rímskokatolíckej cirkvi?`, (100 * rk[1]) / sc.nabozenstvo.Spolu, (x) => pct(x, 0),
      `Rímskokatolícka cirkev: ${pct((100 * rk[1]) / sc.nabozenstvo.Spolu)} obyvateľov (sčítanie 2021).`, undefined, { max: 95 });
  }
  if (ja?.vs != null) cislo('vs-c', 'Sčítanie', `Aký podiel obyvateľov – ${C} – má vysokoškolské vzdelanie?`, ja.vs, (x) => pct(x, 0), `${pct(ja.vs)} obyvateľov nad 15 rokov má vysokú školu (sčítanie 2021).`, stlpce(zPor('vs'), 'Podiel ľudí s vysokoškolským vzdelaním', ' %'), { max: 70 });
  porovnaj('naj-vs', 'Sčítanie', 'Ktoré krajské mesto má najvyšší podiel ľudí s vysokoškolským vzdelaním?', zPor('vs'), true, ' %', 1, 'Podiel ľudí s vysokoškolským vzdelaním', (n, v) => `${n} – ${v} obyvateľov nad 15 rokov.`);
  porovnaj('naj-vs-mimo-ba', 'Sčítanie', 'Ktoré krajské mesto má po Bratislave najvyšší podiel vysokoškolákov?', bezBA(zPor('vs')), true, ' %', 1, 'Podiel vysokoškolákov (bez Bratislavy)', (n, v) => `${n} – ${v}.`);

  // ---------- Práca ----------
  if (ja?.pdu != null) cislo('pdu', 'Práca', `Aká je nezamestnanosť – ${C}?`, ja.pdu, (x) => pct(x),
    `Podiel disponibilných uchádzačov o zamestnanie je ${pct(ja.pdu)} (ÚPSVaR). Krajské mestá majú nezamestnanosť nižšiu ako slovenský priemer.`, stlpce(zPor('pdu'), 'Nezamestnanosť v krajských mestách', ' %', 2, false), { max: 30 });
  porovnaj('naj-pdu', 'Práca', 'Ktoré krajské mesto má najnižšiu nezamestnanosť?', zPor('pdu'), false, ' %', 2, 'Nezamestnanosť v krajských mestách', (n, v) => `${n} – ${v}.`);
  porovnaj('naj-pdu-vys', 'Práca', 'Ktoré krajské mesto má najvyššiu nezamestnanosť?', zPor('pdu'), true, ' %', 2, 'Nezamestnanosť v krajských mestách', (n, v) => `${n} – ${v}.`);
  const pr = dm.praca?.mesacne?.[dm.praca?.obdobie];
  const sr = pr?.['Slovenská republika']?.pdu, mpdu = pr?.[C]?.pdu;
  if (sr && mpdu) pridaj('pdu-sr', 'Práca', `Ako je na tom ${C} s nezamestnanosťou oproti celému Slovensku?`,
    mpdu < sr ? 'nižšia ako priemer SR' : 'vyššia ako priemer SR', [mpdu < sr ? 'vyššia ako priemer SR' : 'nižšia ako priemer SR', 'presne ako priemer SR', 'dvojnásobná oproti priemeru SR'],
    `${C}: ${pct(mpdu, 2)}, Slovensko: ${pct(sr, 2)} (ÚPSVaR, ${dm.praca.obdobie}).`,
    { typ: 'stlpce', nadpis: 'Nezamestnanosť', jednotka: ' %', des: 2, polozky: Object.entries<any>(pr).map(([n, v]) => ({ n, v: v.pdu, ...(n === C ? { ja: true } : {}) })) });

  // ---------- Voľby ----------
  const ob = obdobia(slug).find((o) => !o.priebezne && o.poslancov > 0);
  if (ob) {
    const kom = slug === 'bratislava' ? citaj('data', 'komunalne-bratislava.json')?.volby?.find((v: any) => v.id === ob.rok)?.oso?.primator?.kandidati : dm.komunalne?.[ob.rok]?.primator;
    const kand = (kom ?? []).slice().sort((a: any, b: any) => b.hlasy - a.hlasy);
    const grafKand: Graf | undefined = kand[0]?.podiel != null ? { typ: 'stlpce', nadpis: `Voľba primátora ${ob.rok}`, jednotka: ' %', des: 1, polozky: kand.slice(0, 6).map((k: any) => ({ n: k.meno, v: k.podiel, ...(k.zvoleny ? { ja: true } : {}) })) } : undefined;
    if (ob.primator && kand.length >= 3) pridaj('primator', 'Voľby', `Kto vyhral voľbu primátora v roku ${ob.rok}?`, ob.primator.meno, kand.filter((k: any) => !k.zvoleny).map((k: any) => k.meno),
      `${ob.primator.meno} (${kr(ob.primator.strany)}) získal(a) ${ob.primator.podiel != null ? des(ob.primator.podiel) + ' % hlasov' : 'najviac hlasov'}.`, grafKand);
    if (ob.primator?.podiel != null) cislo('primator-pct', 'Voľby', `Koľko percent hlasov získal(a) víťaz(ka) voľby primátora v roku ${ob.rok}?`, ob.primator.podiel, (x) => pct(x, 0),
      `${ob.primator.meno}: ${pct(ob.primator.podiel)} hlasov.`, grafKand, { max: 95, min: 15 });
    if (ob.poslancov) pridaj('poslancov', 'Voľby', `Koľko poslancov má mestské zastupiteľstvo – ${C}?`, String(ob.poslancov), [ob.poslancov - 6, ob.poslancov + 4, ob.poslancov + 12, ob.poslancov - 10].filter((x) => x > 8).map(String),
      `${ob.poslancov} poslancov zvolených v roku ${ob.rok}. Počet určuje zastupiteľstvo podľa veľkosti mesta.`,
      { typ: 'stlpce', nadpis: 'Zloženie zastupiteľstva', des: 0, polozky: ob.mandaty.slice().sort((a, b) => b.mandaty - a.mandaty).slice(0, 7).map((x) => ({ n: kr(x.strany), v: x.mandaty })) });
    const mand = ob.mandaty.slice().sort((a, b) => b.mandaty - a.mandaty);
    if (mand.length >= 3 && mand[0].mandaty > mand[1].mandaty) pridaj('mandaty', 'Voľby', `Kto má v mestskom zastupiteľstve – ${C} – najviac poslancov (obdobie ${ob.rok}–${Number(ob.rok) + 4})?`,
      kr(mand[0].strany), [...mand.slice(1).map((x) => kr(x.strany)), 'Smer', 'PS', 'KDH'],
      `${kr(mand[0].strany)}: ${mand[0].mandaty} z ${ob.poslancov} mandátov.`, { typ: 'stlpce', nadpis: 'Mandáty podľa strán', des: 0, polozky: mand.slice(0, 7).map((x, i) => ({ n: kr(x.strany), v: x.mandaty, ...(i === 0 ? { ja: true } : {}) })) });
    if (ob.ucast != null) cislo('ucast-kom', 'Voľby', `Aká bola účasť v komunálnych voľbách ${ob.rok}?`, ob.ucast, (x) => pct(x, 0),
      `Volilo ${pct(ob.ucast)} voličov – v komunálnych voľbách býva účasť výrazne nižšia ako v parlamentných.`, stlpce(zPor('ucast_komunalne'), `Účasť v komunálnych voľbách ${ob.rok}`, ' %'), { max: 90 });
    const top = ob.poslanci.slice().sort((a, b) => (b.hlasy ?? 0) - (a.hlasy ?? 0));
    if (top.length >= 4 && top[0].hlasy && top[0].hlasy > (top[1].hlasy ?? 0)) cislo('poslanec-hlasy', 'Voľby', `Koľko hlasov získal(a) najúspešnejší poslanec / poslankyňa vo voľbách ${ob.rok}?`, top[0].hlasy, (x) => `približne ${tis(x)}`,
      `${top[0].meno} (${kr(top[0].strany)}): ${tis(top[0].hlasy)} hlasov.`, undefined, { zaokruhli: true });
  }
  porovnaj('naj-ucast-kom', 'Voľby', 'V ktorom krajskom meste bola najvyššia účasť v komunálnych voľbách 2022?', zPor('ucast_komunalne'), true, ' %', 1, 'Účasť v komunálnych voľbách 2022', (n, v) => `${n} – ${v}.`);
  const nr = dm.volby?.nrsr2023;
  if (nr?.strany?.length >= 4) {
    const s = nr.strany.slice().sort((a: any, b: any) => b.podiel - a.podiel);
    pridaj('nr2023', 'Voľby', `Ktorá strana vyhrala ${m.v} parlamentné voľby 2023?`, kr(s[0].nazov), s.slice(1, 5).map((x: any) => kr(x.nazov)),
      `${kr(s[0].nazov)} – ${pct(s[0].podiel, 2)}, ${kr(s[1].nazov)} – ${pct(s[1].podiel, 2)}.`,
      { typ: 'stlpce', nadpis: 'Parlamentné voľby 2023', jednotka: ' %', des: 1, polozky: s.slice(0, 6).map((x: any, i: number) => ({ n: kr(x.nazov), v: x.podiel, ...(i === 0 ? { ja: true } : {}) })) });
    if (nr.ucast) cislo('nr2023-ucast', 'Voľby', `Aká bola ${m.v} účasť v parlamentných voľbách 2023?`, nr.ucast, (x) => pct(x, 0), `${pct(nr.ucast)} (celé Slovensko ${pct(nr.ucast_sr)}).`, undefined, { max: 95, min: 25 });
  }
  const ep = dm.volby?.ep2024;
  if (ep?.strany?.length >= 4) {
    const s = ep.strany.slice().sort((a: any, b: any) => b.podiel - a.podiel);
    pridaj('ep2024', 'Voľby', `Ktorá strana vyhrala ${m.v} eurovoľby 2024?`, kr(s[0].nazov), s.slice(1, 5).map((x: any) => kr(x.nazov)),
      `${kr(s[0].nazov)} – ${pct(s[0].podiel, 2)}${ep.ucast ? `, účasť ${pct(ep.ucast)}` : ''}.`,
      { typ: 'stlpce', nadpis: 'Voľby do Európskeho parlamentu 2024', jednotka: ' %', des: 1, polozky: s.slice(0, 6).map((x: any, i: number) => ({ n: kr(x.nazov), v: x.podiel, ...(i === 0 ? { ja: true } : {}) })) });
  }

  // ---------- Školy ----------
  const skV = citaj('data', 'mesta', 'skoly.json')?.mesta ?? {};
  const sk = skV[slug];
  const skMesta = (t: string, k = 'skol') => Object.fromEntries(Object.entries<any>(skV).map(([s, v]) => [s, v.suhrn?.[t]?.[k]]).filter(([, v]) => v != null));
  if (sk?.suhrn) {
    const S = sk.suhrn;
    if (S.zs?.skol) cislo('zs', 'Školy', `Koľko základných škôl je v meste – ${C}?`, S.zs.skol, (x) => tis(x), `${S.zs.skol} základných škôl s ${tis(S.zs.ziakov)} žiakmi (Digitálna mapa škôl, MŠVVaM SR).`, stlpce(skMesta('zs'), 'Základné školy v krajských mestách', '', 0), { min: 2 });
    if (S.ms?.skol) cislo('ms', 'Školy', `Koľko materských škôl (škôlok) je v meste – ${C}?`, S.ms.skol, (x) => tis(x), `${S.ms.skol} materských škôl s ${tis(S.ms.ziakov)} deťmi.`, stlpce(skMesta('ms'), 'Materské školy v krajských mestách', '', 0), { min: 2 });
    if (S.ss?.skol) cislo('ss', 'Školy', `Koľko stredných škôl je v meste – ${C}?`, S.ss.skol, (x) => tis(x), `${S.ss.skol} stredných škôl s ${tis(S.ss.ziakov)} žiakmi.`, stlpce(skMesta('ss'), 'Stredné školy v krajských mestách', '', 0), { min: 2 });
    if (S.zs?.ziakov) cislo('zs-ziaci', 'Školy', `Koľko žiakov chodí ${m.v} do základných škôl?`, S.zs.ziakov, (x) => `približne ${tis(x)}`, `${tis(S.zs.ziakov)} žiakov v ${S.zs.skol} základných školách.`, stlpce(skMesta('zs', 'ziakov'), 'Žiaci základných škôl', '', 0), { zaokruhli: true });
    if (S.zs?.ziakov_na_ucitela) cislo('zs-ucitel', 'Školy', `Koľko žiakov pripadá ${m.v} v základných školách na jedného učiteľa?`, S.zs.ziakov_na_ucitela, (x) => des(x, 1), `${des(S.zs.ziakov_na_ucitela)} žiaka na pedagóga.`, stlpce(skMesta('zs', 'ziakov_na_ucitela'), 'Žiaci ZŠ na učiteľa', '', 1));
    const ss = (sk.skoly as any[]).filter((x) => x.t === 'ss' && x.z1 != null).sort((a, b) => b.z1 - a.z1);
    if (ss.length >= 6) pridaj('ss-zaujem', 'Školy', 'Ktorú strednú školu si pri prijímačkách dalo ako 1. voľbu najviac uchádzačov?', ss[0].n, zamiesaj(ss.slice(3), slug + 'ss').slice(0, 3).map((x) => x.n),
      `${ss[0].n}: ${tis(ss[0].z1)} prihlášok s 1. voľbou (MŠVVaM SR).`, { typ: 'stlpce', nadpis: 'Najviac prihlášok s 1. voľbou', des: 0, polozky: ss.slice(0, 6).map((x, i) => ({ n: x.n, v: x.z1, ...(i === 0 ? { ja: true } : {}) })) });
    const zs = (sk.skoly as any[]).filter((x) => x.t === 'zs' && x.z && !/^(Súkr\.|Cirk\.)?\s*MŠ/.test(x.n)).sort((a, b) => b.z - a.z);
    if (zs.length >= 6 && zs[0].z > zs[1].z) pridaj('zs-najvacsia', 'Školy', 'Ktorá základná škola v meste má najviac žiakov?', zs[0].n, zamiesaj(zs.slice(4), slug + 'zs').slice(0, 3).map((x) => x.n),
      `${zs[0].n}: ${tis(zs[0].z)} žiakov.`, { typ: 'stlpce', nadpis: 'Najväčšie základné školy', des: 0, polozky: zs.slice(0, 6).map((x, i) => ({ n: x.n, v: x.z, ...(i === 0 ? { ja: true } : {}) })) });
  }
  const vsSt = ua('Študenti vysokoškolského vzdelávania na 1000 obyvateľov');
  if (vsSt) porovnaj('naj-studenti', 'Školy', 'Ktoré krajské mesto má najviac vysokoškolských študentov na 1000 obyvateľov?', vsSt.hod, true, '', 0, 'VŠ študenti na 1000 obyvateľov', (n, v) => `${n} – ${v} študentov na 1000 obyvateľov (${vsSt.rok}).`);

  // ---------- Peniaze ----------
  const hosp: Record<string, number> = {};
  for (const x of AKT) { const hx = hospodarenie(x.slug); const o = por.find((y) => y.slug === x.slug)?.obyvatelia; if (hx?.posledny?.danove_vynosy && o) hosp[x.slug] = Math.round(hx.posledny.danove_vynosy / o); }
  porovnaj('naj-dane', 'Peniaze', 'Ktoré krajské mesto má najvyššie daňové výnosy na obyvateľa?', hosp, true, ' €', 0, 'Daňové výnosy na obyvateľa', (n, v) => `${n} – asi ${v} na obyvateľa ročne (účtovná závierka). Bratislava a Košice bez mestských častí.`);
  const h = hospodarenie(slug);
  if (h?.posledny?.naklady) {
    cislo('naklady', 'Peniaze', `Koľko stojí prevádzka mesta ${C} za rok (náklady ${h.rok})?`, h.posledny.naklady / 1e6, (x) => `približne ${tis(x)} mil. €`,
      `Náklady mesta v roku ${h.rok}: ${des(h.posledny.naklady / 1e6)} mil. €${ja?.obyvatelia ? `, teda asi ${tis(h.posledny.naklady / ja.obyvatelia)} € na obyvateľa` : ''}.`, undefined, { zaokruhli: true, min: 1 });
    if (hosp[slug]) cislo('dane-c', 'Peniaze', `Koľko daňových výnosov má ${C} na jedného obyvateľa ročne?`, hosp[slug], (x) => eur(zaokr(x)), `Asi ${eur(hosp[slug])} na obyvateľa (${h.rok}).`, stlpce(hosp, 'Daňové výnosy na obyvateľa', ' €', 0));
    const nak = [['transfery_dane', 'príspevky školám, MHD a mestským organizáciám'], ['osobne_naklady', 'mzdy zamestnancov mesta'], ['sluzby', 'služby (údržba, odpad, opravy)'], ['odpisy', 'odpisy majetku']]
      .filter(([k]) => h.posledny[k]).sort((a, b) => h.posledny[b[0]] - h.posledny[a[0]]);
    if (nak.length >= 4) pridaj('naklady-naj', 'Peniaze', `Na čo mesto ${C} míňa najviac peňazí?`, nak[0][1], nak.slice(1).map((x) => x[1]),
      `Najväčšia položka: ${nak[0][1]} – ${des(h.posledny[nak[0][0]] / 1e6)} mil. € (${h.rok}).`,
      { typ: 'stlpce', nadpis: `Náklady mesta ${h.rok} (mil. €)`, des: 1, polozky: nak.map(([k, n], i) => ({ n, v: h.posledny[k] / 1e6, ...(i === 0 ? { ja: true } : {}) })) });
  }
  if (h?.dlhPosledny?.pomer != null) cislo('dlh', 'Peniaze', `Aký veľký je dlh mesta ${C} v pomere k jeho bežným príjmom? (zákonný limit je 60 %)`, h.dlhPosledny.pomer, (x) => pct(x, 0),
    `Dlh ${des(h.dlhPosledny.dlh / 1e6)} mil. € = ${pct(h.dlhPosledny.pomer)} bežných príjmov (MF SR, ${h.rokDlh}).`, undefined, { max: 59 });
  const crz = slug === 'kosice' ? citaj('data', 'mesta', 'samosprava-kosice.json')?.financie?.find((f: any) => f.typ === 'zmluvy') : citaj('data', 'mesta', `crz-${slug}.json`)?.zmluvy;
  const rokZ = crz?.roky ? Object.keys(crz.roky).filter((r) => Number(r) < new Date().getFullYear()).sort().pop() : null;
  if (rokZ && crz.roky[rokZ].pocet > 50) cislo('zmluvy', 'Peniaze', `Koľko zmlúv zverejnilo mesto ${C} za rok ${rokZ}?`, crz.roky[rokZ].pocet, (x) => `približne ${tis(x)}`,
    `${tis(crz.roky[rokZ].pocet)} zmlúv za ${des(crz.roky[rokZ].suma / 1e6)} mil. € (vrátane zmlúv s občanmi, ktorých mená nezverejňujeme).`, undefined, { zaokruhli: true });
  const dod = (crz?.dodavatelia_posledne_3_roky ?? []).filter((d: any) => d.ico && !/minister|úrad|fond|agentúr|kraj|mesto |obec /i.test(d.nazov));
  if (dod.length >= 5) pridaj('dodavatel', 'Peniaze', `Ktorá firma mala s mestom ${C} za posledné 3 roky zmluvy na najviac peňazí?`, dod[0].nazov, zamiesaj(dod.slice(1, 6).map((d: any) => d.nazov), slug + 'd'),
    `${dod[0].nazov}: ${dod[0].pocet} zmlúv za ${des(dod[0].suma / 1e6)} mil. € (Centrálny register zmlúv, bez štátnych inštitúcií).`,
    { typ: 'stlpce', nadpis: 'Zmluvy za 3 roky (mil. €)', des: 1, polozky: dod.slice(0, 6).map((d: any, i: number) => ({ n: d.nazov, v: d.suma / 1e6, ...(i === 0 ? { ja: true } : {}) })) });

  // ---------- Život v meste (Urban Audit, ŠÚ SR) ----------
  const uaOt = (id: string, tema: string, popis: string, otazka: string, f: (x: number) => string, jedn: string, d: number, nadpis: string, vysv: (v: string, rok: string) => string, porovnanie?: [string, boolean, (n: string, v: string) => string, boolean?]) => {
    const u = ua(popis);
    if (!u) return;
    const vys = (t: string) => vysv(t, u.rok);
    if (u.hod[slug] != null) cislo(id, tema, otazka, u.hod[slug], f, vys(`${des(u.hod[slug], d)}${jedn}`), stlpce(u.hod, `${nadpis} (${u.rok})`, jedn, d), { zaokruhli: d === 0 && u.hod[slug] > 50 });
    if (porovnanie) porovnaj(`naj-${id}`, tema, porovnanie[0], porovnanie[3] ? bezBA(u.hod) : u.hod, porovnanie[1], jedn, d, `${nadpis} (${u.rok})`, porovnanie[2]);
  };
  uaOt('auta', 'Doprava', 'Registrované súkromné osobné autá k 1.1. na 1000 obyvateľov', `Koľko osobných áut pripadá ${m.v} na 1000 obyvateľov?`, (x) => tis(x), '', 0, 'Osobné autá na 1000 obyvateľov', (v, r) => `${v} áut na 1000 obyvateľov (${r}).`,
    ['V ktorom krajskom meste je najviac osobných áut na 1000 obyvateľov?', true, (n, v) => `${n} – ${v} áut na 1000 obyvateľov.`]);
  uaOt('cyklo', 'Doprava', 'Dĺžka cyklistickej siete', `Aká dlhá je ${m.v} sieť cyklotrás?`, (x) => `${tis(x)} km`, ' km', 0, 'Dĺžka cyklistickej siete', (v, r) => `${v} cyklotrás (${r}, ŠÚ SR).`,
    ['Ktoré krajské mesto má najdlhšiu sieť cyklotrás?', true, (n, v) => `${n} – ${v}.`]);
  uaOt('listok', 'Doprava', 'Cena kombinovaného mesačného lístka na všetky druhy verejnej dopravy v centre v okruhu 5-10 km', `Koľko stojí ${m.v} mesačný lístok na MHD?`, (x) => `${des(x, 0)} €`, ' €', 1, 'Mesačný lístok MHD', (v, r) => `${v} (${r}, ŠÚ SR – Urban Audit).`,
    ['Kde je po Bratislave najdrahší mesačný lístok na MHD?', true, (n, v) => `${n} – ${v}.`, true]);
  uaOt('taxi', 'Doprava', 'Cena za taxi za 5 km v centre mesta počas dňa', `Koľko stojí ${m.v} cesta taxíkom na 5 km v centre?`, (x) => `${des(x, 1)} €`, ' €', 2, 'Taxi 5 km v centre', (v, r) => `Približne ${v} (${r}).`,
    ['Kde je najlacnejší taxík (5 km v centre)?', false, (n, v) => `${n} – ${v}.`]);
  uaOt('voda', 'Život', 'Cena za m3 vody v domácnostiach – Euro', `Koľko platia domácnosti ${m.v} za kubík vody?`, (x) => `${des(x, 2)} €`, ' €', 2, 'Cena vody za m³', (v, r) => `${v} za m³ (${r}, vodné a stočné).`,
    ['Kde je najlacnejšia voda pre domácnosti?', false, (n, v) => `${n} – ${v} za m³.`]);
  uaOt('voda-spotreba', 'Život', 'Celková spotreba vody – m3 na osobu', `Koľko vody spotrebuje ${m.v} jeden obyvateľ za rok?`, (x) => `${tis(x)} m³`, ' m³', 0, 'Spotreba vody na osobu za rok', (v, r) => `${v} na osobu (${r}).`);
  uaOt('odpad', 'Život', 'Množstvo komunálneho odpadu – kg na osobu', `Koľko komunálneho odpadu vyprodukuje ${m.v} jeden obyvateľ za rok?`, (x) => `${tis(x)} kg`, ' kg', 0, 'Komunálny odpad na osobu za rok', (v, r) => `${v} na osobu (${r}).`,
    ['V ktorom krajskom meste vyprodukuje človek najmenej komunálneho odpadu?', false, (n, v) => `${n} – ${v} na osobu za rok.`]);
  uaOt('kina', 'Život', 'Návštevnosť kín za rok', `Koľko návštev kín bolo ${m.v} za rok?`, (x) => `približne ${tis(x)}`, '', 0, 'Návštevnosť kín za rok', (v, r) => `${v} návštev (${r}).`);
  uaOt('muzea', 'Život', 'Návštevníci múzeí za rok', `Koľko návštevníkov mali ${m.v} múzeá za rok?`, (x) => `približne ${tis(x)}`, '', 0, 'Návštevníci múzeí', (v, r) => `${v} návštevníkov (${r}).`,
    ['Ktoré krajské mesto má po Bratislave najviac návštevníkov múzeí?', true, (n, v) => `${n} – ${v} za rok.`, true]);
  uaOt('turisti', 'Život', 'Prenocovania v ubytovacích zariadeniach cestovného ruchu na obyvateľa', `Koľko prenocovaní turistov pripadá ${m.v} ročne na jedného obyvateľa?`, (x) => des(x, 1), '', 1, 'Prenocovania turistov na obyvateľa', (v, r) => `${v} prenocovania na obyvateľa (${r}).`,
    ['Ktoré krajské mesto má po Bratislave najviac prenocovaní turistov na obyvateľa?', true, (n, v) => `${n} – ${v} na obyvateľa.`, true]);
  uaOt('kino-sedadla', 'Život', 'Celková kapacita sedadiel v kinách na 1000 obyvateľov', `Koľko sedadiel v kinách pripadá ${m.v} na 1000 obyvateľov?`, (x) => des(x, 0), '', 1, 'Sedadlá v kinách na 1000 obyvateľov', (v, r) => `${v} sedadla na 1000 obyvateľov (${r}).`,
    ['Ktoré krajské mesto má najviac sedadiel v kinách na 1000 obyvateľov?', true, (n, v) => `${n} – ${v}.`]);
  uaOt('bazeny', 'Život', 'Počet verejných bazénov (vnútorných aj vonkajších, okrem prírodných pláží)', `Koľko verejných bazénov má ${C}?`, (x) => tis(x), '', 0, 'Verejné bazény', (v, r) => `Počet verejných bazénov: ${v} (${r}, ŠÚ SR).`);
  uaOt('byt-m2', 'Bývanie', 'Priemerná cena za kúpu bytu za m2', `Koľko stojí ${m.v} priemerne štvorcový meter bytu?`, (x) => `${tis(zaokr(x))} €`, ' €', 0, 'Cena bytu za m²', (v, r) => `${v} za m² (${r}, ŠÚ SR).`,
    ['Kde sú po Bratislave najdrahšie byty (cena za m²)?', true, (n, v) => `${n} – ${v} za m².`, true]);
  uaOt('byt', 'Bývanie', 'Priemerná cena za kúpu bytu v eurách', `Koľko stál ${m.v} priemerný byt?`, (x) => `${tis(zaokr(x))} €`, ' €', 0, 'Priemerná cena bytu', (v, r) => `${v} (${r}, ŠÚ SR).`,
    ['Kde je najlacnejší priemerný byt?', false, (n, v) => `${n} – ${v}.`]);
  uaOt('dom', 'Bývanie', 'Priemerná cena za kúpu domu v eurách', `Koľko stál ${m.v} priemerný rodinný dom?`, (x) => `${tis(zaokr(x))} €`, ' €', 0, 'Priemerná cena domu', (v, r) => `${v} (${r}, ŠÚ SR).`);
  uaOt('byty', 'Bývanie', 'Stav počtu bytov', `Koľko bytov je ${m.v}?`, (x) => `približne ${tis(x)}`, '', 0, 'Počet bytov', (v, r) => `${v} bytov (${r}).`);
  uaOt('jasle', 'Život', 'Deti do 4 rokov v predškolských zariadeniach na 1000 detí do 4 rokov', `Koľko z 1000 detí do 4 rokov chodí ${m.v} do jaslí alebo škôlky?`, (x) => tis(x), '', 0, 'Deti do 4 rokov v jasliach a škôlkach (na 1000)', (v, r) => `${v} z 1000 detí (${r}).`,
    ['V ktorom krajskom meste chodí do jaslí a škôlok najviac detí do 4 rokov?', true, (n, v) => `${n} – ${v} z 1000.`]);
  const bv = dm.byty ?? {};
  const rokyB = Object.keys(bv).sort();
  const rokB = rokyB.at(-1);
  if (rokB && bv[rokB]?.DOKONC_BYT) cislo('dokoncene', 'Bývanie', `Koľko nových bytov dokončili ${m.v} v roku ${rokB}?`, bv[rokB].DOKONC_BYT, (x) => tis(x), `${bv[rokB].DOKONC_BYT} dokončených bytov, začatých ${bv[rokB].ZAC_BYT ?? '–'} (ŠÚ SR).`,
    { typ: 'ciara', nadpis: `Dokončené byty ${rokyB.slice(-12)[0]}–${rokB}`, roky: rokyB.slice(-12), hodnoty: rokyB.slice(-12).map((r) => bv[r].DOKONC_BYT ?? 0) }, { min: 5 });

  // ---------- Mesto na mape (portál mesta, OpenStreetMap) ----------
  const mapa = mapaMesta(slug);
  const vrstva = (re: RegExp) => (mapa?.vrstvy.find((v: any) => v.typ === 'body' && re.test(v.nazov))?.body?.length ?? 0) as number;
  const mapaOt = (id: string, re: RegExp, otazka: string, co: string) => { const n = vrstva(re); if (n >= 5) cislo(id, 'Mapa', otazka, n, (x) => tis(x), `Na mape mesta je ${n} ${co} (portál mesta alebo OpenStreetMap) – v skutočnosti ich môže byť o niečo viac.`, undefined, { min: 2 }); };
  if (slug !== 'bratislava') {
    mapaOt('lekarne', /^lekár/i, `Koľko lekární je ${m.v} na mape mesta?`, 'lekární');
    mapaOt('ihriska', /detské ihrisk/i, `Koľko detských ihrísk je ${m.v} na mape mesta?`, 'detských ihrísk');
    mapaOt('nabijanie', /nabíj/i, `Koľko nabíjacích staníc pre elektromobily je ${m.v} na mape mesta?`, 'nabíjacích staníc');
    mapaOt('zastavky', /zastávk/i, `Koľko zastávok MHD je ${m.v} na mape mesta?`, 'zastávok MHD');
  }

  // ---------- Vlaky (ŽSR GTFS) ----------
  const vl = citaj('data', 'mesta', 'vlaky.json')?.mesta;
  const v1 = vl?.[slug];
  if (v1?.odchodov) cislo('vlaky', 'Doprava', `Koľko vlakov odíde ${m.v} zo všetkých staníc za bežný pracovný deň?`, v1.odchodov, (x) => tis(x), `${v1.odchodov} odchodov, z hlavnej stanice ${v1.hlavna} ${v1.odchodov_hlavna} (grafikon ŽSR).`,
    stlpce(Object.fromEntries(Object.entries<any>(vl).map(([s, v]) => [s, v.odchodov])), 'Odchody vlakov za pracovný deň', '', 0), { zaokruhli: true, min: 5 });
  const doBA = v1?.spojenia?.bratislava?.najrychlejsie_min;
  if (slug !== 'bratislava' && doBA) cislo('vlak-ba', 'Doprava', `Ako dlho ide z mesta ${C} najrýchlejší vlak do Bratislavy?`, doBA, minuty,
    `Najrýchlejšie spojenie: ${minuty(doBA)}, ${v1.spojenia.bratislava.vlakov} priamych vlakov denne.`,
    stlpce(Object.fromEntries(Object.entries<any>(vl).filter(([s, v]) => s !== 'bratislava' && v.spojenia?.bratislava?.najrychlejsie_min).map(([s, v]) => [s, v.spojenia.bratislava.najrychlejsie_min])), 'Najrýchlejší vlak do Bratislavy (min)', ' min', 0, false), { min: 25 });
  const doKE = v1?.spojenia?.kosice?.najrychlejsie_min;
  if (slug !== 'kosice' && doKE) cislo('vlak-ke', 'Doprava', `Ako dlho ide z mesta ${C} najrýchlejší vlak do Košíc?`, doKE, minuty, `Najrýchlejšie spojenie: ${minuty(doKE)}, ${v1.spojenia.kosice.vlakov} priamych vlakov denne.`, undefined, { min: 25 });

  // ---------- Ovzdušie (EEA) ----------
  const ov = citaj('data', 'mesta', 'ovzdusie.json')?.mesta;
  const pm = (s: string) => { const r = ov?.[s]?.PM10; if (!r) return null; const y = Object.keys(r).filter((k) => !r[k].neuplny).sort().pop(); return y ? { y, v: r[y].priemer as number } : null; };
  const pmJa = pm(slug);
  if (pmJa) cislo('pm10', 'Prostredie', `Aká bola ${m.v} priemerná koncentrácia prachu PM10 v roku ${pmJa.y}? (limit EÚ 40, odporúčanie WHO 15 µg/m³)`, pmJa.v, (x) => `${des(x, 0)} µg/m³`,
    `${des(pmJa.v)} µg/m³ – ${pmJa.v <= 40 ? 'pod limitom EÚ' : 'nad limitom EÚ'}${pmJa.v > 15 ? ', ale nad odporúčaním WHO' : ' aj pod odporúčaním WHO'} (stanice SHMÚ, EEA).`,
    stlpce(Object.fromEntries(AKT.map((x) => [x.slug, pm(x.slug)?.v as number]).filter(([, v]) => v != null)), 'PM10 – ročný priemer (µg/m³)', '', 1, false), { max: 60, min: 5 });
  const pmVsetky = Object.fromEntries(AKT.map((x) => [x.slug, pm(x.slug)?.v as number]).filter(([, v]) => v != null));
  porovnaj('naj-pm10', 'Prostredie', 'Ktoré krajské mesto má najčistejší vzduch (najnižší priemer prachu PM10)?', pmVsetky, false, ' µg/m³', 1, 'PM10 – ročný priemer', (n, v) => `${n} – ${v}.`);

  // ---------- Stavby (EIA) ----------
  const eia = slug === 'bratislava' ? citaj('public', 'data', 'eia.json') : citaj('public', 'data', 'mesta', `eia-${slug}.json`);
  const aktivne = (eia?.zamery ?? []).filter((z: any) => !(String(z.ukoncene) === 'True' || z.ukoncene === true)).length;
  if (aktivne >= 5) cislo('eia', 'Stavby', `Koľko stavebných zámerov sa ${m.v} práve posudzuje z hľadiska vplyvov na životné prostredie (EIA)?`, aktivne, (x) => tis(x),
    `${aktivne} zámerov v posudzovaní (Enviroportál). Prehľad je v časti Čo sa stavia.`, undefined, { min: 2 });

  return ot;
}
