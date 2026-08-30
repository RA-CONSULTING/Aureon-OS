import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useQuery } from "@tanstack/react-query";
import { supabase } from "@/integrations/supabase/client";
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Area, AreaChart } from "recharts";
import { format, parseISO } from "date-fns";
import { Activity, TrendingUp, Clock, Zap } from "lucide-react";

interface SchedulerHistoryEntry {
  id: string;
  timestamp: string;
  action: string;
  reason: string;
  coherence_at_action: number;
  lighthouse_events_count: number;
  trading_enabled_before: boolean;
  trading_enabled_after: boolean;
  daily_activations: number;
  metadata: any;
}

export function SchedulerHistoryCharts() {
  const { data: history, isLoading } = useQuery({
    queryKey: ['scheduler-history'],
    queryFn: async () => {
      const { data, error } = await supabase
        .from('scheduler_history')
        .select('*')
        .order('timestamp', { ascending: true })
        .limit(100);
      
      if (error) throw error;
      return data as SchedulerHistoryEntry[];
    },
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  if (isLoading) {
    return (
      <div className="grid gap-4">
        <Card>
          <CardHeader>
            <CardTitle>Loading Scheduler History...</CardTitle>
          </CardHeader>
        </Card>
      </div>
    );
  }

  if (!history || history.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="w-5 h-5" />
            Scheduler History
          </CardTitle>
          <CardDescription>
            No scheduler decisions recorded yet. The auto-trading scheduler will log decisions here.
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  // Prepare data for charts
  const coherenceData = history.map(entry => ({
    time: format(parseISO(entry.timestamp), 'HH:mm'),
    coherence: Number(entry.coherence_at_action),
    lheCount: entry.lighthouse_events_count,
    action: entry.action,
  }));

  const activationData = history.map(entry => ({
    time: format(parseISO(entry.timestamp), 'HH:mm'),
    dailyActivations: entry.daily_activations,
    enabled: entry.trading_enabled_after ? 1 : 0,
  }));

  const actionCounts = history.reduce((acc, entry) => {
    acc[entry.action] = (acc[entry.action] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const actionData = Object.entries(actionCounts).map(([action, count]) => ({
    action,
    count,
  }));

  const recentDecisions = history.slice(-10).reverse();

  return (
    <div className="grid gap-4">
      {/* Coherence & LHE Timeline */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-primary" />
            Coherence & Lighthouse Events Timeline
          </CardTitle>
          <CardDescription>
            Field coherence and LHE count at each scheduler decision point
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={coherenceData}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis 
                dataKey="time" 
                className="text-xs"
                tick={{ fill: 'hsl(var(--foreground))' }}
              />
              <YAxis 
                yAxisId="left"
                className="text-xs"
                tick={{ fill: 'hsl(var(--foreground))' }}
                label={{ value: 'Coherence', angle: -90, position: 'insideLeft' }}
              />
              <YAxis 
                yAxisId="right" 
                orientation="right"
                className="text-xs"
                tick={{ fill: 'hsl(var(--foreground))' }}
                label={{ value: 'LHE Count', angle: 90, position: 'insideRight' }}
              />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: 'hsl(var(--background))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '6px'
                }}
              />
              <Legend />
              <Area
                yAxisId="left"
                type="monotone"
                dataKey="coherence"
                stroke="hsl(var(--primary))"
                fill="hsl(var(--primary))"
                fillOpacity={0.3}
                name="Coherence"
              />
              <Line
                yAxisId="right"
                type="monotone"
                dataKey="lheCount"
                stroke="hsl(var(--chart-2))"
                strokeWidth={2}
                dot={{ fill: 'hsl(var(--chart-2))', r: 4 }}
                name="LHE Count"
              />
            </AreaChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Daily Activations & Status */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Zap className="w-5 h-5 text-chart-3" />
            Daily Activations & Trading Status
          </CardTitle>
          <CardDescription>
            Number of activations and trading enabled/disabled states
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={activationData}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis 
                dataKey="time" 
                className="text-xs"
                tick={{ fill: 'hsl(var(--foreground))' }}
              />
              <YAxis 
                yAxisId="left"
                className="text-xs"
                tick={{ fill: 'hsl(var(--foreground))' }}
                label={{ value: 'Daily Activations', angle: -90, position: 'insideLeft' }}
              />
              <YAxis 
                yAxisId="right" 
                orientation="right"
                domain={[0, 1]}
                className="text-xs"
                tick={{ fill: 'hsl(var(--foreground))' }}
                label={{ value: 'Status', angle: 90, position: 'insideRight' }}
              />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: 'hsl(var(--background))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '6px'
                }}
              />
              <Legend />
              <Bar
                yAxisId="left"
                dataKey="dailyActivations"
                fill="hsl(var(--chart-3))"
                name="Daily Activations"
                radius={[4, 4, 0, 0]}
              />
              <Bar
                yAxisId="right"
                dataKey="enabled"
                fill="hsl(var(--chart-4))"
                name="Trading Enabled"
                radius={[4, 4, 0, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Action Distribution */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="w-5 h-5 text-chart-5" />
            Scheduler Action Distribution
          </CardTitle>
          <CardDescription>
            Breakdown of enable, disable, and maintain actions
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={actionData} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis 
                type="number"
                className="text-xs"
                tick={{ fill: 'hsl(var(--foreground))' }}
              />
              <YAxis 
                type="category"
                dataKey="action"
                className="text-xs"
                tick={{ fill: 'hsl(var(--foreground))' }}
                width={80}
              />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: 'hsl(var(--background))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '6px'
                }}
              />
              <Bar
                dataKey="count"
                fill="hsl(var(--chart-5))"
                radius={[0, 4, 4, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Recent Decisions Timeline */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Clock className="w-5 h-5 text-primary" />
            Recent Scheduler Decisions
          </CardTitle>
          <CardDescription>
            Last 10 decisions with reasoning and context
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {recentDecisions.map((decision, index) => (
              <div
                key={decision.id}
                className="flex items-start gap-4 p-4 rounded-lg border border-border bg-card/50"
              >
                <div className="flex-shrink-0">
                  <div className={`w-3 h-3 rounded-full mt-1 ${
                    decision.action === 'enable' ? 'bg-success' :
                    decision.action === 'disable' ? 'bg-destructive' :
                    'bg-warning'
                  }`} />
                </div>
                <div className="flex-1 space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="font-medium capitalize">{decision.action} Trading</span>
                    <span className="text-sm text-muted-foreground">
                      {format(parseISO(decision.timestamp), 'MMM dd, HH:mm:ss')}
                    </span>
                  </div>
                  <p className="text-sm text-muted-foreground">{decision.reason}</p>
                  <div className="flex gap-4 text-xs text-muted-foreground mt-2">
                    <span>Coherence: {Number(decision.coherence_at_action).toFixed(3)}</span>
                    <span>LHE: {decision.lighthouse_events_count}</span>
                    <span>Daily Activations: {decision.daily_activations}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}