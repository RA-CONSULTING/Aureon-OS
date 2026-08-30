import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { Activity, Brain, TrendingUp } from "lucide-react";
import { format } from 'date-fns';
import { useConsciousnessHistory } from "@/hooks/useConsciousnessHistory";

export function ConsciousnessHistoryChart() {
  const { historyData, isLoading } = useConsciousnessHistory(24);

  // Calculate correlation between Schumann and biometric coherence
  const calculateCorrelation = () => {
    const validData = historyData.filter(d => d.biometric_coherence_index !== null);
    if (validData.length < 2) return 0;

    const n = validData.length;
    const schumannValues = validData.map(d => d.schumann_coherence_boost);
    const biometricValues = validData.map(d => d.biometric_coherence_index!);

    const meanSchumann = schumannValues.reduce((a, b) => a + b, 0) / n;
    const meanBiometric = biometricValues.reduce((a, b) => a + b, 0) / n;

    let numerator = 0;
    let denomSchumann = 0;
    let denomBiometric = 0;

    for (let i = 0; i < n; i++) {
      const diffSchumann = schumannValues[i] - meanSchumann;
      const diffBiometric = biometricValues[i] - meanBiometric;
      numerator += diffSchumann * diffBiometric;
      denomSchumann += diffSchumann * diffSchumann;
      denomBiometric += diffBiometric * diffBiometric;
    }

    const correlation = numerator / Math.sqrt(denomSchumann * denomBiometric);
    return isNaN(correlation) ? 0 : correlation;
  };

  const correlation = calculateCorrelation();

  // Prepare chart data
  const chartData = historyData.map(item => ({
    time: format(new Date(item.timestamp), 'HH:mm'),
    fullTime: format(new Date(item.timestamp), 'MMM dd HH:mm'),
    schumannFreq: Number(item.schumann_frequency),
    schumannBoost: Number(item.schumann_coherence_boost) * 100,
    biometricCoherence: item.biometric_coherence_index ? Number(item.biometric_coherence_index) * 100 : null,
    totalCoherence: Number(item.total_coherence) * 100,
    hrv: item.hrv,
    heartRate: item.heart_rate,
  }));

  const getCorrelationStatus = (corr: number) => {
    if (Math.abs(corr) >= 0.7) return { text: 'Strong', color: 'text-success' };
    if (Math.abs(corr) >= 0.4) return { text: 'Moderate', color: 'text-primary' };
    if (Math.abs(corr) >= 0.2) return { text: 'Weak', color: 'text-warning' };
    return { text: 'Minimal', color: 'text-muted-foreground' };
  };

  const corrStatus = getCorrelationStatus(correlation);

  if (isLoading) {
    return (
      <Card className="bg-card/50 backdrop-blur border-border/50">
        <CardContent className="p-6">
          <p className="text-muted-foreground text-center">Loading consciousness field history...</p>
        </CardContent>
      </Card>
    );
  }

  if (chartData.length === 0) {
    return (
      <Card className="bg-card/50 backdrop-blur border-border/50">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-primary" />
            24-Hour Consciousness Field Trends
          </CardTitle>
          <CardDescription>Historical tracking and correlation analysis</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground text-center py-8">
            No historical data available yet. Data will appear as sensors stream information.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="bg-card/50 backdrop-blur border-border/50">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-primary" />
              24-Hour Consciousness Field Trends
            </CardTitle>
            <CardDescription>
              Real-time tracking of {chartData.length} data points over the last 24 hours
            </CardDescription>
          </div>
          <div className="text-right">
            <div className="text-xs text-muted-foreground mb-1">Correlation Strength</div>
            <div className={`text-2xl font-bold ${corrStatus.color}`}>
              {(correlation * 100).toFixed(1)}%
            </div>
            <div className="text-xs text-muted-foreground">{corrStatus.text}</div>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-6">
        {/* Main Coherence Trend */}
        <div>
          <h4 className="text-sm font-semibold mb-3 flex items-center gap-2">
            <Brain className="w-4 h-4 text-primary" />
            Total Field Coherence
          </h4>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.3} />
              <XAxis 
                dataKey="time" 
                stroke="hsl(var(--muted-foreground))"
                fontSize={12}
                tick={{ fill: 'hsl(var(--muted-foreground))' }}
              />
              <YAxis 
                stroke="hsl(var(--muted-foreground))"
                fontSize={12}
                tick={{ fill: 'hsl(var(--muted-foreground))' }}
                domain={[0, 100]}
              />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: 'hsl(var(--card))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '6px'
                }}
                labelFormatter={(label, payload) => payload[0]?.payload?.fullTime || label}
              />
              <Legend />
              <Line 
                type="monotone" 
                dataKey="totalCoherence" 
                stroke="hsl(280, 100%, 70%)"
                strokeWidth={3}
                name="Total Coherence (%)"
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Schumann vs Biometric Comparison */}
        <div>
          <h4 className="text-sm font-semibold mb-3 flex items-center gap-2">
            <Activity className="w-4 h-4 text-success" />
            Schumann & Biometric Correlation
          </h4>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.3} />
              <XAxis 
                dataKey="time" 
                stroke="hsl(var(--muted-foreground))"
                fontSize={12}
                tick={{ fill: 'hsl(var(--muted-foreground))' }}
              />
              <YAxis 
                stroke="hsl(var(--muted-foreground))"
                fontSize={12}
                tick={{ fill: 'hsl(var(--muted-foreground))' }}
              />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: 'hsl(var(--card))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '6px'
                }}
                labelFormatter={(label, payload) => payload[0]?.payload?.fullTime || label}
              />
              <Legend />
              <Line 
                type="monotone" 
                dataKey="schumannBoost" 
                stroke="hsl(142, 76%, 50%)"
                strokeWidth={2}
                name="Schumann Boost (%)"
                dot={false}
              />
              <Line 
                type="monotone" 
                dataKey="biometricCoherence" 
                stroke="hsl(0, 84%, 60%)"
                strokeWidth={2}
                name="Biometric Coherence (%)"
                dot={false}
                connectNulls
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Schumann Frequency Stability */}
        <div>
          <h4 className="text-sm font-semibold mb-3">Schumann Frequency (7.83 Hz baseline)</h4>
          <ResponsiveContainer width="100%" height={150}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.3} />
              <XAxis 
                dataKey="time" 
                stroke="hsl(var(--muted-foreground))"
                fontSize={12}
                tick={{ fill: 'hsl(var(--muted-foreground))' }}
              />
              <YAxis 
                stroke="hsl(var(--muted-foreground))"
                fontSize={12}
                tick={{ fill: 'hsl(var(--muted-foreground))' }}
                domain={[7.6, 8.1]}
              />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: 'hsl(var(--card))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '6px'
                }}
                labelFormatter={(label, payload) => payload[0]?.payload?.fullTime || label}
              />
              <Legend />
              <Line 
                type="monotone" 
                dataKey="schumannFreq" 
                stroke="hsl(142, 76%, 50%)"
                strokeWidth={2}
                name="Frequency (Hz)"
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Correlation Insights */}
        <div className="p-4 bg-muted/50 rounded-lg">
          <h4 className="text-sm font-semibold mb-2">Correlation Analysis</h4>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-muted-foreground">Pearson Correlation:</span>
              <span className={`ml-2 font-bold ${corrStatus.color}`}>
                {correlation.toFixed(3)} ({corrStatus.text})
              </span>
            </div>
            <div>
              <span className="text-muted-foreground">Data Points:</span>
              <span className="ml-2 font-bold">{chartData.length}</span>
            </div>
          </div>
          <p className="text-xs text-muted-foreground mt-3">
            {Math.abs(correlation) >= 0.7 && 
              "Strong correlation detected! Schumann Resonance and biometric coherence are moving together, indicating optimal consciousness field alignment."}
            {Math.abs(correlation) >= 0.4 && Math.abs(correlation) < 0.7 && 
              "Moderate correlation observed. Earth resonance and biological systems show meaningful synchronization."}
            {Math.abs(correlation) < 0.4 && 
              "Correlation is developing. Continue monitoring as more data accumulates for stronger pattern recognition."}
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
