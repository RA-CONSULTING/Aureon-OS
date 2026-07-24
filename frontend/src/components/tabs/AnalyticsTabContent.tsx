/**
 * Analytics Tab Content - Displays trading performance analytics
 * 
 * This component is a PURE VIEW that reads from global state.
 * All systems run continuously in GlobalSystemsManager regardless of which tab is active.
 */

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { cn } from '@/lib/utils';
import { TrendingUp, TrendingDown, BarChart3, Target, Percent, DollarSign, Activity } from 'lucide-react';
import type { GlobalState } from '@/core/globalSystemsManager';

interface AnalyticsTabContentProps {
  globalState: GlobalState;
}

export function AnalyticsTabContent({ globalState }: AnalyticsTabContentProps) {
  const {
    totalTrades,
    winningTrades,
    totalPnl,
    totalEquity,
    gasTankBalance,
    recentTrades,
    coherence,
  } = globalState;

  const winRate = totalTrades > 0 ? (winningTrades / totalTrades) * 100 : 0;
  const losingTrades = totalTrades - winningTrades;
  const profitFactor = totalPnl > 0 ? (totalPnl / (Math.abs(totalPnl) + 1)) : 0;
  
  // Calculate trade statistics
  const tradePnls = recentTrades.map(t => t.pnl);
  const avgWin = tradePnls.filter(p => p > 0).reduce((a, b) => a + b, 0) / (tradePnls.filter(p => p > 0).length || 1);
  const avgLoss = tradePnls.filter(p => p < 0).reduce((a, b) => a + b, 0) / (tradePnls.filter(p => p < 0).length || 1);
  const expectancy = (winRate / 100 * avgWin) + ((100 - winRate) / 100 * avgLoss);

  return (
    <div className="space-y-4">
      {/* Performance Overview */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="border-border/50">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 mb-2">
              <DollarSign className="h-4 w-4 text-muted-foreground" />
              <span className="text-xs text-muted-foreground">Total P&L</span>
            </div>
            <div className={cn(
              "text-2xl font-mono font-bold",
              totalPnl >= 0 ? "text-success" : "text-destructive"
            )}>
              {totalPnl >= 0 ? '+' : ''}${totalPnl.toFixed(2)}
            </div>
          </CardContent>
        </Card>

        <Card className="border-border/50">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 mb-2">
              <Percent className="h-4 w-4 text-muted-foreground" />
              <span className="text-xs text-muted-foreground">Win Rate</span>
            </div>
            <div className={cn(
              "text-2xl font-mono font-bold",
              winRate >= 51 ? "text-success" : "text-warning"
            )}>
              {winRate.toFixed(1)}%
            </div>
            <Progress 
              value={winRate} 
              className={cn(
                "h-1 mt-2",
                winRate >= 51 ? "[&>div]:bg-success" : "[&>div]:bg-warning"
              )}
            />
          </CardContent>
        </Card>

        <Card className="border-border/50">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 mb-2">
              <BarChart3 className="h-4 w-4 text-muted-foreground" />
              <span className="text-xs text-muted-foreground">Total Trades</span>
            </div>
            <div className="text-2xl font-mono font-bold">
              {totalTrades}
            </div>
            <div className="flex gap-2 mt-2 text-xs">
              <span className="text-success">W: {winningTrades}</span>
              <span className="text-destructive">L: {losingTrades}</span>
            </div>
          </CardContent>
        </Card>

        <Card className="border-border/50">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 mb-2">
              <Target className="h-4 w-4 text-muted-foreground" />
              <span className="text-xs text-muted-foreground">Expectancy</span>
            </div>
            <div className={cn(
              "text-2xl font-mono font-bold",
              expectancy >= 0 ? "text-success" : "text-destructive"
            )}>
              ${expectancy.toFixed(2)}
            </div>
            <span className="text-xs text-muted-foreground">per trade</span>
          </CardContent>
        </Card>
      </div>

      {/* Detailed Statistics */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Trade Analysis */}
        <Card className="border-border/50">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Activity className="h-4 w-4 text-primary" />
              Trade Analysis
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex justify-between text-xs">
              <span className="text-muted-foreground">Average Win</span>
              <span className="font-mono text-success">+${avgWin.toFixed(2)}</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-muted-foreground">Average Loss</span>
              <span className="font-mono text-destructive">${avgLoss.toFixed(2)}</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-muted-foreground">Risk/Reward</span>
              <span className="font-mono">{Math.abs(avgWin / (avgLoss || 1)).toFixed(2)}:1</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-muted-foreground">Profit Factor</span>
              <span className="font-mono">{profitFactor.toFixed(2)}</span>
            </div>
          </CardContent>
        </Card>

        {/* Account Status */}
        <Card className="border-border/50">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <DollarSign className="h-4 w-4 text-primary" />
              Account Status
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex justify-between text-xs">
              <span className="text-muted-foreground">Total Equity</span>
              <span className="font-mono font-bold">${totalEquity.toFixed(2)}</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-muted-foreground">Gas Tank</span>
              <span className="font-mono">£{gasTankBalance.toFixed(2)}</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-muted-foreground">Current Coherence</span>
              <span className={cn(
                "font-mono",
                coherence >= 0.7 ? "text-success" : "text-warning"
              )}>
                {coherence.toFixed(3)}
              </span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-muted-foreground">Trade Readiness</span>
              <Badge variant={coherence >= 0.7 ? "default" : "secondary"} className="text-[9px]">
                {coherence >= 0.7 ? "READY" : "WAITING"}
              </Badge>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Recent Trade History */}
      <Card className="border-border/50">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">Trade History</CardTitle>
        </CardHeader>
        <CardContent>
          {recentTrades.length === 0 ? (
            <p className="text-xs text-muted-foreground text-center py-8">
              No trades recorded yet. Start trading to see history here.
            </p>
          ) : (
            <div className="space-y-2">
              {recentTrades.slice(0, 10).map((trade, i) => (
                <div 
                  key={i}
                  className="flex items-center justify-between p-3 rounded border border-border/30 text-xs"
                >
                  <div className="flex items-center gap-3">
                    {trade.pnl >= 0 ? (
                      <TrendingUp className="h-4 w-4 text-success" />
                    ) : (
                      <TrendingDown className="h-4 w-4 text-destructive" />
                    )}
                    <Badge variant={trade.side === 'BUY' ? 'default' : 'secondary'}>
                      {trade.side}
                    </Badge>
                    <span className="font-mono">{trade.symbol}</span>
                  </div>
                  <div className="flex items-center gap-4">
                    <span className="text-muted-foreground">Qty: {trade.quantity}</span>
                    <span className={cn(
                      "font-mono font-bold",
                      trade.pnl >= 0 ? "text-success" : "text-destructive"
                    )}>
                      {trade.pnl >= 0 ? '+' : ''}${trade.pnl.toFixed(2)}
                    </span>
                    <Badge variant={trade.success ? "default" : "destructive"} className="text-[9px]">
                      {trade.success ? "SUCCESS" : "FAILED"}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Performance Targets */}
      <Card className="border-border/50">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">Performance vs Targets</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-muted-foreground">Win Rate (Target: 51%+)</span>
                <span className={cn("font-mono", winRate >= 51 ? "text-success" : "text-destructive")}>
                  {winRate.toFixed(1)}%
                </span>
              </div>
              <Progress 
                value={winRate} 
                className={cn("h-2", winRate >= 51 ? "[&>div]:bg-success" : "[&>div]:bg-destructive")}
              />
            </div>
            
            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-muted-foreground">Coherence (Target: 0.70+)</span>
                <span className={cn("font-mono", coherence >= 0.7 ? "text-success" : "text-warning")}>
                  {coherence.toFixed(3)}
                </span>
              </div>
              <Progress 
                value={coherence * 100} 
                className={cn("h-2", coherence >= 0.7 ? "[&>div]:bg-success" : "[&>div]:bg-warning")}
              />
            </div>
            
            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-muted-foreground">Net Profit</span>
                <span className={cn("font-mono", totalPnl >= 0 ? "text-success" : "text-destructive")}>
                  {totalPnl >= 0 ? '+' : ''}${totalPnl.toFixed(2)}
                </span>
              </div>
              <Progress 
                value={totalPnl >= 0 ? Math.min(totalPnl / 100, 100) : 0} 
                className={cn("h-2", totalPnl >= 0 ? "[&>div]:bg-success" : "[&>div]:bg-destructive")}
              />
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
