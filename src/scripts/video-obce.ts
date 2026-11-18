// Krátke video „… v číslach“ vykreslené v prehliadači na <canvas> z údajov stránky (snímky po 4 s, ~30 s).
// Prehráva sa priamo na stránke; „Stiahnuť video“ ho nahrá cez MediaRecorder (MP4, kde to prehliadač vie, inak WebM).
// Žiadne súbory na serveri – funguje pre každú obec aj mestskú časť.

export type Snimka =
  | { typ: 'titul'; kicker: string; nadpis: string; pod: string }
  | { typ: 'cislo'; hodnota: number; desatiny?: number; predpona?: string; jednotka?: string; popis: string; pozn?: string; rad?: number[] }
  | { typ: 'dve'; a: [string, string]; b: [string, string]; nadpis?: string }
  | { typ: 'stlpce'; nadpis: string; polozky: [string, number, string][] }
  | { typ: 'pamiatky'; nadpis: string; polozky: { n: string; u: string; a?: string }[] }
  | { typ: 'outro'; nadpis: string; url: string };
export interface VideoData { nazov: string; slug: string; foto?: string | null; snimky: Snimka[] }

const DLZKA = 4; // s na snímku
const PRECHOD = 0.45;
const CERVENA = '#e0283f';
const PISMO = 'system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif';

export type Zvuk = 'hlas' | 'hudba' | 'nie';

/** Krátky text, ktorý k snímke prečíta slovenský hlas (snímka trvá 4 s, preto stručne). */
function naCitanie(s: Snimka): string {
  const vyslov = (x: string) => x.replace(/(\d) r\./g, '$1 rokov').replace(/ ?%/g, ' percent').replace(/ ?°C/g, ' stupňa').replace(/(\d) mm/g, '$1 milimetrov').replace(/−/g, 'mínus ').replace(/·/g, ',');
  if (s.typ === 'titul') return vyslov(`${s.nadpis}. ${s.pod}`);
  if (s.typ === 'cislo') return vyslov(`${s.popis}: ${s.predpona ?? ''}${fmt(s.hodnota, s.desatiny ?? 0)}${s.jednotka ? ` ${s.jednotka}` : ''}`);
  if (s.typ === 'stlpce') return vyslov(`${s.nadpis.replace(/\s*\(.*\)/, '')}. ${s.polozky[2]?.[0] ?? ''} ${s.polozky[2]?.[2] ?? ''}`);
  if (s.typ === 'dve') return vyslov(`${s.a[1]} ${s.a[0]}${s.b[1] ? `, ${s.b[1]} ${s.b[0]}` : ''}`);
  if (s.typ === 'pamiatky') return `${s.nadpis}: ${s.polozky.map((x) => x.n).join(', ')}`;
  return 'Všetky čísla nájdete na mesto v číslach bodka es ká.';
}

let _hlas: Promise<SpeechSynthesisVoice | null> | null = null;
/** Slovenský hlas prehliadača / systému (ak nie je, hlasový komentár sa neponúkne). */
export function slovenskyHlas(): Promise<SpeechSynthesisVoice | null> {
  if (typeof speechSynthesis === 'undefined') return Promise.resolve(null);
  return (_hlas ??= new Promise((ok) => {
    const vyber = () => { const v = speechSynthesis.getVoices(); return v.find((x) => /^sk([-_]|$)/i.test(x.lang) && /enhanced|premium|natural|neural/i.test(x.name)) ?? v.find((x) => /^sk([-_]|$)/i.test(x.lang)) ?? null; };
    if (speechSynthesis.getVoices().length) { ok(vyber()); return; }
    const t = setTimeout(() => ok(vyber()), 1500);
    speechSynthesis.addEventListener('voiceschanged', () => { clearTimeout(t); ok(vyber()); }, { once: true });
  }));
}

const ease = (x: number) => 1 - Math.pow(1 - Math.min(1, Math.max(0, x)), 3);
const fmt = (x: number, d = 0) => x.toLocaleString('sk-SK', { minimumFractionDigits: d, maximumFractionDigits: d });

