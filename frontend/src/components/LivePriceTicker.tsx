import { useBinanceWebSocket } from '@/hooks/useBinanceWebSocket';
import { cn } from '@/lib/utils';
import { TrendingUp, TrendingDown, Wifi, WifiOff } from 'lucide-react';

const SYMBOLS = [
  'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'ADAUSDT', 'AVAXUSDT',
  'DOTUSDT', 'NEARUSDT', 'APTUSDT', 'SUIUSDT',
  'ARBUSDT', 'OPUSDT', 'MATICUSDT',
  'UNIUSDT', 'LINKUSDT',
  'DOGEUSDT', 'SHIBUSDT', 'PEPEUSDT', 'BONKUSDT',
];

export const LivePriceTicker = () => {
  const { marketData, connected } = useBinanceWebSocket(SYMBOLS);

  const formatPrice = (price: number) => {
    if (price >= 1000) return `$${price.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
    if (price >= 1) return `$${price.toFixed(2)}`;
    return `$${price.toFixed(4)}`;
  };

  const formatSymbol = (symbol: string) => symbol.replace('USDT', '');

  return (
    <div className="flex items-center gap-4 px-4 py-2 bg-muted/30 border-b border-border overflow-x-auto">
      {/* Connection Status */}
      <div className={cn(
        "flex items-center gap-1.5 text-xs font-medium shrink-0",
        connected ? "text-success" : "text-destructive"
      )}>
        {connected ? <Wifi className="h-3 w-3" /> : <WifiOff className="h-3 w-3" />}
        {connected ? 'LIVE' : 'OFFLINE'}
      </div>

      <div className="h-4 w-px bg-border shrink-0" />

      {/* Price Tickers */}
      {SYMBOLS.map(symbol => {
        const data = marketData[symbol];
        const isPositive = data ? data.priceChange24h >= 0 : true;

        return (
          <div key={symbol} className="flex items-center gap-2 shrink-0">
            <span className="text-xs font-bold text-foreground">
              {formatSymbol(symbol)}
            </span>
            <span className="text-sm font-mono text-foreground">
              {data ? formatPrice(data.price) : '---'}
            </span>
            {data && (
              <span className={cn(
                "flex items-center gap-0.5 text-xs font-medium",
                isPositive ? "text-success" : "text-destructive"
              )}>
                {isPositive ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
                {isPositive ? '+' : ''}{data.priceChange24h.toFixed(2)}%
              </span>
            )}
          </div>
        );
      })}

      {/* Volume Summary */}
      {marketData['BTCUSDT'] && (
        <>
          <div className="h-4 w-px bg-border shrink-0" />
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground shrink-0">
            <span>BTC Vol:</span>
            <span className="font-mono">
              {(marketData['BTCUSDT'].volume24h).toLocaleString(undefined, { maximumFractionDigits: 0 })}
            </span>
          </div>
        </>
      )}
    </div>
  );
};
