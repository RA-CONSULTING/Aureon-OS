import { AQTSOrchestrator } from './aqtsOrchestrator';
import { AQTSConfig, DeepPartial, defaultAQTSConfig, mergeConfig } from './config';
import { PerformanceSnapshot } from './performanceTracker';

export interface BacktestIterationResult {
  iteration: number;
  finalPerformance: PerformanceSnapshot | null;
  finalEquity: number;
  maxDrawdown: number;
  trades: number;
  winRate: number;
  sharpe: number;
  averageDecisionConfidence: number;
}

export interface BacktestSummary {
  config: AQTSConfig;
  iterations: BacktestIterationResult[];
  averages: {
    equity: number;
    drawdown: number;
    winRate: number;
    sharpe: number;
    confidence: number;
    trades: number;
  };
}

export interface BacktestOptions {
  iterations: number;
  steps: number;
  config?: DeepPartial<AQTSConfig>;
}

export const runBacktest = (options: BacktestOptions): BacktestSummary => {
  const { iterations, steps, config } = options;
  const overrides = config ?? {};
  const resolvedConfig = mergeConfig(defaultAQTSConfig, overrides);

  const results: BacktestIterationResult[] = [];

  for (let i = 0; i < iterations; i++) {
    const orchestrator = new AQTSOrchestrator(overrides);
    let finalPerformance: PerformanceSnapshot | null = null;
    let confidenceAccumulator = 0;
    let decisionCount = 0;

    for (let step = 0; step < steps; step++) {
      const output = orchestrator.next();
      confidenceAccumulator += output.decision.confidence;
      decisionCount += 1;
      if (output.performance) {
        finalPerformance = output.performance;
      }
    }

    const portfolio = orchestrator.getPortfolioState();
    const averageDecisionConfidence = decisionCount === 0 ? 0 : confidenceAccumulator / decisionCount;
    const trades = finalPerformance?.totalTrades ?? 0;
    const winRate = trades === 0 ? 0 : (finalPerformance?.wins ?? 0) / trades;

    results.push({
      iteration: i + 1,
      finalPerformance,
      finalEquity: portfolio.equity,
      maxDrawdown: portfolio.maxDrawdown,
      trades,
      winRate,
      sharpe: finalPerformance?.sharpe ?? 0,
      averageDecisionConfidence,
    });
  }

  const averages = results.reduce(
    (acc, result) => {
      acc.equity += result.finalEquity;
      acc.drawdown += result.maxDrawdown;
      acc.winRate += result.winRate;
      acc.sharpe += result.sharpe;
      acc.confidence += result.averageDecisionConfidence;
      acc.trades += result.trades;
      return acc;
    },
    { equity: 0, drawdown: 0, winRate: 0, sharpe: 0, confidence: 0, trades: 0 }
  );

  const divisor = Math.max(1, results.length);

  return {
    config: resolvedConfig,
    iterations: results,
    averages: {
      equity: averages.equity / divisor,
      drawdown: averages.drawdown / divisor,
      winRate: averages.winRate / divisor,
      sharpe: averages.sharpe / divisor,
      confidence: averages.confidence / divisor,
      trades: averages.trades / divisor,
    },
  } satisfies BacktestSummary;
};

