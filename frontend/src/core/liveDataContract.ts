export type ProductionTruthStatus = 'live' | 'real_derived';

export interface DataProvenance {
  truthStatus: ProductionTruthStatus;
  sourceId: string;
  sourceTimestamp: string;
  generatedValues: false;
}

export const DEFAULT_LIVE_MAX_AGE_MS = 5 * 60 * 1000;

export function isFiniteNumber(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value);
}

export function assertFreshProvenance(
  value: DataProvenance,
  maxAgeMs = DEFAULT_LIVE_MAX_AGE_MS,
  nowMs = Date.now(),
): void {
  if (!value || !['live', 'real_derived'].includes(value.truthStatus)) {
    throw new Error('LIVE_DATA_REQUIRED: truthStatus must be live or real_derived');
  }
  if (!value.sourceId?.trim()) {
    throw new Error('LIVE_DATA_REQUIRED: sourceId is required');
  }
  if (value.generatedValues !== false) {
    throw new Error('LIVE_DATA_REQUIRED: generated values are forbidden');
  }

  const sourceTime = Date.parse(value.sourceTimestamp);
  const ageMs = nowMs - sourceTime;
  if (!Number.isFinite(sourceTime) || ageMs < -60_000 || ageMs > maxAgeMs) {
    throw new Error('LIVE_DATA_REQUIRED: source timestamp is invalid or stale');
  }
}

export function asDerivedProvenance(source: DataProvenance): DataProvenance {
  return {
    truthStatus: 'real_derived',
    sourceId: source.sourceId,
    sourceTimestamp: source.sourceTimestamp,
    generatedValues: false,
  };
}
