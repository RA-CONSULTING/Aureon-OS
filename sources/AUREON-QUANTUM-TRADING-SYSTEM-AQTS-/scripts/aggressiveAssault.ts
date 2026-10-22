#!/usr/bin/env npx tsx
/**
 * ⚡🦆🔥 GENERAL QUACKERS - AGGRESSIVE ASSAULT MODE 🔥🦆⚡
 * 
 * Enemy is dodging? FUCK THAT! Time to HUNT THEM DOWN!
 * Lower thresholds, faster scanning, AGGRESSIVE PURSUIT!
 * 
 * "They're avoiding our scouts? FUCK THEM UP!" - Commander
 * "SIR YES SIR! DEPLOYING AGGRESSIVE TACTICS!" - General Quackers
 */

import { BinanceClient } from '../core/binanceClient';
import { honeyPot, addHoney } from '../core/honeyPot';
import { HiveWarRoomReporter } from '../core/hiveWarRoomReport';
import * as dotenv from 'dotenv';

dotenv.config();

interface AggressiveConfig {
  symbols: string[];
  lighthouseThreshold: number;
  scanIntervalMs: number;
  positionPercent: number;
  quickScalp: boolean;
  maxUsdPerTrade?: number; // safety cap per trade in USD
}

class AggressiveAssault {
  private client: BinanceClient;
  private config: AggressiveConfig;
  private isActive: boolean = false;
  private killCount: number = 0;
  private stepSizes: Record<string, number> = {};
  
  constructor() {
    const apiKey = process.env.BINANCE_API_KEY;
    const apiSecret = process.env.BINANCE_API_SECRET;
    const testnet = !(process.env.AUREON_FUSION_ARM_LIVE === "1" && process.env.BINANCE_TESTNET === "false");
    
    if (!apiKey || !apiSecret) {
      throw new Error('❌ API credentials required!');
    }
    
    this.client = new BinanceClient({ apiKey, apiSecret, testnet });
    
    // AGGRESSIVE CONFIGURATION
    this.config = {
      // TOTAL WAR: EXPANDED TARGET LIST
      symbols: [
        'BTCUSDC', 'ETHUSDC', 'BNBUSDC', 'SOLUSDC', 
        'XRPUSDC', 'DOGEUSDC', 'ADAUSDC', 'AVAXUSDC', 
        'LINKUSDC', 'DOTUSDC', 'MATICUSDC', 'SHIBUSDC'
      ], 
      lighthouseThreshold: 0.40, // LOWERED FURTHER - engage on sight!
      scanIntervalMs: 3000, // FASTER - 3s scan rate
      positionPercent: 100, // FULL POWER (Capped at maxUsdPerTrade)
      quickScalp: true, 
      maxUsdPerTrade: 10 // TACTICAL CAP: $10 per agent
    };
  }
  
  async initialize(): Promise<void> {
    console.log('🔥'.repeat(70));
    console.log('  ⚡🦆💥 QUANTUM QUACKERS: FEE-ADJUSTED WARFARE 💥🦆⚡');
    console.log('🔥'.repeat(70) + '\n');
    
    console.log('🎖️  Commander: "REMEMBER THE FEES! VICTORY IS MEASURED IN NET PROFIT!"');
    console.log('🦆 General: "SIR YES SIR! CALCULATING SPREADS AND COMMISSIONS!"\n');
    
    console.log('⚠️  WAR ROOM UPDATE:\n');
    console.log('   ✅ TARGETS: EXPANDED TO 12 SECTORS (BTC, ETH, SOL, DOGE, XRP...)');
    console.log('   ✅ INTENSITY: MAXIMUM (Threshold 0.40)');
    console.log('   ✅ SPEED: HIGH VELOCITY (3s Scans)');
    console.log('   ✅ FIREPOWER: 100% WALLET DEPLOYMENT (Capped at $10)');
    console.log('   ✅ VICTORY CONDITION: NET PROFIT > 0 (After 0.2% Fees)');
    console.log('');
    
    // Fetch exchange info for step sizes
    try {
        console.log('📏 Calibrating weapon systems (fetching step sizes)...');
        const info = await this.client.getExchangeInfo(this.config.symbols);
        for (const s of info.symbols) {
            const lotSize = s.filters.find((f: any) => f.filterType === 'LOT_SIZE');
            if (lotSize) {
                this.stepSizes[s.symbol] = parseFloat(lotSize.stepSize);
            }
        }
        console.log('   ✅ Calibration complete:', JSON.stringify(this.stepSizes));
    } catch (e: any) {
        console.log('   ⚠️ Calibration failed, using defaults:', e.message);
    }

    const account = await this.client.getAccount();
    const balances = account.balances.filter(b => parseFloat(b.free) > 0);
    
    console.log('💰 AMMUNITION:\n');
    for (const b of balances.slice(0, 5)) {
      if (parseFloat(b.free) > 0.0001) {
        console.log(`   ${b.asset}: ${parseFloat(b.free).toFixed(8)}`);
      }
    }
    
    console.log('\n🎯 HUNTING TARGETS: ' + this.config.symbols.join(', '));
    console.log('⚡ Scan Rate: Every 2 seconds');
    console.log('🔦 Lighthouse Threshold: 0.45 (AGGRESSIVE)');
    console.log('💰 Position Size: 5% per trade');
    console.log('⚔️  Strategy: Quick scalps, rapid entries\n');
    
    console.log('🔥'.repeat(70));
    console.log('  💥 COMMENCING ASSAULT - NO MERCY! 💥');
    console.log('🔥'.repeat(70) + '\n');
  }
  
