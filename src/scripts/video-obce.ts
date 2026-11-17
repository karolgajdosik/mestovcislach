// Krátke video „… v číslach“ vykreslené v prehliadači na <canvas> z údajov stránky (snímky po 4 s, ~30 s).
// Prehráva sa priamo na stránke; „Stiahnuť video“ ho nahrá cez MediaRecorder (MP4, kde to prehliadač vie, inak WebM).
// Žiadne súbory na serveri – funguje pre každú obec aj mestskú časť.

export type Snimka =
  | { typ: 'titul'; kicker: string; nadpis: string; pod: string }
  | { typ: 'cislo'; hodnota: number; desatiny?: number; predpona?: string; jednotka?: string; popis: string; pozn?: string; rad?: number[] }
  | { typ: 'dve'; a: [string, string]; b: [string, string]; nadpis?: string }
  | { typ: 'stlpce'; nadpis: string; polozky: [string, number, string][] }
  | { typ: 'outro'; nadpis: string; url: string };
export interface VideoData { nazov: string; slug: string; foto?: string | null; snimky: Snimka[] }

const DLZKA = 4; // s na snímku
const PRECHOD = 0.45;
const CERVENA = '#e0283f';
const PISMO = 'system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif';

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

  constructor(private canvas: HTMLCanvasElement, private d: VideoData) {
    this.ctx = canvas.getContext('2d')!;
    this.trvanie = d.snimky.length * DLZKA;
  }

  /** Načíta fotku (ak je) – s CORS, aby sa video dalo nahrať; pri chybe ostane farebné pozadie. */
  async priprav(): Promise<void> {
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

  hraj(od = 0): Promise<void> {
    cancelAnimationFrame(this.raf);
    this.start = performance.now() - od * 1000;
    this.hra = true;
    return new Promise((ok) => {
      this.koniec = ok;
      const krok = () => {
        const t = this.cas();
        if (t >= this.trvanie) { this.kresli(this.trvanie - 0.001); this.hra = false; this.zastavene = this.trvanie - 0.001; this.onCas?.(this.trvanie); this.koniec?.(); return; }
        this.kresli(t);
        this.onCas?.(t);
        this.raf = requestAnimationFrame(krok);
      };
      this.raf = requestAnimationFrame(krok);
    });
  }

  pauza() { if (!this.hra) return; this.zastavene = this.cas(); this.hra = false; cancelAnimationFrame(this.raf); }
  jeHra() { return this.hra; }
  aktualny() { return this.cas(); }

  /** Nahrá celé video v reálnom čase a vráti súbor (MP4 alebo WebM). */
  async nahraj(postup?: (p: number) => void): Promise<{ blob: Blob; pripona: string }> {
    const typy = ['video/mp4;codecs=avc1.42E01E', 'video/mp4', 'video/webm;codecs=vp9', 'video/webm;codecs=vp8', 'video/webm'];
    const mime = typy.find((m) => typeof MediaRecorder !== 'undefined' && MediaRecorder.isTypeSupported(m));
    if (!mime || !this.canvas.captureStream) throw new Error('Prehliadač nevie nahrávať video.');
    const fotoBolo = this.fotoOk;
    const stream = this.canvas.captureStream(30);
    const rec = new MediaRecorder(stream, { mimeType: mime, videoBitsPerSecond: 8_000_000 });
    const casti: Blob[] = [];
    rec.ondataavailable = (e) => { if (e.data.size) casti.push(e.data); };
    const hotovo = new Promise<void>((ok) => { rec.onstop = () => ok(); });
    const povodne = this.onCas;
    this.onCas = (t) => { povodne?.(t); postup?.(t / this.trvanie); };
    rec.start(250);
    await this.hraj(0);
    await new Promise((r) => setTimeout(r, 300));
    rec.stop();
    await hotovo;
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
    } else if (s.typ === 'outro') {
      this.text(s.nadpis, L, stred - 40 * S, 64 * S, 800, '#fff', sirka);
      this.text(s.url, L, stred + 30 * S, 32 * S, 600, 'rgba(255,255,255,0.88)', sirka);
      this.text('Otvorené dáta o každej obci Slovenska', L, stred + 80 * S, 26 * S, 500, 'rgba(255,255,255,0.7)', sirka);
    }
  }
}
