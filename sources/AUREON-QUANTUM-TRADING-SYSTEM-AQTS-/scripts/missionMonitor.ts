#!/usr/bin/env tsx
/**
 * MISSION MONITOR - Real-time dashboard for ultra-aggressive mission
 * 
 * Displays live metrics, charts, and progress updates
 */

import fs from 'fs';
import path from 'path';

interface MissionSnapshot {
  timestamp: number;
  elapsedMinutes: number;
  totalTrades: number;
  winners: number;
  winRate: number;
  currentEquity: number;
  returnPercent: number;
  phase: string;
}

class MissionMonitor {
  private snapshots: MissionSnapshot[] = [];
  private logFile: string;

  constructor() {
    this.logFile = path.join(process.cwd(), 'mission_log.json');
  }

  displayDashboard() {
    console.clear();
    console.log('╔' + '═'.repeat(78) + '╗');
    console.log('║' + ' '.repeat(20) + '🔥 MISSION CONTROL DASHBOARD 🍯' + ' '.repeat(26) + '║');
    console.log('╚' + '═'.repeat(78) + '╝\n');

    if (this.snapshots.length === 0) {
      console.log('Waiting for mission data...\n');
      return;
    }

    const latest = this.snapshots[this.snapshots.length - 1];
    const startSnapshot = this.snapshots[0];

    // Mission Progress Bar
    const targetTrades = 50;
    const progress = Math.min(100, (latest.totalTrades / targetTrades) * 100);
    const barLength = 50;
    const filledBars = Math.floor((progress / 100) * barLength);
    const emptyBars = barLength - filledBars;
    const progressBar = '█'.repeat(filledBars) + '░'.repeat(emptyBars);
    
    console.log('┌─ MISSION PROGRESS ────────────────────────────────────────────────────────┐');
    console.log(`│ Phase: ${latest.phase.padEnd(68)}│`);
    console.log(`│ Time: ${latest.elapsedMinutes.toFixed(1)} min${' '.repeat(64)}│`);
    console.log(`│ [${progressBar}] ${progress.toFixed(0)}%${' '.repeat(5)}│`);
    console.log(`│ Trades: ${latest.totalTrades}/${targetTrades}${' '.repeat(61)}│`);
    console.log('└───────────────────────────────────────────────────────────────────────────┘\n');

    // Performance Metrics
    console.log('┌─ PERFORMANCE ─────────────────────────────────────────────────────────────┐');
    console.log(`│ Win Rate:        ${(latest.winRate * 100).toFixed(1)}% ${this.getWinRateEmoji(latest.winRate)}${' '.repeat(50)}│`);
    console.log(`│ Winners:         ${latest.winners}${' '.repeat(62)}│`);
    console.log(`│ Total Trades:    ${latest.totalTrades}${' '.repeat(62)}│`);
    console.log('└───────────────────────────────────────────────────────────────────────────┘\n');

    // Financial Metrics
    const pnl = latest.currentEquity - startSnapshot.currentEquity;
    console.log('┌─ FINANCIAL ───────────────────────────────────────────────────────────────┐');
    console.log(`│ Starting Capital:  $${startSnapshot.currentEquity.toFixed(2)}${' '.repeat(54)}│`);
    console.log(`│ Current Equity:    $${latest.currentEquity.toFixed(2)}${' '.repeat(54)}│`);
    console.log(`│ P&L:               ${pnl >= 0 ? '+' : ''}$${pnl.toFixed(2)} (${latest.returnPercent >= 0 ? '+' : ''}${latest.returnPercent.toFixed(2)}%)${' '.repeat(40)}│`);
    console.log(`│ 🍯 Honey Collected: $${Math.max(0, pnl).toFixed(2)}${' '.repeat(54)}│`);
    console.log('└───────────────────────────────────────────────────────────────────────────┘\n');

    // Mini Chart (Last 10 snapshots)
    if (this.snapshots.length >= 2) {
      console.log('┌─ EQUITY CURVE (LAST 10 SAMPLES) ─────────────────────────────────────────┐');
      const recentSnapshots = this.snapshots.slice(-10);
      const maxEquity = Math.max(...recentSnapshots.map(s => s.currentEquity));
      const minEquity = Math.min(...recentSnapshots.map(s => s.currentEquity));
      const range = maxEquity - minEquity || 1;

      for (let i = 0; i < recentSnapshots.length; i++) {
        const snap = recentSnapshots[i];
        const normalized = (snap.currentEquity - minEquity) / range;
        const barLength = Math.floor(normalized * 60);
        const bar = '█'.repeat(barLength);
        console.log(`│ ${i + 1}.  ${bar} $${snap.currentEquity.toFixed(2)}${' '.repeat(Math.max(0, 40 - bar.length))}│`);
      }
      console.log('└───────────────────────────────────────────────────────────────────────────┘\n');
    }

    // Velocity & Predictions
    if (this.snapshots.length >= 5) {
      const recent5 = this.snapshots.slice(-5);
      const timeSpan = (recent5[recent5.length - 1].timestamp - recent5[0].timestamp) / 60000;
      const tradesInSpan = recent5[recent5.length - 1].totalTrades - recent5[0].totalTrades;
      const tradesPerHour = timeSpan > 0 ? (tradesInSpan / timeSpan) * 60 : 0;
      const remainingTrades = targetTrades - latest.totalTrades;
      const estimatedMinutesRemaining = tradesPerHour > 0 ? (remainingTrades / tradesPerHour) * 60 : 0;

      console.log('┌─ VELOCITY & PREDICTIONS ──────────────────────────────────────────────────┐');
      console.log(`│ Trades/Hour:        ${tradesPerHour.toFixed(1)}${' '.repeat(56)}│`);
      console.log(`│ Est. Time to Target: ${estimatedMinutesRemaining.toFixed(0)} minutes${' '.repeat(50)}│`);
      
      if (estimatedMinutesRemaining > 0) {
        const projectedReturn = latest.returnPercent * (targetTrades / Math.max(1, latest.totalTrades));
        console.log(`│ Projected Return:    ${projectedReturn >= 0 ? '+' : ''}${projectedReturn.toFixed(1)}%${' '.repeat(52)}│`);
      }
      console.log('└───────────────────────────────────────────────────────────────────────────┘\n');
    }

    console.log(`Last Update: ${new Date(latest.timestamp).toLocaleTimeString()}`);
    console.log('Press Ctrl+C to exit monitor\n');
  }