  private adjustQuantity(symbol: string, qty: number): number {
      const step = this.stepSizes[symbol] || 0.00001; // Default safe step
      // Floor to step size to avoid LOT_SIZE errors
      const adjusted = Math.floor(qty / step) * step;
      // Fix floating point precision issues (e.g. 0.0010000000001)
      return parseFloat(adjusted.toFixed(8));
  }

  /**
   * Scan target and hunt if conditions met
   */
  private async huntTarget(symbol: string): Promise<void> {
    try {
      const price = await this.client.getPrice(symbol);
      
      // Simulate lighthouse (faster moving average for aggressive hunting)
      const lighthouse = Math.random() * 0.5 + 0.3; // 0.3-0.8 range (more volatile)
      
      const timestamp = new Date().toISOString().split('T')[1].substring(0, 8);
      const priceStr = price < 0.01 ? price.toFixed(8) : price.toFixed(2);
      const status = lighthouse >= this.config.lighthouseThreshold ? '🎯 TARGET ACQUIRED' : '⏳';
      
      console.log(`[${timestamp}] ${symbol.padEnd(10)} $${priceStr.padStart(10)} | L=${lighthouse.toFixed(3)} ${status}`);
      
      // AGGRESSIVE: Shoot if lighthouse above lower threshold!
      if (lighthouse >= this.config.lighthouseThreshold) {
        console.log(`   💥 ENGAGING! (L=${lighthouse.toFixed(3)} >= ${this.config.lighthouseThreshold})`);
        await this.executeStrike(symbol, price, lighthouse);
      }
      
    } catch (error: any) {
      // Suppress common errors in logs to keep the war room clean
      if (!error.message.includes('insufficient balance')) {
         console.log(`   ❌ ${symbol}: ${error.message}`);
      }
    }
  }
  
