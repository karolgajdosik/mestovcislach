// Časté otázky o meste s odpoveďou z dát webu (obyvatelia, primátor, zastupiteľstvo, nezamestnanosť, byty, vzdelanie).
// Používa komponent RychleOdpovede a JSON-LD FAQPage na prehľade mesta.
import fs from 'node:fs';
import path from 'node:path';
import { MESTA } from '../mesta';
import { obdobia, skrat } from './zastupitelstvo';
import { posledny, ua } from './temy';

export type Odpoved = { otazka: string; odpoved: string; zdroj: string; odkaz?: string };

const citaj = (...p: string[]) => {
  const f = path.join(process.cwd(), ...p);
  try { return fs.existsSync(f) ? JSON.parse(fs.readFileSync(f, 'utf-8')) : null; } catch { return null; }
};
const cele = (n: number) => Math.round(n).toLocaleString('sk-SK');
const des = (n: number, d = 1) => n.toLocaleString('sk-SK', { minimumFractionDigits: d, maximumFractionDigits: d });
const bezTit = (m: string) => m.split(/[\s,]+/).filter((s) => s && !s.includes('.') && !/^(PhD|MBA|LL|MPH|MPA|DiS|CSc|ArtD)$/i.test(s)).join(' ');
const strana = (s: string, zena: boolean) => (!s || /^nezávisl/i.test(s) ? (zena ? 'nezávislá' : 'nezávislý') : skrat(s));
const MESIACE = ['január', 'február', 'marec', 'apríl', 'máj', 'jún', 'júl', 'august', 'september', 'október', 'november', 'december'];
// genitív názvu mesta pre otázky („primátor Trnavy“)
const GEN: Record<string, string> = {
  bratislava: 'Bratislavy', trnava: 'Trnavy', trencin: 'Trenčína', nitra: 'Nitry', zilina: 'Žiliny',
  'banska-bystrica': 'Banskej Bystrice', presov: 'Prešova', kosice: 'Košíc',
};

