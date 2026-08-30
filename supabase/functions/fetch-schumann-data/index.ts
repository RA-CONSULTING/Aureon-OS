import { serve } from 'https://deno.land/std@0.168.0/http/server.ts';
import {
  fetchLiveJson,
  requireFiniteNumber,
  requireFreshTimestamp,
} from '../_shared/real_data.ts';

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};

const NOAA_KP_URL = 'https://services.swpc.noaa.gov/json/planetary_k_index_1m.json';
const MAX_SOURCE_AGE_MS = 20 * 60 * 1000;

type KpRow = { time_tag?: string; kp_index?: number | string; estimated_kp?: number | string };

function derivedFrequency(kp: number): number {
  return 7.83 + (kp - 3.0) * 0.015;
}

serve(async (req) => {
  if (req.method === 'OPTIONS') return new Response(null, { headers: corsHeaders });

  try {
    const rows = await fetchLiveJson<KpRow[]>(NOAA_KP_URL);
    if (!Array.isArray(rows) || rows.length === 0) throw new Error('NOAA_SWPC_KP_EMPTY');

    const valid = rows
      .map((row) => ({
        timestamp: row.time_tag ?? '',
        kp: Number(row.kp_index ?? row.estimated_kp),
      }))
      .filter((row) => row.timestamp && Number.isFinite(row.kp) && row.kp >= 0 && row.kp <= 9)
      .sort((a, b) => Date.parse(a.timestamp) - Date.parse(b.timestamp));
    if (valid.length === 0) throw new Error('NOAA_SWPC_KP_HAS_NO_VALID_ROWS');

    const latest = valid[valid.length - 1];
    requireFreshTimestamp(
      latest.timestamp,
      MAX_SOURCE_AGE_MS,
      'NOAA_SWPC_KP',
    );
    const sourceTimestamp = latest.timestamp;
    const kp = requireFiniteNumber(latest.kp, 'NOAA_SWPC_KP.kp');
    const disturbance = Math.max(0, Math.min(1, kp / 9));
    const quality = Math.max(0.35, 1 - disturbance * 0.65);
    const fundamentalHz = derivedFrequency(kp);
    const amplitude = Math.min(1, 0.60 + 0.05 * kp);
    const coherenceBoost = Math.max(0, (quality - 0.5) * 0.1);

    const recentFrequencies = valid
      .filter((row) => Date.parse(sourceTimestamp) - Date.parse(row.timestamp) <= 60 * 60 * 1000)
      .map((row) => derivedFrequency(row.kp));
    const mean = recentFrequencies.reduce((sum, value) => sum + value, 0) / recentFrequencies.length;
    const variance = recentFrequencies.reduce((sum, value) => sum + (value - mean) ** 2, 0) /
      recentFrequencies.length;

    const resonancePhase = amplitude > 0.85 && quality > 0.85 && disturbance < 0.2
      ? 'peak'
      : amplitude > 0.70 && quality > 0.75 && disturbance < 0.4
        ? 'elevated'
        : disturbance > 0.7 || quality < 0.5
          ? 'disturbed'
          : 'stable';

    const harmonics = [
      { frequency: fundamentalHz, amplitude, name: 'Fundamental (n=1)' },
      { frequency: 14.3 * (0.92 + disturbance * 0.08), amplitude: amplitude * 0.7, name: '2nd Mode (n=2)' },
      { frequency: 20.8 * (0.88 + disturbance * 0.12), amplitude: amplitude * 0.5, name: '3rd Mode (n=3)' },
      { frequency: 27.3 * (0.84 + disturbance * 0.16), amplitude: amplitude * 0.35, name: '4th Mode (n=4)' },
    ];

    return new Response(JSON.stringify({
      fundamentalHz,
      amplitude,
      quality,
      variance,
      coherenceBoost,
      resonancePhase,
      earthDisturbance: disturbance,
      harmonics,
      truthStatus: 'real_derived',
      sourceId: 'NOAA_SWPC_KP_DERIVED_SCHUMANN',
      sourceUrl: NOAA_KP_URL,
      sourceTimestamp,
      collectedAt: new Date().toISOString(),
      freshnessTtlSeconds: MAX_SOURCE_AGE_MS / 1000,
      generatedValues: false,
      derivation: 'Aureon HNC Schumann proxy from live NOAA planetary Kp; not a direct station measurement',
    }), { headers: { ...corsHeaders, 'Content-Type': 'application/json' } });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    console.error('[fetch-schumann-data] Live source failure:', message);
    return new Response(JSON.stringify({
      error: message,
      truthStatus: 'no_data',
      sourceId: 'NOAA_SWPC_KP_DERIVED_SCHUMANN',
      generatedValues: false,
    }), { status: 503, headers: { ...corsHeaders, 'Content-Type': 'application/json' } });
  }
});
