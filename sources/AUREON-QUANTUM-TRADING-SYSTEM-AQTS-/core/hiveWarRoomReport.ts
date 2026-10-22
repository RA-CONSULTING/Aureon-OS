/**
 * HIVE WAR ROOM REPORT
 * 
 * Daily intelligence packet from the AUREON hive mind.
 * Summarizes market behavior, engine activity, and field coherence.
 * 
 * Position: Super Quantum Quackers General 🦆⚡
 */

import * as fs from 'fs';
import * as path from 'path';
import { LighthouseMetrics } from './lighthouseMetrics';
import { PerformanceTracker } from './performanceTracker';
import { honeyPot, HoneyMetrics } from './honeyPot';

export interface FieldIntelligence {
  averageLighthouseIntensity: number;
  coherenceBursts: number;
  entropyTrend: 'rising' | 'falling' | 'stable';
  peakCoherenceTime: string;
  peakCoherenceValue: number;
  fieldMood: 'compressed spring' | 'directional flow' | 'chaotic chop' | 'crystalline order';
}

export interface EngineActivity {
  signalsGenerated: number;
  signalsExecuted: number;
  killSwitchEvents: number;
  killSwitchDuration: number; // minutes
  rateLimitEvents: number;
  dataLatencySpikes: number;
}

export interface RiskAssessment {
  drawdownStatus: 'within limits' | 'approaching threshold' | 'exceeded threshold';
  volatilityLevel: 'low' | 'medium' | 'high' | 'extreme';
  recommendations: string[];
}

export interface LionReconOrders {
  targetPairs: string[];
  scanFrequency: 'aggressive' | 'normal' | 'conservative';
  entryThreshold: number; // Minimum lighthouse intensity for entries
  exitStrategy: 'tight' | 'normal' | 'wide';
  positionSize: 'reduced' | 'normal' | 'increased';
  focusAreas: string[]; // What the lions should hunt for
  avoidConditions: string[]; // What the lions should avoid
  tacticalDirective: string; // General's specific orders
}

export interface TradeBreakdown {
  wins: number;
  losses: number;
  averageRR: number;
  biggestWinner: { pair: string; pnl: number };
  biggestLoser: { pair: string; pnl: number };
  topPairs: Array<{ pair: string; pnl: number; trades: number }>;
}

export interface WarRoomBrief {
  // Header
  date: string;
  user: string;
  botName: string;
  fieldStatus: 'Calm' | 'Compressed' | 'Volatile' | 'Coherent';
  
  // Honey Pot Status
  honeyPot?: HoneyMetrics;
  
  // Tactical Summary
  netPnL: number;
  netPnLPercent: number;
  totalTrades: number;
  maxDrawdown: number;
  regime: 'Trending' | 'Choppy' | 'Range-bound';
  marketBias: 'bullish' | 'bearish' | 'neutral';
  coherenceLevel: 'low' | 'medium' | 'high';
  
  // Field Intelligence
  fieldIntelligence: FieldIntelligence;
  
  // Engine Activity
  engineActivity: EngineActivity;
  
  // Performance Breakdown
  tradeBreakdown: TradeBreakdown;
  
  // Risk & Recommendations
  riskAssessment: RiskAssessment;
  
  // LION Reconnaissance Orders
  lionReconOrders: LionReconOrders;
  
  // Closing
  hiveStatus: 'online' | 'degraded' | 'offline';
  closingMessage: string;
}

export class HiveWarRoomReporter {
  private metricsDir: string;
  private logsDir: string;
  
  constructor(metricsDir = './metrics', logsDir = './logs') {
    this.metricsDir = metricsDir;
    this.logsDir = logsDir;
  }
  
