#!/usr/bin/env ts-node
/**
 * Demo: War Room Brief Generator
 * Watch General Quackers brief the LION scouts! 🦆🦁
 */

import * as fs from 'fs';
import * as path from 'path';
import { HiveWarRoomReporter, WarRoomBrief } from '../core/hiveWarRoomReport.js';

// Create sample data for demonstration
function createSampleData() {
  const date = new Date().toISOString().split('T')[0];
  
  // Create logs directory
  const logsDir = './logs';
  const metricsDir = './metrics';
  
  if (!fs.existsSync(logsDir)) fs.mkdirSync(logsDir, { recursive: true });
  if (!fs.existsSync(metricsDir)) fs.mkdirSync(metricsDir, { recursive: true });
  
  // Sample trades (crystalline order scenario)
  const trades = [
    { symbol: 'BTCUSDT', side: 'BUY', pnl: 125.50, timestamp: '2025-11-23T08:30:00Z' },
    { symbol: 'ETHUSDT', side: 'BUY', pnl: 78.25, timestamp: '2025-11-23T09:15:00Z' },
    { symbol: 'BTCUSDT', side: 'SELL', pnl: -35.00, timestamp: '2025-11-23T10:00:00Z' },
    { symbol: 'SOLUSDT', side: 'BUY', pnl: 92.75, timestamp: '2025-11-23T11:30:00Z' },
    { symbol: 'ETHUSDT', side: 'BUY', pnl: 156.80, timestamp: '2025-11-23T13:00:00Z' },
    { symbol: 'BNBUSDT', side: 'BUY', pnl: 45.60, timestamp: '2025-11-23T14:20:00Z' },
    { symbol: 'BTCUSDT', side: 'BUY', pnl: 210.30, timestamp: '2025-11-23T15:45:00Z' },
  ];
  
  // Sample lighthouse data (high coherence scenario)
  const lighthouseReadings = [];
  for (let i = 0; i < 24; i++) {
    const hour = i.toString().padStart(2, '0');
    const intensity = 0.6 + (Math.random() * 0.3); // High coherence
    const entropy = 0.3 - (i * 0.005); // Falling entropy
    lighthouseReadings.push({
      timestamp: `2025-11-23T${hour}:00:00Z`,
      intensity: intensity,
      entropy: Math.max(0.1, entropy)
    });
  }
  
  // Sample engine logs
  const engineEvents = [
    { type: 'signal_generated', timestamp: '2025-11-23T08:25:00Z' },
    { type: 'signal_executed', timestamp: '2025-11-23T08:30:00Z' },
    { type: 'signal_generated', timestamp: '2025-11-23T09:10:00Z' },
    { type: 'signal_executed', timestamp: '2025-11-23T09:15:00Z' },
    { type: 'signal_generated', timestamp: '2025-11-23T09:55:00Z' },
    { type: 'signal_executed', timestamp: '2025-11-23T10:00:00Z' },
    { type: 'signal_generated', timestamp: '2025-11-23T11:25:00Z' },
    { type: 'signal_executed', timestamp: '2025-11-23T11:30:00Z' },
    { type: 'signal_generated', timestamp: '2025-11-23T12:55:00Z' },
    { type: 'signal_executed', timestamp: '2025-11-23T13:00:00Z' },
    { type: 'signal_generated', timestamp: '2025-11-23T14:15:00Z' },
    { type: 'signal_executed', timestamp: '2025-11-23T14:20:00Z' },
    { type: 'signal_generated', timestamp: '2025-11-23T15:40:00Z' },
    { type: 'signal_executed', timestamp: '2025-11-23T15:45:00Z' },
  ];
  
  // Write sample data
  fs.writeFileSync(
    path.join(logsDir, `trades_${date}.json`),
    JSON.stringify(trades, null, 2)
  );
  
  fs.writeFileSync(
    path.join(metricsDir, `lighthouse_${date}.json`),
    JSON.stringify({ readings: lighthouseReadings }, null, 2)
  );
  
  fs.writeFileSync(
    path.join(logsDir, `engine_${date}.json`),
    JSON.stringify({ events: engineEvents }, null, 2)
  );
  
  console.log('✅ Sample data created for', date);
}

async function main() {
  console.log('\n🦆⚡ GENERAL QUACKERS REPORTING FOR DUTY ⚡🦆\n');
  console.log('Generating War Room Brief...\n');
  
  // Create sample data
  createSampleData();
  
  // Generate the brief
  const reporter = new HiveWarRoomReporter();
  const brief = await reporter.generateBrief(
    new Date(),
    'Commander',
    'AUREON-ALPHA'
  );
  
  // Save to file
  const reportPath = await reporter.saveBrief(brief);
  console.log(`\n📄 Brief saved to: ${reportPath}\n`);
  
  // Display the formatted text
  const formattedBrief = reporter.formatBriefAsText(brief);
  console.log(formattedBrief);
  
  // Highlight the LION orders
  console.log('\n\n🎯 KEY TAKEAWAY FOR LION SCOUTS:\n');
  console.log(brief.lionReconOrders.tacticalDirective);
  console.log('\nTarget pairs:', brief.lionReconOrders.targetPairs.join(', '));
  console.log('Scan frequency:', brief.lionReconOrders.scanFrequency.toUpperCase());
  console.log('Position sizing:', brief.lionReconOrders.positionSize.toUpperCase());
  
  console.log('\n\n🦆 General Quackers out! 🦆\n');
}

main().catch(console.error);
