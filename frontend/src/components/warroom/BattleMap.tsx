import { Card } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { Target, TrendingUp, TrendingDown, Activity } from 'lucide-react';
import type { MarketOpportunity } from '@/hooks/useMarketScanner';
import type { AccountBalance } from '@/hooks/useBinanceBalances';

interface BattleMapProps {
  opportunities: MarketOpportunity[];
  accounts: AccountBalance[];
}

export function BattleMap({ opportunities, accounts }: BattleMapProps) {
  // Get positions from accounts (simplified - would need proper position tracking)
  const activePositions = accounts.flatMap(acc => 
    Object.entries(acc.balances)
      .filter(([asset, balance]) => balance.total > 0.001 && asset !== 'USDT')
      .map(([asset, balance]) => ({
        symbol: `${asset}USDT`,
        quantity: balance.total,
        side: 'LONG',
        pnl: 0, // Would need actual calculation
        pnlPercent: 0,
      }))
  );

  return (
    <div className="space-y-4">
      {/* Targets Acquired */}
      <Card className="p-4 bg-card/50 backdrop-blur border-primary/20">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold flex items-center gap-2">
            <Target className="h-5 w-5 text-destructive" />
            🎯 TARGETS ACQUIRED ({opportunities.length})
          </h3>
        </div>

        <ScrollArea className="h-[300px]">
          <div className="space-y-2">
            {opportunities.map((opp, index) => (
              <div
                key={opp.symbol}
                className="flex items-center justify-between p-3 rounded-lg bg-background/50 hover:bg-background/80 transition-all border border-border/50"
              >
                <div className="flex items-center gap-3">
                  <div className="text-2xl font-bold text-muted-foreground">
                    #{index + 1}
                  </div>
                  <div>
                    <p className="font-semibold">{opp.symbol}</p>
                    <p className="text-xs text-muted-foreground">
                      Score: {opp.opportunityScore.toFixed(0)} · Vol: ${(opp.volume24h / 1000000).toFixed(1)}M
                    </p>
                  </div>
                </div>

                <div className="text-right">
                  <p className="font-mono">${opp.price.toFixed(4)}</p>
                  <div className="flex items-center gap-2">
                    {opp.priceChange24h >= 0 ? (
                      <TrendingUp className="h-3 w-3 text-success" />
                    ) : (
                      <TrendingDown className="h-3 w-3 text-destructive" />
                    )}
                    <span className={`text-xs ${opp.priceChange24h >= 0 ? 'text-success' : 'text-destructive'}`}>
                      {opp.priceChange24h.toFixed(2)}%
                    </span>
                  </div>
                </div>

                <Badge variant="outline" className="ml-2">
                  <Activity className="h-3 w-3 mr-1" />
                  {(opp.volatility * 100).toFixed(1)}%
                </Badge>
              </div>
            ))}

            {opportunities.length === 0 && (
              <div className="text-center text-muted-foreground py-8">
                🔍 Scanning for targets...
              </div>
            )}
          </div>
        </ScrollArea>
      </Card>

      {/* Active Positions */}
      <Card className="p-4 bg-card/50 backdrop-blur border-primary/20">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold flex items-center gap-2">
            <Activity className="h-5 w-5 text-primary" />
            ⚡ ACTIVE POSITIONS ({activePositions.length})
          </h3>
        </div>

        <ScrollArea className="h-[200px]">
          <div className="space-y-2">
            {activePositions.slice(0, 10).map((pos, index) => (
              <div
                key={`${pos.symbol}-${index}`}
                className="flex items-center justify-between p-3 rounded-lg bg-background/50 hover:bg-background/80 transition-all border border-border/50"
              >
                <div>
                  <p className="font-semibold">{pos.symbol}</p>
                  <p className="text-xs text-muted-foreground">
                    {pos.side} · Qty: {pos.quantity.toFixed(4)}
                  </p>
                </div>

                <div className="text-right">
                  <p className={`font-semibold ${pos.pnl >= 0 ? 'text-success' : 'text-destructive'}`}>
                    {pos.pnl >= 0 ? '+' : ''}${pos.pnl.toFixed(2)}
                  </p>
                  <p className={`text-xs ${pos.pnlPercent >= 0 ? 'text-success' : 'text-destructive'}`}>
                    ({pos.pnlPercent >= 0 ? '+' : ''}{pos.pnlPercent.toFixed(2)}%)
                  </p>
                </div>
              </div>
            ))}

            {activePositions.length === 0 && (
              <div className="text-center text-muted-foreground py-8">
                💤 No active positions
              </div>
            )}
          </div>
        </ScrollArea>
      </Card>
    </div>
  );
}
