/**
 * Kraken Status Panel
 * Prime Sentinel: GARY LECKEY 02111991
 * 
 * Displays real-time Kraken WebSocket connection status and ticker data
 */

import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Wifi, WifiOff, RefreshCw, TrendingUp, TrendingDown, Activity } from 'lucide-react';
import { useKrakenRealtime } from '@/hooks/useKrakenRealtime';
import { supabase } from '@/integrations/supabase/client';

interface KrakenAPIData {
  success: boolean;
  tickers?: Record<string, any>;
  primaryTicker?: any;
  latencyMs?: number;
  dataSource?: string;
  error?: string;
}

export const KrakenStatusPanel: React.FC = () => {
  const { 
    isConnected, 
    tickers, 
    lastUpdate, 
    error, 
    connect, 
    disconnect,
    btcPrice,
    ethPrice,
    tickerCount,
    connectionAttempts,
  } = useKrakenRealtime({ autoConnect: true });

  const [apiData, setApiData] = useState<KrakenAPIData | null>(null);
  const [isLoadingAPI, setIsLoadingAPI] = useState(false);

  const fetchFromAPI = async () => {
    setIsLoadingAPI(true);
    try {
      const { data, error } = await supabase.functions.invoke('fetch-kraken-market-data', {
        body: { symbols: ['BTCUSD', 'ETHUSD', 'SOLUSD'] }
      });
      
      if (error) throw error;
      setApiData(data);
    } catch (err) {
      console.error('Kraken API fetch error:', err);
      setApiData({ success: false, error: err instanceof Error ? err.message : 'API error' });
    } finally {
      setIsLoadingAPI(false);
    }
  };

  useEffect(() => {
    fetchFromAPI();
    const interval = setInterval(fetchFromAPI, 30000);
    return () => clearInterval(interval);
  }, []);

  const formatPrice = (price: number | null | undefined) => {
    if (!price) return '-';
    return `$${price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const formatTime = (timestamp: number | null) => {
    if (!timestamp) return '-';
    return new Date(timestamp).toLocaleTimeString();
  };

  // Show setup message if not connected and no data
  const showSetupMessage = !isConnected && !apiData?.success;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xl">🦑</span>
          <span className="font-medium">Kraken</span>
        </div>
        <div className="flex items-center gap-2">
          {isConnected ? (
            <Badge className="bg-success/20 text-success text-xs">
              <Wifi className="h-3 w-3 mr-1" />
              LIVE
            </Badge>
          ) : (
            <Badge variant="outline" className="text-xs">
              <WifiOff className="h-3 w-3 mr-1" />
              Offline
            </Badge>
          )}
          <Button variant="ghost" size="sm" onClick={isConnected ? disconnect : connect}>
            <RefreshCw className={`h-4 w-4 ${!isConnected && connectionAttempts > 0 ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </div>

      {showSetupMessage ? (
        <div className="text-center py-8">
          <div className="text-4xl mb-3">🔗</div>
          <p className="text-muted-foreground text-sm mb-2">No Kraken credentials configured</p>
          <p className="text-xs text-muted-foreground">Add your Kraken API keys in Settings to see your balances</p>
        </div>
      ) : (
        <>
          {/* Connection Stats */}
          <div className="grid grid-cols-2 gap-2">
            <div className="p-3 rounded-lg bg-muted/30 border border-border/50">
              <p className="text-xs text-muted-foreground mb-1">Status</p>
              <div className="flex items-center gap-2">
                {isConnected ? (
                  <Activity className="h-4 w-4 text-success animate-pulse" />
                ) : (
                  <WifiOff className="h-4 w-4 text-muted-foreground" />
                )}
                <span className={isConnected ? 'text-success text-sm' : 'text-muted-foreground text-sm'}>
                  {isConnected ? 'Connected' : 'Disconnected'}
                </span>
              </div>
            </div>
            
            <div className="p-3 rounded-lg bg-muted/30 border border-border/50">
              <p className="text-xs text-muted-foreground mb-1">Tickers</p>
              <p className="text-lg font-bold">{tickerCount}</p>
            </div>
          </div>

          {/* Live Prices */}
          {(btcPrice || ethPrice) && (
            <div className="grid grid-cols-2 gap-2">
              <div className="p-2 rounded bg-muted/20 border border-border/30">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">BTC</span>
                  {btcPrice && <TrendingUp className="h-3 w-3 text-success" />}
                </div>
                <p className="text-lg font-bold text-primary">{formatPrice(btcPrice)}</p>
              </div>
              <div className="p-2 rounded bg-muted/20 border border-border/30">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">ETH</span>
                  {ethPrice && <TrendingUp className="h-3 w-3 text-success" />}
                </div>
                <p className="text-lg font-bold text-primary">{formatPrice(ethPrice)}</p>
              </div>
            </div>
          )}

          {/* API Status */}
          {apiData?.success && (
            <div className="p-2 rounded bg-success/10 border border-success/30">
              <div className="flex items-center justify-between">
                <Badge className="bg-success/20 text-success text-xs">{apiData.dataSource}</Badge>
                <span className="text-xs text-muted-foreground">{apiData.latencyMs}ms</span>
              </div>
            </div>
          )}

          {/* Error Display */}
          {error && (
            <div className="p-2 rounded bg-destructive/10 border border-destructive/30">
              <p className="text-xs text-destructive">{error}</p>
            </div>
          )}
        </>
      )}
    </div>
  );
};
