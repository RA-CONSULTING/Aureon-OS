#!/usr/bin/env tsx
import { writeFileSync } from 'node:fs';

// Simple discrete simulator for the Master Formula in the paper
// Λ[n] = substrate[n] + α * tanh(g * avgLambda[n]) + β * Lambda[n - kτ] + noise

type Params = {
  fs: number; // sampling frequency Hz
  T: number; // total time seconds
  alpha: number;
  beta: number;
  tauMs: number;
  g: number;
  deltaTms: number; // observer integration window in ms
  substrate: { f: number; w: number; phi: number }[];
  noiseStd: number;
};

const params: Params = {
  fs: 1000,
  T: 2.0,
  alpha: 0.85,
  beta: 0.90,
  tauMs: 50,
  g: 1.5,
  deltaTms: 25,
  substrate: [
    { f: 5, w: 1.0, phi: 0 },
    { f: 13, w: 0.6, phi: 0.3 },
    { f: 21, w: 0.4, phi: 1.1 },
  ],
  noiseStd: 0.05,
};

const N = Math.round(params.fs * params.T);
const dt = 1 / params.fs;

const kTau = Math.max(1, Math.round((params.tauMs / 1000) * params.fs));
const Nobs = Math.max(1, Math.round((params.deltaTms / 1000) * params.fs));

console.log('Harmonic simulator starting with params:', { ...params, N, kTau, Nobs });

// helper RNG
function gaussian(mean = 0, std = 1) {
  let u = 0, v = 0;
  while (u === 0) u = Math.random();
  while (v === 0) v = Math.random();
  const z = Math.sqrt(-2.0 * Math.log(u)) * Math.cos(2.0 * Math.PI * v);
  return z * std + mean;
}

// substrate generator
function substrateAt(t: number) {
  let s = 0;
  for (const sComp of params.substrate) {
    s += sComp.w * Math.sin(2 * Math.PI * sComp.f * t + sComp.phi);
  }
  return s;
}

// Preallocate arrays
const Lambda: Float64Array = new Float64Array(N + kTau + 10);
const substrateArr: Float64Array = new Float64Array(N);

for (let n = 0; n < N; n++) {
  substrateArr[n] = substrateAt(n * dt);
}

// Running sum for moving average
let obsSum = 0;
const window: number[] = [];

for (let n = 0; n < N; n++) {
  const t = n * dt;
  const s = substrateArr[n];

  // update moving window
  window.push(Lambda[n - 1] ?? 0);
  obsSum += window[window.length - 1];
  if (window.length > Nobs) {
    obsSum -= window.shift() ?? 0;
  }
  const avgLambda = window.length > 0 ? obsSum / window.length : 0;

  const observer = params.alpha * Math.tanh(params.g * avgLambda);
  const echo = (n - kTau >= 0) ? params.beta * Lambda[n - kTau] : 0;
  const noise = gaussian(0, params.noiseStd);

  const value = s + observer + echo + noise;
  Lambda[n] = value;
}

// Analysis: compute coherence C as max normalized autocorrelation at nonzero lag
function autocorrelation(x: Float64Array) {
  const M = x.length;
  const mean = x.reduce((a, b) => a + b, 0) / M;
  const ac = new Float64Array(M);
  for (let lag = 0; lag < M; lag++) {
    let num = 0;
    let den = 0;
    for (let i = 0; i + lag < M; i++) {
      num += (x[i] - mean) * (x[i + lag] - mean);
    }
    for (let i = 0; i < M; i++) {
      den += (x[i] - mean) * (x[i] - mean);
    }
    ac[lag] = den > 0 ? num / den : 0;
  }
  return ac;
}

const ac = autocorrelation(Lambda.subarray(0, N));
let C = 0;
for (let i = 1; i < ac.length; i++) {
  if (ac[i] > C) C = ac[i];
}

// PSD via naive DFT (sufficient for small N)
function PSD(x: Float64Array) {
  const M = x.length;
  const psd: number[] = new Array(M / 2).fill(0);
  for (let k = 0; k < M / 2; k++) {
    let re = 0;
    let im = 0;
    for (let n = 0; n < M; n++) {
      const phi = (-2 * Math.PI * k * n) / M;
      re += x[n] * Math.cos(phi);
      im += x[n] * Math.sin(phi);
    }
    psd[k] = (re * re + im * im) / M;
  }
  const freqs = new Array(psd.length).fill(0).map((_, i) => (i * params.fs) / N);
  return { freqs, psd };
}

const { freqs, psd } = PSD(Lambda.subarray(0, N));

// find peaks in PSD
function findPeaks(freqs: number[], psd: number[], minProminence = 0.1) {
  const peaks: { f: number; p: number }[] = [];
  for (let i = 1; i < psd.length - 1; i++) {
    if (psd[i] > psd[i - 1] && psd[i] > psd[i + 1]) {
      peaks.push({ f: freqs[i], p: psd[i] });
    }
  }
  peaks.sort((a, b) => b.p - a.p);
  return peaks.slice(0, 10);
}

const peaks = findPeaks(freqs, psd);

// Estimate comb spacing by finding differences between prominent peaks
let estTau = 0;
if (peaks.length >= 2) {
  const diffs: number[] = [];
  for (let i = 0; i < Math.min(6, peaks.length - 1); i++) {
    diffs.push(Math.abs(peaks[i].f - peaks[i + 1].f));
  }
  const avgDf = diffs.reduce((a, b) => a + b, 0) / diffs.length;
  if (avgDf > 0) estTau = 1 / avgDf;
}

console.log('\n---- Simulation Results ----');
console.log('Samples:', N, 'fs:', params.fs, 'T(s):', params.T);
console.log('Coherence C (max nonzero ac):', C.toFixed(4));
console.log('Estimated delay (tau) from PSD comb spacing (s):', estTau.toFixed(4));
console.log('Top PSD peaks (freq Hz, power):');
for (let i = 0; i < Math.min(peaks.length, 8); i++) {
  console.log(`  ${i + 1}. ${peaks[i].f.toFixed(3)} Hz  (${peaks[i].p.toFixed(5)})`);
}

// save CSV of time series and PSD
try {
  const csvLines = ['t,lambda,substrate'];
  for (let n = 0; n < N; n++) {
    csvLines.push(`${(n * dt).toFixed(6)},${Lambda[n].toFixed(6)},${substrateArr[n].toFixed(6)}`);
  }
  writeFileSync('harmonic_simulation_timeseries.csv', csvLines.join('\n'));
  const psdCsv = ['freq,psd'];
  for (let i = 0; i < freqs.length; i++) psdCsv.push(`${freqs[i].toFixed(6)},${psd[i].toFixed(8)}`);
  writeFileSync('harmonic_simulation_psd.csv', psdCsv.join('\n'));
  console.log('\nCSV outputs written: harmonic_simulation_timeseries.csv, harmonic_simulation_psd.csv');
} catch (err) {
  console.warn('Unable to write CSV:', (err as Error).message);
}

console.log('\nDone.');
