import { useEffect, useState } from "react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { supabase } from "@/integrations/supabase/client";
import { TrendingUp, TrendingDown, Activity, Wind, Zap } from "lucide-react";
import { 
  ScatterChart, 
  Scatter, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  BarChart,
  Bar,
  LineChart,
  Line,
  Legend
} from "recharts";

interface CorrelationData {
  timestamp: string;
  solarWindSpeed: number;
  kpIndex: number;
  coherence: number;
  lighthouseSignal: number;
  signalStrength: number;
  isLHE: boolean;
}

interface KpCorrelation {
  kpIndex: number;
  avgCoherence: number;
  lheRate: number;
  sampleSize: number;
}

interface SolarWindCorrelation {
  speedRange: number;
  avgCoherence: number;
  optimalSignalRate: number;
  sampleSize: number;
}

interface AnalysisData {
  correlations: CorrelationData[];
  statistics: {
    kpCoherenceCorrelation: number;
    solarWindCoherenceCorrelation: number;
    solarWindSignalCorrelation: number;
    totalSamples: number;
  };
  kpCorrelation: KpCorrelation[];
  solarWindCorrelation: SolarWindCorrelation[];
  optimalConditions: {
    avgKpIndex: number;
    avgSolarWindSpeed: number;
    sampleSize: number;
  } | null;
  insights: {
    strongCorrelation: boolean;
    favorableKpRange: number[];
    favorableSolarWindRange: number[];
  };
}

