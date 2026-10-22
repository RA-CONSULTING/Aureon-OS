#!/usr/bin/env tsx
/**
 * A SONG OF SPACE AND TIME
 * 
 * 🦆 Quantum Quackers conducts the symphony of markets
 * Where five systems harmonize across the fabric of reality
 * Each note a trade, each chord a compounding moment
 * The duck weaves chaos into coherence, entropy into profit
 * 
 * "He's a sick duck. He fucking loves it."
 */
import 'dotenv/config';
import { BinanceClient } from '../core/binanceClient';
import { loadAccountsFromJson } from './utils/accountLoader';

// System definitions (same as simulation)
interface TradingSystem {
  name: string;
  winRateTarget: number;  // Target win rate we're aiming for
  posBase: number;
  winPct: number;
  lossPct: number;
}

const SYSTEMS: TradingSystem[] = [
  { name: 'LION', winRateTarget: 0.78, posBase: 0.75, winPct: 0.006, lossPct: 0.005 },
  { name: 'HIVE', winRateTarget: 0.82, posBase: 0.70, winPct: 0.005, lossPct: 0.005 },
  { name: 'LIGHTHOUSE', winRateTarget: 0.85, posBase: 0.80, winPct: 0.0055, lossPct: 0.0045 },
  { name: 'QUANTUM', winRateTarget: 0.80, posBase: 0.72, winPct: 0.007, lossPct: 0.006 },
  { name: 'SENTINEL', winRateTarget: 0.76, posBase: 0.68, winPct: 0.0065, lossPct: 0.0055 }
];

interface HarmonicState {
  systemWeights: Map<string, number>;
  recentPerformance: Map<string, number[]>;
  equity: number;
  startEquity: number;
  trades: number;
  systemStats: Map<string, { trades: number; wins: number; pnl: number }>;
}

function initializeState(startEquity: number): HarmonicState {
  const weights = new Map<string, number>();
  const equalWeight = 1 / SYSTEMS.length;
  SYSTEMS.forEach(sys => weights.set(sys.name, equalWeight));
  
  return {
    systemWeights: weights,
    recentPerformance: new Map(SYSTEMS.map(s => [s.name, []])),
    equity: startEquity,
    startEquity,
    trades: 0,
    systemStats: new Map(SYSTEMS.map(s => [s.name, { trades: 0, wins: 0, pnl: 0 }]))
  };
}

function updateWeights(state: HarmonicState, lookbackWindow: number, adaptSpeed: number, minWeight: number): void {
  const scores = new Map<string, number>();
  
  SYSTEMS.forEach(sys => {
    const recent = state.recentPerformance.get(sys.name) || [];
    if (recent.length === 0) {
      scores.set(sys.name, 0.5); // neutral
    } else {
      const winRate = recent.reduce((sum, r) => sum + r, 0) / recent.length;
      scores.set(sys.name, winRate);
    }
  });
  
  // Softmax allocation
  const expScores = Array.from(scores.entries()).map(([name, score]) => ({
    name,
    exp: Math.exp(score * 5)
  }));
  const sumExp = expScores.reduce((sum, e) => sum + e.exp, 0);
  
  const newWeights = new Map<string, number>();
  expScores.forEach(({ name, exp }) => {
    const rawWeight = exp / sumExp;
    const current = state.systemWeights.get(name)!;
    const smoothed = current * (1 - adaptSpeed) + rawWeight * adaptSpeed;
    newWeights.set(name, Math.max(minWeight, smoothed));
  });
  
  // Normalize
  const total = Array.from(newWeights.values()).reduce((sum, w) => sum + w, 0);
  newWeights.forEach((w, name) => state.systemWeights.set(name, w / total));
}

function selectSystem(weights: Map<string, number>): TradingSystem {
  const rand = Math.random();
  let cumulative = 0;
  for (const sys of SYSTEMS) {
    cumulative += weights.get(sys.name)!;
    if (rand <= cumulative) return sys;
  }
  return SYSTEMS[SYSTEMS.length - 1];
}

