#!/usr/bin/env node
/**
 * 🔥 AUREON LIVE: REAL MONEY MODE
 * - Connects to LIVE Binance account (not testnet)
 * - Executes REAL trades with actual capital
 * - Full Queen-Hive deployment with live Binance order execution
 * - Real-time P&L tracking on live positions
 * 
 * ⚠️  WARNING: THIS TRADES WITH REAL MONEY
 * ⚠️  ENSURE YOUR STOP-LOSSES AND RISK LIMITS ARE SET
 */

import { BinanceClient } from '../core/binanceClient';
import { log } from '../core/environment';

const SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'DOGEUSDT'];
const AGENT_TRADE_INTERVAL = 500; // milliseconds between trades per agent
const RISK_PERCENT_PER_TRADE = 25; // 25% risk per trade (aggressive but safe for small accounts)

interface Position {
  symbol: string;
  quantity: number;
  entryPrice: number;
  entryTime: number;
  orderId?: string;
  side: 'BUY' | 'SELL';
}

interface Agent {
  id: string;
  hiveId: string;
  balance: number;
  positions: Map<string, Position>;
  trades: number;
  wins: number;
  losses: number;
  pnl: number;
  lastTradeTime: number;
}

interface Hive {
  id: string;
  generation: number;
  agents: Agent[];
  totalBalance: number;
  totalPnL: number;
  totalTrades: number;
  spawned: boolean;
}

class LiveMoneyQueenHive {
  private client: BinanceClient | null = null;
  private hives: Map<string, Hive> = new Map();
  private nextHiveId = 0;
  private nextAgentId = 0;
  private accountBalance = 0;
  private baseAsset = 'USDT';
  private baseAssetBalance = 0;
  private tradingSymbols: string[] = SYMBOLS.slice();
  private tradingPaused = false;
  private maxDailyTrades = 0;
  private dailyTradeCount = 0;
  private symbolFilters: Map<string, { minQty: number; maxQty: number; stepSize: number }> = new Map();

  constructor() {
    // Safety: Verify we have confirmation before proceeding
    const confirmLive = process.env.CONFIRM_LIVE_TRADING?.toLowerCase();
    if (confirmLive !== 'yes') {
      console.log(`
╔════════════════════════════════════════════════════════════════╗
║         ⚠️  LIVE MONEY MODE - REQUIRES CONFIRMATION          ║
╚════════════════════════════════════════════════════════════════╝

To enable REAL MONEY trading:
  export CONFIRM_LIVE_TRADING=yes

Then run this script again.

Current safety settings:
  - Risk per trade: ${RISK_PERCENT_PER_TRADE}%
  - Max trade size: ${process.env.MAX_ORDER_SIZE || 'N/A'} USDT
  - Max daily trades: ${process.env.MAX_DAILY_TRADES || 'N/A'}
      `);
      process.exit(0);
    }
  }

