import 'dotenv/config';
import { BinanceClient } from '../core/binanceClient';
import { loadAccountsFromJson, AccountRecord } from './utils/accountLoader';

type AccountConfig = AccountRecord & { id: number };

const MAX_TRADES_PER_DAY_PER_ACCOUNT = Number(process.env.MAX_TRADES_PER_DAY_PER_ACCOUNT || 50);
// Ranged position sizing & thresholds for decorrelation
const POSITION_SIZE_MIN = Number(process.env.POSITION_SIZE_MIN || 85);
const POSITION_SIZE_MAX = Number(process.env.POSITION_SIZE_MAX || 92);
const MIN_PROFIT_BASE = Number(process.env.MIN_PROFIT_BASE || 0.30); // base target (percent)
const MIN_PROFIT_JITTER = Number(process.env.MIN_PROFIT_JITTER || 0.05); // +/- jitter range
const STOP_LOSS_BASE = Number(process.env.STOP_LOSS_BASE || 0.50); // base loss (percent)
const STOP_LOSS_JITTER = Number(process.env.STOP_LOSS_JITTER || 0.10); // jitter
const MAX_HOLD_TIME_MS = Number(process.env.MAX_HOLD_TIME_MS || 120000);
const CHECK_INTERVAL_MS = Number(process.env.CHECK_INTERVAL_MS || 2000);
// Fees & slippage (spot default ~0.1% per side)
const FEE_RATE = Number(process.env.FEE_RATE || 0.001); // 0.1% per side
const SLIPPAGE_RATE = Number(process.env.SLIPPAGE_RATE || 0.0005); // 0.05% assumed total
// Concurrency cap across all accounts
const MAX_CONCURRENT_POSITIONS = Number(process.env.MAX_CONCURRENT_POSITIONS || 10);
// Random delay jitter (ms) applied to check intervals
const INTERVAL_JITTER_MS = Number(process.env.INTERVAL_JITTER_MS || 500);
// Delay multiplier jitter after a sell (fraction)
const DELAY_JITTER_PCT = Number(process.env.DELAY_JITTER_PCT || 0.10);

type SymbolPrecision = { symbol: string; quantityPrecision: number };
const PRECISIONS: SymbolPrecision[] = [
  { symbol: 'BTCUSDC', quantityPrecision: 5 },
  { symbol: 'ETHUSDC', quantityPrecision: 4 },
  { symbol: 'BNBUSDC', quantityPrecision: 2 }
];

function formatQuantity(symbol: string, qty: number): string {
  const p = PRECISIONS.find(p => p.symbol === symbol)?.quantityPrecision || 4;
  return qty.toFixed(p);
}

interface TradeState {
  inPosition: boolean;
  entryPrice: number;
  symbol: string;
  quantity: number;
  tradesToday: number;
  lastTradeTimestamp: number;
  profitTarget: number; // percent
  stopLoss: number; // negative percent
  positionSizePercent: number; // percent of free USDC
  checkIntervalMs: number; // interval with jitter
}

// Global concurrency tracking
let activePositions = 0;

function randBetween(min: number, max: number) {
  return min + Math.random() * (max - min);
}

function randCentered(range: number) {
  // returns a value in [-range, +range]
  return (Math.random() * 2 - 1) * range;
}

function delay(ms: number) { return new Promise(r => setTimeout(r, ms)); }

