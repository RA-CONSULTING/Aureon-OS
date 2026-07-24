import { useEffect, useState } from "react";
import { supabase } from "@/integrations/supabase/client";

/**
 * Real NOAA space-weather feed (solar wind, magnetometer/Kp, aurora forecast).
 *
 * Backed by the `fetch-noaa-space-weather` edge function — the single source of
 * truth for Kp/storm/solar-wind across the platform. Returns `data: null` (never
 * fabricated values) when the feed is unavailable, so surfaces can render an
 * honest no-data state.
 */

export interface SolarWindData {
  timestamp: string;
  speed: number;
  density: number;
  temperature: number;
  bz: number;
}

export interface MagnetometerData {
  timestamp: string;
  hComponent: number;
  intensity: number;
  kIndex: number;
}

export interface AuroraForecast {
  timestamp: string;
  kpIndex: number;
  probability: number;
  viewingLatitude: number;
}

export interface SpaceWeatherData {
  timestamp: string;
  solarWind: {
    current: SolarWindData;
    history: SolarWindData[];
    status: string;
  };
  magnetometer: {
    current: MagnetometerData;
    history: MagnetometerData[];
    stormLevel: string;
  };
  aurora: {
    current: AuroraForecast;
    forecast: AuroraForecast[];
    visible: boolean;
    location: string;
  };
  alerts: {
    solarWindAlert: boolean;
    magneticStorm: boolean;
    auroraAlert: boolean;
  };
}

export const useNoaaSpaceWeather = (refreshMs = 5 * 60 * 1000) => {
  const [data, setData] = useState<SpaceWeatherData | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    const fetchSpaceWeather = async () => {
      try {
        const { data: weatherData, error } = await supabase.functions.invoke("fetch-noaa-space-weather");
        if (error) throw error;
        if (!cancelled) setData((weatherData as SpaceWeatherData) ?? null);
      } catch (error) {
        console.error("Error fetching space weather:", error);
        if (!cancelled) setData(null);
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    };

    fetchSpaceWeather();
    const interval = setInterval(fetchSpaceWeather, refreshMs);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [refreshMs]);

  return { data, isLoading };
};