async function executeTrade(
  client: BinanceClient,
  symbol: string,
  system: TradingSystem,
  state: HarmonicState
): Promise<{ success: boolean; pnl: number }> {
  try {
    // Get current price
    const price = await client.getPrice(symbol);
    
    // FULL COMPOUND MODE - use entire system risk allocation every trade
    let positionValue = state.equity * system.posBase;
    let quantity = positionValue / price;
    
    // Get symbol filters (LOT_SIZE, MIN_NOTIONAL) and adjust / scale
    let adjustedQty = quantity;
    let minNotional: number | undefined;
    let stepSize: number | undefined;
    try {
      const exchangeInfo = await client.getExchangeInfo();
      const symbolInfo = exchangeInfo.symbols?.find((s: any) => s.symbol === symbol);
      if (symbolInfo && Array.isArray(symbolInfo.filters)) {
        const lotSizeFilter = symbolInfo.filters.find((f: any) => f.filterType === 'LOT_SIZE');
        const notionalFilter = symbolInfo.filters.find((f: any) => f.filterType === 'MIN_NOTIONAL' || f.filterType === 'NOTIONAL');
        if (notionalFilter) {
          minNotional = Number(notionalFilter.minNotional || notionalFilter.notional || notionalFilter.minValue || 0);
        }
        if (lotSizeFilter) {
          const minQty = Number(lotSizeFilter.minQty || 0);
          stepSize = Number(lotSizeFilter.stepSize || 0);
          if (stepSize > 0) {
            adjustedQty = Math.floor(adjustedQty / stepSize) * stepSize;
            // Sanitize precision immediately after rounding
            const stepDecimals = stepSize.toString().split('.')[1]?.length || 0;
            adjustedQty = Number(adjustedQty.toFixed(stepDecimals));
          }
          if (adjustedQty < minQty) {
            const riskCapQty = (state.equity * system.posBase) / price;
            if (minQty <= riskCapQty) {
              adjustedQty = minQty;
              console.log(`  ↗️ Raised quantity to LOT_SIZE minimum ${minQty}`);
            } else {
              console.log(`  ⚠️  Cannot meet LOT_SIZE minQty ${minQty} within risk cap, skipping trade`);
              return { success: false, pnl: 0 };
            }
          }
        }
      }
    } catch (filterError:any) {
      console.log(`  ⚠️  Filter fetch failed (${filterError.message}), proceeding without adjustments`);
    }
    // After initial adjustment compute notional and scale if below minNotional
    let actualPositionValue = adjustedQty * price;
    if (minNotional && actualPositionValue < minNotional) {
      const maxPositionValue = state.equity * system.posBase;
      if (minNotional > maxPositionValue) {
        console.log(`  ⚠️  Min notional $${minNotional.toFixed(2)} exceeds risk cap $${maxPositionValue.toFixed(2)} — skipping trade`);
        return { success: false, pnl: 0 };
      }
      // Scale up quantity to meet minNotional (already within risk cap check above)
      adjustedQty = minNotional / price;
      if (stepSize && stepSize > 0) {
        adjustedQty = Math.ceil(adjustedQty / stepSize) * stepSize;
        // Sanitize precision immediately
        const stepDecimals = stepSize.toString().split('.')[1]?.length || 0;
        adjustedQty = Number(adjustedQty.toFixed(stepDecimals));
      }
      actualPositionValue = adjustedQty * price;
      console.log(`  ↗️ Scaled to meet minNotional $${minNotional.toFixed(2)} (notional $${actualPositionValue.toFixed(2)})`);
    }
    console.log(`  ${system.name}: ${symbol} @ ${price.toFixed(4)} | Qty: ${adjustedQty.toFixed(6)} (~$${actualPositionValue.toFixed(2)})${minNotional ? ` | minNotional=$${minNotional.toFixed(2)}`:''}`);
    
    // 🔴 MAKER ORDER STRATEGY 🔴
    console.log(`  🎯 PLACING MAKER LIMIT BUY...`);
    
    // Get order book for bid/ask
    const orderBook = await client.getOrderBook(symbol, 5);
    const bestBid = Number(orderBook.bids[0][0]);
    const bestAsk = Number(orderBook.asks[0][0]);
    const spread = bestAsk - bestBid;
    
    // Get PRICE_FILTER for limit order precision
    let tickSize: number | undefined;
    let minPrice: number | undefined;
    let maxPrice: number | undefined;
    try {
      const exInfo = await client.getExchangeInfo([symbol]);
      const symInfo = exInfo.symbols?.find((s: any) => s.symbol === symbol);
      if (symInfo && Array.isArray(symInfo.filters)) {
        const priceFilter = symInfo.filters.find((f: any) => f.filterType === 'PRICE_FILTER');
        if (priceFilter) {
          tickSize = Number(priceFilter.tickSize || 0);
          minPrice = Number(priceFilter.minPrice || 0);
          maxPrice = Number(priceFilter.maxPrice || 0);
        }
      }
    } catch (e) {
      console.log(`  ⚠️  Failed to fetch PRICE_FILTER, using raw price`);
    }
    
    // Place limit buy at best bid (or slightly better) to get maker rebate
    let buyPrice = bestBid + spread * 0.1; // 10% into spread for faster fill
    
    // Round to tickSize precision
    if (tickSize && tickSize > 0) {
      buyPrice = Math.round(buyPrice / tickSize) * tickSize;
      const tickDecimals = tickSize.toString().split('.')[1]?.length || 0;
      buyPrice = Number(buyPrice.toFixed(tickDecimals));
    }
    
    const buyOrder = await client.placeOrder({
      symbol,
      side: 'BUY',
      type: 'LIMIT',
      quantity: adjustedQty,
      price: buyPrice,
      timeInForce: 'GTC'
    });
    
    // Wait for fill with timeout (max 10s for maker order)
    let buyFillPrice = 0;
    let filled = false;
    const maxWait = 10000; // 10s timeout for buy fill
    const startWait = Date.now();
    
    while (!filled && (Date.now() - startWait) < maxWait) {
      await new Promise(resolve => setTimeout(resolve, 500));
      const orderStatus = await client.getOrder(symbol, buyOrder.orderId);
      if (orderStatus.status === 'FILLED') {
        filled = true;
        if (orderStatus.fills && orderStatus.fills.length) {
          const totalQty = orderStatus.fills.reduce((s, f) => s + Number(f.qty), 0);
          const weighted = orderStatus.fills.reduce((s, f) => s + Number(f.price) * Number(f.qty), 0);
          buyFillPrice = weighted / (totalQty || 1);
        } else {
          buyFillPrice = Number(orderStatus.price) || buyPrice;
        }
      }
    }
    
    if (!filled) {
      // Cancel unfilled order and fallback to market
      console.log(`  ⚠️  Maker buy timed out, canceling and using market order`);
      try {
        await client.cancelOrder(symbol, buyOrder.orderId);
      } catch (e) {}
      
      const marketBuy = await client.placeOrder({
        symbol,
        side: 'BUY',
        type: 'MARKET',
        quantity: adjustedQty
      });
      
      if (marketBuy.fills && marketBuy.fills.length) {
        const totalQty = marketBuy.fills.reduce((s, f) => s + Number(f.qty), 0);
        const weighted = marketBuy.fills.reduce((s, f) => s + Number(f.price) * Number(f.qty), 0);
        buyFillPrice = weighted / (totalQty || 1);
      } else {
        buyFillPrice = Number(marketBuy.price) || price;
      }
    }
    
    console.log(`  ✅ BUY ${filled ? 'MAKER' : 'TAKER'}: ${buyOrder.orderId} @ ${buyFillPrice.toFixed(4)}`);
    
    // ADAPTIVE POLLING - monitor price every 100ms up to 60s
    console.log(`  🔄 Monitoring position (target: +${(system.winPct*100).toFixed(2)}%, stop: -${(system.lossPct*100).toFixed(2)}%)...`);
    const entryTime = Date.now();
    const maxHoldMs = 60000; // 60s max hold
    let currentPrice = buyFillPrice;
    let priceChange = 0;
    let thresholdEvent: 'TARGET' | 'STOP' | 'TIME' = 'TIME';
    
    while ((Date.now() - entryTime) < maxHoldMs) {
      await new Promise(resolve => setTimeout(resolve, 100)); // 100ms polling
      
      currentPrice = await client.getPrice(symbol);
      priceChange = (currentPrice - buyFillPrice) / buyFillPrice;
    
      // Check exit conditions
      if (priceChange >= system.winPct) {
        thresholdEvent = 'TARGET';
        console.log(`  🎯 Target hit at +${(priceChange * 100).toFixed(3)}% after ${((Date.now() - entryTime)/1000).toFixed(1)}s`);
        break;
      } else if (priceChange <= -system.lossPct) {
        thresholdEvent = 'STOP';
        console.log(`  🛑 Stop hit at ${(priceChange * 100).toFixed(3)}% after ${((Date.now() - entryTime)/1000).toFixed(1)}s`);
        break;
      }
    }
    
    if (thresholdEvent === 'TIME') {
      console.log(`  ⏱️ Time exit at ${(priceChange * 100).toFixed(3)}% after ${((Date.now() - entryTime)/1000).toFixed(1)}s`);
    }
    
    // Execute MARKET sell immediately at current price
    console.log(`  🔥 SELLING at market: $${currentPrice.toFixed(2)} (${thresholdEvent})`);
    
    const sellOrder = await client.placeOrder({
      symbol,
      side: 'SELL',
      type: 'MARKET',
      quantity: adjustedQty
    });
    
    let sellFillPrice = 0;
    if (sellOrder.fills && sellOrder.fills.length) {
      const totalQty = sellOrder.fills.reduce((s, f) => s + Number(f.qty), 0);
      const weighted = sellOrder.fills.reduce((s, f) => s + Number(f.price) * Number(f.qty), 0);
      sellFillPrice = weighted / (totalQty || 1);
    } else {
      sellFillPrice = Number(sellOrder.price) || currentPrice;
    }
    
    console.log(`  ✅ SELL TAKER: ${sellOrder.orderId} @ ${sellFillPrice.toFixed(4)}`);
    
    // Calculate actual PnL (gross)
    const grossPnL = (sellFillPrice - buyFillPrice) * adjustedQty;

    // Real fee calculation from fills with maker/taker tracking
    let commissionTotalUSDC = 0;
    let makerFills = 0;
    let takerFills = 0;
    let makerFeeUSDC = 0;
    let takerFeeUSDC = 0;
    let bnbUsed = false;
    let bnbCommissionTotal = 0;
    
    const accumulateCommission = async (order: any, side: 'BUY' | 'SELL') => {
      if (!order.fills) return;
      for (const f of order.fills) {
        const commission = Number(f.commission || 0);
        const asset = f.commissionAsset;
        const isMaker = f.maker === true; // Binance fill includes `maker` boolean
        
        if (isMaker) {
          makerFills++;
        } else {
          takerFills++;
        }
        
        if (commission === 0) continue;
        
        let feeInUSDC = 0;
        
        if (asset === 'USDC') {
          feeInUSDC = commission;
        } else if (asset === 'USDT') {
          feeInUSDC = commission; // Treat as parity
        } else if (asset === 'BNB') {
          bnbUsed = true;
          bnbCommissionTotal += commission;
          try {
            const bnbPrice = await client.getPrice('BNBUSDC');
            feeInUSDC = commission * bnbPrice;
          } catch {
            // Fallback: approximate as 10% of typical USDC fee (since BNB gives 25% discount)
            const notional = Number(f.qty) * Number(f.price);
            feeInUSDC = notional * 0.001 * 0.75; // Assume BNB discount applied
          }
        } else {
          // Other asset: treat as stable approximation
          feeInUSDC = commission;
        }
        
        if (isMaker) {
          makerFeeUSDC += feeInUSDC;
        } else {
          takerFeeUSDC += feeInUSDC;
        }
        
        commissionTotalUSDC += feeInUSDC;
      }
    };

    await accumulateCommission(buyOrder, 'BUY');
    await accumulateCommission(sellOrder, 'SELL');

    // If commissions not populated, fallback to estimate
    let fallbackUsed = false;
    if (commissionTotalUSDC === 0) {
      const notional = adjustedQty * ((buyFillPrice + sellFillPrice) / 2);
      commissionTotalUSDC = notional * 0.001 * 2; // Assume taker on both sides
      takerFeeUSDC = commissionTotalUSDC;
      takerFills = 2;
      fallbackUsed = true;
    }

    const netPnL = grossPnL - commissionTotalUSDC;
    const success = netPnL > 0;
    
    // Calculate effective fee rate
    const totalNotional = adjustedQty * (buyFillPrice + sellFillPrice);
    const effectiveFeeRate = totalNotional > 0 ? (commissionTotalUSDC / totalNotional) * 100 : 0;
    
    // BNB optimization alert
    let bnbAlert = '';
    if (!bnbUsed && !fallbackUsed) {
      const potentialSavings = commissionTotalUSDC * 0.25; // 25% discount with BNB
      bnbAlert = `\n  💡 BNB FEE TIP: Not using BNB for fees! Could save ~$${potentialSavings.toFixed(4)} (25% discount) per trade`;
    } else if (bnbUsed) {
      bnbAlert = `\n  ✨ BNB discount active (${bnbCommissionTotal.toFixed(6)} BNB used)`;
    }

    console.log(`  💰 GrossPnL: $${grossPnL.toFixed(6)} | Fees: $${commissionTotalUSDC.toFixed(6)} (${effectiveFeeRate.toFixed(3)}%) | NetPnL: $${netPnL.toFixed(6)}`);
    console.log(`  📊 Maker: ${makerFills} fills ($${makerFeeUSDC.toFixed(6)}) | Taker: ${takerFills} fills ($${takerFeeUSDC.toFixed(6)}) | Event=${thresholdEvent}${bnbAlert}`);

    return { success, pnl: netPnL };
    
  } catch (error: any) {
    console.error(`  ❌ Trade failed:`, error.message);
    return { success: false, pnl: 0 };
  }
}

