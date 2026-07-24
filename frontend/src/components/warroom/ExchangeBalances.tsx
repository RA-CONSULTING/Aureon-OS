import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { Wallet, ArrowRightLeft } from 'lucide-react';

interface ExchangeBalancesProps {
  totalEquityUsd: number;
  exchanges: Array<{
    exchange: string;
    connected: boolean;
    totalUsdValue: number;
  }>;
}

export function ExchangeBalances({ totalEquityUsd, exchanges }: ExchangeBalancesProps) {
  const formatUsd = (value: number) => {
    if (value >= 1000000) return `$${(value / 1000000).toFixed(2)}M`;
    if (value >= 1000) return `$${(value / 1000).toFixed(1)}K`;
    return `$${value.toFixed(2)}`;
  };

  return (
    <Card className="border-border/50">
      <CardHeader className="pb-2">
        <CardTitle className="text-xs font-medium text-muted-foreground flex items-center gap-1">
          <Wallet className="h-3 w-3" /> EXCHANGE BALANCES
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Total Equity */}
        <div className="bg-muted/30 rounded-md p-2">
          <p className="text-[10px] text-muted-foreground uppercase">Total Equity</p>
          <p className="text-xl font-bold font-mono">{formatUsd(totalEquityUsd)}</p>
        </div>

        {/* Exchange Breakdown */}
        <div className="space-y-2">
          {exchanges.map((exchange) => (
            <div key={exchange.exchange} className="flex items-center justify-between text-xs">
              <div className="flex items-center gap-2">
                <div className={cn(
                  "h-1.5 w-1.5 rounded-full",
                  exchange.connected ? "bg-success" : "bg-destructive"
                )} />
                <span className="capitalize">{exchange.exchange}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="font-mono">{formatUsd(exchange.totalUsdValue)}</span>
                <Badge variant={exchange.connected ? "default" : "secondary"} className="text-[9px] h-4">
                  {exchange.connected ? 'LIVE' : 'OFF'}
                </Badge>
              </div>
            </div>
          ))}
        </div>

        {/* Smart Routing */}
        <div className="flex items-center justify-between pt-2 border-t border-border/30 text-xs">
          <div className="flex items-center gap-1 text-muted-foreground">
            <ArrowRightLeft className="h-3 w-3" />
            <span>Smart Router</span>
          </div>
          <Badge variant="outline" className="text-[9px]">
            ACTIVE
          </Badge>
        </div>
      </CardContent>
    </Card>
  );
}
