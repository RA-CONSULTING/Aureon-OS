/**
 * Full Portfolio Display - Complete Exchange Data
 * Shows all balances, trades, positions with full metadata from Binance & Kraken
 */

import { useState, useEffect } from 'react';
import { useUserBalances } from '@/hooks/useUserBalances';
import { supabase } from '@/integrations/supabase/client';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { 
  Wallet, 
  TrendingUp, 
  TrendingDown, 
  RefreshCw, 
  Clock, 
  DollarSign,
  Activity,
  FileText,
  Hash,
  Calendar
} from 'lucide-react';
import { format } from 'date-fns';
import PredictionAccuracyPanel from '@/components/PredictionAccuracyPanel';
import AnomalyAlertsPanel from '@/components/AnomalyAlertsPanel';

interface TradeExecution {
  id: string;
  symbol: string;
  side: string;
  quantity: number;
  price: number | null;
  executed_price: number | null;
  status: string;
  exchange_order_id: string | null;
  signal_type: string;
  order_type: string;
  position_size_usdt: number;
  coherence: number;
  lighthouse_value: number;
  lighthouse_confidence: number;
  prism_level: number;
  stop_loss_price: number | null;
  take_profit_price: number | null;
  error_message: string | null;
  created_at: string;
  executed_at: string | null;
}

interface TradeAudit {
  id: string;
  trade_id: string;
  external_order_id: string | null;
  client_order_id: string | null;
  symbol: string;
  side: string;
  exchange: string;
  order_type: string | null;
  quantity: number;
  price: number | null;
  executed_qty: number | null;
  executed_price: number | null;
  commission: number | null;
  commission_asset: string | null;
  stage: string;
  validation_status: string | null;
  error_message: string | null;
  exchange_response: any;
  created_at: string;
  updated_at: string;
}

interface Position {
  id: string;
  symbol: string;
  side: string;
  entry_price: number;
  quantity: number;
  position_value_usdt: number;
  current_price: number | null;
  unrealized_pnl: number | null;
  realized_pnl: number | null;
  stop_loss_price: number | null;
  take_profit_price: number | null;
  status: string;
  opened_at: string;
  closed_at: string | null;
}

