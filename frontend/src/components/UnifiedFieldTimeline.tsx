import { useEffect, useState } from "react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { supabase } from "@/integrations/supabase/client";
import { Clock, TrendingUp, Zap, Activity } from "lucide-react";
import { 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  Area,
  AreaChart,
  Legend,
  ReferenceLine,
  ComposedChart,
  Bar
} from "recharts";

interface HourlyFieldData {
  hour: number;
  seismicStability: number;
  schumannCoherence: number;
  solarWindStability: number;
  kpIndexNormalized: number;
  tradingCoherence: number;
  lighthouseEvents: number;
  unifiedFieldCoherence: number;
  optimalWindow: boolean;
}

interface RecurringPattern {
  startHour: number;
  endHour: number;
  duration: number;
  avgCoherence: number;
}

interface AnalysisData {
  timestamp: string;
  timeline: HourlyFieldData[];
  statistics: {
    avgUnifiedCoherence: number;
    totalOptimalHours: number;
    totalLighthouseEvents: number;
    peakCoherenceHour: number;
    peakCoherence: number;
  };
  recurringPatterns: RecurringPattern[];
  topPeriods: Array<{ hour: number; coherence: number; hasLHE: boolean }>;
  insights: {
    bestTradingWindow: RecurringPattern | null;
    fieldAlignment: string;
  };
}

