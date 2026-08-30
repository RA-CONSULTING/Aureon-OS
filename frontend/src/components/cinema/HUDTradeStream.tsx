/**
 * HUDTradeStream - Right-side sliding trade cards
 * Latest trades slide in from right with auto-dismiss
 */

import { useState, useEffect, useRef } from 'react';

interface TradeData {
  time: string;
  side: string;
  symbol: string;
  quantity: number;
  pnl: number;
  exchange?: string;
}

interface HUDTradeStreamProps {
  recentTrades: TradeData[];
}

interface DisplayTrade extends TradeData {
  id: string;
  opacity: number;
  offsetX: number;
  addedAt: number;
}

export function HUDTradeStream({ recentTrades = [] }: HUDTradeStreamProps) {
  const [displayTrades, setDisplayTrades] = useState<DisplayTrade[]>([]);
  const seenRef = useRef<Set<string>>(new Set());

  // Detect new trades and add with animation
  useEffect(() => {
    const newTrades: DisplayTrade[] = [];

    for (const trade of recentTrades.slice(0, 8)) {
      const id = `${trade.time}-${trade.symbol}-${trade.side}`;
      if (seenRef.current.has(id)) continue;
      seenRef.current.add(id);

      if (seenRef.current.size > 200) {
        const entries = Array.from(seenRef.current);
        seenRef.current = new Set(entries.slice(-100));
      }

      newTrades.push({
        ...trade,
        id,
        opacity: 0,
        offsetX: 100,
        addedAt: Date.now(),
      });
    }

    if (newTrades.length > 0) {
      setDisplayTrades(prev => [...newTrades, ...prev].slice(0, 6));
    }
  }, [recentTrades]);

  // Animation loop: slide in + auto-dismiss
  useEffect(() => {
    const interval = setInterval(() => {
      setDisplayTrades(prev => {
        const now = Date.now();
        return prev
          .map(trade => {
            const age = now - trade.addedAt;
            // Slide in over 300ms
            const offsetX = Math.max(0, 100 - age * 0.33);
            // Fade in over 300ms, then hold, then fade out after 10s
            let opacity: number;
            if (age < 300) {
              opacity = age / 300;
            } else if (age < 10000) {
              opacity = 1;
            } else {
              opacity = Math.max(0, 1 - (age - 10000) / 1000);
            }
            return { ...trade, offsetX, opacity };
          })
          .filter(trade => trade.opacity > 0.01);
      });
    }, 30);

    return () => clearInterval(interval);
  }, []);

  if (displayTrades.length === 0) return null;

  return (
    <div className="absolute top-24 right-4 z-10 w-56 pointer-events-none">
      <div className="space-y-2">
        {displayTrades.map(trade => {
          const isBuy = trade.side.toUpperCase().includes('BUY') || trade.side.toUpperCase().includes('LONG');
          const sideColor = isBuy ? '#00ff88' : '#ff4466';

          return (
            <div
              key={trade.id}
              className="px-3 py-2 rounded-lg backdrop-blur-xl bg-black/30 border border-white/[0.06]"
              style={{
                opacity: trade.opacity,
                transform: `translateX(${trade.offsetX}px)`,
                transition: 'none',
              }}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div
                    className="w-1 h-5 rounded-full"
                    style={{ backgroundColor: sideColor, boxShadow: `0 0 4px ${sideColor}` }}
                  />
                  <div>
                    <div className="text-xs font-medium text-white/80">{trade.symbol}</div>
                    <div className="text-[9px] text-white/30">
                      {trade.exchange?.toUpperCase() || 'KRAKEN'}
                    </div>
                  </div>
                </div>
                <div className="text-right">
                  <div
                    className="text-[10px] font-medium uppercase tracking-wider"
                    style={{ color: sideColor }}
                  >
                    {isBuy ? 'BUY' : 'SELL'}
                  </div>
                  <div className={`text-[10px] ${trade.pnl >= 0 ? 'text-success' : 'text-destructive'}`}>
                    {trade.pnl >= 0 ? '+' : ''}{trade.pnl.toFixed(2)}
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
