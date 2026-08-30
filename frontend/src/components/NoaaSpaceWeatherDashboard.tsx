import { useEffect, useState } from "react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { supabase } from "@/integrations/supabase/client";
import { Activity, Wind, Magnet, Zap, AlertTriangle } from "lucide-react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area, AreaChart } from "recharts";

interface SolarWindData {
  timestamp: string;
  speed: number;
  density: number;
  temperature: number;
  bz: number;
}

interface MagnetometerData {
  timestamp: string;
  hComponent: number;
  intensity: number;
  kIndex: number;
}

interface AuroraForecast {
  timestamp: string;
  kpIndex: number;
  probability: number;
  viewingLatitude: number;
}

interface SpaceWeatherData {
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

export const NoaaSpaceWeatherDashboard = () => {
  const [data, setData] = useState<SpaceWeatherData | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const fetchSpaceWeather = async () => {
    try {
      const { data: weatherData, error } = await supabase.functions.invoke('fetch-noaa-space-weather');
      
      if (error) throw error;
      setData(weatherData);
    } catch (error) {
      console.error('Error fetching space weather:', error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchSpaceWeather();
    const interval = setInterval(fetchSpaceWeather, 5 * 60 * 1000); // Update every 5 minutes
    return () => clearInterval(interval);
  }, []);

  if (isLoading) {
    return (
      <Card className="p-6">
        <div className="flex items-center justify-center h-96">
          <div className="text-muted-foreground">Loading space weather data...</div>
        </div>
      </Card>
    );
  }

  if (!data) {
    return (
      <Card className="p-6">
        <div className="text-muted-foreground">No data available</div>
      </Card>
    );
  }

  const getStormColor = (level: string) => {
    switch (level) {
      case 'Severe': return 'destructive';
      case 'Strong': return 'destructive';
      case 'Moderate': return 'default';
      case 'Minor': return 'secondary';
      default: return 'outline';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold"> NOAA Space Weather Dashboard</h2>
          <p className="text-sm text-muted-foreground">
            Real-time solar wind, magnetometer, and aurora data
          </p>
        </div>
        <div className="flex gap-2">
          {data.alerts.solarWindAlert && (
            <Badge variant="destructive" className="gap-1">
              <AlertTriangle className="h-3 w-3" />
              High Solar Wind
            </Badge>
          )}
          {data.alerts.magneticStorm && (
            <Badge variant="destructive" className="gap-1">
              <AlertTriangle className="h-3 w-3" />
              Magnetic Storm
            </Badge>
          )}
          {data.alerts.auroraAlert && (
            <Badge variant="default" className="gap-1">
              <Zap className="h-3 w-3" />
              Aurora Alert
            </Badge>
          )}
        </div>
      </div>

      {/* Current Conditions */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="p-4">
          <div className="flex items-center gap-2 mb-2">
            <Wind className="h-5 w-5 text-primary" />
            <h3 className="font-semibold">Solar Wind</h3>
          </div>
          <div className="space-y-2">
            <div className="flex justify-between">
              <span className="text-sm text-muted-foreground">Speed</span>
              <span className="font-mono font-bold">{data.solarWind.current.speed.toFixed(0)} km/s</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-muted-foreground">Density</span>
              <span className="font-mono">{data.solarWind.current.density.toFixed(1)} p/cm³</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-muted-foreground">Bz</span>
              <span className="font-mono">{data.solarWind.current.bz.toFixed(1)} nT</span>
            </div>
            <Badge variant="outline">{data.solarWind.status}</Badge>
          </div>
        </Card>

        <Card className="p-4">
          <div className="flex items-center gap-2 mb-2">
            <Magnet className="h-5 w-5 text-primary" />
            <h3 className="font-semibold">Geomagnetic Field</h3>
          </div>
          <div className="space-y-2">
            <div className="flex justify-between">
              <span className="text-sm text-muted-foreground">Kp Index</span>
              <span className="font-mono font-bold">{data.magnetometer.current.kIndex.toFixed(1)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-muted-foreground">H Component</span>
              <span className="font-mono">{data.magnetometer.current.hComponent.toFixed(1)} nT</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-muted-foreground">Storm Level</span>
              <Badge variant={getStormColor(data.magnetometer.stormLevel) as any}>
                {data.magnetometer.stormLevel}
              </Badge>
            </div>
          </div>
        </Card>

        <Card className="p-4">
          <div className="flex items-center gap-2 mb-2">
            <Activity className="h-5 w-5 text-primary" />
            <h3 className="font-semibold">Aurora Forecast</h3>
          </div>
          <div className="space-y-2">
            <div className="flex justify-between">
              <span className="text-sm text-muted-foreground">Current Kp</span>
              <span className="font-mono font-bold">{data.aurora.current.kpIndex.toFixed(1)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-muted-foreground">Probability</span>
              <span className="font-mono">{data.aurora.current.probability.toFixed(0)}%</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-muted-foreground">Visible</span>
              <Badge variant={data.aurora.visible ? "default" : "outline"}>
                {data.aurora.visible ? "Yes" : "No"}
              </Badge>
            </div>
            <p className="text-xs text-muted-foreground">{data.aurora.location}</p>
          </div>
        </Card>
      </div>

      {/* Solar Wind History */}
      <Card className="p-6">
        <h3 className="font-semibold mb-4 flex items-center gap-2">
          <Wind className="h-4 w-4" />
          Solar Wind Speed (24h)
        </h3>
        <ResponsiveContainer width="100%" height={250}>
          <AreaChart data={data.solarWind.history}>
            <defs>
              <linearGradient id="solarWindGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.3} />
                <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" opacity={0.1} />
            <XAxis 
              dataKey="timestamp" 
              fontSize={12}
              tickFormatter={(value) => new Date(value).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            />
            <YAxis fontSize={12} />
            <Tooltip 
              labelFormatter={(value) => new Date(value).toLocaleString()}
              formatter={(value: number) => [`${value.toFixed(0)} km/s`, 'Speed']}
            />
            <Area 
              type="monotone" 
              dataKey="speed" 
              stroke="hsl(var(--primary))" 
              fill="url(#solarWindGradient)"
              strokeWidth={2}
            />
          </AreaChart>
        </ResponsiveContainer>
      </Card>

      {/* Kp Index History */}
      <Card className="p-6">
        <h3 className="font-semibold mb-4 flex items-center gap-2">
          <Magnet className="h-4 w-4" />
          Planetary Kp Index (Recent)
        </h3>
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={data.magnetometer.history}>
            <CartesianGrid strokeDasharray="3 3" opacity={0.1} />
            <XAxis 
              dataKey="timestamp" 
              fontSize={12}
              tickFormatter={(value) => new Date(value).toLocaleTimeString([], { hour: '2-digit' })}
            />
            <YAxis fontSize={12} domain={[0, 9]} />
            <Tooltip 
              labelFormatter={(value) => new Date(value).toLocaleString()}
              formatter={(value: number) => [value.toFixed(1), 'Kp Index']}
            />
            <Line 
              type="stepAfter" 
              dataKey="kIndex" 
              stroke="hsl(var(--primary))" 
              strokeWidth={2}
              dot={{ r: 3 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </Card>

      {/* Aurora Forecast */}
      <Card className="p-6">
        <h3 className="font-semibold mb-4 flex items-center gap-2">
          <Zap className="h-4 w-4" />
          Aurora Forecast (Next 12h)
        </h3>
        <ResponsiveContainer width="100%" height={200}>
          <AreaChart data={data.aurora.forecast}>
            <defs>
              <linearGradient id="auroraGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="hsl(var(--chart-2))" stopOpacity={0.5} />
                <stop offset="95%" stopColor="hsl(var(--chart-2))" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" opacity={0.1} />
            <XAxis 
              dataKey="timestamp" 
              fontSize={12}
              tickFormatter={(value) => new Date(value).toLocaleTimeString([], { hour: '2-digit' })}
            />
            <YAxis fontSize={12} domain={[0, 9]} />
            <Tooltip 
              labelFormatter={(value) => new Date(value).toLocaleString()}
              formatter={(value: number) => [value.toFixed(1), 'Kp Forecast']}
            />
            <Area 
              type="monotone" 
              dataKey="kpIndex" 
              stroke="hsl(var(--chart-2))" 
              fill="url(#auroraGradient)"
              strokeWidth={2}
            />
          </AreaChart>
        </ResponsiveContainer>
      </Card>

      {/* Footer */}
      <div className="text-xs text-muted-foreground text-center">
        Data provided by NOAA Space Weather Prediction Center • Updated every 5 minutes
      </div>
    </div>
  );
};
