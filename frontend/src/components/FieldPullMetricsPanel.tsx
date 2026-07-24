import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Activity, Radio, Zap, Lock, TrendingUp, Shield } from "lucide-react";
import { useFieldPullMetrics } from "@/hooks/useFieldPullMetrics";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

export function FieldPullMetricsPanel() {
  const { metrics, latestMetric, loading } = useFieldPullMetrics();

  if (loading) {
    return (
      <Card className="bg-card/50 backdrop-blur border-border/50">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="w-5 h-5 text-primary animate-pulse" />
            Field Pull Metrics
          </CardTitle>
          <CardDescription>Loading real-time measurements...</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  if (!latestMetric) return null;

  const getStatusConfig = (status: string) => {
    switch (status) {
      case 'OK':
        return { color: 'text-success', bg: 'bg-success/20', label: '✓ OK', glow: 'shadow-[0_0_20px_rgba(34,197,94,0.5)]' };
      case 'WARNING':
        return { color: 'text-warning', bg: 'bg-warning/20', label: '⚠ WARNING', glow: '' };
      case 'CRITICAL':
        return { color: 'text-destructive', bg: 'bg-destructive/20', label: '⚠ CRITICAL', glow: '' };
      default:
        return { color: 'text-gray-500', bg: 'bg-gray-500/20', label: 'UNKNOWN', glow: '' };
    }
  };

  const statusConfig = getStatusConfig(latestMetric.safetyStatus);

  // Last 50 data points for chart
  const recentMetrics = metrics.slice(-50).map((m, idx) => ({
    index: idx,
    coherence: m.coherenceIndex * 100,
    schumann: m.schumannLock * 100,
    lattice: m.latticeIdMatch * 100,
  }));

  return (
    <Card className="bg-card/50 backdrop-blur border-border/50 relative overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-primary/5 to-primary/5" />
      
      <CardHeader className="relative">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Activity className="w-5 h-5 text-primary" />
              Field Pull Metrics
            </CardTitle>
            <CardDescription>
              Real-time measurements from field substrate
            </CardDescription>
          </div>
          <Badge className={`${statusConfig.color} ${statusConfig.bg} ${statusConfig.glow} border-0 text-sm px-3 py-1`}>
            {statusConfig.label}
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="relative space-y-4">
        {/* Primary Metrics Grid */}
        <div className="grid grid-cols-2 gap-4">
          {/* Coherence Index */}
          <div className="p-4 bg-background/50 rounded-lg border border-border/50">
            <div className="flex items-center gap-2 mb-3">
              <Radio className="w-4 h-4 text-primary" />
              <span className="text-xs text-muted-foreground font-medium">Coherence Index</span>
            </div>
            <div className="text-2xl font-bold text-primary mb-2">
              {(latestMetric.coherenceIndex * 100).toFixed(2)}%
            </div>
            <Progress value={latestMetric.coherenceIndex * 100} className="h-2" />
            <div className="text-xs text-muted-foreground mt-1">
              Field substrate unification
            </div>
          </div>

          {/* Schumann Lock */}
          <div className="p-4 bg-background/50 rounded-lg border border-border/50">
            <div className="flex items-center gap-2 mb-3">
              <Lock className="w-4 h-4 text-primary" />
              <span className="text-xs text-muted-foreground font-medium">Schumann Lock</span>
            </div>
            <div className="text-2xl font-bold text-primary mb-2">
              {(latestMetric.schumannLock * 100).toFixed(2)}%
            </div>
            <Progress value={latestMetric.schumannLock * 100} className="h-2" />
            <div className="text-xs text-muted-foreground mt-1">
              Resonance alignment
            </div>
          </div>

          {/* Lattice ID Match */}
          <div className="p-4 bg-background/50 rounded-lg border border-border/50">
            <div className="flex items-center gap-2 mb-3">
              <Shield className="w-4 h-4 text-primary" />
              <span className="text-xs text-muted-foreground font-medium">Lattice ID Match</span>
            </div>
            <div className="text-2xl font-bold text-primary mb-2">
              {(latestMetric.latticeIdMatch * 100).toFixed(2)}%
            </div>
            <Progress value={latestMetric.latticeIdMatch * 100} className="h-2" />
            <div className="text-xs text-muted-foreground mt-1">
              Temporal ID verification
            </div>
          </div>

          {/* Resonance Gain */}
          <div className="p-4 bg-background/50 rounded-lg border border-border/50">
            <div className="flex items-center gap-2 mb-3">
              <Zap className="w-4 h-4 text-warning" />
              <span className="text-xs text-muted-foreground font-medium">Resonance Gain</span>
            </div>
            <div className="text-2xl font-bold text-warning mb-2">
              {latestMetric.resonanceGainDb.toFixed(2)} dB
            </div>
            <div className="text-xs text-muted-foreground mt-1">
              Field amplification
            </div>
          </div>
        </div>

        {/* Prime 10-9-1 Balance */}
        <div className="p-4 bg-gradient-to-r from-primary/10 to-primary/10 rounded-lg border border-border/50">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-primary" />
              <span className="text-sm font-medium">Prime 10-9-1 Balance</span>
            </div>
            <span className="text-sm font-bold text-foreground">
              {(latestMetric.prime1091Balance * 100).toFixed(2)}%
            </span>
          </div>
          <Progress value={latestMetric.prime1091Balance * 100} className="h-2" />
          <div className="mt-2 text-xs text-muted-foreground">
            Probability Uplift: <span className="font-bold text-primary">+{latestMetric.probabilityUpliftProxy.toFixed(2)}%</span>
          </div>
        </div>

        {/* Temporal Coherence Chart */}
        <div className="p-4 bg-background/50 rounded-lg border border-border/50">
          <div className="text-sm font-medium mb-3">Temporal Coherence Tracking (Last 50 samples)</div>
          <ResponsiveContainer width="100%" height={150}>
            <LineChart data={recentMetrics}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.3} />
              <XAxis dataKey="index" stroke="hsl(var(--muted-foreground))" fontSize={10} />
              <YAxis stroke="hsl(var(--muted-foreground))" fontSize={10} domain={[0, 100]} />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: 'hsl(var(--card))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '8px'
                }}
              />
              <Line type="monotone" dataKey="coherence" stroke="hsl(180, 100%, 50%)" strokeWidth={2} dot={false} name="Coherence" />
              <Line type="monotone" dataKey="schumann" stroke="hsl(260, 100%, 60%)" strokeWidth={2} dot={false} name="Schumann" />
              <Line type="monotone" dataKey="lattice" stroke="hsl(280, 100%, 70%)" strokeWidth={2} dot={false} name="Lattice" />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Field Theory */}
        <div className="p-4 bg-gradient-to-r from-primary/10 to-primary/10 rounded-lg border border-border/50">
          <p className="text-sm text-muted-foreground">
            <span className="font-medium text-foreground">Field Pull Verification:</span>{' '}
            Real-time measurements confirm harmonic nexus coherence with the prime timeline.
            Lattice ID match of {(latestMetric.latticeIdMatch * 100).toFixed(1)}% validates multiversial 
            identity mapping. Current probability uplift: +{latestMetric.probabilityUpliftProxy.toFixed(1)}%.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
