// Aureon — Math & Meaning Core
// Minimal dependencies, safe for Vite/React.
// Provides: units, equation templates (QSSR, Kuramoto, Spiral, Echo), TeX, meaning strings.

export type Num = number;

// ---------- Units (dimensional analysis) ----------
/** Base dimensions exponents: [L, M, T, I, Θ, N, J] */
export type Dim = [number, number, number, number, number, number, number];

export const DIM: Record<string, Dim> = {
  // base
  "":   [0,0,0,0,0,0,0],
  L:    [1,0,0,0,0,0,0],     // length
  M:    [0,1,0,0,0,0,0],     // mass
  T:    [0,0,1,0,0,0,0],     // time
  I:    [0,0,0,1,0,0,0],     // electric current
  TH:   [0,0,0,0,1,0,0],     // temperature
  N:    [0,0,0,0,0,1,0],     // amount of substance
  J:    [0,0,0,0,0,0,1],     // luminous intensity
};

export interface Qty { v: Num; d: Dim; }
export const qty = (v: Num, d: Dim = DIM[""]) : Qty => ({ v, d });

export const add = (a: Qty, b: Qty): Qty => {
  if (!sameDim(a.d, b.d)) throw new Error("Unit mismatch in add");
  return qty(a.v + b.v, a.d);
};
export const sub = (a: Qty, b: Qty): Qty => add(a, qty(-b.v, b.d));

export const mul = (a: Qty, b: Qty): Qty => qty(a.v * b.v, addDim(a.d, b.d));
export const div = (a: Qty, b: Qty): Qty => qty(a.v / b.v, subDim(a.d, b.d));
export const pow = (a: Qty, p: number): Qty => qty(a.v ** p, scaleDim(a.d, p));

export function sameDim(a: Dim, b: Dim) { return a.every((x, i) => x === b[i]); }
export function addDim(a: Dim, b: Dim): Dim { return a.map((x, i) => x + b[i]) as Dim; }
export function subDim(a: Dim, b: Dim): Dim { return a.map((x, i) => x - b[i]) as Dim; }
export function scaleDim(a: Dim, k: number): Dim { return a.map(x => x * k) as Dim; }
export function isDimensionless(a: Qty) { return sameDim(a.d, DIM[""]); }

// Shorthands
export const UNIT = {
  // time s
  s: DIM.T,
  // frequency 1/s
  Hz: subDim(DIM[""], DIM.T),
  // angle is dimensionless, treat as ""
  rad: DIM[""],
};

// ---------- Helpers ----------
export const clamp = (x: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, x));
export const TAU = Math.PI * 2;

// ---------- Equation Templates (math + TeX + meaning) ----------
export type EquationId = "QSSR" | "KURAMOTO" | "SPIRAL" | "ECHO";

export interface EquationResult {
  id: EquationId;
  values: Record<string, number>;
  units: Record<string, string>;
  meaning: string[];
  tex: string[];
}

export interface CompileIntent {
  equations: EquationId[]; // which templates were selected
  notes?: string;
}

// 1) QSSR Coherence:  C(t) = | sum A_i exp(j(ω_i t + φ_i)) | / sum A_i
export function qssrCoherence(
  amps: number[], omegas: number[], phases: number[], t: number
): EquationResult {
  const A = amps.reduce((a,b)=>a+b,0) || 1;
  let re = 0, im = 0;
  for (let i=0;i<amps.length;i++){
    const phi = omegas[i]*t + phases[i];
    re += amps[i]*Math.cos(phi);
    im += amps[i]*Math.sin(phi);
  }
  const C = Math.hypot(re, im)/A;
  const tex = [
    String.raw`\mathcal{C}(t)=\frac{\left|\sum_i A_i e^{j(\omega_i t + \phi_i)}\right|}{\sum_i A_i}`,
    String.raw`\text{with }A_i>0,\ \omega_i \in \mathbb{R},\ \phi_i \in \mathbb{R}.`
  ];
  const meaning = [
    "C(t)∈[0,1] measures phase-alignment across sources.",
    "High C ⇒ constructive interference; low C ⇒ dissonance.",
  ];
  return { id: "QSSR", values: { C, re, im }, units: { C: "1" }, meaning, tex };
}

