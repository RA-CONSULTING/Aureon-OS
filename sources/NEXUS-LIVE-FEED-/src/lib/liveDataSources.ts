import rawConfig from "@/data/liveDataSources.json";

export interface LiveDataSource {
  id: string;
  type: string;
  path: string;
  schema?: string;
}

export interface EnrichedLiveDataSource extends LiveDataSource {
  /** Human friendly label derived from the source identifier. */
  label: string;
  /** Update cadence (for example "1m") or `null` when no cadence is declared. */
  updateRate: string | null;
}

export interface LiveDataSourceRegistry {
  version: string;
  sources: EnrichedLiveDataSource[];
}

type RawConfig = {
  version?: unknown;
  sources?: unknown;
  update_rates?: unknown;
};

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null;

const toCleanString = (value: unknown): string | null => {
  if (typeof value !== "string") {
    return null;
  }
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
};

const formatIdentifier = (identifier: string): string =>
  identifier
    .split(/[_\s-]+/)
    .filter(Boolean)
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(" ") || identifier;

const parseUpdateRates = (raw: unknown): Record<string, string> => {
  if (!isRecord(raw)) {
    return {};
  }

  const entries: Array<[string, string]> = [];
  for (const [key, value] of Object.entries(raw)) {
    const cleanKey = toCleanString(key) ?? key;
    const cleanValue = toCleanString(value);
    if (cleanValue) {
      entries.push([cleanKey, cleanValue]);
    }
  }
  return Object.fromEntries(entries);
};

const parseSources = (raw: unknown): EnrichedLiveDataSource[] => {
  if (!Array.isArray(raw)) {
    return [];
  }

  return raw
    .map((entry, index) => {
      if (!isRecord(entry)) {
        return null;
      }

      const id = toCleanString(entry.id) ?? `source_${index + 1}`;
      const type = toCleanString(entry.type) ?? "unknown";
      const path = toCleanString(entry.path) ?? "Unavailable";
      const schema = toCleanString(entry.schema) ?? undefined;

      return {
        id,
        type,
        path,
        schema,
        label: formatIdentifier(id),
        updateRate: null,
      } satisfies EnrichedLiveDataSource;
    })
    .filter((entry): entry is EnrichedLiveDataSource => Boolean(entry));
};

const normaliseConfig = (config: RawConfig): LiveDataSourceRegistry => {
  const version = toCleanString(config.version) ?? "1.0";
  const sources = parseSources(config.sources);
  const updateRates = parseUpdateRates(config.update_rates);

  const enriched = sources.map((source) => ({
    ...source,
    updateRate: updateRates[source.id] ?? null,
  }));

  return {
    version,
    sources: enriched,
  };
};

const raw: RawConfig = rawConfig as RawConfig;

export const liveDataSourceRegistry: LiveDataSourceRegistry = normaliseConfig(raw);

export const getLiveDataSource = (id: string): EnrichedLiveDataSource | undefined =>
  liveDataSourceRegistry.sources.find((source) => source.id === id);

export default liveDataSourceRegistry;
