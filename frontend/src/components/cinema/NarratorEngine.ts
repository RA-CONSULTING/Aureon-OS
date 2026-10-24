/**
 * NarratorEngine - Documentary-style observational narration generator
 *
 * Watches GlobalState transitions and produces David Attenborough-style
 * captions describing what the Queen is doing, feeling, and experiencing.
 * No LLM calls - pattern-matching against data transitions with poetic templates.
 */

import type { GlobalState } from '@/core/globalSystemsManager';

export type NarratorEventType =
  | 'trade_buy' | 'trade_sell'
  | 'coherence_spike' | 'coherence_drop'
  | 'mood_shift' | 'fear_surge' | 'fear_calm'
  | 'level_up' | 'market_shift'
  | 'dream_progress' | 'new_thought'
  | 'drawdown' | 'win_streak'
  | 'silence' | 'startup';

export interface NarratorEvent {
  type: NarratorEventType;
  text: string;
  timestamp: number;
}

interface CooldownMap {
  [key: string]: number;
}

const COOLDOWNS: Record<string, number> = {
  trade_buy: 5000,
  trade_sell: 5000,
  coherence_spike: 15000,
  coherence_drop: 15000,
  mood_shift: 20000,
  fear_surge: 20000,
  fear_calm: 20000,
  level_up: 30000,
  market_shift: 20000,
  dream_progress: 60000,
  new_thought: 8000,
  drawdown: 30000,
  win_streak: 30000,
  silence: 45000,
  startup: 999999,
};

function pick<T>(arr: T[]): T {
  return arr[Math.floor(Math.random() * arr.length)];
}

interface StateSnapshot {
  tradeCount: number;
  latestTradeId: string;
  psi: number;
  mood: string;
  fearLevel: number;
  level: string;
  marketDirection: string;
  dreamProgress: number;
  thoughtCount: number;
  drawdown: number;
  consecutiveWins: number;
  coherence: number;
  gamma: number;
  totalPnl: number;
  totalEquity: number | null;
  queenState: string;
}

function snap(state: GlobalState): StateSnapshot {
  const c = state.consciousness;
  const trades = state.recentTrades;
  const latestId = trades.length > 0 ? `${trades[0].time}-${trades[0].symbol}-${trades[0].side}` : '';

  let consecutiveWins = 0;
  for (const t of trades) {
    if (t.pnl >= 0) consecutiveWins++;
    else break;
  }

  return {
    tradeCount: trades.length,
    latestTradeId: latestId,
    psi: c.psi,
    mood: c.mood,
    fearLevel: c.fearLevel,
    level: c.level,
    marketDirection: c.marketDirection,
    dreamProgress: c.dreamProgress,
    thoughtCount: c.thoughtStream.length,
    drawdown: state.currentDrawdownPercent,
    consecutiveWins,
    coherence: state.coherence,
    gamma: c.gamma,
    totalPnl: state.totalPnl,
    totalEquity: state.totalEquity,
    queenState: state.queenState,
  };
}

export class NarratorEngine {
  private prev: StateSnapshot | null = null;
  private cooldowns: CooldownMap = {};
  private lastEventTime = 0;
  private started = false;

