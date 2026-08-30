import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { portfolioRebalancer } from '@/core/portfolioRebalancer';
import { PieChart, ArrowUpDown, RefreshCw } from 'lucide-react';
import { cn } from '@/lib/utils';

interface RebalanceRecommendation {
  asset: string;
  action: 'BUY' | 'SELL';
  currentWeight: number;
  targetWeight: number;
  deviation: number;
  usdAmount: number;
}

export const PortfolioRebalancerPanel = () => {
  const [recommendations, setRecommendations] = useState<RebalanceRecommendation[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const fetchRecommendations = async () => {
    setIsLoading(true);
    try {
      // Simulate fetching current holdings
      const mockBalances = [
        { asset: 'BTC', exchange: 'binance', quantity: 0.1, usdValue: 4500 },
        { asset: 'ETH', exchange: 'binance', quantity: 1.5, usdValue: 2500 },
        { asset: 'SOL', exchange: 'binance', quantity: 20, usdValue: 1500 },
        { asset: 'USDT', exchange: 'binance', quantity: 1500, usdValue: 1500 }
      ];
      
      const result = portfolioRebalancer.analyzePortfolio(mockBalances);
      
      const recs: RebalanceRecommendation[] = result.trades.map(trade => ({
        asset: trade.asset,
        action: trade.side,
        currentWeight: (result.currentAllocations.get(trade.asset) || 0) / 100,
        targetWeight: (result.targetAllocations.get(trade.asset) || 0) / 100,
        deviation: (result.deviations.get(trade.asset) || 0) / 100,
        usdAmount: trade.usdValue
      }));
      
      setRecommendations(recs);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchRecommendations();
  }, []);

  return (
    <Card className="border-border/50 bg-card/50 backdrop-blur">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-sm font-medium">
            <PieChart className="h-4 w-4 text-primary" />
            Portfolio Rebalancer
          </CardTitle>
          <Button 
            variant="ghost" 
            size="icon" 
            className="h-6 w-6"
            onClick={fetchRecommendations}
            disabled={isLoading}
          >
            <RefreshCw className={cn("h-3 w-3", isLoading && "animate-spin")} />
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="space-y-2 max-h-48 overflow-y-auto">
          {recommendations.length === 0 ? (
            <div className="text-xs text-muted-foreground text-center py-4">
              Portfolio is balanced - no rebalancing needed
            </div>
          ) : (
            recommendations.map((rec, i) => (
              <div key={i} className="p-2 rounded bg-muted/20 text-xs space-y-1">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Badge 
                      variant={rec.action === 'BUY' ? 'default' : 'destructive'} 
                      className="text-[10px]"
                    >
                      {rec.action}
                    </Badge>
                    <span className="font-medium">{rec.asset}</span>
                  </div>
                  <span className="font-mono text-muted-foreground">
                    ${rec.usdAmount.toFixed(2)}
                  </span>
                </div>
                <div className="flex items-center justify-between text-muted-foreground">
                  <div className="flex items-center gap-1">
                    <span>{(rec.currentWeight * 100).toFixed(1)}%</span>
                    <ArrowUpDown className="h-3 w-3" />
                    <span>{(rec.targetWeight * 100).toFixed(1)}%</span>
                  </div>
                  <span className={cn(
                    "font-mono",
                    rec.deviation > 0 ? "text-destructive" : "text-success"
                  )}>
                    {rec.deviation > 0 ? '+' : ''}{(rec.deviation * 100).toFixed(1)}%
                  </span>
                </div>
              </div>
            ))
          )}
        </div>

        <div className="text-[10px] text-muted-foreground text-center">
          Rebalance threshold: 5% deviation
        </div>
      </CardContent>
    </Card>
  );
};
