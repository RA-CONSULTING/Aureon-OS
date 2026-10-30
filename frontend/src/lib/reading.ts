/** A live reading. Missing stays null. A real zero stays zero. */

export function finiteOrNull(value: unknown): number | null {
  if (value === null || value === undefined || value === '') return null;
  const num = typeof value === 'number' ? value : Number(value);
  return Number.isFinite(num) ? num : null;
}

export function readingText(
  value: unknown,
  format: (n: number) => string = (n) => String(n),
): string {
  const num = finiteOrNull(value);
  return num == null ? 'unavailable' : format(num);
}

/** Sum only finite readings. An empty set is a real zero. Any missing part withholds the total. */
export function sumReadings(values: readonly unknown[]): number | null {
  if (values.length === 0) return 0;
  let sum = 0;
  for (const value of values) {
    const num = finiteOrNull(value);
    if (num == null) return null;
    sum += num;
  }
  return sum;
}

/**
 * Exchange books that were both read. A missing book does not become zero,
 * and a reported zero is kept. When only one book was read, that reading stands.
 */
export function combineBookTotals(...values: Array<number | null>): number | null {
  const present = values.filter((value): value is number => value != null && Number.isFinite(value));
  if (present.length === 0) return null;
  return present.reduce((sum, value) => sum + value, 0);
}

/** Prefer the first book that actually reported, including a genuine zero. */
export function selectEquity(
  equityNote: string,
  kraken: number | null,
  capital: number | null,
): number | null {
  if (equityNote) return null;
  if (kraken != null) return kraken;
  return capital;
}

export function equityReadingFromExchange(state: {
  truthStatus?: string | null;
  generatedValues?: boolean | null;
  totalEquityUsd?: unknown;
}): number | null {
  if (state.truthStatus !== 'real_derived' || state.generatedValues !== false) return null;
  return finiteOrNull(state.totalEquityUsd);
}

export function metricRingCaption(
  parts: Array<{ name: string; value: unknown }>,
): string | null {
  const missing = parts
    .filter((part) => finiteOrNull(part.value) == null)
    .map((part) => part.name);
  return missing.length ? `${missing.join(', ')} unavailable` : null;
}