export function otazkyMesta(slug: string): Odpoved[] {
  const m = MESTA.find((x) => x.slug === slug);
  if (!m) return [];
  const gen = GEN[slug] ?? m.nazov;
  const out: Odpoved[] = [];
  const por = (citaj('data', 'mesta', 'porovnanie.json')?.mesta ?? []).find((p: any) => p.slug === slug);
  const ba = slug === 'bratislava';
  const pre = (s: string) => (ba ? `/bratislava/${s}` : `/${slug}/${s}`);

  if (por?.obyvatelia) {
    const z = por.zmena10;
    out.push({
      otazka: `Koľko obyvateľov má ${m.nazov}?`,
      odpoved: `V meste ${m.nazov} žilo k 31. 12. ${por.rok} ${cele(por.obyvatelia)} obyvateľov s trvalým pobytom.${z != null ? ` Za posledných 10 rokov sa počet ${z >= 0 ? 'zvýšil' : 'znížil'} o ${des(Math.abs(z))} %.` : ''}`,
      zdroj: 'Štatistický úrad SR (DATAcube)', odkaz: ba ? '/bratislava/obyvatelia' : `/${slug}#obyvatelia`,
    });
  }
  const o = obdobia(slug);
  const n = o.find((x) => x.rok === '2026' && !x.priebezne);
  if (n?.primator) {
    const s = o.find((x) => x.rok === '2022');
    const zena = /(ová|á)$/.test(bezTit(n.primator.meno).split(' ').pop() ?? '');
    const obhajil = s?.primator && bezTit(s.primator.meno).toLowerCase() === bezTit(n.primator.meno).toLowerCase();
    out.push({
      otazka: `Kto je primátor ${gen}?`,
      odpoved: `${zena ? 'Primátorkou' : 'Primátorom'} ${gen} je ${bezTit(n.primator.meno)} (${strana(n.primator.strany, zena)}). V komunálnych voľbách 24. októbra 2026 ${obhajil ? `funkciu ${zena ? 'obhájila' : 'obhájil'}` : zena ? 'zvíťazila' : 'zvíťazil'}${n.primator.podiel != null ? ` so ziskom ${des(n.primator.podiel)} % hlasov` : ''}. Volebné obdobie trvá do roku 2030.`,
      zdroj: 'Štatistický úrad SR (volbysr.sk)', odkaz: ba ? '/bratislava/volby' : `/${slug}/volby`,
    });
  }
  if (n?.poslancov) {
    const naj = n.mandaty.slice().sort((a, b) => b.mandaty - a.mandaty)[0];
    out.push({
      otazka: `Koľko poslancov má mestské zastupiteľstvo ${gen}?`,
      odpoved: `Mestské zastupiteľstvo má na obdobie 2026 – 2030 ${n.poslancov} poslancov.${naj ? ` Najviac mandátov (${naj.mandaty}) ${naj.strany === 'nezávislý kandidát' ? 'získali nezávislí kandidáti' : skrat(naj.strany).includes(' + ') ? `získala koalícia ${skrat(naj.strany)}` : `získala strana ${skrat(naj.strany)}`}.` : ''}`,
      zdroj: 'Štatistický úrad SR (volbysr.sk)', odkaz: pre('zastupitelstvo'),
    });
  }
  if (n?.ucast != null) {
    const s = o.find((x) => x.rok === '2022');
    out.push({
      otazka: `Aká bola účasť v komunálnych voľbách 2026 v meste ${m.nazov}?`,
      odpoved: `Voliť prišlo ${des(n.ucast)} % oprávnených voličov${s?.ucast != null ? `, v roku 2022 to bolo ${des(s.ucast)} %` : ''}.`,
      zdroj: 'Štatistický úrad SR (volbysr.sk)', odkaz: '/volby-2026',
    });
  }
  const dm = citaj('data', 'mesta', `${slug}.json`);
  const praca = dm?.praca;
  if (praca?.obdobie) {
    const mes = praca.mesacne?.[praca.obdobie] ?? {};
    // mesto = jeden okres, Bratislava a Košice viac okresov → súčet (podiel cez ekonomicky aktívnych = disp / pdu)
    const okresy: string[] = (dm?.mesto?.okresy ?? [m.nazov]).filter((k: string) => mes[k]?.pdu);
    if (okresy.length) {
      const disp = okresy.reduce((a, k) => a + mes[k].disp, 0), uoz = okresy.reduce((a, k) => a + mes[k].uoz, 0);
      const ea = okresy.reduce((a, k) => a + (mes[k].disp * 100) / mes[k].pdu, 0);
      const [r, mm] = praca.obdobie.split('-');
      const sr = mes['Slovenská republika']?.pdu;
      out.push({
        otazka: `Aká je nezamestnanosť v meste ${m.nazov}?`,
        odpoved: `Podiel disponibilných uchádzačov o zamestnanie bol ${okresy.length > 1 ? `v okresoch ${okresy[0]} – ${okresy[okresy.length - 1].split(' ').pop()}` : `v okrese ${okresy[0]}`} za ${MESIACE[+mm - 1]} ${r} ${des((100 * disp) / ea, 2)} %${sr != null ? `, na Slovensku ${des(sr, 2)} %` : ''}. Na úrade práce bolo evidovaných ${cele(uoz)} uchádzačov.`,
        zdroj: 'Ústredie práce, sociálnych vecí a rodiny', odkaz: ba ? '/bratislava/obyvatelia' : `/${slug}#praca`,
      });
    }
  }
  const cena = posledny(ua(slug, 'Priemerná cena za kúpu bytu za m2'));
  if (cena) {
    out.push({
      otazka: `Koľko stojí byt v meste ${m.nazov}?`,
      odpoved: `Priemerná cena za kúpu bytu bola v roku ${cena[0]} asi ${cele(cena[1])} € za m². Byt s rozlohou 60 m² teda vychádzal približne na ${cele(cena[1] * 60)} €.`,
      zdroj: 'Štatistický úrad SR (Urban Audit)', odkaz: '/porovnaj?a=' + slug,
    });
  }
  if (por?.vs != null) {
    out.push({
      otazka: `Koľko ľudí v meste ${m.nazov} má vysokoškolské vzdelanie?`,
      odpoved: `Podľa sčítania 2021 má vysokoškolské vzdelanie ${des(por.vs)} % obyvateľov od 15 rokov.${por.seniori != null ? ` Ľudia nad 65 rokov tvoria ${des(por.seniori)} % obyvateľov, deti do 14 rokov ${des(por.deti)} %.` : ''}`,
      zdroj: 'Sčítanie obyvateľov, domov a bytov 2021', odkaz: ba ? '/bratislava/obyvatelia' : `/${slug}#obyvatelia`,
    });
  }
  return out;
}

/** JSON-LD FAQPage pre Base (prop jsonld). */
export const faqLd = (slug: string) => {
  const q = otazkyMesta(slug);
  return q.length ? { '@type': 'FAQPage', mainEntity: q.map((x) => ({ '@type': 'Question', name: x.otazka, acceptedAnswer: { '@type': 'Answer', text: x.odpoved } })) } : null;
};
