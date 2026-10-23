/**
 * 🍯 THE HONEY POT 🍯
 * 
 * Tracks accumulated profits from the LION hunts.
 * Because every successful hunt brings honey back to the hive!
 * 
 * "The lion hunts, the honey flows" — General Quackers, 2025
 */

import * as fs from 'fs';
import * as path from 'path';

export interface HoneyMetrics {
  totalHoney: number; // Total profit in USD
  initialBalance: number;
  currentBalance: number;
  growthPercent: number;
  totalTrades: number;
  winningTrades: number;
  losingTrades: number;
  winRate: number;
  biggestWin: number;
  biggestLoss: number;
  currentStreak: number;
  bestStreak: number;
  worstStreak: number;
  dailyHoney: { [date: string]: number };
  milestones: HoneyMilestone[];
  lastUpdated: string;
}

export interface HoneyMilestone {
  type: 'balance' | 'profit' | 'trades' | 'streak';
  value: number;
  achievedAt: string;
  message: string;
}

export interface TradeResult {
  symbol: string;
  pnl: number;
  timestamp: string;
  side: 'BUY' | 'SELL';
}

export class HoneyPot {
  private metrics: HoneyMetrics;
  private honeyPath: string;
  
  constructor(honeyPath = './honey/honey_pot.json', initialBalance = 10000) {
    this.honeyPath = honeyPath;
    this.metrics = this.loadOrInitialize(initialBalance);
  }
  
  /**
   * Load existing honey pot or initialize new one
   */
  private loadOrInitialize(initialBalance: number): HoneyMetrics {
    try {
      if (fs.existsSync(this.honeyPath)) {
        const data = fs.readFileSync(this.honeyPath, 'utf-8');
        return JSON.parse(data);
      }
    } catch (error) {
      console.warn('⚠️  Could not load honey pot, initializing fresh...');
    }
    
    return {
      totalHoney: 0,
      initialBalance,
      currentBalance: initialBalance,
      growthPercent: 0,
      totalTrades: 0,
      winningTrades: 0,
      losingTrades: 0,
      winRate: 0,
      biggestWin: 0,
      biggestLoss: 0,
      currentStreak: 0,
      bestStreak: 0,
      worstStreak: 0,
      dailyHoney: {},
      milestones: [],
      lastUpdated: new Date().toISOString()
    };
  }
  
  /**
   * Add a trade result to the honey pot
   */
  addTrade(trade: TradeResult): HoneyMetrics {
    const today = trade.timestamp.split('T')[0];
    
    // Update basic metrics
    this.metrics.totalHoney += trade.pnl;
    this.metrics.currentBalance += trade.pnl;
    this.metrics.totalTrades++;
    
    // Update win/loss tracking
    if (trade.pnl > 0) {
      this.metrics.winningTrades++;
      this.metrics.currentStreak = Math.max(0, this.metrics.currentStreak) + 1;
      this.metrics.bestStreak = Math.max(this.metrics.bestStreak, this.metrics.currentStreak);
      if (trade.pnl > this.metrics.biggestWin) {
        this.metrics.biggestWin = trade.pnl;
        this.checkMilestone('profit', trade.pnl, `🏆 NEW BIGGEST WIN: $${trade.pnl.toFixed(2)} on ${trade.symbol}!`);
      }
    } else if (trade.pnl < 0) {
      this.metrics.losingTrades++;
      this.metrics.currentStreak = Math.min(0, this.metrics.currentStreak) - 1;
      this.metrics.worstStreak = Math.min(this.metrics.worstStreak, this.metrics.currentStreak);
      if (trade.pnl < this.metrics.biggestLoss) {
        this.metrics.biggestLoss = trade.pnl;
      }
    }
    
    // Update win rate
    this.metrics.winRate = this.metrics.totalTrades > 0
      ? (this.metrics.winningTrades / this.metrics.totalTrades) * 100
      : 0;
    
    // Update growth percent
    this.metrics.growthPercent = ((this.metrics.currentBalance - this.metrics.initialBalance) / this.metrics.initialBalance) * 100;
    
    // Update daily honey
    if (!this.metrics.dailyHoney[today]) {
      this.metrics.dailyHoney[today] = 0;
    }
    this.metrics.dailyHoney[today] += trade.pnl;
    
    // Check for milestones
    this.checkBalanceMilestones();
    this.checkStreakMilestones();
    this.checkTradeMilestones();
    
    // Update timestamp
    this.metrics.lastUpdated = trade.timestamp;
    
    // Save to disk
    this.save();
    
    // Celebrate if profitable!
    if (trade.pnl > 0) {
      this.celebrate(trade);
    }
    
    return this.metrics;
  }
  
