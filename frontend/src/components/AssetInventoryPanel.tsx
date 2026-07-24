import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { RefreshCw, Search, Database, CheckCircle, XCircle } from 'lucide-react';
import { useAvailableAssets } from '@/hooks/useAvailableAssets';

interface AssetInventoryPanelProps {
  className?: string;
  compact?: boolean;
}

export function AssetInventoryPanel({ className, compact = false }: AssetInventoryPanelProps) {
  const {
    assets,
    assetsByExchange,
    isLoading,
    lastSynced,
    totalAssets,
    syncAssets,
    searchAssets,
  } = useAvailableAssets();

  const [searchQuery, setSearchQuery] = useState('');
  const [isSyncing, setIsSyncing] = useState(false);

  const handleSync = async () => {
    setIsSyncing(true);
    try {
      await syncAssets(['binance', 'kraken']);
    } catch (error) {
      console.error('Sync failed:', error);
    } finally {
      setIsSyncing(false);
    }
  };

  const filteredAssets = searchQuery ? searchAssets(searchQuery) : assets;
  const displayAssets = filteredAssets.slice(0, compact ? 10 : 50);

  const exchangeCounts = Object.entries(assetsByExchange).map(([exchange, assets]) => ({
    exchange,
    count: assets.length,
    active: assets.filter(a => a.isActive).length,
  }));

  if (compact) {
    return (
      <Card className={className}>
        <CardHeader className="py-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm flex items-center gap-2">
              <Database className="h-4 w-4" />
              Asset Registry
            </CardTitle>
            <Badge variant="outline">{totalAssets} assets</Badge>
          </div>
        </CardHeader>
        <CardContent className="py-2">
          <div className="flex gap-2 text-xs text-muted-foreground">
            {exchangeCounts.map(({ exchange, count }) => (
              <span key={exchange} className="capitalize">
                {exchange}: {count}
              </span>
            ))}
          </div>
          {lastSynced && (
            <div className="text-xs text-muted-foreground mt-1">
              Synced: {lastSynced.toLocaleTimeString()}
            </div>
          )}
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Database className="h-5 w-5" />
            Crypto Asset Registry
          </CardTitle>
          <Button
            variant="outline"
            size="sm"
            onClick={handleSync}
            disabled={isSyncing || isLoading}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${isSyncing ? 'animate-spin' : ''}`} />
            {isSyncing ? 'Syncing...' : 'Sync Now'}
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {/* Exchange Summary */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
          {exchangeCounts.map(({ exchange, count, active }) => (
            <div key={exchange} className="bg-muted/50 rounded-lg p-3">
              <div className="text-xs text-muted-foreground capitalize">{exchange}</div>
              <div className="text-lg font-semibold">{count}</div>
              <div className="text-xs text-muted-foreground">
                {active} active
              </div>
            </div>
          ))}
          <div className="bg-primary/10 rounded-lg p-3">
            <div className="text-xs text-muted-foreground">Total</div>
            <div className="text-lg font-semibold text-primary">{totalAssets}</div>
            <div className="text-xs text-muted-foreground">
              {lastSynced ? `${Math.floor((Date.now() - lastSynced.getTime()) / 60000)}m ago` : 'Never synced'}
            </div>
          </div>
        </div>

        {/* Search */}
        <div className="relative mb-4">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search assets (e.g., BTC, ETH)..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9"
          />
        </div>

        {/* Asset List */}
        <ScrollArea className="h-[300px]">
          <div className="space-y-1">
            {displayAssets.map((asset) => (
              <div
                key={`${asset.exchange}-${asset.symbol}`}
                className="flex items-center justify-between p-2 rounded hover:bg-muted/50 text-sm"
              >
                <div className="flex items-center gap-2">
                  {asset.isActive ? (
                    <CheckCircle className="h-3 w-3 text-success" />
                  ) : (
                    <XCircle className="h-3 w-3 text-destructive" />
                  )}
                  <span className="font-mono font-medium">{asset.symbol}</span>
                  <Badge variant="outline" className="text-xs capitalize">
                    {asset.exchange}
                  </Badge>
                </div>
                <div className="flex items-center gap-3 text-xs text-muted-foreground">
                  {asset.minNotional && (
                    <span>Min: ${asset.minNotional.toFixed(2)}</span>
                  )}
                  {asset.stepSize && (
                    <span>Step: {asset.stepSize}</span>
                  )}
                </div>
              </div>
            ))}
          </div>
          {filteredAssets.length > displayAssets.length && (
            <div className="text-center text-sm text-muted-foreground py-2">
              + {filteredAssets.length - displayAssets.length} more assets
            </div>
          )}
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