  /**
   * Generate a War Room Brief for a specific date
   */
  async generateBrief(date: Date, user: string, botName: string): Promise<WarRoomBrief> {
    const dateStr = date.toISOString().split('T')[0];
    
    // Load trade data
    const trades = await this.loadTradeData(dateStr);
    
    // Load lighthouse metrics
    const lighthouseData = await this.loadLighthouseData(dateStr);
    
    // Load engine logs
    const engineLogs = await this.loadEngineLogs(dateStr);
    
    // Compute all sections
    const tacticalSummary = this.computeTacticalSummary(trades);
    const fieldIntelligence = this.computeFieldIntelligence(lighthouseData);
    const engineActivity = this.computeEngineActivity(engineLogs);
    const tradeBreakdown = this.computeTradeBreakdown(trades);
    const riskAssessment = this.computeRiskAssessment(tacticalSummary, fieldIntelligence);
    
    // Generate LION reconnaissance orders
    const lionReconOrders = this.generateLionReconOrders(
      tacticalSummary,
      fieldIntelligence,
      tradeBreakdown,
      riskAssessment
    );
    
    // Determine field status
    const fieldStatus = this.determineFieldStatus(fieldIntelligence, tacticalSummary);
    
    // Generate closing message
    const closingMessage = this.generateClosingMessage(fieldIntelligence, tacticalSummary);
    
    // Get honey pot metrics
    const honeyMetrics = honeyPot.getMetrics();
    
    return {
      date: dateStr,
      user,
      botName,
      fieldStatus,
      honeyPot: honeyMetrics,
      ...tacticalSummary,
      fieldIntelligence,
      engineActivity,
      tradeBreakdown,
      riskAssessment,
      lionReconOrders,
      hiveStatus: 'online',
      closingMessage
    };
  }
  
  private async loadTradeData(date: string): Promise<any[]> {
    try {
      const tradePath = path.join(this.logsDir, `trades_${date}.json`);
      if (fs.existsSync(tradePath)) {
        const data = fs.readFileSync(tradePath, 'utf-8');
        return JSON.parse(data);
      }
    } catch (error) {
      console.warn(`No trade data for ${date}`);
    }
    return [];
  }
  
  private async loadLighthouseData(date: string): Promise<any> {
    try {
      const metricsPath = path.join(this.metricsDir, `lighthouse_${date}.json`);
      if (fs.existsSync(metricsPath)) {
        const data = fs.readFileSync(metricsPath, 'utf-8');
        return JSON.parse(data);
      }
    } catch (error) {
      console.warn(`No lighthouse data for ${date}`);
    }
    return { readings: [] };
  }
  
  private async loadEngineLogs(date: string): Promise<any> {
    try {
      const logPath = path.join(this.logsDir, `engine_${date}.json`);
      if (fs.existsSync(logPath)) {
        const data = fs.readFileSync(logPath, 'utf-8');
        return JSON.parse(data);
      }
    } catch (error) {
      console.warn(`No engine logs for ${date}`);
    }
    return { events: [] };
  }
  
  private computeTacticalSummary(trades: any[]) {
    const netPnL = trades.reduce((sum, t) => sum + (t.pnl || 0), 0);
    const initialBalance = 10000; // Should come from config
    const netPnLPercent = (netPnL / initialBalance) * 100;
    
    // Compute drawdown
    let peak = initialBalance;
    let maxDrawdown = 0;
    let running = initialBalance;
    
    for (const trade of trades) {
      running += trade.pnl || 0;
      if (running > peak) peak = running;
      const dd = ((peak - running) / peak) * 100;
      if (dd > maxDrawdown) maxDrawdown = dd;
    }
    
    // Determine regime
    const winningTrades = trades.filter(t => (t.pnl || 0) > 0);
    const winRate = trades.length > 0 ? winningTrades.length / trades.length : 0;
    
    let regime: 'Trending' | 'Choppy' | 'Range-bound' = 'Choppy';
    if (winRate > 0.6) regime = 'Trending';
    else if (winRate < 0.4) regime = 'Choppy';
    else regime = 'Range-bound';
    
    // Market bias
    const longTrades = trades.filter(t => t.side === 'BUY');
    const shortTrades = trades.filter(t => t.side === 'SELL');
    let marketBias: 'bullish' | 'bearish' | 'neutral' = 'neutral';
    if (longTrades.length > shortTrades.length * 1.5) marketBias = 'bullish';
    else if (shortTrades.length > longTrades.length * 1.5) marketBias = 'bearish';
    
    return {
      netPnL,
      netPnLPercent,
      totalTrades: trades.length,
      maxDrawdown,
      regime,
      marketBias,
      coherenceLevel: 'medium' as 'low' | 'medium' | 'high'
    };
  }
  
