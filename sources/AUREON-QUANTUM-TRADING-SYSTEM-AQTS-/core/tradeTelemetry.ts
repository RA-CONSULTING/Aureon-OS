import { appendFileSync } from 'fs';
import path from 'path';

export interface TradeTelemetryRecord {
  ts: string;
  cycle: number;
  symbol: string;
  lambda: number;
  coherence: number;
  appliedThreshold: number;
  baseThreshold: number;
  votes: number;
  requiredVotes: number;
  direction: 'BUY' | 'SELL' | 'HOLD';
  decision: 'EXECUTE' | 'SKIP';
  reason: string;
  alpha: number;
  beta: number;
  // Lighthouse energy metrics (ablation study)
  lighthouse?: {
    Q: number;          // |Q| — Anomaly pointer (flame)
    G_eff: number;      // G_eff — Effective gravity (brake)
    C_lin: number;      // Linear coherence
    C_nonlin: number;   // Nonlinear coherence
    L: number;          // Lighthouse intensity
  };
  // Harmonic loop stability metrics (Harmonic String Theory)
  harmonicStability?: {
    coherencePeak: number;      // Γ_peak masked autocorrelation peak
    rmsPower: number;           // RMS power of Λ
    amplificationRatio: number; // RMS / baselineRMS gain factor
    sampleSize: number;         // samples used for calculation
  };
}

export function logTelemetry(filePath: string | null, rec: TradeTelemetryRecord): void {
  if (!filePath) return;
  try {
    appendFileSync(filePath, JSON.stringify(rec) + '\n');
  } catch {
    // swallow
  }
}

export function ensureArtifactsPath(): string | null {
  try {
    const artifacts = path.resolve(process.cwd(), 'artifacts');
    return artifacts;
  } catch {
    return null;
  }
}