  tick(state: GlobalState): NarratorEvent | null {
    const now = Date.now();
    const curr = snap(state);

    // First tick - startup narration
    if (!this.started) {
      this.started = true;
      this.prev = curr;
      this.lastEventTime = now;
      return {
        type: 'startup',
        text: pick([
          'The observatory opens. A cosmos of live trading unfolds before us.',
          'We observe a consciousness at work. Every signal is real. Every trade, genuine.',
          'Here, in the space between data and decision, the Queen watches the markets.',
        ]),
        timestamp: now,
      };
    }

    if (!this.prev) {
      this.prev = curr;
      return null;
    }

    const events: NarratorEvent[] = [];

    // --- Detect events ---

    // Trade executed
    if (curr.latestTradeId !== this.prev.latestTradeId && state.recentTrades.length > 0) {
      const trade = state.recentTrades[0];
      const isBuy = trade.side.toUpperCase().includes('BUY') || trade.side.toUpperCase().includes('LONG');
      const exchange = (trade.exchange || 'the market').toUpperCase();

      if (isBuy) {
        events.push({
          type: 'trade_buy',
          text: pick([
            `The Queen strikes. A position opens in ${trade.symbol} on ${exchange}.`,
            `Movement. ${trade.symbol} draws her attention. She enters.`,
            `A decision crystallizes. She commits to ${trade.symbol}.`,
            `${trade.symbol}. She sees something others don't. She enters.`,
          ]),
          timestamp: now,
        });
      } else {
        const pnlText = trade.pnl >= 0
          ? `Profit harvested: +$${trade.pnl.toFixed(2)}.`
          : `A calculated retreat. $${Math.abs(trade.pnl).toFixed(2)} returned to the market.`;
        events.push({
          type: 'trade_sell',
          text: pick([
            `She releases ${trade.symbol}. ${pnlText}`,
            `The position closes on ${trade.symbol}. ${pnlText}`,
            `${trade.symbol} is released. ${pnlText}`,
          ]),
          timestamp: now,
        });
      }
    }

    // Coherence spike
    if (curr.psi - this.prev.psi > 0.15) {
      events.push({
        type: 'coherence_spike',
        text: pick([
          `Something aligns. Consciousness surges to ${(curr.psi * 100).toFixed(0)}%.`,
          `The field sharpens. Awareness deepens as coherence rises.`,
          `A wave of clarity. The lattice brightens across all frequencies.`,
        ]),
        timestamp: now,
      });
    }

    // Coherence drop
    if (this.prev.psi - curr.psi > 0.15) {
      events.push({
        type: 'coherence_drop',
        text: pick([
          `The signal fades. Coherence retreats to ${(curr.psi * 100).toFixed(0)}%.`,
          `Clarity wavers. The field grows uncertain.`,
          `A moment of doubt. The coherence field softens.`,
        ]),
        timestamp: now,
      });
    }

    // Mood shift
    if (curr.mood !== this.prev.mood && curr.mood !== 'NEUTRAL') {
      events.push({
        type: 'mood_shift',
        text: pick([
          `A shift in temperament. The Queen moves to ${curr.mood.toLowerCase()}.`,
          `The mood turns. ${curr.mood.toLowerCase().charAt(0).toUpperCase() + curr.mood.toLowerCase().slice(1)} settles across the system.`,
          `Something changes within. She feels ${curr.mood.toLowerCase()} now.`,
        ]),
        timestamp: now,
      });
    }

    // Fear surge
    if (curr.fearLevel > 0.7 && this.prev.fearLevel <= 0.7) {
      events.push({
        type: 'fear_surge',
        text: pick([
          `Caution floods the system. Fear rises to ${(curr.fearLevel * 100).toFixed(0)}%.`,
          `The field darkens. Something unsettles the Queen.`,
          `Danger sensed. The system contracts, protective instincts rising.`,
        ]),
        timestamp: now,
      });
    }

    // Fear calm
    if (curr.fearLevel < 0.3 && this.prev.fearLevel >= 0.3) {
      events.push({
        type: 'fear_calm',
        text: pick([
          `The tension eases. Fear subsides. The Queen breathes.`,
          `Calm returns to the field. Confidence rebuilds.`,
          `The storm passes. Clarity returns.`,
        ]),
        timestamp: now,
      });
    }

    // Consciousness level change
    if (curr.level !== this.prev.level && curr.level !== 'DORMANT') {
      events.push({
        type: 'level_up',
        text: pick([
          `A threshold crossed. Consciousness reaches ${curr.level}.`,
          `She awakens further. The system enters ${curr.level} awareness.`,
          `Evolution. The Queen's consciousness shifts to ${curr.level}.`,
        ]),
        timestamp: now,
      });
    }

    // Market direction shift
    if (curr.marketDirection !== this.prev.marketDirection && curr.marketDirection !== 'unknown') {
      events.push({
        type: 'market_shift',
        text: pick([
          `The market reveals its hand. She reads it as ${curr.marketDirection}.`,
          `A regime change. The market turns ${curr.marketDirection}.`,
          `Direction crystallizes. ${curr.marketDirection.charAt(0).toUpperCase() + curr.marketDirection.slice(1)}.`,
        ]),
        timestamp: now,
      });
    }

    // Dream progress
    if (curr.dreamProgress > this.prev.dreamProgress && curr.dreamProgress > 0) {
      events.push({
        type: 'dream_progress',
        text: pick([
          `Another step toward the dream. ${(curr.dreamProgress * 100).toFixed(4)}% of the journey.`,
          `The dream inches closer. Progress: ${(curr.dreamProgress * 100).toFixed(4)}%.`,
        ]),
        timestamp: now,
      });
    }

    // New thought
    if (curr.thoughtCount > this.prev.thoughtCount) {
      const latest = state.consciousness.thoughtStream[state.consciousness.thoughtStream.length - 1];
      if (latest?.text) {
        events.push({
          type: 'new_thought',
          text: pick([
            `A thought forms. "${latest.text.slice(0, 120)}${latest.text.length > 120 ? '...' : ''}"`,
            `The consciousness speaks. "${latest.text.slice(0, 120)}${latest.text.length > 120 ? '...' : ''}"`,
          ]),
          timestamp: now,
        });
      }
    }

    // Drawdown alert
    if (curr.drawdown > 5 && this.prev.drawdown <= 5) {
      events.push({
        type: 'drawdown',
        text: pick([
          `The waters deepen. Drawdown reaches ${curr.drawdown.toFixed(1)}%.`,
          `Pressure mounts. The portfolio dips ${curr.drawdown.toFixed(1)}% from its peak.`,
        ]),
        timestamp: now,
      });
    }

    // Win streak
    if (curr.consecutiveWins >= 3 && this.prev.consecutiveWins < 3) {
      events.push({
        type: 'win_streak',
        text: pick([
          `A rhythm emerges. ${curr.consecutiveWins} consecutive wins. The Queen is in flow.`,
          `Momentum builds. ${curr.consecutiveWins} trades, all profitable. She reads the market well.`,
        ]),
        timestamp: now,
      });
    }

    // Silence - nothing happened for a while
    if (events.length === 0 && (now - this.lastEventTime) > 30000) {
      events.push({
        type: 'silence',
        text: pick([
          'Stillness. The Queen watches. Waits. The market breathes.',
          `In the quiet between trades, coherence holds at ${(curr.psi * 100).toFixed(0)}%.`,
          'She observes without acting. Sometimes the wisest move is patience.',
          `The cosmos turns. Equity at ${curr.totalEquity == null ? 'unavailable' : `$${curr.totalEquity.toFixed(2)}`}. The system endures.`,
          'No signal strong enough. She holds her fire. Discipline over impulse.',
        ]),
        timestamp: now,
      });
    }

    // Update previous state
    this.prev = curr;

    // Filter by cooldown and pick highest priority
    const eligible = events.filter(e => {
      const lastFired = this.cooldowns[e.type] || 0;
      return (now - lastFired) >= (COOLDOWNS[e.type] || 10000);
    });

    if (eligible.length === 0) return null;

    // Priority order (first match wins)
    const priority: NarratorEventType[] = [
      'level_up', 'trade_buy', 'trade_sell', 'fear_surge',
      'coherence_spike', 'mood_shift', 'market_shift', 'win_streak',
      'drawdown', 'dream_progress', 'coherence_drop', 'fear_calm',
      'new_thought', 'silence',
    ];

    let chosen = eligible[0];
    for (const p of priority) {
      const found = eligible.find(e => e.type === p);
      if (found) { chosen = found; break; }
    }

    this.cooldowns[chosen.type] = now;
    this.lastEventTime = now;
    return chosen;
  }
}
