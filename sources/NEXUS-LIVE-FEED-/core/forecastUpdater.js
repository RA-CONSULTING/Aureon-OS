import { readFile, writeFile, mkdir } from 'fs/promises';
import path from 'path';

const DEFAULT_WINDOW_DAYS = 7;

const ensureDirectory = async (targetPath) => {
  const dir = path.dirname(targetPath);
  await mkdir(dir, { recursive: true });
};

const readJsonArray = async (targetPath) => {
  try {
    const raw = await readFile(targetPath, 'utf-8');
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed)) {
      return parsed;
    }
    throw new Error(`Expected array in ${targetPath}`);
  } catch (error) {
    if (error.code === 'ENOENT') {
      return [];
    }
    throw error;
  }
};

const writeJsonArray = async (targetPath, payload) => {
  await ensureDirectory(targetPath);
  await writeFile(targetPath, `${JSON.stringify(payload, null, 2)}\n`, 'utf-8');
};

const toIsoDate = (value) => {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return null;
  }
  return date.toISOString();
};

const compareByDate = (a, b) => {
  const left = new Date(a.date).getTime();
  const right = new Date(b.date).getTime();
  return left - right;
};

const deepMerge = (base, incoming) => {
  if (incoming === undefined) {
    return base;
  }

  if (Array.isArray(base) || Array.isArray(incoming)) {
    return incoming;
  }

  if (base && typeof base === 'object' && incoming && typeof incoming === 'object') {
    const result = { ...base };
    for (const [key, value] of Object.entries(incoming)) {
      result[key] = deepMerge(base?.[key], value);
    }
    return result;
  }

  return incoming;
};

const normalizeEntry = (existingEntry, feedEntry, observedAtIso) => {
  const { observed_at: _ignoredObservedAt, validation = {}, ...rest } = feedEntry;
  const nextValidation = {
    ...existingEntry?.validation,
    ...validation,
    last_synced_at: observedAtIso,
  };

  const merged = deepMerge(existingEntry ?? {}, rest);
  return {
    ...merged,
    validation: nextValidation,
    last_updated: observedAtIso,
  };
};

const updateStream = async ({ forecastPath, feedPath, windowDays = DEFAULT_WINDOW_DAYS }) => {
  const [forecast, feed] = await Promise.all([
    readJsonArray(forecastPath),
    readJsonArray(feedPath),
  ]);

  const index = new Map(forecast.map((entry) => [entry.date, entry]));
  const stats = { added: 0, updated: 0, skipped: 0 };

  for (const feedEntry of feed) {
    if (!feedEntry?.date) {
      stats.skipped += 1;
      continue;
    }

    const observedAtIso = toIsoDate(feedEntry.observed_at) ?? new Date().toISOString();
    const existing = index.get(feedEntry.date);

    if (!existing) {
      const normalized = normalizeEntry(null, feedEntry, observedAtIso);
      index.set(feedEntry.date, normalized);
      stats.added += 1;
      continue;
    }

    const existingUpdatedAt = toIsoDate(existing.last_updated) ?? new Date(0).toISOString();
    if (new Date(observedAtIso) <= new Date(existingUpdatedAt)) {
      stats.skipped += 1;
      continue;
    }

    const normalized = normalizeEntry(existing, feedEntry, observedAtIso);
    index.set(feedEntry.date, normalized);
    stats.updated += 1;
  }

  const sorted = Array.from(index.values()).sort(compareByDate);
  const trimmed = sorted.slice(-windowDays);
  await writeJsonArray(forecastPath, trimmed);

  return {
    stats,
    windowDays,
    forecastPath,
    feedPath,
    totalEntries: trimmed.length,
    firstDate: trimmed[0]?.date ?? null,
    lastDate: trimmed[trimmed.length - 1]?.date ?? null,
  };
};

export const refreshForecasts = async (config) => {
  const results = [];
  if (config?.quantum) {
    results.push(await updateStream(config.quantum));
  }
  if (config?.bioLinear) {
    results.push(await updateStream(config.bioLinear));
  }
  return results;
};

export const startAutoRefresh = (config, { logger = console, intervalMs = 60 * 60 * 1000 } = {}) => {
  if (!config) {
    throw new Error('Auto refresh requires a configuration object.');
  }

  const runRefresh = async () => {
    try {
      const results = await refreshForecasts(config);
      for (const result of results) {
        logger.info?.(
          `[forecast-updater] ${path.basename(result.forecastPath)} -> window ${result.firstDate} – ${result.lastDate} ` +
            `(added ${result.stats.added}, updated ${result.stats.updated}, skipped ${result.stats.skipped})`
        );
      }
    } catch (error) {
      logger.error?.('[forecast-updater] refresh failed', error);
    }
  };

  runRefresh();
  return setInterval(runRefresh, intervalMs);
};

export default {
  refreshForecasts,
  startAutoRefresh,
};