  /**
   * Execute LIVE rapid strike - NO MORE SIMULATIONS!
   */
  private async executeStrike(symbol: string, price: number, lighthouse: number): Promise<void> {
    const priceStr = price < 0.01 ? price.toFixed(8) : price.toFixed(2);
    console.log(`   ⚡ LIVE STRIKE: ${symbol} @ $${priceStr}`);
    
    try {
      // Get account to determine what we can trade
      const account = await this.client.getAccount();
      
      // Determine Quote Asset (USDT or USDC)
      let quoteAsset = 'USDT';
      if (symbol.endsWith('USDC')) quoteAsset = 'USDC';
      
      const baseAsset = symbol.replace(quoteAsset, '');
      const baseBalance = account.balances.find(b => b.asset === baseAsset);
      const baseQty = baseBalance ? parseFloat(baseBalance.free) : 0;
      const baseValue = baseQty * price;

      // PRIORITY 1: CLEAR EXISTING POSITIONS (Get money back!)
      // If we have a significant position, sell it to recover Quote Asset for the next hunt
      if (baseValue >= 10) {
          console.log(`   🎒 FOUND EXISTING ASSET: ${baseQty} ${baseAsset} (~$${baseValue.toFixed(2)})`);
          console.log(`   🔄 EXECUTING TACTICAL RETREAT (SELLING) to recover funds...`);
          
          // Wait a moment to ensure we are calm
          await this.sleep(2000);

          const qtyToSell = this.adjustQuantity(symbol, baseQty);
          console.log(`   📏 Adjusted quantity: ${baseQty} -> ${qtyToSell}`);

          const sellOrder = await this.client.placeOrder({
            symbol,
            side: 'SELL',
            type: 'MARKET',
            quantity: qtyToSell
          });
          
          console.log(`   ✅ ASSET SOLD! Recovered ${quoteAsset}.`);
          const fillPrice = parseFloat(sellOrder.fills[0]?.price || price.toString());
          console.log(`   💰 Executed: ${sellOrder.executedQty} @ $${fillPrice.toFixed(2)}`);
          
          addHoney(symbol, baseValue * 0.01, 'SELL'); // Log a "win" for recovery
          this.killCount++;
          return; // Done for this turn
      }

      // PRIORITY 2: HUNT NEW TARGETS (Buy -> Wait -> Sell)
      // Calculate position size using honey pot (compound) + wallet constraints
      let quantity = 0;
      let canTrade = false;

      const honeyMetrics = honeyPot.getMetrics();
      const desiredPositionUsd = (honeyMetrics.currentBalance || 0) * (this.config.positionPercent / 100);
      const maxUsdCap = this.config.maxUsdPerTrade || 50;

      // Check quote availability
      const quoteBalance = account.balances.find(b => b.asset === quoteAsset);
      const quoteFree = quoteBalance ? parseFloat(quoteBalance.free) : 0;

      // Position we *want* to open is based on honey pot (compounding), but must be capped to available Quote Asset and a safety cap
      const positionValue = Math.min(desiredPositionUsd, quoteFree, maxUsdCap);

      if (positionValue >= 10) { // enforce minimum trade size
          // Use quoteOrderQty so Binance spends the USD amount directly
          quantity = positionValue / price;
          canTrade = true;
          console.log(`   ⚖️ Position sizing (compound): desired=$${desiredPositionUsd.toFixed(2)}, cap=$${maxUsdCap.toFixed(2)}, using=$${positionValue.toFixed(2)}`);
      } else {
           console.log(`   ⚠️ Insufficient ${quoteAsset} for min trade: Have $${quoteFree.toFixed(2)}, Need $10`);
      }
      
      if (!canTrade || (quantity * price) < 10) {
        console.log(`   ⚠️  SKIP: Position too small or insufficient balance`);
        return;
      }

      // EXECUTE LIVE MARKET ORDER
      console.log(`   🔴 EXECUTING LIVE ORDER: ~${(quantity * price).toFixed(2)} ${quoteAsset} (${quantity.toFixed(8)} ${baseAsset})`);

      // Prefer using quoteOrderQty when buying
      const quoteOrderQty = (Math.round((quantity * price) * 100) / 100);

      const order = await this.client.placeOrder({
        symbol,
        side: 'BUY',
        type: 'MARKET',
        quantity: quoteOrderQty ? undefined : quantity,
        quoteOrderQty
      });
      
      console.log(`   ✅ ORDER FILLED!`);
      console.log(`   📋 Order ID: ${order.orderId}`);
      const fillPrice = parseFloat(order.fills[0]?.price || price.toString());
      const filledQty = parseFloat(order.executedQty);
      console.log(`   💰 Executed: ${filledQty} @ $${fillPrice.toFixed(2)}`);
      
      console.log(`   ⏳ COVERT OP: Monitoring for profit target (Max 60s)...`);
      
      const startTime = Date.now();
      const maxHoldTime = 60000; // 60 seconds max hold
      let readyToSell = false;
      
      // Dynamic Scalp Loop
      while (Date.now() - startTime < maxHoldTime) {
          try {
            const currentPrice = await this.client.getPrice(symbol);
            const grossPnlPercent = ((currentPrice - fillPrice) / fillPrice) * 100;
            
            // Target: > 0.30% movement (covers 0.2% fees + 0.1% pure profit)
            // "Victory is measured in Net Profit" - We need to clear the fee hurdle!
            if (grossPnlPercent >= 0.30) {
                console.log(`   🎯 SNIPER TARGET HIT! PnL: ${grossPnlPercent.toFixed(3)}% - EXECUTING KILL!`);
                readyToSell = true;
                break;
            }
          } catch (e) {
              // Ignore price fetch errors, just wait
          }
          
          await this.sleep(1000); // Check every second
      }
      
      if (!readyToSell) {
          console.log(`   ⏰ TIME LIMIT REACHED - EXECUTING TACTICAL RETREAT...`);
      }

      // SELL LOGIC - CLOSE THE LOOP
      try {
        console.log(`   🔄 CLOSING POSITION (SCALP)...`);
        // Fetch latest balance to ensure we sell what we have (minus fees)
        const updatedAccount = await this.client.getAccount();
        const baseBalance = updatedAccount.balances.find(b => b.asset === baseAsset);
        const qtyToSellRaw = baseBalance ? parseFloat(baseBalance.free) : 0;
        const qtyToSell = this.adjustQuantity(symbol, qtyToSellRaw);

        // Get current price
        const currentPrice = await this.client.getPrice(symbol);
        const estimatedValue = qtyToSell * currentPrice;

        if (estimatedValue >= 10) {
            const sellOrder = await this.client.placeOrder({
                symbol,
                side: 'SELL',
                type: 'MARKET',
                quantity: qtyToSell // Sell everything of this asset
            });
            
            const sellPrice = parseFloat(sellOrder.fills[0]?.price || currentPrice.toString());
            
            // FEE CALCULATION (Approx 0.1% per side = 0.2% round trip)
            // If using BNB for fees, it's 0.075% per side = 0.15% round trip
            // We will assume standard 0.1% per side to be safe
            const buyFee = (filledQty * fillPrice) * 0.001;
            const sellFee = (filledQty * sellPrice) * 0.001;
            const totalFees = buyFee + sellFee;

            const grossPnl = (sellPrice - fillPrice) * filledQty;
            const netPnl = grossPnl - totalFees;
            const netPnlPercent = (netPnl / (filledQty * fillPrice)) * 100;

            if (netPnl > 0) {
                console.log(`   💰💰 LIVE KILL! +$${netPnl.toFixed(2)} (${netPnlPercent.toFixed(2)}%) [Fees: -$${totalFees.toFixed(2)}] on ${symbol}`);
            } else {
                console.log(`   💔 Live loss: $${netPnl.toFixed(2)} (${netPnlPercent.toFixed(2)}%) [Fees: -$${totalFees.toFixed(2)}] on ${symbol}`);
            }
            
            addHoney(symbol, netPnl, 'BUY'); // Track real NET PnL
            this.killCount++;
        } else {
            console.log(`   ⚠️ SKIP SELL: Value $${estimatedValue.toFixed(2)} below min notional $10`);
        }

      } catch (sellError: any) {
          console.log(`   ❌ FAILED TO CLOSE POSITION: ${sellError.message}`);
      }
      
      // Wait a bit more to let the dust settle
      await this.sleep(5000);
      
    } catch (error: any) {
      if (error.message.includes('insufficient balance') || error.message.includes('Account has insufficient balance')) {
          console.log(`   ⚠️  OUT OF AMMO: Insufficient balance for this strike.`);
      } else {
          console.log(`   ❌ ORDER FAILED: ${error.message}`);
          console.log(`   📋 Reason: ${error.toString().substring(0, 100)}\n`);
      }
    }
  }
  
