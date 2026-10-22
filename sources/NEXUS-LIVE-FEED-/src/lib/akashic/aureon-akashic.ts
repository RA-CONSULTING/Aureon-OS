// Aureon Akashic Mapper — core utilities (no deps)
// Converts meditation + "mirror ping-pong" into a measurable frequency map.

export type Sample = { t: number; v: number };         // timestamped sample
export type Stream = Sample[];                          // e.g., breath, HRV (IBI -> resampled)
export type Weights = { breath?: number; hrv?: number; eeg?: number };

export const defaultW: Required<Weights> = { breath: 0.5, hrv: 0.5, eeg: 0.0 };

// ---------------- Phase-locking via lock-in (quadrature) ----------------
/** Lock-in PLV estimate between real signal s(t) and reference sin(2π f t). */
export function plvLockIn(stream: Stream, f: number, lpAlpha = 0.02): number {
  if (!stream.length) return 0;
  // Simple online quadrature: multiply by sin/cos, low-pass accumulate
  let x = 0, y = 0, ax = 0, ay = 0;
  for (const { t, v } of stream) {
    const w = 2 * Math.PI * f * t;
    const cs = Math.cos(w), sn = Math.sin(w);
    // demod
    const vx = v * cs, vy = v * sn;
    // 1-pole IIR low-pass
    ax = (1 - lpAlpha) * ax + lpAlpha * vx;
    ay = (1 - lpAlpha) * ay + lpAlpha * vy;
    x += ax; y += ay;
  }
  const r = Math.hypot(x, y);
  const n = Math.max(1, stream.length);
  // crude normalization → bound to [0,1] for ranking purposes
  return Math.min(1, Math.max(0, (r / n) * 2));
}

// ---------------- Akashic Alignment Index ----------------
export type AAIInput = {
  f: number;                   // test frequency (Hz)
  breath?: Stream;             // slow respiration waveform (0.05–0.5 Hz)
  hrv?: Stream;                // HRV (resampled LF/HF envelope 0.04–0.4 Hz)
  eegAlpha?: Stream;           // optional alpha-band envelope (8–13 Hz -> envelope ~0–2 Hz)
  weights?: Weights;
};

export function AAI({ f, breath, hrv, eegAlpha, weights }: AAIInput) {
  const w = { ...defaultW, ...(weights || {}) };
  const pb = breath?.length ? plvLockIn(breath!, f) : 0;
  const ph = hrv?.length ? plvLockIn(hrv!, f) : 0;
  const pe = eegAlpha?.length ? plvLockIn(eegAlpha!, f) : 0;
  const sumW = (breath ? w.breath : 0) + (hrv ? w.hrv : 0) + (eegAlpha ? w.eeg : 0) || 1;
  const score = ((breath ? w.breath * pb : 0) + (hrv ? w.hrv * ph : 0) + (eegAlpha ? w.eeg * pe : 0)) / sumW;
  return { score, components: { pb, ph, pe } };
}

// ---------------- Frequency scan ----------------
export type ScanResult = {
  bestF: number;
  bestAAI: number;
  table: Array<{ f: number; aai: number; pb: number; ph: number; pe: number }>;
};

export function scanAAI(
  streams: { breath?: Stream; hrv?: Stream; eegAlpha?: Stream },
  fMin = 0.05, fMax = 12, steps = 60, weights?: Weights
): ScanResult {
  const table: ScanResult["table"] = [];
  for (let i = 0; i < steps; i++) {
    const f = fMin + (i / (steps - 1)) * (fMax - fMin);
    const { score, components } = AAI({ f, ...streams, weights });
    table.push({ f, aai: score, pb: components.pb, ph: components.ph, pe: components.pe });
  }
  const best = table.reduce((a, b) => (b.aai > a.aai ? b : a), table[0] || { f: 0, aai: 0, pb: 0, ph: 0, pe: 0 });
  return { bestF: best.f, bestAAI: best.aai, table };
}

// ---------------- Minimal resampler (uniform dt) ----------------
export function resample(stream: Stream, dt = 0.1): Stream {
  if (!stream.length) return [];
  const t0 = stream[0].t;
  const t1 = stream[stream.length - 1].t;
  const N = Math.max(2, Math.floor((t1 - t0) / dt));
  const out: Stream = [];
  let j = 0;
  for (let k = 0; k <= N; k++) {
    const t = t0 + k * dt;
    while (j + 1 < stream.length && stream[j + 1].t < t) j++;
    const a = stream[j], b = stream[Math.min(j + 1, stream.length - 1)];
    const u = (t - a.t) / Math.max(1e-9, (b.t - a.t));
    const v = a.v + (b.v - a.v) * Math.min(1, Math.max(0, u));
    out.push({ t, v });
  }
  return out;
}

// ---------------- WebAudio ping-pong driver ----------------
export type PingPong = {
  ctx: AudioContext;
  gLeft: GainNode;
  gRight: GainNode;
  amGain: GainNode;
  carrier: OscillatorNode;
  modOsc: OscillatorNode;
  pannerL: StereoPannerNode;
  pannerR: StereoPannerNode;
};

export function startPingPong(carrierHz = 432, amHz = 0.1, gain = 0.12): PingPong {
  const ctx = new (window.AudioContext || (window as any).webkitAudioContext)();
  const carrier = ctx.createOscillator();
  const am = ctx.createOscillator();
  const amGain = ctx.createGain();

  // L/R paths
  const pannerL = ctx.createStereoPanner(); pannerL.pan.value = -1;
  const pannerR = ctx.createStereoPanner(); pannerR.pan.value = +1;
  const gLeft = ctx.createGain();  gLeft.gain.value = 0;
  const gRight = ctx.createGain(); gRight.gain.value = 0;

  // Amplitude modulation drives both channels with π phase offset → ping-pong
  am.type = "sine"; am.frequency.value = amHz;
  amGain.gain.value = 0.5; // 0..1 depth
  am.connect(amGain);

  // Modulation to L/R, offset phase by π via inversion
  const inv = ctx.createGain(); inv.gain.value = -1;
  amGain.connect(gLeft.gain);
  amGain.connect(inv); inv.connect(gRight.gain);

  carrier.type = "sine";
  carrier.frequency.value = carrierHz;
  carrier.connect(pannerL).connect(gLeft).connect(ctx.destination);
  carrier.connect(pannerR).connect(gRight).connect(ctx.destination);

  carrier.start(); am.start();
  // gentle base loudness
  const base = ctx.createGain(); base.gain.value = gain;
  gLeft.connect(base).connect(ctx.destination);
  gRight.connect(base).connect(ctx.destination);

  return { ctx, gLeft, gRight, amGain, carrier, modOsc: am, pannerL, pannerR };
}

export function setAM(pp: PingPong, amHz: number) {
  pp.modOsc.frequency.setTargetAtTime(amHz, pp.ctx.currentTime, 0.03);
}
export function setCarrier(pp: PingPong, hz: number) {
  pp.carrier.frequency.setTargetAtTime(hz, pp.ctx.currentTime, 0.03);
}
export function stopPingPong(pp: PingPong) {
  try { pp.carrier.stop(); pp.modOsc.stop(); } catch {}
  pp.ctx.close();
}