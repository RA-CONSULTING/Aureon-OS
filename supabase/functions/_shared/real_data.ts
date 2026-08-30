export type TruthStatus = "live" | "real_derived" | "no_data";

export interface SourceProvenance {
  truthStatus: TruthStatus;
  sourceId: string;
  sourceUrl: string;
  collectedAt: string;
  sourceTimestamp?: string;
  freshnessAgeMs?: number;
  freshnessTtlMs: number;
}

export function requireFiniteNumber(value: unknown, field: string): number {
  const numberValue = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(numberValue)) {
    throw new Error(`LIVE_SOURCE_INVALID_NUMBER:${field}`);
  }
  return numberValue;
}

export function requireFreshTimestamp(
  sourceTimestamp: string,
  freshnessTtlMs: number,
  field = "sourceTimestamp",
): number {
  const epochMs = Date.parse(sourceTimestamp.endsWith("Z") ? sourceTimestamp : `${sourceTimestamp}Z`);
  if (!Number.isFinite(epochMs)) {
    throw new Error(`LIVE_SOURCE_INVALID_TIMESTAMP:${field}`);
  }
  const ageMs = Date.now() - epochMs;
  if (ageMs < -300_000 || ageMs > freshnessTtlMs) {
    throw new Error(`LIVE_SOURCE_STALE:${field}:age_ms=${ageMs}`);
  }
  return ageMs;
}

export async function fetchLiveJson<T>(url: string, timeoutMs = 15_000): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, {
      headers: { Accept: "application/json" },
      signal: controller.signal,
    });
    if (!response.ok) {
      throw new Error(`LIVE_SOURCE_HTTP:${response.status}:${url}`);
    }
    return await response.json() as T;
  } finally {
    clearTimeout(timeout);
  }
}

export function liveProvenance(
  sourceId: string,
  sourceUrl: string,
  sourceTimestamp: string,
  freshnessTtlMs: number,
): SourceProvenance {
  return {
    truthStatus: "live",
    sourceId,
    sourceUrl,
    collectedAt: new Date().toISOString(),
    sourceTimestamp,
    freshnessAgeMs: requireFreshTimestamp(sourceTimestamp, freshnessTtlMs),
    freshnessTtlMs,
  };
}

export function derivedProvenance(
  sourceId: string,
  sourceUrl: string,
  sourceTimestamp: string,
  freshnessTtlMs: number,
): SourceProvenance {
  return {
    ...liveProvenance(sourceId, sourceUrl, sourceTimestamp, freshnessTtlMs),
    truthStatus: "real_derived",
  };
}
