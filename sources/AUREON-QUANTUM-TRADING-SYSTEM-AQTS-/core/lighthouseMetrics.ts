/**
 * LIGHTHOUSE ENERGY METRICS — |Q| & G_eff
 * 
 * Implements QGITA ablation study metrics:
 * - |Q| (Anomaly Pointer): Flame metric — spikes during sudden change
 * - G_eff (Effective Gravity): Brake metric — geometric curvature × Fibonacci match
 * 
 * Based on QGITA Whitepaper ablation study:
 * "Nonlinear coherence (C_nonlin) and effective gravity signal (G_eff) 
 *  are the most critical components for event confirmation, while an 
 *  anomaly pointer metric (|Q|) acts as a suppressor for spurious triggers."
 * 
 * Gary Leckey & GitHub Copilot | November 15, 2025
 */

import { MarketSnapshot } from './binanceWebSocket';

export interface LighthouseMetrics {
  Q: number;          // |Q| — Anomaly pointer (0-1), flame metric
  G_eff: number;      // G_eff — Effective gravity (0-1), brake metric
  C_lin: number;      // Linear coherence (MACD-based)
  C_nonlin: number;   // Nonlinear coherence (volatility-adjusted)
  L: number;          // Lighthouse intensity (geometric mean)
}

export interface HarmonicLoopMetrics {
  coherencePeak: number;      // Γ_peak — masked ACF peak excluding lag 0 band
  rmsPower: number;           // RMS(Λ) — current loop power
  amplificationRatio: number; // RMS(Λ) / RMS_baseline — gain vs early baseline
  sampleSize: number;         // number of Lambda samples used
}

/**
 * PHI — Golden ratio
 */
const PHI = 1.618033988749;
const PHI_INV = 1 / PHI;

/**
 * Compute |Q| — Anomaly Pointer (Flame Metric)
 * 
 * Measures sudden deviation from baseline:
 * - Volume spikes
 * - Spread expansion
 * - Price acceleration
 * 
 * High |Q| = flame lit (sudden change detected)
 */
export function computeAnomalyPointer(
  snapshot: MarketSnapshot,
  priceHistory: number[],
  volumeHistory: number[]
): number {
  if (priceHistory.length < 10 || volumeHistory.length < 10) return 0;

  // Volume spike component
  const recentVolume = volumeHistory.slice(-10);
  const meanVolume = recentVolume.reduce((sum, v) => sum + v, 0) / recentVolume.length;
  const volumeSpike = snapshot.volume ? Math.min(1, snapshot.volume / (meanVolume + 1)) : 0;

  // Spread expansion component
  const spread = snapshot.spread || 0;
  const price = snapshot.price;
  const spreadRatio = spread / price;
  const spreadAnomaly = Math.min(1, spreadRatio * 1000); // normalize to 0-1

  // Price acceleration component (second derivative)
  const recentPrices = priceHistory.slice(-5);
  if (recentPrices.length < 3) return volumeSpike * 0.5 + spreadAnomaly * 0.5;
  
  const diffs = [];
  for (let i = 1; i < recentPrices.length; i++) {
    diffs.push(recentPrices[i] - recentPrices[i - 1]);
  }
  
  const accel = [];
  for (let i = 1; i < diffs.length; i++) {
    accel.push(Math.abs(diffs[i] - diffs[i - 1]));
  }
  
  const meanAccel = accel.reduce((sum, a) => sum + a, 0) / accel.length;
  const priceAccel = Math.min(1, meanAccel / (price * 0.001)); // normalize

  // Weighted combination
  const Q = volumeSpike * 0.4 + spreadAnomaly * 0.3 + priceAccel * 0.3;
  
  return Math.min(1, Q);
}