export default function FullPortfolioDisplay() {
  const { balances, totalEquityUsd, connectedExchanges, isLoading, refresh, lastUpdated } = useUserBalances(true, 15000);
  const [executions, setExecutions] = useState<TradeExecution[]>([]);
  const [auditLogs, setAuditLogs] = useState<TradeAudit[]>([]);
  const [positions, setPositions] = useState<Position[]>([]);
  const [loading, setLoading] = useState(true);

  // Fetch all trade data
  const fetchTradeData = async () => {
    setLoading(true);
    try {
      // Fetch executions
      const { data: execData } = await supabase
        .from('trading_executions')
        .select('*')
        .order('created_at', { ascending: false })
        .limit(100);
      
      // Fetch audit logs
      const { data: auditData } = await supabase
        .from('trade_audit_log')
        .select('*')
        .order('created_at', { ascending: false })
        .limit(100);
      
      // Fetch positions
      const { data: posData } = await supabase
        .from('trading_positions')
        .select('*')
        .order('opened_at', { ascending: false })
        .limit(100);

      setExecutions(execData || []);
      setAuditLogs(auditData || []);
      setPositions(posData || []);
    } catch (error) {
      console.error('Error fetching trade data:', error);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchTradeData();

    // Subscribe to real-time updates
    const execChannel = supabase
      .channel('portfolio-executions')
      .on('postgres_changes', { event: '*', schema: 'public', table: 'trading_executions' }, fetchTradeData)
      .subscribe();

    const posChannel = supabase
      .channel('portfolio-positions')
      .on('postgres_changes', { event: '*', schema: 'public', table: 'trading_positions' }, fetchTradeData)
      .subscribe();

    const auditChannel = supabase
      .channel('portfolio-audit')
      .on('postgres_changes', { event: '*', schema: 'public', table: 'trade_audit_log' }, fetchTradeData)
      .subscribe();

    return () => {
      supabase.removeChannel(execChannel);
      supabase.removeChannel(posChannel);
      supabase.removeChannel(auditChannel);
    };
  }, []);

  const openPositions = positions.filter(p => p.status === 'open');
  const closedPositions = positions.filter(p => p.status === 'closed');
  const totalRealizedPnl = closedPositions.reduce((sum, p) => sum + (p.realized_pnl || 0), 0);
  const totalUnrealizedPnl = openPositions.reduce((sum, p) => sum + (p.unrealized_pnl || 0), 0);

  return (
    <div className="space-y-6">
      {/* Header Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
        <StatCard
          title="Total Equity"
          value={`$${totalEquityUsd.toLocaleString(undefined, { minimumFractionDigits: 2 })}`}
          icon={<Wallet className="w-4 h-4" />}
          status="neutral"
        />
        <StatCard
          title="Connected Exchanges"
          value={connectedExchanges.length.toString()}
          icon={<Activity className="w-4 h-4" />}
          status={connectedExchanges.length > 0 ? 'success' : 'warning'}
        />
        <StatCard
          title="Open Positions"
          value={openPositions.length.toString()}
          icon={<TrendingUp className="w-4 h-4" />}
          status="neutral"
        />
        <StatCard
          title="Unrealized P&L"
          value={`${totalUnrealizedPnl >= 0 ? '+' : ''}$${totalUnrealizedPnl.toFixed(2)}`}
          icon={<DollarSign className="w-4 h-4" />}
          status={totalUnrealizedPnl >= 0 ? 'success' : 'error'}
        />
        <StatCard
          title="Realized P&L"
          value={`${totalRealizedPnl >= 0 ? '+' : ''}$${totalRealizedPnl.toFixed(2)}`}
          icon={<DollarSign className="w-4 h-4" />}
          status={totalRealizedPnl >= 0 ? 'success' : 'error'}
        />
        <StatCard
          title="Total Trades"
          value={executions.length.toString()}
          icon={<FileText className="w-4 h-4" />}
          status="neutral"
        />
      </div>

      {/* Refresh Controls */}
      <div className="flex items-center justify-between">
        <div className="text-sm text-muted-foreground">
          Last updated: {lastUpdated ? format(lastUpdated, 'HH:mm:ss') : '--:--:--'}
        </div>
        <Button variant="outline" size="sm" onClick={() => { refresh(); fetchTradeData(); }}>
          <RefreshCw className={`w-4 h-4 mr-2 ${isLoading || loading ? 'animate-spin' : ''}`} />
          Refresh All
        </Button>
      </div>

      <Tabs defaultValue="balances" className="w-full">
        <TabsList className="grid w-full grid-cols-7">
          <TabsTrigger value="balances">Balances</TabsTrigger>
          <TabsTrigger value="positions">Positions</TabsTrigger>
          <TabsTrigger value="executions">Executions</TabsTrigger>
          <TabsTrigger value="audit">Audit Log</TabsTrigger>
          <TabsTrigger value="consolidated">Portfolio</TabsTrigger>
          <TabsTrigger value="predictions">Predictions</TabsTrigger>
          <TabsTrigger value="anomalies">Anomalies</TabsTrigger>
        </TabsList>

        {/* BALANCES TAB */}
        <TabsContent value="balances" className="space-y-4">
          {balances.map(exchange => (
            <Card key={exchange.exchange} className="border-border/50 bg-card/50">
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="flex items-center gap-2">
                    <Badge variant={exchange.connected ? 'default' : 'secondary'}>
                      {exchange.exchange.toUpperCase()}
                    </Badge>
                    {exchange.connected ? (
                      <span className="w-2 h-2 rounded-full bg-success" />
                    ) : (
                      <span className="w-2 h-2 rounded-full bg-destructive" />
                    )}
                  </CardTitle>
                  <span className="text-xl font-bold font-mono">
                    ${exchange.totalUsd.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                  </span>
                </div>
                {exchange.error && (
                  <p className="text-xs text-warning">{exchange.error}</p>
                )}
              </CardHeader>
              <CardContent>
                {exchange.assets.length > 0 ? (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-border/50 text-muted-foreground">
                          <th className="text-left py-2 px-2">Asset</th>
                          <th className="text-right py-2 px-2">Free</th>
                          <th className="text-right py-2 px-2">Locked</th>
                          <th className="text-right py-2 px-2">Total</th>
                          <th className="text-right py-2 px-2">USD Value</th>
                        </tr>
                      </thead>
                      <tbody>
                        {exchange.assets.map(asset => (
                          <tr key={asset.asset} className="border-b border-border/20 hover:bg-muted/20">
                            <td className="py-2 px-2 font-bold">{asset.asset}</td>
                            <td className="py-2 px-2 text-right font-mono">{asset.free.toFixed(8)}</td>
                            <td className="py-2 px-2 text-right font-mono text-warning">{asset.locked.toFixed(8)}</td>
                            <td className="py-2 px-2 text-right font-mono">{(asset.free + asset.locked).toFixed(8)}</td>
                            <td className="py-2 px-2 text-right font-mono text-success">${asset.usdValue.toFixed(2)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <p className="text-center text-muted-foreground py-4">
                    {exchange.connected ? 'No assets found' : 'Not connected'}
                  </p>
                )}
              </CardContent>
            </Card>
          ))}
        </TabsContent>

        {/* POSITIONS TAB */}
        <TabsContent value="positions" className="space-y-4">
          <Card className="border-border/50 bg-card/50">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <TrendingUp className="w-5 h-5" />
                Open Positions ({openPositions.length})
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[400px]">
                {openPositions.length > 0 ? (
                  <div className="space-y-2">
                    {openPositions.map(pos => (
                      <PositionCard key={pos.id} position={pos} />
                    ))}
                  </div>
                ) : (
                  <p className="text-center text-muted-foreground py-8">No open positions</p>
                )}
              </ScrollArea>
            </CardContent>
          </Card>

          <Card className="border-border/50 bg-card/50">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <TrendingDown className="w-5 h-5" />
                Closed Positions ({closedPositions.length})
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[300px]">
                {closedPositions.length > 0 ? (
                  <div className="space-y-2">
                    {closedPositions.slice(0, 20).map(pos => (
                      <PositionCard key={pos.id} position={pos} />
                    ))}
                  </div>
                ) : (
                  <p className="text-center text-muted-foreground py-8">No closed positions</p>
                )}
              </ScrollArea>
            </CardContent>
          </Card>
        </TabsContent>

        {/* EXECUTIONS TAB */}
        <TabsContent value="executions">
          <Card className="border-border/50 bg-card/50">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Activity className="w-5 h-5" />
                Trade Executions ({executions.length})
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[600px]">
                {executions.length > 0 ? (
                  <div className="space-y-2">
                    {executions.map(exec => (
                      <ExecutionCard key={exec.id} execution={exec} />
                    ))}
                  </div>
                ) : (
                  <p className="text-center text-muted-foreground py-8">No executions yet</p>
                )}
              </ScrollArea>
            </CardContent>
          </Card>
        </TabsContent>

        {/* AUDIT LOG TAB */}
        <TabsContent value="audit">
          <Card className="border-border/50 bg-card/50">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileText className="w-5 h-5" />
                Trade Audit Log ({auditLogs.length})
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[600px]">
                {auditLogs.length > 0 ? (
                  <div className="space-y-2">
                    {auditLogs.map(audit => (
                      <AuditCard key={audit.id} audit={audit} />
                    ))}
                  </div>
                ) : (
                  <p className="text-center text-muted-foreground py-8">No audit logs yet</p>
                )}
              </ScrollArea>
            </CardContent>
          </Card>
        </TabsContent>

        {/* CONSOLIDATED PORTFOLIO TAB */}
        <TabsContent value="consolidated">
          <ConsolidatedPortfolio balances={balances} />
        </TabsContent>
        {/* PREDICTIONS TAB */}
        <TabsContent value="predictions">
          <PredictionAccuracyPanel />
        </TabsContent>

        {/* ANOMALIES TAB */}
        <TabsContent value="anomalies">
          <AnomalyAlertsPanel />
        </TabsContent>
      </Tabs>
    </div>
  );
}

// Stat Card Component
function StatCard({ title, value, icon, status }: { title: string; value: string; icon: React.ReactNode; status: 'success' | 'error' | 'warning' | 'neutral' }) {
  const statusColors = {
    success: 'text-success border-success/30 bg-success/5',
    error: 'text-destructive border-destructive/30 bg-destructive/5',
    warning: 'text-warning border-warning/30 bg-warning/5',
    neutral: 'text-foreground border-border/50 bg-card/50',
  };

  return (
    <Card className={`${statusColors[status]} backdrop-blur`}>
      <CardContent className="p-4">
        <div className="flex items-center gap-2 text-muted-foreground mb-1">
          {icon}
          <span className="text-xs">{title}</span>
        </div>
        <div className="text-lg font-bold font-mono">{value}</div>
      </CardContent>
    </Card>
  );
}

// Position Card Component
function PositionCard({ position }: { position: Position }) {
  const pnl = position.status === 'closed' ? position.realized_pnl : position.unrealized_pnl;
  const pnlPositive = (pnl || 0) >= 0;

  return (
    <div className={`p-3 rounded-lg border ${pnlPositive ? 'border-success/30 bg-success/5' : 'border-destructive/30 bg-destructive/5'}`}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Badge variant={position.side === 'BUY' ? 'default' : 'destructive'}>
            {position.side}
          </Badge>
          <span className="font-bold">{position.symbol}</span>
          <Badge variant="outline">{position.status.toUpperCase()}</Badge>
        </div>
        <span className={`font-mono font-bold ${pnlPositive ? 'text-success' : 'text-destructive'}`}>
          {pnlPositive ? '+' : ''}${(pnl || 0).toFixed(2)}
        </span>
      </div>
      <div className="grid grid-cols-4 gap-2 text-xs text-muted-foreground">
        <div><span className="text-foreground">Entry:</span> ${position.entry_price.toFixed(4)}</div>
        <div><span className="text-foreground">Qty:</span> {position.quantity.toFixed(6)}</div>
        <div><span className="text-foreground">Value:</span> ${position.position_value_usdt.toFixed(2)}</div>
        <div><span className="text-foreground">Current:</span> ${(position.current_price || 0).toFixed(4)}</div>
      </div>
      <div className="grid grid-cols-3 gap-2 text-xs text-muted-foreground mt-1">
        <div><Clock className="w-3 h-3 inline mr-1" />{format(new Date(position.opened_at), 'MMM dd HH:mm:ss')}</div>
        {position.stop_loss_price && <div className="text-destructive">SL: ${position.stop_loss_price.toFixed(4)}</div>}
        {position.take_profit_price && <div className="text-success">TP: ${position.take_profit_price.toFixed(4)}</div>}
      </div>
      <div className="text-xs text-muted-foreground mt-1">
        <Hash className="w-3 h-3 inline mr-1" />ID: {position.id.slice(0, 8)}...
      </div>
    </div>
  );
}

// Execution Card Component
function ExecutionCard({ execution }: { execution: TradeExecution }) {
  const execPrice = execution.executed_price || execution.price || 0;
  const value = execPrice * execution.quantity;

  return (
    <div className={`p-3 rounded-lg border ${execution.side === 'BUY' ? 'border-l-4 border-l-green-500' : 'border-l-4 border-l-red-500'} bg-muted/20`}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Badge variant={execution.side === 'BUY' ? 'default' : 'destructive'}>{execution.side}</Badge>
          <span className="font-bold">{execution.symbol}</span>
          <Badge variant="outline">{execution.signal_type}</Badge>
          <Badge variant={execution.status === 'filled' ? 'default' : 'secondary'}>{execution.status}</Badge>
        </div>
        <span className="font-mono text-foreground">${value.toFixed(2)}</span>
      </div>
      <div className="grid grid-cols-4 gap-2 text-xs">
        <div><span className="text-muted-foreground">Price:</span> <span className="font-mono">${execution.price?.toFixed(4) || '-'}</span></div>
        <div><span className="text-muted-foreground">Exec Price:</span> <span className="font-mono">${execution.executed_price?.toFixed(4) || '-'}</span></div>
        <div><span className="text-muted-foreground">Qty:</span> <span className="font-mono">{execution.quantity.toFixed(6)}</span></div>
        <div><span className="text-muted-foreground">Size:</span> <span className="font-mono">${execution.position_size_usdt.toFixed(2)}</span></div>
      </div>
      <div className="grid grid-cols-4 gap-2 text-xs mt-1">
        <div><span className="text-muted-foreground">Γ:</span> <span className="font-mono">{execution.coherence.toFixed(3)}</span></div>
        <div><span className="text-muted-foreground">L:</span> <span className="font-mono">{execution.lighthouse_value.toFixed(3)}</span></div>
        <div><span className="text-muted-foreground">Prism:</span> <span className="font-mono">{execution.prism_level}</span></div>
        {execution.exchange_order_id && <div><span className="text-muted-foreground">Order:</span> <span className="font-mono text-xs">{execution.exchange_order_id.slice(0, 12)}...</span></div>}
      </div>
      <div className="grid grid-cols-3 gap-2 text-xs mt-1">
        {execution.stop_loss_price && <div className="text-destructive">SL: ${execution.stop_loss_price.toFixed(4)}</div>}
        {execution.take_profit_price && <div className="text-success">TP: ${execution.take_profit_price.toFixed(4)}</div>}
        {execution.error_message && <div className="text-destructive truncate">{execution.error_message}</div>}
      </div>
      <div className="flex items-center gap-4 text-xs text-muted-foreground mt-2">
        <div><Calendar className="w-3 h-3 inline mr-1" />{format(new Date(execution.created_at), 'MMM dd HH:mm:ss.SSS')}</div>
        <div><Hash className="w-3 h-3 inline mr-1" />{execution.id.slice(0, 8)}...</div>
      </div>
    </div>
  );
}

// Audit Card Component
function AuditCard({ audit }: { audit: TradeAudit }) {
  const stageColors: Record<string, string> = {
    SIGNAL_GENERATED: 'bg-primary/20 text-primary',
    ORDER_SUBMITTED: 'bg-warning/20 text-warning',
    ORDER_CONFIRMED: 'bg-primary/20 text-primary',
    PARTIALLY_FILLED: 'bg-primary/20 text-primary',
    FILLED: 'bg-success/20 text-success',
    SETTLED: 'bg-success/20 text-success',
    FAILED: 'bg-destructive/20 text-destructive',
  };

  return (
    <div className="p-3 rounded-lg border border-border/30 bg-muted/10">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Badge className={stageColors[audit.stage] || 'bg-muted'}>{audit.stage}</Badge>
          <span className="font-bold">{audit.symbol}</span>
          <Badge variant={audit.side === 'BUY' ? 'default' : 'destructive'}>{audit.side}</Badge>
          <Badge variant="outline">{audit.exchange?.toUpperCase()}</Badge>
        </div>
        <Badge variant={audit.validation_status === 'confirmed' ? 'default' : 'secondary'}>
          {audit.validation_status || 'pending'}
        </Badge>
      </div>
      <div className="grid grid-cols-5 gap-2 text-xs">
        <div><span className="text-muted-foreground">Type:</span> {audit.order_type}</div>
        <div><span className="text-muted-foreground">Qty:</span> <span className="font-mono">{audit.quantity?.toFixed(6)}</span></div>
        <div><span className="text-muted-foreground">Exec Qty:</span> <span className="font-mono">{audit.executed_qty?.toFixed(6) || '-'}</span></div>
        <div><span className="text-muted-foreground">Price:</span> <span className="font-mono">${audit.price?.toFixed(4) || '-'}</span></div>
        <div><span className="text-muted-foreground">Exec Price:</span> <span className="font-mono">${audit.executed_price?.toFixed(4) || '-'}</span></div>
      </div>
      <div className="grid grid-cols-4 gap-2 text-xs mt-1">
        {audit.commission !== null && <div><span className="text-muted-foreground">Commission:</span> <span className="text-warning">{audit.commission?.toFixed(8)} {audit.commission_asset}</span></div>}
        {audit.external_order_id && <div><span className="text-muted-foreground">Ext Order:</span> <span className="font-mono">{audit.external_order_id}</span></div>}
        {audit.client_order_id && <div><span className="text-muted-foreground">Client:</span> <span className="font-mono">{audit.client_order_id?.slice(0, 12)}...</span></div>}
        <div><span className="text-muted-foreground">Trade ID:</span> <span className="font-mono">{audit.trade_id?.slice(0, 8)}...</span></div>
      </div>
      {audit.error_message && (
        <div className="mt-2 p-2 rounded bg-destructive/10 text-destructive text-xs">{audit.error_message}</div>
      )}
      {audit.exchange_response && (
        <details className="mt-2">
          <summary className="text-xs text-muted-foreground cursor-pointer">Exchange Response</summary>
          <pre className="mt-1 p-2 rounded bg-muted/20 text-xs overflow-x-auto">
            {JSON.stringify(audit.exchange_response, null, 2)}
          </pre>
        </details>
      )}
      <div className="flex items-center gap-4 text-xs text-muted-foreground mt-2">
        <div><Calendar className="w-3 h-3 inline mr-1" />Created: {format(new Date(audit.created_at), 'MMM dd HH:mm:ss')}</div>
        <div>Updated: {format(new Date(audit.updated_at), 'MMM dd HH:mm:ss')}</div>
        <div><Hash className="w-3 h-3 inline mr-1" />{audit.id.slice(0, 8)}...</div>
      </div>
    </div>
  );
}

// Consolidated Portfolio Component
function ConsolidatedPortfolio({ balances }: { balances: any[] }) {
  const assetMap = new Map<string, { free: number; locked: number; usdValue: number; exchanges: string[] }>();

  for (const exchange of balances) {
    if (!exchange.connected) continue;
    for (const asset of exchange.assets) {
      const existing = assetMap.get(asset.asset);
      if (existing) {
        existing.free += asset.free;
        existing.locked += asset.locked;
        existing.usdValue += asset.usdValue;
        existing.exchanges.push(exchange.exchange);
      } else {
        assetMap.set(asset.asset, {
          free: asset.free,
          locked: asset.locked,
          usdValue: asset.usdValue,
          exchanges: [exchange.exchange]
        });
      }
    }
  }

  const consolidated = Array.from(assetMap.entries())
    .map(([asset, data]) => ({ asset, ...data }))
    .sort((a, b) => b.usdValue - a.usdValue);

  const totalValue = consolidated.reduce((sum, a) => sum + a.usdValue, 0);

  return (
    <Card className="border-border/50 bg-card/50">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Wallet className="w-5 h-5" />
            Consolidated Portfolio
          </CardTitle>
          <span className="text-2xl font-bold font-mono text-success">
            ${totalValue.toLocaleString(undefined, { minimumFractionDigits: 2 })}
          </span>
        </div>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border/50 text-muted-foreground">
                <th className="text-left py-2 px-2">Asset</th>
                <th className="text-right py-2 px-2">Free</th>
                <th className="text-right py-2 px-2">Locked</th>
                <th className="text-right py-2 px-2">Total</th>
                <th className="text-right py-2 px-2">USD Value</th>
                <th className="text-right py-2 px-2">% Portfolio</th>
                <th className="text-left py-2 px-2">Exchanges</th>
              </tr>
            </thead>
            <tbody>
              {consolidated.map(asset => (
                <tr key={asset.asset} className="border-b border-border/20 hover:bg-muted/20">
                  <td className="py-2 px-2 font-bold">{asset.asset}</td>
                  <td className="py-2 px-2 text-right font-mono">{asset.free.toFixed(8)}</td>
                  <td className="py-2 px-2 text-right font-mono text-warning">{asset.locked.toFixed(8)}</td>
                  <td className="py-2 px-2 text-right font-mono">{(asset.free + asset.locked).toFixed(8)}</td>
                  <td className="py-2 px-2 text-right font-mono text-success">${asset.usdValue.toFixed(2)}</td>
                  <td className="py-2 px-2 text-right font-mono">{((asset.usdValue / totalValue) * 100).toFixed(1)}%</td>
                  <td className="py-2 px-2">
                    {asset.exchanges.map(ex => (
                      <Badge key={ex} variant="outline" className="mr-1 text-xs">{ex}</Badge>
                    ))}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}
