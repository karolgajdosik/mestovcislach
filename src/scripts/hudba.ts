// Podkladová hudba k videu „… v číslach“ – syntetizovaná priamo v prehliadači (Web Audio API).
// Žiadne nahrávky ani licencie: akordy, basa, arpeggio a jemný rytmus sa vytvoria z oscilátorov.
// Tempo 120 BPM → jedna snímka (4 s) = 2 takty; akord sa mení s každou snímkou, pred prechodom zaznie jemný „šum“.

const BPM = 120;
const DOBA = 60 / BPM; // 0,5 s
// D dur: D – A – Hm – G (I – V – vi – IV), tóny v Hz pre akord (v strednej polohe) a basu
const AKORDY: { tony: number[]; basa: number }[] = [
  { tony: [293.66, 369.99, 440.0], basa: 73.42 }, // D
  { tony: [277.18, 329.63, 440.0], basa: 110.0 }, // A
  { tony: [293.66, 369.99, 493.88], basa: 61.74 }, // Hm
  { tony: [293.66, 392.0, 493.88], basa: 98.0 }, // G
];

export class Hudba {
  private ac: AudioContext;
  private master: GainNode;
  private uzly: AudioScheduledSourceNode[] = [];
  private sum: AudioBuffer;
  /** Kam ide zvuk – reproduktory a pri nahrávaní aj stopa pre MediaRecorder. */
  readonly vystup: GainNode;

  constructor(ac: AudioContext) {
    this.ac = ac;
    this.vystup = ac.createGain();
    const komp = ac.createDynamicsCompressor();
    komp.threshold.value = -18; komp.ratio.value = 3;
    this.master = ac.createGain();
    this.master.connect(komp); komp.connect(this.vystup);
    // biely šum na hi-hat a prechody
    this.sum = ac.createBuffer(1, ac.sampleRate, ac.sampleRate);
    const d = this.sum.getChannelData(0);
    for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
  }

  /** Naplánuje hudbu od času `od` (s) videa po `trvanie`; `snimok` = počet snímok po `dlzka` s. */
  hraj(od: number, trvanie: number, snimok: number, dlzka: number) {
    this.zastav();
    const ac = this.ac, t0 = ac.currentTime + 0.05 - od; // čas videa 0 = t0 v AudioContext
    const m = this.master.gain;
    m.cancelScheduledValues(ac.currentTime);
    m.setValueAtTime(0, ac.currentTime);
    m.linearRampToValueAtTime(0.55, ac.currentTime + (od > 0.1 ? 0.25 : 0.8));
    m.setValueAtTime(0.55, t0 + trvanie - 1.6);
    m.linearRampToValueAtTime(0, t0 + trvanie);
    const pred = (t: number) => t >= od - 0.01; // plánuje sa len to, čo ešte nezaznelo
    for (let s = 0; s < snimok; s++) {
      const zac = s * dlzka, ak = AKORDY[s % AKORDY.length], posledna = s === snimok - 1;
      // pad – celý akord cez snímku (pri poslednej doznie)
      if (zac + dlzka > od) for (const f of ak.tony) this.pad(f, t0 + Math.max(zac, od), t0 + zac + (posledna ? dlzka + 0.5 : dlzka + 0.15));
      for (let b = 0; b < dlzka / DOBA; b++) {
        const t = zac + b * DOBA;
        if (!pred(t) || t >= trvanie - 0.3) continue;
        if (b % 2 === 0) this.basa(ak.basa, t0 + t);
        if (s > 0 && !posledna) { this.kick(t0 + t, b % 4 === 0 ? 0.32 : 0.2); this.hihat(t0 + t + DOBA / 2); }
        if (s > 0 || b >= 4) {
          // arpeggio v osminách o oktávu vyššie
          const arp = [...ak.tony, ak.tony[1] * 2];
          this.pluk(arp[(b * 2) % arp.length] * 2, t0 + t, 0.035);
          if (!posledna) this.pluk(arp[(b * 2 + 1) % arp.length] * 2, t0 + t + DOBA / 2, 0.025);
        }
      }
      // prechod do ďalšej snímky
      if (!posledna && pred(zac + dlzka - 0.6)) this.prechod(t0 + zac + dlzka - 0.6);
    }
  }

