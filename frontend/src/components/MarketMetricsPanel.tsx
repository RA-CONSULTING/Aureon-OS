import { useBinanceWebSocket } from '@/hooks/useBinanceWebSocket';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Activity, TrendingUp, Gauge, BarChart3 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useMemo } from 'react';

export const MarketMetricsPanel = () => {
  const { marketData, connected } = useBinanceWebSocket(['BTCUSDT']);
  const btc = marketData['BTCUSDT'];

  const metrics = useMemo(() => {
    if (!btc) return null;

    // Calculate volatility from high/low range
    const volatility = btc.high24h && btc.low24h 
      ? ((btc.high24h - btc.low24h) / btc.low24h * 100)
      : 0;

    // Momentum from price position in range
    const momentum = btc.high24h && btc.low24h && btc.price
      ? ((btc.price - btc.low24h) / (btc.high24h - btc.low24h) * 2 - 1)
      : 0;

    // Volume in billions
    const volumeUSD = btc.volume24h * btc.price;

    return {
      volatility: volatility.toFixed(2),
      momentum: momentum.toFixed(2),
      volumeUSD: volumeUSD > 1e9 
        ? `$${(volumeUSD / 1e9).toFixed(1)}B` 
        : `$${(volumeUSD / 1e6).toFixed(0)}M`,
      range: `$${btc.low24h?.toLocaleString(undefined, { maximumFractionDigits: 0 })} - $${btc.high24h?.toLocaleString(undefined, { maximumFractionDigits: 0 })}`
    };
  }, [btc]);

  return (
    <Card className="h-full">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          <Activity className="h-4 w-4 text-primary" />
          Market Metrics
          <span className={cn(
            "ml-auto text-xs",
            connected ? "text-success" : "text-destructive"
          )}>
            {connected ? '● Live' : '○ Offline'}
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Gauge className="h-4 w-4" />
            Volatility
          </div>
          <span className="font-mono text-sm">
            {metrics?.volatility ?? '---'}%
          </span>
        </div>

        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <TrendingUp className="h-4 w-4" />
            Momentum
          </div>
          <span className={cn(
            "font-mono text-sm",
            metrics && parseFloat(metrics.momentum) > 0 ? "text-success" : "text-destructive"
          )}>
            {metrics?.momentum ?? '---'}
          </span>
        </div>

        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <BarChart3 className="h-4 w-4" />
            Volume 24h
          </div>
          <span className="font-mono text-sm">
            {metrics?.volumeUSD ?? '---'}
          </span>
        </div>

        <div className="pt-2 border-t border-border">
          <div className="text-xs text-muted-foreground">24h Range</div>
          <div className="text-xs font-mono mt-1">
            {metrics?.range ?? '---'}
          </div>
        </div>
      </CardContent>
    </Card>
  );
};
