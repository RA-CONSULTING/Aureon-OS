// Minimal glue for activation orchestration
export type Signals = number[][];
export type Verdict = {
  coherence: number; purity_avg: number; purity_each: number[]; validated: boolean;
};

export type Config = {
  coherence_threshold: number;
  base_frequency_hz: number;
  love_frequency_hz: number;
  unity_frequency_hz: number;
  timeout_seconds: number;
  logging_enabled: boolean;
  log_file: string;
};

export function phaseCoherence(a: number[], b: number[]): number {
  // coarse coherence proxy (magnitude corr of spectra)
  const N = Math.min(a.length, b.length);
  if (N < 64) return 0;
  const am = mean(a), bm = mean(b);
  let num = 0, da = 0, db = 0;
  for (let i = 0; i < N; i++) {
    const x = a[i] - am, y = b[i] - bm;
    num += x * y; da += x * x; db += y * y;
  }
  const den = Math.sqrt(da * db) + 1e-12;
  const corr = Math.max(0, Math.min(1, num / den));
  return corr; // 0..1
}

export function normalizedEntropy(x: number[], bins = 64): number {
  if (x.length < 64) return 0;
  const min = Math.min(...x), max = Math.max(...x) + 1e-12;
  const hist = new Array(bins).fill(0);
  for (const v of x) {
    const idx = Math.max(0, Math.min(bins - 1, Math.floor((bins * (v - min)) / (max - min))));
    hist[idx] += 1;
  }
  const N = x.length;
  let H = 0;
  for (const h of hist) {
    if (h <= 0) continue;
    const p = h / N;
    H += -p * Math.log(p);
  }
  const Hmax = Math.log(bins);
  return 1 - H / Hmax; // 0..1 higher = more ordered (purity)
}

export function validateAura(signals: Signals, threshold = 0.945): Verdict {
  const heart = signals?.[0] ?? [];
  const gaze = signals?.[1] ?? [];
  const intent = signals?.[2] ?? [];
  const coh = (phaseCoherence(heart, gaze) + phaseCoherence(heart, intent) + phaseCoherence(gaze, intent)) / 3;
  const pur = [heart, gaze, intent].map(s => normalizedEntropy(s));
  const purity_avg = pur.reduce((a, b) => a + b, 0) / (pur.length || 1);
  const validated = coh >= threshold && purity_avg >= 0.70;
  return { coherence: coh, purity_avg, purity_each: pur, validated };
}

function mean(v: number[]) { return v.reduce((a,b)=>a+b,0)/(v.length||1); }

export type ActivationResult = {
  verdict: Verdict;
  proceeded: boolean;
  actions: string[];
};

export async function runActivation(signals: Signals, cfg: Config): Promise<ActivationResult> {
  // 1. Consent is assumed handled by caller/UI
  // 2. Sync base frequency (UI breathing / audio cue) – no-op here
  const verdict = validateAura(signals, cfg.coherence_threshold);
  const actions: string[] = ["CHECK_CONSENT","SYNC_BASE_FREQUENCY","MEASURE_COHERENCE"];
  if (!verdict.validated) {
    actions.push("SOFTEN_PROJECTION");
    return { verdict, proceeded: false, actions };
  }
  // 3. Render mirror (caller provides renderer)
  actions.push("MIRROR_RENDER","STABILIZE","LOG_AUDIT");
  return { verdict, proceeded: true, actions };
}
