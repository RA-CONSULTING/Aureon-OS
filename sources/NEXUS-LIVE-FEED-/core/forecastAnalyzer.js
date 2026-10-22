import { readFile, readdir } from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const DEFAULT_DATA_DIR = path.resolve(__dirname, '..', 'data');
const DEFAULT_WINDOW_DAYS = 7;

const HAZARD_SEVERITY_SCALE = new Map(
  [
    ['background', 0],
    ['minimal', 0],
    ['low', 1],
    ['guarded', 1],
    ['moderate', 2],
    ['elevated', 2],
    ['considerable', 3],
    ['high', 3],
    ['very high', 4],
    ['extreme', 4],
    ['critical', 5],
  ].map(([key, value]) => [key, value])
);

const toNumber = (value) => {
  const parsed = Number.parseFloat(String(value));
  return Number.isFinite(parsed) ? parsed : null;
};

const safeDateValue = (value) => {
  const stamp = new Date(value).getTime();
  return Number.isFinite(stamp) ? stamp : null;
};

const pickLastUpdated = (entry) =>
  entry?.last_updated ?? entry?.validation?.last_synced_at ?? null;

const readJson = async (targetPath) => {
  if (!targetPath) {
    return [];
  }

  try {
    const raw = await readFile(targetPath, 'utf-8');
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch (error) {
    if (error.code === 'ENOENT') {
      return [];
    }
    throw error;
  }
};

const findLatestForecastFile = async (directory, prefix) => {
  try {
    const entries = await readdir(directory);
    const filtered = entries
      .filter((fileName) => fileName.startsWith(prefix) && fileName.endsWith('.json'))
      .sort();
    if (filtered.length === 0) {
      return null;
    }
    return path.join(directory, filtered[filtered.length - 1]);
  } catch (error) {
    if (error.code === 'ENOENT') {
      return null;
    }
    throw error;
  }
};

const sliceWindow = (entries, windowDays) => {
  if (!Array.isArray(entries)) {
    return [];
  }
  const sortable = entries
    .filter((entry) => entry?.date && safeDateValue(entry.date) !== null)
    .sort((a, b) => safeDateValue(a.date) - safeDateValue(b.date));
  if (!windowDays || sortable.length <= windowDays) {
    return sortable;
  }
  return sortable.slice(-windowDays);
};

const formatNumber = (value, fractionDigits = 1) => {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    return null;
  }
  return value.toFixed(fractionDigits);
};

const computeRange = (entries) => {
  if (!entries.length) {
    return { start: null, end: null };
  }
  return { start: entries[0].date ?? null, end: entries[entries.length - 1].date ?? null };
};

const computeLastUpdated = (entries) => {
  let latest = null;
  for (const entry of entries) {
    const candidate = pickLastUpdated(entry);
    if (!candidate) {
      continue;
    }
    if (!latest || new Date(candidate).getTime() > new Date(latest).getTime()) {
      latest = candidate;
    }
  }
  return latest;
};

const computeSolarWindTrend = (entries) => {
  const speeds = entries
    .map((entry) => toNumber(entry?.solar_field?.solar_wind_speed_km_s))
    .filter((value) => value !== null);
  if (speeds.length < 2) {
    return null;
  }
  const first = speeds[0];
  const last = speeds[speeds.length - 1];
  const delta = last - first;
  const direction = delta === 0 ? 'steady' : delta > 0 ? 'rising' : 'falling';
  return {
    direction,
    delta,
  };
};

