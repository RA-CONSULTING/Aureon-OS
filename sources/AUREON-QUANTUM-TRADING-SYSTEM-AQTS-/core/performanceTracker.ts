import { ExecutionReport } from './executionEngine';
import { RiskAdjustedOrder } from './riskManagement';

export interface PerformanceMetrics {
  realizedPnl: number;
  unrealizedPnl: number;
  totalTrades: number;
  wins: number;
  sharpe: number;
  maxDrawdown: number;
}

export interface PerformanceSnapshot extends PerformanceMetrics {
  timestamp: number;
}

export class PerformanceTracker {
  private metrics: PerformanceMetrics = {
    realizedPnl: 0,
    unrealizedPnl: 0,
    totalTrades: 0,
    wins: 0,
    sharpe: 0,
    maxDrawdown: 0,
  };

  private returns: number[] = [];

  update(report: ExecutionReport, order: RiskAdjustedOrder, markPrice: number): PerformanceSnapshot {
    const directionMultiplier = order.direction === 'long' ? 1 : -1;
    const entry = report.averagePrice;
    const positionReturn = ((markPrice - entry) / entry) * directionMultiplier;
    const pnl = positionReturn * order.notional;

    this.metrics.realizedPnl += pnl;
    this.metrics.totalTrades += 1;
    if (pnl > 0) {
      this.metrics.wins += 1;
    }

    this.returns.push(positionReturn);
    if (this.returns.length > 100) {
      this.returns.shift();
    }

    const avg = this.returns.reduce((a, b) => a + b, 0) / this.returns.length;
    const variance = this.returns.reduce((a, b) => a + (b - avg) ** 2, 0) / this.returns.length;
    const std = Math.sqrt(variance);
    this.metrics.sharpe = std === 0 ? 0 : (avg * Math.sqrt(365)) / std;

    const drawdownCandidate = Math.max(0, -positionReturn);
    this.metrics.maxDrawdown = Math.max(this.metrics.maxDrawdown, drawdownCandidate);

    return {
      timestamp: Date.now(),
      ...this.metrics,
    };
  }
}
