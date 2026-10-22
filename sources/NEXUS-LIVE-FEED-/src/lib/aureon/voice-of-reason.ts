// src/lib/aureon/voice-of-reason.ts
// The Voice of Reason — retrospective, nowcast, forecast, counterfactuals.

export type Sample = { t: number; v: number }; // epoch ms, value
export type Series = Sample[];

export type Retrospective = {
  n: number;
  window_ms: number;
  mean: number;
  min: number;
  max: number;
  slope_per_hr: number;        // linear trend
  change_pct: number;          // last vs first
  anomalies: Array<{ t: number; v: number; z: number }>;
};

export type Nowcast = {
  last_t: number | null;
  last_v: number | null;
  freshness_ms: number | null;
  integrity: "GREEN" | "AMBER" | "RED";
  integrityScore: number | null;
  notes: string[];
};

export type Forecast = {
  horizon_ms: number;
  model: "EMA+TREND";
  yhat: Array<{ t: number; v: number; lo: number; hi: number }>;
  rmse: number;
};

export type WhatIf = {
  label: string;
  baseline: number | null;
  scenario: number | null;
  delta: number | null;
  notes: string[];
};

const clamp = (x:number, lo:number, hi:number)=>Math.max(lo, Math.min(hi, x));
const mean = (xs:number[]) => xs.length ? xs.reduce((a,b)=>a+b,0)/xs.length : NaN;
const std  = (xs:number[]) => {
  if (xs.length < 2) return NaN;
  const m = mean(xs); const v = mean(xs.map(x => (x-m)*(x-m)));
  return Math.sqrt(v);
};

function linearTrend(series: Series){
  // simple least squares on (t, v)
  if (series.length < 2) return { slope: 0, intercept: series[0]?.v ?? 0 };
  const xs = series.map(s=>s.t/3600000); // hours
  const ys = series.map(s=>s.v);
  const mx = mean(xs), my = mean(ys);
  let num=0, den=0;
  for (let i=0;i<xs.length;i++){ num += (xs[i]-mx)*(ys[i]-my); den += (xs[i]-mx)*(xs[i]-mx); }
  const slope = den ? num/den : 0;
  const intercept = my - slope*mx;
  return { slope, intercept };
}

function ema(series: Series, alpha=0.2){
  let y: number[] = [];
  for (let i=0;i<series.length;i++){
    const v = series[i].v;
    if (i===0) y.push(v); else y.push(alpha*v + (1-alpha)*y[i-1]);
  }
  return y;
}

export function retrospective(series: Series, lookback_ms: number, zThreshold=3): Retrospective {
  const now = Date.now();
  const lo = now - lookback_ms;
  const sub = series.filter(s=>s.t>=lo);
  const values = sub.map(s=>s.v);
  const m = mean(values);
  const mn = Math.min(...values);
  const mx = Math.max(...values);
  const { slope } = linearTrend(sub);
  const change_pct = (sub.length>=2) ? ((sub[sub.length-1].v - sub[0].v) / Math.max(Math.abs(sub[0].v), 1e-12))*100 : 0;

  // anomalies via rolling z on detrended residuals
  const yhat = ema(sub, 0.2);
  const resid = sub.map((s,i)=> s.v - yhat[i]);
  const sdev = std(resid);
  const anomalies = sub
    .map((s,i)=> ({ t:s.t, v:s.v, z: sdev ? (resid[i]/sdev) : 0 }))
    .filter(a => Math.abs(a.z) >= zThreshold);

  return {
    n: sub.length,
    window_ms: lookback_ms,
    mean: isFinite(m)?m:NaN,
    min: isFinite(mn)?mn:NaN,
    max: isFinite(mx)?mx:NaN,
    slope_per_hr: slope,
    change_pct,
    anomalies
  };
}

export function nowcast(series: Series, stalenessRed=60_000, stalenessAmber=10_000): Nowcast {
  const last = series[series.length-1];
  if (!last) return { last_t: null, last_v: null, freshness_ms: null, integrity: "RED", integrityScore: null, notes:["no data"]};
  const freshness = Date.now() - last.t;
  const integrity = freshness>stalenessRed ? "RED" : (freshness>stalenessAmber ? "AMBER" : "GREEN");
  const notes: string[] = [];
  if (integrity!=="GREEN") notes.push(`freshness=${freshness}ms`);
  
  let score = 1.0;
  if (freshness > stalenessAmber) {
    score = 1.0 - (freshness - stalenessAmber) / (stalenessRed - stalenessAmber);
  }
  const integrityScore = clamp(score, 0, 1);

  return { last_t: last.t, last_v: last.v, freshness_ms: freshness, integrity, integrityScore, notes };
}

export function forecast(series: Series, horizon_ms=60_000, steps=30): Forecast {
  if (series.length<3) return { horizon_ms, model:"EMA+TREND", yhat:[], rmse:NaN };
  const sm = ema(series, 0.25);
  const detrended: Series = series.map((s,i)=>({ t: s.t, v: s.v - sm[i]}));
  const { slope } = linearTrend(series);
  const last = series[series.length-1];
  const dt = Math.floor(horizon_ms/steps);
  // residual RMSE around EMA
  const resid = series.map((s,i)=> s.v - sm[i]);
  const rmse = Math.sqrt(mean(resid.map(r=>r*r))) || 0;

  const out = [];
  for (let k=1;k<=steps;k++){
    const t = last.t + k*dt;
    const hoursFromLast = (t - last.t)/3600000;
    const v = sm[sm.length-1] + slope*hoursFromLast; // EMA baseline + linear drift
    out.push({ t, v, lo: v - 1.96*rmse, hi: v + 1.96*rmse });
  }
  return { horizon_ms, model:"EMA+TREND", yhat: out, rmse };
}

export type Sensitivity = { // simple linear sensitivity for sandbox “what-if”
  metric: string;            // e.g., "qssr.coherence"
  dY_dX: number;             // ∂(target)/∂(this metric)
  clamp_lo?: number;
  clamp_hi?: number;
};

export function whatIf(
  baseline: number | null,
  deltaX: number,
  sens: Sensitivity
): WhatIf {
  if (baseline==null) return { label: sens.metric, baseline: null, scenario: null, delta: null, notes:["no baseline"]};
  let scenario = baseline + sens.dY_dX*deltaX;
  if (sens.clamp_lo!==undefined) scenario = Math.max(sens.clamp_lo, scenario);
  if (sens.clamp_hi!==undefined) scenario = Math.min(sens.clamp_hi, scenario);
  return {
    label: sens.metric,
    baseline,
    scenario,
    delta: scenario - baseline,
    notes: ["counterfactual (simulation only)"]
  };
}