/**
 * Compute G_eff — Effective Gravity (Brake Metric)
 * 
 * G_eff = α × |κ| × (1 - |r_k - φ^(-1)| / ε)_+ × |Δx| / 2
 * 
 * Components:
 * - |κ|: Price curvature (second derivative)
 * - Fibonacci match: Deviation from golden ratio spacing
 * - Local contrast: Price delta magnitude
 * 
 * High G_eff = brake applied (geometric constraint active)
 */
export function computeEffectiveGravity(
  priceHistory: number[],
  timeHistory: number[],
  alpha: number = 1.0,
  tolerance: number = 0.1
): number {
  if (priceHistory.length < 5 || timeHistory.length < 5) return 0;

  const recent = priceHistory.slice(-5);
  const times = timeHistory.slice(-5);

  // Compute curvature κ (discrete second derivative)
  const p0 = recent[recent.length - 3];
  const p1 = recent[recent.length - 2];
  const p2 = recent[recent.length - 1];
  
  const dx1 = p1 - p0;
  const dx2 = p2 - p1;
  const curvature = Math.abs(dx2 - dx1);
  
  // Normalize curvature by price scale
  const kappa = curvature / (p1 + 1);

  // Compute interval ratio (check for Fibonacci spacing)
  const t0 = times[times.length - 3];
  const t1 = times[times.length - 2];
  const t2 = times[times.length - 1];
  
  const dt1 = t1 - t0;
  const dt2 = t2 - t1;
  
  const ratio = dt1 > 0 ? dt2 / dt1 : 1.0;
  
  // Fibonacci match quality
  const fibMatch = Math.max(0, 1 - Math.abs(ratio - PHI_INV) / tolerance);

  // Local contrast (price delta)
  const localContrast = Math.abs(p2 - p1) / 2;
  const normalizedContrast = Math.min(1, localContrast / (p1 * 0.01));

  // G_eff formula
  const G_eff = alpha * kappa * fibMatch * normalizedContrast;
  
  return Math.min(1, G_eff * 100); // scale to 0-1
}

/**
 * Compute C_lin — Linear Coherence (MACD-based)
 * 
 * Measures trend strength via exponential moving averages
 */
export function computeLinearCoherence(priceHistory: number[], window: number = 20): number {
  if (priceHistory.length < window) return 0;

  const prices = priceHistory.slice(-window);
  
  // Simple EMA implementation
  const emaFast = computeEMA(prices, 12);
  const emaSlow = computeEMA(prices, 26);
  
  const macd = emaFast - emaSlow;
  const coherence = Math.min(1, Math.abs(macd) / (emaSlow * 0.05));
  
  return coherence;
}

/**
 * Compute C_nonlin — Nonlinear Coherence (Volatility-adjusted)
 * 
 * Inverse relationship: low volatility = high coherence
 */
export function computeNonlinearCoherence(priceHistory: number[], window: number = 20): number {
  if (priceHistory.length < window) return 0;

  const recent = priceHistory.slice(-window);
  const mean = recent.reduce((sum, p) => sum + p, 0) / recent.length;
  const variance = recent.reduce((sum, p) => sum + Math.pow(p - mean, 2), 0) / recent.length;
  const volatility = Math.sqrt(variance) / mean;
  
  const coherence = 1.0 / (1.0 + volatility);
  
  return coherence;
}

/**
 * Compute L — Lighthouse Intensity (Geometric Mean)
 * 
 * L(t) = (C_lin^w1 × C_nonlin^w2 × G_eff^w3 × |Q|^w4)^(1/Σw_i)
 * 
 * Ablation study weights:
 * - C_nonlin: 1.2 (strongest driver)
 * - G_eff: 1.2 (strongest driver)
 * - |Q|: 0.8 (suppressor for spurious triggers)
 * - C_lin: 1.0 (baseline)
 */