async function runAccount(account: AccountConfig) {
  const client = new BinanceClient({ apiKey: account.apiKey, apiSecret: account.apiSecret, testnet: !(process.env.AUREON_FUSION_ARM_LIVE === "1" && process.env.BINANCE_TESTNET === "false") });
  // Expanded symbol universe for diversification
  const symbols = ['BTCUSDC', 'ETHUSDC', 'BNBUSDC']; // Could add more if available
  const symbolCycle = symbols.slice();
  const state: TradeState = {
    inPosition: false,
    entryPrice: 0,
    symbol: symbolCycle[0],
    quantity: 0,
    tradesToday: 0,
    lastTradeTimestamp: Date.now(),
    profitTarget: MIN_PROFIT_BASE + randCentered(MIN_PROFIT_JITTER),
    stopLoss: -(STOP_LOSS_BASE + Math.abs(randCentered(STOP_LOSS_JITTER))),
    positionSizePercent: randBetween(POSITION_SIZE_MIN, POSITION_SIZE_MAX),
    checkIntervalMs: CHECK_INTERVAL_MS + Math.floor(Math.random() * INTERVAL_JITTER_MS)
  };

  console.log(`\n[ACCOUNT ${account.id}] Starting multi-account beast mode...`);

  while (true) {
    try {
      const now = Date.now();
      // Reset daily trades at UTC midnight
      const utcMidnight = new Date();
      utcMidnight.setUTCHours(0, 0, 0, 0);
      if (now - utcMidnight.getTime() < CHECK_INTERVAL_MS) {
        state.tradesToday = 0;
      }

      if (state.tradesToday >= MAX_TRADES_PER_DAY_PER_ACCOUNT) {
        await new Promise(r => setTimeout(r, 60000));
        continue;
      }

      if (!state.inPosition) {
        // Respect concurrency cap
        if (activePositions >= MAX_CONCURRENT_POSITIONS) {
          await delay(3000);
          continue;
        }
        // Randomize symbol order occasionally
        if (Math.random() < 0.2) {
          symbolCycle.sort(() => Math.random() - 0.5);
        }
        state.symbol = symbolCycle[state.tradesToday % symbolCycle.length];
        const accountInfo = await client.getAccount();
        const usdc = accountInfo.balances.find(b => b.asset === 'USDC');
        const freeUSDC = Number(usdc?.free || 0);
        if (freeUSDC < 5) { // Skip if too low
          await delay(10000);
          continue;
        }
        const price = await client.getPrice(state.symbol);
        const positionSizeUSDC = freeUSDC * (state.positionSizePercent / 100);
        const rawQty = positionSizeUSDC / price;
        const quantity = Number(formatQuantity(state.symbol, rawQty));

        if (quantity <= 0) {
          await delay(10000);
          continue;
        }

        const buyOrder = await client.placeOrder({ symbol: state.symbol, side: 'BUY', type: 'MARKET', quantity });
        state.inPosition = true;
        state.entryPrice = price;
        state.quantity = quantity;
        state.lastTradeTimestamp = now;
        activePositions++;
        console.log(`[ACCOUNT ${account.id}] Bought ${quantity} ${state.symbol} @ ${price}`);
      } else {
        const currentPrice = await client.getPrice(state.symbol);
        const grossChangePercent = ((currentPrice - state.entryPrice) / state.entryPrice) * 100;
        // Net change after fees & slippage (approx two sides + slippage)
        const feeSlippagePercent = (FEE_RATE * 2 + SLIPPAGE_RATE) * 100;
        const netChangePercent = grossChangePercent - feeSlippagePercent;
        const heldMs = Date.now() - state.lastTradeTimestamp;

        let shouldSell = false;
        // Require gross profit to exceed target + overhead to achieve desired net
        const requiredGross = state.profitTarget + feeSlippagePercent;
        if (grossChangePercent >= requiredGross) shouldSell = true;
        else if (netChangePercent <= state.stopLoss) shouldSell = true;
        else if (heldMs >= MAX_HOLD_TIME_MS && netChangePercent > -0.25) shouldSell = true; // Graceful exit

        if (shouldSell) {
          const sellOrder = await client.placeOrder({ symbol: state.symbol, side: 'SELL', type: 'MARKET', quantity: state.quantity });
          console.log(`[ACCOUNT ${account.id}] Sold ${state.quantity} ${state.symbol} @ ${currentPrice} | Gross ${grossChangePercent.toFixed(2)}% | Net ${netChangePercent.toFixed(2)}% (Target ${state.profitTarget.toFixed(2)}% / Stop ${state.stopLoss.toFixed(2)}%)`);
          state.inPosition = false;
          state.tradesToday++;
          state.quantity = 0;
          activePositions = Math.max(0, activePositions - 1);
          // Re-randomize per-trade params for decorrelation
          state.profitTarget = MIN_PROFIT_BASE + randCentered(MIN_PROFIT_JITTER);
          state.stopLoss = -(STOP_LOSS_BASE + Math.abs(randCentered(STOP_LOSS_JITTER)));
          state.positionSizePercent = randBetween(POSITION_SIZE_MIN, POSITION_SIZE_MAX);
          state.checkIntervalMs = CHECK_INTERVAL_MS + Math.floor(Math.random() * INTERVAL_JITTER_MS);
          // Stagger next entry to spread load
          const baseDelayMinutes = Math.max(1, Math.floor((24 * 60) / (MAX_TRADES_PER_DAY_PER_ACCOUNT + 5)));
          const jitterFactor = 1 + (Math.random()*2 - 1) * DELAY_JITTER_PCT; // +/- DELAY_JITTER_PCT
          const actualDelayMs = baseDelayMinutes * jitterFactor * 60 * 1000;
          await delay(actualDelayMs);
          continue;
        }
      }
      await delay(state.checkIntervalMs);
    } catch (err: any) {
      console.error(`[ACCOUNT ${account.id}] Error:`, err.message || err);
      await delay(5000);
    }
  }
}

async function main() {
  const accounts = loadAccountsFromJson().map((acc, idx) => ({ ...acc, id: idx + 1 }));
  if (accounts.length === 0) {
    console.error('No accounts loaded. Check accounts.json file.');
    process.exit(1);
  }
  console.log(`\n════════ MULTI-ACCOUNT AUREON ════════`);
  console.log(`Loaded Accounts: ${accounts.length}`);
  console.log(`Total Potential Trades/Day: ${accounts.length * MAX_TRADES_PER_DAY_PER_ACCOUNT}`);
  console.log(`Profit Target Base: ${MIN_PROFIT_BASE}% ±${MIN_PROFIT_JITTER}% | Stop Base: -${STOP_LOSS_BASE}% ±${STOP_LOSS_JITTER}%`);
  console.log(`Position Size Range: ${POSITION_SIZE_MIN}% - ${POSITION_SIZE_MAX}% of free USDC`);
  console.log(`Fees+Slippage assumed: ${(FEE_RATE*100).toFixed(2)}%/side + ${(SLIPPAGE_RATE*100).toFixed(2)}% total`);
  console.log(`Concurrency Cap: ${MAX_CONCURRENT_POSITIONS} simultaneous positions`);
  console.log(`Max Hold: ${(MAX_HOLD_TIME_MS/1000)}s | Base Interval: ${CHECK_INTERVAL_MS}ms (±${INTERVAL_JITTER_MS}ms jitter)`);

  // Launch each account asynchronously
  for (const acc of accounts) {
    runAccount(acc); // Fire and forget
    await new Promise(r => setTimeout(r, 1000)); // Stagger startup
  }
}

main();
