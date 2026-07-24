import { useState } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { useQueenHive } from '@/hooks/useQueenHive';
import { Play, Square, SkipForward, Activity, TrendingUp, Users } from 'lucide-react';

export function QueenHiveControl() {
  const { session, hives, agents, isRunning, isStarting, roi, startHive, stopHive, manualStep } = useQueenHive();
  const [initialCapital, setInitialCapital] = useState('100');

  const handleStart = async () => {
    const capital = parseFloat(initialCapital);
    if (isNaN(capital) || capital < 10) {
      alert('Minimum capital: $10');
      return;
    }
    await startHive(capital);
  };

  const handleStop = () => {
    if (session) {
      stopHive(session.id);
    }
  };

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
    }).format(value);
  };

  return (
    <div className="space-y-6">
      {/* Control Panel */}
      <Card className="p-6">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <Activity className="w-6 h-6 text-primary" />
            <h2 className="text-2xl font-bold">Queen-Hive Control</h2>
          </div>
          <Badge variant={isRunning ? "default" : "secondary"} className="text-sm">
            {isRunning ? '🐝 ACTIVE' : '⏸️ IDLE'}
          </Badge>
        </div>

        {!session ? (
          // Start Configuration
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium mb-2 block">Initial Capital (USD)</label>
              <Input
                type="number"
                value={initialCapital}
                onChange={(e) => setInitialCapital(e.target.value)}
                placeholder="100"
                min="10"
                className="max-w-xs"
              />
              <p className="text-xs text-muted-foreground mt-1">Minimum: $10</p>
            </div>

            <Button 
              onClick={handleStart} 
              disabled={isStarting}
              className="w-full sm:w-auto"
            >
              <Play className="w-4 h-4 mr-2" />
              {isStarting ? 'Deploying Hive...' : 'Deploy Queen-Hive'}
            </Button>

            <div className="border-t pt-4 mt-4">
              <h3 className="font-semibold mb-2">System Overview</h3>
              <ul className="text-sm space-y-1 text-muted-foreground">
                <li>• Multi-agent trading system with autonomous hives</li>
                <li>• 5 agents per hive trading BTC, ETH, BNB, ADA, DOGE</li>
                <li>• Auto-spawns new hives at 5x growth</li>
                <li>• Real-time P&L tracking and position management</li>
              </ul>
            </div>
          </div>
        ) : (
          // Active Session
          <div className="space-y-6">
            {/* Session Stats */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="bg-muted/50 rounded-lg p-4">
                <div className="text-xs text-muted-foreground mb-1">Initial Capital</div>
                <div className="text-xl font-bold">{formatCurrency(session.initial_capital)}</div>
              </div>

              <div className="bg-muted/50 rounded-lg p-4">
                <div className="text-xs text-muted-foreground mb-1">Current Equity</div>
                <div className="text-xl font-bold text-primary">{formatCurrency(session.current_equity)}</div>
              </div>

              <div className="bg-muted/50 rounded-lg p-4">
                <div className="text-xs text-muted-foreground mb-1">ROI</div>
                <div className={`text-xl font-bold ${roi >= 0 ? 'text-success' : 'text-destructive'}`}>
                  {roi >= 0 ? '+' : ''}{roi.toFixed(2)}%
                </div>
              </div>

              <div className="bg-muted/50 rounded-lg p-4">
                <div className="text-xs text-muted-foreground mb-1">Steps Executed</div>
                <div className="text-xl font-bold">{session.steps_executed}</div>
              </div>
            </div>

            {/* Hive & Agent Stats */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="flex items-center gap-3 p-4 border rounded-lg">
                <div className="p-2 rounded-lg bg-warning/10">
                  <Activity className="w-5 h-5 text-warning" />
                </div>
                <div>
                  <div className="text-xs text-muted-foreground">Active Hives</div>
                  <div className="text-lg font-bold">{hives.length}</div>
                </div>
              </div>

              <div className="flex items-center gap-3 p-4 border rounded-lg">
                <div className="p-2 rounded-lg bg-primary/10">
                  <Users className="w-5 h-5 text-primary" />
                </div>
                <div>
                  <div className="text-xs text-muted-foreground">Trading Agents</div>
                  <div className="text-lg font-bold">{agents.length}</div>
                </div>
              </div>

              <div className="flex items-center gap-3 p-4 border rounded-lg">
                <div className="p-2 rounded-lg bg-success/10">
                  <TrendingUp className="w-5 h-5 text-success" />
                </div>
                <div>
                  <div className="text-xs text-muted-foreground">Total Trades</div>
                  <div className="text-lg font-bold">{session.total_trades}</div>
                </div>
              </div>
            </div>

            {/* Control Buttons */}
            <div className="flex gap-3">
              {isRunning ? (
                <Button variant="destructive" onClick={handleStop}>
                  <Square className="w-4 h-4 mr-2" />
                  Stop Trading
                </Button>
              ) : (
                <Button variant="outline" onClick={manualStep}>
                  <SkipForward className="w-4 h-4 mr-2" />
                  Execute Step
                </Button>
              )}
            </div>

            {/* Hive Breakdown */}
            {hives.length > 0 && (
              <div className="border-t pt-6">
                <h3 className="font-semibold mb-4">Hive Breakdown</h3>
                <div className="space-y-3">
                  {hives.map((hive) => {
                    const hiveAgents = agents.filter(a => a.hive_id === hive.id);
                    const growthPercent = ((hive.current_balance - hive.initial_balance) / hive.initial_balance) * 100;

                    return (
                      <div key={hive.id} className="p-4 border rounded-lg">
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center gap-2">
                            <Badge variant="outline">Gen {hive.generation}</Badge>
                            <span className="font-medium">
                              {formatCurrency(hive.current_balance)}
                            </span>
                          </div>
                          <span className={`text-sm font-medium ${growthPercent >= 0 ? 'text-success' : 'text-destructive'}`}>
                            {growthPercent >= 0 ? '+' : ''}{growthPercent.toFixed(1)}%
                          </span>
                        </div>
                        
                        <Progress 
                          value={Math.min(100, (hive.current_balance / hive.initial_balance) * 20)} 
                          className="h-2 mb-2"
                        />
                        
                        <div className="text-xs text-muted-foreground">
                          {hiveAgents.length} agents • {hiveAgents.reduce((sum, a) => sum + a.trades_count, 0)} trades
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

      {/* Documentation Card */}
      <Card className="p-6 bg-muted/30">
        <h3 className="font-semibold mb-3">🐝 Queen-Hive Architecture</h3>
        <div className="text-sm space-y-2 text-muted-foreground">
          <p>
            <strong>Multi-Agent System:</strong> Each hive contains 5 autonomous trading agents. Agents independently select symbols, execute trades, and track P&L.
          </p>
          <p>
            <strong>Hive Spawning:</strong> When a hive's balance reaches 5x its initial capital, it harvests 10% to create a new "child hive" with its own agents.
          </p>
          <p>
            <strong>Symbols:</strong> Agents trade across BTC, ETH, BNB, ADA, and DOGE with position sizing based on hive balance.
          </p>
          <p>
            <strong>Safety:</strong> Currently running in paper trading mode. No real funds at risk.
          </p>
        </div>
      </Card>
    </div>
  );
}