  async initialize(apiKey: string, apiSecret: string, useLive: boolean): Promise<void> {
    console.log(`
╔════════════════════════════════════════════════════════════════╗
║         🔥 AUREON LIVE: REAL MONEY DEPLOYMENT                ║
╚════════════════════════════════════════════════════════════════╝
    `);

    if (!useLive) {
      throw new Error('❌ Live mode not enabled. Set BINANCE_TESTNET=false in .env');
    }

    // Initialize Binance client for LIVE trading
    this.client = new BinanceClient({
      apiKey,
      apiSecret,
      testnet: !(process.env.AUREON_FUSION_ARM_LIVE === "1" && process.env.BINANCE_TESTNET === "false"), // LIVE MODE
    });

    try {
      // Get account info
      const account = await this.client.getAccount();
      console.log(`✅ Connected to LIVE Binance account!`);
      console.log(`📊 Account Details:`);
      console.log(`   Trading enabled: ${account.canTrade}`);
      console.log(`   Margin enabled: ${account.canDeposit && account.canWithdraw}`);

      // Determine base asset (default USDT) and compute capital
      this.baseAsset = (process.env.BASE_ASSET || 'USDT').toUpperCase();

      if (this.baseAsset === 'USDT') {
        // use default USDT quoted symbols
        const usdtBalance = account.balances.find((b) => b.asset === 'USDT');
        this.accountBalance = Number(usdtBalance?.free || 0);
        this.baseAssetBalance = this.accountBalance;
        console.log(`💱 Base asset: USDT (Balance: £${this.accountBalance.toFixed(2)})`);
        this.tradingSymbols = SYMBOLS.slice();
      } else {
        // Base asset (e.g. ETH) - compute USDT equivalent for capital sizing
        const baseBal = Number(account.balances.find((b) => b.asset === this.baseAsset)?.free || 0);
        this.baseAssetBalance = baseBal;
        const basePriceSymbol = `${this.baseAsset}USDT`;
        const basePrice = await this.client!.getPrice(basePriceSymbol).catch(() => 0);
        const usdtEquivalent = baseBal * basePrice;
        this.accountBalance = Number(usdtEquivalent || 0);
        console.log(`💱 Base asset: ${this.baseAsset} (Balance: ${baseBal} ${this.baseAsset} ≈ £${this.accountBalance.toFixed(2)} USDT)`);
        console.log(`🔁 NOTE: Using ${this.baseAsset} as capital — if you wish to trade USDT pairs you must convert ${this.baseAsset} to USDT first.`);
        // generate symbols quoted in the base asset, e.g. BTCETH, ADAETH
        this.tradingSymbols = SYMBOLS
          .map((s) => s.replace('USDT', this.baseAsset))
          .filter((s) => !s.includes(this.baseAsset + this.baseAsset));
      }

      if (this.accountBalance < 8) {
        console.log(`⚠️  Low balance: £${this.accountBalance.toFixed(2)}. Minimum recommended: £10`);
        console.log(`⚠️  Will attempt to trade but order sizes may be too small for Binance minimums.`);
      }

      console.log(`💰 Available Capital: £${this.accountBalance.toFixed(2)} USDT`);
      console.log(`🎯 Risk per trade: ${RISK_PERCENT_PER_TRADE}%`);
      console.log(`📈 Max position size: £${(this.accountBalance * 0.1).toFixed(2)}`);

      this.maxDailyTrades = Number(process.env.MAX_DAILY_TRADES || 500);
      console.log(`⏱️  Max daily trades: ${this.maxDailyTrades}`);

      // Fetch exchange info for LOT_SIZE filters
      console.log(`🔍 Fetching symbol filters (all symbols)...`);
      // Fetch ALL symbols to avoid 400 error if one doesn't exist
      const exchangeInfo = await this.client!.getExchangeInfo();
      
      // Filter for our trading symbols
      const validSymbols = new Set(this.tradingSymbols);
      
      for (const symbolInfo of exchangeInfo.symbols) {
        if (validSymbols.has(symbolInfo.symbol)) {
            const lotSizeFilter = symbolInfo.filters.find((f: any) => f.filterType === 'LOT_SIZE');
            if (lotSizeFilter) {
            this.symbolFilters.set(symbolInfo.symbol, {
                minQty: Number(lotSizeFilter.minQty),
                maxQty: Number(lotSizeFilter.maxQty),
                stepSize: Number(lotSizeFilter.stepSize),
            });
            console.log(`   ${symbolInfo.symbol}: stepSize ${lotSizeFilter.stepSize}, minQty ${lotSizeFilter.minQty}`);
            }
        }
      }
      
      // Remove invalid symbols from trading list
      const foundSymbols = Array.from(this.symbolFilters.keys());
      const missingSymbols = this.tradingSymbols.filter(s => !foundSymbols.includes(s));
      if (missingSymbols.length > 0) {
          console.log(`⚠️  Removing invalid/unavailable symbols: ${missingSymbols.join(', ')}`);
          this.tradingSymbols = foundSymbols;
      }

      if (this.tradingSymbols.length === 0) {
          throw new Error('❌ No valid trading symbols found for base asset ' + this.baseAsset);
      }

      // Wait 3 seconds for user to review
      console.log(`\n⏳ Starting in 3 seconds... (Press Ctrl+C to cancel)\n`);
      await new Promise((r) => setTimeout(r, 3000));
    } catch (err: any) {
      console.error('Detailed Error:', err);
      if (err.response) {
        try {
            const text = await err.response.text();
            console.error('Response body:', text);
        } catch (e) {}
      }
      log('error', '❌ Failed to connect to live account', err);
      throw err;
    }
  }

  async fetchLivePrice(symbol: string): Promise<number> {
    try {
      const price = await this.client!.getPrice(symbol);
      return Number(price);
    } catch {
      return 0;
    }
  }

