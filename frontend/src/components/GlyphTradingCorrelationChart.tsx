import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { useGlyphTradingCorrelation } from '@/hooks/useGlyphTradingCorrelation';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine } from 'recharts';
import { TrendingUp, RefreshCw, Lightbulb, Target, Activity } from 'lucide-react';
import { format } from 'date-fns';

const GLYPH_COLORS: Record<number, string> = {
  396: '#3b82f6', // blue
  432: '#eab308', // yellow
  528: '#22c55e', // green
  639: '#a855f7', // purple
  741: '#06b6d4', // cyan
  852: '#ec4899', // pink
  963: '#8b5cf6', // violet
};

export function GlyphTradingCorrelationChart() {
  const { correlation, isAnalyzing, error, refresh } = useGlyphTradingCorrelation(7);

  if (isAnalyzing) {
    return (
      <Card className="border-primary/20">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5 text-primary" />
            Historical Glyph-Trading Correlation
          </CardTitle>
          <CardDescription>Analyzing patterns...</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Skeleton className="h-64 w-full" />
          <Skeleton className="h-32 w-full" />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="border-destructive/20">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-destructive">
            <TrendingUp className="h-5 w-5" />
            Historical Glyph-Trading Correlation
          </CardTitle>
          <CardDescription>Error: {error}</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  if (!correlation || correlation.glyphActivations.length === 0) {
    return (
      <Card className="border-muted">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5 text-muted-foreground" />
            Historical Glyph-Trading Correlation
          </CardTitle>
          <CardDescription>
            Insufficient historical data. Correlation analysis will be available after collecting more trading and field data.
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  // Prepare activation timeline data
  const activationTimeline = correlation.glyphActivations.map(activation => ({
    time: format(new Date(activation.startTime), 'MMM dd HH:mm'),
    timestamp: new Date(activation.startTime).getTime(),
    frequency: activation.frequency,
    glyphName: activation.glyphName.split(' (')[0],
    resonance: activation.avgResonance * 100,
    duration: activation.duration,
  }));

  // Prepare trading windows data
  const tradingWindowData = correlation.tradingWindows.map(window => ({
    time: format(new Date(window.startTime), 'MMM dd HH:mm'),
    timestamp: new Date(window.startTime).getTime(),
    winRate: window.winRate * 100,
    trades: window.totalTradesCount,
    coherence: window.avgCoherence,
    dominantFreq: window.dominantFrequency,
  }));

  // Group activations by frequency for summary
  const frequencySummary = Object.entries(
    correlation.glyphActivations.reduce((acc, act) => {
      if (!acc[act.frequency]) {
        acc[act.frequency] = {
          frequency: act.frequency,
          name: act.glyphName.split(' (')[0],
          count: 0,
          totalDuration: 0,
          avgResonance: 0,
        };
      }
      acc[act.frequency].count++;
      acc[act.frequency].totalDuration += act.duration;
      acc[act.frequency].avgResonance += act.avgResonance;
      return acc;
    }, {} as Record<number, any>)
  ).map(([_, data]) => ({
    ...data,
    avgResonance: (data.avgResonance / data.count) * 100,
    avgDuration: data.totalDuration / data.count,
  }));

  const getCorrelationColor = (score: number) => {
    if (score > 0.7) return 'text-success';
    if (score > 0.4) return 'text-warning';
    return 'text-warning';
  };

  const getCorrelationLabel = (score: number) => {
    if (score > 0.7) return 'Strong';
    if (score > 0.4) return 'Moderate';
    return 'Weak';
  };

  return (
    <Card className="border-primary/20">
      <CardHeader>
        <div className="flex items-start justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-primary" />
              Historical Glyph-Trading Correlation
            </CardTitle>
            <CardDescription>
              7-day analysis of glyph activation patterns vs profitable trading windows
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <Badge className={getCorrelationColor(correlation.correlationScore)}>
              {getCorrelationLabel(correlation.correlationScore)}: {(correlation.correlationScore * 100).toFixed(0)}%
            </Badge>
            <Button
              variant="outline"
              size="sm"
              onClick={refresh}
              disabled={isAnalyzing}
            >
              <RefreshCw className={`h-4 w-4 ${isAnalyzing ? 'animate-spin' : ''}`} />
            </Button>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-6">
        {/* Insights */}
        {correlation.insights.length > 0 && (
          <div className="p-4 bg-primary/5 rounded-lg border border-primary/20">
            <div className="flex items-start gap-2 mb-2">
              <Lightbulb className="h-5 w-5 text-primary mt-0.5" />
              <h4 className="font-semibold text-foreground">Key Insights</h4>
            </div>
            <ul className="space-y-1 text-sm text-muted-foreground">
              {correlation.insights.map((insight, idx) => (
                <li key={idx} className="flex items-start gap-2">
                  <span className="text-primary mt-1">•</span>
                  <span>{insight}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Trading Windows Win Rate Chart */}
        {tradingWindowData.length > 0 && (
          <div>
            <h4 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
              <Target className="h-4 w-4" />
              Trading Window Performance
            </h4>
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={tradingWindowData}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis 
                  dataKey="time" 
                  tick={{ fontSize: 10 }}
                  className="text-muted-foreground"
                />
                <YAxis 
                  tick={{ fontSize: 10 }}
                  className="text-muted-foreground"
                  label={{ value: 'Win Rate %', angle: -90, position: 'insideLeft', fontSize: 10 }}
                />
                <Tooltip
                  contentStyle={{ 
                    backgroundColor: 'hsl(var(--background))',
                    border: '1px solid hsl(var(--border))',
                    borderRadius: '6px',
                    fontSize: '12px'
                  }}
                  formatter={(value: any, name: string) => {
                    if (name === 'winRate') return [`${value.toFixed(1)}%`, 'Win Rate'];
                    if (name === 'coherence') return [value.toFixed(3), 'Coherence'];
                    return [value, name];
                  }}
                />
                <Legend wrapperStyle={{ fontSize: '12px' }} />
                <ReferenceLine y={60} stroke="hsl(var(--primary))" strokeDasharray="3 3" />
                <Line 
                  type="monotone" 
                  dataKey="winRate" 
                  stroke="hsl(var(--primary))" 
                  strokeWidth={2}
                  dot={{ r: 3 }}
                  name="Win Rate"
                />
                <Line 
                  type="monotone" 
                  dataKey="coherence" 
                  stroke="hsl(var(--muted-foreground))" 
                  strokeWidth={1}
                  strokeDasharray="3 3"
                  dot={false}
                  name="Coherence"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Glyph Activation Frequency Summary */}
        {frequencySummary.length > 0 && (
          <div>
            <h4 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
              <Activity className="h-4 w-4" />
              Glyph Activation Summary
            </h4>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={frequencySummary}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis 
                  dataKey="name" 
                  tick={{ fontSize: 10 }}
                  className="text-muted-foreground"
                />
                <YAxis 
                  tick={{ fontSize: 10 }}
                  className="text-muted-foreground"
                  label={{ value: 'Activations', angle: -90, position: 'insideLeft', fontSize: 10 }}
                />
                <Tooltip
                  contentStyle={{ 
                    backgroundColor: 'hsl(var(--background))',
                    border: '1px solid hsl(var(--border))',
                    borderRadius: '6px',
                    fontSize: '12px'
                  }}
                  formatter={(value: any, name: string) => {
                    if (name === 'count') return [value, 'Activations'];
                    if (name === 'avgResonance') return [`${value.toFixed(1)}%`, 'Avg Resonance'];
                    if (name === 'avgDuration') return [`${value.toFixed(1)} min`, 'Avg Duration'];
                    return [value, name];
                  }}
                />
                <Legend wrapperStyle={{ fontSize: '12px' }} />
                <Bar 
                  dataKey="count" 
                  fill="hsl(var(--primary))"
                  name="Activations"
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Recent Activations List */}
        {activationTimeline.length > 0 && (
          <div>
            <h4 className="text-sm font-semibold text-foreground mb-3">
              Recent Glyph Activations (Last 10)
            </h4>
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {activationTimeline.slice(-10).reverse().map((activation, idx) => (
                <div
                  key={idx}
                  className="p-3 rounded-lg bg-muted/50 border border-border text-sm"
                >
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-2">
                      <div
                        className="w-3 h-3 rounded-full"
                        style={{ backgroundColor: GLYPH_COLORS[activation.frequency] }}
                      />
                      <span className="font-medium text-foreground">{activation.glyphName}</span>
                      <Badge variant="outline" className="text-xs">
                        {activation.frequency} Hz
                      </Badge>
                    </div>
                    <span className="text-xs text-muted-foreground">
                      {activation.time}
                    </span>
                  </div>
                  <div className="flex items-center gap-4 text-xs text-muted-foreground">
                    <span>Resonance: {activation.resonance.toFixed(1)}%</span>
                    <span>Duration: {activation.duration.toFixed(0)} min</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