const computeQuantumAnalysis = (entries) => {
  if (!entries.length) {
    return null;
  }

  const kpValues = entries
    .map((entry) => toNumber(entry?.solar_field?.kp_index))
    .filter((value) => value !== null);
  const averageKp = kpValues.length ? kpValues.reduce((sum, value) => sum + value, 0) / kpValues.length : null;
  const peakKp = kpValues.length ? Math.max(...kpValues) : null;

  let peakEntry = null;
  for (const entry of entries) {
    const kp = toNumber(entry?.solar_field?.kp_index) ?? -Infinity;
    if (!peakEntry || kp > (toNumber(peakEntry?.solar_field?.kp_index) ?? -Infinity)) {
      peakEntry = entry;
    }
  }

  const windTrend = computeSolarWindTrend(entries);
  const resonancePeaks = entries
    .map((entry) => toNumber(entry?.schumann_resonance?.tomsk_amplitude))
    .filter((value) => value !== null);
  const maxResonance = resonancePeaks.length ? Math.max(...resonancePeaks) : null;

  const auroraHighlights = entries
    .map((entry) => entry?.solar_field?.aurora_outlook)
    .filter((value, index, array) => typeof value === 'string' && value.trim().length > 0 && array.indexOf(value) === index)
    .slice(-3);

  const latestNarrative = entries[entries.length - 1]?.narrative ?? null;
  const latestGuidance = entries[entries.length - 1]?.nervous_system_guidance ?? null;

  const summaryFragments = [];
  if (averageKp !== null) {
    summaryFragments.push(`Average Kp index ${formatNumber(averageKp, 1)}`);
  }
  if (peakEntry?.solar_field?.storm_class) {
    summaryFragments.push(`peak storm class ${peakEntry.solar_field.storm_class}`);
  } else if (peakKp !== null) {
    summaryFragments.push(`peak Kp ${formatNumber(peakKp, 1)}`);
  }
  if (windTrend && windTrend.delta !== 0) {
    const sign = windTrend.delta > 0 ? '+' : '';
    summaryFragments.push(`solar wind ${windTrend.direction} ${sign}${Math.round(windTrend.delta)} km/s over the window`);
  }
  if (maxResonance !== null) {
    summaryFragments.push(`Schumann amplitude crest ${formatNumber(maxResonance, 2)}`);
  }

  const summary = summaryFragments.length
    ? `${summaryFragments.join('; ')}.`
    : 'Quantum telemetry steady across the seven-day horizon.';

  const metrics = [];
  if (averageKp !== null) {
    metrics.push({
      label: 'Average Kp Index',
      value: formatNumber(averageKp, 2),
      hint: 'Normalized across the 7-day quantum window.',
    });
  }
  if (peakEntry?.solar_field?.storm_class || peakKp !== null) {
    metrics.push({
      label: 'Peak Storm Activity',
      value: peakEntry?.solar_field?.storm_class ?? `Kp ${formatNumber(peakKp, 1)}`,
      hint: 'Highest geomagnetic excitation detected this cycle.',
    });
  }
  if (windTrend) {
    const sign = windTrend.delta > 0 ? '+' : '';
    metrics.push({
      label: 'Solar Wind Shift',
      value: `${sign}${Math.round(windTrend.delta)} km/s`,
      hint: `Field ${windTrend.direction} across seven days.`,
    });
  }
  if (maxResonance !== null) {
    metrics.push({
      label: 'Schumann Apex',
      value: formatNumber(maxResonance, 2),
      hint: 'Peak Tomsk amplitude recorded.',
    });
  }

  return {
    summary,
    metrics,
    highlights: auroraHighlights,
    latestNarrative,
    guidance: Array.isArray(latestGuidance) ? latestGuidance : null,
  };
};

const resolveHazardWeight = (level) => {
  if (typeof level !== 'string') {
    return null;
  }
  const normalized = level.trim().toLowerCase();
  if (!normalized) {
    return null;
  }
  return HAZARD_SEVERITY_SCALE.get(normalized) ?? null;
};

