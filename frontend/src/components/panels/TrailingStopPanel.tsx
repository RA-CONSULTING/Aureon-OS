import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { trailingStopManager, TrailingStop } from '@/core/trailingStopManager';
import { ShieldCheck, TrendingDown, TrendingUp } from 'lucide-react';
import { cn } from '@/lib/utils';

export const TrailingStopPanel = () => {
  const [stops, setStops] = useState<TrailingStop[]>([]);
  const [stats, setStats] = useState({ totalStops: 0, activeStops: 0, triggeredCount: 0, avgUnrealizedPnl: 0 });

  useEffect(() => {
    const interval = setInterval(() => {
      setStops(trailingStopManager.getAllStops());
      setStats(trailingStopManager.getStats());
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  return (
    <Card className="border-border/50 bg-card/50 backdrop-blur">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-sm font-medium">
          <ShieldCheck className="h-4 w-4 text-primary" />
          Trailing Stop Manager
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="grid grid-cols-4 gap-2 text-xs">
          <div className="text-center p-2 rounded bg-muted/30">
            <div className="text-muted-foreground">Total</div>
            <div className="font-mono font-bold">{stats.totalStops}</div>
          </div>
          <div className="text-center p-2 rounded bg-muted/30">
            <div className="text-muted-foreground">Active</div>
            <div className="font-mono font-bold text-warning">{stats.activeStops}</div>
          </div>
          <div className="text-center p-2 rounded bg-muted/30">
            <div className="text-muted-foreground">Triggered</div>
            <div className="font-mono font-bold text-destructive">{stats.triggeredCount}</div>
          </div>
          <div className="text-center p-2 rounded bg-muted/30">
            <div className="text-muted-foreground">Avg P&L</div>
            <div className={cn("font-mono font-bold", stats.avgUnrealizedPnl >= 0 ? "text-success" : "text-destructive")}>
              {stats.avgUnrealizedPnl.toFixed(2)}%
            </div>
          </div>
        </div>

        <div className="space-y-2 max-h-40 overflow-y-auto">
          {stops.length === 0 ? (
            <div className="text-xs text-muted-foreground text-center py-4">
              No active trailing stops
            </div>
          ) : (
            stops.slice(0, 5).map((stop, i) => (
              <div key={i} className="flex items-center justify-between p-2 rounded bg-muted/20 text-xs">
                <div className="flex items-center gap-2">
                  <Badge variant={stop.isActivated ? "default" : "outline"} className="text-[10px]">
                    {stop.symbol}
                  </Badge>
                  <span className="text-muted-foreground font-mono">
                    Stop: ${stop.trailPrice.toFixed(2)}
                  </span>
                </div>
                <div className="flex items-center gap-1">
                  {stop.unrealizedPnlPct >= 0 ? (
                    <TrendingUp className="h-3 w-3 text-success" />
                  ) : (
                    <TrendingDown className="h-3 w-3 text-destructive" />
                  )}
                  <span className={cn("font-mono", stop.unrealizedPnlPct >= 0 ? "text-success" : "text-destructive")}>
                    {stop.unrealizedPnlPct.toFixed(2)}%
                  </span>
                </div>
              </div>
            ))
          )}
        </div>
      </CardContent>
    </Card>
  );
};