  zastav() {
    const t = this.ac.currentTime;
    this.master.gain.cancelScheduledValues(t);
    this.master.gain.setTargetAtTime(0, t, 0.05);
    for (const u of this.uzly) { try { u.stop(t + 0.2); } catch { /* už skončil */ } }
    this.uzly = [];
  }

  private obalka(g: GainNode, start: number, koniec: number, max: number, nabeh: number, dobeh: number) {
    g.gain.setValueAtTime(0, start);
    g.gain.linearRampToValueAtTime(max, start + nabeh);
    g.gain.setValueAtTime(max, Math.max(start + nabeh, koniec - dobeh));
    g.gain.linearRampToValueAtTime(0, koniec);
  }

  private osc(typ: OscillatorType, f: number, start: number, koniec: number, ciel: AudioNode, detune = 0) {
    const o = this.ac.createOscillator();
    o.type = typ; o.frequency.value = f; o.detune.value = detune;
    o.connect(ciel); o.start(start); o.stop(koniec + 0.05);
    this.uzly.push(o);
    return o;
  }

  private pad(f: number, start: number, koniec: number) {
    const ac = this.ac, g = ac.createGain(), lp = ac.createBiquadFilter();
    lp.type = 'lowpass'; lp.frequency.value = 1100; lp.Q.value = 0.4;
    g.connect(lp); lp.connect(this.master);
    this.obalka(g, start, koniec, 0.045, 0.5, 0.6);
    this.osc('sawtooth', f, start, koniec, g, -6);
    this.osc('triangle', f, start, koniec, g, 5);
  }

  private basa(f: number, t: number) {
    const g = this.ac.createGain();
    g.connect(this.master);
    g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(0.22, t + 0.02); g.gain.exponentialRampToValueAtTime(0.001, t + 0.9);
    this.osc('triangle', f, t, t + 0.95, g);
  }

  private pluk(f: number, t: number, hlasitost: number) {
    const g = this.ac.createGain();
    g.connect(this.master);
    g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(hlasitost, t + 0.01); g.gain.exponentialRampToValueAtTime(0.0005, t + 0.4);
    this.osc('triangle', f, t, t + 0.42, g);
  }

  private kick(t: number, hlasitost: number) {
    const ac = this.ac, g = ac.createGain();
    g.connect(this.master);
    g.gain.setValueAtTime(hlasitost, t); g.gain.exponentialRampToValueAtTime(0.001, t + 0.28);
    const o = this.osc('sine', 120, t, t + 0.3, g);
    o.frequency.setValueAtTime(120, t); o.frequency.exponentialRampToValueAtTime(42, t + 0.22);
  }

  private hihat(t: number) {
    const ac = this.ac, src = ac.createBufferSource(), hp = ac.createBiquadFilter(), g = ac.createGain();
    src.buffer = this.sum; hp.type = 'highpass'; hp.frequency.value = 7000;
    src.connect(hp); hp.connect(g); g.connect(this.master);
    g.gain.setValueAtTime(0.035, t); g.gain.exponentialRampToValueAtTime(0.0005, t + 0.06);
    src.start(t, Math.random() * 0.5, 0.08);
    this.uzly.push(src);
  }

  private prechod(t: number) {
    const ac = this.ac, src = ac.createBufferSource(), bp = ac.createBiquadFilter(), g = ac.createGain();
    src.buffer = this.sum; bp.type = 'bandpass'; bp.Q.value = 1.2;
    bp.frequency.setValueAtTime(400, t); bp.frequency.exponentialRampToValueAtTime(5000, t + 0.6);
    src.connect(bp); bp.connect(g); g.connect(this.master);
    g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(0.05, t + 0.5); g.gain.linearRampToValueAtTime(0, t + 0.75);
    src.start(t, 0, 0.8);
    this.uzly.push(src);
  }
}
