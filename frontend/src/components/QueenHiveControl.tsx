import { useState } from 'react';
import type { ReactNode } from 'react';
import { Activity, Play, SkipForward, Square, TrendingUp, Users } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Progress } from '@/components/ui/progress';
import { useQueenHive } from '@/hooks/useQueenHive';

function formatCurrency(value: number | null | undefined): string {
  if (!Number.isFinite(Number(value))) return 'Unavailable';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
  }).format(Number(value));
}

export function QueenHiveControl() {
  const { session, hives, agents, isRunning, isStarting, roi, startHive, stopHive, manualStep } = useQueenHive();
  const [initialCapital, setInitialCapital] = useState('');
  const [liveExecutionConfirmed, setLiveExecutionConfirmed] = useState(false);

  const handleStart = async () => {
    const capital = Number(initialCapital);
    if (!Number.isFinite(capital) || capital <= 0) {
      window.alert('Enter a positive USD allocation. It cannot exceed fresh provider-observed equity.');
      return;
    }
    if (!liveExecutionConfirmed) {
      window.alert('Confirm that this session can submit real exchange orders.');
      return;
    }
    const confirmed = window.confirm(
      `LIVE EXECUTION: manual steps may submit real Binance market orders using this ${formatCurrency(capital)} allocation. Continue?`,
    );
    if (confirmed) await startHive(capital, true);
  };

  const handleStop = () => {
    if (session) void stopHive(session.id);
  };

  return (
    <div className="space-y-6">
      <Card className="p-6">
        <div className="mb-6 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Activity className="h-6 w-6 text-primary" />
            <h2 className="text-2xl font-bold">Queen-Hive Live Control</h2>
          </div>
          <Badge variant={isRunning ? 'default' : 'secondary'}>
            {isRunning ? 'LIVE SESSION' : 'IDLE'}
          </Badge>
        </div>

        {!session ? (
          <div className="space-y-4">
            <div>
              <label className="mb-2 block text-sm font-medium">Live capital allocation (USD)</label>
              <Input
                type="number"
                value={initialCapital}
                onChange={(event) => setInitialCapital(event.target.value)}
                placeholder="Enter live allocation"
                min="0.01"
                step="0.01"
                className="max-w-xs"
              />
              <p className="mt-1 text-xs text-muted-foreground">
                Validated against a fresh provider-observed account balance before the session is created.
              </p>
            </div>

            <label className="flex items-start gap-3 rounded-md border border-destructive/50 p-3 text-sm">
              <input
                type="checkbox"
                checked={liveExecutionConfirmed}
                onChange={(event) => setLiveExecutionConfirmed(event.target.checked)}
                className="mt-1"
              />
              <span>
                I understand this is live execution. A manual step may submit real Binance market orders and place real funds at risk.
              </span>
            </label>

            <Button onClick={handleStart} disabled={isStarting || !liveExecutionConfirmed}>
              <Play className="mr-2 h-4 w-4" />
              {isStarting ? 'Connecting live hive…' : 'Connect live Queen-Hive'}
            </Button>

            <div className="border-t pt-4">
              <h3 className="mb-2 font-semibold">Production contract</h3>
              <ul className="space-y-1 text-sm text-muted-foreground">
                <li>Five agents route fresh native QGITA signals for BTC, ETH, BNB, ADA, and DOGE.</li>
                <li>Order sizing uses configured limits and current Binance symbol rules.</li>
                <li>Every step reports provider-confirmed fills, explicit skips, or an error/no-data state.</li>
                <li>No paper, demo, mock, random, or generated market values are substituted.</li>
              </ul>
            </div>
          </div>
        ) : (
          <div className="space-y-6">
            <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
              <Metric label="Allocated capital" value={formatCurrency(session.initial_capital)} />
              <Metric label="Provider-observed equity" value={formatCurrency(session.current_equity)} primary />
              <Metric
                label="Observed ROI"
                value={roi === null ? 'Unavailable' : `${roi >= 0 ? '+' : ''}${roi.toFixed(2)}%`}
                good={roi !== null && roi >= 0}
              />
              <Metric label="Manual steps" value={String(session.steps_executed)} />
            </div>

            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
              <Count icon={<Activity className="h-5 w-5 text-warning" />} label="Active hives" value={hives.length} />
              <Count icon={<Users className="h-5 w-5 text-primary" />} label="Signal agents" value={agents.length} />
              <Count icon={<TrendingUp className="h-5 w-5 text-success" />} label="Provider-confirmed trades" value={session.total_trades} />
            </div>

            <div className="flex flex-wrap gap-3">
              {isRunning && (
                <Button onClick={manualStep}>
                  <SkipForward className="mr-2 h-4 w-4" />
                  Execute live step
                </Button>
              )}
              {isRunning && (
                <Button variant="destructive" onClick={handleStop}>
                  <Square className="mr-2 h-4 w-4" />
                  Stop live session
                </Button>
              )}
            </div>

            {hives.length > 0 && (
              <div className="border-t pt-6">
                <h3 className="mb-4 font-semibold">Hive allocations</h3>
                <div className="space-y-3">
                  {hives.map((hive) => {
                    const hiveAgents = agents.filter((agent) => agent.hive_id === hive.id);
                    const validBalance = Number.isFinite(hive.current_balance) && Number.isFinite(hive.initial_balance) && hive.initial_balance > 0;
                    const growth = validBalance
                      ? ((hive.current_balance - hive.initial_balance) / hive.initial_balance) * 100
                      : null;
                    return (
                      <div key={hive.id} className="rounded-lg border p-4">
                        <div className="mb-2 flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <Badge variant="outline">Generation {hive.generation}</Badge>
                            <span className="font-medium">{formatCurrency(hive.current_balance)}</span>
                          </div>
                          <span className="text-sm font-medium">
                            {growth === null ? 'Unavailable' : `${growth >= 0 ? '+' : ''}${growth.toFixed(1)}%`}
                          </span>
                        </div>
                        <Progress value={growth === null ? 0 : Math.max(0, Math.min(100, growth + 50))} className="mb-2 h-2" />
                        <div className="text-xs text-muted-foreground">
                          {hiveAgents.length} agents · {hiveAgents.reduce((sum, agent) => sum + agent.trades_count, 0)} confirmed trades
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        )}
      </Card>

      <Card className="bg-muted/30 p-6">
        <h3 className="mb-3 font-semibold">Queen-Hive data provenance</h3>
        <div className="space-y-2 text-sm text-muted-foreground">
          <p>Signals come from fresh provenance-bearing QGITA rows; prices, exchange rules, rate limits, and fills come from live Binance endpoints.</p>
          <p>A threshold crossing is not called a trade. Only an exchange order receipt with a filled quantity and price increments the trade count.</p>
          <p>Missing or stale source data is shown as unavailable and blocks the affected route.</p>
        </div>
      </Card>
    </div>
  );
}

function Metric({ label, value, primary = false, good = false }: { label: string; value: string; primary?: boolean; good?: boolean }) {
  return (
    <div className="rounded-lg bg-muted/50 p-4">
      <div className="mb-1 text-xs text-muted-foreground">{label}</div>
      <div className={`text-xl font-bold ${primary ? 'text-primary' : good ? 'text-success' : ''}`}>{value}</div>
    </div>
  );
}

function Count({ icon, label, value }: { icon: ReactNode; label: string; value: number }) {
  return (
    <div className="flex items-center gap-3 rounded-lg border p-4">
      <div className="rounded-lg bg-muted p-2">{icon}</div>
      <div>
        <div className="text-xs text-muted-foreground">{label}</div>
        <div className="text-lg font-bold">{value}</div>
      </div>
    </div>
  );
}
