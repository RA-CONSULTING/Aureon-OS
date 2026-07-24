import { useEffect, useState } from 'react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { supabase } from '@/integrations/supabase/client';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine } from 'recharts';
import { TrendingUp, TrendingDown, Activity } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';

type CorrelationDataPoint = {
  date: string;
  avgCoherence: number;
  solarPower: number;
  flareCount: number;
};

export const SolarCoherenceCorrelationChart = () => {
  const [correlationStrength, setCorrelationStrength] = useState(0);
  const [trendDirection, setTrendDirection] = useState<'up' | 'down' | 'stable'>('stable');

  const { data: chartData, isLoading } = useQuery({
    queryKey: ['solar-coherence-correlation'],
    queryFn: async () => {
      const thirtyDaysAgo = new Date();
      thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);

      // Fetch solar flare data
      const { data: flareData } = await supabase
        .from('solar_flare_correlations')
        .select('flare_time, flare_power, flare_class')
        .gte('flare_time', thirtyDaysAgo.toISOString())
        .order('flare_time', { ascending: true });

      // Fetch coherence history
      const { data: coherenceData } = await supabase
        .from('coherence_history')
        .select('timestamp, coherence')
        .gte('timestamp', thirtyDaysAgo.toISOString())
        .order('timestamp', { ascending: true });

      // Group data by day
      const dailyData = new Map<string, { coherenceSum: number; coherenceCount: number; flarePowerSum: number; flareCount: number }>();

      // Process coherence data
      coherenceData?.forEach(item => {
        const date = new Date(item.timestamp).toISOString().split('T')[0];
        if (!dailyData.has(date)) {
          dailyData.set(date, { coherenceSum: 0, coherenceCount: 0, flarePowerSum: 0, flareCount: 0 });
        }
        const day = dailyData.get(date)!;
        day.coherenceSum += item.coherence;
        day.coherenceCount++;
      });

      // Process flare data
      flareData?.forEach(item => {
        const date = new Date(item.flare_time).toISOString().split('T')[0];
        if (!dailyData.has(date)) {
          dailyData.set(date, { coherenceSum: 0, coherenceCount: 0, flarePowerSum: 0, flareCount: 0 });
        }
        const day = dailyData.get(date)!;
        day.flarePowerSum += item.flare_power;
        day.flareCount++;
      });

      // Convert to array and calculate averages
      const result: CorrelationDataPoint[] = Array.from(dailyData.entries())
        .map(([date, data]) => ({
          date,
          avgCoherence: data.coherenceCount > 0 ? data.coherenceSum / data.coherenceCount : 0,
          solarPower: data.flareCount > 0 ? data.flarePowerSum / data.flareCount : 1.0,
          flareCount: data.flareCount
        }))
        .sort((a, b) => a.date.localeCompare(b.date));

      return result;
    },
    refetchInterval: 300000 // Refresh every 5 minutes
  });

  useEffect(() => {
    if (chartData && chartData.length > 5) {
      // Calculate correlation coefficient
      const coherenceValues = chartData.map(d => d.avgCoherence);
      const solarValues = chartData.map(d => d.solarPower);
      
      const n = coherenceValues.length;
      const sumCoherence = coherenceValues.reduce((a, b) => a + b, 0);
      const sumSolar = solarValues.reduce((a, b) => a + b, 0);
      const sumCoherenceSq = coherenceValues.reduce((a, b) => a + b * b, 0);
      const sumSolarSq = solarValues.reduce((a, b) => a + b * b, 0);
      const sumProduct = coherenceValues.reduce((a, b, i) => a + b * solarValues[i], 0);

      const numerator = n * sumProduct - sumCoherence * sumSolar;
      const denominator = Math.sqrt((n * sumCoherenceSq - sumCoherence ** 2) * (n * sumSolarSq - sumSolar ** 2));
      
      const correlation = denominator !== 0 ? numerator / denominator : 0;
      setCorrelationStrength(correlation);

      // Determine trend
      const recent = chartData.slice(-7);
      const older = chartData.slice(-14, -7);
      const recentAvg = recent.reduce((sum, d) => sum + d.avgCoherence, 0) / recent.length;
      const olderAvg = older.length > 0 ? older.reduce((sum, d) => sum + d.avgCoherence, 0) / older.length : recentAvg;
      
      if (recentAvg > olderAvg * 1.05) setTrendDirection('up');
      else if (recentAvg < olderAvg * 0.95) setTrendDirection('down');
      else setTrendDirection('stable');
    }
  }, [chartData]);

  if (isLoading) {
    return (
      <Card className="p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-muted rounded w-1/3" />
          <div className="h-64 bg-muted rounded" />
        </div>
      </Card>
    );
  }

  const avgCoherence = chartData?.length 
    ? chartData.reduce((sum, d) => sum + d.avgCoherence, 0) / chartData.length 
    : 0;

  const correlationLabel = 
    Math.abs(correlationStrength) > 0.7 ? 'Strong' :
    Math.abs(correlationStrength) > 0.4 ? 'Moderate' :
    Math.abs(correlationStrength) > 0.2 ? 'Weak' : 'Minimal';

  const correlationColor = 
    Math.abs(correlationStrength) > 0.7 ? 'text-success' :
    Math.abs(correlationStrength) > 0.4 ? 'text-warning' :
    'text-muted-foreground';

  return (
    <Card className="p-6 bg-gradient-to-br from-background to-primary/5 border-primary/20">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <Activity className="w-6 h-6 text-primary" />
          <div>
            <h3 className="text-xl font-semibold text-foreground">Solar Activity vs Market Coherence</h3>
            <p className="text-sm text-muted-foreground">30-Day Historical Correlation Analysis</p>
          </div>
        </div>
        <div className="text-right space-y-1">
          <div className="flex items-center gap-2">
            {trendDirection === 'up' && <TrendingUp className="w-5 h-5 text-success" />}
            {trendDirection === 'down' && <TrendingDown className="w-5 h-5 text-destructive" />}
            {trendDirection === 'stable' && <Activity className="w-5 h-5 text-warning" />}
            <Badge variant={trendDirection === 'up' ? 'default' : 'secondary'}>
              {trendDirection === 'up' ? 'Uptrend' : trendDirection === 'down' ? 'Downtrend' : 'Stable'}
            </Badge>
          </div>
        </div>
      </div>

      <ResponsiveContainer width="100%" height={400}>
        <LineChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.3} />
          <XAxis 
            dataKey="date" 
            stroke="hsl(var(--muted-foreground))"
            tick={{ fill: 'hsl(var(--muted-foreground))' }}
            tickFormatter={(value) => new Date(value).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
          />
          <YAxis 
            yAxisId="left"
            stroke="hsl(var(--primary))"
            tick={{ fill: 'hsl(var(--primary))' }}
            label={{ value: 'Coherence', angle: -90, position: 'insideLeft', fill: 'hsl(var(--primary))' }}
          />
          <YAxis 
            yAxisId="right" 
            orientation="right"
            stroke="hsl(var(--chart-2))"
            tick={{ fill: 'hsl(var(--chart-2))' }}
            label={{ value: 'Solar Power', angle: 90, position: 'insideRight', fill: 'hsl(var(--chart-2))' }}
          />
          <Tooltip 
            contentStyle={{ 
              backgroundColor: 'hsl(var(--background))', 
              border: '1px solid hsl(var(--border))',
              borderRadius: '8px'
            }}
            labelFormatter={(value) => new Date(value).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}
            formatter={(value: number, name: string) => [
              name === 'avgCoherence' ? value.toFixed(4) : value.toFixed(2),
              name === 'avgCoherence' ? 'Coherence' : name === 'solarPower' ? 'Solar Power' : 'Flares'
            ]}
          />
          <Legend 
            wrapperStyle={{ paddingTop: '20px' }}
            formatter={(value) => {
              if (value === 'avgCoherence') return 'Market Coherence';
              if (value === 'solarPower') return 'Solar Power Index';
              if (value === 'flareCount') return 'Flare Count';
              return value;
            }}
          />
          <ReferenceLine yAxisId="left" y={avgCoherence} stroke="hsl(var(--primary))" strokeDasharray="3 3" />
          <Line 
            yAxisId="left"
            type="monotone" 
            dataKey="avgCoherence" 
            stroke="hsl(var(--primary))" 
            strokeWidth={2}
            dot={{ fill: 'hsl(var(--primary))', r: 3 }}
            activeDot={{ r: 5 }}
          />
          <Line 
            yAxisId="right"
            type="monotone" 
            dataKey="solarPower" 
            stroke="hsl(var(--chart-2))" 
            strokeWidth={2}
            dot={{ fill: 'hsl(var(--chart-2))', r: 3 }}
            activeDot={{ r: 5 }}
          />
        </LineChart>
      </ResponsiveContainer>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
        <Card className="p-4 bg-background/50 border-primary/30">
          <div className="text-sm text-muted-foreground mb-1">Correlation Strength</div>
          <div className={`text-2xl font-bold ${correlationColor}`}>
            {correlationStrength > 0 ? '+' : ''}{(correlationStrength * 100).toFixed(1)}%
          </div>
          <Badge variant="outline" className="mt-2">
            {correlationLabel} {correlationStrength > 0 ? 'Positive' : 'Negative'}
          </Badge>
          <p className="text-xs text-muted-foreground mt-2">
            {Math.abs(correlationStrength) > 0.5 
              ? 'Strong statistical relationship between solar activity and coherence'
              : 'Moderate to weak correlation detected in this period'}
          </p>
        </Card>

        <Card className="p-4 bg-background/50 border-primary/30">
          <div className="text-sm text-muted-foreground mb-1">Avg Coherence (30d)</div>
          <div className="text-2xl font-bold text-primary">
            {avgCoherence.toFixed(4)}
          </div>
          <Badge variant="secondary" className="mt-2">
            {avgCoherence > 0.945 ? 'Excellent' : avgCoherence > 0.920 ? 'Good' : 'Normal'}
          </Badge>
          <p className="text-xs text-muted-foreground mt-2">
            Baseline coherence over the analysis period
          </p>
        </Card>

        <Card className="p-4 bg-background/50 border-primary/30">
          <div className="text-sm text-muted-foreground mb-1">Solar Events</div>
          <div className="text-2xl font-bold text-chart-2">
            {chartData?.reduce((sum, d) => sum + d.flareCount, 0) || 0}
          </div>
          <Badge variant="outline" className="mt-2 border-chart-2/50 text-chart-2">
            Significant Flares
          </Badge>
          <p className="text-xs text-muted-foreground mt-2">
            M-class and X-class solar flares detected
          </p>
        </Card>
      </div>

      <div className="mt-6 p-4 bg-secondary/20 rounded-lg border border-secondary/30">
        <h4 className="font-semibold text-foreground mb-2">Trend Analysis</h4>
        <div className="space-y-2 text-sm text-muted-foreground">
          <p>
            <span className="font-semibold text-foreground">Pattern:</span> {correlationStrength > 0 
              ? 'Increased solar activity correlates with higher market coherence'
              : 'Solar activity shows inverse relationship with coherence during this period'}
          </p>
          <p>
            <span className="font-semibold text-foreground">7-Day Trend:</span> Market coherence is {
              trendDirection === 'up' ? 'improving steadily' :
              trendDirection === 'down' ? 'declining gradually' :
              'remaining stable'
            } compared to the previous week
          </p>
          <p>
            <span className="font-semibold text-foreground">Forecast:</span> {
              correlationStrength > 0.5 && trendDirection === 'up' 
                ? 'Strong upward momentum expected to continue with favorable space weather'
                : correlationStrength > 0.3
                ? 'Moderate correlation suggests continued influence from solar conditions'
                : 'Solar activity impact appears limited in current market conditions'
            }
          </p>
        </div>
      </div>
    </Card>
  );
};