  private computeFieldIntelligence(lighthouseData: any): FieldIntelligence {
    const readings = lighthouseData.readings || [];
    
    if (readings.length === 0) {
      return {
        averageLighthouseIntensity: 0,
        coherenceBursts: 0,
        entropyTrend: 'stable',
        peakCoherenceTime: 'N/A',
        peakCoherenceValue: 0,
        fieldMood: 'chaotic chop'
      };
    }
    
    // Average lighthouse intensity
    const avgIntensity = readings.reduce((sum: number, r: any) => sum + (r.intensity || 0), 0) / readings.length;
    
    // Count coherence bursts (intensity > 0.7)
    const coherenceBursts = readings.filter((r: any) => (r.intensity || 0) > 0.7).length;
    
    // Find peak coherence
    const peak = readings.reduce((max: any, r: any) => 
      (r.intensity || 0) > (max.intensity || 0) ? r : max, 
      { intensity: 0, timestamp: 'N/A' }
    );
    
    // Entropy trend (simplified)
    const firstHalf = readings.slice(0, Math.floor(readings.length / 2));
    const secondHalf = readings.slice(Math.floor(readings.length / 2));
    const firstAvgEntropy = firstHalf.reduce((sum: number, r: any) => sum + (r.entropy || 0), 0) / firstHalf.length;
    const secondAvgEntropy = secondHalf.reduce((sum: number, r: any) => sum + (r.entropy || 0), 0) / secondHalf.length;
    
    let entropyTrend: 'rising' | 'falling' | 'stable' = 'stable';
    if (secondAvgEntropy > firstAvgEntropy * 1.1) entropyTrend = 'rising';
    else if (secondAvgEntropy < firstAvgEntropy * 0.9) entropyTrend = 'falling';
    
    // Field mood
    let fieldMood: FieldIntelligence['fieldMood'] = 'chaotic chop';
    if (avgIntensity > 0.75 && entropyTrend === 'falling') fieldMood = 'crystalline order';
    else if (avgIntensity > 0.6 && coherenceBursts > 3) fieldMood = 'directional flow';
    else if (avgIntensity > 0.4 && entropyTrend === 'falling') fieldMood = 'compressed spring';
    
    return {
      averageLighthouseIntensity: avgIntensity,
      coherenceBursts,
      entropyTrend,
      peakCoherenceTime: peak.timestamp,
      peakCoherenceValue: peak.intensity,
      fieldMood
    };
  }
  
  private computeEngineActivity(engineLogs: any): EngineActivity {
    const events = engineLogs.events || [];
    
    const signalsGenerated = events.filter((e: any) => e.type === 'signal_generated').length;
    const signalsExecuted = events.filter((e: any) => e.type === 'signal_executed').length;
    const killSwitchEvents = events.filter((e: any) => e.type === 'kill_switch').length;
    const rateLimitEvents = events.filter((e: any) => e.type === 'rate_limit').length;
    const dataLatencySpikes = events.filter((e: any) => e.type === 'latency_spike').length;
    
    // Calculate total kill switch duration
    const killSwitchDuration = events
      .filter((e: any) => e.type === 'kill_switch')
      .reduce((sum: number, e: any) => sum + (e.duration || 0), 0);
    
    return {
      signalsGenerated,
      signalsExecuted,
      killSwitchEvents,
      killSwitchDuration,
      rateLimitEvents,
      dataLatencySpikes
    };
  }
  
