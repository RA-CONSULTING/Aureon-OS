import React, { useEffect, useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { RefreshCw, TrendingUp, DollarSign } from 'lucide-react';
import { supabase } from '@/integrations/supabase/client';

interface AlpacaBalance {
  asset: string;
  free: number;
  locked: number;
  total: number;
  usdValue: number;
}

interface AlpacaData {
  balances: AlpacaBalance[];
  totalUsd: number;
  connected: boolean;
  account?: {
    status: string;
    buyingPower: number;
    equity: number;
    portfolioValue: number;
  };
  message?: string;
  error?: string;
}

export const AlpacaStatusPanel: React.FC = () => {
  const [data, setData] = useState<AlpacaData | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    try {
      const { data: result, error } = await supabase.functions.invoke('get-alpaca-balances');
      if (error) throw error;
      setData(result);
    } catch (err) {
      console.error('Alpaca fetch error:', err);
      setData({ connected: false, balances: [], totalUsd: 0, error: String(err) });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 60000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xl">🦙</span>
          <span className="font-medium">Alpaca</span>
        </div>
        <div className="flex items-center gap-2">
          {data?.connected ? (
            <Badge className="bg-success/20 text-success text-xs">Connected</Badge>
          ) : (
            <Badge variant="outline" className="text-xs">Offline</Badge>
          )}
          <Button variant="ghost" size="sm" onClick={fetchData} disabled={loading}>
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </div>

      {loading && !data ? (
        <div className="text-center py-8 text-muted-foreground">
          <RefreshCw className="h-6 w-6 animate-spin mx-auto mb-2" />
          <p className="text-sm">Fetching balances...</p>
        </div>
      ) : !data?.connected ? (
        <div className="text-center py-8">
          <div className="text-4xl mb-3">🔗</div>
          <p className="text-muted-foreground text-sm mb-2">No Alpaca credentials configured</p>
          <p className="text-xs text-muted-foreground">Add your Alpaca API keys in Settings to trade US stocks</p>
        </div>
      ) : (
        <>
          {/* Account Value */}
          <div className="p-4 rounded-lg bg-gradient-to-br from-primary/10 to-primary/5 border border-primary/20">
            <div className="flex items-center gap-2 mb-1">
              <DollarSign className="h-4 w-4 text-primary" />
              <span className="text-xs text-muted-foreground">Portfolio Value</span>
            </div>
            <div className="text-2xl font-bold text-primary">
              ${data.account?.portfolioValue?.toFixed(2) || data.totalUsd.toFixed(2)}
            </div>
          </div>

          {/* Account Stats */}
          {data.account && (
            <div className="grid grid-cols-2 gap-2">
              <div className="p-3 rounded-lg bg-muted/30 border border-border/50">
                <p className="text-xs text-muted-foreground mb-1">Buying Power</p>
                <p className="text-lg font-bold text-success">${data.account.buyingPower.toFixed(2)}</p>
              </div>
              <div className="p-3 rounded-lg bg-muted/30 border border-border/50">
                <p className="text-xs text-muted-foreground mb-1">Equity</p>
                <p className="text-lg font-bold">${data.account.equity.toFixed(2)}</p>
              </div>
            </div>
          )}

          {/* Positions */}
          {data.balances.length > 0 && (
            <div className="space-y-2">
              <p className="text-xs text-muted-foreground">Positions ({data.balances.length})</p>
              <div className="max-h-[150px] overflow-y-auto space-y-1">
                {data.balances.map((bal) => (
                  <div key={bal.asset} className="flex justify-between items-center p-2 rounded bg-muted/20 border border-border/30">
                    <span className="text-sm font-medium">{bal.asset}</span>
                    <div className="text-right">
                      <p className="text-sm font-bold">${bal.usdValue.toFixed(2)}</p>
                      <p className="text-xs text-muted-foreground">{bal.total.toFixed(2)} shares</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};
