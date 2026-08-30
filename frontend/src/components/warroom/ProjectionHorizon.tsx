import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area, ComposedChart } from 'recharts';
import { useProjections } from '@/hooks/useProjections';

export function ProjectionHorizon() {
  const { projections, loading } = useProjections();

  if (loading) {
    return (
      <Card className="bg-card/50 backdrop-blur border-primary/20">
        <CardHeader>
          <CardTitle> 6-Month Projection Horizon</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-64 flex items-center justify-center">
            <p className="text-muted-foreground">Loading projections...</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="bg-card/50 backdrop-blur border-primary/20">
      <CardHeader>
        <CardTitle> 6-Month Projection Horizon (Monte Carlo)</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={250}>
          <ComposedChart data={projections}>
            <CartesianGrid strokeDasharray="3 3" opacity={0.1} />
            <XAxis 
              dataKey="week" 
              label={{ value: 'Weeks', position: 'insideBottom', offset: -5 }}
              style={{ fontSize: '10px' }}
            />
            <YAxis 
              scale="log"
              domain={[10, 100000000]}
              tickFormatter={(val) => val >= 1000000 ? `$${(val/1000000).toFixed(1)}M` : val >= 1000 ? `$${(val/1000).toFixed(0)}K` : `$${val}`}
              style={{ fontSize: '10px' }}
            />
            <Tooltip 
              contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))' }}
              formatter={(value: number) => [
                value >= 1000000 ? `$${(value/1000000).toFixed(2)}M` : value >= 1000 ? `$${(value/1000).toFixed(2)}K` : `$${value.toFixed(2)}`,
                ''
              ]}
            />
            <Area
              type="monotone"
              dataKey="p75"
              stroke="none"
              fill="hsl(var(--primary))"
              fillOpacity={0.1}
            />
            <Area
              type="monotone"
              dataKey="p25"
              stroke="none"
              fill="hsl(var(--card))"
              fillOpacity={1}
            />
            <Line 
              type="monotone" 
              dataKey="median" 
              stroke="hsl(var(--primary))" 
              strokeWidth={3}
              dot={(props: any) => {
                const milestone = projections[props.index]?.milestone;
                if (milestone) {
                  return (
                    <circle
                      cx={props.cx}
                      cy={props.cy}
                      r={6}
                      fill="hsl(var(--primary))"
                      stroke="hsl(var(--background))"
                      strokeWidth={2}
                    />
                  );
                }
                return null;
              }}
            />
          </ComposedChart>
        </ResponsiveContainer>

        {/* Milestones */}
        <div className="mt-4 flex flex-wrap gap-2 justify-center">
          {projections
            .filter(p => p.milestone)
            .map((p, idx) => (
              <div
                key={idx}
                className="text-xs px-3 py-1 rounded-full bg-primary/20 border border-primary/50"
              >
                Week {p.week}: {p.milestone}
              </div>
            ))}
        </div>
      </CardContent>
    </Card>
  );
}
