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
      nazov: 'Obyvateľstvo', stranka: '/bratislava',
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
      nazov: 'Voľby', stranka: '/bratislava/volby',
      fakty: volby.volby.map((v: any) => ({
        volby: v.nazov, datum: v.datum,
        bratislava: { ucast_pct: v.mesto.ucast, strany_pct: v.mesto.strany.slice(0, 10).map((s: any) => `${s.nazov} ${s.podiel}`) },
        slovensko: { ucast_pct: v.slovensko?.ucast, strany_pct: v.slovensko?.strany?.slice(0, 8).map((s: any) => `${s.nazov} ${s.podiel}`) },
        mestske_casti: v.mestske_casti.map((c: any) => ({ nazov: mc(c.kod_obce) ?? c.nazov, ucast_pct: c.ucast, prve_tri: c.strany.slice(0, 3).map((s: any) => `${s.nazov} ${s.podiel}`) })),
      })),
    };
  }
  const kom = nacitaj('komunalne-bratislava.json');
  if (kom) {
    const viz = (k: any[]) => k?.find((x: any) => x.zvoleny);
    temy.komunalne = {
      nazov: 'Komunálne a krajské voľby (primátor, starostovia, zastupiteľstvá, BSK)', stranka: '/bratislava/volby#komunalne',
      fakty: kom.volby.map((v: any) => v.stav !== 'vysledky' ? {
        volby: v.nazov, datum: v.datum, stav: 'výsledky ešte nie sú zverejnené – web ich doplní automaticky po zverejnení ŠÚ SR',
        kandidati_na_primatora: v.kandidati_primator?.map((x: any) => `${x.meno} (${x.strany})`) ?? 'Štatistický úrad SR ho zatiaľ nezverejnil v otvorených dátach (kandidátov poznať z médií a webu mesta)',
        kandidati_na_predsedu_bsk: v.kandidati_predseda_bsk?.map((x: any) => `${x.meno} (${x.strany})`),
      } : {
        volby: v.nazov, datum: v.datum,
        primator: { ucast_pct: v.oso.primator.ucast.ucast_pct, kandidati: v.oso.primator.kandidati.map((c: any) => `${c.meno} (${c.strany}) ${c.podiel} %${c.zvoleny ? ' – ZVOLENÝ' : ''}`) },
        primator_podla_mestskych_casti: v.oso.primator.mestske_casti.map((m: any) => `${m.nazov}: účasť ${m.ucast} %, ${m.poradie.slice(0, 2).map((x: any) => `${x.meno} ${x.podiel} %`).join(', ')}`),
        mestske_zastupitelstvo_mandaty: v.oso.mestske_zastupitelstvo.mandaty.map((m: any) => `${m.strany}: ${m.mandaty}`),
        starostovia: v.oso.starostovia.map((st: any) => { const z = viz(st.kandidati); return `${st.nazov}: ${z ? `${z.meno} (${z.strany}) ${z.podiel} %` : '–'}, účasť ${st.ucast.ucast_pct} %, kandidátov ${st.kandidati.length}`; }),
        predseda_bsk: v.osk ? { ucast_kraj_pct: v.osk.predseda.kraj.ucast.ucast_pct, kandidati: v.osk.predseda.kraj.kandidati.slice(0, 6).map((c: any) => `${c.meno} (${c.strany}) ${c.podiel} %${c.zvoleny ? ' – ZVOLENÝ' : ''}`) } : undefined,
        krajski_poslanci_za_bratislavu: v.osk?.poslanci_za_bratislavu.mandaty.map((m: any) => `${m.strany}: ${m.mandaty}`),
      }),
    };
  }
  const sc = nacitaj('scitanie-bratislava.json');
  if (sc) {
    const podiely = (d: Record<string, number>, kat: string[]) => {
      const sp = kat.reduce((a, k) => a + (d[k] ?? 0), 0) || 1;
      return kat.filter((k) => (d[k] ?? 0) > 0).map((k) => `${k.replace(/ \(.*$/, '').trim()} ${Math.round((1000 * (d[k] ?? 0)) / sp) / 10} %`).join('; ');
    };
    const temySc: any = {};
    for (const [t, td] of Object.entries<any>(sc.temy)) {
      const kat = td.kategorie.filter((k: string) => !/0-14 rokov|^Neznáme$/.test(k));
      temySc[td.nazov] = { Bratislava: podiely(td.mesto, kat), ...Object.fromEntries(Object.entries<any>(td.mestske_casti).map(([mc, d]) => [mc, podiely(d, kat)])) };
    }
    temy.scitanie = { nazov: 'Sčítanie obyvateľov 2021 (k 1. 1. 2021): vek, vzdelanie (z obyvateľov 15+), národnosť, jazyk, viera, rodinný stav, domácnosti, byty', stranka: '/bratislava/obyvatelia', fakty: temySc };
  }
  const rozp = nacitaj('rozpocet-bratislava.json');
  const zmluvy = nacitaj('zmluvy-bratislava.json');
  const majetok = nacitaj('majetok-bratislava.json');
  if (rozp) {
    temy.rozpocet = {
      nazov: 'Rozpočet mesta', stranka: '/bratislava/financie',
      fakty: { jednotka: 'EUR, skutočnosť', ...Object.fromEntries(Object.entries(rozp.casti).map(([k, c]: [string, any]) => [k, posledne(c.roky, 3)])) },
    };
  }
  if (zmluvy) {
    temy.zmluvy = {
      nazov: 'Zmluvy magistrátu', stranka: '/bratislava/financie',
      fakty: {
        po_rokoch: zmluvy.po_rokoch,
        najvacsi_dodavatelia_za_posledny_rok: zmluvy.posledny_rok.dodavatelia.slice(0, 10).map((d: any) => `${d.nazov} (IČO ${d.ico}): ${d.pocet} zmlúv, ${zaokr(d.suma)} €`),
        najvacsie_zmluvy: zmluvy.posledny_rok.najvacsie.slice(0, 10).map((z: any) => `${z.datum} ${z.dodavatel}: ${z.predmet} – ${zaokr(z.suma)} €`),
      },
    };
  }
  const nez = nacitaj('nezamestnanost-bratislava.json');
  if (nez) {
    temy.nezamestnanost = {
      nazov: 'Nezamestnanosť v okresoch Bratislava I–V (ŠÚ SR, k 31. 12.)', stranka: '/bratislava/obyvatelia#nezamestnanost',
      fakty: { okresy_a_mestske_casti: nez.okresy_mc,
        mesacne_upsvr_pdu_a_pocet_uchadzacov: Object.fromEntries(Object.entries<any>(nez.mesacne ?? {}).slice(-13).map(([k, v]) => [k, Object.fromEntries(Object.entries<any>(v).map(([u, x]) => [u, `PDU ${x.pdu} %, uchádzači ${x.uoz}`]))])),
        ...Object.fromEntries(Object.entries<any>(nez.ukazovatele).filter(([k]) => /miera|disponib/i.test(k))
        .map(([k, v]) => [k, Object.fromEntries(Object.entries<any>(v).map(([u, r]) => [u, Object.fromEntries(Object.entries<any>(r).filter(([y]) => Number(y) >= 2015))]))])) },
    };
  }
  const eia = nacitaj('eia-bratislava.json');
  if (eia) {
    const pred = (r: number) => new Date(Date.now() - r * 365 * 864e5).toISOString().slice(0, 10);
    const zam = eia.zamery.filter((z: any) => !z.ukoncene || z.zmena >= pred(3));
    const KAT: Record<string, string> = { byvanie: 'bývanie a polyfunkcia', obcianska: 'obchod, kancelárie, služby', doprava: 'doprava', priemysel: 'priemysel a sklady', odpady: 'odpady', energia: 'energetika', voda: 'voda a kanalizácia', plan: 'územný plán alebo koncepcia', ine: 'iné' };
    const mc: Record<string, number> = {};
    for (const z of eia.zamery.filter((x: any) => !x.ukoncene)) for (const m of z.mc) mc[m] = (mc[m] ?? 0) + 1;
    temy.stavby = {
      nazov: 'Čo sa stavia – zámery v posudzovaní vplyvov na životné prostredie (EIA/SEA, Enviroportál)', stranka: '/bratislava/vystavba#co-sa-stavia',
      fakty: {
        poznamka: 'Zámery väčších stavieb a plánov, ktoré prešli alebo prechádzajú posudzovaním EIA/SEA. Nie je to zoznam všetkých stavieb ani stavebných povolení. K prebiehajúcemu zámeru sa môže vyjadriť verejnosť – lehota a dokumenty sú na Enviroportáli.',
        prave_sa_posudzuje_spolu: eia.zamery.filter((z: any) => !z.ukoncene).length,
        prebiehajuce_podla_mestskych_casti: mc,
        zamery: zam.map((z: any) => ({ nazov: z.nazov, mc: z.mc, kat: KAT[z.kat] ?? z.kat, stav: z.stav, ukoncene: z.ukoncene, zmena: z.zmena, navrhovatel: z.navrhovatel, ucel: (z.ucel ?? '').slice(0, 260), url: `https://www.enviroportal.sk/eia/detail/${z.seo}` })),
      },
    };
  }
  const byv = nacitaj('byvanie-bratislava.json');
  if (byv) {
    const rad = byv.ceny.rad;
    const roky = Object.keys(byv.vystavba.roky).sort().slice(-10);
    temy.byvanie = {
      nazov: 'Bývanie: ceny nehnuteľností (ŠÚ SR, index realizačných cien) a výstavba bytov (ŠÚ SR)', stranka: '/bratislava/vystavba#ceny',
      fakty: {
        poznamka: 'Ceny sú len ako index za Bratislavský kraj (nie €/m², nie za mestské časti). Index rr = rovnaké obdobie minulého roka 100; idx = 1. štvrťrok 2022 = 100. Údaje o výstavbe za rok 2025 sú z nového registra a nemusia byť porovnateľné.',
        ceny_po_stvrtrokoch: rad.slice(-12).map((r: any) => `${r.obdobie}: BA kraj medziročne ${(r.ba_total_rr - 100).toFixed(1)} % (novostavby ${(r.ba_dw_new_rr - 100).toFixed(1)} %, staršie ${(r.ba_dw_exst_rr - 100).toFixed(1)} %), SR ${(r.sr_total_rr - 100).toFixed(1)} %; od 1. Q 2022 BA +${(r.ba_total_idx - 100).toFixed(1)} %`),
        byty_bratislava_po_rokoch: Object.fromEntries(roky.map((r) => [r, `dokončené ${byv.vystavba.roky[r].Bratislava.DOKONC_BYT}, začaté ${byv.vystavba.roky[r].Bratislava.ZAC_BYT}, rozostavané k 31.12. ${byv.vystavba.roky[r].Bratislava.ROZOST_BYT_KON}`])),
        okresy_posledny_rok: Object.fromEntries(Object.entries<any>(byv.vystavba.roky[roky[roky.length - 1]]).filter(([o]) => o !== 'Bratislava').map(([o, v]) => [`${o} (${byv.vystavba.okresy_casti[o]})`, `dokončené ${v.DOKONC_BYT}, začaté ${v.ZAC_BYT}`])),
      },
    };
  }
  const zmc = nacitaj('zmluvy-mc.json');
  if (zmc) {
    temy.zmluvy_mc = {
      nazov: `Zmluvy a dotácie mestských častí (Centrálny register zmlúv, ${zmc.od} – ${zmc.do})`, stranka: '/bratislava/financie#zmluvy-mc',
      fakty: {
        poznamka: 'Hodnota = suma uvedená v zmluvách. Zmluvy s fyzickými osobami sú len započítané, bez mien. Dotácie = zmluvy s dotáciou alebo grantom v predmete; poskytnuté = mestská časť ich dala klubom a združeniam, prijaté = dostala ich od štátu, kraja, mesta alebo fondov.',
        ...Object.fromEntries(Object.entries<any>(zmc.mestske_casti).map(([mc, v]) => [mc, {
          zmluv: v.zmluv, hodnota_eur: v.suma, zmluv_s_fyzickymi_osobami: v.fyzicke_osoby.zmluv,
          po_rokoch: Object.fromEntries(Object.entries<any>(v.roky).map(([r, [n, sm]]) => [r, `${n} zmlúv, ${zaokr(sm)} €`])),
          najvacsi_partneri: v.najvacsi_partneri.slice(0, 6).map((x: any) => `${x.nazov}${x.ico ? ` (IČO ${x.ico})` : ''}: ${x.zmluv} zmlúv, ${zaokr(x.suma)} €`),
          najvacsie_zmluvy: v.najvacsie_zmluvy.slice(0, 4).map((z: any) => `${z.d} ${z.p}: ${z.pr ?? ''} – ${zaokr(z.s)} €`),
          dotacie_poskytnute_mestskou_castou: (() => { const d = zmc.dotacie[mc]?.poskytnute ?? zmc.dotacie[mc]; return d?.prijimatelia ? `${d.zmluv} zmlúv, ${zaokr(d.suma)} €; príjemcovia: ${d.prijimatelia.slice(0, 6).map((x: any) => `${x.nazov} ${zaokr(x.suma)} €`).join('; ')}` : 'žiadne'; })(),
          dotacie_prijate_mestskou_castou: (() => { const d = zmc.dotacie[mc]?.prijate; return d?.poskytovatelia?.length ? `${d.zmluv} zmlúv, ${zaokr(d.suma)} €; od: ${d.poskytovatelia.slice(0, 4).map((x: any) => `${x.nazov} ${zaokr(x.suma)} €`).join('; ')}` : 'žiadne'; })(),
        }])),
      },
    };
  }
  if (majetok) {
    temy.majetok = { nazov: 'Majetok mesta', stranka: '/bratislava/financie', fakty: { spolu: majetok.spolu, druhy: majetok.druhy, spravcovia: majetok.spravcovia.slice(0, 8) } };
  }
  const mhd = nacitaj('doprava-bratislava.json');
  const stat = nacitaj('doprava-statistiky-bratislava.json');
  if (mhd) {
    temy.mhd = {
      nazov: 'MHD', stranka: '/bratislava/doprava#doprava',
      fakty: {
        typicky_pracovny_den: mhd.den, mesto: mhd.mesto,
        mestske_casti: mhd.mestske_casti.map((c: any) => ({ nazov: mc(c.kod_obce), zastavky: c.zastavky, linky: c.linky, odchody_za_den: c.odchody })),
        najvytazenejsie_zastavky: mhd.zastavky.slice(0, 10).map((z: any) => `${z.nazov}: ${z.odchody} odchodov, linky ${z.linky.join(', ')}`),
        cestujuci_rocne: stat?.cestujuci?.rocne,
      },
    };
  }
  if (stat?.nehody) {
    temy.nehody = { nazov: 'Dopravné nehody (historické, okresy)', stranka: '/bratislava/doprava', fakty: { poznamka: 'aktuálne nehody mesto nezverejňuje', ...stat.nehody.vsetky?.okresy } };
  }
  const scit = nacitaj('scitace-bratislava.json');
  if (scit) {
    temy.scitace = {
      nazov: 'Sčítače dopravy – kedy je najviac premávky', stranka: '/bratislava/doprava#premavka',
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
      nazov: 'Cyklotrasy a BAjk', stranka: '/bratislava/doprava#cyklo',
      fakty: { km_spolu: zaokr(cyklo.mesto.km_spolu), km: cyklo.mesto.km, stanice_bajk: bajk?.stanice.length, mestske_casti_km: cyklo.mestske_casti.map((c: any) => `${c.nazov} ${c.km_spolu.toFixed(1)}`) },
    };
  }
  const skoly = nacitaj('skoly-bratislava.json');
  if (skoly) {
    temy.skoly = {
      nazov: 'Školy a škôlky', stranka: '/bratislava/vybavenost',
      fakty: Object.fromEntries(Object.entries(skoly.typy).map(([k, t]: [string, any]) => [k === 'zs' ? 'zakladne_skoly' : 'materske_skoly', {
        spolu: t.spolu, zriadovatel: t.zriadovatel, mestske_casti: Object.fromEntries(Object.entries(t.mestske_casti).map(([kod, n]) => [mc(kod), n])),
      }])),
    };
  }
  const iedu = nacitaj('skoly-iedu.json');
  if (iedu) {
    temy.skoly ??= { nazov: 'Školy a škôlky', stranka: '/bratislava/vybavenost', fakty: {} };
    Object.assign(temy.skoly.fakty, {
      ziaci_a_skoly_mesto: Object.fromEntries(Object.entries<any>(iedu.mesto).map(([t, v]) => [iedu.typy[t], v])),
      ziaci_podla_mc: Object.fromEntries(Object.entries<any>(iedu.mestske_casti).map(([m, t]) => [m, `ZŠ ${t.zs?.ziakov ?? 0} žiakov (${t.zs?.skol ?? 0} škôl), MŠ ${t.ms?.ziakov ?? 0} detí, SŠ ${t.ss?.ziakov ?? 0} žiakov`])),
      najvacsie_zs: iedu.najvacsie.zs.map((x: any) => `${x.nazov} (${x.mc}) ${x.ziaci}`),
      najvacsie_ss: iedu.najvacsie.ss.map((x: any) => `${x.nazov} (${x.mc}) ${x.ziaci}`),
      najvacsi_zaujem_o_ss: iedu.zaujem_ss.najzaujimavejsie.slice(0, 10).map((x: any) => `${x.nazov.replace(/,? ako organizačná zložka.*$/, '')}, ${x.adresa}: ${x.zaujem1} prihlášok s 1. voľbou`),
      zdroj_cisel: 'MŠVVaM SR – Digitálna mapa škôl (žiaci, pedagógovia, rozpočet 2024); spádovú školu podľa adresy nájde vyhľadávanie na /vybavenost#spadova-skola',
    });
  }
  const soc = nacitaj('socialne-bratislava.json');
  if (soc) {
    temy.socialne = {
      nazov: 'Jasle a sociálne služby (register MPSVR SR)', stranka: '/bratislava/vybavenost#socialne',
      fakty: { sluzieb: soc.sluzieb, druhy: soc.druhy.map((d: any) => `${d.druh}: ${d.pocet}${d.kapacita ? `, kapacita ${d.kapacita}` : ''}`), mestske_casti: soc.mestske_casti, poznamka: 'len aktívne služby s adresou v Bratislave, bez terénnych služieb; konkrétne zariadenia sú v miestach (Jasle, Sociálne služby)' },
    };
  }
  const ukaz = nacitaj('mc-ukazovatele.json');
  if (ukaz?.dlh) {
    const roky = Object.keys(ukaz.dlh.roky).sort();
    temy.rozpocet ??= { nazov: 'Rozpočet mesta', stranka: '/bratislava/financie', fakty: {} };
    temy.rozpocet.fakty.dlh = {
      popis: ukaz.dlh.popis,
      hlavne_mesto_podla_rokov: Object.fromEntries(roky.map((y) => [y, ukaz.dlh.roky[y]['Hlavné mesto']])),
      [`mestske_casti_${roky[roky.length - 1]}`]: Object.fromEntries(Object.entries<any>(ukaz.dlh.roky[roky[roky.length - 1]]).filter(([k]) => k !== 'Hlavné mesto').map(([k, v]) => [k, `dlh ${v.dlh} €, ${v.pomer} % príjmov`])),
    };
  }
  const hosp = nacitaj('mesta/hospodarenie.json');
  if (hosp?.mestske_casti) {
    const mm = (n: number) => `${(n / 1e6).toFixed(2).replace('.', ',')} mil. €`;
    const riadok = (r: any) => `výnosy ${mm(r.vynosy)} (daňové ${mm(r.danove_vynosy ?? 0)}), náklady ${mm(r.naklady)}, výsledok ${mm(r.vysledok)}, bankové úvery ${mm(r.bankove_uvery ?? 0)}, majetok ${mm(r.majetok ?? 0)}`;
    temy.rozpocet ??= { nazov: 'Rozpočet mesta', stranka: '/bratislava/financie', fakty: {} };
    const ba = hosp.mesta?.bratislava?.roky ?? {};
    temy.rozpocet.fakty.hospodarenie_uctovne_zavierky = {
      popis: 'Individuálne účtovné závierky z Registra účtovných závierok (akruálne výnosy a náklady, nie rozpočet; bez škôl a organizácií). Stránka /bratislava/financie#hospodarenie.',
      hlavne_mesto: Object.fromEntries(Object.entries<any>(ba).slice(-5).map(([r, v]) => [r, riadok(v)])),
      mestske_casti_posledny_rok: Object.fromEntries(Object.entries<any>(hosp.mestske_casti).map(([mc, v]) => { const r = Object.keys(v.roky).sort().pop()!; return [mc, `${r}: ${riadok(v.roky[r])}`]; })),
    };
  }
  if (ukaz?.index_rozvoja) {
    temy.rozvoj = { nazov: 'Index regionálneho rozvoja mestských častí (MIRRI SR)', stranka: '/bratislava/obyvatelia#index-rozvoja', fakty: ukaz.index_rozvoja };
  }
  const pamReg = nacitaj('pamiatky-register.json');
  if (pamReg) {
    temy.pamiatky = { nazov: 'Kultúrne pamiatky – register MK SR', stranka: '/bratislava/mapa#pamiatky', fakty: { ...pamReg, zdroj: pamReg.zdroj.nazov } };
  }
  const csd = nacitaj('csd-bratislava.json');
  if (csd) {
    temy.csd = { nazov: 'Celoštátne sčítanie dopravy (diaľnice a cesty)', stranka: '/bratislava/doprava#csd', fakty: { popis: csd.popis, narast_2005_2015: csd.narast_2005_2015, cesty: csd.cesty.slice(0, 16), najvytazenejsie_useky_2015: csd.useky_2015.slice(0, 8) } };
  }
  const hl = nacitaj('hlasovania-msz.json');
  if (hl) {
    temy.hlasovania = {
      nazov: hl.obdobia['9']?.z_webu_od ? `Hlasovania poslancov mestského zastupiteľstva (12/2014 – ${hl.obdobia['9'].do.slice(5, 7)}/${hl.obdobia['9'].do.slice(0, 4)})` : 'Hlasovania poslancov mestského zastupiteľstva (otvorené dáta 12/2014 – 6/2023)', stranka: '/bratislava/volby#hlasovania',
      fakty: {
        poznamka: hl.obdobia['9']?.z_webu_od
          ? `Do júna 2023 z otvorených dát mesta, od ${hl.obdobia['9'].z_webu_od} z webu zastupitelstvo.bratislava.sk. Údaje obdobia 2022–2026 siahajú do ${hl.obdobia['9'].do}.`
          : 'Otvorené dáta mesta obsahujú hlasovania len do júna 2023; z obdobia 2022–2026 len 12/2022–6/2023. Novšie hlasovania sú len v dokumentoch na zastupitelstvo.bratislava.sk.',
        ...Object.fromEntries(Object.entries<any>(hl.obdobia).map(([, o]) => [`obdobie ${o.nazov}`, {
          hlasovani: o.hlasovani, zasadnuti: o.zasadnuti, od: o.od, do: o.do,
          kluby: o.kluby.map((k: any) => `${k.klub}: ${k.clenov} členov, jednotnosť ${k.jednotnost} %`),
          poslanci: o.poslanci.map((p: any) => `${p.meno} (${p.klub}): prítomnosť ${p.pritomnost} %, za ${p.za}, proti ${p.proti}, zdržal ${p.zdrzal}, zhoda s väčšinou ${p.zhoda_s_vacsinou} %, s klubom ${p.zhoda_s_klubom} %`),
        }])),
      },
    };
  }
  const bez = nacitaj('bezpecnost-bratislava.json');
  if (bez) {
    const cist = (t: string) => t.replace(/^\d+\s*-\s*/, '');
    const udal = (u: any) => u && { spolu: u.spolu, roky: u.roky, druhy: u.druhy.slice(0, 10).map((d: any) => `${cist(d.druh)}: ${d.pocet}`),
      ulice: u.ulice.slice(0, 10).map((x: any) => `${x.ulica} (${x.mc}): ${x.pocet}`),
      mestske_casti: Object.fromEntries(Object.entries<any>(u.mestske_casti).map(([m, v]) => [m, v.roky])) };
    temy.bezpecnost = {
      nazov: 'Bezpečnosť – evidencia mestskej polície 2017–2022 a podnety občanov', stranka: '/bratislava/bezpecnost',
      fakty: { poznamka: 'Mesto zverejnilo údaje mestskej polície len za 2017–2022; trestné činy rieši najmä Policajný zbor SR.',
        priestupky: udal(bez.priestupky), podozrenia_z_trestnych_cinov: udal(bez.trestne_ciny), ine_zasahy: udal(bez.ostatne),
        podnety_obcanov: bez.podnety && { spolu: bez.podnety.spolu, roky: bez.podnety.roky, kategorie: bez.podnety.kategorie.slice(0, 10), stavy: bez.podnety.stavy, median_dni: bez.podnety.median_dni_vyriesenia } },
    };
  }
  const fakt = nacitaj('faktury-bratislava.json');
  if (fakt) {
    temy.faktury = {
      nazov: 'Faktúry, objednávky a zmluvy magistrátu a mestských firiem (OLO, Marianum, MIB)', stranka: '/bratislava/financie#faktury',
      fakty: Object.fromEntries(fakt.datasety.map((d: any) => [`${d.organizacia} – ${d.typ}`, {
        roky: Object.fromEntries(Object.entries<any>(d.roky).slice(-5)),
        najvacsi_dodavatelia_3_roky: d.dodavatelia_posledne_3_roky.slice(0, 8).map((x: any) => `${x.nazov}: ${x.suma} € (${x.pocet}×)`),
        median_dni_uhrady: d.median_dni_uhrady ?? undefined,
      }])),
    };
  }
  const vrs = nacitaj('vrstvy-bratislava.json');
  const klima = nacitaj('klima-bratislava.json');
  if (klima) {
    temy.klima = { nazov: 'Klimatický atlas – riziká horúčav a prívalových dažďov (mapa)', stranka: '/bratislava/mapa#horucavy',
      fakty: { poznamka: 'Mapa po štvorcoch 200 × 200 m, hodnoty sa porovnávajú v rámci mesta; konkrétne miesto je na mape (vrstvy Klíma a obyvatelia).', vrstvy: Object.values<any>(klima.vrstvy).map((v) => `${v.nazov}: ${v.popis ?? ''}`) } };
  }
  const katStav = nacitaj('katalog-stav.json');
  temy.hluk = {
    nazov: 'Hluk – strategické hlukové mapy ÚVZ SR', stranka: '/bratislava/mapa#hluk',
    fakty: { popis: 'Mapa izofón 55, 60, 65 a 70 dB pre hluk z ciest (Lden celý deň, Lnight noc) a z priemyslu v aglomerácii Bratislava. Konkrétnu ulicu si treba pozrieť na mape webu (vrstva Hluk). Odporúčanie WHO pre hluk z ciest: najviac 53 dB Lden a 45 dB v noci; vyhláška pre obytné územie pri hlavných cestách: 60 dB cez deň, 50 dB v noci.' },
  };
  const vyb = nacitaj('vybavenost-bratislava.json');
  if (vyb) {
    temy.vybavenost = {
      nazov: 'Lekárne, zdravotníctvo, nabíjanie (počty, OpenStreetMap)', stranka: '/bratislava/vybavenost',
      fakty: { mesto: vyb.mesto, mestske_casti: vyb.mestske_casti.map((c: any) => `${c.nazov}: lekárne ${c.lekarne}, nemocnice ${c.nemocnice}, ambulancie ${c.ambulancie}, nabíjacie stanice ${c.nabijanie}`) },
    };
  }
  const ovz = nacitaj('ovzdusie-bratislava.json');
  if (ovz) {
    temy.ovzdusie = {
      nazov: 'Kvalita ovzdušia (ročné hodnoty)', stranka: '/bratislava/prostredie',
      fakty: Object.fromEntries(Object.entries(ovz.ukazovatele).map(([k, u]: [string, any]) => [k, { popis: u.popis, jednotka: u.jednotka, limit: u.limit, stanice: Object.fromEntries(Object.entries(u.stanice).map(([s, r]: [string, any]) => [s, posledne(r, 4)])) }])),
    };
  }
  const pr = nacitaj('prostredie-bratislava.json');
  if (pr) {
    const rokV = Object.keys(pr.vysadba.roky).sort().pop()!;
    temy.prostredie = {
      nazov: 'Odpad, výsadba stromov, čierne skládky', stranka: '/bratislava/prostredie',
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
      nazov: 'Chránená príroda', stranka: '/bratislava/prostredie',
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
  const oficialne = { pamiatky: nacitaj('pamiatky-register.json', 'public/data'), stromy: nacitaj('stromy-sop.json', 'public/data') };
  for (const subor of ['vybavenost-bratislava.json', 'pamiatky-bratislava.json']) {
    const d = nacitaj(subor, 'public/data');
    for (const [lat, lon, kat, nazov, det] of d?.body ?? []) {
      if ((oficialne as any)[kat]) continue; // pamiatky a stromy z oficiálnych registrov
      miesta.push({ n: nazov, k: d.kategorie[kat] ?? kat, c: castPre(lat, lon), lat, lon, ...(det ?? {}) });
    }
  }
  for (const [lat, lon, nazov, det] of oficialne.pamiatky?.body ?? []) {
    miesta.push({ n: nazov, k: 'Kultúrne pamiatky', c: det.mc, lat, lon, typ: det.typ, a: det.a, vznik: det.vznik, sloh: det.sloh });
  }
  for (const [lat, lon, nazov, det] of oficialne.stromy?.body ?? []) {
    miesta.push({ n: nazov, k: 'Chránené stromy', c: det.mc, lat, lon, typ: det.druh, a: det.lok });
  }
  const TYP_SKOLY: Record<string, string> = { ms: 'Materská škola', zs: 'Základná škola', ss: 'Stredná škola', spec: 'Špeciálna škola', zus: 'Základná umelecká škola', cvc: 'Centrum voľného času' };
  for (const [lat, lon, t, nazov, det] of nacitaj('skoly-iedu.json', 'public/data')?.body ?? []) {
    miesta.push({ n: nazov, k: TYP_SKOLY[t], c: castPre(lat, lon), lat, lon, a: det.a, w: det.w, ziaci: det.z });
  }
  for (const [lat, lon, kat, nazov, det] of nacitaj('socialne-bratislava.json', 'public/data')?.body ?? []) {
    miesta.push({ n: nazov, k: kat === 'deti' ? 'Jasle' : 'Sociálne služby', c: det.mc, lat, lon, typ: det.druh, a: det.a, w: det.w, kapacita: det.kap });
  }
  for (const z of mhd?.zastavky ?? []) miesta.push({ n: z.nazov, k: 'Zastávka MHD', c: mc(z.kod_obce), lat: z.lat, lon: z.lon, linky: z.linky.join(', '), odchody: z.odchody });
  for (const s of bajk?.stanice ?? []) miesta.push({ n: s.nazov, k: 'Stanica BAjk', c: mc(s.kod_obce), lat: s.lat, lon: s.lon });
  for (const [lat, lon, kat, nazov, det] of nacitaj('vrstvy-bratislava.json', 'public/data')?.body ?? []) {
    const K: Record<string, string> = { bezbarierove: 'Bezbariérové miesta', fontany: 'Pitné fontány', sportoviska: 'Športoviská', bezdomovci: 'Pomoc ľuďom bez domova', veterina: 'Veterinárne ambulancie a kliniky', ochladzovanie: 'Ochladzovacie miesta (Ochlaď sa!)', fixpointy: 'Fixpointy na zber injekčných striekačiek', debarierizacie: 'Debarierizované chodníky' };
    miesta.push({ n: nazov, k: K[kat] ?? kat, c: castPre(lat, lon), lat, lon, typ: det.typ, a: det.a, w: det.w, info: det.info?.join('; ')?.slice(0, 200) });
  }
  for (const m of miesta) { delete m.f; delete m.id; }
  // Katalóg dát: názvy tabuliek pre vyhľadávanie asistentom (údaje načíta funkcia z /data/tabulky/<id>.json)
  const katalog = (katStav?.datasety ?? []).filter((d: any) => d.stav === 'katalog').map((d: any) => ({ id: d.id, n: d.nazov, k: d.kategoria }));

  return new Response(JSON.stringify({ temy, miesta, katalog, mestske_casti: [...nazvyMC.values()] }), { headers: { 'Content-Type': 'application/json' } });
}
