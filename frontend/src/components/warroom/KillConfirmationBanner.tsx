/**
 * 🎯☘️ KILL CONFIRMATION BANNER ☘️🎯
 * ====================================
 * 
 * When a Duck Commando confirms a kill (profitable SELL trade),
 * this banner appears with:
 * - The duck's identity and province
 * - Irish tricolor animation
 * - Random victory quote
 * - Atmospheric Belfast subtitle
 * - 6-second countdown before fade
 * 
 * "Every kill is a victory against the system that hunted us."
 */

import React, { useEffect, useState } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  getDuckForExchange,
  getRandomKillQuote,
  getRandomAtmosphere,
  getMilestoneQuote,
} from '../../core/duckCommandos';

interface KillData {
  symbol: string;
  exchange: string;
  pnl: number;
  quantity?: number;
  price?: number;
  timestamp?: string;
  totalKills?: number; // For milestone quotes
}

interface KillConfirmationBannerProps {
  kill: KillData | null;
  onDismiss?: () => void;
  autoHideMs?: number;
}

export function KillConfirmationBanner({ 
  kill, 
  onDismiss, 
  autoHideMs = 6000 
}: KillConfirmationBannerProps) {
  const [visible, setVisible] = useState(false);
  const [countdown, setCountdown] = useState(100);
  const [quote, setQuote] = useState('');
  const [atmosphere, setAtmosphere] = useState('');
  const [milestoneQuote, setMilestoneQuote] = useState<string | null>(null);

  useEffect(() => {
    if (kill) {
      // Generate quotes on new kill
      setQuote(getRandomKillQuote(kill.exchange));
      setAtmosphere(getRandomAtmosphere());
      setMilestoneQuote(kill.totalKills ? getMilestoneQuote(kill.totalKills) : null);
      setVisible(true);
      setCountdown(100);

      // Countdown animation
      const interval = setInterval(() => {
        setCountdown((prev) => Math.max(0, prev - (100 / (autoHideMs / 100))));
      }, 100);

      // Auto-hide
      const timeout = setTimeout(() => {
        setVisible(false);
        onDismiss?.();
      }, autoHideMs);

      return () => {
        clearInterval(interval);
        clearTimeout(timeout);
      };
    }
  }, [kill, autoHideMs, onDismiss]);

  if (!kill || !visible) return null;

  const duck = getDuckForExchange(kill.exchange);
  const exchangeLabel = kill.exchange.charAt(0).toUpperCase() + kill.exchange.slice(1);

  return (
    <Card className="relative overflow-hidden bg-gradient-to-br from-slate-900 to-slate-800 border-success/50 animate-in slide-in-from-top-4 duration-500 shadow-lg shadow-success/20 mb-4">
      {/* Irish Tricolor Animated Border */}
      <div className="absolute top-0 left-0 right-0 h-1 flex">
        <div className="flex-1 bg-success animate-pulse" />
        <div className="flex-1 bg-white animate-pulse [animation-delay:100ms]" />
        <div className="flex-1 bg-warning animate-pulse [animation-delay:200ms]" />
      </div>

      <CardContent className="p-4 pt-5">
        {/* Header */}
        <div className="flex items-center justify-center gap-3 mb-3">
          <span className="text-2xl animate-bounce">☘️</span>
          <span className="text-xl font-extrabold tracking-wider bg-gradient-to-r from-success via-white to-warning bg-clip-text text-transparent">
            KILL CONFIRMED
          </span>
          <span className="text-2xl animate-bounce">☘️</span>
        </div>

        {/* Duck Identity */}
        {duck && (
          <div 
            className="flex items-center justify-center gap-2 mb-3 text-sm flex-wrap"
            style={{ color: duck.provinceColor }}
          >
            <span className="text-3xl">{duck.avatar}</span>
            <span className="font-bold">{duck.realName}</span>
            <span className="italic opacity-90">"{duck.nickname}"</span>
            <Badge 
              variant="outline" 
              className="text-xs"
              style={{ borderColor: duck.provinceColor, color: duck.provinceColor }}
            >
              {duck.province} {duck.provinceEmoji}
            </Badge>
          </div>
        )}

        {/* Trade Details */}
        <div className="flex items-center justify-center gap-4 mb-3 flex-wrap">
          <span className="text-lg font-bold text-white">{kill.symbol}</span>
          <Badge 
            className="text-xs font-semibold"
            style={{ backgroundColor: duck?.provinceColor || '#888', color: '#000' }}
          >
            {duck?.exchangeEmoji || '💱'} {exchangeLabel}
          </Badge>
          <span className={`text-xl font-extrabold ${kill.pnl >= 0 ? 'text-success drop-shadow-[0_0_10px_rgba(0,255,136,0.5)]' : 'text-destructive'}`}>
            {kill.pnl >= 0 ? '+' : ''}${kill.pnl.toFixed(4)}
          </span>
        </div>

        {/* Victory Quote */}
        <p className="text-center text-warning italic mb-2 text-sm drop-shadow-[0_0_10px_rgba(255,215,0,0.3)]">
          "{quote}"
        </p>

        {/* Milestone Quote (if applicable) */}
        {milestoneQuote && (
          <p className="text-center text-warning font-bold text-sm mb-2 animate-pulse">
            👑 {milestoneQuote}
          </p>
        )}

        {/* Atmospheric Subtitle */}
        <p className="text-center text-gray-500 italic text-xs mb-3">
          {atmosphere}
        </p>

        {/* Countdown Bar */}
        <div className="h-1 bg-slate-700 rounded-full overflow-hidden">
          <div 
            className="h-full bg-gradient-to-r from-success via-white to-warning transition-all duration-100"
            style={{ width: `${countdown}%` }}
          />
        </div>
      </CardContent>
    </Card>
  );
}

export default KillConfirmationBanner;