export class VideoObce {
  private ctx: CanvasRenderingContext2D;
  private foto: HTMLImageElement | null = null;
  private fotoOk = false;
  private start = 0;
  private raf = 0;
  private hra = false;
  private koniec: (() => void) | null = null;
  readonly trvanie: number;
  onCas: ((t: number) => void) | null = null;
  /** Zvuk pri prehrávaní: hudba + hlasový komentár, len hudba, alebo ticho. */
  zvuk: Zvuk = 'hudba';
  private ac: AudioContext | null = null;
  private hudba: import('./hudba').Hudba | null = null;
  private hlas: SpeechSynthesisVoice | null = null;
  private poslednaSnimka = -1;
  private nahrava = false;
  private fotky: (HTMLImageElement | null)[] = [];

  constructor(private canvas: HTMLCanvasElement, private d: VideoData) {
    this.ctx = canvas.getContext('2d')!;
    this.trvanie = d.snimky.length * DLZKA;
  }

  /** Načíta fotku (ak je) – s CORS, aby sa video dalo nahrať; pri chybe ostane farebné pozadie. */
  async priprav(): Promise<void> {
    this.hlas = await slovenskyHlas();
    const pam = this.d.snimky.find((s) => s.typ === 'pamiatky') as Extract<Snimka, { typ: 'pamiatky' }> | undefined;
    if (pam) this.fotky = await Promise.all(pam.polozky.map((x) => new Promise<HTMLImageElement | null>((ok) => {
      const i = new Image(); i.crossOrigin = 'anonymous'; i.decoding = 'async';
      i.onload = () => { try { const c = document.createElement('canvas').getContext('2d')!; c.drawImage(i, 0, 0, 1, 1); c.getImageData(0, 0, 1, 1); ok(i); } catch { ok(null); } };
      i.onerror = () => ok(null); i.src = x.u;
    })));
    if (!this.d.foto) return;
    const nacitaj = (src: string) => new Promise<HTMLImageElement>((ok, chyba) => {
      const i = new Image();
      i.crossOrigin = 'anonymous';
      i.decoding = 'async';
      i.onload = () => ok(i);
      i.onerror = chyba;
      i.src = src;
    });
    const velka = this.d.foto.replace(/\/(\d+)px-/, '/1280px-');
    try { this.foto = await nacitaj(velka); } catch { try { this.foto = await nacitaj(this.d.foto); } catch { this.foto = null; } }
    if (this.foto) {
      // overenie, že plátno ostane „čisté“ (inak by nahrávanie nefungovalo)
      try { this.ctx.drawImage(this.foto, 0, 0, 2, 2); this.ctx.getImageData(0, 0, 1, 1); this.fotoOk = true; } catch { this.fotoOk = false; }
    }
  }

  nastavRozmer(w: number, h: number) { this.canvas.width = w; this.canvas.height = h; this.kresli(Math.min(this.cas(), this.trvanie)); }

  private cas() { return this.hra ? (performance.now() - this.start) / 1000 : this.zastavene; }
  private zastavene = 0.6;

  /** Je k dispozícii slovenský hlas na komentár? (po priprav) */
  maHlas() { return !!this.hlas; }

  /** Volať priamo v kliknutí (pred akýmkoľvek await) – iPhone/Safari inak zvuk nepustí. */
  odomkniZvuk() {
    try {
      if (!this.ac) { const AC = window.AudioContext ?? (window as any).webkitAudioContext; if (AC) this.ac = new AC(); }
      if (this.ac?.state === 'suspended') this.ac.resume();
      if (typeof speechSynthesis !== 'undefined' && !this.hlasOdomknuty) { const u = new SpeechSynthesisUtterance(' '); u.volume = 0; speechSynthesis.speak(u); this.hlasOdomknuty = true; }
    } catch { /* bez zvuku */ }
  }
  private hlasOdomknuty = false;

