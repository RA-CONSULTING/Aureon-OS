/** A live reading. Missing stays null. A real zero stays zero. */

const NUMERIC_TEXT = /^[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?$/;

export function finiteOrNull(value: unknown): number | null {
  if (typeof value === 'number') return Number.isFinite(value) ? value : null;
  if (typeof value !== 'string') return null;
  const trimmed = value.trim();
  if (!trimmed || !NUMERIC_TEXT.test(trimmed)) return null;
  const num = Number(trimmed);
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

export type MoneyBook = {
  name: string;
  /** Null when the feed did not name a currency. Do not guess one. */
  currency: string | null;
  amount: number | null;
};

export type BookTotal = {
  total: number | null;
  currency: string | null;
  missing: string[];
  note: string;
};

/**
 * A combined total exists only when every book was read and they share one
 * labelled currency. No conversion is applied. A missing book is named.
 * A reported zero is kept inside a book and inside a same-currency total.
 */
export function combineBookTotals(books: MoneyBook[]): BookTotal {
  const missing = books.filter((book) => book.amount == null).map((book) => book.name);
  if (missing.length > 0) {
    return {
      total: null,
      currency: null,
      missing,
      note: `${missing.join(' and ')} unavailable`,
    };
  }
  const currencies = books.map((book) => (book.currency == null ? '' : book.currency.trim()));
  const sameCurrency = currencies.every((currency) => currency.length > 0) && new Set(currencies).size === 1;
  if (!sameCurrency) {
    return { total: null, currency: null, missing: [], note: 'unavailable' };
  }
  return {
    total: books.reduce((sum, book) => sum + (book.amount as number), 0),
    currency: currencies[0],
    missing: [],
    note: '',
  };
}

/**
 * One portfolio figure from the book that reported.
 * A Kraken equity of exactly 0 is a real reading, so it is kept and Capital
 * is not substituted for it. Capital is used only when Kraken did not report.
 * A non-empty equity note withholds the figure.
 */
export function selectEquity(
  equityNote: string,
  kraken: number | null,
  capital: number | null,
): number | null {
  if (equityNote) return null;
  if (kraken != null) return kraken;
  return capital;
}

/** Kraken's own pool. A missing pool is not replaced by another book or a combined total. */
export function krakenPoolAvailable(poolAvailable: number | null, freeMargin: number | null): number | null {
  if (poolAvailable != null) return poolAvailable;
  return freeMargin;
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