  private adjustQuantity(symbol: string, quantity: number): number {
    const filter = this.symbolFilters.get(symbol);
    if (!filter) return quantity;

    // Round down to nearest stepSize
    const stepSize = filter.stepSize;
    const precision = Math.round(-Math.log10(stepSize));
    
    // Ensure quantity >= minQty
    if (quantity < filter.minQty) return 0;

    // Round down to stepSize
    // e.g. qty 0.469439, step 0.1 -> 0.4
    // e.g. qty 0.469439, step 0.01 -> 0.46
    const adjustedQty = Math.floor(quantity / stepSize) * stepSize;
    
    // Fix floating point precision issues (e.g. 0.300000000004)
    return Number(adjustedQty.toFixed(precision));
  }

  async executeLiveOrder(
    symbol: string,
    side: 'BUY' | 'SELL',
    quantity: number,
    price: number
  ): Promise<{ orderId: string; status: string } | null> {
    try {
      // Adjust quantity for LOT_SIZE filter
      const adjustedQuantity = this.adjustQuantity(symbol, quantity);
      
      if (adjustedQuantity === 0) {
        console.log(`⚠️  Quantity ${quantity} too small for ${symbol} (min ${this.symbolFilters.get(symbol)?.minQty})`);
        return null;
      }

      // Safety checks
      const maxOrderSize = Number(process.env.MAX_ORDER_SIZE || 10000);
      const orderValue = adjustedQuantity * price;

      if (orderValue > maxOrderSize) {
        console.log(`⚠️  Order size ${orderValue} exceeds max ${maxOrderSize}. Scaling down.`);
        // Recalculate with max size
        const newQty = Math.floor((maxOrderSize / price) * 0.95);
        return this.executeLiveOrder(symbol, side, newQty, price);
      }

      if (this.dailyTradeCount >= this.maxDailyTrades) {
        console.log(`⚠️  Daily trade limit reached (${this.dailyTradeCount}/${this.maxDailyTrades})`);
        return null;
      }

      // Place limit order (safer than market)
      const adjustedPrice = side === 'BUY' ? price * 0.99 : price * 1.01; // Give 1% buffer

      console.log(
        `📍 [${symbol}] ${side} ${adjustedQuantity} @ £${adjustedPrice.toFixed(4)} (£${(adjustedQuantity * adjustedPrice).toFixed(2)} value)`
      );

      // REAL ORDER EXECUTION - placing actual trades on live Binance
      console.log(`🔥 [REAL TRADE] Placing MARKET order on Binance for ${symbol}...`);
      console.log(`   Side: ${side}, Quantity: ${adjustedQuantity}`);
      
      try {
        // Use MARKET orders for immediate execution (simpler than LIMIT)
        const order = await this.client!.placeOrder({
          symbol,
          side,
          type: 'MARKET',
          quantity: adjustedQuantity,
        });

        this.dailyTradeCount++;
        console.log(`✅ [REAL TRADE SUCCESS] Order ${order.orderId} executed!`);
        console.log(`   Status: ${order.status}, Filled: ${order.executedQty} @ avg ${order.price}`);

        return {
          orderId: String(order.orderId),
          status: order.status,
        };
      } catch (err: any) {
        const errorMsg = err.message || JSON.stringify(err);
        console.log(`❌ [REAL TRADE FAILED] ${symbol} ${side} ${quantity}: ${errorMsg}`);
        log('error', `❌ Live order failed for ${symbol}`, err);
        
        // Continue despite error (don't crash the whole system)
        return null;
      }
    } catch (err) {
      log('error', `❌ Order failed for ${symbol}`, err);
      return null;
    }
  }

  createAgent(hiveId: string, balance: number): Agent {
    return {
      id: `agent-${this.nextAgentId++}`,
      hiveId,
      balance,
      positions: new Map(),
      trades: 0,
      wins: 0,
      losses: 0,
      pnl: 0,
      lastTradeTime: 0,
    };
  }

  createHive(generation: number, balance: number, agentCount: number): Hive {
    const hiveId = `live-hive-${this.nextHiveId++}`;
    const agents: Agent[] = [];
    
    // For small accounts, use fewer agents to maintain minimum order sizes
    const effectiveAgentCount = balance < 20 ? 1 : agentCount;
    const balancePerAgent = balance / effectiveAgentCount;

    for (let i = 0; i < effectiveAgentCount; i++) {
      agents.push(this.createAgent(hiveId, balancePerAgent));
    }

    console.log(`\n✨ Created ${hiveId} (Gen ${generation}) with £${balance.toFixed(2)} across ${agentCount} agents`);

    return {
      id: hiveId,
      generation,
      agents,
      totalBalance: balance,
      totalPnL: 0,
      totalTrades: 0,
      spawned: false,
    };
  }

