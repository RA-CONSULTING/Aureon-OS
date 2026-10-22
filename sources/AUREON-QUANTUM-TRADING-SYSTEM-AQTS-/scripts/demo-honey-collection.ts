#!/usr/bin/env npx tsx
/**
 * 🍯 HONEY COLLECTION DEMO 🍯
 * 
 * Watch the honey pot fill up from successful LION hunts!
 * Milestones, celebrations, and sweet gains!
 */

import { honeyPot, addHoney, showHoney } from '../core/honeyPot';

function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function simulateHunt() {
  console.log('\n' + '═'.repeat(70));
  console.log('  🦁🍯 LION HUNTS & HONEY COLLECTION SIMULATOR 🍯🦆');
  console.log('═'.repeat(70) + '\n');
  
  console.log('🦁 The LION pride begins their hunt...\n');
  await sleep(1000);
  
  // Reset for demo
  honeyPot.reset(10000);
  
  // Simulate a series of trades
  const hunts = [
    { symbol: 'BTCUSDT', pnl: 125.50, desc: 'Strong breakout, trending move' },
    { symbol: 'ETHUSDT', pnl: 78.25, desc: 'Pullback entry, clean execution' },
    { symbol: 'BTCUSDT', pnl: -35.00, desc: 'Stopped out, false breakout' },
    { symbol: 'SOLUSDT', pnl: 92.75, desc: 'Volume spike, momentum trade' },
    { symbol: 'ETHUSDT', pnl: 156.80, desc: 'Range breakout, perfect entry' },
    { symbol: 'BNBUSDT', pnl: 45.60, desc: 'Quick scalp, support bounce' },
    { symbol: 'BTCUSDT', pnl: 210.30, desc: 'Major trend continuation' },
    { symbol: 'ADAUSDT', pnl: 67.40, desc: 'Volatility play, nice exit' },
    { symbol: 'ETHUSDT', pnl: -28.50, desc: 'Early entry, tight stop hit' },
    { symbol: 'SOLUSDT', pnl: 189.20, desc: 'Coherence spike, big move' },
  ];
  
  for (let i = 0; i < hunts.length; i++) {
    const hunt = hunts[i];
    console.log(`\n${'─'.repeat(70)}`);
    console.log(`🦁 HUNT #${i + 1}: ${hunt.symbol}`);
    console.log(`   Strategy: ${hunt.desc}`);
    console.log(`   Result: ${hunt.pnl >= 0 ? '✅' : '❌'} ${hunt.pnl >= 0 ? '+' : ''}$${hunt.pnl.toFixed(2)}`);
    
    await sleep(800);
    
    // Add to honey pot
    addHoney(hunt.symbol, hunt.pnl);
    
    await sleep(1200);
  }
  
  // Show final status
  console.log('\n' + '═'.repeat(70));
  console.log('  🎯 HUNT SESSION COMPLETE');
  console.log('═'.repeat(70));
  
  await sleep(500);
  
  showHoney();
  
  // Show what milestones we would hit next
  const metrics = honeyPot.getMetrics();
  console.log('\n📊 PROGRESS TO NEXT MILESTONES:\n');
  
  const nextBalance = 11000;
  if (metrics.currentBalance < nextBalance) {
    const needed = nextBalance - metrics.currentBalance;
    console.log(`   🎯 Next milestone: $${nextBalance} balance`);
    console.log(`   💰 Need: $${needed.toFixed(2)} more honey`);
  }
  
  const nextStreak = 5;
  if (metrics.currentStreak > 0 && metrics.currentStreak < nextStreak) {
    const needed = nextStreak - metrics.currentStreak;
    console.log(`   🔥 Next milestone: ${nextStreak}-trade winning streak`);
    console.log(`   🎯 Need: ${needed} more winning trades`);
  }
  
  const nextTrades = 100;
  if (metrics.totalTrades < nextTrades) {
    const needed = nextTrades - metrics.totalTrades;
    console.log(`   💯 Next milestone: ${nextTrades} total trades`);
    console.log(`   📈 Need: ${needed} more trades`);
  }
  
  console.log('\n' + '═'.repeat(70));
  console.log('  🦆 "The honey flows when the pride hunts well!" - General Quackers');
  console.log('═'.repeat(70) + '\n');
  
  // Now show War Room Brief with honey
  console.log('📡 Generating War Room Brief with Honey Pot status...\n');
  await sleep(1000);
  
  const { HiveWarRoomReporter } = await import('../core/hiveWarRoomReport');
  const reporter = new HiveWarRoomReporter();
  
  const brief = await reporter.generateBrief(
    new Date(),
    'Commander',
    'AUREON-LION'
  );
  
  console.log(reporter.formatBriefAsText(brief));
}

simulateHunt().catch(console.error);