export const UnifiedFieldTimeline = () => {
  const [data, setData] = useState<AnalysisData | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const fetchAnalysis = async () => {
    try {
      const { data: analysisData, error } = await supabase.functions.invoke('unified-field-analysis');
      
      if (error) throw error;
      setData(analysisData);
    } catch (error) {
      console.error('Error fetching unified field analysis:', error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalysis();
    const interval = setInterval(fetchAnalysis, 10 * 60 * 1000); // Update every 10 minutes
    return () => clearInterval(interval);
  }, []);

  if (isLoading) {
    return (
      <Card className="p-6">
        <div className="flex items-center justify-center h-96">
          <div className="text-muted-foreground">Analyzing unified field patterns...</div>
        </div>
      </Card>
    );
  }

  if (!data) {
    return (
      <Card className="p-6">
        <div className="text-muted-foreground">No analysis data available</div>
      </Card>
    );
  }

  const formatHour = (hour: number) => {
    const period = hour >= 12 ? 'PM' : 'AM';
    const displayHour = hour === 0 ? 12 : hour > 12 ? hour - 12 : hour;
    return `${displayHour}${period}`;
  };

  const getAlignmentColor = (level: string) => {
    switch (level) {
      case 'EXCELLENT': return 'default';
      case 'GOOD': return 'secondary';
      default: return 'outline';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold flex items-center gap-2">
          <Clock className="h-6 w-6 text-primary" />
          Unified Field Coherence Timeline
        </h2>
        <p className="text-sm text-muted-foreground">
          24-hour pattern analysis across all Earth and space systems
        </p>
      </div>

      {/* Statistics Overview */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="p-4">
          <div className="text-sm text-muted-foreground mb-1">Field Alignment</div>
          <div className="flex items-center justify-between">
            <div className="text-2xl font-bold">
              {(data.statistics.avgUnifiedCoherence * 100).toFixed(0)}%
            </div>
            <Badge variant={getAlignmentColor(data.insights.fieldAlignment) as any}>
              {data.insights.fieldAlignment}
            </Badge>
          </div>
        </Card>

        <Card className="p-4">
          <div className="text-sm text-muted-foreground mb-1">Optimal Hours</div>
          <div className="text-2xl font-bold">
            {data.statistics.totalOptimalHours}/24
          </div>
          <div className="text-xs text-muted-foreground mt-1">
            {((data.statistics.totalOptimalHours / 24) * 100).toFixed(0)}% of day
          </div>
        </Card>

        <Card className="p-4">
          <div className="text-sm text-muted-foreground mb-1">Peak Hour</div>
          <div className="text-2xl font-bold">
            {formatHour(data.statistics.peakCoherenceHour)}
          </div>
          <div className="text-xs text-muted-foreground mt-1">
            {(data.statistics.peakCoherence * 100).toFixed(0)}% coherence
          </div>
        </Card>

        <Card className="p-4">
          <div className="text-sm text-muted-foreground mb-1">LHE Events</div>
          <div className="text-2xl font-bold">
            {data.statistics.totalLighthouseEvents}
          </div>
          <div className="text-xs text-muted-foreground mt-1">
            Last 24 hours
          </div>
        </Card>
      </div>

      {/* Unified Field Coherence Timeline */}
      <Card className="p-6">
        <h3 className="font-semibold mb-4 flex items-center gap-2">
          <TrendingUp className="h-4 w-4" />
          24-Hour Unified Field Coherence
        </h3>
        <ResponsiveContainer width="100%" height={300}>
          <ComposedChart data={data.timeline}>
            <defs>
              <linearGradient id="unifiedGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.8} />
                <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" opacity={0.1} />
            <XAxis 
              dataKey="hour" 
              tickFormatter={formatHour}
              fontSize={12}
            />
            <YAxis domain={[0, 1]} fontSize={12} />
            <Tooltip 
              labelFormatter={(hour) => formatHour(Number(hour))}
              formatter={(value: number) => [`${(value * 100).toFixed(1)}%`, 'Coherence']}
            />
            <ReferenceLine y={0.75} stroke="hsl(var(--chart-2))" strokeDasharray="3 3" label="Optimal Threshold" />
            
            {/* Highlight optimal windows */}
            {data.timeline.map((item, idx) => 
              item.optimalWindow ? (
                <ReferenceLine 
                  key={idx}
                  x={item.hour} 
                  stroke="hsl(var(--chart-3))" 
                  strokeWidth={3}
                  opacity={0.3}
                />
              ) : null
            )}
            
            <Area 
              type="monotone" 
              dataKey="unifiedFieldCoherence" 
              stroke="hsl(var(--primary))" 
              fill="url(#unifiedGradient)"
              strokeWidth={3}
            />
            <Bar 
              dataKey={(item) => item.lighthouseEvents > 0 ? 1 : 0}
              fill="hsl(var(--chart-3))"
              opacity={0.3}
            />
          </ComposedChart>
        </ResponsiveContainer>
        <p className="text-xs text-muted-foreground mt-2">
          Green bars indicate Lighthouse Events. Dashed line shows optimal threshold (75%). 
          Highlighted periods are optimal trading windows.
        </p>
      </Card>

      {/* Multi-System Layer View */}
      <Card className="p-6">
        <h3 className="font-semibold mb-4 flex items-center gap-2">
          <Activity className="h-4 w-4" />
          Multi-System Coherence Layers
        </h3>
        <ResponsiveContainer width="100%" height={350}>
          <LineChart data={data.timeline}>
            <CartesianGrid strokeDasharray="3 3" opacity={0.1} />
            <XAxis 
              dataKey="hour" 
              tickFormatter={formatHour}
              fontSize={12}
            />
            <YAxis domain={[0, 1]} fontSize={12} />
            <Tooltip 
              labelFormatter={(hour) => formatHour(Number(hour))}
              formatter={(value: number, name: string) => [`${(value * 100).toFixed(1)}%`, name]}
            />
            <Legend />
            <Line 
              type="monotone" 
              dataKey="seismicStability" 
              stroke="hsl(var(--destructive))" 
              strokeWidth={2}
              name="Seismic Stability"
              dot={false}
            />
            <Line 
              type="monotone" 
              dataKey="schumannCoherence" 
              stroke="hsl(var(--primary))" 
              strokeWidth={2}
              name="Schumann Coherence"
              dot={false}
            />
            <Line 
              type="monotone" 
              dataKey="solarWindStability" 
              stroke="hsl(var(--chart-2))" 
              strokeWidth={2}
              name="Solar Wind Stability"
              dot={false}
            />
            <Line 
              type="monotone" 
              dataKey="kpIndexNormalized" 
              stroke="hsl(var(--chart-3))" 
              strokeWidth={2}
              name="Geomagnetic Stability"
              dot={false}
            />
            <Line 
              type="monotone" 
              dataKey="tradingCoherence" 
              stroke="hsl(var(--chart-4))" 
              strokeWidth={2}
              name="Trading Coherence"
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
        <p className="text-xs text-muted-foreground mt-2">
          Individual system coherence contributions. When all lines align high, unified field coherence peaks.
        </p>
      </Card>

      {/* Recurring Patterns */}
      {data.recurringPatterns.length > 0 && (
        <Card className="p-6">
          <h3 className="font-semibold mb-4 flex items-center gap-2">
            <Zap className="h-4 w-4" />
            Recurring Optimal Windows
          </h3>
          <div className="space-y-3">
            {data.recurringPatterns.map((pattern, idx) => (
              <div key={idx} className="flex items-center justify-between p-4 bg-muted rounded-lg">
                <div className="flex-1">
                  <div className="font-medium">
                    {formatHour(pattern.startHour)} - {formatHour(pattern.endHour)}
                  </div>
                  <div className="text-sm text-muted-foreground">
                    Duration: {pattern.duration} hour{pattern.duration > 1 ? 's' : ''}
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-xl font-bold">
                    {(pattern.avgCoherence * 100).toFixed(0)}%
                  </div>
                  <div className="text-xs text-muted-foreground">
                    Avg Coherence
                  </div>
                </div>
                {idx === 0 && (
                  <Badge className="ml-4" variant="default">
                    Best Window
                  </Badge>
                )}
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Top 5 Peak Periods */}
      <Card className="p-6">
        <h3 className="font-semibold mb-4">🎯 Top 5 Peak Coherence Periods</h3>
        <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
          {data.topPeriods.map((period, idx) => (
            <div key={idx} className="text-center p-4 bg-muted rounded-lg">
              <div className="text-sm text-muted-foreground mb-1">#{idx + 1}</div>
              <div className="text-2xl font-bold mb-1">{formatHour(period.hour)}</div>
              <div className="text-sm font-medium">{(period.coherence * 100).toFixed(0)}%</div>
              {period.hasLHE && (
                <Badge variant="outline" className="mt-2 text-xs">
                  LHE
                </Badge>
              )}
            </div>
          ))}
        </div>
      </Card>

      {/* Insights */}
      <Card className="p-6">
        <h3 className="font-semibold mb-4">📊 Unified Field Insights</h3>
        <div className="space-y-3">
          {data.insights.bestTradingWindow && (
            <div className="border-l-4 border-primary pl-4">
              <p className="text-sm font-medium">🎯 Optimal Trading Window Identified</p>
              <p className="text-xs text-muted-foreground mt-1">
                Best window: {formatHour(data.insights.bestTradingWindow.startHour)} - {formatHour(data.insights.bestTradingWindow.endHour)} 
                ({data.insights.bestTradingWindow.duration} hours) with {(data.insights.bestTradingWindow.avgCoherence * 100).toFixed(0)}% 
                average unified field coherence. All systems aligned during this period.
              </p>
            </div>
          )}

          {data.insights.fieldAlignment === 'EXCELLENT' && (
            <div className="border-l-4 border-success pl-4">
              <p className="text-sm font-medium">✨ Excellent Field Alignment Today</p>
              <p className="text-xs text-muted-foreground mt-1">
                Multiple hours showing unified coherence above 80%. Earth and space systems are in strong harmony. 
                Ideal conditions for high-confidence trading.
              </p>
            </div>
          )}

          <div className="border-l-4 border-primary pl-4">
            <p className="text-sm font-medium">🌍 Unified Field Theory</p>
            <p className="text-xs text-muted-foreground mt-1">
              When seismic stability, Schumann resonance, solar wind conditions, geomagnetic indices, and trading 
              coherence all peak simultaneously, it indicates a fundamental alignment in natural systems. These 
              recurring patterns can predict optimal trading windows.
            </p>
          </div>

          {data.statistics.totalOptimalHours < 4 && (
            <div className="border-l-4 border-warning pl-4">
              <p className="text-sm font-medium">⚠️ Limited Optimal Windows</p>
              <p className="text-xs text-muted-foreground mt-1">
                Only {data.statistics.totalOptimalHours} optimal hours detected in the last 24 hours. 
                Exercise caution during non-optimal periods. Wait for field alignment to improve.
              </p>
            </div>
          )}
        </div>
      </Card>

      {/* Footer */}
      <div className="text-xs text-muted-foreground text-center">
        Unified analysis: Seismic + Schumann + Solar Wind + Geomagnetic + Trading coherence • Updates every 10 minutes
      </div>
    </div>
  );
};