export function computeLighthouseIntensity(
  C_lin: number,
  C_nonlin: number,
  G_eff: number,
  Q: number,
  weights: number[] = [1.0, 1.2, 1.2, 0.8]
): number {
  const metrics = [C_lin, C_nonlin, G_eff, Q];
  
  // Geometric mean with weights
  let product = 1.0;
  for (let i = 0; i < metrics.length; i++) {
    if (metrics[i] <= 0) return 0; // any zero kills consensus
    product *= Math.pow(metrics[i], weights[i]);
  }
  
  const totalWeight = weights.reduce((sum, w) => sum + w, 0);
  const L = Math.pow(product, 1.0 / totalWeight);
  
  return L;
}

/**
 * Compute all Lighthouse metrics from snapshot and history
 */
export function computeLighthouseMetrics(
  snapshot: MarketSnapshot,
  priceHistory: number[],
  volumeHistory: number[],
  timeHistory: number[]
): LighthouseMetrics {
  const Q = computeAnomalyPointer(snapshot, priceHistory, volumeHistory);
  const G_eff = computeEffectiveGravity(priceHistory, timeHistory);
  const C_lin = computeLinearCoherence(priceHistory);
  const C_nonlin = computeNonlinearCoherence(priceHistory);
  const L = computeLighthouseIntensity(C_lin, C_nonlin, G_eff, Q);
  
  return { Q, G_eff, C_lin, C_nonlin, L };
}

/**
 * Compute Harmonic Loop Metrics — Coherence & Amplification
 *
 * Approximates simulation math:
 *  - coherencePeak Γ_peak: max normalized autocorrelation excluding lag band around 0
 *  - rmsPower: √(mean(Λ²)) over full window
 *  - amplificationRatio: rmsPower / baselineRMS, baseline from earliest 10% of samples
 *
 * Mask logic: exclude lags 0..maskWidth (default 10) to avoid trivial self match.
 */
export function computeHarmonicLoopMetrics(
  lambdaSeries: number[],
  maskWidth: number = 10
): HarmonicLoopMetrics {
  const n = lambdaSeries.length;
  if (n < maskWidth + 5) {
    return { coherencePeak: 0, rmsPower: 0, amplificationRatio: 0, sampleSize: n };
  }

  // Mean-center
  const mean = lambdaSeries.reduce((s, v) => s + v, 0) / n;
  const centered = lambdaSeries.map(v => v - mean);

  // Autocorrelation (naive) — only compute needed lags up to n/4 for efficiency
  const maxLag = Math.min(Math.floor(n / 4), 200); // cap for performance
  const acf: number[] = [];
  for (let lag = 0; lag <= maxLag; lag++) {
    let sum = 0;
    for (let i = 0; i < n - lag; i++) {
      sum += centered[i] * centered[i + lag];
    }
    acf[lag] = sum;
  }
  const acf0 = acf[0] === 0 ? 1 : acf[0];
  for (let i = 0; i < acf.length; i++) acf[i] /= acf0; // normalize

  // Mask out lag band near zero
  let coherencePeak = 0;
  for (let lag = maskWidth + 1; lag < acf.length; lag++) {
    if (acf[lag] > coherencePeak) coherencePeak = acf[lag];
  }

  // RMS power
  const rmsPower = Math.sqrt(centered.reduce((s, v) => s + v * v, 0) / n);

  // Baseline RMS from earliest 10% of samples (min 10)
  const baselineCount = Math.max(10, Math.floor(n * 0.1));
  const baselineSlice = centered.slice(0, baselineCount);
  const baselineRMS = Math.sqrt(baselineSlice.reduce((s, v) => s + v * v, 0) / baselineSlice.length) || 1;
  const amplificationRatio = rmsPower / baselineRMS;

  return { coherencePeak, rmsPower, amplificationRatio, sampleSize: n };
}

/**
 * Helper: Compute exponential moving average
 */
function computeEMA(prices: number[], period: number): number {
  if (prices.length < period) return prices[prices.length - 1] || 0;
  
  const k = 2 / (period + 1);
  let ema = prices[0];
  
  for (let i = 1; i < prices.length; i++) {
    ema = prices[i] * k + ema * (1 - k);
  }
  
  return ema;
}
