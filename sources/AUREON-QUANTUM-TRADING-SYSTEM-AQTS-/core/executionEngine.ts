import { DataIngestionSnapshot, ExchangeFeedSnapshot } from './dataIngestion';
import { RiskAdjustedOrder } from './riskManagement';

export interface ExecutionFill {
  exchange: string;
  price: number;
  size: number;
  latencyMs: number;
}

export interface ExecutionReport {
  success: boolean;
  fills: ExecutionFill[];
  averagePrice: number;
  slippage: number;
}

export interface ExecutionConfig {
  maxSlippageBps: number;
  latencyRange: {
    min: number;
    max: number;
  };
  partialFillProbability: number;
}

const DEFAULT_CONFIG: ExecutionConfig = {
  maxSlippageBps: 18,
  latencyRange: { min: 35, max: 125 },
  partialFillProbability: 0.15,
};

const chooseVenue = (feeds: ExchangeFeedSnapshot[], direction: 'long' | 'short') => {
  if (direction === 'long') {
    return feeds.reduce((best, current) => (current.price < best.price ? current : best), feeds[0]);
  }
  return feeds.reduce((best, current) => (current.price > best.price ? current : best), feeds[0]);
};

export class ExecutionEngine {
  private readonly config: ExecutionConfig;

  constructor(config: Partial<ExecutionConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config } satisfies ExecutionConfig;
  }

  execute(order: RiskAdjustedOrder, snapshot: DataIngestionSnapshot): ExecutionReport {
    const venue = chooseVenue(snapshot.exchangeFeeds, order.direction);
    const baseNoise = (Math.random() - 0.5) * venue.spread * snapshot.consolidatedOHLCV.close;
    const directionFactor = order.direction === 'long' ? 1 : -1;
    const constrainedNoise = Math.max(
      -this.config.maxSlippageBps / 10000,
      Math.min(this.config.maxSlippageBps / 10000, baseNoise / snapshot.consolidatedOHLCV.close)
    );
    const fillPrice = venue.price * (1 + constrainedNoise * directionFactor);

    const primarySize = order.notional / fillPrice;

    const latencyMs =
      this.config.latencyRange.min +
      Math.random() * (this.config.latencyRange.max - this.config.latencyRange.min);

    const fills: ExecutionFill[] = [
      { exchange: venue.exchange, price: fillPrice, size: primarySize, latencyMs },
    ];

    if (Math.random() < this.config.partialFillProbability) {
      const residual = primarySize * 0.25;
      const residualLatency = latencyMs + Math.random() * 40;
      const residualPrice = fillPrice * (1 + Math.random() * 0.0005 * directionFactor);
      fills.push({ exchange: venue.exchange, price: residualPrice, size: residual, latencyMs: residualLatency });
    }

    const totalNotional = fills.reduce((acc, fill) => acc + fill.price * fill.size, 0);
    const totalSize = fills.reduce((acc, fill) => acc + fill.size, 0);
    const averagePrice = totalNotional / totalSize;

    const midPrice = snapshot.consolidatedOHLCV.close;
    const slippage = (averagePrice - midPrice) / midPrice;

    return {
      success: true,
      fills,
      averagePrice,
      slippage,
    } satisfies ExecutionReport;
  }
}
