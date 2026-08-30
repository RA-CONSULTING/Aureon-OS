import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useMultiSymbolWatchlist, type WatchlistSymbol } from '@/hooks/useMultiSymbolWatchlist';
import { PriceAlerts } from '@/components/PriceAlerts';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

const WATCHLIST_SYMBOLS = [
  // TOP TIER
  'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT', 'ADAUSDT', 'AVAXUSDT',
  'DOTUSDT', 'ATOMUSDT', 'NEARUSDT', 'APTUSDT', 'SUIUSDT',
  // LAYER 2s
  'ARBUSDT', 'OPUSDT', 'MATICUSDT',
  // DEFI
  'UNIUSDT', 'AAVEUSDT', 'LINKUSDT',
  // AI
  'FETUSDT', 'INJUSDT', 'WLDUSDT',
  // MEMECOINS
  'DOGEUSDT', 'SHIBUSDT', 'PEPEUSDT', 'BONKUSDT', 'WIFUSDT',
];

export const Watchlist = () => {
  const { symbolData, isConnected } = useMultiSymbolWatchlist(WATCHLIST_SYMBOLS);

  const renderSymbolCard = (symbol: string) => {
    const data = symbolData.get(symbol);
    
    if (!data) {
      return (
        <Card key={symbol} className="p-4 bg-muted/30">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-semibold text-sm">{symbol}</p>
              <p className="text-xs text-muted-foreground">Loading...</p>
            </div>
          </div>
        </Card>
      );
    }

    const isPositive = data.changePercent > 0;
    const isNeutral = data.changePercent === 0;
    const trendColor = isPositive ? 'text-success' : isNeutral ? 'text-muted-foreground' : 'text-destructive';
    const bgColor = isPositive ? 'bg-success/10' : isNeutral ? 'bg-muted/30' : 'bg-destructive/10';

    return (
      <Card key={symbol} className={`p-4 ${bgColor} transition-colors`}>
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <p className="font-semibold text-sm">{data.symbol}</p>
            {isPositive && <TrendingUp className="h-3 w-3 text-success" />}
            {!isPositive && !isNeutral && <TrendingDown className="h-3 w-3 text-destructive" />}
            {isNeutral && <Minus className="h-3 w-3 text-muted-foreground" />}
          </div>
          <Badge variant="outline" className={`${trendColor} text-xs`}>
            {isPositive ? '+' : ''}{data.changePercent.toFixed(2)}%
          </Badge>
        </div>
        
        <div className="space-y-1">
          <div className="flex justify-between items-baseline">
            <span className="text-xs text-muted-foreground">Price</span>
            <span className="font-mono font-medium">${data.price.toLocaleString()}</span>
          </div>
          
          <div className="flex justify-between items-baseline">
            <span className="text-xs text-muted-foreground">24h Change</span>
            <span className={`font-mono text-xs ${trendColor}`}>
              {isPositive ? '+' : ''}{data.change24h.toFixed(2)}
            </span>
          </div>
          
          <div className="flex justify-between items-baseline">
            <span className="text-xs text-muted-foreground">Volume</span>
            <span className="font-mono text-xs">
              {(data.volume / 1000000).toFixed(2)}M
            </span>
          </div>
          
          <div className="flex justify-between items-baseline pt-1 border-t border-border/50">
            <span className="text-xs text-muted-foreground">High</span>
            <span className="font-mono text-xs">${data.high24h.toLocaleString()}</span>
          </div>
          
          <div className="flex justify-between items-baseline">
            <span className="text-xs text-muted-foreground">Low</span>
            <span className="font-mono text-xs">${data.low24h.toLocaleString()}</span>
          </div>
        </div>
      </Card>
    );
  };

  return (
    <div className="space-y-6">
      <Card className="p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-semibold">Market Watchlist</h3>
            <p className="text-sm text-muted-foreground">Real-time monitoring across multiple pairs</p>
          </div>
          {isConnected ? (
            <Badge style={{ backgroundColor: '#00FF88' }}>Live</Badge>
          ) : (
            <Badge variant="outline">Connecting...</Badge>
          )}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {WATCHLIST_SYMBOLS.map(renderSymbolCard)}
        </div>
      </Card>

      <PriceAlerts symbolData={symbolData} />
    </div>
  );
};
