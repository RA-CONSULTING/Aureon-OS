import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { crossExchangeArbitrageScanner, ArbitrageOpportunity } from '@/core/crossExchangeArbitrageScanner';
import { ArrowRightLeft, TrendingUp } from 'lucide-react';

export const ArbitrageScannerPanel = () => {
  const [opportunities, setOpportunities] = useState<ArbitrageOpportunity[]>([]);
  const [stats, setStats] = useState({ totalScans: 0, totalOpportunities: 0, executedCount: 0, totalProfit: 0 });

  useEffect(() => {
    const interval = setInterval(() => {
      const lastScan = crossExchangeArbitrageScanner.getLastScan();
      if (lastScan) {
        setOpportunities(lastScan.opportunities.filter(o => o.isViable));
      }
      setStats(crossExchangeArbitrageScanner.getStats());
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  return (
    <Card className="border-border/50 bg-card/50 backdrop-blur">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-sm font-medium">
          <ArrowRightLeft className="h-4 w-4 text-primary" />
          Cross-Exchange Arbitrage
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="grid grid-cols-3 gap-2 text-xs">
          <div className="text-center p-2 rounded bg-muted/30">
            <div className="text-muted-foreground">Scans</div>
            <div className="font-mono font-bold">{stats.totalScans}</div>
          </div>
          <div className="text-center p-2 rounded bg-muted/30">
            <div className="text-muted-foreground">Found</div>
            <div className="font-mono font-bold text-primary">{stats.totalOpportunities}</div>
          </div>
          <div className="text-center p-2 rounded bg-muted/30">
            <div className="text-muted-foreground">Profit</div>
            <div className="font-mono font-bold text-success">${stats.totalProfit.toFixed(2)}</div>
          </div>
        </div>

        <div className="space-y-2 max-h-40 overflow-y-auto">
          {opportunities.length === 0 ? (
            <div className="text-xs text-muted-foreground text-center py-4">
              No arbitrage opportunities detected
            </div>
          ) : (
            opportunities.slice(0, 5).map((opp, i) => (
              <div key={i} className="flex items-center justify-between p-2 rounded bg-muted/20 text-xs">
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className="text-[10px]">{opp.symbol}</Badge>
                  <span className="text-muted-foreground">
                    {opp.buyExchange} → {opp.sellExchange}
                  </span>
                </div>
                <div className="flex items-center gap-1 text-success">
                  <TrendingUp className="h-3 w-3" />
                  <span className="font-mono">{(opp.spreadPct * 100).toFixed(2)}%</span>
                </div>
              </div>
            ))
          )}
        </div>
      </CardContent>
    </Card>
  );
};
