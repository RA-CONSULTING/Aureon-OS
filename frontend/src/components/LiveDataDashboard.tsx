/**
 * Live Data Dashboard - Real-Time Trading View
 * Shows live trades, accounts, P&L using WebSocket and API data
 * Now includes 🦆🪐 Platypus Planetary Coherence!
 * 🌉 Updated with Aureon Live Bridge integration!
 */

import { useGlobalState, useTradingState, useQuantumState, usePlatypusState } from '@/hooks/useGlobalState';
import { useUserBalances } from '@/hooks/useUserBalances';
import { useStrikeFeed } from '@/hooks/useStrikeFeed';
import { useBinanceWebSocket } from '@/hooks/useBinanceWebSocket';
import { useAureonLiveData } from '@/hooks/useAureonLiveData';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import PlatypusCoherencePanel from '@/components/PlatypusCoherencePanel';
import AnomalyAlertsPanel from '@/components/AnomalyAlertsPanel';
import { 
  Activity, 
  TrendingUp, 
  TrendingDown, 
  Wallet, 
  Zap, 
  Clock,
  ArrowUpRight,
  ArrowDownRight,
  RefreshCw,
  Orbit,
  Wifi,
  WifiOff,
  Brain,
  Target,
  Sparkles
} from 'lucide-react';
import { format } from 'date-fns';