  private computeTradeBreakdown(trades: any[]): TradeBreakdown {
    const wins = trades.filter(t => (t.pnl || 0) > 0);
    const losses = trades.filter(t => (t.pnl || 0) < 0);
    
    // Average R:R
    const avgWin = wins.length > 0 ? wins.reduce((sum, t) => sum + t.pnl, 0) / wins.length : 0;
    const avgLoss = losses.length > 0 ? Math.abs(losses.reduce((sum, t) => sum + t.pnl, 0) / losses.length) : 1;
    const averageRR = avgLoss > 0 ? avgWin / avgLoss : 0;
    
    // Biggest winner/loser
    const biggestWinner = trades.length > 0 
      ? trades.reduce((max, t) => (t.pnl || 0) > (max.pnl || 0) ? t : max)
      : { symbol: 'N/A', pnl: 0 };
    const biggestLoser = trades.length > 0
      ? trades.reduce((min, t) => (t.pnl || 0) < (min.pnl || 0) ? t : min)
      : { symbol: 'N/A', pnl: 0 };
    
    // Top pairs
    const pairStats = new Map<string, { pnl: number; trades: number }>();
    for (const trade of trades) {
      const pair = trade.symbol || 'UNKNOWN';
      const current = pairStats.get(pair) || { pnl: 0, trades: 0 };
      pairStats.set(pair, {
        pnl: current.pnl + (trade.pnl || 0),
        trades: current.trades + 1
      });
    }
    
    const topPairs = Array.from(pairStats.entries())
      .map(([pair, stats]) => ({ pair, ...stats }))
      .sort((a, b) => b.pnl - a.pnl)
      .slice(0, 5);
    
    return {
      wins: wins.length,
      losses: losses.length,
      averageRR,
      biggestWinner: { pair: biggestWinner.symbol, pnl: biggestWinner.pnl },
      biggestLoser: { pair: biggestLoser.symbol, pnl: biggestLoser.pnl },
      topPairs
    };
  }
  
  private computeRiskAssessment(
    tactical: ReturnType<typeof this.computeTacticalSummary>,
    field: FieldIntelligence
  ): RiskAssessment {
    const recommendations: string[] = [];
    
    // Drawdown status
    let drawdownStatus: RiskAssessment['drawdownStatus'] = 'within limits';
    if (tactical.maxDrawdown > 15) drawdownStatus = 'exceeded threshold';
    else if (tactical.maxDrawdown > 10) drawdownStatus = 'approaching threshold';
    
    // Volatility level
    let volatilityLevel: RiskAssessment['volatilityLevel'] = 'medium';
    if (field.averageLighthouseIntensity > 0.8) volatilityLevel = 'extreme';
    else if (field.averageLighthouseIntensity > 0.6) volatilityLevel = 'high';
    else if (field.averageLighthouseIntensity < 0.3) volatilityLevel = 'low';
    
    // Generate recommendations
    if (drawdownStatus !== 'within limits') {
      recommendations.push('Consider reducing position size until drawdown recovers');
    }
    
    if (volatilityLevel === 'extreme' || volatilityLevel === 'high') {
      recommendations.push('High volatility detected - widen stops or reduce leverage');
    }
    
    if (field.entropyTrend === 'rising') {
      recommendations.push('Entropy increasing - expect choppier conditions, tighten risk management');
    }
    
    if (tactical.regime === 'Choppy' && tactical.totalTrades > 20) {
      recommendations.push('Choppy regime with high trade frequency - consider reducing trade cadence');
    }
    
    if (recommendations.length === 0) {
      recommendations.push('Risk parameters nominal - continue current strategy');
    }
    
    return {
      drawdownStatus,
      volatilityLevel,
      recommendations
    };
  }
  
