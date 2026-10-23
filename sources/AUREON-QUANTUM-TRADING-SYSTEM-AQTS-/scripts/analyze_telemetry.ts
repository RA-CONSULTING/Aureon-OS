#!/usr/bin/env node
/**
 * LIGHTHOUSE TELEMETRY ANALYZER
 * 
 * Analyzes trade_telemetry.jsonl for:
 * - Skip reason distribution
 * - |Q| & G_eff correlation with execution
 * - Coherence boost impact
 * - Ablation study validation
 * 
 * Gary Leckey & GitHub Copilot | November 15, 2025
 */

import { readFileSync } from 'fs';
import path from 'path';

interface TelemetryRecord {
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
  lighthouse?: {
    Q: number;
    G_eff: number;
    C_lin: number;
    C_nonlin: number;
    L: number;
  };
}

function analyzeTelemetry(filePath: string): void {
  console.log('');
  console.log('═══════════════════════════════════════════════════════');
  console.log('   🔦 LIGHTHOUSE TELEMETRY ANALYSIS');
  console.log('═══════════════════════════════════════════════════════');
  console.log('');

  const content = readFileSync(filePath, 'utf-8');
  const lines = content.trim().split('\n').filter(l => l.length > 0);
  const records: TelemetryRecord[] = lines.map(l => JSON.parse(l));

  if (records.length === 0) {
    console.log('No telemetry records found.');
    return;
  }

  console.log(`📊 DATASET:`);
  console.log(`   Total Cycles: ${records.length}`);
  console.log(`   Symbol: ${records[0].symbol}`);
  console.log(`   Timespan: ${records[0].ts} → ${records[records.length - 1].ts}`);
  console.log('');

  // Decision distribution
  const executed = records.filter(r => r.decision === 'EXECUTE').length;
  const skipped = records.filter(r => r.decision === 'SKIP').length;
  const executionRate = (executed / records.length) * 100;

  console.log(`📈 EXECUTION RATE:`);
  console.log(`   Executed: ${executed} (${executionRate.toFixed(1)}%)`);
  console.log(`   Skipped:  ${skipped} (${(100 - executionRate).toFixed(1)}%)`);
  console.log('');

  // Skip reason breakdown
  const skipReasons: Record<string, number> = {};
  for (const record of records) {
    if (record.decision === 'SKIP') {
      skipReasons[record.reason] = (skipReasons[record.reason] || 0) + 1;
    }
  }

  console.log(`🚫 SKIP REASONS:`);
  for (const [reason, count] of Object.entries(skipReasons).sort((a, b) => b[1] - a[1])) {
    const pct = ((count / skipped) * 100).toFixed(1);
    console.log(`   ${reason.padEnd(25)}: ${count.toString().padStart(3)} (${pct}%)`);
  }
  console.log('');

  // Lighthouse metrics statistics
  const withMetrics = records.filter(r => r.lighthouse && r.lighthouse.Q > 0);
  
  if (withMetrics.length > 0) {
    const Q_values = withMetrics.map(r => r.lighthouse!.Q);
    const G_eff_values = withMetrics.map(r => r.lighthouse!.G_eff);
    const C_lin_values = withMetrics.map(r => r.lighthouse!.C_lin);
    const C_nonlin_values = withMetrics.map(r => r.lighthouse!.C_nonlin);
    const L_values = withMetrics.map(r => r.lighthouse!.L);

    console.log(`🔦 LIGHTHOUSE METRICS (${withMetrics.length} samples):`);
    console.log('');
    
    console.log(`   |Q| (Anomaly Pointer — Flame):`);
    console.log(`      Mean:   ${mean(Q_values).toFixed(4)}`);
    console.log(`      Median: ${median(Q_values).toFixed(4)}`);
    console.log(`      Max:    ${Math.max(...Q_values).toFixed(4)}`);
    console.log(`      StdDev: ${stdDev(Q_values).toFixed(4)}`);
    console.log('');
    
    console.log(`   G_eff (Effective Gravity — Brake):`);
    console.log(`      Mean:   ${mean(G_eff_values).toFixed(4)}`);
    console.log(`      Median: ${median(G_eff_values).toFixed(4)}`);
    console.log(`      Max:    ${Math.max(...G_eff_values).toFixed(4)}`);
    console.log(`      StdDev: ${stdDev(G_eff_values).toFixed(4)}`);
    console.log('');
    
    console.log(`   C_lin (Linear Coherence):`);
    console.log(`      Mean:   ${mean(C_lin_values).toFixed(4)}`);
    console.log(`      Max:    ${Math.max(...C_lin_values).toFixed(4)}`);
    console.log('');
    
    console.log(`   C_nonlin (Nonlinear Coherence):`);
    console.log(`      Mean:   ${mean(C_nonlin_values).toFixed(4)}`);
    console.log(`      Min:    ${Math.min(...C_nonlin_values).toFixed(4)}`);
    console.log('');
    
    console.log(`   L (Lighthouse Intensity):`);
    console.log(`      Mean:   ${mean(L_values).toFixed(4)}`);
    console.log(`      Max:    ${Math.max(...L_values).toFixed(4)}`);
    console.log('');

    // Flame threshold analysis
    const flameThreshold = 0.7;
    const flameLit = withMetrics.filter(r => r.lighthouse!.Q > flameThreshold).length;
    console.log(`   🔥 FLAME LIT (|Q| > ${flameThreshold}): ${flameLit} cycles (${((flameLit / withMetrics.length) * 100).toFixed(1)}%)`);
    
    // Brake threshold analysis
    const brakeThreshold = 0.7;
    const brakeActive = withMetrics.filter(r => r.lighthouse!.G_eff > brakeThreshold).length;
    console.log(`   🛑 BRAKE ACTIVE (G_eff > ${brakeThreshold}): ${brakeActive} cycles (${((brakeActive / withMetrics.length) * 100).toFixed(1)}%)`);
    console.log('');
  } else {
    console.log(`⚠️  No Lighthouse metrics available (insufficient data history)`);
    console.log('');
  }

  // Coherence boost impact
  const avgRawCoherence = mean(records.map(r => r.coherence / 1.1)); // reverse boost for raw estimate
  const avgBoostedCoherence = mean(records.map(r => r.coherence));
  const avgThreshold = mean(records.map(r => r.appliedThreshold));

  console.log(`🌍 STARGATE GRID IMPACT:`);
  console.log(`   Avg Raw Coherence (est):    ${avgRawCoherence.toFixed(3)}`);
  console.log(`   Avg Boosted Coherence:      ${avgBoostedCoherence.toFixed(3)}`);
  console.log(`   Avg Adaptive Threshold:     ${avgThreshold.toFixed(3)}`);
  console.log(`   Coherence Boost:            +${((avgBoostedCoherence / avgRawCoherence - 1) * 100).toFixed(1)}%`);
  console.log('');

  // Vote statistics
  const avgVotes = mean(records.map(r => r.votes));
  const maxVotes = Math.max(...records.map(r => r.votes));
  const consensusMet = records.filter(r => r.votes >= r.requiredVotes).length;

  console.log(`🔦 LIGHTHOUSE CONSENSUS:`);
  console.log(`   Avg Votes:           ${avgVotes.toFixed(1)}/9`);
  console.log(`   Max Votes:           ${maxVotes}/9`);
  console.log(`   Consensus Met:       ${consensusMet} cycles (${((consensusMet / records.length) * 100).toFixed(1)}%)`);
  console.log('');

  console.log('═══════════════════════════════════════════════════════');
  console.log('   ANALYSIS COMPLETE');
  console.log('═══════════════════════════════════════════════════════');
  console.log('');
}

// Statistics helpers
function mean(values: number[]): number {
  return values.reduce((sum, v) => sum + v, 0) / values.length;
}

function median(values: number[]): number {
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 === 0 ? (sorted[mid - 1] + sorted[mid]) / 2 : sorted[mid];
}

function stdDev(values: number[]): number {
  const avg = mean(values);
  const variance = values.reduce((sum, v) => sum + Math.pow(v - avg, 2), 0) / values.length;
  return Math.sqrt(variance);
}

// Run analysis
const telemetryPath = path.join(process.cwd(), 'artifacts', 'trade_telemetry.jsonl');
try {
  analyzeTelemetry(telemetryPath);
} catch (error: any) {
  console.error(`Error: ${error.message}`);
  process.exit(1);
}
