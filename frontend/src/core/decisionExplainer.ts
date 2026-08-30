/**
 * Decision Explainer Engine
 * Traces WHY each HOLD/BUY/SELL decision was made with human-readable reasoning
 */

import { unifiedBus } from './unifiedBus';

export type DecisionAction = 'BUY' | 'SELL' | 'HOLD';

export interface DecisionFactor {
  name: string;
  value: number;
  threshold: number;
  passed: boolean;
  weight: number;
  contribution: string;
}

export interface DecisionExplanation {
  id: string;
  timestamp: number;
  action: DecisionAction;
  confidence: number;
  factors: DecisionFactor[];
  reasoning: string[];
  summary: string;
  inputFrequency: number;
  outputFrequency: number;
  prismLevel: number;
  waveState: string;
  symbol: string;
}

export interface DecisionMetrics {
  coherence: number;
  lambda: number;
  lighthouseL: number;
  qgitaTier: number;
  qgitaConfidence: number;
  prismFrequency: number;
  prismLevel: number;
  waveState: string;
  harmonicLock: boolean;
  probabilityFused: number;
  sentimentScore: number;
  geometricAlignment: number;
}

class DecisionExplainerClass {
  private explanations: DecisionExplanation[] = [];
  private readonly maxHistory = 100;
  private listeners: Set<(explanation: DecisionExplanation) => void> = new Set();