  /**
   * Check for balance milestones
   */
  private checkBalanceMilestones(): void {
    const balanceMilestones = [
      { value: 11000, msg: '🍯 First $1K profit!' },
      { value: 12500, msg: '🍯 $2.5K profit - 25% growth!' },
      { value: 15000, msg: '🍯 $5K profit - 50% growth!' },
      { value: 20000, msg: '🍯 DOUBLED THE HONEY POT! 100% gains!' },
      { value: 30000, msg: '🍯 TRIPLED! $20K profit!' },
      { value: 50000, msg: '🍯💰 $40K PROFIT - 5X THE INITIAL!' },
      { value: 100000, msg: '🍯💰💎 $90K PROFIT - 10X! INTO 6 FIGURES!' },
    ];
    
    for (const milestone of balanceMilestones) {
      if (this.metrics.currentBalance >= milestone.value && 
          !this.hasMilestone('balance', milestone.value)) {
        this.addMilestone('balance', milestone.value, milestone.msg);
      }
    }
  }
  
  /**
   * Check for streak milestones
   */
  private checkStreakMilestones(): void {
    const streakMilestones = [
      { value: 5, msg: '🔥 5-trade winning streak!' },
      { value: 10, msg: '🔥🔥 10-trade winning streak - ON FIRE!' },
      { value: 20, msg: '🔥🔥🔥 20-trade winning streak - UNSTOPPABLE!' },
    ];
    
    for (const milestone of streakMilestones) {
      if (this.metrics.currentStreak >= milestone.value && 
          !this.hasMilestone('streak', milestone.value)) {
        this.addMilestone('streak', milestone.value, milestone.msg);
      }
    }
  }
  
  /**
   * Check for trade count milestones
   */
  private checkTradeMilestones(): void {
    const tradeMilestones = [
      { value: 100, msg: '💯 First 100 trades completed!' },
      { value: 500, msg: '💯 500 trades - Veteran trader!' },
      { value: 1000, msg: '💯 1,000 trades - Trading master!' },
    ];
    
    for (const milestone of tradeMilestones) {
      if (this.metrics.totalTrades >= milestone.value && 
          !this.hasMilestone('trades', milestone.value)) {
        this.addMilestone('trades', milestone.value, milestone.msg);
      }
    }
  }
  
  /**
   * Check if milestone already exists
   */
  private hasMilestone(type: HoneyMilestone['type'], value: number): boolean {
    return this.metrics.milestones.some(m => m.type === type && m.value === value);
  }
  
  /**
   * Add a new milestone
   */
  private addMilestone(type: HoneyMilestone['type'], value: number, message: string): void {
    const milestone: HoneyMilestone = {
      type,
      value,
      achievedAt: new Date().toISOString(),
      message
    };
    this.metrics.milestones.push(milestone);
    console.log('\n' + '🎉'.repeat(20));
    console.log(`   ${message}`);
    console.log('🎉'.repeat(20) + '\n');
  }
  
  /**
   * Generic milestone checker
   */
  private checkMilestone(type: HoneyMilestone['type'], value: number, message: string): void {
    if (!this.hasMilestone(type, value)) {
      this.addMilestone(type, value, message);
    }
  }
  
  /**
   * Celebrate a winning trade!
   */
  private celebrate(trade: TradeResult): void {
    const emojis = ['🍯', '💰', '✨', '🎯', '🦁', '🦆'];
    const emoji = emojis[Math.floor(Math.random() * emojis.length)];
    
    if (trade.pnl > 100) {
      console.log(`\n${emoji} BIG HONEY: +$${trade.pnl.toFixed(2)} from ${trade.symbol} ${emoji}`);
    } else if (trade.pnl > 50) {
      console.log(`${emoji} Nice honey: +$${trade.pnl.toFixed(2)} from ${trade.symbol}`);
    }
    
    // Show honey pot status on big wins
    if (trade.pnl > 100) {
      console.log(`🍯 Honey Pot: $${this.metrics.totalHoney.toFixed(2)} (+${this.metrics.growthPercent.toFixed(1)}%)`);
    }
  }
  
  /**
   * Save honey pot to disk
   */
  save(): void {
    const dir = path.dirname(this.honeyPath);
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
    fs.writeFileSync(this.honeyPath, JSON.stringify(this.metrics, null, 2));
  }
  
