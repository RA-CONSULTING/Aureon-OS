import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import {
  derivedProvenance,
  fetchLiveJson,
  liveProvenance,
  requireFiniteNumber,
} from "../_shared/real_data.ts";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

const NOAA_ROOT = "https://services.swpc.noaa.gov";
const WIND_URL = `${NOAA_ROOT}/json/rtsw/rtsw_wind_1m.json`;
const IMF_URL = `${NOAA_ROOT}/json/rtsw/rtsw_mag_1m.json`;
const GOES_MAG_URL = `${NOAA_ROOT}/json/goes/primary/magnetometers-6-hour.json`;
const KP_URL = `${NOAA_ROOT}/json/planetary_k_index_1m.json`;
const FORECAST_URL = `${NOAA_ROOT}/products/noaa-planetary-k-index-forecast.json`;
const TELEMETRY_TTL_MS = 20 * 60 * 1000;

type WindRow = {
  time_tag: string;
  active: boolean;
  source: string;
  proton_speed: number | null;
  proton_density: number | null;
  proton_temperature: number | null;
};

type ImfRow = {
  time_tag: string;
  active: boolean;
  source: string;
  bz_gsm: number | null;
};

type GoesMagRow = {
  time_tag: string;
  satellite: number;
  Hp: number | null;
  total: number | null;
  arcjet_flag: boolean;
};

type KpRow = {
  time_tag: string;
  estimated_kp: number | null;
};

type ForecastRow = {
  time_tag: string;
  kp: number | null;
  observed: string;
  noaa_scale: string | null;
};

function epoch(timestamp: string): number {
  return Date.parse(timestamp.endsWith("Z") ? timestamp : `${timestamp}Z`);
}

function nearest<T extends { time_tag: string }>(rows: T[], timestamp: string, toleranceMs: number): T | null {
  const target = epoch(timestamp);
  let best: T | null = null;
  let bestDelta = Number.POSITIVE_INFINITY;
  for (const row of rows) {
    const delta = Math.abs(epoch(row.time_tag) - target);
    if (delta < bestDelta) {
      best = row;
      bestDelta = delta;
    }
  }
  return bestDelta <= toleranceMs ? best : null;
}

function latest<T extends { timestamp: string }>(rows: T[]): T {
  if (!rows.length) throw new Error("LIVE_SOURCE_EMPTY:NOAA_SWPC");
  return rows.reduce((current, row) => epoch(row.timestamp) > epoch(current.timestamp) ? row : current);
}

