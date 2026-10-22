#!/usr/bin/env node
/**
 * 📊 PERFORMANCE REPORT GENERATOR
 * 
 * Generates comprehensive performance analytics
 * - ROI calculations
 * - Win rate analysis
 * - Trade history summary
 * - Milestone tracking
 */

import * as fs from 'fs';
import * as path from 'path';

const GREEN = '\x1b[32m';
const RED = '\x1b[31m';
const YELLOW = '\x1b[33m';
const BLUE = '\x1b[34m';
const BOLD = '\x1b[1m';
const RESET = '\x1b[0m';

interface Trade {
  timestamp: number;
  bot: string;
  symbol: string;
  side: 'BUY' | 'SELL';
  quantity: number;
  price: number;
  value: number;
  fee?: number;
  profit?: number;
}

interface BotStats {
  totalTrades: number;
  wins: number;
  losses: number;
  winRate: number;
  totalProfit: number;
  avgProfit: number;
  avgLoss: number;
  largestWin: number;
  largestLoss: number;
}

function log(message: string, color: string = RESET) {
  console.log(`${color}${message}${RESET}`);
}

function header(text: string) {
  console.log('\n' + '═'.repeat(70));
  log(`  ${text}`, BOLD + BLUE);
  console.log('═'.repeat(70) + '\n');
}

function formatCurrency(value: number): string {
  if (value >= 1_000_000) {
    return `$${(value / 1_000_000).toFixed(2)}M`;
  } else if (value >= 1_000) {
    return `$${(value / 1_000).toFixed(2)}K`;
  } else {
    return `$${value.toFixed(2)}`;
  }
}

function loadTrades(): Trade[] {
  const trades: Trade[] = [];
  
  // Try to load from CSV
  const csvPath = path.join(process.cwd(), 'backtest_trades.csv');
  if (fs.existsSync(csvPath)) {
    const content = fs.readFileSync(csvPath, 'utf-8');
    const lines = content.split('\n').slice(1); // Skip header
    
    lines.forEach(line => {
      if (!line.trim()) return;
      
      const [timestamp, bot, symbol, side, quantity, price, value, fee, profit] = line.split(',');
      
      trades.push({
        timestamp: parseInt(timestamp) || Date.now(),
        bot: bot?.trim() || 'Unknown',
        symbol: symbol?.trim() || 'UNKNOWN',
        side: (side?.trim() as 'BUY' | 'SELL') || 'BUY',
        quantity: parseFloat(quantity) || 0,
        price: parseFloat(price) || 0,
        value: parseFloat(value) || 0,
        fee: parseFloat(fee) || 0,
        profit: parseFloat(profit) || 0
      });
    });
  }
  
  return trades;
}

function calculateBotStats(trades: Trade[], botName: string): BotStats {
  const botTrades = trades.filter(t => t.bot === botName);
  
  const wins = botTrades.filter(t => (t.profit || 0) > 0);
  const losses = botTrades.filter(t => (t.profit || 0) < 0);
  
  const totalProfit = botTrades.reduce((sum, t) => sum + (t.profit || 0), 0);
  const avgProfit = wins.length > 0 ? wins.reduce((sum, t) => sum + (t.profit || 0), 0) / wins.length : 0;
  const avgLoss = losses.length > 0 ? losses.reduce((sum, t) => sum + (t.profit || 0), 0) / losses.length : 0;
  
  const largestWin = wins.length > 0 ? Math.max(...wins.map(t => t.profit || 0)) : 0;
  const largestLoss = losses.length > 0 ? Math.min(...losses.map(t => t.profit || 0)) : 0;
  
  return {
    totalTrades: botTrades.length,
    wins: wins.length,
    losses: losses.length,
    winRate: botTrades.length > 0 ? (wins.length / botTrades.length) * 100 : 0,
    totalProfit,
    avgProfit,
    avgLoss,
    largestWin,
    largestLoss
  };
}

function displayOverview(trades: Trade[]) {
  header('📊 PERFORMANCE OVERVIEW');
  
  const totalTrades = trades.length;
  const totalValue = trades.reduce((sum, t) => sum + t.value, 0);
  const totalFees = trades.reduce((sum, t) => sum + (t.fee || 0), 0);
  const totalProfit = trades.reduce((sum, t) => sum + (t.profit || 0), 0);
  
  const wins = trades.filter(t => (t.profit || 0) > 0).length;
  const losses = trades.filter(t => (t.profit || 0) < 0).length;
  const winRate = totalTrades > 0 ? (wins / totalTrades) * 100 : 0;
  
  log(`Total Trades: ${totalTrades}`, GREEN);
  log(`Total Volume: ${formatCurrency(totalValue)}`, GREEN);
  log(`Total Fees: ${formatCurrency(totalFees)}`, YELLOW);
  log(`Net Profit: ${formatCurrency(totalProfit)}`, totalProfit >= 0 ? GREEN : RED);
  log(`Win Rate: ${winRate.toFixed(1)}% (${wins}W / ${losses}L)`, winRate >= 60 ? GREEN : YELLOW);
  
  if (trades.length > 0) {
    const firstTrade = trades[0];
    const lastTrade = trades[trades.length - 1];
    const duration = lastTrade.timestamp - firstTrade.timestamp;
    const days = duration / (1000 * 60 * 60 * 24);
    
    log(`\nTrading Period: ${days.toFixed(1)} days`, BLUE);
    log(`Trades per Day: ${(totalTrades / days).toFixed(1)}`, BLUE);
  }
}

