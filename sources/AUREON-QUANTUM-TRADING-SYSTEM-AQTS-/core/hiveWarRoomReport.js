"use strict";
/**
 * HIVE WAR ROOM REPORT
 *
 * Daily intelligence packet from the AUREON hive mind.
 * Summarizes market behavior, engine activity, and field coherence.
 *
 * Position: Super Quantum Quackers General 🦆⚡
 */
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.HiveWarRoomReporter = void 0;
exports.generateWarRoomBrief = generateWarRoomBrief;
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
class HiveWarRoomReporter {
    constructor(metricsDir = './metrics', logsDir = './logs') {
        this.metricsDir = metricsDir;
        this.logsDir = logsDir;
    }
    /**
     * Generate a War Room Brief for a specific date
     */
    async generateBrief(date, user, botName) {
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
        const lionReconOrders = this.generateLionReconOrders(tacticalSummary, fieldIntelligence, tradeBreakdown, riskAssessment);
        // Determine field status
        const fieldStatus = this.determineFieldStatus(fieldIntelligence, tacticalSummary);
        // Generate closing message
        const closingMessage = this.generateClosingMessage(fieldIntelligence, tacticalSummary);
        return {
            date: dateStr,
            user,
            botName,
            fieldStatus,
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
    async loadTradeData(date) {
        try {
            const tradePath = path.join(this.logsDir, `trades_${date}.json`);
            if (fs.existsSync(tradePath)) {
                const data = fs.readFileSync(tradePath, 'utf-8');
                return JSON.parse(data);
            }
        }
        catch (error) {
            console.warn(`No trade data for ${date}`);
        }
        return [];
    }
    async loadLighthouseData(date) {
        try {
            const metricsPath = path.join(this.metricsDir, `lighthouse_${date}.json`);
            if (fs.existsSync(metricsPath)) {
                const data = fs.readFileSync(metricsPath, 'utf-8');
                return JSON.parse(data);
            }
        }
        catch (error) {
            console.warn(`No lighthouse data for ${date}`);
        }
        return { readings: [] };
    }
    async loadEngineLogs(date) {
        try {
            const logPath = path.join(this.logsDir, `engine_${date}.json`);
            if (fs.existsSync(logPath)) {
                const data = fs.readFileSync(logPath, 'utf-8');
                return JSON.parse(data);
            }
        }
        catch (error) {
            console.warn(`No engine logs for ${date}`);
        }
        return { events: [] };
    }
    computeTacticalSummary(trades) {
        const netPnL = trades.reduce((sum, t) => sum + (t.pnl || 0), 0);
        const initialBalance = 10000; // Should come from config
        const netPnLPercent = (netPnL / initialBalance) * 100;
        // Compute drawdown
        let peak = initialBalance;
        let maxDrawdown = 0;
        let running = initialBalance;
        for (const trade of trades) {
            running += trade.pnl || 0;
            if (running > peak)
                peak = running;
            const dd = ((peak - running) / peak) * 100;
            if (dd > maxDrawdown)
                maxDrawdown = dd;
        }
        // Determine regime
        const winningTrades = trades.filter(t => (t.pnl || 0) > 0);
        const winRate = trades.length > 0 ? winningTrades.length / trades.length : 0;
        let regime = 'Choppy';
        if (winRate > 0.6)
            regime = 'Trending';
        else if (winRate < 0.4)
            regime = 'Choppy';
        else
            regime = 'Range-bound';
        // Market bias
        const longTrades = trades.filter(t => t.side === 'BUY');
        const shortTrades = trades.filter(t => t.side === 'SELL');
        let marketBias = 'neutral';
        if (longTrades.length > shortTrades.length * 1.5)
            marketBias = 'bullish';
        else if (shortTrades.length > longTrades.length * 1.5)
            marketBias = 'bearish';
        return {
            netPnL,
            netPnLPercent,
            totalTrades: trades.length,
            maxDrawdown,
            regime,
            marketBias,
            coherenceLevel: 'medium'
        };
    }
    computeFieldIntelligence(lighthouseData) {
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
        const avgIntensity = readings.reduce((sum, r) => sum + (r.intensity || 0), 0) / readings.length;
        // Count coherence bursts (intensity > 0.7)
        const coherenceBursts = readings.filter((r) => (r.intensity || 0) > 0.7).length;
        // Find peak coherence
        const peak = readings.reduce((max, r) => (r.intensity || 0) > (max.intensity || 0) ? r : max, { intensity: 0, timestamp: 'N/A' });
        // Entropy trend (simplified)
        const firstHalf = readings.slice(0, Math.floor(readings.length / 2));
        const secondHalf = readings.slice(Math.floor(readings.length / 2));
        const firstAvgEntropy = firstHalf.reduce((sum, r) => sum + (r.entropy || 0), 0) / firstHalf.length;
        const secondAvgEntropy = secondHalf.reduce((sum, r) => sum + (r.entropy || 0), 0) / secondHalf.length;
        let entropyTrend = 'stable';
        if (secondAvgEntropy > firstAvgEntropy * 1.1)
            entropyTrend = 'rising';
        else if (secondAvgEntropy < firstAvgEntropy * 0.9)
            entropyTrend = 'falling';
        // Field mood
        let fieldMood = 'chaotic chop';
        if (avgIntensity > 0.75 && entropyTrend === 'falling')
            fieldMood = 'crystalline order';
        else if (avgIntensity > 0.6 && coherenceBursts > 3)
            fieldMood = 'directional flow';
        else if (avgIntensity > 0.4 && entropyTrend === 'falling')
            fieldMood = 'compressed spring';
        return {
            averageLighthouseIntensity: avgIntensity,
            coherenceBursts,
            entropyTrend,
            peakCoherenceTime: peak.timestamp,
            peakCoherenceValue: peak.intensity,
            fieldMood
        };
    }
    computeEngineActivity(engineLogs) {
        const events = engineLogs.events || [];
        const signalsGenerated = events.filter((e) => e.type === 'signal_generated').length;
        const signalsExecuted = events.filter((e) => e.type === 'signal_executed').length;
        const killSwitchEvents = events.filter((e) => e.type === 'kill_switch').length;
        const rateLimitEvents = events.filter((e) => e.type === 'rate_limit').length;
        const dataLatencySpikes = events.filter((e) => e.type === 'latency_spike').length;
        // Calculate total kill switch duration
        const killSwitchDuration = events
            .filter((e) => e.type === 'kill_switch')
            .reduce((sum, e) => sum + (e.duration || 0), 0);
        return {
            signalsGenerated,
            signalsExecuted,
            killSwitchEvents,
            killSwitchDuration,
            rateLimitEvents,
            dataLatencySpikes
        };
    }
    computeTradeBreakdown(trades) {
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
        const pairStats = new Map();
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
    computeRiskAssessment(tactical, field) {
        const recommendations = [];
        // Drawdown status
        let drawdownStatus = 'within limits';
        if (tactical.maxDrawdown > 15)
            drawdownStatus = 'exceeded threshold';
        else if (tactical.maxDrawdown > 10)
            drawdownStatus = 'approaching threshold';
        // Volatility level
        let volatilityLevel = 'medium';
        if (field.averageLighthouseIntensity > 0.8)
            volatilityLevel = 'extreme';
        else if (field.averageLighthouseIntensity > 0.6)
            volatilityLevel = 'high';
        else if (field.averageLighthouseIntensity < 0.3)
            volatilityLevel = 'low';
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
    generateLionReconOrders(tactical, field, trades, risk) {
        const orders = {
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
        }
        else if (field.fieldMood === 'directional flow') {
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
        }
        else if (field.fieldMood === 'compressed spring') {
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
        }
        else {
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
        }
        else if (field.entropyTrend === 'falling') {
            orders.focusAreas.push('Entropy falling - conditions improving for sustained moves');
        }
        // === VOLATILITY ADJUSTMENTS ===
        if (risk.volatilityLevel === 'extreme') {
            orders.positionSize = 'reduced';
            orders.avoidConditions.push('Extreme volatility - reduce size by 50%');
            orders.tacticalDirective = '⚠️ ' + orders.tacticalDirective + ' VOLATILITY EXTREME - HALF POSITION SIZES.';
        }
        else if (risk.volatilityLevel === 'high') {
            orders.avoidConditions.push('High volatility - widen stops or reduce leverage');
        }
        // === DRAWDOWN ADJUSTMENTS ===
        if (risk.drawdownStatus === 'exceeded threshold') {
            orders.scanFrequency = 'conservative';
            orders.positionSize = 'reduced';
            orders.tacticalDirective = '🚨 DRAWDOWN RECOVERY MODE: ' + orders.tacticalDirective + ' Focus on capital preservation. Only A+ setups.';
        }
        else if (risk.drawdownStatus === 'approaching threshold') {
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
            }
            else if (winRate > 0.6) {
                orders.focusAreas.push('Win rate solid - current strategy working well');
            }
        }
        if (trades.averageRR < 1.5) {
            orders.focusAreas.push('R:R below target - let winners run longer or tighten entries');
        }
        return orders;
    }
    determineFieldStatus(field, tactical) {
        if (field.averageLighthouseIntensity > 0.7 && field.coherenceBursts > 5) {
            return 'Coherent';
        }
        else if (field.averageLighthouseIntensity > 0.5) {
            return 'Volatile';
        }
        else if (field.entropyTrend === 'falling' && field.fieldMood === 'compressed spring') {
            return 'Compressed';
        }
        else {
            return 'Calm';
        }
    }
    generateClosingMessage(field, tactical) {
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
        }
        else if (field.fieldMood === 'chaotic chop') {
            return "Choppy waters navigated. Not every day is coherent. Hive adapts.";
        }
        else if (tactical.netPnL > 0) {
            return "Profitable cycle completed. Coherence exploited efficiently. Hive pleased.";
        }
        return messages[Math.floor(Math.random() * messages.length)];
    }
    /**
     * Save brief to file
     */
    async saveBrief(brief, outputDir = './reports') {
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
    formatBriefAsText(brief) {
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
                : 'Entropy remained stable.'}

Hive reading: ${fi.fieldMood}.

─────────────────────────────────────────────────────────────────
ENGINE ACTIVITY
─────────────────────────────────────────────────────────────────

Signals: ${ea.signalsGenerated} generated, ${ea.signalsExecuted} executed.
${ea.rateLimitEvents > 0 ? `Rate-limit events: ${ea.rateLimitEvents}` : 'No rate-limit events.'}
${ea.killSwitchEvents > 0
            ? `Kill-switch engaged ${ea.killSwitchEvents} time(s) for ${ea.killSwitchDuration} minutes total.`
            : 'No kill-switch events.'}
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
exports.HiveWarRoomReporter = HiveWarRoomReporter;
// Export convenience function
async function generateWarRoomBrief(date = new Date(), user = 'Trader', botName = 'AUREON-PRIME') {
    const reporter = new HiveWarRoomReporter();
    return reporter.generateBrief(date, user, botName);
}