  explain(metrics: DecisionMetrics, symbol: string = 'BTCUSDT'): DecisionExplanation {
    const factors: DecisionFactor[] = [];
    const reasoning: string[] = [];

    // Factor 1: Coherence Check
    const coherenceThreshold = 0.70;
    const coherencePassed = metrics.coherence >= coherenceThreshold;
    factors.push({
      name: 'Coherence (Γ)',
      value: metrics.coherence,
      threshold: coherenceThreshold,
      passed: coherencePassed,
      weight: 0.25,
      contribution: coherencePassed ? 'SUPPORTS trade' : 'BLOCKS trade'
    });
    reasoning.push(
      coherencePassed 
        ? `✓ Coherence ${(metrics.coherence * 100).toFixed(1)}% exceeds ${coherenceThreshold * 100}% threshold`
        : `✗ Coherence ${(metrics.coherence * 100).toFixed(1)}% below ${coherenceThreshold * 100}% threshold`
    );

    // Factor 2: Lighthouse Signal
    const lighthouseThreshold = 0.5;
    const lighthousePassed = metrics.lighthouseL >= lighthouseThreshold;
    factors.push({
      name: 'Lighthouse (L)',
      value: metrics.lighthouseL,
      threshold: lighthouseThreshold,
      passed: lighthousePassed,
      weight: 0.20,
      contribution: lighthousePassed ? 'SUPPORTS trade' : 'NEUTRAL'
    });
    reasoning.push(
      lighthousePassed
        ? `✓ Lighthouse signal ${metrics.lighthouseL.toFixed(3)} indicates opportunity`
        : `○ Lighthouse signal ${metrics.lighthouseL.toFixed(3)} is neutral`
    );

    // Factor 3: QGITA Tier
    const qgitaTierThreshold = 2;
    const qgitaPassed = metrics.qgitaTier <= qgitaTierThreshold && metrics.qgitaTier > 0;
    factors.push({
      name: 'QGITA Tier',
      value: metrics.qgitaTier,
      threshold: qgitaTierThreshold,
      passed: qgitaPassed,
      weight: 0.20,
      contribution: qgitaPassed ? `Tier ${metrics.qgitaTier} SUPPORTS` : 'LOW confidence'
    });
    reasoning.push(
      qgitaPassed
        ? `✓ QGITA Tier ${metrics.qgitaTier} with ${(metrics.qgitaConfidence * 100).toFixed(0)}% confidence`
        : `✗ QGITA Tier ${metrics.qgitaTier} insufficient (need Tier 1-2)`
    );

    // Factor 4: Prism Frequency Lock
    const prismLockThreshold = 500; // Near 528 Hz love frequency
    const prismLocked = metrics.prismFrequency >= prismLockThreshold && metrics.prismLevel >= 4;
    factors.push({
      name: 'Prism Lock',
      value: metrics.prismFrequency,
      threshold: prismLockThreshold,
      passed: prismLocked,
      weight: 0.15,
      contribution: prismLocked ? '528Hz ALIGNED' : 'FORMING'
    });
    reasoning.push(
      prismLocked
        ? `✓ Prism at ${metrics.prismFrequency.toFixed(0)}Hz (Level ${metrics.prismLevel}) - 528Hz lock`
        : `○ Prism at ${metrics.prismFrequency.toFixed(0)}Hz (Level ${metrics.prismLevel}) - transforming`
    );

    // Factor 5: 6D Wave State
    const bullishStates = ['ACCUMULATION', 'MARKUP', 'BULLISH'];
    const bearishStates = ['DISTRIBUTION', 'MARKDOWN', 'BEARISH'];
    const isBullish = bullishStates.includes(metrics.waveState.toUpperCase());
    const isBearish = bearishStates.includes(metrics.waveState.toUpperCase());
    factors.push({
      name: '6D Wave State',
      value: isBullish ? 1 : isBearish ? -1 : 0,
      threshold: 0,
      passed: isBullish || isBearish,
      weight: 0.10,
      contribution: isBullish ? 'BULLISH' : isBearish ? 'BEARISH' : 'NEUTRAL'
    });
    reasoning.push(
      `○ 6D Wave State: ${metrics.waveState} (${isBullish ? 'bullish' : isBearish ? 'bearish' : 'neutral'})`
    );

    // Factor 6: Harmonic Lock
    factors.push({
      name: 'Harmonic Lock',
      value: metrics.harmonicLock ? 1 : 0,
      threshold: 1,
      passed: metrics.harmonicLock,
      weight: 0.10,
      contribution: metrics.harmonicLock ? 'LOCKED' : 'UNLOCKED'
    });
    reasoning.push(
      metrics.harmonicLock
        ? `✓ Harmonic lock ACTIVE - enhanced confidence`
        : `○ Harmonic lock inactive`
    );

    // Calculate weighted decision
    let buyScore = 0;
    let sellScore = 0;

    // Coherence and Lighthouse must pass for any trade
    const canTrade = coherencePassed;

    if (canTrade) {
      // Direction from wave state and sentiment
      if (isBullish || metrics.sentimentScore > 0.1) {
        buyScore += 0.4;
      }
      if (isBearish || metrics.sentimentScore < -0.1) {
        sellScore += 0.4;
      }

      // QGITA confidence boost
      if (qgitaPassed) {
        const boost = metrics.qgitaConfidence * 0.3;
        if (metrics.probabilityFused > 0.5) buyScore += boost;
        else if (metrics.probabilityFused < 0.5) sellScore += boost;
      }

      // Prism lock boost
      if (prismLocked) {
        buyScore += 0.15;
      }

      // Harmonic lock boost
      if (metrics.harmonicLock) {
        if (buyScore > sellScore) buyScore += 0.1;
        else if (sellScore > buyScore) sellScore += 0.1;
      }
    }

    // Determine action
    let action: DecisionAction = 'HOLD';
    let confidence = 0;

    if (!canTrade) {
      action = 'HOLD';
      confidence = 1 - metrics.coherence; // High confidence in holding when coherence is low
      reasoning.push(`⚠ HOLD: Coherence below threshold - waiting for field alignment`);
    } else if (buyScore > sellScore && buyScore > 0.3) {
      action = 'BUY';
      confidence = Math.min(0.95, buyScore + (metrics.harmonicLock ? 0.1 : 0));
      reasoning.push(`→ BUY: Score ${(buyScore * 100).toFixed(0)}% > ${(sellScore * 100).toFixed(0)}%`);
    } else if (sellScore > buyScore && sellScore > 0.3) {
      action = 'SELL';
      confidence = Math.min(0.95, sellScore + (metrics.harmonicLock ? 0.1 : 0));
      reasoning.push(`→ SELL: Score ${(sellScore * 100).toFixed(0)}% > ${(buyScore * 100).toFixed(0)}%`);
    } else {
      action = 'HOLD';
      confidence = 0.5;
      reasoning.push(`→ HOLD: No clear direction (buy: ${(buyScore * 100).toFixed(0)}%, sell: ${(sellScore * 100).toFixed(0)}%)`);
    }

    // Build summary
    const summary = this.buildSummary(action, confidence, factors);

    const explanation: DecisionExplanation = {
      id: `decision-${Date.now()}-${crypto.randomUUID()}`,
      timestamp: Date.now(),
      action,
      confidence,
      factors,
      reasoning,
      summary,
      inputFrequency: metrics.prismFrequency * 0.8, // Approximate input
      outputFrequency: metrics.prismFrequency,
      prismLevel: metrics.prismLevel,
      waveState: metrics.waveState,
      symbol
    };

    // Store and notify
    this.explanations.unshift(explanation);
    if (this.explanations.length > this.maxHistory) {
      this.explanations.pop();
    }

    // Publish to bus
    unifiedBus.publish({
      systemName: 'DecisionExplainer',
      timestamp: Date.now(),
      ready: true,
      coherence: confidence,
      confidence,
      signal: action === 'BUY' ? 'BUY' : action === 'SELL' ? 'SELL' : 'NEUTRAL',
      data: { explanation }
    });

    // Notify listeners
    this.listeners.forEach(listener => listener(explanation));

    return explanation;
  }

  private buildSummary(action: DecisionAction, confidence: number, factors: DecisionFactor[]): string {
    const passedFactors = factors.filter(f => f.passed).length;
    const totalFactors = factors.length;

    if (action === 'BUY') {
      return `BUY signal with ${(confidence * 100).toFixed(0)}% confidence. ${passedFactors}/${totalFactors} factors aligned for long entry.`;
    } else if (action === 'SELL') {
      return `SELL signal with ${(confidence * 100).toFixed(0)}% confidence. ${passedFactors}/${totalFactors} factors aligned for short/exit.`;
    } else {
      return `HOLD - waiting for better conditions. ${passedFactors}/${totalFactors} factors aligned. Need stronger signal clarity.`;
    }
  }

  getExplanations(): DecisionExplanation[] {
    return [...this.explanations];
  }

  getLatest(): DecisionExplanation | null {
    return this.explanations[0] || null;
  }

  subscribe(listener: (explanation: DecisionExplanation) => void): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  clear(): void {
    this.explanations = [];
  }
}

export const decisionExplainer = new DecisionExplainerClass();