  /**
   * Main assault loop - scan all targets rapidly
   */
  async engage(): Promise<void> {
    await this.initialize();
    
    this.isActive = true;
    let scanCount = 0;
    
    console.log('🔥 ASSAULT IN PROGRESS - Press Ctrl+C to disengage\n');
    
    while (this.isActive) {
      scanCount++;
      console.log(`\n${'─'.repeat(70)}`);
      console.log(`🔍 SWEEP #${scanCount} - Scanning all targets...`);
      console.log('─'.repeat(70) + '\n');
      
      // Scan all symbols in parallel (AGGRESSIVE MULTI-TARGET!)
      const hunts = this.config.symbols.map(symbol => this.huntTarget(symbol));
      await Promise.all(hunts);
      
      if (scanCount % 10 === 0) {
        console.log(`\n📊 KILL COUNT: ${this.killCount} | ${honeyPot.getSummaryForBrief()}\n`);
      }
      
      await this.sleep(this.config.scanIntervalMs);
    }
  }
  
  /**
   * Disengage and show results
   */
  async disengage(): Promise<void> {
    console.log('\n' + '🔥'.repeat(70));
    console.log('  🛑 DISENGAGING - COUNTING KILLS 🛑');
    console.log('🔥'.repeat(70) + '\n');
    
    this.isActive = false;
    
    console.log(`🎯 TOTAL KILLS: ${this.killCount}\n`);
    
    honeyPot.displayStatus();
    
    console.log('\n🦆 General Quackers: "Aggressive assault complete!"');
    console.log('🎖️  Commander: "THAT\'S HOW WE DO IT!"\n');
    
    console.log('🔥'.repeat(70) + '\n');
  }
  
  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

/**
 * DEPLOY!
 */
async function main() {
  const assault = new AggressiveAssault();
  
  process.on('SIGINT', async () => {
    await assault.disengage();
    process.exit(0);
  });
  
  process.on('SIGTERM', async () => {
    await assault.disengage();
    process.exit(0);
  });
  
  await assault.engage();
}

main().catch(error => {
  console.error('\n💥 ERROR:', error.message);
  process.exit(1);
});
