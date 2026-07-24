import { useEffect, useState, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Loader2, RefreshCw, TrendingUp, TrendingDown, Clock, DollarSign, Fuel } from "lucide-react";
import { supabase } from "@/integrations/supabase/client";
import { useToast } from "@/hooks/use-toast";

interface PositionWithPnL {
  id: string;
  symbol: string;
  side: "BUY" | "SELL";
  entryPrice: number;
  quantity: number;
  positionValueUsdt: number;
  currentPrice: number;
  unrealizedPnl: number;
  unrealizedPnlPct: number;
  openedAt: string;
  exchange: string;
  entryFee: number;
  gasCost: number;
  totalCosts: number;
  netPnl: number;
  holdingDurationMs: number;
  holdingDurationFormatted: string;
}

interface Summary {
  totalPnl: number;
  totalCosts: number;
  netPnl: number;
  positionCount: number;
}

export function LivePnLTable() {
  const { toast } = useToast();
  const [positions, setPositions] = useState<PositionWithPnL[]>([]);
  const [summary, setSummary] = useState<Summary>({ totalPnl: 0, totalCosts: 0, netPnl: 0, positionCount: 0 });
  const [loading, setLoading] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetchPositions = useCallback(async () => {
    setLoading(true);
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) {
        toast({ title: "Not authenticated", variant: "destructive" });
        return;
      }

      const { data, error } = await supabase.functions.invoke("fetch-positions-pnl", {
        headers: { Authorization: `Bearer ${session.access_token}` },
      });

      if (error) throw error;

      if (data?.success) {
        setPositions(data.positions || []);
        setSummary(data.summary || { totalPnl: 0, totalCosts: 0, netPnl: 0, positionCount: 0 });
        setLastUpdated(new Date());
      } else {
        throw new Error(data?.error || "Failed to fetch positions");
      }
    } catch (err: any) {
      console.error("Fetch positions error:", err);
      toast({
        title: "Failed to fetch positions",
        description: err?.message || String(err),
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    fetchPositions();
    // Auto-refresh every 10 seconds for live P&L
    const interval = setInterval(fetchPositions, 10000);
    return () => clearInterval(interval);
  }, [fetchPositions]);

  const formatCurrency = (value: number) => {
    const prefix = value >= 0 ? "+$" : "-$";
    return `${prefix}${Math.abs(value).toFixed(2)}`;
  };

  const formatPercent = (value: number) => {
    const prefix = value >= 0 ? "+" : "";
    return `${prefix}${value.toFixed(2)}%`;
  };

  const binancePositions = positions.filter(p => p.exchange === "binance");
  const krakenPositions = positions.filter(p => p.exchange === "kraken");

  const calcSummary = (items: PositionWithPnL[]) => ({
    totalPnl: items.reduce((s, p) => s + p.unrealizedPnl, 0),
    totalCosts: items.reduce((s, p) => s + p.totalCosts, 0),
    netPnl: items.reduce((s, p) => s + p.netPnl, 0),
    count: items.length,
  });

  const binanceSummary = calcSummary(binancePositions);
  const krakenSummary = calcSummary(krakenPositions);

  const renderPositionCard = (pos: PositionWithPnL) => (
    <div key={pos.id} className="rounded-lg border border-border/30 bg-background/50 p-3 text-xs">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-1">
          <Badge variant={pos.side === "BUY" ? "default" : "destructive"} className="text-[10px] px-1">
            {pos.side}
          </Badge>
          <span className="font-semibold">{pos.symbol}</span>
        </div>
        <div className={`font-mono font-bold ${pos.netPnl >= 0 ? "text-success" : "text-destructive"}`}>
          {formatCurrency(pos.netPnl)}
        </div>
      </div>
      <div className="grid grid-cols-2 gap-1 text-muted-foreground">
        <div>Entry: <span className="font-mono text-foreground">${pos.entryPrice.toFixed(2)}</span></div>
        <div>Now: <span className="font-mono text-foreground">${pos.currentPrice.toFixed(2)}</span></div>
        <div>Qty: <span className="font-mono text-foreground">{pos.quantity.toFixed(4)}</span></div>
        <div>Fees: <span className="font-mono text-warning">-${pos.totalCosts.toFixed(2)}</span></div>
      </div>
      <div className="mt-1 text-muted-foreground flex items-center gap-1">
        <Clock className="h-3 w-3" /> {pos.holdingDurationFormatted}
      </div>
    </div>
  );

  const renderExchangeColumn = (
    items: PositionWithPnL[],
    exchange: string,
    emoji: string,
    sum: { totalPnl: number; totalCosts: number; netPnl: number; count: number }
  ) => (
    <div className="flex-1 min-w-0">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-lg">{emoji}</span>
          <span className="font-semibold capitalize">{exchange}</span>
          <Badge variant="outline" className="text-xs">{sum.count}</Badge>
        </div>
        <span className={`text-sm font-mono ${sum.netPnl >= 0 ? "text-success" : "text-destructive"}`}>
          {formatCurrency(sum.netPnl)}
        </span>
      </div>
      <ScrollArea className="h-72 rounded-lg border border-border/50 bg-muted/20 p-2">
        {items.length === 0 ? (
          <div className="text-xs text-muted-foreground text-center py-8">
            No {exchange} positions
          </div>
        ) : (
          <div className="space-y-2">
            {items.map(renderPositionCard)}
          </div>
        )}
      </ScrollArea>
      <div className="mt-2 grid grid-cols-3 gap-2 text-xs">
        <div>
          <div className="text-muted-foreground">Gross</div>
          <div className={`font-mono ${sum.totalPnl >= 0 ? "text-success" : "text-destructive"}`}>
            {formatCurrency(sum.totalPnl)}
          </div>
        </div>
        <div>
          <div className="text-muted-foreground">Costs</div>
          <div className="font-mono text-warning">-${sum.totalCosts.toFixed(2)}</div>
        </div>
        <div>
          <div className="text-muted-foreground">Net</div>
          <div className={`font-mono font-semibold ${sum.netPnl >= 0 ? "text-success" : "text-destructive"}`}>
            {formatCurrency(sum.netPnl)}
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span>Live P&L Tracker</span>
            <Badge variant="outline" className="text-xs">
              Net: {formatCurrency(summary.netPnl)}
            </Badge>
          </div>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            {lastUpdated && <span>{lastUpdated.toLocaleTimeString()}</span>}
            <Button variant="ghost" size="sm" onClick={fetchPositions} disabled={loading}>
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
            </Button>
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent>
        {loading && positions.length === 0 ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <div className="flex gap-4">
            {renderExchangeColumn(binancePositions, "binance", "🟡", binanceSummary)}
            {renderExchangeColumn(krakenPositions, "kraken", "🐙", krakenSummary)}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
