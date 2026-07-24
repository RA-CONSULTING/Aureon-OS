import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { useHistoricalData } from '@/hooks/useHistoricalData';

export function HistoricalTimeline() {
  const { data, loading } = useHistoricalData();

  if (loading) {
    return (
      <Card className="bg-card/50 backdrop-blur border-primary/20">
        <CardHeader>
          <CardTitle> Historical Performance (24h)</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-64 flex items-center justify-center">
            <p className="text-muted-foreground">Loading historical data...</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="bg-card/50 backdrop-blur border-primary/20">
      <CardHeader>
        <CardTitle> Historical Performance (24h)</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={250}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" opacity={0.1} />
            <XAxis 
              dataKey="timestamp" 
              tickFormatter={(val) => new Date(val).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              style={{ fontSize: '10px' }}
            />
            <YAxis yAxisId="left" style={{ fontSize: '10px' }} />
            <YAxis yAxisId="right" orientation="right" style={{ fontSize: '10px' }} />
            <Tooltip 
              contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))' }}
              labelFormatter={(val) => new Date(val).toLocaleString()}
            />
            <Legend />
            <Line 
              yAxisId="left"
              type="monotone" 
              dataKey="coherence" 
              stroke="hsl(var(--primary))" 
              strokeWidth={2}
              name="Coherence"
              dot={false}
            />
            <Line 
              yAxisId="left"
              type="monotone" 
              dataKey="lighthouse"
              stroke="hsl(var(--chart-2))"
              strokeWidth={2}
              name="Lighthouse"
              dot={false}
            />
            <Line 
              yAxisId="right"
              type="monotone" 
              dataKey="balance"
              stroke="hsl(var(--success))"
              strokeWidth={2}
              name="Balance ($)"
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