// 2) Kuramoto order parameter: R e^{iψ} = (1/N) Σ e^{iθ_k}
export function kuramotoOrder(phases: number[]): EquationResult {
  const N = phases.length || 1;
  let xr=0, xi=0;
  for (const th of phases){ xr += Math.cos(th); xi += Math.sin(th); }
  const R = Math.hypot(xr, xi)/N;
  const psi = Math.atan2(xi, xr);
  const tex = [
    String.raw`R(t)e^{i\psi(t)}=\frac{1}{N}\sum_{k=1}^N e^{i\theta_k(t)}`,
    String.raw`R\in[0,1]\text{ quantifies synchronization (unison).}`,
  ];
  const meaning = [
    "R close to 1 ⇒ strong unison thread.",
    "ψ is the collective phase (where the group points).",
  ];
  return { id: "KURAMOTO", values: { R, psi }, units: { R: "1", psi: "rad" }, meaning, tex };
}

// 3) Log-spiral fit: r = a e^{bθ}
export type PolarPoint = { r: number; theta: number };
export function spiralFit(points: PolarPoint[]): EquationResult {
  const n = points.length;
  if (n < 3) { return {
    id: "SPIRAL",
    values: { a: NaN, b: NaN, R2: 0 },
    units: { a: "L", b: "1", R2: "1" },
    meaning: ["Need ≥3 points for a stable spiral fit."],
    tex: [String.raw`r(\theta)=ae^{b\theta}`]
  }; }
  const r = points.map(p => Math.max(p.r, 1e-12));
  const th= points.map(p => p.theta);
  const y = r.map(v => Math.log(v));
  let sx=0, sy=0, sxx=0, sxy=0;
  for (let i=0;i<n;i++){ const x=th[i]; sx+=x; sy+=y[i]; sxx+=x*x; sxy+=x*y[i]; }
  const det = n*sxx - sx*sx || 1e-12;
  const ln_a = (sxx*sy - sx*sxy)/det;
  const b    = (n*sxy - sx*sy)/det;
  // R^2
  const yhat = th.map(x => ln_a + b*x);
  const ymean = sy/n;
  const ssr = y.reduce((s,yi,i)=>s+(yi - yhat[i])**2, 0);
  const sst = y.reduce((s,yi)=>s+(yi - ymean)**2, 0) || 1e-12;
  const R2 = 1 - ssr/sst;
  const a = Math.exp(ln_a);
  const tex = [
    String.raw`r(\theta)=ae^{b\theta}\quad\Rightarrow\quad \ln r = \ln a + b\theta`,
    String.raw`b \text{ quantifies spiral curvature; } R^2 \text{ fit quality.}`
  ];
  const meaning = [
    "b>0: expanding spiral; b<0: contracting.",
    "R² close to 1 ⇒ the glyph is truly spiral in form."
  ];
  return { id: "SPIRAL", values: { a, b, R2 }, units: { a: "L", b: "1", R2: "1" }, meaning, tex };
}

// 4) Echo: max cross-correlation lag/strength
export function echoPeak(x: number[], y: number[], maxLag?: number): EquationResult {
  // normalize
  const nx = normz(x), ny = normz(y);
  const n = nx.length + ny.length - 1;
  const corr: number[] = new Array(n).fill(0);
  // direct (safe) correlation
  const lags: number[] = [];
  for (let k = -ny.length+1; k < nx.length; k++) {
    let s = 0;
    for (let i=0;i<nx.length;i++){
      const j = i - k;
      if (j>=0 && j<ny.length) s += nx[i]*ny[j];
    }
    lags.push(k);
    corr[k + ny.length - 1] = s / (nx.length); // normalized-ish
  }
  let iMax = 0; for (let i=1;i<corr.length;i++){ if (corr[i] > corr[iMax]) iMax = i; }
  const lag = lags[iMax];
  const rho = corr[iMax];
  const tex = [
    String.raw`\tau_{\text{echo}}=\arg\max_{\tau}\left(\sum_t x(t)\,y(t+\tau)\right),\quad \rho_{\max}=\max_{\tau}\rho_{xy}(\tau)`
  ];
  const meaning = [
    "Echo lag near 0 ⇒ near-instant reflection; large |lag| ⇒ delayed mirror.",
    "High ρ means strong recognition by the field."
  ];
  return { id: "ECHO", values: { lag, rho }, units: { lag: "samples", rho: "1" }, meaning, tex };
}