export default function LiveDataDashboard() {
  const globalState = useGlobalState();
  const tradingState = useTradingState();
  const quantumState = useQuantumState();
  const platypusState = usePlatypusState();
  const { events, executionCount } = useStrikeFeed(50);
  const { balances, totalEquityUsd, connectedExchanges, isLoading: balancesLoading, lastUpdated } = useUserBalances(true, 10000);
  const { marketData, connected: wsConnected } = useBinanceWebSocket(['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT']);
  
  // 🌉 AUREON LIVE BRIDGE - Real-time data from Python systems
  const bridgeData = useAureonLiveData();

  const winRate = tradingState.totalTrades > 0 
    ? ((tradingState.winningTrades / tradingState.totalTrades) * 100).toFixed(1)
    : '0.0';

  return (
    <div className="min-h-screen bg-background p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold text-foreground">
            🦆 AUREON LIVE DATA VIEWER
          </h1>
          <p className="text-muted-foreground flex items-center gap-2 mt-1">
            Real-Time Trading Data • WebSocket Connected
            {wsConnected && (
              <Badge variant="default" className="bg-success/20 text-success border-success/50">
                <Activity className="w-3 h-3 mr-1 animate-pulse" />
                WS LIVE
              </Badge>
            )}
            {bridgeData.connected && (
              <Badge variant="default" className="bg-primary/20 text-primary border-primary/50">
                <Wifi className="w-3 h-3 mr-1 animate-pulse" />
                BRIDGE LIVE
              </Badge>
            )}
            {globalState.isRunning && (
              <Badge variant="default" className="bg-primary/20 text-primary border-primary/50">
                SYSTEMS ONLINE
              </Badge>
            )}
          </p>
        </div>
        <div className="text-right">
          <div className="text-sm text-muted-foreground">Last Update</div>
          <div className="text-foreground font-mono">
            {lastUpdated ? format(lastUpdated, 'HH:mm:ss') : '--:--:--'}
          </div>
        </div>
      </div>

      {/* Main Stats Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4 mb-6">
        <StatCard 
          title="Total Equity" 
          value={`$${totalEquityUsd.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
          icon={<Wallet className="w-4 h-4" />}
          status={totalEquityUsd > 0 ? 'success' : 'neutral'}
        />
        <StatCard 
          title="Net P&L" 
          value={`${tradingState.totalPnl >= 0 ? '+' : ''}$${tradingState.totalPnl.toFixed(2)}`}
          icon={tradingState.totalPnl >= 0 ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
          status={tradingState.totalPnl >= 0 ? 'success' : 'error'}
        />
        <StatCard 
          title="Total Trades" 
          value={tradingState.totalTrades.toString()}
          icon={<Activity className="w-4 h-4" />}
          status="neutral"
        />
        <StatCard 
          title="Win Rate" 
          value={`${winRate}%`}
          icon={<Zap className="w-4 h-4" />}
          status={parseFloat(winRate) >= 51 ? 'success' : parseFloat(winRate) > 0 ? 'warning' : 'neutral'}
        />
        <StatCard 
          title="Coherence Γ" 
          value={quantumState.coherence.toFixed(3)}
          icon={<RefreshCw className="w-4 h-4" />}
          status={quantumState.coherence >= 0.45 ? 'success' : 'warning'}
        />
        <StatCard 
          title="Lambda Λ" 
          value={quantumState.lambda.toFixed(2)}
          icon={<Zap className="w-4 h-4" />}
          status="neutral"
        />
        <StatCard 
          title="🪐 Planetary Γ" 
          value={platypusState.planetaryCoherence.toFixed(3)}
          icon={<Orbit className="w-4 h-4" />}
          status={platypusState.lighthouseActive ? 'success' : platypusState.planetaryCoherence >= 0.5 ? 'warning' : 'neutral'}
          extra={platypusState.lighthouseActive ? '🔦' : undefined}
        />
      </div>

      {/* 🌉 BRIDGE SYSTEMS STATUS - Trading system signals from Python */}
      {bridgeData.connected && (
        <div className="mb-6 p-4 rounded-lg border border-primary/30 bg-primary/5">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Wifi className="w-5 h-5 text-primary animate-pulse" />
              <span className="font-bold text-primary">AUREON LIVE BRIDGE</span>
              <Badge variant="outline" className="text-xs">
                {bridgeData.updatesReceived} updates
              </Badge>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant="default" className="bg-success/20 text-success">
                ${bridgeData.totalPortfolioValue.toLocaleString(undefined, { maximumFractionDigits: 2 })} Total
              </Badge>
              <Badge variant="outline" className="text-warning">
                {bridgeData.signalCount} Signals
              </Badge>
            </div>
          </div>
          
          {/* Systems Online */}
          <div className="flex flex-wrap gap-2 mb-3">
            {bridgeData.systemsOnline.map(system => (
              <Badge key={system} variant="default" className="text-xs bg-success/20 text-success">
                {system === 'V14' ? '🏆' : system === 'Mycelium' ? '🍄' : system === 'Commando' ? '🦅' : 
                 system === 'Nexus' ? '🔮' : system === 'Multiverse' ? '🌌' : system === 'MinerBrain' ? '🧠' : 
                 system === 'Omega' ? '🔱' : '⚡'} {system}
              </Badge>
            ))}
          </div>
          
          {/* Top Signals */}
          {bridgeData.signals.length > 0 && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
              {bridgeData.signals.slice(0, 4).map((sig, i) => (
                <div key={`${sig.system}-${sig.symbol}-${i}`} 
                     className={`p-2 rounded border text-xs ${
                       sig.signal_type === 'BUY' || sig.signal_type === 'CONVERT' 
                         ? 'bg-success/10 border-success/30' 
                         : sig.signal_type === 'SELL' 
                         ? 'bg-destructive/10 border-destructive/30' 
                         : 'bg-warning/10 border-warning/30'
                     }`}>
                  <div className="flex justify-between items-center">
                    <span className="font-mono font-bold">{sig.symbol}</span>
                    <Badge variant="outline" className="text-[10px]">{sig.signal_type}</Badge>
                  </div>
                  <div className="text-muted-foreground mt-1">
                    {sig.system} • {(sig.confidence * 100).toFixed(0)}%
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        {/* Left: Live Market Data */}
        <div className="space-y-4">
          <Card className="border-border/50 bg-card/50 backdrop-blur">
            <CardHeader className="pb-2">
              <CardTitle className="text-lg flex items-center gap-2">
                <Activity className="w-5 h-5 text-primary" />
                Live Market Data
                {wsConnected && <span className="w-2 h-2 rounded-full bg-success animate-pulse" />}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {Object.entries(marketData).length > 0 ? (
                  Object.values(marketData).map((ticker) => (
                    <div key={ticker.symbol} className="flex items-center justify-between p-3 rounded-lg bg-muted/30 border border-border/30">
                      <div>
                        <div className="font-bold text-foreground">{ticker.symbol}</div>
                        <div className="text-xs text-muted-foreground">
                          Vol: {(ticker.volume24h / 1000000).toFixed(2)}M
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="font-mono text-lg text-foreground">
                          ${ticker.price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </div>
                        <div className={`text-sm font-mono ${ticker.priceChange24h >= 0 ? 'text-success' : 'text-destructive'}`}>
                          {ticker.priceChange24h >= 0 ? '+' : ''}{ticker.priceChange24h.toFixed(2)}%
                        </div>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="text-center text-muted-foreground py-8">
                    Connecting to WebSocket...
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* 🦆🪐 Platypus Planetary Coherence Panel */}
          <PlatypusCoherencePanel />

          {/* 🔍 Anomaly Detection Panel */}
          <AnomalyAlertsPanel />
        </div>

        {/* Center-Left: Account Balances */}
        <div className="space-y-4">
          <Card className="border-border/50 bg-card/50 backdrop-blur">
            <CardHeader className="pb-2">
              <CardTitle className="text-lg flex items-center gap-2">
                <Wallet className="w-5 h-5 text-primary" />
                Exchange Balances
                {balancesLoading && <RefreshCw className="w-4 h-4 animate-spin text-muted-foreground" />}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[500px]">
                <div className="space-y-3">
                  {balances.length > 0 ? (
                    balances.map((exchange) => (
                      <div key={exchange.exchange} className="p-3 rounded-lg bg-muted/30 border border-border/30">
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center gap-2">
                            <Badge variant={exchange.connected ? 'default' : 'secondary'} className="text-xs">
                              {exchange.exchange.toUpperCase()}
                            </Badge>
                            {exchange.connected ? (
                              <span className="w-2 h-2 rounded-full bg-success" />
                            ) : (
                              <span className="w-2 h-2 rounded-full bg-muted-foreground" />
                            )}
                          </div>
                          <span className="font-mono text-foreground">
                            ${exchange.totalUsd.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                          </span>
                        </div>
                        {exchange.connected && exchange.assets.slice(0, 5).map((asset) => (
                          <div key={asset.asset} className="flex justify-between text-xs text-muted-foreground ml-2">
                            <span>{asset.asset}</span>
                            <span>{asset.free.toFixed(6)} (${asset.usdValue.toFixed(2)})</span>
                          </div>
                        ))}
                      </div>
                    ))
                  ) : (
                    <div className="text-center text-muted-foreground py-8">
                      {balancesLoading ? 'Loading balances...' : 'No exchange connections'}
                    </div>
                  )}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>
        </div>

        {/* Right: Live Trade Stream (now spans 2 columns) */}
        <Card className="border-border/50 bg-card/50 backdrop-blur lg:col-span-2">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-lg flex items-center gap-2">
                <Zap className="w-5 h-5 text-warning" />
                Live Trade Stream
              </CardTitle>
              <div className="flex items-center gap-4 text-sm">
                <span className="text-success">✓ {executionCount.success} Filled</span>
                <span className="text-destructive">✗ {executionCount.failed} Failed</span>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-[600px]">
              <div className="space-y-2">
                {events.length > 0 ? (
                  events.map((event) => (
                    <TradeEventRow key={event.id} event={event} />
                  ))
                ) : (
                  <div className="text-center text-muted-foreground py-16">
                    <Activity className="w-12 h-12 mx-auto mb-4 opacity-30" />
                    <p>Waiting for live trade events...</p>
                    <p className="text-xs mt-2">Trades will appear here in real-time</p>
                  </div>
                )}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>
      </div>

      {/* Recent Trades Summary */}
      {tradingState.recentTrades.length > 0 && (
        <Card className="mt-4 border-border/50 bg-card/50 backdrop-blur">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg flex items-center gap-2">
              <Clock className="w-5 h-5 text-primary" />
              Recent Trade History
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-2">
              {tradingState.recentTrades.slice(0, 8).map((trade, i) => (
                <div key={i} className={`p-3 rounded-lg border ${trade.success ? 'border-success/30 bg-success/5' : 'border-destructive/30 bg-destructive/5'}`}>
                  <div className="flex items-center justify-between">
                    <span className={`font-bold ${trade.side === 'BUY' ? 'text-success' : 'text-destructive'}`}>
                      {trade.side}
                    </span>
                    <span className="text-xs text-muted-foreground">{trade.time}</span>
                  </div>
                  <div className="text-foreground font-mono">{trade.symbol}</div>
                  <div className={`text-sm ${trade.pnl >= 0 ? 'text-success' : 'text-destructive'}`}>
                    {trade.pnl >= 0 ? '+' : ''}${trade.pnl.toFixed(2)}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// Stat Card Component
function StatCard({ 
  title, 
  value, 
  icon, 
  status,
  extra
}: { 
  title: string; 
  value: string; 
  icon: React.ReactNode; 
  status: 'success' | 'error' | 'warning' | 'neutral';
  extra?: string;
}) {
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
          {extra && <span className="text-sm animate-pulse">{extra}</span>}
        </div>
        <div className="text-xl font-bold font-mono">{value}</div>
      </CardContent>
    </Card>
  );
}

// Trade Event Row Component
function TradeEventRow({ event }: { event: any }) {
  const typeStyles: Record<string, string> = {
    execution: 'border-l-4 border-l-blue-500',
    position_update: 'border-l-4 border-l-purple-500',
    lighthouse: 'border-l-4 border-l-yellow-500',
    signal: 'border-l-4 border-l-cyan-500',
    order_queue: 'border-l-4 border-l-orange-500',
  };

  const statusColors: Record<string, string> = {
    success: 'bg-success/10 text-success',
    failed: 'bg-destructive/10 text-destructive',
    pending: 'bg-warning/10 text-warning',
  };

  return (
    <div className={`p-3 rounded-lg bg-muted/20 ${typeStyles[event.type] || ''}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          {event.side === 'BUY' ? (
            <ArrowUpRight className="w-5 h-5 text-success" />
          ) : event.side === 'SELL' ? (
            <ArrowDownRight className="w-5 h-5 text-destructive" />
          ) : (
            <Activity className="w-5 h-5 text-primary" />
          )}
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-foreground">{event.symbol || event.type.toUpperCase()}</span>
              <Badge variant="outline" className={statusColors[event.status]}>
                {event.status}
              </Badge>
            </div>
            <div className="text-sm text-muted-foreground">{event.message}</div>
          </div>
        </div>
        <div className="text-right">
          {event.price && (
            <div className="font-mono text-foreground">${event.price.toFixed(4)}</div>
          )}
          {event.pnl !== undefined && (
            <div className={`font-mono text-sm ${event.pnl >= 0 ? 'text-success' : 'text-destructive'}`}>
              {event.pnl >= 0 ? '+' : ''}${event.pnl.toFixed(2)}
            </div>
          )}
          <div className="text-xs text-muted-foreground">
            {event.timestamp ? format(new Date(event.timestamp), 'HH:mm:ss') : '--:--:--'}
          </div>
        </div>
      </div>
      {(event.coherence || event.lighthouse) && (
        <div className="flex gap-4 mt-2 text-xs text-muted-foreground">
          {event.coherence && <span>Γ: {event.coherence.toFixed(3)}</span>}
          {event.lighthouse && <span>L: {event.lighthouse.toFixed(3)}</span>}
        </div>
      )}
    </div>
  );
}
