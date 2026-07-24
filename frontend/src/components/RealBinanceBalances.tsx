import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useBinanceBalances } from '@/hooks/useBinanceBalances';
import { RefreshCw, Wallet, DollarSign, Bitcoin } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

export function RealBinanceBalances() {
  const { accounts, totals, loading, lastUpdated, refresh } = useBinanceBalances();

  const hasData = accounts.length > 0 || totals.totalUSDValue > 0;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Wallet className="h-5 w-5 text-primary" />
          <span className="font-medium">Binance</span>
        </div>
        <Button onClick={refresh} disabled={loading} variant="ghost" size="sm">
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
        </Button>
      </div>

      {loading ? (
        <div className="text-center py-8 text-muted-foreground">
          <RefreshCw className="h-6 w-6 animate-spin mx-auto mb-2" />
          <p className="text-sm">Fetching balances...</p>
        </div>
      ) : !hasData ? (
        <div className="text-center py-8">
          <div className="text-4xl mb-3">🔗</div>
          <p className="text-muted-foreground text-sm mb-2">No Binance credentials configured</p>
          <p className="text-xs text-muted-foreground">Add your Binance API keys in Settings to see your balances</p>
        </div>
      ) : (
        <>
          {/* Total Portfolio Value */}
          <div className="p-4 rounded-lg bg-gradient-to-br from-primary/10 to-primary/5 border border-primary/20">
            <div className="flex items-center gap-2 mb-1">
              <DollarSign className="h-4 w-4 text-primary" />
              <span className="text-xs text-muted-foreground">Total Value</span>
            </div>
            <div className="text-2xl font-bold text-primary">
              ${totals.totalUSDValue.toFixed(2)}
            </div>
            {lastUpdated && (
              <p className="text-xs text-muted-foreground mt-1">
                Updated {formatDistanceToNow(lastUpdated, { addSuffix: true })}
              </p>
            )}
          </div>

          {/* Asset Breakdown */}
          <div className="grid grid-cols-3 gap-2">
            <div className="p-3 rounded-lg bg-muted/30 border border-border/50">
              <div className="flex items-center gap-1 mb-1">
                <DollarSign className="h-3 w-3 text-success" />
                <span className="text-xs text-muted-foreground">USDT</span>
              </div>
              <div className="text-lg font-bold text-success">${totals.USDT.toFixed(2)}</div>
            </div>
            
            <div className="p-3 rounded-lg bg-muted/30 border border-border/50">
              <div className="flex items-center gap-1 mb-1">
                <Bitcoin className="h-3 w-3 text-warning" />
                <span className="text-xs text-muted-foreground">BTC</span>
              </div>
              <div className="text-lg font-bold text-warning">{totals.BTC.toFixed(6)}</div>
            </div>
            
            <div className="p-3 rounded-lg bg-muted/30 border border-border/50">
              <div className="flex items-center gap-1 mb-1">
                <span className="text-xs text-primary">Ξ</span>
                <span className="text-xs text-muted-foreground">ETH</span>
              </div>
              <div className="text-lg font-bold text-primary">{totals.ETH.toFixed(6)}</div>
            </div>
          </div>

          {/* Bot Status */}
          {accounts.length > 0 && (
            <div className="space-y-2">
              <div className="text-xs font-medium text-muted-foreground">Active Bots ({accounts.length})</div>
              <div className="max-h-[200px] overflow-y-auto space-y-1">
                {accounts.map((account) => (
                  <div key={account.name} className="p-2 rounded bg-muted/20 border border-border/30">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium">{account.name}</span>
                      {account.error ? (
                        <Badge variant="destructive" className="text-xs">Error</Badge>
                      ) : account.canTrade ? (
                        <Badge className="bg-success/20 text-success text-xs">Active</Badge>
                      ) : (
                        <Badge variant="outline" className="text-xs">Restricted</Badge>
                      )}
                    </div>
                    
                    {account.error ? (
                      <div className="text-xs text-destructive">{account.error}</div>
                    ) : (
                      <div className="grid grid-cols-3 gap-1 text-xs">
                        {Object.entries(account.balances)
                          .filter(([_, bal]) => bal.total > 0.001)
                          .slice(0, 3)
                          .map(([asset, balance]) => (
                            <div key={asset} className="flex justify-between">
                              <span className="text-muted-foreground">{asset}:</span>
                              <span>{balance.total.toFixed(asset === 'USDT' ? 2 : 4)}</span>
                            </div>
                          ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