function displayBotPerformance(trades: Trade[]) {
  header('🤖 BOT PERFORMANCE');
  
  const bots = ['Hummingbird', 'ArmyAnts', 'LoneWolf'];
  
  bots.forEach(botName => {
    const stats = calculateBotStats(trades, botName);
    
    if (stats.totalTrades === 0) {
      log(`${botName}: No trades yet`, YELLOW);
      return;
    }
    
    console.log('');
    log(`${botName}:`, BOLD + BLUE);
    log(`  Total Trades: ${stats.totalTrades}`, GREEN);
    log(`  Win Rate: ${stats.winRate.toFixed(1)}% (${stats.wins}W / ${stats.losses}L)`, 
        stats.winRate >= 60 ? GREEN : YELLOW);
    log(`  Total Profit: ${formatCurrency(stats.totalProfit)}`, 
        stats.totalProfit >= 0 ? GREEN : RED);
    log(`  Avg Win: ${formatCurrency(stats.avgProfit)}`, GREEN);
    log(`  Avg Loss: ${formatCurrency(stats.avgLoss)}`, RED);
    log(`  Largest Win: ${formatCurrency(stats.largestWin)}`, GREEN);
    log(`  Largest Loss: ${formatCurrency(stats.largestLoss)}`, RED);
  });
}

function displayRecentActivity(trades: Trade[]) {
  header('📈 RECENT ACTIVITY (Last 10 Trades)');
  
  const recent = trades.slice(-10).reverse();
  
  if (recent.length === 0) {
    log('No trades yet', YELLOW);
    return;
  }
  
  console.log('');
  log('Time       | Bot          | Symbol      | Side | Quantity    | Price      | Profit', BLUE);
  log('─'.repeat(85), BLUE);
  
  recent.forEach(trade => {
    const time = new Date(trade.timestamp).toLocaleTimeString();
    const bot = trade.bot.padEnd(12);
    const symbol = trade.symbol.padEnd(11);
    const side = trade.side.padEnd(4);
    const quantity = trade.quantity.toFixed(6).padStart(11);
    const price = trade.price.toFixed(4).padStart(10);
    const profit = formatCurrency(trade.profit || 0).padStart(8);
    
    const color = (trade.profit || 0) >= 0 ? GREEN : RED;
    
    log(`${time} | ${bot} | ${symbol} | ${side} | ${quantity} | ${price} | ${profit}`, color);
  });
}

function displayMilestones(trades: Trade[], startingCapital: number) {
  header('🏁 MILESTONE TRACKING');
  
  const milestones = [100, 1000, 10000, 100000, 1000000, 10000000];
  let currentCapital = startingCapital;
  
  log(`Starting Capital: ${formatCurrency(startingCapital)}`, BLUE);
  console.log('');
  
  const sortedTrades = [...trades].sort((a, b) => a.timestamp - b.timestamp);
  
  milestones.forEach(milestone => {
    let reached = false;
    let reachedAt = null;
    
    for (const trade of sortedTrades) {
      currentCapital += (trade.profit || 0);
      
      if (currentCapital >= milestone && !reached) {
        reached = true;
        reachedAt = new Date(trade.timestamp);
        break;
      }
    }
    
    if (reached && reachedAt) {
      const duration = (reachedAt.getTime() - sortedTrades[0].timestamp) / (1000 * 60 * 60 * 24);
      log(`✅ ${formatCurrency(milestone)}: Day ${Math.floor(duration)} (${reachedAt.toLocaleDateString()})`, GREEN);
    } else {
      log(`⏳ ${formatCurrency(milestone)}: Not reached yet`, YELLOW);
    }
  });
  
  // Current balance
  console.log('');
  log(`Current Capital: ${formatCurrency(currentCapital)}`, BOLD + GREEN);
  const roi = ((currentCapital - startingCapital) / startingCapital) * 100;
  log(`ROI: ${roi.toFixed(0)}% (${(currentCapital / startingCapital).toFixed(1)}x)`, BOLD + GREEN);
}

function generateReport() {
  console.clear();
  
  header('📊 AUREON PERFORMANCE REPORT');
  
  log('Generating comprehensive performance analytics...', BLUE);
  
  // Load trades
  const trades = loadTrades();
  
  if (trades.length === 0) {
    log('\n⚠️  No trading data found.', YELLOW);
    log('Trade data is loaded from: backtest_trades.csv', YELLOW);
    log('Start trading to generate performance reports.', YELLOW);
    return;
  }
  
  // Display sections
  displayOverview(trades);
  displayBotPerformance(trades);
  displayRecentActivity(trades);
  displayMilestones(trades, 15); // Starting capital $15
  
  // Footer
  header('✅ REPORT COMPLETE');
  
  log('To view detailed logs:', BLUE);
  log('  ./logs/', BLUE);
  console.log('');
  log('To export data:', BLUE);
  log('  npx tsx scripts/collect_trades.ts', BLUE);
  console.log('');
}

if (require.main === module) {
  generateReport();
}

export { loadTrades, calculateBotStats };
