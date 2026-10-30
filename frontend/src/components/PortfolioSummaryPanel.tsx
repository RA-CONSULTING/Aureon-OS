import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useUserBalances } from '@/hooks/useUserBalances';
import { readingText } from '@/lib/reading';
import { Wallet, RefreshCw } from 'lucide-react';
import { formatDistanceToNowStrict } from 'date-fns';

export function PortfolioSummaryPanel() {
  const { totalEquityUsd, isLoading, error, lastUpdated, refresh, getConsolidatedAssets } = useUserBalances(true, 30000);
  const allAssets = getConsolidatedAssets();

  // Split assets by exchange
  const binanceAssets = allAssets.filter(a => a.exchanges.includes('binance'));
  const krakenAssets = allAssets.filter(a => a.exchanges.includes('kraken'));

  const binanceTotal = binanceAssets.reduce((sum, a) => {
    // Get only the binance portion of the asset value (approximate split)
    const binanceRatio = 1 / a.exchanges.length;
    return sum + (a.usdValue * binanceRatio);
  }, 0);

  const krakenTotal = krakenAssets.reduce((sum, a) => {
    const krakenRatio = 1 / a.exchanges.length;
    return sum + (a.usdValue * krakenRatio);
  }, 0);

  const renderExchangeColumn = (
    assets: typeof allAssets,
    exchange: string,
    emoji: string,
    total: number
  ) => (
    <div className="flex-1 min-w-0">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-lg">{emoji}</span>
          <span className="font-semibold capitalize">{exchange}</span>
          <Badge variant="outline" className="text-xs">{assets.length}</Badge>
        </div>
        <span className="text-sm font-mono text-muted-foreground">${total.toFixed(2)}</span>
      </div>
      <ScrollArea className="h-40 rounded-lg border border-border/50 bg-muted/20 p-2">
        {assets.length === 0 ? (
          <div className="text-xs text-muted-foreground text-center py-6">
            No {exchange} assets
          </div>
        ) : (
          <div className="space-y-1">
            {assets.slice(0, 8).map((a) => (
              <div key={`${exchange}-${a.asset}`} className="flex items-center justify-between text-xs">
                <span className="font-medium">{a.asset}</span>
                <span className="font-mono text-muted-foreground">
                  ${a.usdValue.toLocaleString(undefined, { maximumFractionDigits: 2 })}
                </span>
              </div>
            ))}
          </div>
        )}
      </ScrollArea>
    </div>
  );

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          <Wallet className="h-4 w-4 text-primary" />
          Portfolio
          <Badge variant="outline" className="text-xs ml-1">
            {readingText(totalEquityUsd, (equity) => `$${equity.toLocaleString(undefined, { maximumFractionDigits: 2 })}`)}
          </Badge>
          <Button
            variant="ghost"
            size="icon"
            className="ml-auto"
            onClick={() => refresh()}
            disabled={isLoading}
            aria-label="Refresh portfolio"
          >
            <RefreshCw className={isLoading ? 'h-4 w-4 animate-spin' : 'h-4 w-4'} />
          </Button>
        </CardTitle>
        {lastUpdated && (
          <div className="text-xs text-muted-foreground">
            Updated {formatDistanceToNowStrict(lastUpdated)} ago
          </div>
        )}
      </CardHeader>
      <CardContent>
        {error ? (
          <div className="text-sm text-destructive">{error}</div>
        ) : isLoading && allAssets.length === 0 ? (
          <div className="text-sm text-muted-foreground text-center py-4">Loading balances…</div>
        ) : (
          <div className="flex gap-4">
            {renderExchangeColumn(binanceAssets, "binance", "🟡", binanceTotal)}
            {renderExchangeColumn(krakenAssets, "kraken", "🐙", krakenTotal)}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
