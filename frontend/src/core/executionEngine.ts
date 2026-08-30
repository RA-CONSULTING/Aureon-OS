import { DataIngestionSnapshot } from './dataIngestion';
import { RiskAdjustedOrder } from './riskManagement';

export interface ExecutionFill {
  exchange: string;
  price: number;
  size: number;
  latencyMs: number | null;
  providerFillId: string;
}

export interface ExecutionReport {
  success: boolean;
  fills: ExecutionFill[];
  averagePrice: number;
  slippage: number;
  providerOrderId: string;
  sourceId: string;
  sourceEventId: string;
  providerTimestamp: number;
  truthStatus: 'live';
  generated: false;
}

export interface ProviderExecutionReceipt {
  success: boolean;
  fills: ExecutionFill[];
  providerOrderId: string;
  sourceId: string;
  sourceEventId: string;
  providerTimestamp: number;
  generated: false;
}

export interface ExecutionConfig {
  maxSlippageBps: number;
  latencyRange: { min: number; max: number };
  partialFillProbability: number;
}

const DEFAULT_CONFIG: ExecutionConfig = {
  maxSlippageBps: 18,
  latencyRange: { min: 0, max: 0 },
  partialFillProbability: 0,
};

const timestampMs = (value: number): number => value < 10_000_000_000 ? value * 1000 : value;

/**
 * Validates provider receipts. Order placement belongs to the authenticated
 * exchange connector; this class never invents latency, slippage, partial
 * fills, or a successful execution.
 */
export class ExecutionEngine {
  private readonly config: ExecutionConfig;

  constructor(config: Partial<ExecutionConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
  }

  execute(_order: RiskAdjustedOrder, _snapshot: DataIngestionSnapshot): never {
    throw new Error('DIRECT_EXECUTION_RETIRED: invoke the authenticated exchange connector and record its receipt');
  }

  recordProviderExecution(
    order: RiskAdjustedOrder,
    snapshot: DataIngestionSnapshot,
    receipt: ProviderExecutionReceipt
  ): ExecutionReport {
    if (!receipt || receipt.generated !== false || !receipt.sourceId || !receipt.sourceEventId) {
      throw new Error('EXECUTION_RECEIPT_PROVENANCE_REQUIRED');
    }
    const providerTimestamp = timestampMs(receipt.providerTimestamp);
    const ageMs = Date.now() - providerTimestamp;
    if (ageMs < -30_000 || ageMs > 300_000) {
      throw new Error(`EXECUTION_RECEIPT_STALE:${ageMs}`);
    }
    if (!receipt.success || !receipt.providerOrderId || !receipt.fills.length) {
      throw new Error('EXECUTION_NOT_CONFIRMED_BY_PROVIDER');
    }
    for (const fill of receipt.fills) {
      if (!fill.exchange || !fill.providerFillId || !Number.isFinite(fill.price) || fill.price <= 0) {
        throw new Error('EXECUTION_FILL_INVALID');
      }
      if (!Number.isFinite(fill.size) || fill.size <= 0) {
        throw new Error('EXECUTION_FILL_SIZE_INVALID');
      }
    }
    const totalNotional = receipt.fills.reduce((sum, fill) => sum + fill.price * fill.size, 0);
    const totalSize = receipt.fills.reduce((sum, fill) => sum + fill.size, 0);
    const averagePrice = totalNotional / totalSize;
    const referencePrice = snapshot.consolidatedOHLCV.close;
    const direction = order.direction === 'long' ? 1 : -1;
    const slippage = ((averagePrice - referencePrice) / referencePrice) * direction;
    if (Math.abs(slippage) * 10_000 > this.config.maxSlippageBps) {
      throw new Error(`EXECUTION_SLIPPAGE_LIMIT_EXCEEDED:${slippage}`);
    }
    return {
      success: true,
      fills: receipt.fills,
      averagePrice,
      slippage,
      providerOrderId: receipt.providerOrderId,
      sourceId: receipt.sourceId,
      sourceEventId: receipt.sourceEventId,
      providerTimestamp,
      truthStatus: 'live',
      generated: false,
    };
  }
}