  /**
   * Get current metrics
   */
  getMetrics(): HoneyMetrics {
    return { ...this.metrics };
  }
  
  /**
   * Get today's honey
   */
  getTodayHoney(): number {
    const today = new Date().toISOString().split('T')[0];
    return this.metrics.dailyHoney[today] || 0;
  }
  
  /**
   * Get last N days of honey
   */
  getRecentHoney(days: number = 7): { date: string; honey: number }[] {
    const dates = Object.keys(this.metrics.dailyHoney).sort().slice(-days);
    return dates.map(date => ({
      date,
      honey: this.metrics.dailyHoney[date]
    }));
  }
  
  /**
   * Display honey pot status
   */
  displayStatus(): void {
    const m = this.metrics;
    
    console.log('\n' + '═'.repeat(60));
    console.log('              🍯 THE HONEY POT 🍯');
    console.log('═'.repeat(60) + '\n');
    
    console.log(`💰 Current Balance:  $${m.currentBalance.toFixed(2)}`);
    console.log(`🍯 Total Honey:      $${m.totalHoney.toFixed(2)} (${m.growthPercent >= 0 ? '+' : ''}${m.growthPercent.toFixed(2)}%)`);
    console.log(`📊 Initial Balance:  $${m.initialBalance.toFixed(2)}`);
    
    console.log('\n' + '─'.repeat(60) + '\n');
    
    console.log(`📈 Total Trades:     ${m.totalTrades}`);
    console.log(`✅ Wins:             ${m.winningTrades} (${m.winRate.toFixed(1)}%)`);
    console.log(`❌ Losses:           ${m.losingTrades}`);
    
    console.log('\n' + '─'.repeat(60) + '\n');
    
    console.log(`🏆 Biggest Win:      $${m.biggestWin.toFixed(2)}`);
    console.log(`💔 Biggest Loss:     $${m.biggestLoss.toFixed(2)}`);
    console.log(`🔥 Current Streak:   ${m.currentStreak} ${m.currentStreak > 0 ? '🔥' : ''}`);
    console.log(`⚡ Best Streak:      ${m.bestStreak}`);
    
    console.log('\n' + '─'.repeat(60) + '\n');
    
    const todayHoney = this.getTodayHoney();
    console.log(`📅 Today's Honey:    $${todayHoney.toFixed(2)}`);
    
    const recentHoney = this.getRecentHoney(7);
    if (recentHoney.length > 0) {
      console.log('\n📊 Last 7 Days:');
      recentHoney.forEach(day => {
        const sign = day.honey >= 0 ? '+' : '';
        const emoji = day.honey > 0 ? '🍯' : day.honey < 0 ? '💔' : '➖';
        console.log(`   ${emoji} ${day.date}: ${sign}$${day.honey.toFixed(2)}`);
      });
    }
    
    if (m.milestones.length > 0) {
      console.log('\n' + '─'.repeat(60) + '\n');
      console.log('🏆 MILESTONES ACHIEVED:\n');
      m.milestones.slice(-5).forEach(milestone => {
        console.log(`   ${milestone.message}`);
      });
    }
    
    console.log('\n' + '═'.repeat(60) + '\n');
  }
  
  /**
   * Get honey pot summary for War Room Brief
   */
  getSummaryForBrief(): string {
    const m = this.metrics;
    return `Honey Pot: $${m.totalHoney.toFixed(2)} (${m.growthPercent >= 0 ? '+' : ''}${m.growthPercent.toFixed(1)}%) | ${m.winningTrades}W/${m.losingTrades}L | Streak: ${m.currentStreak}`;
  }
  
  /**
   * Reset honey pot (use with caution!)
   */
  reset(newInitialBalance?: number): void {
    console.log('🍯 Resetting honey pot...');
    this.metrics = this.loadOrInitialize(newInitialBalance || this.metrics.initialBalance);
    this.save();
    console.log('✅ Honey pot reset complete!');
  }
}

// Export singleton instance
export const honeyPot = new HoneyPot();

/**
 * Convenience function to add trade and celebrate
 */
export function addHoney(symbol: string, pnl: number, side: 'BUY' | 'SELL' = 'BUY'): HoneyMetrics {
  return honeyPot.addTrade({
    symbol,
    pnl,
    side,
    timestamp: new Date().toISOString()
  });
}

/**
 * Convenience function to display status
 */
export function showHoney(): void {
  honeyPot.displayStatus();
}