  /** Hudba cez Web Audio – AudioContext sa vytvorí až pri prvom prehraní (v kliknutí, kvôli pravidlám prehliadačov). */
  private async spustiZvuk(od: number) {
    if (this.zvuk === 'nie') return;
    try {
      this.odomkniZvuk();
      if (!this.ac) return;
      if (!this.hudba) {
        const { Hudba } = await import('./hudba');
        this.hudba = new Hudba(this.ac);
        this.hudba.vystup.connect(this.ac.destination);
      }
      if (this.ac.state === 'suspended') await this.ac.resume();
      if (!this.hra && !this.nahrava) return; // medzitým pauza
      // čas videa v tejto chvíli (prvé spustenie čaká na načítanie modulu hudby)
      this.hudba!.hraj(this.hra ? Math.min(this.cas(), this.trvanie) : od, this.trvanie, this.d.snimky.length, DLZKA);
    } catch { /* bez zvuku */ }
  }
  private zastavZvuk() { this.hudba?.zastav(); if (typeof speechSynthesis !== 'undefined') speechSynthesis.cancel(); }
  private povedz(i: number) {
    if (this.zvuk !== 'hlas' || !this.hlas || this.nahrava) return;
    speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(naCitanie(this.d.snimky[i]));
    u.voice = this.hlas; u.lang = this.hlas.lang; u.rate = 1.12;
    speechSynthesis.speak(u);
  }

  hraj(od = 0): Promise<void> {
    cancelAnimationFrame(this.raf);
    this.spustiZvuk(od);
    // komentár: snímka, do ktorej sa vstupuje od začiatku, sa prečíta; pri pokračovaní uprostred snímky až nasledujúca
    this.poslednaSnimka = od % DLZKA < 0.4 ? Math.floor(od / DLZKA) - 1 : Math.floor(od / DLZKA);
    this.start = performance.now() - od * 1000;
    this.hra = true;
    return new Promise((ok) => {
      this.koniec = ok;
      const krok = () => {
        const t = this.cas();
        if (t >= this.trvanie) { this.kresli(this.trvanie - 0.001); this.hra = false; this.zastavene = this.trvanie - 0.001; this.onCas?.(this.trvanie); this.koniec?.(); return; }
        this.kresli(t);
        const i = Math.floor(t / DLZKA);
        if (i !== this.poslednaSnimka) { this.poslednaSnimka = i; this.povedz(i); }
        this.onCas?.(t);
        this.raf = requestAnimationFrame(krok);
      };
      this.raf = requestAnimationFrame(krok);
    });
  }

  pauza() { if (!this.hra) return; this.zastavene = this.cas(); this.hra = false; cancelAnimationFrame(this.raf); this.zastavZvuk(); }
  jeHra() { return this.hra; }
  aktualny() { return this.cas(); }

  /** Nahrá celé video v reálnom čase a vráti súbor (MP4 alebo WebM). */
  async nahraj(postup?: (p: number) => void): Promise<{ blob: Blob; pripona: string }> {
    const sHudbou = this.zvuk !== 'nie';
    const typy = [...(sHudbou ? ['video/mp4;codecs=avc1.42E01E,mp4a.40.2', 'video/webm;codecs=vp9,opus', 'video/webm;codecs=vp8,opus'] : []), 'video/mp4;codecs=avc1.42E01E', 'video/mp4', 'video/webm;codecs=vp9', 'video/webm;codecs=vp8', 'video/webm'];
    const mime = typy.find((m) => typeof MediaRecorder !== 'undefined' && MediaRecorder.isTypeSupported(m));
    if (!mime || !this.canvas.captureStream) throw new Error('Prehliadač nevie nahrávať video.');
    const fotoBolo = this.fotoOk;
    this.nahrava = true;
    const stream = this.canvas.captureStream(30);
    // hudba do súboru: výstup Web Audio → stopa MediaStream (hlasový komentár prehliadača sa nahrať nedá)
    let audio: MediaStreamAudioDestinationNode | null = null;
    if (sHudbou) {
      await this.spustiZvuk(0); this.hudba?.zastav();
      if (this.ac && this.hudba) { audio = this.ac.createMediaStreamDestination(); this.hudba.vystup.connect(audio); audio.stream.getAudioTracks().forEach((tr) => stream.addTrack(tr)); }
    }
    const rec = new MediaRecorder(stream, { mimeType: mime, videoBitsPerSecond: 8_000_000 });
    const casti: Blob[] = [];
    rec.ondataavailable = (e) => { if (e.data.size) casti.push(e.data); };
    const hotovo = new Promise<void>((ok) => { rec.onstop = () => ok(); });
    const povodne = this.onCas;
    this.onCas = (t) => { povodne?.(t); postup?.(t / this.trvanie); };
    rec.start(250);
    try {
      await this.hraj(0);
      await new Promise((r) => setTimeout(r, 300));
    } finally {
      rec.stop();
      this.nahrava = false;
    }
    await hotovo;
    if (audio && this.hudba) { try { this.hudba.vystup.disconnect(audio); } catch { /* nič */ } }
    this.onCas = povodne;
    this.fotoOk = fotoBolo;
    stream.getTracks().forEach((x) => x.stop());
    return { blob: new Blob(casti, { type: mime.split(';')[0] }), pripona: mime.startsWith('video/mp4') ? 'mp4' : 'webm' };
  }

