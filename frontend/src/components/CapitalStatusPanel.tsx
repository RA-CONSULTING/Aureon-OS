import React, { useEffect, useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { RefreshCw, DollarSign, TrendingUp, TrendingDown } from 'lucide-react';
import { supabase } from '@/integrations/supabase/client';

interface CapitalBalance {
  asset: string;
  free: number;
  locked: number;
  usdValue: number;
}

interface CapitalData {
  balances: CapitalBalance[];
  totalUsd: number;
  connected: boolean;
  accounts?: Array<{
    accountId: string;
    accountName: string;
    balance: number;
    currency: string;
  }>;
  message?: string;
  error?: string;
}

export const CapitalStatusPanel: React.FC = () => {
  const [data, setData] = useState<CapitalData | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    try {
      const { data: result, error } = await supabase.functions.invoke('get-capital-balances');
      if (error) throw error;
      setData(result);
    } catch (err) {
      console.error('Capital.com fetch error:', err);
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
          <span className="text-xl">💼</span>
          <span className="font-medium">Capital.com</span>
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
          <p className="text-muted-foreground text-sm mb-2">No Capital.com credentials configured</p>
          <p className="text-xs text-muted-foreground">Add your Capital.com API keys in Settings to trade CFDs</p>
        </div>
      ) : (
        <>
          {/* Total Balance */}
          <div className="p-4 rounded-lg bg-gradient-to-br from-primary/10 to-primary/5 border border-primary/20">
            <div className="flex items-center gap-2 mb-1">
              <DollarSign className="h-4 w-4 text-primary" />
              <span className="text-xs text-muted-foreground">Total Balance</span>
            </div>
            <div className="text-2xl font-bold text-primary">
              ${data.totalUsd.toFixed(2)}
            </div>
          </div>

          {/* Accounts */}
          {data.accounts && data.accounts.length > 0 && (
            <div className="space-y-2">
              <p className="text-xs text-muted-foreground">Accounts ({data.accounts.length})</p>
              <div className="space-y-1">
                {data.accounts.map((acc) => (
                  <div key={acc.accountId} className="flex justify-between items-center p-2 rounded bg-muted/20 border border-border/30">
                    <span className="text-sm font-medium">{acc.accountName}</span>
                    <div className="text-right">
                      <p className="text-sm font-bold">{acc.currency} {acc.balance.toFixed(2)}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Balances */}
          {data.balances.length > 0 && (
            <div className="space-y-2">
              <p className="text-xs text-muted-foreground">Assets</p>
              <div className="max-h-[150px] overflow-y-auto space-y-1">
                {data.balances.map((bal) => (
                  <div key={bal.asset} className="flex justify-between items-center p-2 rounded bg-muted/20 border border-border/30">
                    <span className="text-sm font-medium">{bal.asset}</span>
                    <p className="text-sm font-bold">${bal.usdValue.toFixed(2)}</p>
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