  /**
   * Generate tactical orders for LION reconnaissance agents
   * The General tells the lions what to hunt for based on field conditions
   */
  private generateLionReconOrders(
    tactical: ReturnType<typeof this.computeTacticalSummary>,
    field: FieldIntelligence,
    trades: TradeBreakdown,
    risk: RiskAssessment
  ): LionReconOrders {
    const orders: LionReconOrders = {
      targetPairs: [],
      scanFrequency: 'normal',
      entryThreshold: 0.5,
      exitStrategy: 'normal',
      positionSize: 'normal',
      focusAreas: [],
      avoidConditions: [],
      tacticalDirective: ''
    };
    
    // Determine target pairs from recent performance
    if (trades.topPairs.length > 0) {
      // Keep profitable pairs, investigate losing pairs cautiously
      orders.targetPairs = trades.topPairs
        .filter(p => p.pnl > 0 || p.trades < 3) // Winners or unexplored
        .map(p => p.pair)
        .slice(0, 5);
    }
    
    // If no good pairs, default majors
    if (orders.targetPairs.length === 0) {
      orders.targetPairs = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT'];
    }
    
    // === FIELD MOOD DIRECTIVES ===
    
    if (field.fieldMood === 'crystalline order') {
      // Perfect conditions - be aggressive
      orders.scanFrequency = 'aggressive';
      orders.entryThreshold = 0.6;
      orders.exitStrategy = 'wide';
      orders.positionSize = risk.drawdownStatus === 'within limits' ? 'increased' : 'normal';
      orders.focusAreas = [
        'Strong trending moves with sustained momentum',
        'Breakouts from consolidation with high volume',
        'Clear directional bias with low noise',
        'Multiple timeframe alignment'
      ];
      orders.avoidConditions = [
        'Counter-trend setups (field is trending)',
        'Range-bound patterns (field wants to move)'
      ];
      orders.tacticalDirective = '🦁 HUNT AGGRESSIVELY: Field is crystalline. This is rare. Exploit trending opportunities with confidence. Widen stops, let winners run. The field wants to move - let it.';
      
    } else if (field.fieldMood === 'directional flow') {
      // Good trending conditions
      orders.scanFrequency = 'normal';
      orders.entryThreshold = 0.5;
      orders.exitStrategy = 'normal';
      orders.positionSize = 'normal';
      orders.focusAreas = [
        'Momentum continuations in direction of flow',
        'Pullback entries in trending markets',
        'Breakout retests with volume confirmation',
        'Pairs showing strong relative strength'
      ];
      orders.avoidConditions = [
        'Low volume breakouts',
        'Reversal patterns against the flow',
        'Choppy intraday noise'
      ];
      orders.tacticalDirective = '🦁 STANDARD HUNT: Field has directional bias. Follow the flow, take pullback entries. Let trends develop. Stay disciplined.';
      
    } else if (field.fieldMood === 'compressed spring') {
      // Energy building - prepare for breakout
      orders.scanFrequency = 'conservative';
      orders.entryThreshold = 0.6;
      orders.exitStrategy = 'tight';
      orders.positionSize = 'reduced';
      orders.focusAreas = [
        'Tight consolidation patterns ready to break',
        'Volume compression zones',
        'Support/resistance tests with decreasing range',
        'Volatility contraction setups'
      ];
      orders.avoidConditions = [
        'Random breakout attempts without volume',
        'Mid-range entries (wait for edges)',
        'Low probability scalps'
      ];
      orders.tacticalDirective = '🦁 STALK PATIENTLY: Energy is building but not released yet. Watch for the spring to uncoil. Be patient, wait for confirmed breakouts. Don\'t chase phantoms.';
      
    } else {
      // Chaotic chop - be very defensive
      orders.scanFrequency = 'conservative';
      orders.entryThreshold = 0.7;
      orders.exitStrategy = 'tight';
      orders.positionSize = 'reduced';
      orders.focusAreas = [
        'Only extreme high-probability setups',
        'Strong support/resistance bounces with confirmation',
        'Mean reversion at significant levels',
        'Pairs with clear structure despite chaos'
      ];
      orders.avoidConditions = [
        'Breakout attempts (likely to fail)',
        'Trend-following entries (no trends present)',
        'Low timeframe noise',
        'Unconfirmed signals'
      ];
      orders.tacticalDirective = '🦁 DEFENSIVE POSTURE: Field is chaotic. Reduce activity. Only hunt when prey is obvious and isolated. Tight stops, quick exits. Preserve capital for better hunting grounds.';
    }
    
    // === ENTROPY ADJUSTMENTS ===
    
    if (field.entropyTrend === 'rising') {
      orders.focusAreas.push('Expect increasing chop - prioritize quick scalps over swings');
      orders.exitStrategy = 'tight';
    } else if (field.entropyTrend === 'falling') {
      orders.focusAreas.push('Entropy falling - conditions improving for sustained moves');
    }
    
    // === VOLATILITY ADJUSTMENTS ===
    
    if (risk.volatilityLevel === 'extreme') {
      orders.positionSize = 'reduced';
      orders.avoidConditions.push('Extreme volatility - reduce size by 50%');
      orders.tacticalDirective = '⚠️ ' + orders.tacticalDirective + ' VOLATILITY EXTREME - HALF POSITION SIZES.';
    } else if (risk.volatilityLevel === 'high') {
      orders.avoidConditions.push('High volatility - widen stops or reduce leverage');
    }
    
    // === DRAWDOWN ADJUSTMENTS ===
    
    if (risk.drawdownStatus === 'exceeded threshold') {
      orders.scanFrequency = 'conservative';
      orders.positionSize = 'reduced';
      orders.tacticalDirective = '🚨 DRAWDOWN RECOVERY MODE: ' + orders.tacticalDirective + ' Focus on capital preservation. Only A+ setups.';
    } else if (risk.drawdownStatus === 'approaching threshold') {
      orders.focusAreas.push('Drawdown approaching limit - tighten risk on next trades');
    }
    
    // === REGIME ADJUSTMENTS ===
    
    if (tactical.regime === 'Choppy' && tactical.totalTrades > 20) {
      orders.scanFrequency = 'conservative';
      orders.avoidConditions.push('High trade frequency in chop - reduce activity');
    }
    
    // === PERFORMANCE FEEDBACK ===
    
    if (trades.wins > 0 && trades.losses > 0) {
      const winRate = trades.wins / (trades.wins + trades.losses);
      if (winRate < 0.4) {
        orders.focusAreas.push('Win rate low - be more selective, wait for stronger confirmations');
      } else if (winRate > 0.6) {
        orders.focusAreas.push('Win rate solid - current strategy working well');
      }
    }
    
    if (trades.averageRR < 1.5) {
      orders.focusAreas.push('R:R below target - let winners run longer or tighten entries');
    }
    
    return orders;
  }
  