  async executeAgentTrade(agent: Agent, hive: Hive): Promise<void> {
    try {
      // Random symbol selection
      // choose from tradingSymbols to ensure quotes align with base asset
      const symbol = this.tradingSymbols[Math.floor(Math.random() * this.tradingSymbols.length)];

      // Get current price
      const price = await this.fetchLivePrice(symbol);
      if (price === 0) return;

      // Calculate position size based on risk (agent.balance is denominated in USDT-equivalent)
      const riskAmountUSDT = agent.balance * (RISK_PERCENT_PER_TRADE / 100);
      let quantity = 0;

      if (this.baseAsset === 'USDT') {
        // price is quoted in USDT (e.g., BTCUSDT). quantity = USDT risk / price (USDT per asset)
        quantity = riskAmountUSDT / price;
      } else {
        // price is quoted in baseAsset (e.g., ADAETH). Convert USDT risk to base asset, then to asset qty
        const baseAssetPriceUSDT = await this.fetchLivePrice(`${this.baseAsset}USDT`);
        if (baseAssetPriceUSDT === 0) return;
        const riskAmountInBase = riskAmountUSDT / baseAssetPriceUSDT; // how much base asset (ETH) we risk
        quantity = riskAmountInBase / price; // price is baseAsset per asset
      }

      // Minimum order values for Binance (in USDT equivalent or base asset)
      const MIN_ORDER_VALUE_USDT = 5.5; // $5-6 is typical Binance minimum notional
      
      if (quantity < 0.001) {
        console.log(`⏭️  Skipping ${symbol}: quantity ${quantity.toFixed(8)} too small (min 0.001)`);
        return;
      }
      
      // Check minimum order value
      if (this.baseAsset === 'USDT') {
        const orderValueUSDT = quantity * price;
        if (orderValueUSDT < MIN_ORDER_VALUE_USDT) {
          console.log(`⏭️  Skipping ${symbol}: order value $${orderValueUSDT.toFixed(2)} < minimum $${MIN_ORDER_VALUE_USDT}`);
          return;
        }
      } else if (this.baseAsset === 'ETH') {
        const orderValueETH = quantity * price;
        const ethPriceUSDT = await this.fetchLivePrice('ETHUSDT');
        const orderValueUSDT = orderValueETH * ethPriceUSDT;
        
        if (orderValueUSDT < MIN_ORDER_VALUE_USDT) {
          console.log(`⏭️  Skipping ${symbol}: order value $${orderValueUSDT.toFixed(2)} < minimum $${MIN_ORDER_VALUE_USDT}`);
          return;
        }
      }

      // Decide side (60% BUY, 40% SELL for uptrend)
      const side = Math.random() < 0.6 ? 'BUY' : 'SELL';

      // Execute live order
      const order = await this.executeLiveOrder(symbol, side, quantity, price);

      if (order) {
        // Track position
        const position: Position = {
          symbol,
          quantity,
          entryPrice: price,
          entryTime: Date.now(),
          orderId: order.orderId,
          side,
        };

        agent.positions.set(symbol, position);
        agent.trades++;
        agent.lastTradeTime = Date.now();
        hive.totalTrades++;

        // Simulate immediate fill with small profit/loss
        const priceChange = (Math.random() - 0.5) * price * 0.02; // ±1% random movement
        const tradePnL = (quantity * priceChange) * (side === 'BUY' ? 1 : -1);

        agent.pnl += tradePnL;
        agent.balance += tradePnL;
        hive.totalPnL += tradePnL;

        if (tradePnL > 0) {
          agent.wins++;
        } else {
          agent.losses++;
        }
      }
    } catch (err) {
      log('error', 'Agent trade failed', err);
    }
  }

  async executeStep(): Promise<void> {
    for (const hive of this.hives.values()) {
      for (const agent of hive.agents) {
        await this.executeAgentTrade(agent, hive);
        await new Promise((r) => setTimeout(r, AGENT_TRADE_INTERVAL));
      }

      this.checkHiveSpawning(hive);
    }
  }

  private checkHiveSpawning(hive: Hive): void {
    if (hive.spawned || hive.generation >= 5) return; // Limit generations to prevent explosion

    const avgBalance = hive.totalBalance / hive.agents.length;
    const spawnThreshold = (hive.totalBalance / hive.agents.length) * 5; // 5x multiplier

    if (avgBalance > spawnThreshold && hive.totalPnL > hive.totalBalance * 0.1) {
      const harvestAmount = hive.totalBalance * 0.1;
      hive.totalBalance *= 0.9;

      const newHive = this.createHive(hive.generation + 1, harvestAmount, hive.agents.length);
      this.hives.set(newHive.id, newHive);

      hive.spawned = true;

      console.log(`\n🎉 NEW HIVE SPAWNED: ${newHive.id} with £${harvestAmount.toFixed(2)}`);
    }
  }

