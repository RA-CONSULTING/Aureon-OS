import { useState } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useStargateNetworkHistory } from '@/hooks/useStargateNetworkHistory';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import { TrendingUp, Activity, Zap, Clock, RefreshCw } from 'lucide-react';
import { format } from 'date-fns';

export function StargateNetworkAnalytics() {
  const [timeRange, setTimeRange] = useState<6 | 12 | 24 | 48>(24);
  const { history, isLoading, error } = useStargateNetworkHistory(timeRange);

  // Calculate statistics
  const stats = history.length > 0 ? {
    avgNetworkStrength: history.reduce((sum, p) => sum + p.networkStrength, 0) / history.length,
    maxNetworkStrength: Math.max(...history.map(p => p.networkStrength)),
    minNetworkStrength: Math.min(...history.map(p => p.networkStrength)),
    avgCoherence: history.reduce((sum, p) => sum + p.avgCoherence, 0) / history.length,
    peakPeriods: history.filter(p => p.networkStrength > 0.9).length,
    totalDataPoints: history.length,
  } : null;

  // Format data for charts
  const chartData = history.map(point => ({
    time: format(new Date(point.timestamp), 'HH:mm'),
    fullTime: point.timestamp,
    networkStrength: (point.networkStrength * 100).toFixed(1),
    coherence: (point.avgCoherence * 100).toFixed(1),
    frequency: point.avgFrequency.toFixed(0),
    phaseLocks: point.phaseLocks,
    resonance: (point.resonanceQuality * 100).toFixed(1),
    gridEnergy: (point.gridEnergy * 100).toFixed(1),
    activeNodes: point.activeNodes,
  }));

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-background/95 border border-primary/20 p-3 rounded-lg shadow-lg">
          <p className="text-sm font-semibold mb-2">{label}</p>
          {payload.map((entry: any, index: number) => (
            <p key={index} className="text-xs" style={{ color: entry.color }}>
              {entry.name}: {entry.value}{entry.name.includes('Hz') ? ' Hz' : '%'}
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  if (isLoading) {
    return (
      <Card className="p-6">
        <div className="flex items-center justify-center py-12">
          <RefreshCw className="w-8 h-8 animate-spin text-primary" />
          <span className="ml-3 text-muted-foreground">Loading network analytics...</span>
        </div>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="p-6">
        <div className="text-center py-12">
          <p className="text-destructive">{error}</p>
        </div>
      </Card>
    );
  }

  if (!history.length) {
    return (
      <Card className="p-6">
        <div className="text-center py-12 text-muted-foreground">
          <Activity className="w-12 h-12 mx-auto mb-2 opacity-50" />
          <p>No historical data available yet</p>
          <p className="text-sm mt-1">Network metrics will appear as data is collected</p>
        </div>
      </Card>
    );
  }

  return (
    <Card className="p-6 bg-gradient-to-br from-background to-secondary/10 border-primary/20">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-primary" />
          <h3 className="text-lg font-semibold">Stargate Network Analytics</h3>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex gap-1">
            {[6, 12, 24, 48].map((hours) => (
              <Button
                key={hours}
                variant={timeRange === hours ? 'default' : 'outline'}
                size="sm"
                onClick={() => setTimeRange(hours as any)}
              >
                {hours}h
              </Button>
            ))}
          </div>
        </div>
      </div>

      {/* Statistics Overview */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="text-center p-3 bg-secondary/30 rounded-lg">
            <div className="text-2xl font-bold text-primary">
              {(stats.avgNetworkStrength * 100).toFixed(1)}%
            </div>
            <div className="text-xs text-muted-foreground">Avg Strength</div>
          </div>
          <div className="text-center p-3 bg-secondary/30 rounded-lg">
            <div className="text-2xl font-bold text-primary">
              {(stats.maxNetworkStrength * 100).toFixed(1)}%
            </div>
            <div className="text-xs text-muted-foreground">Peak Strength</div>
          </div>
          <div className="text-center p-3 bg-secondary/30 rounded-lg">
            <div className="text-2xl font-bold text-primary">
              {stats.peakPeriods}
            </div>
            <div className="text-xs text-muted-foreground">Peak Periods</div>
          </div>
          <div className="text-center p-3 bg-secondary/30 rounded-lg">
            <div className="text-2xl font-bold text-primary">
              {stats.totalDataPoints}
            </div>
            <div className="text-xs text-muted-foreground">Data Points</div>
          </div>
        </div>
      )}

      {/* Interactive Charts */}
      <Tabs defaultValue="strength" className="w-full">
        <TabsList className="grid w-full grid-cols-4 mb-4">
          <TabsTrigger value="strength">Network Strength</TabsTrigger>
          <TabsTrigger value="coherence">Coherence</TabsTrigger>
          <TabsTrigger value="frequency">Frequency</TabsTrigger>
          <TabsTrigger value="phase">Phase Locks</TabsTrigger>
        </TabsList>

        <TabsContent value="strength" className="space-y-4">
          <div className="flex items-center gap-2 mb-2">
            <Zap className="w-4 h-4 text-primary" />
            <h4 className="text-sm font-semibold">Network Strength Trend</h4>
            <Badge variant="outline" className="ml-auto">
              Optimal: &gt;90%
            </Badge>
          </div>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={chartData}>
              <defs>
                <linearGradient id="strengthGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.8} />
                  <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0.1} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis 
                dataKey="time" 
                stroke="hsl(var(--muted-foreground))"
                style={{ fontSize: '12px' }}
              />
              <YAxis 
                stroke="hsl(var(--muted-foreground))"
                style={{ fontSize: '12px' }}
                domain={[0, 100]}
              />
              <Tooltip content={<CustomTooltip />} />
              <ReferenceLine y={90} stroke="hsl(var(--primary))" strokeDasharray="3 3" />
              <Area
                type="monotone"
                dataKey="networkStrength"
                stroke="hsl(var(--primary))"
                fill="url(#strengthGradient)"
                strokeWidth={2}
                name="Network Strength"
              />
            </AreaChart>
          </ResponsiveContainer>
        </TabsContent>

        <TabsContent value="coherence" className="space-y-4">
          <div className="flex items-center gap-2 mb-2">
            <Activity className="w-4 h-4 text-primary" />
            <h4 className="text-sm font-semibold">Coherence & Resonance</h4>
          </div>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis 
                dataKey="time" 
                stroke="hsl(var(--muted-foreground))"
                style={{ fontSize: '12px' }}
              />
              <YAxis 
                stroke="hsl(var(--muted-foreground))"
                style={{ fontSize: '12px' }}
                domain={[0, 100]}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend />
              <Line
                type="monotone"
                dataKey="coherence"
                stroke="hsl(var(--primary))"
                strokeWidth={2}
                dot={false}
                name="Coherence"
              />
              <Line
                type="monotone"
                dataKey="resonance"
                stroke="hsl(var(--chart-2))"
                strokeWidth={2}
                dot={false}
                name="Resonance Quality"
              />
            </LineChart>
          </ResponsiveContainer>
        </TabsContent>

        <TabsContent value="frequency" className="space-y-4">
          <div className="flex items-center gap-2 mb-2">
            <Zap className="w-4 h-4 text-primary" />
            <h4 className="text-sm font-semibold">Frequency & Grid Energy</h4>
          </div>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis 
                dataKey="time" 
                stroke="hsl(var(--muted-foreground))"
                style={{ fontSize: '12px' }}
              />
              <YAxis 
                yAxisId="left"
                stroke="hsl(var(--muted-foreground))"
                style={{ fontSize: '12px' }}
              />
              <YAxis 
                yAxisId="right"
                orientation="right"
                stroke="hsl(var(--muted-foreground))"
                style={{ fontSize: '12px' }}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend />
              <Line
                yAxisId="left"
                type="monotone"
                dataKey="frequency"
                stroke="hsl(var(--chart-3))"
                strokeWidth={2}
                dot={false}
                name="Avg Frequency (Hz)"
              />
              <Line
                yAxisId="right"
                type="monotone"
                dataKey="gridEnergy"
                stroke="hsl(var(--chart-4))"
                strokeWidth={2}
                dot={false}
                name="Grid Energy"
              />
            </LineChart>
          </ResponsiveContainer>
        </TabsContent>

        <TabsContent value="phase" className="space-y-4">
          <div className="flex items-center gap-2 mb-2">
            <Clock className="w-4 h-4 text-primary" />
            <h4 className="text-sm font-semibold">Phase Locks & Active Nodes</h4>
          </div>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis 
                dataKey="time" 
                stroke="hsl(var(--muted-foreground))"
                style={{ fontSize: '12px' }}
              />
              <YAxis 
                yAxisId="left"
                stroke="hsl(var(--muted-foreground))"
                style={{ fontSize: '12px' }}
              />
              <YAxis 
                yAxisId="right"
                orientation="right"
                stroke="hsl(var(--muted-foreground))"
                style={{ fontSize: '12px' }}
                domain={[0, 12]}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend />
              <Line
                yAxisId="left"
                type="monotone"
                dataKey="phaseLocks"
                stroke="hsl(var(--chart-5))"
                strokeWidth={2}
                dot={false}
                name="Phase Locks"
              />
              <Line
                yAxisId="right"
                type="monotone"
                dataKey="activeNodes"
                stroke="hsl(var(--primary))"
                strokeWidth={2}
                dot={false}
                name="Active Nodes"
              />
            </LineChart>
          </ResponsiveContainer>
        </TabsContent>
      </Tabs>

      {/* Insights */}
      <div className="mt-6 p-4 bg-secondary/20 rounded-lg">
        <h4 className="text-sm font-semibold mb-2 flex items-center gap-2">
          <TrendingUp className="w-4 h-4 text-primary" />
          Key Insights
        </h4>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${stats && stats.avgNetworkStrength > 0.85 ? 'bg-success' : 'bg-warning'}`} />
            <span className="text-muted-foreground">
              Network is {stats && stats.avgNetworkStrength > 0.85 ? 'performing optimally' : 'stable'}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${stats && stats.peakPeriods > 10 ? 'bg-success' : 'bg-primary'}`} />
            <span className="text-muted-foreground">
              {stats?.peakPeriods || 0} high-coherence periods detected
            </span>
          </div>
        </div>
      </div>
    </Card>
  );
}