  private determineFieldStatus(
    field: FieldIntelligence,
    tactical: ReturnType<typeof this.computeTacticalSummary>
  ): WarRoomBrief['fieldStatus'] {
    if (field.averageLighthouseIntensity > 0.7 && field.coherenceBursts > 5) {
      return 'Coherent';
    } else if (field.averageLighthouseIntensity > 0.5) {
      return 'Volatile';
    } else if (field.entropyTrend === 'falling' && field.fieldMood === 'compressed spring') {
      return 'Compressed';
    } else {
      return 'Calm';
    }
  }
  
  private generateClosingMessage(
    field: FieldIntelligence,
    tactical: ReturnType<typeof this.computeTacticalSummary>
  ): string {
    const messages = [
      "Hive status: online. Field monitored. Coherence logged. Next cycle awaits.",
      "Field coherence captured. System nominal. The Hive watches.",
      "Quantum signatures archived. Market geometry mapped. Stand by.",
      "Lighthouse sweeps complete. Trajectories recorded. Hive remains vigilant.",
      "Intelligence gathered. Patterns recognized. Awaiting next field shift."
    ];
    
    // Choose based on field mood
    if (field.fieldMood === 'crystalline order') {
      return "Peak coherence achieved today. Field crystallized beautifully. Hive satisfied.";
    } else if (field.fieldMood === 'chaotic chop') {
      return "Choppy waters navigated. Not every day is coherent. Hive adapts.";
    } else if (tactical.netPnL > 0) {
      return "Profitable cycle completed. Coherence exploited efficiently. Hive pleased.";
    }
    
    return messages[Math.floor(Math.random() * messages.length)];
  }
  