  // ---------- kreslenie ----------
  kresli(t: number) {
    const { ctx } = this;
    const W = this.canvas.width, H = this.canvas.height;
    const S = Math.min(W, H) / 720; // mierka písma a okrajov
    const vysoke = H > W;
    // pozadie: fotka s pomalým priblížením (Ken Burns) a stmavením, inak farebný prechod
    ctx.save();
    if (this.foto && this.fotoOk) {
      const z = 1.06 + 0.12 * (t / this.trvanie);
      const r = Math.max(W / this.foto.width, H / this.foto.height) * z;
      const fw = this.foto.width * r, fh = this.foto.height * r;
      const dx = (W - fw) / 2 - (t / this.trvanie) * W * 0.03, dy = (H - fh) / 2;
      ctx.drawImage(this.foto, dx, dy, fw, fh);
      const g = ctx.createLinearGradient(0, 0, 0, H);
      g.addColorStop(0, 'rgba(10,12,18,0.55)'); g.addColorStop(0.55, 'rgba(10,12,18,0.72)'); g.addColorStop(1, 'rgba(10,12,18,0.9)');
      ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
    } else {
      const g = ctx.createLinearGradient(0, 0, W, H);
      g.addColorStop(0, '#1d2433'); g.addColorStop(1, '#3a1c24');
      ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
    }
    ctx.restore();
    // aktuálna snímka + prelínanie
    const i = Math.min(this.d.snimky.length - 1, Math.floor(t / DLZKA));
    const u = t - i * DLZKA;
    const alfa = Math.min(ease(u / PRECHOD), i === this.d.snimky.length - 1 ? 1 : ease((DLZKA - u) / PRECHOD));
    ctx.save();
    ctx.globalAlpha = alfa;
    ctx.translate(0, (1 - alfa) * 18 * S);
    this.snimka(this.d.snimky[i], u, W, H, S, vysoke);
    ctx.restore();
    // pätička: značka a priebeh
    ctx.fillStyle = 'rgba(255,255,255,0.18)';
    ctx.fillRect(0, H - 6 * S, W, 6 * S);
    ctx.fillStyle = CERVENA;
    ctx.fillRect(0, H - 6 * S, W * Math.min(1, t / this.trvanie), 6 * S);
    this.znacka(W, H, S);
  }

  private znacka(W: number, H: number, S: number) {
    const { ctx } = this;
    ctx.font = `800 ${26 * S}px ${PISMO}`;
    ctx.textBaseline = 'alphabetic';
    const x = 44 * S, y = H - 36 * S;
    const a = 'mesto', b = 'v', c = 'číslach.sk';
    ctx.fillStyle = '#fff'; ctx.fillText(a, x, y);
    const wa = ctx.measureText(a).width;
    ctx.fillStyle = CERVENA; ctx.fillText(b, x + wa, y);
    ctx.fillStyle = '#fff'; ctx.fillText(c, x + wa + ctx.measureText(b).width, y);
  }

