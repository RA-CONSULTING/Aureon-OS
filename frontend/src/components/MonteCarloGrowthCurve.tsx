import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Area, AreaChart } from "recharts";
import { TrendingUp, Target, Award } from "lucide-react";

export function MonteCarloGrowthCurve() {
  // Projected growth data based on Monte Carlo simulation results from whitepaper
  const projectedGrowth = [
    { 
      period: "Start", 
      median: 15, 
      p25: 15, 
      p75: 15,
      label: "$15"
    },
    { 
      period: "Week 1", 
      median: 39, 
      p25: 32, 
      p75: 48,
      label: "$39"
    },
    { 
      period: "Week 2", 
      median: 100, 
      p25: 81, 
      p75: 125,
      label: "$100"
    },
    { 
      period: "Month 1", 
      median: 859, 
      p25: 682, 
      p75: 1089,
      label: "$859"
    },
    { 
      period: "Month 2", 
      median: 47000, 
      p25: 38200, 
      p75: 58100,
      label: "$47K"
    },
    { 
      period: "Month 3", 
      median: 1160000, 
      p25: 921000, 
      p75: 1450000,
      label: "$1.16M"
    },
    { 
      period: "Month 4", 
      median: 9530000, 
      p25: 7620000, 
      p75: 11890000,
      label: "$9.53M"
    },
    { 
      period: "Month 6", 
      median: 13620000, 
      p25: 10850000, 
      p75: 17010000,
      label: "$13.62M"
    },
  ];

  const formatCurrency = (value: number) => {
    if (value >= 1000000) return `$${(value / 1000000).toFixed(2)}M`;
    if (value >= 1000) return `$${(value / 1000).toFixed(2)}K`;
    return `$${value}`;
  };

  const finalROI = ((13620000 - 15) / 15) * 100;

  return (
    <Card className="bg-card/50 backdrop-blur border-border/50">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5 text-primary" />
            <div>
              <CardTitle className="text-xl font-bold">Monte Carlo Growth Projection</CardTitle>
              <CardDescription>6-month projected trajectory (n=100 simulations)</CardDescription>
            </div>
          </div>
          <div className="flex gap-2">
            <Badge variant="outline" className="text-success">
              100% Success Rate
            </Badge>
            <Badge variant="outline" className="text-primary">
              ROI: {(finalROI / 1000000).toFixed(1)}M%
            </Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Growth Curve Chart */}
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={projectedGrowth}>
              <defs>
                <linearGradient id="colorMedian" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0}/>
                </linearGradient>
                <linearGradient id="colorRange" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="hsl(var(--chart-1))" stopOpacity={0.2}/>
                  <stop offset="95%" stopColor="hsl(var(--chart-1))" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.3} />
              <XAxis 
                dataKey="period" 
                stroke="hsl(var(--muted-foreground))"
                style={{ fontSize: '12px' }}
              />
              <YAxis 
                stroke="hsl(var(--muted-foreground))"
                style={{ fontSize: '12px' }}
                tickFormatter={formatCurrency}
                scale="log"
                domain={[10, 20000000]}
              />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: 'hsl(var(--card))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '8px'
                }}
                formatter={(value: number) => formatCurrency(value)}
              />
              <Legend />
              <Area 
                type="monotone" 
                dataKey="p75" 
                stroke="hsl(var(--chart-1))"
                fillOpacity={1}
                fill="url(#colorRange)"
                name="75th Percentile"
              />
              <Area 
                type="monotone" 
                dataKey="median" 
                stroke="hsl(var(--primary))"
                strokeWidth={3}
                fillOpacity={1}
                fill="url(#colorMedian)"
                name="Median (50th)"
              />
              <Area 
                type="monotone" 
                dataKey="p25" 
                stroke="hsl(var(--chart-2))"
                fillOpacity={0}
                name="25th Percentile"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Key Milestones */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="p-3 bg-muted/30 rounded-lg border border-border/30">
            <div className="flex items-center gap-2 mb-1">
              <Target className="h-4 w-4 text-success" />
              <p className="text-xs text-muted-foreground">Week 2</p>
            </div>
            <p className="text-lg font-bold font-mono text-foreground">$100</p>
            <p className="text-xs text-muted-foreground">First $100</p>
          </div>

          <div className="p-3 bg-muted/30 rounded-lg border border-border/30">
            <div className="flex items-center gap-2 mb-1">
              <Target className="h-4 w-4 text-warning" />
              <p className="text-xs text-muted-foreground">Month 2</p>
            </div>
            <p className="text-lg font-bold font-mono text-foreground">$47K</p>
            <p className="text-xs text-muted-foreground">$50K milestone</p>
          </div>

          <div className="p-3 bg-muted/30 rounded-lg border border-border/30">
            <div className="flex items-center gap-2 mb-1">
              <Award className="h-4 w-4 text-primary" />
              <p className="text-xs text-muted-foreground">Month 3</p>
            </div>
            <p className="text-lg font-bold font-mono text-primary">$1.16M</p>
            <p className="text-xs text-muted-foreground">Millionaire 💎</p>
          </div>

          <div className="p-3 bg-muted/30 rounded-lg border border-border/30">
            <div className="flex items-center gap-2 mb-1">
              <TrendingUp className="h-4 w-4 text-success" />
              <p className="text-xs text-muted-foreground">Month 6</p>
            </div>
            <p className="text-lg font-bold font-mono text-success">$13.62M</p>
            <p className="text-xs text-muted-foreground">Target reached 🏁</p>
          </div>
        </div>

        {/* Distribution Statistics */}
        <div className="p-4 bg-gradient-to-r from-primary/10 to-accent/10 rounded-lg border border-primary/30">
          <h4 className="text-sm font-semibold mb-3 text-foreground">Distribution Statistics (Month 6)</h4>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3 text-xs">
            <div>
              <p className="text-muted-foreground">Minimum</p>
              <p className="font-mono font-semibold text-foreground">$9.65M</p>
            </div>
            <div>
              <p className="text-muted-foreground">25th %ile</p>
              <p className="font-mono font-semibold text-foreground">$10.85M</p>
            </div>
            <div>
              <p className="text-muted-foreground">Median</p>
              <p className="font-mono font-semibold text-primary">$13.62M</p>
            </div>
            <div>
              <p className="text-muted-foreground">75th %ile</p>
              <p className="font-mono font-semibold text-foreground">$17.01M</p>
            </div>
            <div>
              <p className="text-muted-foreground">Maximum</p>
              <p className="font-mono font-semibold text-success">$35.34M</p>
            </div>
          </div>
        </div>

        {/* Constraints Applied */}
        <div className="p-4 bg-background/50 rounded-lg border border-border/30">
          <h4 className="text-sm font-semibold mb-2 text-foreground">Realistic Constraints Applied</h4>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-2 text-xs text-muted-foreground">
            <div className="flex items-center gap-2">
              <div className="h-1.5 w-1.5 rounded-full bg-success" />
              Trading fees: 0.1% per trade
            </div>
            <div className="flex items-center gap-2">
              <div className="h-1.5 w-1.5 rounded-full bg-success" />
              Slippage: 0.01%-1% based on size
            </div>
            <div className="flex items-center gap-2">
              <div className="h-1.5 w-1.5 rounded-full bg-success" />
              Exchange limits: $50M max
            </div>
            <div className="flex items-center gap-2">
              <div className="h-1.5 w-1.5 rounded-full bg-success" />
              API rate limits: 50 trades/day
            </div>
            <div className="flex items-center gap-2">
              <div className="h-1.5 w-1.5 rounded-full bg-success" />
              Market variance: ±10%
            </div>
            <div className="flex items-center gap-2">
              <div className="h-1.5 w-1.5 rounded-full bg-success" />
              Position sizing: 98% compound
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