const computeBioLinearAnalysis = (entries) => {
  if (!entries.length) {
    return null;
  }

  const hazardAggregate = new Map();
  let totalConfidence = 0;
  let confidenceSamples = 0;
  let totalAlerts = 0;

  for (const entry of entries) {
    const hazards = entry?.hazard_ratings ?? {};
    for (const [key, rating] of Object.entries(hazards)) {
      const weight = resolveHazardWeight(rating?.level);
      const confidence = toNumber(rating?.confidence);
      const normalizedConfidence = confidence ?? 0.5;

      if (weight === null && !rating?.notes) {
        continue;
      }

      const existing = hazardAggregate.get(key) ?? {
        label: key,
        weightedSeverity: 0,
        samples: 0,
        latestLevel: rating?.level ?? null,
        confidenceSum: 0,
      };

      if (weight !== null) {
        existing.weightedSeverity += weight * normalizedConfidence;
      }
      if (confidence !== null) {
        existing.confidenceSum += confidence;
      }
      existing.samples += 1;
      if (rating?.level) {
        existing.latestLevel = rating.level;
      }
      hazardAggregate.set(key, existing);
    }

    totalAlerts += Array.isArray(entry?.alerts) ? entry.alerts.length : 0;

    const confidences = Object.values(hazards)
      .map((rating) => toNumber(rating?.confidence))
      .filter((value) => value !== null);
    for (const value of confidences) {
      totalConfidence += value;
      confidenceSamples += 1;
    }
  }

  const hazards = Array.from(hazardAggregate.values());
  hazards.sort((a, b) => b.weightedSeverity - a.weightedSeverity);
  const dominantHazard = hazards[0] ?? null;

  const averageConfidence = confidenceSamples ? totalConfidence / confidenceSamples : null;

  const summaryParts = [];
  if (dominantHazard) {
    summaryParts.push(
      `${dominantHazard.label.replace(/[_-]/g, ' ')} holding ${dominantHazard.latestLevel ?? 'steady'} levels`
    );
  }
  if (totalAlerts) {
    summaryParts.push(`${totalAlerts} alert bulletins issued`);
  }
  const summary = summaryParts.length
    ? `${summaryParts.join('; ')} across the seven-day bio-weather sweep.`
    : 'Bio-linear hazard field stable across the seven-day sweep.';

  const metrics = [];
  if (dominantHazard) {
    const label = dominantHazard.label
      .split(/[_-]/g)
      .map((token) => token.charAt(0).toUpperCase() + token.slice(1))
      .join(' ');
    const confidencePercent =
      dominantHazard.confidenceSum && dominantHazard.samples
        ? `${Math.round((dominantHazard.confidenceSum / dominantHazard.samples) * 100)}%`
        : undefined;
    metrics.push({
      label: 'Dominant Hazard',
      value: `${label}${dominantHazard.latestLevel ? ` · ${dominantHazard.latestLevel}` : ''}`,
      hint: confidencePercent ? `Mean confidence ${confidencePercent}.` : 'Weighted by 7-day readings.',
    });
  }
  if (averageConfidence !== null) {
    metrics.push({
      label: 'Average Confidence',
      value: `${Math.round(averageConfidence * 100)}%`,
      hint: 'Aggregate confidence across all hazard bands.',
    });
  }
  metrics.push({
    label: 'Alert Volume',
    value: `${totalAlerts}`,
    hint: 'Bulletins issued during the seven-day cycle.',
  });

  const highlightedAlerts = entries
    .flatMap((entry) => (Array.isArray(entry?.alerts) ? entry.alerts : []))
    .filter((value, index, array) => typeof value === 'string' && value.trim().length > 0 && array.indexOf(value) === index)
    .slice(0, 3);

  const preparedness = entries
    .flatMap((entry) => (Array.isArray(entry?.preparedness_actions) ? entry.preparedness_actions : []))
    .filter((value, index, array) => typeof value === 'string' && value.trim().length > 0 && array.indexOf(value) === index)
    .slice(0, 4);

  return {
    summary,
    metrics,
    highlights: highlightedAlerts,
    guidance: preparedness,
  };
};

const buildForecastWindow = (entries, windowDays, analyzer) => {
  const windowEntries = sliceWindow(entries, windowDays);
  return {
    entries: windowEntries,
    range: computeRange(windowEntries),
    lastUpdated: computeLastUpdated(windowEntries),
    analysis: analyzer(windowEntries),
  };
};

const buildQuantumReportWindow = (entries, windowDays) => {
  const windowEntries = sliceWindow(entries, windowDays);
  return {
    cycles: windowEntries,
    range: computeRange(windowEntries),
    lastUpdated: computeLastUpdated(windowEntries),
  };
};

export const loadForecastSummary = async ({ dataDir = DEFAULT_DATA_DIR, windowDays = DEFAULT_WINDOW_DAYS } = {}) => {
  const [quantumPath, bioLinearPath, quantumReportPath] = await Promise.all([
    findLatestForecastFile(dataDir, 'quantum_weather_forecast'),
    findLatestForecastFile(dataDir, 'bio_linear_disaster_outlook'),
    findLatestForecastFile(dataDir, 'quantum_weather_report_cycles'),
  ]);

  const [quantumEntries, bioLinearEntries, quantumReportEntries] = await Promise.all([
    readJson(quantumPath),
    readJson(bioLinearPath),
    readJson(quantumReportPath),
  ]);

  return {
    quantum: buildForecastWindow(quantumEntries, windowDays, computeQuantumAnalysis),
    bioLinear: buildForecastWindow(bioLinearEntries, windowDays, computeBioLinearAnalysis),
    quantumReport: buildQuantumReportWindow(quantumReportEntries, windowDays),
  };
};

export default {
  loadForecastSummary,
};