  private text(t: string, x: number, y: number, px: number, vaha = 800, farba = '#fff', maxW?: number) {
    const { ctx } = this;
    let size = px;
    ctx.font = `${vaha} ${size}px ${PISMO}`;
    if (maxW) while (ctx.measureText(t).width > maxW && size > 12) { size -= 2; ctx.font = `${vaha} ${size}px ${PISMO}`; }
    ctx.fillStyle = farba;
    ctx.fillText(t, x, y);
    return size;
  }

  private snimka(s: Snimka, u: number, W: number, H: number, S: number, vysoke: boolean) {
    const { ctx } = this;
    const L = 64 * S, sirka = W - 2 * L;
    const stred = vysoke ? H * 0.42 : H * 0.5;
    ctx.textBaseline = 'alphabetic';
    if (s.typ === 'titul') {
      ctx.fillStyle = CERVENA; ctx.fillRect(L, stred - 150 * S, 70 * S, 8 * S);
      this.text(s.kicker.toUpperCase(), L, stred - 100 * S, 26 * S, 700, 'rgba(255,255,255,0.85)');
      this.text(s.nadpis, L, stred + 10 * S, (vysoke ? 104 : 96) * S, 800, '#fff', sirka);
      this.text(s.pod, L, stred + 70 * S, 32 * S, 500, 'rgba(255,255,255,0.85)', sirka);
    } else if (s.typ === 'cislo') {
      const v = s.hodnota * ease(u / 1.3);
      const h = `${s.predpona ?? ''}${fmt(v, s.desatiny ?? 0)}${s.jednotka ? ` ${s.jednotka}` : ''}`;
      this.text(s.popis, L, stred - 110 * S, 34 * S, 700, 'rgba(255,255,255,0.88)', sirka);
      this.text(h, L, stred + 20 * S, (vysoke ? 150 : 140) * S, 800, '#fff', sirka);
      if (s.pozn) this.text(s.pozn, L, stred + 80 * S, 28 * S, 500, 'rgba(255,255,255,0.8)', sirka);
      if (s.rad && s.rad.length > 2) {
        // malý graf vývoja, kreslí sa postupne
        const gx = L, gy = stred + 120 * S, gw = Math.min(sirka, 560 * S), gh = 110 * S;
        const mn = Math.min(...s.rad), mx = Math.max(...s.rad), roz = mx - mn || 1;
        const n = s.rad.length, kolko = Math.max(2, Math.ceil(n * ease((u - 0.3) / 2)));
        ctx.strokeStyle = 'rgba(255,255,255,0.25)'; ctx.lineWidth = 2 * S;
        ctx.beginPath(); ctx.moveTo(gx, gy + gh); ctx.lineTo(gx + gw, gy + gh); ctx.stroke();
        ctx.strokeStyle = CERVENA; ctx.lineWidth = 5 * S; ctx.lineJoin = 'round'; ctx.beginPath();
        for (let k = 0; k < kolko; k++) { const x = gx + (gw * k) / (n - 1), y = gy + gh - (gh * (s.rad[k] - mn)) / roz; k ? ctx.lineTo(x, y) : ctx.moveTo(x, y); }
        ctx.stroke();
      }
    } else if (s.typ === 'dve') {
      if (s.nadpis) this.text(s.nadpis, L, stred - 150 * S, 34 * S, 700, 'rgba(255,255,255,0.88)', sirka);
      const dvaStlpce = !vysoke;
      const polozky = [s.a, s.b];
      polozky.forEach(([h, popis], k) => {
        const p = ease((u - 0.25 - k * 0.35) / 0.6);
        ctx.save(); ctx.globalAlpha *= p;
        const x = dvaStlpce ? L + k * (sirka / 2) : L;
        const y = dvaStlpce ? stred + 10 * S : stred - 40 * S + k * 220 * S;
        this.text(h, x, y, 104 * S, 800, '#fff', dvaStlpce ? sirka / 2 - 30 * S : sirka);
        this.text(popis, x, y + 52 * S, 28 * S, 500, 'rgba(255,255,255,0.85)', dvaStlpce ? sirka / 2 - 30 * S : sirka);
        ctx.restore();
      });
    } else if (s.typ === 'stlpce') {
      this.text(s.nadpis, L, stred - 170 * S, 36 * S, 700, '#fff', sirka);
      const riadok = 92 * S;
      s.polozky.forEach(([t, v, h], k) => {
        const y = stred - 90 * S + k * riadok;
        const p = ease((u - 0.3 - k * 0.25) / 1.1);
        this.text(t, L, y, 28 * S, 600, 'rgba(255,255,255,0.88)', sirka * 0.6);
        ctx.fillStyle = 'rgba(255,255,255,0.16)'; ctx.fillRect(L, y + 14 * S, sirka, 26 * S);
        ctx.fillStyle = k === 0 ? CERVENA : '#ffffff';
        ctx.globalAlpha *= k === 0 ? 1 : 0.85;
        ctx.fillRect(L, y + 14 * S, sirka * Math.min(1, v / 100) * p, 26 * S);
        ctx.globalAlpha /= k === 0 ? 1 : 0.85;
        ctx.textAlign = 'right';
        this.text(h, L + sirka, y, 30 * S, 800, '#fff');
        ctx.textAlign = 'left';
      });
    } else if (s.typ === 'pamiatky') {
      this.text(s.nadpis, L, (vysoke ? stred - 330 * S : stred - 190 * S), 36 * S, 700, '#fff', sirka);
      const n = s.polozky.length, medzera = 24 * S;
      const kw = vysoke ? sirka : (sirka - medzera * (n - 1)) / n;
      const kh = vysoke ? Math.min(250 * S, (H * 0.62 - medzera * (n - 1)) / n) : kw * 0.68;
      s.polozky.forEach((x, k) => {
        const p = ease((u - 0.2 - k * 0.3) / 0.7);
        const kx = vysoke ? L : L + k * (kw + medzera), ky = (vysoke ? stred - 300 * S + k * (kh + medzera) : stred - 150 * S) + (1 - p) * 40 * S;
        ctx.save(); ctx.globalAlpha *= p;
        const f = this.fotky[k];
        ctx.beginPath(); (ctx as any).roundRect ? (ctx as any).roundRect(kx, ky, kw, kh, 14 * S) : ctx.rect(kx, ky, kw, kh); ctx.save(); ctx.clip();
        ctx.fillStyle = '#2a3142'; ctx.fillRect(kx, ky, kw, kh);
        if (f) { const z = 1.04 + 0.06 * (u / DLZKA), r = Math.max(kw / f.width, kh / f.height) * z, fw = f.width * r, fh = f.height * r; ctx.drawImage(f, kx + (kw - fw) / 2, ky + (kh - fh) / 2, fw, fh); }
        const g = ctx.createLinearGradient(0, ky + kh * 0.45, 0, ky + kh); g.addColorStop(0, 'rgba(0,0,0,0)'); g.addColorStop(1, 'rgba(0,0,0,0.8)');
        ctx.fillStyle = g; ctx.fillRect(kx, ky, kw, kh);
        ctx.restore();
        this.text(x.n, kx + 16 * S, ky + kh - 18 * S, 26 * S, 700, '#fff', kw - 32 * S);
        ctx.restore();
      });
      const autori = [...new Set(s.polozky.map((x) => x.a).filter(Boolean))].join(', ');
      if (autori) this.text(`Foto: ${autori} (Wikimedia Commons)`, L, H - 80 * S, 18 * S, 500, 'rgba(255,255,255,0.7)', sirka);
    } else if (s.typ === 'outro') {
      this.text(s.nadpis, L, stred - 40 * S, 64 * S, 800, '#fff', sirka);
      this.text(s.url, L, stred + 30 * S, 32 * S, 600, 'rgba(255,255,255,0.88)', sirka);
      this.text('Otvorené dáta o každej obci Slovenska', L, stred + 80 * S, 26 * S, 500, 'rgba(255,255,255,0.7)', sirka);
    }
  }
}
