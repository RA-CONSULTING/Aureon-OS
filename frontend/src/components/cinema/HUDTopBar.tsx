/**
 * HUDTopBar - Top-of-screen metrics bar
 * Equity, P&L, win rate, coherence, system status
 */

import { useState, useEffect, useRef } from 'react';

interface HUDTopBarProps {
  totalEquity: number;
  totalPnl: number;
  cyclePnlPercent: number;
  winRate: number;
  coherence: number;
  totalTrades: number;
  isActive: boolean;
  krakenConnected: boolean;
  capitalConnected: boolean;
  binanceConnected: boolean;
}

// Animated number counter
function AnimatedNumber({ value, prefix = '', suffix = '', decimals = 2, colorBySign = false }: {
  value: number;
  prefix?: string;
  suffix?: string;
  decimals?: number;
  colorBySign?: boolean;
}) {
  const displayRef = useRef(value);
  const [display, setDisplay] = useState(value);

  useEffect(() => {
    const interval = setInterval(() => {
      displayRef.current += (value - displayRef.current) * 0.1;
      if (Math.abs(value - displayRef.current) < 0.01) {
        displayRef.current = value;
        clearInterval(interval);
      }
      setDisplay(displayRef.current);
    }, 30);
    return () => clearInterval(interval);
  }, [value]);

  const colorClass = colorBySign
    ? display >= 0 ? 'text-success' : 'text-destructive'
    : 'text-white';

  return (
    <span className={colorClass}>
      {prefix}{display.toLocaleString(undefined, {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals,
      })}{suffix}
    </span>
  );
}

function StatusDot({ connected, label }: { connected: boolean; label: string }) {
  return (
    <div className="flex items-center gap-1.5">
      <div className={`w-1.5 h-1.5 rounded-full ${
        connected
          ? 'bg-success shadow-[0_0_6px_rgba(52,211,153,0.8)]'
          : 'bg-destructive shadow-[0_0_6px_rgba(248,113,113,0.6)]'
      }`} />
      <span className="text-[10px] text-white/40 uppercase tracking-wider">{label}</span>
    </div>
  );
}

export function HUDTopBar({
  totalEquity = 0,
  totalPnl = 0,
  cyclePnlPercent = 0,
  winRate = 0,
  coherence = 0,
  totalTrades = 0,
  isActive = false,
  krakenConnected = false,
  capitalConnected = false,
  binanceConnected = false,
}: HUDTopBarProps) {
  return (
    <div className="absolute top-0 left-0 right-0 z-10 flex justify-center pointer-events-none">
      <div className="mt-4 px-6 py-3 rounded-2xl backdrop-blur-xl bg-black/30 border border-white/[0.08] shadow-[0_8px_32px_rgba(0,0,0,0.4)]">
        <div className="flex items-center gap-8">
          {/* Equity */}
          <div className="text-center">
            <div className="text-[10px] text-white/30 uppercase tracking-widest mb-0.5">Equity</div>
            <div className="text-lg font-light tracking-wide">
              <AnimatedNumber value={totalEquity} prefix="$" />
            </div>
          </div>

          {/* Divider */}
          <div className="w-px h-8 bg-white/10" />

          {/* P&L */}
          <div className="text-center">
            <div className="text-[10px] text-white/30 uppercase tracking-widest mb-0.5">Session P&L</div>
            <div className="text-lg font-light tracking-wide">
              <AnimatedNumber value={totalPnl} prefix="$" colorBySign />
              <span className="text-xs text-white/30 ml-1.5">
                <AnimatedNumber value={cyclePnlPercent} suffix="%" colorBySign />
              </span>
            </div>
          </div>

          <div className="w-px h-8 bg-white/10" />

          {/* Win Rate */}
          <div className="text-center">
            <div className="text-[10px] text-white/30 uppercase tracking-widest mb-0.5">Win Rate</div>
            <div className="text-lg font-light tracking-wide text-white">
              <AnimatedNumber value={winRate} suffix="%" decimals={1} />
              <span className="text-xs text-white/30 ml-1.5">
                {totalTrades} trades
              </span>
            </div>
          </div>

          <div className="w-px h-8 bg-white/10" />

          {/* Coherence Bar */}
          <div className="text-center min-w-[80px]">
            <div className="text-[10px] text-white/30 uppercase tracking-widest mb-1">Coherence</div>
            <div className="relative h-1.5 bg-white/5 rounded-full overflow-hidden">
              <div
                className="absolute inset-y-0 left-0 rounded-full transition-all duration-1000"
                style={{
                  width: `${coherence * 100}%`,
                  background: coherence > 0.7
                    ? 'linear-gradient(90deg, #00ff88, #00ffcc)'
                    : coherence > 0.4
                    ? 'linear-gradient(90deg, #4488ff, #44ccff)'
                    : 'linear-gradient(90deg, #8844ff, #cc44ff)',
                  boxShadow: `0 0 8px ${coherence > 0.7 ? '#00ff88' : coherence > 0.4 ? '#4488ff' : '#8844ff'}`,
                }}
              />
            </div>
            <div className="text-[10px] text-white/40 mt-0.5">
              {(coherence * 100).toFixed(0)}%
            </div>
          </div>

          <div className="w-px h-8 bg-white/10" />

          {/* Exchange Status */}
          <div className="text-center">
            <div className="text-[10px] text-white/30 uppercase tracking-widest mb-1">Exchanges</div>
            <div className="flex items-center gap-3">
              <StatusDot connected={krakenConnected} label="KRK" />
              <StatusDot connected={capitalConnected} label="CAP" />
              <StatusDot connected={binanceConnected} label="BIN" />
            </div>
          </div>

          {/* System Active */}
          <div className="flex items-center gap-1.5 ml-2">
            <div className={`w-2 h-2 rounded-full ${
              isActive
                ? 'bg-success animate-pulse shadow-[0_0_8px_rgba(52,211,153,0.8)]'
                : 'bg-white/20'
            }`} />
            <span className="text-[10px] text-white/40 uppercase tracking-wider">
              {isActive ? 'LIVE' : 'IDLE'}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