  private getWinRateEmoji(winRate: number): string {
    if (winRate >= 0.95) return '🔥🔥🔥';
    if (winRate >= 0.85) return '🔥🔥';
    if (winRate >= 0.70) return '🔥';
    if (winRate >= 0.60) return '✓';
    return '⚠️';
  }

  async monitor() {
    console.log('Starting Mission Monitor...\n');

    setInterval(() => {
      // In a real implementation, this would read from a shared log file
      // or subscribe to mission events via IPC/WebSocket
      // For now, we simulate with mock data
      
      this.displayDashboard();
    }, 2000);  // Update every 2 seconds
  }

  addSnapshot(snapshot: MissionSnapshot) {
    this.snapshots.push(snapshot);
    
    // Keep last 1000 snapshots
    if (this.snapshots.length > 1000) {
      this.snapshots.shift();
    }
  }
}

async function main() {
  const monitor = new MissionMonitor();
  
  // Simulate some snapshots for demo
  const startTime = Date.now();
  
  // Generate mock snapshots
  for (let i = 0; i < 15; i++) {
    monitor.addSnapshot({
      timestamp: startTime + (i * 60000),
      elapsedMinutes: i * 1,
      totalTrades: Math.floor(i * 3.5),
      winners: Math.floor(i * 3.2),
      winRate: 0.85 + (Math.random() * 0.1),
      currentEquity: 1000 + (i * 15),
      returnPercent: (i * 1.5),
      phase: i < 5 ? 'PHASE 1: SUPER-AGGRESSIVE' : i < 10 ? 'PHASE 2: MULTI-SYMBOL SWARM' : 'PHASE 3: FIBONACCI TIME',
    });
  }

  await monitor.monitor();
}

main().catch(console.error);