async function main() {
  const testnet = !(process.env.AUREON_FUSION_ARM_LIVE === "1" && process.env.BINANCE_TESTNET === "false");
  const bullets = Number(process.env.BULLETS ?? 50);
  const lookbackWindow = Number(process.env.LOOKBACK_WINDOW ?? 10);
  const minWeight = Number(process.env.MIN_WEIGHT ?? 0.10);
  const adaptSpeed = Number(process.env.ADAPT_SPEED ?? 0.3);
  const symbol = process.env.SYMBOL || 'BTCUSDT';
  
  console.log(`\n🎵 A SONG OF SPACE AND TIME 🎵`);
  console.log(`🦆 Quantum Quackers conducts the ${testnet ? 'TESTNET' : '🔴 MAINNET 🔴'} Symphony 🦆`);
  console.log(`"Where five harmonies dance through the market's rhythm"\n`);
  
  if (!testnet) {
    console.log(`\n🔴🔴🔴 MAINNET MODE - REAL MONEY 🔴🔴🔴\n`);
  }
  
  // Use .env credentials (the working ones from check_balances)
  const apiKey = process.env.BINANCE_API_KEY;
  const apiSecret = process.env.BINANCE_API_SECRET;
  
  if (!apiKey || !apiSecret) {
    console.error('❌ BINANCE_API_KEY and BINANCE_API_SECRET must be set in .env');
    process.exit(1);
  }
  
  console.log(`Using credentials from .env`);
  const client = new BinanceClient({
    apiKey,
    apiSecret,
    testnet
  });
  
  // Get starting balance - CONSOLIDATE ALL STABLES INTO ONE POT
  const account = await client.getAccount();
  const usdcBalance = account.balances.find(b => b.asset === 'USDC');
  const ldUsdcBalance = account.balances.find(b => b.asset === 'LDUSDC');
  const usdtBalance = account.balances.find(b => b.asset === 'USDT');
  const fdusdBalance = account.balances.find(b => b.asset === 'FDUSD');
  
  // Sum ALL stable assets - the full pot (LDUSDC excluded as it's locked lending)
  const startEquity = 
    Number(usdcBalance?.free || 0) + 
    Number(usdtBalance?.free || 0) +
    Number(fdusdBalance?.free || 0);
  
  const ldUsdcLocked = Number(ldUsdcBalance?.free || 0);
  
  if (startEquity < 5) {
    console.error(`❌ Insufficient balance: $${startEquity}`);
    if (testnet) {
      console.error(`Visit https://testnet.binance.vision/ to get testnet funds`);
    }
    process.exit(1);
  }
  
  console.log(`🏦 FULL POT ACTIVATED: $${startEquity.toFixed(2)} (TRADABLE STABLES)`);
  console.log(`   USDC: $${Number(usdcBalance?.free || 0).toFixed(2)} | USDT: $${Number(usdtBalance?.free || 0).toFixed(2)}${fdusdBalance ? ` | FDUSD: $${Number(fdusdBalance.free).toFixed(2)}` : ''}`);
  if (ldUsdcLocked > 0) {
    console.log(`   ⚠️  LDUSDC: $${ldUsdcLocked.toFixed(2)} (locked in lending, not tradable)`);
  }
  console.log(`Bullets: ${bullets} | Symbol: ${symbol}\n`);

  // Multi-coin rotation pool
  const COIN_POOL = [
    'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'ADAUSDT',
    'XRPUSDT', 'DOGEUSDT', 'DOTUSDT', 'MATICUSDT', 'LTCUSDT',
    'AVAXUSDT', 'LINKUSDT', 'ATOMUSDT', 'UNIUSDT', 'ETCUSDT'
  ];
  
  const multiCoin = process.env.MULTI_COIN !== 'false'; // Default ON
  
  // Auto-adjust symbol to match available quote asset (prefer largest balance)
  let tradeSymbol = symbol;
  const quoteBalances = [
    { asset: 'USDC', balance: Number(usdcBalance?.free || 0) },
    { asset: 'USDT', balance: Number(usdtBalance?.free || 0) },
    { asset: 'FDUSD', balance: Number(fdusdBalance?.free || 0) }
  ].sort((a, b) => b.balance - a.balance);
  
  const dominantQuote = quoteBalances[0].asset;
  
  async function selectBestCoin(): Promise<string> {
    if (!multiCoin) {
      // Single symbol mode - just adjust quote asset
      if (!symbol.endsWith(dominantQuote) && quoteBalances[0].balance >= 5) {
        const baseAsset = symbol.replace(/(USDT|USDC|FDUSD)$/, '');
        const altSymbol = baseAsset + dominantQuote;
        try {
          const exInfo = await client.getExchangeInfo([altSymbol]);
      if (exInfo.symbols && exInfo.symbols.find((s: any) => s.symbol === altSymbol)) {
        console.log(`  ℹ️  Auto-switching to ${altSymbol} (largest quote balance: ${dominantQuote})`);
        tradeSymbol = altSymbol;
      }
    } catch (e:any) {
      console.log(`  ℹ️  Keeping ${symbol} (alt symbol ${altSymbol} check failed)`);
    }
  }
  
  const state = initializeState(startEquity);
  
  console.log(`Systems Available:`);
  SYSTEMS.forEach(s => {
    console.log(`  ${s.name.padEnd(12)}: Target WinRate=${(s.winRateTarget*100).toFixed(0)}% Pos=${(s.posBase*100).toFixed(0)}%`);
  });
  console.log();
  
  // Trading loop
  for (let i = 0; i < bullets; i++) {
    console.log(`\n🎯 Trade ${i + 1}/${bullets}`);
    
    // Select system
    const system = selectSystem(state.systemWeights);
    
    // Execute trade
    const result = await executeTrade(client, tradeSymbol, system, state);
    
    // Update state
    state.equity += result.pnl;
    state.trades++;
    
    const systemStats = state.systemStats.get(system.name)!;
    systemStats.trades++;
    systemStats.pnl += result.pnl;
    if (result.success) systemStats.wins++;
    
    const recent = state.recentPerformance.get(system.name)!;
    recent.push(result.success ? 1 : 0);
    if (recent.length > lookbackWindow) recent.shift();
    
    console.log(`  ${result.success ? '✅ WIN' : '❌ LOSS'}: PnL ${result.pnl > 0 ? '+' : ''}$${result.pnl.toFixed(4)}`);
    console.log(`  Equity: $${state.equity.toFixed(2)} (${((state.equity / state.startEquity - 1) * 100).toFixed(2)}%)`);
    
    // Update weights every 5 trades
    if ((i + 1) % 5 === 0) {
      updateWeights(state, lookbackWindow, adaptSpeed, minWeight);
      console.log(`\n  🎼 Weight Rebalance:`);
      Array.from(state.systemWeights.entries())
        .sort((a, b) => b[1] - a[1])
        .forEach(([name, weight]) => {
          console.log(`    ${name.padEnd(12)}: ${(weight * 100).toFixed(1)}%`);
        });
    }
    
    // Delay between trades
    await new Promise(resolve => setTimeout(resolve, 2000));
  }
  
  // Final report
  console.log(`\n\n🎵 THE SYMPHONY CONCLUDES 🎵`);
  console.log(`  Start: $${state.startEquity.toFixed(2)}`);
  console.log(`  Final: $${state.equity.toFixed(2)}`);
  console.log(`  PnL: ${state.equity > state.startEquity ? '+' : ''}$${(state.equity - state.startEquity).toFixed(2)} (${((state.equity / state.startEquity - 1) * 100).toFixed(2)}%)`);
  console.log(`  Trades: ${state.trades}\n`);
  
  console.log(`  System Performance:`);
  Array.from(state.systemStats.entries())
    .sort((a, b) => b[1].trades - a[1].trades)
    .forEach(([name, stats]) => {
      const winRate = stats.trades > 0 ? (stats.wins / stats.trades * 100).toFixed(1) : '0.0';
      console.log(`    ${name.padEnd(12)}: ${stats.trades} trades | ${winRate}% wins | PnL $${stats.pnl.toFixed(2)}`);
    });
  
  console.log(`\n🦆 Through space and time, the song echoes on... 🎼\n`);
}

main().catch(err => {
  console.error('Testnet deployment failed:', err);
  process.exit(1);
});
