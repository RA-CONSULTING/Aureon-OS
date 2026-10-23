#!/usr/bin/env npx tsx
/**
 * DEMO: General Quackers Commands the LION Pride
 * 
 * Watch the full command chain in action:
 * 1. General analyzes the field
 * 2. Issues tactical orders
 * 3. LION scouts receive and acknowledge
 * 4. Hunt strategy adapts automatically
 */

import { lionCommand } from '../core/lionCommandCenter';

async function main() {
  console.log('\n');
  console.log('═'.repeat(70));
  console.log('  🦆⚡ GENERAL QUACKERS & THE LION PRIDE ⚡🦁');
  console.log('═'.repeat(70));
  console.log('\n');

  // Step 1: General issues orders
  console.log('📡 STEP 1: General Quackers analyzes field conditions...\n');
  await new Promise(resolve => setTimeout(resolve, 1000));
  
  const orders = await lionCommand.fetchLatestOrders();
  
  console.log('\n' + '─'.repeat(70) + '\n');
  
  // Step 2: Command center translates to config
  console.log('📡 STEP 2: LION Command Center translating orders...\n');
  await new Promise(resolve => setTimeout(resolve, 500));
  
  const config = lionCommand.translateOrdersToConfig(orders);
  
  console.log('✅ TRANSLATED HUNTING CONFIGURATION:\n');
  console.log('   📍 Target Pairs:');
  config.targetPairs?.forEach(pair => {
    console.log(`      • ${pair}`);
  });
  console.log(`\n   ⚡ Scan Interval: ${(config.scanIntervalMs || 5000) / 1000}s`);
  console.log(`   🎯 Min Lighthouse: ${config.minLighthouseIntensity?.toFixed(2)}`);
  console.log(`   💪 Aggression Level: ${config.aggressionLevel?.toUpperCase()}`);
  console.log(`   💰 Position Size: ${((config.positionSizeMultiplier || 1.0) * 100).toFixed(0)}%`);
  console.log(`   🛡️  Stop Loss Width: ${((config.stopLossMultiplier || 1.0) * 100).toFixed(0)}%`);
  console.log(`   🔢 Max Concurrent Trades: ${config.maxConcurrentTrades}`);
  
  console.log('\n' + '─'.repeat(70) + '\n');
  
  // Step 3: Demonstrate signal validation
  console.log('📡 STEP 3: Signal validation example...\n');
  await new Promise(resolve => setTimeout(resolve, 500));
  
  const testSignals = [
    { lighthouse: 0.75, condition: 'strong breakout with volume' },
    { lighthouse: 0.45, condition: 'trending market' },
    { lighthouse: 0.82, condition: 'low volume breakout' },
    { lighthouse: 0.65, condition: 'range-bound chop' },
  ];
  
  console.log('🔍 Testing potential signals against General\'s orders:\n');
  
  for (const signal of testSignals) {
    const result = lionCommand.shouldTakeSignal(signal.lighthouse, signal.condition);
    const status = result.allowed ? '✅ TAKE' : '🚫 SKIP';
    console.log(`   ${status} | L=${signal.lighthouse.toFixed(2)} | ${signal.condition}`);
    if (!result.allowed) {
      console.log(`        └─ Reason: ${result.reason}`);
    }
  }
  
  console.log('\n' + '─'.repeat(70) + '\n');
  
  // Step 4: Summary
  console.log('📡 STEP 4: Mission ready!\n');
  await new Promise(resolve => setTimeout(resolve, 500));
  
  console.log('✅ COMMAND CHAIN COMPLETE:\n');
  console.log('   1. 🦆 General Quackers → Analyzes field, issues orders');
  console.log('   2. 📡 Command Center → Translates to hunting parameters');
  console.log('   3. 🦁 LION Scouts → Follow directives, validate signals');
  console.log('   4. 💰 Trades Execute → Only when conditions match orders');
  console.log('   5. 📊 Results Report → Back to General for next brief\n');
  
  console.log('═'.repeat(70));
  console.log('  🎯 THE PRIDE HUNTS AS ONE UNDER THE GENERAL\'S COMMAND');
  console.log('═'.repeat(70));
  console.log('\n');
  
  console.log('💡 TO RUN ENHANCED LION HUNT:\n');
  console.log('   npx tsx scripts/lionHuntEnhanced.ts\n');
  console.log('   (Will automatically fetch and follow General\'s orders)\n');
  
  console.log('🦆 General Quackers out! 🦆\n');
}

main().catch(console.error);
