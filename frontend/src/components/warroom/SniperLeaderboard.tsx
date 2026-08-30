/**
 *  SNIPER LEADERBOARD 
 * ==========================
 * 
 * Rankings of symbols by penny-profit kills.
 * Each exchange column shows the assigned Duck Commando.
 * 
 * "We track every kill. Every penny. Every victory."
 * - Quantum Quackers, Commander
 */

import React, { useState, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  getDuckForExchange,
  DUCK_COMMANDOS_LIST,
  QUANTUM_QUACKERS,
} from '../../core/duckCommandos';

interface SymbolStats {
  symbol: string;
  totalKills: number;
  totalPnl: number;
  avgPnl: number;
  quickKillRate: number; // % of kills < 10 bars
  avgBarsToProfit: number;
  winRate: number;
  byExchange: {
    [exchange: string]: {
      kills: number;
      pnl: number;
    };
  };
}

interface SniperLeaderboardProps {
  symbolStats: SymbolStats[];
  sortBy?: 'kills' | 'pnl' | 'quickKillRate' | 'avgBars';
  maxDisplay?: number;
}

type SortField = 'kills' | 'pnl' | 'quickKillRate' | 'avgBars';

export function SniperLeaderboard({
  symbolStats,
  sortBy = 'kills',
  maxDisplay = 20,
}: SniperLeaderboardProps) {
  const [currentSort, setCurrentSort] = useState<SortField>(sortBy);
  const [hoveredExchange, setHoveredExchange] = useState<string | null>(null);

  const exchanges = ['kraken', 'binance', 'alpaca', 'capital'];

  const sortedStats = useMemo(() => {
    const sorted = [...symbolStats].sort((a, b) => {
      switch (currentSort) {
        case 'kills':
          return b.totalKills - a.totalKills;
        case 'pnl':
          return b.totalPnl - a.totalPnl;
        case 'quickKillRate':
          return b.quickKillRate - a.quickKillRate;
        case 'avgBars':
          return a.avgBarsToProfit - b.avgBarsToProfit; // Lower is better
        default:
          return 0;
      }
    });
    return sorted.slice(0, maxDisplay);
  }, [symbolStats, currentSort, maxDisplay]);

  const totals = useMemo(() => {
    return symbolStats.reduce(
      (acc, stat) => ({
        kills: acc.kills + stat.totalKills,
        pnl: acc.pnl + stat.totalPnl,
        avgQuickKill: acc.avgQuickKill + stat.quickKillRate / symbolStats.length,
      }),
      { kills: 0, pnl: 0, avgQuickKill: 0 }
    );
  }, [symbolStats]);

  return (
    <Card className="bg-gradient-to-br from-slate-900 to-slate-800 border-primary/20 overflow-hidden">
      {/* Header */}
      <CardHeader className="bg-gradient-to-r from-success/30 via-slate-800 to-warning/30 border-b border-slate-700 pb-3">
        <CardTitle className="flex items-center justify-center gap-3 text-lg">
          <span className="font-extrabold tracking-wider text-foreground">Signal Leaderboard</span>
        </CardTitle>
        <p className="text-center text-xs text-gray-400 italic mt-1">
          "{QUANTUM_QUACKERS.signature}"
        </p>
      </CardHeader>

      <CardContent className="p-4">
        {/* Duck Commandos Banner */}
        <div className="flex justify-around mb-4 gap-2">
          {exchanges.map((exchange) => {
            const duck = getDuckForExchange(exchange);
            if (!duck) return null;
            return (
              <div
                key={exchange}
                className={`flex flex-col items-center p-2 rounded-lg bg-slate-800/50 border-2 transition-all cursor-pointer hover:scale-105 ${
                  hoveredExchange === exchange ? 'border-opacity-100' : 'border-opacity-30'
                }`}
                style={{ borderColor: duck.provinceColor }}
                onMouseEnter={() => setHoveredExchange(exchange)}
                onMouseLeave={() => setHoveredExchange(null)}
              >
                <span className="text-2xl">{duck.avatar}</span>
                <span className="text-xs font-semibold text-white">{duck.codename}</span>
                <span className="text-xs">{duck.exchangeEmoji}</span>
                <span className="text-xs">{duck.provinceEmoji}</span>
              </div>
            );
          })}
        </div>

        {/* Summary Stats */}
        <div className="grid grid-cols-3 gap-4 mb-4">
          <div className="text-center p-3 bg-slate-800/50 rounded-lg">
            <span className="block text-2xl font-bold text-white">{totals.kills.toLocaleString()}</span>
            <span className="text-xs text-gray-400 uppercase">Total Kills</span>
          </div>
          <div className="text-center p-3 bg-slate-800/50 rounded-lg">
            <span className="block text-2xl font-bold text-success">+${totals.pnl.toFixed(2)}</span>
            <span className="text-xs text-gray-400 uppercase">Total PnL</span>
          </div>
          <div className="text-center p-3 bg-slate-800/50 rounded-lg">
            <span className="block text-2xl font-bold text-white">{(totals.avgQuickKill * 100).toFixed(1)}%</span>
            <span className="text-xs text-gray-400 uppercase">Quick Kill Rate</span>
          </div>
        </div>

        {/* Sort Controls */}
        <div className="flex items-center gap-2 mb-4 flex-wrap">
          <span className="text-xs text-gray-400">Sort by:</span>
          {[
            { key: 'kills', label: ' Kills' },
            { key: 'pnl', label: ' PnL' },
            { key: 'quickKillRate', label: ' Speed' },
            { key: 'avgBars', label: ' Bars' },
          ].map(({ key, label }) => (
            <Button
              key={key}
              size="sm"
              variant={currentSort === key ? 'default' : 'outline'}
              className={`text-xs h-7 ${currentSort === key ? 'bg-success' : ''}`}
              onClick={() => setCurrentSort(key as SortField)}
            >
              {label}
            </Button>
          ))}
        </div>

        {/* Leaderboard Table */}
        <ScrollArea className="h-[350px]">
          {symbolStats.length === 0 && (
            <div className="flex flex-col items-center justify-center h-[320px] text-center px-6">
              <span className="text-3xl mb-2 opacity-60"></span>
              <p className="text-sm text-gray-300 font-semibold">No sniper telemetry yet</p>
              <p className="text-xs text-gray-500 mt-1">
                Awaiting live trades — kill stats populate from real executions as they happen.
              </p>
            </div>
          )}
          <div className="space-y-1" hidden={symbolStats.length === 0}>
            {/* Table Header */}
            <div className="grid grid-cols-10 gap-1 text-xs text-gray-400 font-semibold uppercase p-2 bg-slate-800/50 rounded sticky top-0">
              <div className="text-center">#</div>
              <div className="col-span-2">Symbol</div>
              <div className="text-center">Kills</div>
              <div className="text-center">PnL</div>
              <div className="text-center">Quick%</div>
              <div className="text-center">Bars</div>
              {exchanges.slice(0, 3).map((ex) => {
                const duck = getDuckForExchange(ex);
                return (
                  <div key={ex} className="text-center" title={duck?.realName || ex}>
                    {duck?.avatar || ''}
                  </div>
                );
              })}
            </div>

            {/* Table Rows */}
            {sortedStats.map((stat, index) => (
              <div
                key={stat.symbol}
                className={`grid grid-cols-10 gap-1 text-xs p-2 rounded transition-colors hover:bg-slate-700/50 ${
                  index === 0 ? 'bg-warning/10' : 
                  index === 1 ? 'bg-gray-400/10' : 
                  index === 2 ? 'bg-warning/10' : ''
                }`}
              >
                <div className="text-center font-bold">
                  {index === 0 && ''}
                  {index === 1 && ''}
                  {index === 2 && ''}
                  {index >= 3 && index + 1}
                </div>
                <div className="col-span-2 font-bold text-white">{stat.symbol}</div>
                <div className="text-center text-white">{stat.totalKills}</div>
                <div className={`text-center ${stat.totalPnl >= 0 ? 'text-success' : 'text-destructive'}`}>
                  {stat.totalPnl >= 0 ? '+' : ''}${stat.totalPnl.toFixed(2)}
                </div>
                <div className="text-center">
                  <span className={stat.quickKillRate >= 0.9 ? 'text-warning font-bold' : 'text-gray-300'}>
                    {(stat.quickKillRate * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="text-center">
                  <span className={stat.avgBarsToProfit <= 2 ? 'text-success font-bold' : 'text-gray-300'}>
                    {stat.avgBarsToProfit.toFixed(1)}
                  </span>
                </div>
                {exchanges.slice(0, 3).map((ex) => {
                  const duck = getDuckForExchange(ex);
                  const exStats = stat.byExchange[ex];
                  return (
                    <div
                      key={ex}
                      className="text-center rounded"
                      style={{
                        backgroundColor: exStats?.kills > 0 
                          ? `${duck?.provinceColor}20` 
                          : 'transparent',
                      }}
                    >
                      {exStats?.kills > 0 ? exStats.kills : '-'}
                    </div>
                  );
                })}
              </div>
            ))}
          </div>
        </ScrollArea>

        {/* Commander Quote Footer */}
        <div className="flex items-center justify-center gap-3 mt-4 pt-3 border-t border-slate-700">
          <span className="text-2xl">{QUANTUM_QUACKERS.avatar}</span>
          <span className="text-xs text-gray-400 italic">
            "{QUANTUM_QUACKERS.signature}" - {QUANTUM_QUACKERS.name}, Commander
          </span>
        </div>
      </CardContent>
    </Card>
  );
}

export default SniperLeaderboard;
