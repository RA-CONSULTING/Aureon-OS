/**
 * Production analytics view. Every displayed value is either a stored provider
 * observation or a transparent calculation over stored trade receipts.
 */

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { TrendingUp, TrendingDown, BarChart3, Percent, DollarSign, Activity } from 'lucide-react';
import type { GlobalState } from '@/core/globalSystemsManager';

interface AnalyticsTabContentProps {
  globalState: GlobalState;
}

const finite = (value: unknown): value is number =>
  typeof value === 'number' && Number.isFinite(value);

const numberText = (value: number | null | undefined, decimals = 2): string =>
  finite(value) ? value.toFixed(decimals) : 'Unavailable';

const moneyText = (value: number | null | undefined, currency = '$', signed = false): string =>
  finite(value) ? `${signed && value >= 0 ? '+' : ''}${currency}${value.toFixed(2)}` : 'Unavailable';

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

  const hasCounts = finite(totalTrades) && totalTrades >= 0 && finite(winningTrades) &&
    winningTrades >= 0 && winningTrades <= totalTrades;
  const winRate = hasCounts && totalTrades > 0 ? (winningTrades / totalTrades) * 100 : null;
  const losingTrades = hasCounts ? totalTrades - winningTrades : null;

  const receiptPnls = recentTrades.map((trade) => trade.pnl).filter(finite);
  const wins = receiptPnls.filter((pnl) => pnl > 0);
  const losses = receiptPnls.filter((pnl) => pnl < 0);
  const avgWin = wins.length > 0 ? wins.reduce((sum, pnl) => sum + pnl, 0) / wins.length : null;
  const avgLoss = losses.length > 0 ? losses.reduce((sum, pnl) => sum + pnl, 0) / losses.length : null;
  const grossProfit = wins.length > 0 ? wins.reduce((sum, pnl) => sum + pnl, 0) : null;
  const grossLoss = losses.length > 0 ? Math.abs(losses.reduce((sum, pnl) => sum + pnl, 0)) : null;
  const profitFactor = finite(grossProfit) && finite(grossLoss) && grossLoss > 0 ? grossProfit / grossLoss : null;
  const riskReward = finite(avgWin) && finite(avgLoss) && avgLoss !== 0 ? Math.abs(avgWin / avgLoss) : null;
  const expectancy = finite(winRate) && finite(avgWin) && finite(avgLoss)
    ? (winRate / 100) * avgWin + ((100 - winRate) / 100) * avgLoss
    : null;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <MetricCard
          icon={DollarSign}
          label="Total P&L"
          value={moneyText(totalPnl, '$', true)}
          tone={finite(totalPnl) ? (totalPnl >= 0 ? 'positive' : 'negative') : 'neutral'}
        />
        <MetricCard
          icon={Percent}
          label="Win Rate"
          value={finite(winRate) ? `${winRate.toFixed(1)}%` : 'Unavailable'}
        />
        <MetricCard icon={BarChart3} label="Total Trades" value={finite(totalTrades) ? String(totalTrades) : 'Unavailable'} />
        <MetricCard
          icon={Activity}
          label="Recent-receipt expectancy"
          value={moneyText(expectancy)}
          tone={finite(expectancy) ? (expectancy >= 0 ? 'positive' : 'negative') : 'neutral'}
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card className="border-border/50">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Receipt-derived statistics</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-xs">
            <Row label="Winning trades" value={finite(winningTrades) ? String(winningTrades) : 'Unavailable'} />
            <Row label="Losing trades" value={finite(losingTrades) ? String(losingTrades) : 'Unavailable'} />
            <Row label="Recent average win" value={moneyText(avgWin)} />
            <Row label="Recent average loss" value={moneyText(avgLoss)} />
            <Row label="Recent risk/reward" value={finite(riskReward) ? `${riskReward.toFixed(2)}:1` : 'Unavailable'} />
            <Row label="Recent profit factor" value={numberText(profitFactor)} />
          </CardContent>
        </Card>

        <Card className="border-border/50">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Observed account state</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-xs">
            <Row label="Total equity" value={moneyText(totalEquity)} />
            <Row label="Gas tank" value={moneyText(gasTankBalance, '£')} />
            <Row label="Current coherence" value={numberText(coherence, 3)} />
            <div className="flex justify-between items-center">
              <span className="text-muted-foreground">Trade readiness</span>
              <Badge variant={finite(coherence) && coherence >= 0.7 ? 'default' : 'secondary'} className="text-[9px]">
                {!finite(coherence) ? 'NO DATA' : coherence >= 0.7 ? 'READY' : 'WAITING'}
              </Badge>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card className="border-border/50">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">Recent provider receipts</CardTitle>
        </CardHeader>
        <CardContent>
          {recentTrades.length === 0 ? (
            <p className="text-xs text-muted-foreground text-center py-8">No verified trade receipts are available.</p>
          ) : (
            <div className="space-y-2">
              {recentTrades.slice(0, 10).map((trade, index) => (
                <div key={trade.tradeId ?? `${trade.time}-${index}`} className="flex items-center justify-between p-3 rounded border border-border/30 text-xs">
                  <div className="flex items-center gap-3">
                    {finite(trade.pnl) && trade.pnl >= 0
                      ? <TrendingUp className="h-4 w-4 text-success" />
                      : <TrendingDown className="h-4 w-4 text-destructive" />}
                    <Badge variant={trade.side === 'BUY' ? 'default' : 'secondary'}>{trade.side}</Badge>
                    <span className="font-mono">{trade.symbol}</span>
                  </div>
                  <div className="flex items-center gap-4">
                    <span className="text-muted-foreground">Qty: {finite(trade.quantity) ? trade.quantity : 'Unavailable'}</span>
                    <span className={cn('font-mono font-bold', finite(trade.pnl) && (trade.pnl >= 0 ? 'text-success' : 'text-destructive'))}>
                      {moneyText(trade.pnl, '$', true)}
                    </span>
                    <Badge variant={trade.success ? 'default' : 'destructive'} className="text-[9px]">
                      {trade.success ? 'CONFIRMED' : 'FAILED'}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-mono">{value}</span>
    </div>
  );
}

function MetricCard({
  icon: Icon,
  label,
  value,
  tone = 'neutral',
}: {
  icon: typeof Activity;
  label: string;
  value: string;
  tone?: 'positive' | 'negative' | 'neutral';
}) {
  return (
    <Card className="border-border/50">
      <CardContent className="p-4">
        <div className="flex items-center gap-2 mb-2">
          <Icon className="h-4 w-4 text-muted-foreground" />
          <span className="text-xs text-muted-foreground">{label}</span>
        </div>
        <div className={cn('text-2xl font-mono font-bold', tone === 'positive' && 'text-success', tone === 'negative' && 'text-destructive')}>
          {value}
        </div>
      </CardContent>
    </Card>
  );
}
