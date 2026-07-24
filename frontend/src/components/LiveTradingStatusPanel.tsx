/**
 * Live Trading Status Panel
 * Shows real-time trading capability, probability matrix state, and temporal echoes
 */

import React, { useEffect, useState } from 'react';
import { Activity, Zap, Brain, Timer, TrendingUp, AlertTriangle, CheckCircle, Radio } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { unifiedBus } from '@/core/unifiedBus';
import { elephantMemory } from '@/core/elephantMemory';
import { probabilityMatrix } from '@/core/enhanced6DProbabilityMatrix';
import { useEcosystemData } from '@/hooks/useEcosystemData';

interface TemporalEcho {
  timestamp: number;
  coherence: number;
  probability: number;
  action: string;
  confidence: number;
}

export const LiveTradingStatusPanel: React.FC = () => {
  const { metrics, busSnapshot, isInitialized } = useEcosystemData();
  const [temporalEchoes, setTemporalEchoes] = useState<TemporalEcho[]>([]);
  const [lastUpdate, setLastUpdate] = useState<number>(Date.now());
  const [isStreaming, setIsStreaming] = useState(false);
  const [tradingReady, setTradingReady] = useState(false);

  useEffect(() => {
    const interval = setInterval(() => {
      // Check if data is streaming (bus has states with recent timestamps)
      const now = Date.now();
      const snapshot = unifiedBus.snapshot();
      const hasRecentData = Object.values(snapshot.states).some(s => now - s.timestamp < 10000);
      setIsStreaming(hasRecentData || isInitialized);

      // Get latest probability fusion
      const fusion = probabilityMatrix.getLastFusion();
      
      // Check trading readiness
      const allSystemsReady = snapshot.systemsReady >= 3; // At least 3 systems
      setTradingReady(allSystemsReady && isStreaming);

      // Record temporal echo
      if (fusion) {
        const echo: TemporalEcho = {
          timestamp: now,
          coherence: metrics.coherence,
          probability: fusion.fusedProbability,
          action: fusion.action,
          confidence: fusion.confidence,
        };

        setTemporalEchoes(prev => {
          const updated = [...prev, echo].slice(-50); // Keep last 50 echoes
          return updated;
        });
      }

      setLastUpdate(now);
    }, 1000);

    return () => clearInterval(interval);
  }, [metrics, isInitialized]);

  // Get elephant memory state
  const elephantState = elephantMemory.getState();
  const fusion = probabilityMatrix.getLastFusion();

  // Calculate temporal drift (variance in probability over time)
  const recentEchoes = temporalEchoes.slice(-10);
  const probVariance = recentEchoes.length > 1
    ? recentEchoes.reduce((sum, e, i, arr) => {
        if (i === 0) return 0;
        return sum + Math.abs(e.probability - arr[i - 1].probability);
      }, 0) / recentEchoes.length
    : 0;

  const temporalStability = Math.max(0, 1 - probVariance * 5);

  return (
    <Card className="bg-background/50 border-primary/20">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm flex items-center gap-2">
          <Radio className={`h-4 w-4 ${isStreaming ? 'text-success animate-pulse' : 'text-destructive'}`} />
          Live Trading Status
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Trading Capability */}
        <div className="grid grid-cols-2 gap-2 text-xs">
          <div className="flex items-center gap-2">
            {tradingReady ? (
              <CheckCircle className="h-4 w-4 text-success" />
            ) : (
              <AlertTriangle className="h-4 w-4 text-warning" />
            )}
            <span className="text-muted-foreground">Trade Ready:</span>
            <Badge variant={tradingReady ? "default" : "secondary"} className="text-xs">
              {tradingReady ? 'YES' : 'NO'}
            </Badge>
          </div>
          <div className="flex items-center gap-2">
            <Activity className={`h-4 w-4 ${isStreaming ? 'text-success' : 'text-destructive'}`} />
            <span className="text-muted-foreground">Data Stream:</span>
            <Badge variant={isStreaming ? "default" : "destructive"} className="text-xs">
              {isStreaming ? 'LIVE' : 'STALE'}
            </Badge>
          </div>
        </div>

        {/* Probability Matrix Status */}
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Brain className="h-4 w-4 text-primary" />
            Probability Matrix
          </div>
          {fusion ? (
            <div className="grid grid-cols-3 gap-2 text-xs">
              <div className="bg-background/50 p-2 rounded border border-primary/10">
                <div className="text-muted-foreground">6D Prob</div>
                <div className="text-lg font-mono text-primary">
                  {(fusion.probability6D * 100).toFixed(1)}%
                </div>
              </div>
              <div className="bg-background/50 p-2 rounded border border-primary/10">
                <div className="text-muted-foreground">HNC Prob</div>
                <div className="text-lg font-mono text-primary">
                  {(fusion.probabilityHNC * 100).toFixed(1)}%
                </div>
              </div>
              <div className="bg-background/50 p-2 rounded border border-primary/10">
                <div className="text-muted-foreground">Fused</div>
                <div className="text-lg font-mono text-success">
                  {(fusion.fusedProbability * 100).toFixed(1)}%
                </div>
              </div>
            </div>
          ) : (
            <div className="text-xs text-muted-foreground">Waiting for data...</div>
          )}
        </div>

        {/* Current Action */}
        {fusion && (
          <div className="flex items-center justify-between bg-background/50 p-2 rounded border border-primary/10">
            <div className="flex items-center gap-2">
              <Zap className="h-4 w-4 text-warning" />
              <span className="text-xs text-muted-foreground">Action:</span>
            </div>
            <Badge 
              variant={fusion.action.includes('BUY') ? 'default' : fusion.action.includes('SELL') ? 'destructive' : 'secondary'}
              className="text-xs"
            >
              {fusion.action}
            </Badge>
            <div className="flex items-center gap-1">
              <span className="text-xs text-muted-foreground">Conf:</span>
              <span className="text-xs font-mono">{(fusion.confidence * 100).toFixed(0)}%</span>
            </div>
          </div>
        )}

        {/* Temporal Echo Status */}
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Timer className="h-4 w-4 text-primary" />
            Temporal Memory
          </div>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="bg-background/50 p-2 rounded border border-primary/10">
              <div className="text-muted-foreground">Echoes Recorded</div>
              <div className="text-lg font-mono">{temporalEchoes.length}</div>
            </div>
            <div className="bg-background/50 p-2 rounded border border-primary/10">
              <div className="text-muted-foreground">Temporal Stability</div>
              <div className={`text-lg font-mono ${temporalStability > 0.7 ? 'text-success' : temporalStability > 0.4 ? 'text-warning' : 'text-destructive'}`}>
                {(temporalStability * 100).toFixed(0)}%
              </div>
            </div>
          </div>
        </div>

        {/* Elephant Memory */}
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <TrendingUp className="h-4 w-4 text-primary" />
            Elephant Memory (Never Forgets)
          </div>
          <div className="grid grid-cols-3 gap-2 text-xs">
            <div className="bg-background/50 p-2 rounded border border-primary/10">
              <div className="text-muted-foreground">Total Trades</div>
              <div className="text-lg font-mono">{elephantState.totalTrades}</div>
            </div>
            <div className="bg-background/50 p-2 rounded border border-primary/10">
              <div className="text-muted-foreground">Win Rate</div>
              <div className={`text-lg font-mono ${elephantState.overallWinRate > 0.5 ? 'text-success' : 'text-destructive'}`}>
                {(elephantState.overallWinRate * 100).toFixed(0)}%
              </div>
            </div>
            <div className="bg-background/50 p-2 rounded border border-primary/10">
              <div className="text-muted-foreground">Blacklisted</div>
              <div className="text-lg font-mono text-destructive">{elephantState.blacklistedSymbols.length}</div>
            </div>
          </div>
        </div>

        {/* Recent Temporal Echoes */}
        <div className="space-y-1">
          <div className="text-xs text-muted-foreground">Recent Probability Echoes:</div>
          <div className="flex gap-1 overflow-hidden">
            {recentEchoes.slice(-20).map((echo, i) => (
              <div
                key={i}
                className="w-2 rounded-sm"
                style={{
                  height: `${Math.max(8, echo.probability * 32)}px`,
                  backgroundColor: echo.action.includes('BUY') 
                    ? 'hsl(var(--chart-1))' 
                    : echo.action.includes('SELL') 
                      ? 'hsl(var(--destructive))' 
                      : 'hsl(var(--muted))',
                  opacity: 0.5 + (i / 20) * 0.5,
                }}
              />
            ))}
          </div>
        </div>

        {/* Last Update */}
        <div className="text-xs text-muted-foreground text-right">
          Last update: {new Date(lastUpdate).toLocaleTimeString()}
        </div>
      </CardContent>
    </Card>
  );
};