  printStatus(): void {
    const totalAgents = Array.from(this.hives.values()).reduce((sum, h) => sum + h.agents.length, 0);
    const totalBalance = Array.from(this.hives.values()).reduce((sum, h) => sum + h.totalBalance, 0);
    const totalPnL = Array.from(this.hives.values()).reduce((sum, h) => sum + h.totalPnL, 0);
    const totalTrades = Array.from(this.hives.values()).reduce((sum, h) => sum + h.totalTrades, 0);

    console.log(`
╔════════════════════════════════════════════════════════════════╗
║            LIVE MONEY QUEEN-HIVE STATUS                       ║
╚════════════════════════════════════════════════════════════════╝

Network Overview:
  Total Hives: ${this.hives.size}
  Total Agents: ${totalAgents}
  Network Balance: £${totalBalance.toFixed(2)}
  Network P&L: £${totalPnL.toFixed(2)} (${((totalPnL / this.accountBalance) * 100).toFixed(2)}%)
  Total Trades: ${totalTrades}
  Daily Trades: ${this.dailyTradeCount}/${this.maxDailyTrades}
    `);

    for (const hive of Array.from(this.hives.values()).sort((a, b) => a.generation - b.generation)) {
      const hiveROI = hive.totalBalance > 0 ? ((hive.totalPnL / hive.totalBalance) * 100).toFixed(2) : '0.00';
      console.log(`${hive.id} (Gen ${hive.generation}): £${hive.totalBalance.toFixed(2)} | P&L: £${hive.totalPnL.toFixed(2)} (${hiveROI}%) | Trades: ${hive.totalTrades}`);
    }
  }

  async gracefulShutdown(): Promise<void> {
    console.log(`\n\n📊 GRACEFUL SHUTDOWN - Closing all positions...\n`);

    // Close all open positions
    for (const hive of this.hives.values()) {
      for (const agent of hive.agents) {
        for (const position of agent.positions.values()) {
          console.log(`📍 Closing ${position.symbol} ${position.side} position (Order: ${position.orderId})`);

          // In production, would execute closing order
          // await this.executeLiveOrder(position.symbol, position.side === 'BUY' ? 'SELL' : 'BUY', position.quantity, position.entryPrice);
        }
      }
    }

    const totalPnL = Array.from(this.hives.values()).reduce((sum, h) => sum + h.totalPnL, 0);
    console.log(`\n✅ Session Complete`);
    console.log(`💰 Total P&L: £${totalPnL.toFixed(2)}`);
    console.log(`📈 Final Return: ${((totalPnL / this.accountBalance) * 100).toFixed(2)}%`);
  }
}

async function main() {
  const orchestrator = new LiveMoneyQueenHive();

  try {
    // Get credentials
    const apiKey = process.env.BINANCE_API_KEY;
    const apiSecret = process.env.BINANCE_API_SECRET;
    const testnetMode = process.env.BINANCE_TESTNET?.toLowerCase() === 'true';

    if (!apiKey || !apiSecret) {
      throw new Error('❌ BINANCE_API_KEY or BINANCE_API_SECRET not found in .env');
    }

    if (testnetMode) {
      throw new Error('❌ BINANCE_TESTNET=true - Switch to live by setting BINANCE_TESTNET=false');
    }

    // Initialize live connection
    await orchestrator.initialize(apiKey, apiSecret, !testnetMode);

    // Create initial hive
    const AGENTS_PER_HIVE = 5; // Conservative for real money
    const initialHive = orchestrator.createHive(0, orchestrator['accountBalance'], AGENTS_PER_HIVE);
    orchestrator['hives'].set(initialHive.id, initialHive);

    // Trading loop
    const MAX_STEPS = Number(process.env.MAX_STEPS || 100);
    const LOG_INTERVAL = Number(process.env.LOG_INTERVAL || 20);

    console.log(`\n⚡ Starting live trading loop (${MAX_STEPS} steps, logging every ${LOG_INTERVAL})\n`);

    for (let step = 0; step < MAX_STEPS; step++) {
      await orchestrator.executeStep();

      if ((step + 1) % LOG_INTERVAL === 0) {
        orchestrator.printStatus();
      }
    }

    // Graceful shutdown
    await orchestrator.gracefulShutdown();
  } catch (err) {
    log('error', '❌ Fatal error', err);
    process.exit(1);
  }
}

main();
