import { useState, useEffect } from 'react';
import { Card } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { supabase } from '@/integrations/supabase/client';
import { TrendingUp, TrendingDown, Target, Calendar, Award, AlertTriangle } from 'lucide-react';
import { LineChart, Line, BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

interface TradeMetrics {
  totalTrades: number;
  winningTrades: number;
  losingTrades: number;
  winRate: number;
  totalPnL: number;
  avgPnL: number;
  avgWin: number;
  avgLoss: number;
  bestTrade: any;
  worstTrade: any;
  profitFactor: number;
  avgTradeDuration: number;
}

interface TimeSeriesData {
  date: string;
  pnl: number;
  cumulativePnL: number;
  trades: number;
}

export const TradingAnalytics = () => {
  const [timeRange, setTimeRange] = useState<'24h' | '7d' | '30d' | 'all'>('7d');
  const [metrics, setMetrics] = useState<TradeMetrics>({
    totalTrades: 0,
    winningTrades: 0,
    losingTrades: 0,
    winRate: 0,
    totalPnL: 0,
    avgPnL: 0,
    avgWin: 0,
    avgLoss: 0,
    bestTrade: null,
    worstTrade: null,
    profitFactor: 0,
    avgTradeDuration: 0,
  });
  const [timeSeriesData, setTimeSeriesData] = useState<TimeSeriesData[]>([]);
  const [symbolPerformance, setSymbolPerformance] = useState<any[]>([]);

  useEffect(() => {
    loadAnalytics();
  }, [timeRange]);

  const getTimeRangeFilter = () => {
    const now = new Date();
    switch (timeRange) {
      case '24h':
        return new Date(now.getTime() - 24 * 60 * 60 * 1000).toISOString();
      case '7d':
        return new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000).toISOString();
      case '30d':
        return new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000).toISOString();
      default:
        return new Date(0).toISOString();
    }
  };

  const loadAnalytics = async () => {
    const timeFilter = getTimeRangeFilter();

    // Load closed positions
    const { data: closedPositions } = await supabase
      .from('trading_positions')
      .select('*')
      .eq('status', 'closed')
      .gte('closed_at', timeFilter)
      .order('closed_at', { ascending: true });

    if (!closedPositions || closedPositions.length === 0) {
      setMetrics({
        totalTrades: 0,
        winningTrades: 0,
        losingTrades: 0,
        winRate: 0,
        totalPnL: 0,
        avgPnL: 0,
        avgWin: 0,
        avgLoss: 0,
        bestTrade: null,
        worstTrade: null,
        profitFactor: 0,
        avgTradeDuration: 0,
      });
      return;
    }

    // Calculate metrics
    const wins = closedPositions.filter(p => Number(p.realized_pnl || 0) > 0);
    const losses = closedPositions.filter(p => Number(p.realized_pnl || 0) < 0);
    const totalPnL = closedPositions.reduce((sum, p) => sum + Number(p.realized_pnl || 0), 0);
    const totalWinPnL = wins.reduce((sum, p) => sum + Number(p.realized_pnl || 0), 0);
    const totalLossPnL = Math.abs(losses.reduce((sum, p) => sum + Number(p.realized_pnl || 0), 0));

    const sortedByPnL = [...closedPositions].sort((a, b) => 
      Number(b.realized_pnl || 0) - Number(a.realized_pnl || 0)
    );

    // Calculate average trade duration
    const durations = closedPositions.map(p => {
      const opened = new Date(p.opened_at).getTime();
      const closed = new Date(p.closed_at!).getTime();
      return (closed - opened) / (1000 * 60); // minutes
    });
    const avgDuration = durations.reduce((sum, d) => sum + d, 0) / durations.length;

    setMetrics({
      totalTrades: closedPositions.length,
      winningTrades: wins.length,
      losingTrades: losses.length,
      winRate: (wins.length / closedPositions.length) * 100,
      totalPnL,
      avgPnL: totalPnL / closedPositions.length,
      avgWin: wins.length > 0 ? totalWinPnL / wins.length : 0,
      avgLoss: losses.length > 0 ? totalLossPnL / losses.length : 0,
      bestTrade: sortedByPnL[0],
      worstTrade: sortedByPnL[sortedByPnL.length - 1],
      profitFactor: totalLossPnL > 0 ? totalWinPnL / totalLossPnL : 0,
      avgTradeDuration: avgDuration,
    });

    // Time series data
    const dailyData = new Map<string, { pnl: number; trades: number }>();
    closedPositions.forEach(p => {
      const date = new Date(p.closed_at!).toLocaleDateString();
      const existing = dailyData.get(date) || { pnl: 0, trades: 0 };
      dailyData.set(date, {
        pnl: existing.pnl + Number(p.realized_pnl || 0),
        trades: existing.trades + 1,
      });
    });

    let cumulativePnL = 0;
    const timeSeriesArray: TimeSeriesData[] = Array.from(dailyData.entries()).map(([date, data]) => {
      cumulativePnL += data.pnl;
      return {
        date,
        pnl: data.pnl,
        cumulativePnL,
        trades: data.trades,
      };
    });
    setTimeSeriesData(timeSeriesArray);

    // Symbol performance
    const symbolStats = new Map<string, { pnl: number; trades: number; wins: number }>();
    closedPositions.forEach(p => {
      const existing = symbolStats.get(p.symbol) || { pnl: 0, trades: 0, wins: 0 };
      const pnl = Number(p.realized_pnl || 0);
      symbolStats.set(p.symbol, {
        pnl: existing.pnl + pnl,
        trades: existing.trades + 1,
        wins: existing.wins + (pnl > 0 ? 1 : 0),
      });
    });

    const symbolPerfArray = Array.from(symbolStats.entries()).map(([symbol, stats]) => ({
      symbol,
      pnl: stats.pnl,
      trades: stats.trades,
      winRate: (stats.wins / stats.trades) * 100,
    })).sort((a, b) => b.pnl - a.pnl);
    setSymbolPerformance(symbolPerfArray);
  };

  const COLORS = ['hsl(var(--primary))', 'hsl(var(--destructive))', 'hsl(var(--chart-3))', 'hsl(var(--chart-4))'];

  return (
    <div className="space-y-6">
      {/* Time Range Selector */}
      <div className="flex gap-2">
        {(['24h', '7d', '30d', 'all'] as const).map((range) => (
          <button
            key={range}
            onClick={() => setTimeRange(range)}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              timeRange === range
                ? 'bg-primary text-primary-foreground'
                : 'bg-muted hover:bg-muted/80'
            }`}
          >
            {range === '24h' ? '24 Hours' : range === '7d' ? '7 Days' : range === '30d' ? '30 Days' : 'All Time'}
          </button>
        ))}
      </div>

      {/* Key Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">Total P&L</p>
              <p className={`text-2xl font-bold ${metrics.totalPnL >= 0 ? 'text-success' : 'text-destructive'}`}>
                {metrics.totalPnL >= 0 ? '+' : ''}${metrics.totalPnL.toFixed(2)}
              </p>
            </div>
            {metrics.totalPnL >= 0 ? (
              <TrendingUp className="h-8 w-8 text-success" />
            ) : (
              <TrendingDown className="h-8 w-8 text-destructive" />
            )}
          </div>
        </Card>

        <Card className="p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">Win Rate</p>
              <p className="text-2xl font-bold">{metrics.winRate.toFixed(1)}%</p>
              <p className="text-xs text-muted-foreground">
                {metrics.winningTrades}W / {metrics.losingTrades}L
              </p>
            </div>
            <Target className="h-8 w-8 text-primary" />
          </div>
        </Card>

        <Card className="p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">Avg P&L</p>
              <p className={`text-2xl font-bold ${metrics.avgPnL >= 0 ? 'text-success' : 'text-destructive'}`}>
                {metrics.avgPnL >= 0 ? '+' : ''}${metrics.avgPnL.toFixed(2)}
              </p>
              <p className="text-xs text-muted-foreground">{metrics.totalTrades} trades</p>
            </div>
            <Calendar className="h-8 w-8 text-primary" />
          </div>
        </Card>

        <Card className="p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">Profit Factor</p>
              <p className="text-2xl font-bold">{metrics.profitFactor.toFixed(2)}</p>
              <p className="text-xs text-muted-foreground">
                Avg Duration: {metrics.avgTradeDuration.toFixed(0)}m
              </p>
            </div>
            <Award className="h-8 w-8 text-warning" />
          </div>
        </Card>
      </div>

      {/* Charts Section */}
      <Tabs defaultValue="performance" className="w-full">
        <TabsList>
          <TabsTrigger value="performance">Performance</TabsTrigger>
          <TabsTrigger value="distribution">Distribution</TabsTrigger>
          <TabsTrigger value="symbols">By Symbol</TabsTrigger>
          <TabsTrigger value="trades">Best/Worst</TabsTrigger>
        </TabsList>

        <TabsContent value="performance" className="space-y-4">
          <Card className="p-6">
            <h3 className="text-lg font-semibold mb-4">Cumulative P&L</h3>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={timeSeriesData}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis dataKey="date" stroke="hsl(var(--muted-foreground))" />
                <YAxis stroke="hsl(var(--muted-foreground))" />
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: 'hsl(var(--popover))', 
                    border: '1px solid hsl(var(--border))',
                    borderRadius: '8px'
                  }}
                />
                <Legend />
                <Line 
                  type="monotone" 
                  dataKey="cumulativePnL" 
                  stroke="hsl(var(--primary))" 
                  strokeWidth={2}
                  name="Cumulative P&L"
                />
              </LineChart>
            </ResponsiveContainer>
          </Card>

          <Card className="p-6">
            <h3 className="text-lg font-semibold mb-4">Daily P&L</h3>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={timeSeriesData}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis dataKey="date" stroke="hsl(var(--muted-foreground))" />
                <YAxis stroke="hsl(var(--muted-foreground))" />
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: 'hsl(var(--popover))', 
                    border: '1px solid hsl(var(--border))',
                    borderRadius: '8px'
                  }}
                />
                <Legend />
                <Bar dataKey="pnl" name="Daily P&L">
                  {timeSeriesData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.pnl >= 0 ? 'hsl(var(--chart-2))' : 'hsl(var(--destructive))'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </Card>
        </TabsContent>

        <TabsContent value="distribution" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card className="p-6">
              <h3 className="text-lg font-semibold mb-4">Win/Loss Distribution</h3>
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={[
                      { name: 'Wins', value: metrics.winningTrades },
                      { name: 'Losses', value: metrics.losingTrades },
                    ]}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={(entry) => `${entry.name}: ${entry.value}`}
                    outerRadius={80}
                    fill="hsl(var(--primary))"
                    dataKey="value"
                  >
                    <Cell fill="hsl(var(--chart-2))" />
                    <Cell fill="hsl(var(--destructive))" />
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </Card>

            <Card className="p-6">
              <h3 className="text-lg font-semibold mb-4">Performance Breakdown</h3>
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between mb-2">
                    <span className="text-sm text-muted-foreground">Average Win</span>
                    <span className="text-sm font-bold text-success">+${metrics.avgWin.toFixed(2)}</span>
                  </div>
                  <div className="h-2 bg-muted rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-success" 
                      style={{ width: `${(metrics.avgWin / (metrics.avgWin + metrics.avgLoss)) * 100}%` }}
                    />
                  </div>
                </div>
                <div>
                  <div className="flex justify-between mb-2">
                    <span className="text-sm text-muted-foreground">Average Loss</span>
                    <span className="text-sm font-bold text-destructive">-${metrics.avgLoss.toFixed(2)}</span>
                  </div>
                  <div className="h-2 bg-muted rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-destructive" 
                      style={{ width: `${(metrics.avgLoss / (metrics.avgWin + metrics.avgLoss)) * 100}%` }}
                    />
                  </div>
                </div>
                <div className="pt-4 border-t">
                  <div className="flex justify-between">
                    <span className="text-sm font-medium">Risk/Reward Ratio</span>
                    <span className="text-sm font-bold">
                      {metrics.avgLoss > 0 ? (metrics.avgWin / metrics.avgLoss).toFixed(2) : 'N/A'}
                    </span>
                  </div>
                </div>
              </div>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="symbols" className="space-y-4">
          <Card className="p-6">
            <h3 className="text-lg font-semibold mb-4">Performance by Symbol</h3>
            <div className="space-y-3">
              {symbolPerformance.map((symbol, index) => (
                <div key={index} className="flex items-center justify-between p-3 border rounded-lg">
                  <div className="flex items-center gap-3">
                    <span className="font-semibold">{symbol.symbol}</span>
                    <Badge variant="outline">{symbol.trades} trades</Badge>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="text-right">
                      <p className="text-sm text-muted-foreground">Win Rate</p>
                      <p className="font-medium">{symbol.winRate.toFixed(1)}%</p>
                    </div>
                    <div className="text-right">
                      <p className={`text-lg font-bold ${symbol.pnl >= 0 ? 'text-success' : 'text-destructive'}`}>
                        {symbol.pnl >= 0 ? '+' : ''}${symbol.pnl.toFixed(2)}
                      </p>
                    </div>
                  </div>
                </div>
              ))}
              {symbolPerformance.length === 0 && (
                <p className="text-center text-muted-foreground py-8">No trades in this period</p>
              )}
            </div>
          </Card>
        </TabsContent>

        <TabsContent value="trades" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {metrics.bestTrade && (
              <Card className="p-6">
                <div className="flex items-center gap-2 mb-4">
                  <Award className="h-5 w-5 text-success" />
                  <h3 className="text-lg font-semibold">Best Trade</h3>
                </div>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-sm text-muted-foreground">Symbol</span>
                    <span className="font-semibold">{metrics.bestTrade.symbol}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-muted-foreground">Side</span>
                    <Badge variant={metrics.bestTrade.side === 'LONG' ? 'default' : 'destructive'}>
                      {metrics.bestTrade.side}
                    </Badge>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-muted-foreground">Entry</span>
                    <span className="font-medium">${parseFloat(metrics.bestTrade.entry_price).toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-muted-foreground">Exit</span>
                    <span className="font-medium">${parseFloat(metrics.bestTrade.current_price).toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between pt-2 border-t">
                    <span className="text-sm font-medium">P&L</span>
                    <span className="text-lg font-bold text-success">
                      +${parseFloat(metrics.bestTrade.realized_pnl).toFixed(2)}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-muted-foreground">Close Reason</span>
                    <span className="text-sm">{metrics.bestTrade.close_reason}</span>
                  </div>
                </div>
              </Card>
            )}

            {metrics.worstTrade && (
              <Card className="p-6">
                <div className="flex items-center gap-2 mb-4">
                  <AlertTriangle className="h-5 w-5 text-destructive" />
                  <h3 className="text-lg font-semibold">Worst Trade</h3>
                </div>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-sm text-muted-foreground">Symbol</span>
                    <span className="font-semibold">{metrics.worstTrade.symbol}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-muted-foreground">Side</span>
                    <Badge variant={metrics.worstTrade.side === 'LONG' ? 'default' : 'destructive'}>
                      {metrics.worstTrade.side}
                    </Badge>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-muted-foreground">Entry</span>
                    <span className="font-medium">${parseFloat(metrics.worstTrade.entry_price).toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-muted-foreground">Exit</span>
                    <span className="font-medium">${parseFloat(metrics.worstTrade.current_price).toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between pt-2 border-t">
                    <span className="text-sm font-medium">P&L</span>
                    <span className="text-lg font-bold text-destructive">
                      ${parseFloat(metrics.worstTrade.realized_pnl).toFixed(2)}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-muted-foreground">Close Reason</span>
                    <span className="text-sm">{metrics.worstTrade.close_reason}</span>
                  </div>
                </div>
              </Card>
            )}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
};