  /**
   * Save brief to file
   */
  async saveBrief(brief: WarRoomBrief, outputDir = './reports'): Promise<string> {
    if (!fs.existsSync(outputDir)) {
      fs.mkdirSync(outputDir, { recursive: true });
    }
    
    const filename = `war_room_brief_${brief.date}_${brief.botName}.json`;
    const filepath = path.join(outputDir, filename);
    
    fs.writeFileSync(filepath, JSON.stringify(brief, null, 2));
    
    return filepath;
  }
  
  /**
   * Format brief as human-readable text
   */
  formatBriefAsText(brief: WarRoomBrief): string {
    const { fieldIntelligence: fi, engineActivity: ea, tradeBreakdown: tb, riskAssessment: ra, lionReconOrders: lion } = brief;
    
    return `
╔═══════════════════════════════════════════════════════════════╗
║             WAR ROOM BRIEF – ISSUED BY THE HIVE               ║
╚═══════════════════════════════════════════════════════════════╝

Date: ${brief.date}
User: ${brief.user}
Bot: ${brief.botName}
Field Status: ${brief.fieldStatus}

─────────────────────────────────────────────────────────────────
🍯 THE HONEY POT 🍯
─────────────────────────────────────────────────────────────────

${brief.honeyPot ? `
Total Honey Collected: $${brief.honeyPot.totalHoney.toFixed(2)} (${brief.honeyPot.growthPercent >= 0 ? '+' : ''}${brief.honeyPot.growthPercent.toFixed(1)}%)
Current Balance: $${brief.honeyPot.currentBalance.toFixed(2)} (started with $${brief.honeyPot.initialBalance.toFixed(2)})
Win Rate: ${brief.honeyPot.winRate.toFixed(1)}% (${brief.honeyPot.winningTrades}W / ${brief.honeyPot.losingTrades}L)
Current Streak: ${brief.honeyPot.currentStreak > 0 ? '🔥' : ''}${brief.honeyPot.currentStreak}${brief.honeyPot.currentStreak > 0 ? ' 🔥' : ''}
Best Streak: ${brief.honeyPot.bestStreak} trades
Biggest Win: $${brief.honeyPot.biggestWin.toFixed(2)}
` : 'Honey pot not initialized'}

─────────────────────────────────────────────────────────────────
TACTICAL SUMMARY
─────────────────────────────────────────────────────────────────

Net PnL: ${brief.netPnL >= 0 ? '+' : ''}$${brief.netPnL.toFixed(2)} (${brief.netPnLPercent >= 0 ? '+' : ''}${brief.netPnLPercent.toFixed(2)}%)
Trades: ${brief.totalTrades}
Max Drawdown: ${brief.maxDrawdown.toFixed(2)}%
Regime: ${brief.regime}

Today the field leaned ${brief.marketBias} with ${brief.coherenceLevel} coherence.

─────────────────────────────────────────────────────────────────
FIELD INTELLIGENCE (Quantum Vibes)
─────────────────────────────────────────────────────────────────

Average Lighthouse Intensity: ${fi.averageLighthouseIntensity.toFixed(3)}
Coherence Bursts: ${fi.coherenceBursts}
Entropy Trend: ${fi.entropyTrend}
Peak Coherence: ${fi.peakCoherenceValue.toFixed(3)} at ${fi.peakCoherenceTime}

Lighthouse readings peaked at ${fi.peakCoherenceValue.toFixed(2)} during ${fi.peakCoherenceTime}.
${fi.entropyTrend === 'falling' 
  ? 'Entropy fell, suggesting a transition from noise to order.' 
  : fi.entropyTrend === 'rising' 
    ? 'Entropy rose, indicating increasing market chaos.'
    : 'Entropy remained stable.'
}

Hive reading: ${fi.fieldMood}.

─────────────────────────────────────────────────────────────────
ENGINE ACTIVITY
─────────────────────────────────────────────────────────────────

Signals: ${ea.signalsGenerated} generated, ${ea.signalsExecuted} executed.
${ea.rateLimitEvents > 0 ? `Rate-limit events: ${ea.rateLimitEvents}` : 'No rate-limit events.'}
${ea.killSwitchEvents > 0 
  ? `Kill-switch engaged ${ea.killSwitchEvents} time(s) for ${ea.killSwitchDuration} minutes total.`
  : 'No kill-switch events.'
}
${ea.dataLatencySpikes > 0 ? `Data latency spikes: ${ea.dataLatencySpikes}` : ''}

─────────────────────────────────────────────────────────────────
PERFORMANCE BREAKDOWN
─────────────────────────────────────────────────────────────────

Wins: ${tb.wins} | Losses: ${tb.losses}
Win Rate: ${brief.totalTrades > 0 ? ((tb.wins / brief.totalTrades) * 100).toFixed(1) : '0'}%
Average R:R: ${tb.averageRR.toFixed(2)}
Biggest Winner: ${tb.biggestWinner.pair} (+$${tb.biggestWinner.pnl.toFixed(2)})
Biggest Loser: ${tb.biggestLoser.pair} ($${tb.biggestLoser.pnl.toFixed(2)})

Top Pairs:
${tb.topPairs.map(p => `  ${p.pair}: $${p.pnl.toFixed(2)} (${p.trades} trades)`).join('\n')}

─────────────────────────────────────────────────────────────────
RISK & RECOMMENDATIONS
─────────────────────────────────────────────────────────────────

Drawdown Status: ${ra.drawdownStatus}
Volatility Level: ${ra.volatilityLevel}

Recommendations:
${ra.recommendations.map(r => `  • ${r}`).join('\n')}

─────────────────────────────────────────────────────────────────
🦁 LION RECONNAISSANCE ORDERS 🦁
─────────────────────────────────────────────────────────────────

TACTICAL DIRECTIVE:
${lion.tacticalDirective}

Target Pairs: ${lion.targetPairs.join(', ')}
Scan Frequency: ${lion.scanFrequency.toUpperCase()}
Entry Threshold: ${lion.entryThreshold.toFixed(2)} (minimum lighthouse intensity)
Exit Strategy: ${lion.exitStrategy.toUpperCase()}
Position Size: ${lion.positionSize.toUpperCase()}

FOCUS AREAS (What to hunt):
${lion.focusAreas.map(a => `  ✓ ${a}`).join('\n')}

AVOID CONDITIONS (What to ignore):
${lion.avoidConditions.map(a => `  ✗ ${a}`).join('\n')}

─────────────────────────────────────────────────────────────────
CLOSING
─────────────────────────────────────────────────────────────────

${brief.closingMessage}

Hive Status: ${brief.hiveStatus.toUpperCase()}

╔═══════════════════════════════════════════════════════════════╗
║                    End of War Room Brief                      ║
╚═══════════════════════════════════════════════════════════════╝
`;
  }
}

// Export convenience function
export async function generateWarRoomBrief(
  date: Date = new Date(),
  user: string = 'Trader',
  botName: string = 'AUREON-PRIME'
): Promise<WarRoomBrief> {
  const reporter = new HiveWarRoomReporter();
  return reporter.generateBrief(date, user, botName);
}
