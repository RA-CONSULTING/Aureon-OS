import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { adaptiveFilterThresholds } from '@/core/adaptiveFilterThresholds';
import { Activity, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { cn } from '@/lib/utils';

type MarketRegime = 'TRENDING' | 'VOLATILE' | 'RANGING' | 'NORMAL';

const regimeConfig: Record<MarketRegime, { icon: typeof Activity; color: string; bg: string }> = {
  'TRENDING': { icon: TrendingUp, color: 'text-success', bg: 'bg-success/10' },
  'VOLATILE': { icon: Activity, color: 'text-primary', bg: 'bg-primary/10' },
  'RANGING': { icon: Minus, color: 'text-warning', bg: 'bg-warning/10' },
  'NORMAL': { icon: Minus, color: 'text-muted-foreground', bg: 'bg-muted/30' }
};

export const MarketRegimeIndicator = () => {
  const [regime, setRegime] = useState<MarketRegime>('NORMAL');
  const [thresholds, setThresholds] = useState({ 
    minCoherence: 0.7, 
    minMomentum: 0.01, 
    maxPositions: 6 
  });

  useEffect(() => {
    const interval = setInterval(() => {
      setRegime(adaptiveFilterThresholds.getCurrentRegime());
      const current = adaptiveFilterThresholds.getCurrentThresholds();
      setThresholds({
        minCoherence: current.minCoherence,
        minMomentum: current.minMomentum,
        maxPositions: current.maxPositions
      });
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  const config = regimeConfig[regime];
  const Icon = config.icon;

  return (
    <Card className="border-border/50 bg-card/50 backdrop-blur">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-sm font-medium">
          <Activity className="h-4 w-4 text-primary" />
          Market Regime
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className={cn("flex items-center justify-center gap-3 p-4 rounded-lg", config.bg)}>
          <Icon className={cn("h-8 w-8", config.color)} />
          <div className="text-center">
            <Badge variant="outline" className={cn("text-sm font-bold", config.color)}>
              {regime}
            </Badge>
          </div>
        </div>

        <div className="space-y-2">
          <div className="text-xs text-muted-foreground mb-2">Adapted Thresholds</div>
          <div className="grid grid-cols-3 gap-2 text-xs">
            <div className="text-center p-2 rounded bg-muted/30">
              <div className="text-muted-foreground">Coherence</div>
              <div className="font-mono font-bold text-primary">
                {(thresholds.minCoherence * 100).toFixed(0)}%
              </div>
            </div>
            <div className="text-center p-2 rounded bg-muted/30">
              <div className="text-muted-foreground">Momentum</div>
              <div className="font-mono font-bold text-primary">
                {(thresholds.minMomentum * 100).toFixed(1)}%
              </div>
            </div>
            <div className="text-center p-2 rounded bg-muted/30">
              <div className="text-muted-foreground">Max Pos</div>
              <div className="font-mono font-bold text-primary">
                {thresholds.maxPositions}
              </div>
            </div>
          </div>
        </div>

        <div className="text-[10px] text-muted-foreground text-center">
          Thresholds adapt based on market conditions
        </div>
      </CardContent>
    </Card>
  );
};
