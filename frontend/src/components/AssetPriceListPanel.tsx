import { useState, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { 
  RefreshCw, 
  Search, 
  TrendingUp, 
  TrendingDown, 
  ArrowUpDown,
  BarChart3,
  Activity,
  ChevronDown,
  ChevronUp,
  Database
} from 'lucide-react';
import { useAssetPriceList, AssetPrice } from '@/hooks/useAssetPriceList';
import { cn } from '@/lib/utils';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';

type SortField = 'symbol' | 'price' | 'change' | 'volume' | 'volatility';
type SortDirection = 'asc' | 'desc';

export function AssetPriceListPanel() {
  const { assets, stats, isLoading, lastRefresh, refresh } = useAssetPriceList();
  const [isOpen, setIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [sortField, setSortField] = useState<SortField>('volume');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');
  const [filterSource, setFilterSource] = useState<'all' | 'LIVE' | 'CACHED' | 'STALE'>('all');

  // Filter and sort assets
  const displayedAssets = useMemo(() => {
    let filtered = assets;

    // Apply search filter
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      filtered = filtered.filter(a =>
        a.symbol.toLowerCase().includes(q) ||
        a.base.toLowerCase().includes(q)
      );
    }

    // Apply source filter
    if (filterSource !== 'all') {
      filtered = filtered.filter(a => a.dataSource === filterSource);
    }

    // Apply sorting
    filtered.sort((a, b) => {
      let cmp = 0;
      switch (sortField) {
        case 'symbol': cmp = a.symbol.localeCompare(b.symbol); break;
        case 'price': cmp = a.price - b.price; break;
        case 'change': cmp = a.change - b.change; break;
        case 'volume': cmp = a.volume - b.volume; break;
        case 'volatility': cmp = a.volatility - b.volatility; break;
      }
      return sortDirection === 'desc' ? -cmp : cmp;
    });

    return filtered;
  }, [assets, searchQuery, sortField, sortDirection, filterSource]);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(d => d === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  const getDataSourceBadge = (source: AssetPrice['dataSource']) => {
    switch (source) {
      case 'LIVE':
        return <Badge variant="default" className="text-[9px] bg-success">LIVE</Badge>;
      case 'CACHED':
        return <Badge variant="secondary" className="text-[9px] bg-warning">CACHED</Badge>;
      case 'STALE':
        return <Badge variant="destructive" className="text-[9px]">STALE</Badge>;
      case 'NO_DATA':
        return <Badge variant="outline" className="text-[9px]">NO DATA</Badge>;
    }
  };

  const formatPrice = (price: number): string => {
    if (price >= 1000) return price.toLocaleString(undefined, { maximumFractionDigits: 2 });
    if (price >= 1) return price.toFixed(4);
    if (price >= 0.0001) return price.toFixed(6);
    return price.toExponential(2);
  };

  const formatVolume = (vol: number): string => {
    if (vol >= 1e12) return `${(vol / 1e12).toFixed(1)}T`;
    if (vol >= 1e9) return `${(vol / 1e9).toFixed(1)}B`;
    if (vol >= 1e6) return `${(vol / 1e6).toFixed(1)}M`;
    if (vol >= 1e3) return `${(vol / 1e3).toFixed(1)}K`;
    return vol.toFixed(0);
  };

  return (
    <Card className="border-border/50">
      <Collapsible open={isOpen} onOpenChange={setIsOpen}>
        <CardHeader className="pb-2">
          <CollapsibleTrigger asChild>
            <div className="flex items-center justify-between cursor-pointer hover:bg-muted/30 -mx-4 -my-2 px-4 py-2 rounded-lg transition-colors">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <Database className="h-4 w-4" />
                FULL ASSET PRICE LIST
                <Badge variant="outline" className="text-[10px]">
                  {stats.totalAssets} pairs
                </Badge>
              </CardTitle>
              <div className="flex items-center gap-3">
                {/* Quick Stats */}
                <div className="hidden md:flex items-center gap-2 text-[10px]">
                  <span className="text-success">● {stats.liveAssets} live</span>
                  <span className="text-warning">● {stats.cachedAssets} cached</span>
                  <span className="text-destructive">● {stats.staleAssets} stale</span>
                </div>
                <Badge 
                  variant={stats.dataFreshness > 80 ? 'default' : stats.dataFreshness > 50 ? 'secondary' : 'destructive'}
                  className="text-[10px]"
                >
                  {stats.dataFreshness.toFixed(0)}% Fresh
                </Badge>
                {isOpen ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              </div>
            </div>
          </CollapsibleTrigger>
        </CardHeader>

        <CollapsibleContent>
          <CardContent className="space-y-3">
            {/* Controls Row */}
            <div className="flex flex-col sm:flex-row gap-2">
              <div className="relative flex-1">
                <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search assets..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-8 h-9 text-sm"
                />
              </div>
              <div className="flex gap-1">
                <Button
                  variant={filterSource === 'all' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setFilterSource('all')}
                  className="text-xs"
                >
                  All
                </Button>
                <Button
                  variant={filterSource === 'LIVE' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setFilterSource('LIVE')}
                  className="text-xs"
                >
                  Live
                </Button>
                <Button
                  variant={filterSource === 'CACHED' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setFilterSource('CACHED')}
                  className="text-xs"
                >
                  Cached
                </Button>
                <Button
                  variant={filterSource === 'STALE' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setFilterSource('STALE')}
                  className="text-xs"
                >
                  Stale
                </Button>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={refresh}
                disabled={isLoading}
                className="gap-1"
              >
                <RefreshCw className={cn("h-3 w-3", isLoading && "animate-spin")} />
                Refresh
              </Button>
            </div>

            {/* Stats Summary */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
              <div className="bg-muted/30 rounded-lg p-2">
                <p className="text-[10px] text-muted-foreground">Top Gainer</p>
                {stats.topGainer && (
                  <div className="flex items-center gap-1">
                    <TrendingUp className="h-3 w-3 text-success" />
                    <span className="text-xs font-mono">{stats.topGainer.symbol}</span>
                    <span className="text-xs text-success">+{stats.topGainer.change.toFixed(2)}%</span>
                  </div>
                )}
              </div>
              <div className="bg-muted/30 rounded-lg p-2">
                <p className="text-[10px] text-muted-foreground">Top Loser</p>
                {stats.topLoser && (
                  <div className="flex items-center gap-1">
                    <TrendingDown className="h-3 w-3 text-destructive" />
                    <span className="text-xs font-mono">{stats.topLoser.symbol}</span>
                    <span className="text-xs text-destructive">{stats.topLoser.change.toFixed(2)}%</span>
                  </div>
                )}
              </div>
              <div className="bg-muted/30 rounded-lg p-2">
                <p className="text-[10px] text-muted-foreground">Top Volume</p>
                {stats.topVolume && (
                  <div className="flex items-center gap-1">
                    <BarChart3 className="h-3 w-3 text-primary" />
                    <span className="text-xs font-mono">{stats.topVolume.symbol}</span>
                    <span className="text-xs text-muted-foreground">{formatVolume(stats.topVolume.volume)}</span>
                  </div>
                )}
              </div>
              <div className="bg-muted/30 rounded-lg p-2">
                <p className="text-[10px] text-muted-foreground">Avg Volatility</p>
                <div className="flex items-center gap-1">
                  <Activity className="h-3 w-3 text-primary" />
                  <span className="text-xs font-mono">{stats.avgVolatility.toFixed(2)}%</span>
                </div>
              </div>
            </div>

            {/* Column Headers */}
            <div className="grid grid-cols-12 gap-1 text-[10px] text-muted-foreground border-b border-border/50 pb-1">
              <button 
                className="col-span-2 flex items-center gap-1 hover:text-foreground text-left"
                onClick={() => handleSort('symbol')}
              >
                Symbol <ArrowUpDown className="h-3 w-3" />
              </button>
              <button 
                className="col-span-2 flex items-center gap-1 hover:text-foreground text-right justify-end"
                onClick={() => handleSort('price')}
              >
                Price <ArrowUpDown className="h-3 w-3" />
              </button>
              <button 
                className="col-span-2 flex items-center gap-1 hover:text-foreground text-right justify-end"
                onClick={() => handleSort('change')}
              >
                24h % <ArrowUpDown className="h-3 w-3" />
              </button>
              <button 
                className="col-span-2 flex items-center gap-1 hover:text-foreground text-right justify-end"
                onClick={() => handleSort('volume')}
              >
                Volume <ArrowUpDown className="h-3 w-3" />
              </button>
              <button 
                className="col-span-2 flex items-center gap-1 hover:text-foreground text-right justify-end"
                onClick={() => handleSort('volatility')}
              >
                Vol% <ArrowUpDown className="h-3 w-3" />
              </button>
              <div className="col-span-2 text-center">Source</div>
            </div>

            {/* Asset List */}
            <ScrollArea className="h-[400px]">
              <div className="space-y-0.5">
                {displayedAssets.slice(0, 200).map((asset) => (
                  <div 
                    key={asset.symbol}
                    className="grid grid-cols-12 gap-1 text-xs py-1.5 hover:bg-muted/30 rounded px-1 transition-colors"
                  >
                    <div className="col-span-2 font-mono font-medium truncate">
                      {asset.symbol}
                    </div>
                    <div className="col-span-2 text-right font-mono">
                      ${formatPrice(asset.price)}
                    </div>
                    <div className={cn(
                      "col-span-2 text-right font-mono",
                      asset.change >= 0 ? "text-success" : "text-destructive"
                    )}>
                      {asset.change >= 0 ? '+' : ''}{asset.change.toFixed(2)}%
                    </div>
                    <div className="col-span-2 text-right font-mono text-muted-foreground">
                      {formatVolume(asset.volume)}
                    </div>
                    <div className="col-span-2 text-right font-mono text-muted-foreground">
                      {asset.volatility.toFixed(2)}%
                    </div>
                    <div className="col-span-2 flex justify-center">
                      {getDataSourceBadge(asset.dataSource)}
                    </div>
                  </div>
                ))}
                {displayedAssets.length > 200 && (
                  <p className="text-xs text-muted-foreground text-center py-2">
                    Showing top 200 of {displayedAssets.length} assets
                  </p>
                )}
              </div>
            </ScrollArea>

            {/* Footer */}
            <div className="flex items-center justify-between text-[10px] text-muted-foreground pt-2 border-t border-border/50">
              <span>
                Last refresh: {lastRefresh ? lastRefresh.toLocaleTimeString() : 'Never'}
              </span>
              <span>
                Showing {Math.min(displayedAssets.length, 200)} of {displayedAssets.length} filtered / {stats.totalAssets} total
              </span>
            </div>
          </CardContent>
        </CollapsibleContent>
      </Collapsible>
    </Card>
  );
}
