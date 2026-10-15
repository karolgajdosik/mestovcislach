// Podklady pre AI asistenta: stručné fakty z dát webu rozdelené do tém + zoznam miest na vyhľadávanie.
// Generuje sa pri builde do /data/asistent.json, Pages Function /api/asistent si z neho vyberá podľa otázky.
import fs from 'node:fs';
import path from 'node:path';

const nacitaj = (subor: string, priecinok = 'data') => {
  const p = path.join(process.cwd(), priecinok, subor);
  return fs.existsSync(p) ? JSON.parse(fs.readFileSync(p, 'utf-8')) : null;
};
const zaokr = (n: number) => Math.round(n);
const posledne = <T,>(o: Record<string, T>, n: number) => Object.fromEntries(Object.entries(o).sort().slice(-n));

export async function GET() {
  const obyv = nacitaj('obyvatelstvo-bratislava.json');
  const nazvyMC = new Map<string, string>((obyv?.mestske_casti ?? []).map((c: any) => [c.kod.slice(-6), c.nazov_kratky]));
  const mc = (kod: string) => nazvyMC.get(kod) ?? kod;
  const temy: Record<string, { nazov: string; stranka: string; fakty: any }> = {};

  if (obyv) {
    const rok = Object.keys(obyv.mesto.roky).sort().pop()!;
    temy.obyvatelstvo = {
      nazov: 'Obyvateľstvo', stranka: '/',
      fakty: {
        zdroj: 'ŠÚ SR, trvale bývajúci obyvatelia k 31. 12.',
        mesto_po_rokoch: posledne(obyv.mesto.roky, 12),
        mestske_casti: obyv.mestske_casti.map((c: any) => ({ nazov: c.nazov_kratky, [rok]: c.roky[rok], [String(+rok - 10)]: c.roky[String(+rok - 10)] })),
      },
    };
  }
  const volby = nacitaj('volby-bratislava.json');
  if (volby) {
    temy.volby = {
      nazov: 'Voľby', stranka: '/volby',
      fakty: volby.volby.map((v: any) => ({
        volby: v.nazov, datum: v.datum,
        bratislava: { ucast_pct: v.mesto.ucast, strany_pct: v.mesto.strany.slice(0, 10).map((s: any) => `${s.nazov} ${s.podiel}`) },
        slovensko: { ucast_pct: v.slovensko?.ucast, strany_pct: v.slovensko?.strany?.slice(0, 8).map((s: any) => `${s.nazov} ${s.podiel}`) },
        mestske_casti: v.mestske_casti.map((c: any) => ({ nazov: mc(c.kod_obce) ?? c.nazov, ucast_pct: c.ucast, prve_tri: c.strany.slice(0, 3).map((s: any) => `${s.nazov} ${s.podiel}`) })),
      })),
    };
  }
  const rozp = nacitaj('rozpocet-bratislava.json');
  const zmluvy = nacitaj('zmluvy-bratislava.json');
  const majetok = nacitaj('majetok-bratislava.json');
  if (rozp) {
    temy.rozpocet = {
      nazov: 'Rozpočet mesta', stranka: '/financie',
      fakty: { jednotka: 'EUR, skutočnosť', ...Object.fromEntries(Object.entries(rozp.casti).map(([k, c]: [string, any]) => [k, posledne(c.roky, 3)])) },
    };
  }
  if (zmluvy) {
    temy.zmluvy = {
      nazov: 'Zmluvy magistrátu', stranka: '/financie',
      fakty: {
        po_rokoch: zmluvy.po_rokoch,
        najvacsi_dodavatelia_za_posledny_rok: zmluvy.posledny_rok.dodavatelia.slice(0, 10).map((d: any) => `${d.nazov} (IČO ${d.ico}): ${d.pocet} zmlúv, ${zaokr(d.suma)} €`),
        najvacsie_zmluvy: zmluvy.posledny_rok.najvacsie.slice(0, 10).map((z: any) => `${z.datum} ${z.dodavatel}: ${z.predmet} – ${zaokr(z.suma)} €`),
      },
    };
  }
  if (majetok) {
    temy.majetok = { nazov: 'Majetok mesta', stranka: '/financie', fakty: { spolu: majetok.spolu, druhy: majetok.druhy, spravcovia: majetok.spravcovia.slice(0, 8) } };
  }
  const mhd = nacitaj('doprava-bratislava.json');
  const stat = nacitaj('doprava-statistiky-bratislava.json');
  if (mhd) {
    temy.mhd = {
      nazov: 'MHD', stranka: '/doprava#doprava',
      fakty: {
        typicky_pracovny_den: mhd.den, mesto: mhd.mesto,
        mestske_casti: mhd.mestske_casti.map((c: any) => ({ nazov: mc(c.kod_obce), zastavky: c.zastavky, linky: c.linky, odchody_za_den: c.odchody })),
        najvytazenejsie_zastavky: mhd.zastavky.slice(0, 10).map((z: any) => `${z.nazov}: ${z.odchody} odchodov, linky ${z.linky.join(', ')}`),
        cestujuci_rocne: stat?.cestujuci?.rocne,
      },
    };
  }
  if (stat?.nehody) {
    temy.nehody = { nazov: 'Dopravné nehody (historické, okresy)', stranka: '/doprava', fakty: { poznamka: 'aktuálne nehody mesto nezverejňuje', ...stat.nehody.vsetky?.okresy } };
  }
  const scit = nacitaj('scitace-bratislava.json');
  if (scit) {
    temy.scitace = {
      nazov: 'Sčítače dopravy – kedy je najviac premávky', stranka: '/doprava#premavka',
      fakty: {
        obdobie: scit.obdobie, poznamka: 'autá merajú len 4 sčítače v centre; hodina = začiatok hodiny',
        ...Object.fromEntries(Object.entries(scit.kategorie).map(([k, v]: [string, any]) => [k, v.scitace.map((s: any) =>
          `${s.nazov}: ${s.pracovny_den_spolu}/pracovný deň, ranná špička ${s.spicka_rano?.hodina}:00 (${s.spicka_rano?.pocet}/h), popoludní ${s.spicka_vecer?.hodina}:00 (${s.spicka_vecer?.pocet}/h)`)])),
      },
    };
  }
  const cyklo = nacitaj('cyklo-bratislava.json');
  const bajk = nacitaj('bajk-bratislava.json');
  if (cyklo) {
    temy.cyklo = {
      nazov: 'Cyklotrasy a BAjk', stranka: '/doprava#cyklo',
      fakty: { km_spolu: zaokr(cyklo.mesto.km_spolu), km: cyklo.mesto.km, stanice_bajk: bajk?.stanice.length, mestske_casti_km: cyklo.mestske_casti.map((c: any) => `${c.nazov} ${c.km_spolu.toFixed(1)}`) },
    };
  }
  const skoly = nacitaj('skoly-bratislava.json');
  if (skoly) {
    temy.skoly = {
      nazov: 'Školy a škôlky', stranka: '/vybavenost',
      fakty: Object.fromEntries(Object.entries(skoly.typy).map(([k, t]: [string, any]) => [k === 'zs' ? 'zakladne_skoly' : 'materske_skoly', {
        spolu: t.spolu, zriadovatel: t.zriadovatel, mestske_casti: Object.fromEntries(Object.entries(t.mestske_casti).map(([kod, n]) => [mc(kod), n])),
      }])),
    };
  }
  const vyb = nacitaj('vybavenost-bratislava.json');
  if (vyb) {
    temy.vybavenost = {
      nazov: 'Lekárne, zdravotníctvo, nabíjanie (počty, OpenStreetMap)', stranka: '/vybavenost',
      fakty: { mesto: vyb.mesto, mestske_casti: vyb.mestske_casti.map((c: any) => `${c.nazov}: lekárne ${c.lekarne}, nemocnice ${c.nemocnice}, ambulancie ${c.ambulancie}, nabíjacie stanice ${c.nabijanie}`) },
    };
  }
  const ovz = nacitaj('ovzdusie-bratislava.json');
  if (ovz) {
    temy.ovzdusie = {
      nazov: 'Kvalita ovzdušia (ročné hodnoty)', stranka: '/prostredie',
      fakty: Object.fromEntries(Object.entries(ovz.ukazovatele).map(([k, u]: [string, any]) => [k, { popis: u.popis, jednotka: u.jednotka, limit: u.limit, stanice: Object.fromEntries(Object.entries(u.stanice).map(([s, r]: [string, any]) => [s, posledne(r, 4)])) }])),
    };
  }
  const pr = nacitaj('prostredie-bratislava.json');
  if (pr) {
    const rokV = Object.keys(pr.vysadba.roky).sort().pop()!;
    temy.prostredie = {
      nazov: 'Odpad, výsadba stromov, čierne skládky', stranka: '/prostredie',
      fakty: {
        odpad_kg_na_obyvatela: pr.odpad.na_obyvatela.roky, recyklacia_pct: pr.odpad.recyklacia.roky, skladkovanie_pct: pr.odpad.skladkovanie.roky,
        [`vysadba_${rokV}`]: Object.fromEntries(Object.entries(pr.vysadba.roky[rokV]).map(([k, v]) => [mc(k), v])),
        [`cierne_skladky_${pr.cierne_skladky.rok}`]: pr.cierne_skladky.body.length,
      },
    };
  }
  const prir = nacitaj('priroda-bratislava.json');
  if (prir) {
    temy.priroda = {
      nazov: 'Chránená príroda', stranka: '/prostredie',
      fakty: { mesto: prir.mesto, mestske_casti: prir.mestske_casti.map((c: any) => `${c.nazov}: chránené ${c.chranene_pct} %, Natura 2000 ${c.natura_pct} %`), najvacsie_uzemia: prir.uzemia.slice(0, 12).map((u: any) => `${u.nazov} (${u.kategoria}) ${u.km2_v_meste} km²`) },
    };
  }

  // Miesta na vyhľadávanie podľa názvu / kategórie / mestskej časti
  const hranice = nacitaj('hranice-bratislava.geojson');
  const polygony: [string, number[][][][]][] = (hranice?.features ?? []).map((f: any) =>
    [mc(f.properties.kod_obce), f.geometry.type === 'Polygon' ? [f.geometry.coordinates] : f.geometry.coordinates]);
  const vnutri = (x: number, y: number, ring: number[][]) => {
    let v = false;
    for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
      const [xi, yi] = ring[i], [xj, yj] = ring[j];
      if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) v = !v;
    }
    return v;
  };
  const castPre = (lat: number, lon: number) => polygony.find(([, mp]) => mp.some((p) => vnutri(lon, lat, p[0]) && !p.slice(1).some((h) => vnutri(lon, lat, h))))?.[0] ?? '';
  const miesta: any[] = [];
  for (const subor of ['vybavenost-bratislava.json', 'pamiatky-bratislava.json']) {
    const d = nacitaj(subor, 'public/data');
    for (const [lat, lon, kat, nazov, det] of d?.body ?? []) {
      miesta.push({ n: nazov, k: d.kategorie[kat] ?? kat, c: castPre(lat, lon), lat, lon, ...(det ?? {}) });
    }
  }
  for (const z of mhd?.zastavky ?? []) miesta.push({ n: z.nazov, k: 'Zastávka MHD', c: mc(z.kod_obce), lat: z.lat, lon: z.lon, linky: z.linky.join(', '), odchody: z.odchody });
  for (const s of bajk?.stanice ?? []) miesta.push({ n: s.nazov, k: 'Stanica BAjk', c: mc(s.kod_obce), lat: s.lat, lon: s.lon });
  for (const m of miesta) { delete m.f; delete m.id; }

  return new Response(JSON.stringify({ temy, miesta, mestske_casti: [...nazvyMC.values()] }), { headers: { 'Content-Type': 'application/json' } });
}
