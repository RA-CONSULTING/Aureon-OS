import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useAutonomousTrading } from '@/hooks/useAutonomousTrading';
import { Activity, Play, Square, TrendingUp, Zap } from 'lucide-react';

export const AutonomousTradingPanel = () => {
  const {
    isActive,
    tradesExecuted,
    totalProfit,
    totalFees,
    netProfit,
    opportunities,
    totalPairs,
    isScanning,
    start,
    stop,
  } = useAutonomousTrading();

  return (
    <Card className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold flex items-center gap-2">
            <Zap className="h-5 w-5 text-warning" />
            AUREON Quantum Trading System
            <Badge className="bg-gradient-to-r from-primary to-primary text-white ml-2">🌈 LIVE</Badge>
          </h3>
          <p className="text-sm text-muted-foreground">
            Master Equation (Λ) • 9 Auris Nodes • Lighthouse (Γ{'>'}0.945) • 528Hz Prism | {totalPairs} pairs
          </p>
        </div>
        {isActive ? (
          <Button onClick={stop} variant="destructive" size="lg">
            <Square className="h-4 w-4 mr-2" />
            Stop Trading
          </Button>
        ) : (
          <Button onClick={start} size="lg">
            <Play className="h-4 w-4 mr-2" />
            Start Trading
          </Button>
        )}
      </div>

      {/* Status */}
      <div className="grid grid-cols-4 gap-4">
        <div className="p-4 rounded-lg bg-muted/50">
          <div className="text-2xl font-bold">{tradesExecuted}</div>
          <div className="text-xs text-muted-foreground">Trades Executed</div>
        </div>
        <div className="p-4 rounded-lg bg-muted/50">
          <div className="text-2xl font-bold text-success">
            ${totalProfit.toFixed(2)}
          </div>
          <div className="text-xs text-muted-foreground">Total Profit</div>
        </div>
        <div className="p-4 rounded-lg bg-muted/50">
          <div className="text-2xl font-bold text-destructive">
            ${totalFees.toFixed(2)}
          </div>
          <div className="text-xs text-muted-foreground">Total Fees</div>
        </div>
        <div className="p-4 rounded-lg bg-muted/50">
          <div className={`text-2xl font-bold ${netProfit >= 0 ? 'text-success' : 'text-destructive'}`}>
            ${netProfit.toFixed(2)}
          </div>
          <div className="text-xs text-muted-foreground">Net Profit</div>
        </div>
      </div>

      {/* Status Badge */}
      <div className="flex items-center gap-2">
        {isActive ? (
          <Badge className="bg-success">
            <Activity className="h-3 w-3 mr-1" />
            ACTIVE
          </Badge>
        ) : (
          <Badge variant="outline">PAUSED</Badge>
        )}
        {isScanning && <Badge variant="secondary">Scanning Market...</Badge>}
      </div>

      {/* Top Opportunities */}
      <div>
        <h4 className="text-sm font-medium mb-3 flex items-center gap-2">
          <TrendingUp className="h-4 w-4" />
          Top 20 Opportunities (of {totalPairs} pairs)
        </h4>
        <div className="space-y-2 max-h-[300px] overflow-y-auto">
          {opportunities.slice(0, 20).map((opp) => (
            <div
              key={opp.symbol}
              className="flex items-center justify-between p-3 rounded-lg bg-muted/30 hover:bg-muted/50 transition-colors"
            >
              <div className="flex-1">
                <div className="font-medium text-sm">{opp.symbol}</div>
                <div className="text-xs text-muted-foreground">
                  ${opp.price.toFixed(4)} • Vol: ${(opp.volume24h / 1e6).toFixed(1)}M
                </div>
              </div>
              <div className="text-right">
                <div
                  className={`text-sm font-medium ${
                    opp.priceChange24h > 0 ? 'text-success' : 'text-destructive'
                  }`}
                >
                  {opp.priceChange24h > 0 ? '+' : ''}
                  {opp.priceChange24h.toFixed(2)}%
                </div>
                <div className="text-xs text-muted-foreground">
                  Score: {opp.opportunityScore.toFixed(2)}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </Card>
  );
};