function normz(a: number[]): number[] {
  const m = a.reduce((s,x)=>s+x,0)/(a.length||1);
  const v = a.reduce((s,x)=>s+(x-m)*(x-m),0)/(a.length||1);
  const sd = Math.sqrt(v)+1e-12;
  return a.map(x=>(x-m)/sd);
}

// ---------- Intuition compiler (keyword router) ----------
export function compileIntuition(text: string): CompileIntent {
  const t = (text||"").toLowerCase();
  const eqs: EquationId[] = [];
  if (/\bqssr|\bcoherence|\bphasor/.test(t)) eqs.push("QSSR");
  if (/\bkuramoto|\bunison|\bsync/.test(t))  eqs.push("KURAMOTO");
  if (/\bspiral|\blog\s?spiral|\bglyph/.test(t)) eqs.push("SPIRAL");
  if (/\becho|\bcross.?corr|\brecognition/.test(t)) eqs.push("ECHO");
  if (eqs.length===0) eqs.push("QSSR"); // default useful
  return { equations: eqs, notes: "Compiled by keyword routing." };
}

// ---------- Aggregator ----------
export interface AureonRunInput {
  intent: CompileIntent;
  data: {
    // QSSR & Kuramoto
    amps?: number[];
    omegas?: number[];
    phases?: number[];
    t?: number;
    // Spiral
    points?: PolarPoint[];
    // Echo
    x?: number[];
    y?: number[];
    maxLag?: number;
  };
}

export interface AureonRunOutput {
  results: EquationResult[];
  ok: boolean;
  errors?: string[];
}

// Execute selected equations with provided data (robust defaults)
export function runAureon(input: AureonRunInput): AureonRunOutput {
  const out: EquationResult[] = [];
  const errs: string[] = [];
  const eqs = input.intent.equations;

  for (const id of eqs) {
    try {
      if (id === "QSSR") {
        const amps   = input.data.amps   ?? [1, 0.8, 0.6];
        const omegas = input.data.omegas ?? [0.9, 1.1, 1.3];
        const phases = input.data.phases ?? [0, 0.3, -0.2];
        const t      = input.data.t      ?? 0;
        out.push(qssrCoherence(amps, omegas, phases, t));
      } else if (id === "KURAMOTO") {
        const phases = input.data.phases ?? [0, 0.2, -0.4, 1.1];
        out.push(kuramotoOrder(phases));
      } else if (id === "SPIRAL") {
        const pts = input.data.points ?? [
          { r: 1.0, theta: 0.0 },
          { r: 1.3, theta: 0.6 },
          { r: 1.8, theta: 1.2 },
          { r: 2.6, theta: 1.8 },
        ];
        out.push(spiralFit(pts));
      } else if (id === "ECHO") {
        const x = input.data.x ?? [0,1,1,0, -1,-1,0, 1,0];
        const y = input.data.y ?? [0,1,1,0, -1,-1,0, 1,0];
        const maxLag = input.data.maxLag;
        out.push(echoPeak(x, y, maxLag));
      }
    } catch (e: any) {
      errs.push(`${id}: ${String(e?.message||e)}`);
    }
  }

  return { results: out, ok: errs.length===0, errors: errs.length?errs:undefined };
}

// ---------- Render helpers ----------
export function asCSV(rows: Array<Record<string, any>>): string {
  if (!rows.length) return "";
  const keys = Object.keys(rows[0]);
  const esc = (s:any)=>`"${String(s).replace(/"/g, '""')}"`;
  return [keys.join(","), ...rows.map(r=>keys.map(k=>esc(r[k])).join(","))].join("\n");
}

export function flattenResults(rs: EquationResult[]): Record<string, any>[] {
  return rs.map(r => ({ id: r.id, ...r.values }));
}

export const AureonCore = {
  compileIntuition, runAureon,
  qssrCoherence, kuramotoOrder, spiralFit, echoPeak,
  asCSV, flattenResults,
};

export default AureonCore;