export const SpaceWeatherCorrelationAnalyzer = () => {
  const [data, setData] = useState<AnalysisData | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const fetchCorrelation = async () => {
    try {
      const { data: analysisData, error } = await supabase.functions.invoke('analyze-space-weather-correlation');
      
      if (error) throw error;
      setData(analysisData);
    } catch (error) {
      console.error('Error fetching space weather correlation:', error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchCorrelation();
    const interval = setInterval(fetchCorrelation, 10 * 60 * 1000); // Update every 10 minutes
    return () => clearInterval(interval);
  }, []);

  if (isLoading) {
    return (
      <Card className="p-6">
        <div className="flex items-center justify-center h-96">
          <div className="text-muted-foreground">Analyzing space weather correlations...</div>
        </div>
      </Card>
    );
  }

  if (!data) {
    return (
      <Card className="p-6">
        <div className="text-muted-foreground">No correlation data available</div>
      </Card>
    );
  }

  const getCorrelationStrength = (value: number) => {
    const abs = Math.abs(value);
    if (abs > 0.7) return { label: 'Strong', variant: 'default' };
    if (abs > 0.4) return { label: 'Moderate', variant: 'secondary' };
    return { label: 'Weak', variant: 'outline' };
  };

  const kpCoherenceStrength = getCorrelationStrength(data.statistics.kpCoherenceCorrelation);
  const solarWindCoherenceStrength = getCorrelationStrength(data.statistics.solarWindCoherenceCorrelation);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold flex items-center gap-2">
          <Activity className="h-6 w-6 text-primary" />
          Space Weather Correlation Analysis
        </h2>
        <p className="text-sm text-muted-foreground">
          How solar activity influences trading coherence and lighthouse events
        </p>
      </div>

      {/* Overall Statistics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="p-4">
          <div className="flex items-center justify-between mb-2">
            <h3 className="font-semibold text-sm">Kp ↔ Coherence</h3>
            <Badge variant={kpCoherenceStrength.variant as any}>
              {kpCoherenceStrength.label}
            </Badge>
          </div>
          <div className="text-2xl font-bold flex items-center gap-2">
            {data.statistics.kpCoherenceCorrelation > 0 ? (
              <TrendingUp className="h-5 w-5 text-success" />
            ) : (
              <TrendingDown className="h-5 w-5 text-destructive" />
            )}
            {(data.statistics.kpCoherenceCorrelation * 100).toFixed(1)}%
          </div>
          <p className="text-xs text-muted-foreground mt-1">
            Geomagnetic activity correlation
          </p>
        </Card>

        <Card className="p-4">
          <div className="flex items-center justify-between mb-2">
            <h3 className="font-semibold text-sm">Solar Wind ↔ Coherence</h3>
            <Badge variant={solarWindCoherenceStrength.variant as any}>
              {solarWindCoherenceStrength.label}
            </Badge>
          </div>
          <div className="text-2xl font-bold flex items-center gap-2">
            {data.statistics.solarWindCoherenceCorrelation > 0 ? (
              <TrendingUp className="h-5 w-5 text-success" />
            ) : (
              <TrendingDown className="h-5 w-5 text-destructive" />
            )}
            {(data.statistics.solarWindCoherenceCorrelation * 100).toFixed(1)}%
          </div>
          <p className="text-xs text-muted-foreground mt-1">
            Solar wind speed correlation
          </p>
        </Card>

        <Card className="p-4">
          <div className="flex items-center justify-between mb-2">
            <h3 className="font-semibold text-sm">Total Samples</h3>
            <Badge variant="outline">{data.statistics.totalSamples}</Badge>
          </div>
          <div className="text-2xl font-bold">
            {data.statistics.totalSamples}
          </div>
          <p className="text-xs text-muted-foreground mt-1">
            Correlated data points (7 days)
          </p>
        </Card>
      </div>

      {/* Insights */}
      {data.insights.strongCorrelation && (
        <Card className="p-4 border-primary">
          <div className="flex items-start gap-3">
            <Zap className="h-5 w-5 text-primary mt-0.5" />
            <div className="flex-1">
              <h3 className="font-semibold mb-2">Strong Correlation Detected</h3>
              <p className="text-sm text-muted-foreground mb-3">
                Space weather shows significant influence on trading coherence. Optimal conditions identified:
              </p>
              {data.optimalConditions && (
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-muted-foreground">Optimal Kp Range:</span>
                    <div className="font-mono font-bold">
                      {data.insights.favorableKpRange.join(', ')}
                    </div>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Optimal Solar Wind:</span>
                    <div className="font-mono font-bold">
                      {data.insights.favorableSolarWindRange.map(s => `${s}-${s+100}`).join(', ')} km/s
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </Card>
      )}

      {/* Kp Index vs Coherence */}
      <Card className="p-6">
        <h3 className="font-semibold mb-4 flex items-center gap-2">
          <Activity className="h-4 w-4" />
          Geomagnetic Activity vs Trading Coherence
        </h3>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={data.kpCorrelation}>
            <CartesianGrid strokeDasharray="3 3" opacity={0.1} />
            <XAxis dataKey="kpIndex" label={{ value: 'Kp Index', position: 'insideBottom', offset: -5 }} />
            <YAxis yAxisId="left" label={{ value: 'Avg Coherence', angle: -90, position: 'insideLeft' }} />
            <YAxis yAxisId="right" orientation="right" label={{ value: 'LHE Rate (%)', angle: 90, position: 'insideRight' }} />
            <Tooltip />
            <Legend />
            <Bar yAxisId="left" dataKey="avgCoherence" fill="hsl(var(--primary))" name="Avg Coherence" />
            <Bar yAxisId="right" dataKey="lheRate" fill="hsl(var(--chart-2))" name="LHE Rate (%)" />
          </BarChart>
        </ResponsiveContainer>
        <p className="text-xs text-muted-foreground mt-2">
          Higher Kp index indicates stronger geomagnetic activity. Shows correlation with coherence levels and LHE frequency.
        </p>
      </Card>

      {/* Solar Wind vs Signals */}
      <Card className="p-6">
        <h3 className="font-semibold mb-4 flex items-center gap-2">
          <Wind className="h-4 w-4" />
          Solar Wind Speed vs Signal Quality
        </h3>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={data.solarWindCorrelation}>
            <CartesianGrid strokeDasharray="3 3" opacity={0.1} />
            <XAxis 
              dataKey="speedRange" 
              label={{ value: 'Solar Wind Speed (km/s)', position: 'insideBottom', offset: -5 }}
              tickFormatter={(value) => `${value}`}
            />
            <YAxis yAxisId="left" label={{ value: 'Avg Coherence', angle: -90, position: 'insideLeft' }} />
            <YAxis yAxisId="right" orientation="right" label={{ value: 'Optimal Signal Rate (%)', angle: 90, position: 'insideRight' }} />
            <Tooltip 
              labelFormatter={(value) => `${value}-${value+100} km/s`}
            />
            <Legend />
            <Line yAxisId="left" type="monotone" dataKey="avgCoherence" stroke="hsl(var(--primary))" strokeWidth={2} name="Avg Coherence" />
            <Line yAxisId="right" type="monotone" dataKey="optimalSignalRate" stroke="hsl(var(--chart-3))" strokeWidth={2} name="Optimal Signal Rate (%)" />
          </LineChart>
        </ResponsiveContainer>
        <p className="text-xs text-muted-foreground mt-2">
          Correlation between solar wind speed and trading signal strength. Identifies optimal solar wind conditions for high-quality signals.
        </p>
      </Card>

      {/* Scatter Plot: Kp vs Coherence */}
      <Card className="p-6">
        <h3 className="font-semibold mb-4">Kp Index vs Coherence (Scatter)</h3>
        <ResponsiveContainer width="100%" height={300}>
          <ScatterChart>
            <CartesianGrid strokeDasharray="3 3" opacity={0.1} />
            <XAxis dataKey="kpIndex" name="Kp Index" />
            <YAxis dataKey="coherence" name="Coherence" />
            <Tooltip cursor={{ strokeDasharray: '3 3' }} />
            <Scatter 
              name="LHE Events" 
              data={data.correlations.filter(c => c.isLHE)} 
              fill="hsl(var(--primary))" 
            />
            <Scatter 
              name="Regular Signals" 
              data={data.correlations.filter(c => !c.isLHE)} 
              fill="hsl(var(--muted))" 
              opacity={0.5}
            />
            <Legend />
          </ScatterChart>
        </ResponsiveContainer>
      </Card>

      {/* Scatter Plot: Solar Wind vs Signal Strength */}
      <Card className="p-6">
        <h3 className="font-semibold mb-4">Solar Wind Speed vs Signal Strength (Scatter)</h3>
        <ResponsiveContainer width="100%" height={300}>
          <ScatterChart>
            <CartesianGrid strokeDasharray="3 3" opacity={0.1} />
            <XAxis dataKey="solarWindSpeed" name="Solar Wind Speed (km/s)" />
            <YAxis dataKey="signalStrength" name="Signal Strength" domain={[0, 1]} />
            <Tooltip cursor={{ strokeDasharray: '3 3' }} />
            <Scatter 
              name="High Strength (>0.7)" 
              data={data.correlations.filter(c => c.signalStrength > 0.7)} 
              fill="hsl(var(--chart-2))" 
            />
            <Scatter 
              name="Normal Strength" 
              data={data.correlations.filter(c => c.signalStrength <= 0.7)} 
              fill="hsl(var(--muted))" 
              opacity={0.5}
            />
            <Legend />
          </ScatterChart>
        </ResponsiveContainer>
      </Card>

      {/* Footer */}
      <div className="text-xs text-muted-foreground text-center">
        Correlation analysis updates every 10 minutes • Data from NOAA SWPC and Lovable Cloud database
      </div>
    </div>
  );
};
