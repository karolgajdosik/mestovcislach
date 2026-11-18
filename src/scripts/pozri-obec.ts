// Oživenie sekcie „Video a prelet“ (PozriObec.astro) – na stránke obce aj vo Videozóne (obsah vložený dodatočne).
import { VideoObce, type VideoData } from './video-obce';
import { kedViditelne } from './ked-viditelne';

/** Spustí video a prelet vo všetkých sekciách v `koren` (každý prvok len raz). */
export function oziv(koren: ParentNode = document) {
  koren.querySelectorAll<HTMLElement>('.pv-video:not([data-ozivene])').forEach((box) => {
    box.dataset.ozivene = '1';
    const canvas = box.querySelector('canvas')!;
    const d = JSON.parse(box.dataset.video!) as VideoData;
    const v = new VideoObce(canvas, d);
    (box as any).__zastav = () => v.pauza(); // Videozóna: pred výmenou obsahu
    const stav = box.querySelector<HTMLElement>('.pv-stav')!;
    const tlHraj = box.querySelector<HTMLButtonElement>('[data-v="hraj"]')!;
    const velke = box.querySelector<HTMLButtonElement>('.pv-hraj')!;
    const format = box.querySelector<HTMLSelectElement>('[data-v="format"]')!;
    const tlStiahni = box.querySelector<HTMLButtonElement>('[data-v="stiahni"]')!;
    // reproduktor: zapnutý = hudba (+ slovenský hlas, ak ho prehliadač má); prečiarknutý = ticho
    const zvuk = box.querySelector<HTMLButtonElement>('[data-v="zvuk"]')!;
    let zapnuty = (() => { try { return localStorage.getItem('video-zvuk') !== 'nie'; } catch { return true; } })();
    const nastavZvuk = () => {
      v.zvuk = zapnuty ? (v.maHlas() ? 'hlas' : 'hudba') : 'nie';
      zvuk.textContent = zapnuty ? '🔊' : '🔇';
      const popis = zapnuty ? 'Vypnúť zvuk' : 'Zapnúť zvuk';
      zvuk.setAttribute('aria-pressed', String(zapnuty)); zvuk.setAttribute('aria-label', popis); zvuk.title = popis;
    };
    nastavZvuk();
    let pripravene: Promise<void> | null = null;
    const priprav = () => (pripravene ??= v.priprav().then(() => {
      v.nastavRozmer(canvas.width, canvas.height);
      // hlasový komentár len ak má prehliadač slovenský hlas; predvolene hudba a hlas
      nastavZvuk(); // až teraz vieme, či je slovenský hlas
    }));
    // fotka a prvý obrázok až keď je video blízko obrazovky
    kedViditelne(box, () => { priprav(); }, '300px');
    const tlacidla = () => { const h = v.jeHra(); tlHraj.textContent = h ? '⏸ Pauza' : '▶ Prehrať'; velke.hidden = h; };
    v.onCas = () => tlacidla();
    const hraj = async () => {
      if (!v.jeHra()) v.odomkniZvuk();
      await priprav();
      if (v.jeHra()) { v.pauza(); tlacidla(); return; }
      const od = v.aktualny() >= v.trvanie - 0.05 ? 0 : v.aktualny() > 0.7 ? v.aktualny() : 0;
      const p = v.hraj(od); tlacidla(); await p; tlacidla();
    };
    tlHraj.addEventListener('click', hraj);
    velke.addEventListener('click', hraj);
    zvuk.addEventListener('click', () => {
      zapnuty = !zapnuty;
      if (zapnuty) v.odomkniZvuk();
      nastavZvuk();
      try { localStorage.setItem('video-zvuk', zapnuty ? 'ano' : 'nie'); } catch { /* nič */ }
      if (v.jeHra()) { const t = v.aktualny(); v.pauza(); v.hraj(t).then(tlacidla); tlacidla(); }
    });
    format.addEventListener('change', () => {
      v.pauza();
      const vysoke = format.value === '9x16';
      box.classList.toggle('pv-vysoke', vysoke);
      v.nastavRozmer(vysoke ? 1080 : 1280, vysoke ? 1920 : 720);
      tlacidla();
    });
    tlStiahni.addEventListener('click', async () => {
      v.odomkniZvuk();
      await priprav();
      tlStiahni.disabled = true; tlHraj.disabled = true; format.disabled = true; zvuk.disabled = true;
      const povodny = stav.textContent;
      try {
        const { blob, pripona } = await v.nahraj((p) => { stav.textContent = `Nahrávam video… ${Math.round(p * 100)} %`; });
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = `${d.slug}-v-cislach${format.value === '9x16' ? '-na-vysku' : ''}.${pripona}`;
        document.body.append(a); a.click();
        setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 2000);
        stav.textContent = `Hotovo – video sa stiahlo (${pripona.toUpperCase()}, ${(blob.size / 1e6).toLocaleString('sk-SK', { maximumFractionDigits: 1 })} MB).`;
      } catch (e) {
        stav.textContent = `Video sa nepodarilo nahrať: ${(e as Error).message} Skúste iný prehliadač (Chrome, Edge, Safari).`;
        setTimeout(() => { stav.textContent = povodny; }, 8000);
      } finally {
        tlStiahni.disabled = false; tlHraj.disabled = false; format.disabled = false; zvuk.disabled = false; tlacidla();
      }
    });
  });

  koren.querySelectorAll<HTMLElement>('.pr:not([data-ozivene])').forEach((el) => {
    el.dataset.ozivene = '1';
    el.querySelector('.pr-start')?.addEventListener('click', () => {
      // iPhone/Safari: reč sa musí „odomknúť“ priamo v kliknutí, inak neskôr nezaznie
      try { if ('speechSynthesis' in window) { const u = new SpeechSynthesisUtterance(' '); u.volume = 0; window.speechSynthesis.speak(u); } } catch { /* bez hlasu */ }
      import('./prelet').then(({ spustiPrelet }) => spustiPrelet(el)).catch(() => {
        const t = el.querySelector('.pr-titulok b');
        if (t) t.textContent = 'Mapu sa nepodarilo načítať.';
      });
    }, { once: true });
  });
}