serve(async (req) => {
  if (req.method === "OPTIONS") return new Response(null, { headers: corsHeaders });

  try {
    const [windRows, imfRows, goesRows, kpRows, forecastRows] = await Promise.all([
      fetchLiveJson<WindRow[]>(WIND_URL),
      fetchLiveJson<ImfRow[]>(IMF_URL),
      fetchLiveJson<GoesMagRow[]>(GOES_MAG_URL),
      fetchLiveJson<KpRow[]>(KP_URL),
      fetchLiveJson<ForecastRow[]>(FORECAST_URL),
    ]);

    const activeImf = imfRows.filter((row) => row.active && row.bz_gsm !== null);
    const solarWindData = windRows
      .filter((row) => row.active && row.proton_speed !== null && row.proton_density !== null && row.proton_temperature !== null)
      .map((row) => ({ row, imf: nearest(activeImf, row.time_tag, 5 * 60 * 1000) }))
      .filter((entry): entry is { row: WindRow; imf: ImfRow } => entry.imf !== null)
      .slice(0, 60)
      .map(({ row, imf }) => ({
        timestamp: `${row.time_tag}Z`,
        speed: requireFiniteNumber(row.proton_speed, "proton_speed"),
        density: requireFiniteNumber(row.proton_density, "proton_density"),
        temperature: requireFiniteNumber(row.proton_temperature, "proton_temperature"),
        bz: requireFiniteNumber(imf.bz_gsm, "bz_gsm"),
        source: row.source,
      }));

    const validKp = kpRows.filter((row) => row.estimated_kp !== null);
    const magnetometerData = goesRows
      .filter((row) => !row.arcjet_flag && row.Hp !== null && row.total !== null)
      .map((row) => ({ row, kp: nearest(validKp, row.time_tag, 10 * 60 * 1000) }))
      .filter((entry): entry is { row: GoesMagRow; kp: KpRow } => entry.kp !== null)
      .slice(-60)
      .map(({ row, kp }) => ({
        timestamp: row.time_tag,
        hComponent: requireFiniteNumber(row.Hp, "GOES.Hp"),
        intensity: requireFiniteNumber(row.total, "GOES.total"),
        kIndex: requireFiniteNumber(kp.estimated_kp, "estimated_kp"),
        satellite: row.satellite,
      }));

    const auroraForecast = forecastRows
      .filter((row) => row.observed === "predicted" && row.kp !== null)
      .slice(0, 24)
      .map((row) => {
        const kpIndex = requireFiniteNumber(row.kp, "forecast.kp");
        return {
          timestamp: row.time_tag,
          kpIndex,
          probability: Math.min(100, (kpIndex / 9) * 100),
          viewingLatitude: 66 - (kpIndex * 4),
          noaaScale: row.noaa_scale,
          truthStatus: "real_derived",
          derivedFrom: ["NOAA_SWPC_KP_FORECAST"],
        };
      });

    const currentSolarWind = latest(solarWindData);
    const currentMag = latest(magnetometerData);
    const currentForecast = auroraForecast[0];
    if (!currentForecast) throw new Error("LIVE_SOURCE_EMPTY:NOAA_SWPC_FORECAST");

    const solarProvenance = liveProvenance("noaa_swpc_rtsw", WIND_URL, currentSolarWind.timestamp, TELEMETRY_TTL_MS);
    const magProvenance = liveProvenance("noaa_swpc_goes_magnetometer", GOES_MAG_URL, currentMag.timestamp, TELEMETRY_TTL_MS);
    const forecastProvenance = derivedProvenance("noaa_swpc_kp_forecast", FORECAST_URL, new Date().toISOString(), TELEMETRY_TTL_MS);
    const stormLevel = currentMag.kIndex >= 8 ? "Severe" : currentMag.kIndex >= 6 ? "Strong" : currentMag.kIndex >= 5 ? "Moderate" : currentMag.kIndex >= 4 ? "Minor" : "Quiet";
    const auroraVisible = currentForecast.kpIndex >= 5;
    const auroraLocation = currentForecast.kpIndex >= 7 ? "Mid-latitudes (45°+)" : currentForecast.kpIndex >= 5 ? "High latitudes (55°+)" : currentForecast.kpIndex >= 3 ? "Arctic Circle (65°+)" : "Polar regions only";

    return new Response(JSON.stringify({
      timestamp: new Date().toISOString(),
      truthStatus: "live",
      solarWind: {
        current: currentSolarWind,
        history: solarWindData,
        status: currentSolarWind.speed > 600 ? "High" : currentSolarWind.speed > 400 ? "Moderate" : "Normal",
        provenance: solarProvenance,
      },
      magnetometer: { current: currentMag, history: magnetometerData, stormLevel, provenance: magProvenance },
      aurora: { current: currentForecast, forecast: auroraForecast, visible: auroraVisible, location: auroraLocation, provenance: forecastProvenance },
      alerts: {
        solarWindAlert: currentSolarWind.speed > 700,
        magneticStorm: currentMag.kIndex >= 5,
        auroraAlert: currentForecast.kpIndex >= 5,
      },
    }), { headers: { ...corsHeaders, "Content-Type": "application/json" } });
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : "Unknown error occurred";
    console.error("[fetch-noaa-space-weather] live source failure:", errorMessage);
    return new Response(JSON.stringify({
      success: false,
      truthStatus: "no_data",
      sourceId: "noaa_swpc",
      error: errorMessage,
      generatedValues: false,
    }), { status: 503, headers: { ...corsHeaders, "Content-Type": "application/json" } });
  }
});
