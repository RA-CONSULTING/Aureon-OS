import { useEffect, useRef, useState } from 'react';
import { Card } from '@/components/ui/card';
import { useGlobalState } from '@/hooks/useGlobalState';
import { cn } from '@/lib/utils';

const safeNumber = (value: unknown, fallback = 0): number => {
  const num = Number(value);
  return Number.isFinite(num) ? num : fallback;
};

const formatSigned = (value: unknown, digits = 2, prefix = '') => {
  const num = safeNumber(value);
  const sign = num >= 0 ? '+' : '';
  return `${prefix}${sign}${num.toFixed(digits)}`;
};

const formatClock = (value: Date | number | string | null | undefined) => {
  const date = value instanceof Date ? value : value ? new Date(value) : null;
  return date && !Number.isNaN(date.getTime()) ? date.toLocaleTimeString() : '--:--:--';
};

const formatAge = (seconds: unknown) => {
  const total = Math.max(0, Math.floor(safeNumber(seconds)));
  const mins = Math.floor(total / 60);
  const secs = total % 60;
  return `${mins}m ${secs}s`;
};

const ExchangeMetric = ({
  label,
  value,
  className,
}: {
  label: string;
  value: string;
  className?: string;
}) => (
  <div className="flex items-center justify-between gap-3 text-[11px] font-mono">
    <span className="text-muted-foreground">{label}</span>
    <span className={cn('text-foreground', className)}>{value}</span>
  </div>
);

const PositionLine = ({
  symbol,
  side,
  entryPrice,
  currentPrice,
  pnlPercent,
  exchange,
  tradeId,
}: {
  symbol: string;
  side: 'LONG' | 'SHORT';
  entryPrice: number;
  currentPrice: number;
  pnlPercent: number;
  exchange?: string;
  tradeId?: string;
}) => (
  <div className="rounded border border-border/40 bg-background/60 px-3 py-2">
    <div className="flex items-center justify-between gap-3 font-mono text-[11px]">
      <div className="flex items-center gap-2">
        <span className="font-semibold text-foreground">{symbol}</span>
        <span className={cn('text-[10px]', side === 'LONG' ? 'text-success' : 'text-destructive')}>
          {side}
        </span>
        {exchange && <span className="text-[10px] uppercase text-muted-foreground">{exchange}</span>}
      </div>
      <span className={cn(pnlPercent >= 0 ? 'text-success' : 'text-destructive')}>
        {formatSigned(pnlPercent, 2)}%
      </span>
    </div>
    <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 font-mono text-[10px] text-muted-foreground">
      <span>Entry ${entryPrice.toFixed(4)}</span>
      <span>Now ${currentPrice.toFixed(4)}</span>
      <span>ID {tradeId || 'n/a'}</span>
    </div>
  </div>
);

const ShadowLine = ({
  symbol,
  side,
  entryPrice,
  currentPrice,
  movePercent,
  targetMovePercent,
  exchange,
  validated,
  ageSeconds,
}: {
  symbol: string;
  side: 'LONG' | 'SHORT';
  entryPrice: number;
  currentPrice: number;
  movePercent: number;
  targetMovePercent: number;
  exchange?: string;
  validated?: boolean;
  ageSeconds?: number;
}) => (
  <div className="rounded border border-border/40 bg-background/60 px-3 py-2">
    <div className="flex items-center justify-between gap-3 font-mono text-[11px]">
      <div className="flex items-center gap-2">
        <span className="font-semibold text-foreground">{symbol}</span>
        <span className={cn('text-[10px]', side === 'LONG' ? 'text-success' : 'text-destructive')}>
          {side}
        </span>
        {exchange && <span className="text-[10px] uppercase text-muted-foreground">{exchange}</span>}
        {validated && <span className="text-[10px] text-warning">VALID</span>}
      </div>
      <span className={cn(movePercent >= 0 ? 'text-success' : 'text-destructive')}>
        {formatSigned(movePercent, 3)}%
      </span>
    </div>
    <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 font-mono text-[10px] text-muted-foreground">
      <span>Entry ${entryPrice.toFixed(4)}</span>
      <span>Now ${currentPrice.toFixed(4)}</span>
      <span>Need {targetMovePercent.toFixed(3)}%</span>
      <span>Age {formatAge(ageSeconds)}</span>
    </div>
  </div>
);

export function LiveTerminalStats() {
  const state = useGlobalState();
  const [clock, setClock] = useState(() => new Date());
  const [voiceEnabled, setVoiceEnabled] = useState(true);
  const lastSpokenRef = useRef('');
  const lastSpokenAtRef = useRef(0);
  const pendingSpeechRef = useRef('');
  const unlockedRef = useRef(false);
  const [voiceStatus, setVoiceStatus] = useState('starting');

  const normalizeSpeechText = (text: string) =>
    text
      .replace(/\b\d+(?:\.\d+)?%/g, '')
      .replace(/\b[$£€]\s*\d+(?:\.\d+)?/g, '')
      .replace(/\b\d+(?:\.\d+)?\b/g, '')
      .replace(/\s+/g, ' ')
      .trim();

  const speakQueenText = (text: string) => {
    if (typeof window === 'undefined' || !('speechSynthesis' in window)) {
      setVoiceStatus('unsupported');
      return;
    }
    const synth = window.speechSynthesis;
    const trimmed = normalizeSpeechText(text);
    if (!trimmed) {
      return;
    }
    const voices = synth.getVoices();
    if (voices.length === 0) {
      pendingSpeechRef.current = trimmed;
      setVoiceStatus('loading');
      return;
    }
    if (!unlockedRef.current) {
      pendingSpeechRef.current = trimmed;
      setVoiceStatus('waiting');
      return;
    }
    const now = Date.now();
    if ((now - lastSpokenAtRef.current) < 6000 && lastSpokenRef.current !== '') {
      pendingSpeechRef.current = trimmed;
      setVoiceStatus('cooldown');
      return;
    }
    if (lastSpokenRef.current === trimmed && voiceStatus !== 'waiting' && voiceStatus !== 'loading' && voiceStatus !== 'starting') {
      setVoiceStatus('live');
      return;
    }
    synth.cancel();
    const utterance = new SpeechSynthesisUtterance(trimmed);
    utterance.lang = 'en-GB';
    utterance.rate = 1.02;
    utterance.pitch = 0.92;
    utterance.volume = 1;
    const preferred = voices.find((voice) =>
      /female|zira|susan|aria|libby|samantha|serena|google uk english female/i.test(
        `${voice.name} ${voice.voiceURI}`,
      ),
    );
    if (preferred) {
      utterance.voice = preferred;
    }
    utterance.onstart = () => setVoiceStatus('speaking');
    utterance.onend = () => setVoiceStatus('live');
    utterance.onerror = () => setVoiceStatus('blocked');
    lastSpokenRef.current = trimmed;
    lastSpokenAtRef.current = now;
    pendingSpeechRef.current = '';
    synth.resume();
    window.setTimeout(() => synth.speak(utterance), 30);
  };

  useEffect(() => {
    const id = window.setInterval(() => setClock(new Date()), 1000);
    return () => window.clearInterval(id);
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined' || !('speechSynthesis' in window)) {
      setVoiceStatus('unsupported');
      return;
    }
    const synth = window.speechSynthesis;
    const unlock = () => {
      unlockedRef.current = true;
      synth.resume();
      if (voiceEnabled && pendingSpeechRef.current) {
        const pending = pendingSpeechRef.current;
        pendingSpeechRef.current = '';
        speakQueenText(pending);
      } else if (voiceEnabled) {
        speakQueenText(String(state.queenVoice?.text || 'Queen voice online.'));
      } else {
        setVoiceStatus('live');
      }
    };
    const handleVoicesChanged = () => {
      if (voiceEnabled && pendingSpeechRef.current) {
        speakQueenText(pendingSpeechRef.current);
      }
    };
    window.addEventListener('click', unlock, { once: true });
    window.addEventListener('pointerdown', unlock, { once: true });
    window.addEventListener('keydown', unlock, { once: true });
    synth.onvoiceschanged = handleVoicesChanged;
    synth.getVoices();
    return () => {
      synth.onvoiceschanged = null;
      window.removeEventListener('click', unlock);
      window.removeEventListener('pointerdown', unlock);
      window.removeEventListener('keydown', unlock);
    };
  }, [voiceEnabled, state.queenVoice?.text]);

  useEffect(() => {
    if (!voiceEnabled) {
      return;
    }
    const id = window.setInterval(() => {
      if (pendingSpeechRef.current && unlockedRef.current) {
        const pending = pendingSpeechRef.current;
        pendingSpeechRef.current = '';
        speakQueenText(pending);
      }
    }, 1500);
    return () => window.clearInterval(id);
  }, [voiceEnabled]);

  useEffect(() => {
    const text = String(state.queenVoice?.text || '').trim();
    if (!voiceEnabled || !text) {
      return;
    }
    speakQueenText(text);
  }, [state.queenVoice?.text, voiceEnabled]);

  const summary = state.unifiedMarketSummary;
  const activePositions = Array.isArray(state.activePositions) ? state.activePositions : [];
  const shadowTrades = Array.isArray(state.shadowTrades) ? state.shadowTrades : [];
  const recentTrades = Array.isArray(state.recentTrades) ? state.recentTrades : [];
  const krakenPositions = activePositions.filter((pos) => pos.exchange === 'kraken');
  const capitalPositions = activePositions.filter((pos) => pos.exchange === 'capital');
  const krakenShadows = shadowTrades.filter((shadow) => shadow.exchange === 'kraken');
  const capitalShadows = shadowTrades.filter((shadow) => shadow.exchange === 'capital');
  const topWinningTrades = [...recentTrades]
    .filter((trade) => safeNumber(trade.pnl) > 0)
    .sort((a, b) => safeNumber(b.pnl) - safeNumber(a.pnl))
    .slice(0, 5);

  const totalEquity = safeNumber(state.totalEquity);
  const available = safeNumber(state.availableBalance);
  const totalPnl = safeNumber(state.totalPnl);
  const krakenEquity = safeNumber(summary?.krakenEquity);
  const capitalEquity = safeNumber(summary?.capitalEquityGbp);
  const krakenPnl = safeNumber(summary?.krakenSessionPnl);
  const capitalPnl = safeNumber(summary?.capitalSessionPnlGbp);
  const krakenOpen = safeNumber(summary?.krakenOpenPositions, krakenPositions.length);
  const capitalOpen = safeNumber(summary?.capitalOpenPositions, capitalPositions.length);
  const capitalRisk = summary?.capitalRiskEnvelope || {};
  const capitalRatchet = summary?.capitalConfidenceRatchet || {};
  const capitalWaveform = summary?.capitalUnifiedWaveformCheck || {};
  const capitalNoLossQueue = summary?.capitalNoLossHoldQueue || {};
  const queenVoice = state.queenVoice;

  return (
    <Card className="border-border/50 bg-background/95 p-4">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3 border-b border-border/40 pb-3">
        <div>
          <div className="text-sm font-semibold text-foreground">Live Exchange Metrics</div>
          <div className="text-xs text-muted-foreground">Trade IDs, winners, and terminal timing</div>
        </div>
        <div className="grid gap-1 text-right font-mono text-[11px]">
          <div className="text-foreground">Now {formatClock(clock)}</div>
          <div className="text-muted-foreground">Feed {state.wsConnected ? 'live' : 'polling'} ({state.wsMessageCount})</div>
          <div className="text-muted-foreground">Updated {formatClock(state.lastDataReceived)}</div>
        </div>
      </div>

      <div className="mb-4 rounded border border-border/40 bg-muted/20 p-3">
        <div className="mb-2 flex items-center justify-between gap-3">
          <div>
            <div className="font-mono text-xs font-semibold text-foreground">QUEEN VOICE</div>
            <div className="text-[11px] text-muted-foreground">
              Live explanation from current exchange intelligence snapshots
            </div>
          </div>
          <button
            type="button"
            onClick={() => setVoiceEnabled((current) => !current)}
            className={cn(
              'rounded border px-2 py-1 font-mono text-[10px]',
              voiceEnabled ? 'border-success/50 text-success' : 'border-border/50 text-muted-foreground',
            )}
          >
            {voiceEnabled ? 'Voice On' : 'Voice Off'}
          </button>
          <button
            type="button"
            onClick={() => {
              unlockedRef.current = true;
              lastSpokenRef.current = '';
              speakQueenText(String(queenVoice?.text || 'Queen voice test. Audio path confirmed.'));
            }}
            className="rounded border border-border/50 px-2 py-1 font-mono text-[10px] text-foreground"
          >
            Test Voice
          </button>
        </div>
        <div className="space-y-2">
          <div className="font-mono text-[11px] leading-5 text-foreground">
            {queenVoice?.text || 'Queen voice is waiting for live intelligence snapshots.'}
          </div>
          <div className="flex flex-wrap gap-x-3 gap-y-1 font-mono text-[10px] text-muted-foreground">
            <span>Mode {queenVoice?.mode || state.queenState}</span>
            <span>Stamped {formatClock(queenVoice?.ts)}</span>
            <span>Audio {voiceStatus}</span>
          </div>
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.4fr_1.4fr_1fr]">
        <div className="rounded border border-border/40 bg-muted/20 p-3">
          <div className="mb-2 font-mono text-xs font-semibold text-foreground">KRAKEN</div>
          <div className="space-y-1.5">
            <ExchangeMetric label="Equity" value={`$${krakenEquity.toFixed(2)}`} />
            <ExchangeMetric label="Session P&L" value={formatSigned(krakenPnl, 2, '$')} className={krakenPnl >= 0 ? 'text-success' : 'text-destructive'} />
            <ExchangeMetric label="Open Positions" value={`${krakenOpen}`} />
            <ExchangeMetric label="Shadows" value={`${safeNumber(summary?.krakenShadows, krakenShadows.length)}`} />
          </div>
          <div className="mt-3 space-y-2">
            {krakenPositions.length > 0 ? (
              krakenPositions.slice(0, 5).map((pos, index) => (
                <PositionLine
                  key={`kraken-${pos.symbol}-${pos.tradeId || index}`}
                  symbol={pos.symbol}
                  side={pos.side}
                  entryPrice={safeNumber(pos.entryPrice)}
                  currentPrice={safeNumber(pos.currentPrice, safeNumber(pos.entryPrice))}
                  pnlPercent={safeNumber(pos.pnlPercent)}
                  exchange={pos.exchange}
                  tradeId={pos.tradeId}
                />
              ))
            ) : (
              <div className="font-mono text-[11px] text-muted-foreground">No open Kraken positions</div>
            )}
          </div>
          <div className="mt-3 space-y-2">
            <div className="font-mono text-[10px] uppercase tracking-wide text-muted-foreground">Shadow Validation</div>
            {krakenShadows.length > 0 ? (
              krakenShadows.slice(0, 4).map((shadow, index) => (
                <ShadowLine
                  key={`kraken-shadow-${shadow.symbol}-${index}`}
                  symbol={shadow.symbol}
                  side={shadow.side}
                  entryPrice={safeNumber(shadow.entryPrice)}
                  currentPrice={safeNumber(shadow.currentPrice, safeNumber(shadow.entryPrice))}
                  movePercent={safeNumber(shadow.movePercent)}
                  targetMovePercent={safeNumber(shadow.targetMovePercent)}
                  exchange={shadow.exchange}
                  validated={Boolean(shadow.validated)}
                  ageSeconds={safeNumber(shadow.ageSeconds)}
                />
              ))
            ) : (
              <div className="font-mono text-[11px] text-muted-foreground">No active Kraken shadows</div>
            )}
          </div>
        </div>

        <div className="rounded border border-border/40 bg-muted/20 p-3">
          <div className="mb-2 font-mono text-xs font-semibold text-foreground">CAPITAL</div>
          <div className="space-y-1.5">
            <ExchangeMetric label="Equity" value={`£${capitalEquity.toFixed(2)}`} />
            <ExchangeMetric label="Session P&L" value={formatSigned(capitalPnl, 2, '£')} className={capitalPnl >= 0 ? 'text-success' : 'text-destructive'} />
            <ExchangeMetric label="Open Positions" value={`${capitalOpen}`} />
            <ExchangeMetric label="Shadows" value={`${safeNumber(summary?.capitalShadows, capitalShadows.length)}`} />
          </div>
          <div className="mt-3 rounded border border-border/40 bg-background/60 p-2 font-mono text-[10px]">
            <div className="mb-1 font-semibold text-foreground">Capital Survival Brain</div>
            <div className="grid gap-1 text-muted-foreground">
              <div className="flex justify-between gap-2">
                <span>Reserve</span>
                <span className="text-foreground">GBP {safeNumber(capitalRisk.reserve_required_gbp).toFixed(2)}</span>
              </div>
              <div className="flex justify-between gap-2">
                <span>Stress Buffer</span>
                <span className={safeNumber(capitalRisk.stress_buffer_before_gbp) >= 0 ? 'text-success' : 'text-destructive'}>
                  GBP {safeNumber(capitalRisk.stress_buffer_before_gbp).toFixed(2)}
                </span>
              </div>
              <div className="flex justify-between gap-2">
                <span>Dynamic Slots</span>
                <span className={capitalRisk.dynamic_lane_expansion_enabled ? 'text-success' : 'text-muted-foreground'}>
                  {capitalRisk.dynamic_lane_expansion_enabled ? 'armed' : 'base lanes'}
                </span>
              </div>
              <div className="flex justify-between gap-2">
                <span>Waveform</span>
                <span className={capitalWaveform.ok === false ? 'text-destructive' : 'text-success'}>
                  {capitalWaveform.ok === false ? 'contradiction' : 'clear'}
                </span>
              </div>
              <div className="flex justify-between gap-2">
                <span>Ratchet</span>
                <span className={capitalRatchet.ok === false ? 'text-warning' : 'text-success'}>
                  {capitalRatchet.reason || 'ready'}
                </span>
              </div>
              <div className="flex justify-between gap-2">
                <span>No-loss queue</span>
                <span className={safeNumber(capitalNoLossQueue.losing_position_count) > 0 ? 'text-warning' : 'text-muted-foreground'}>
                  {safeNumber(capitalNoLossQueue.losing_position_count)} held
                </span>
              </div>
            </div>
          </div>
          <div className="mt-3 space-y-2">
            {capitalPositions.length > 0 ? (
              capitalPositions.slice(0, 5).map((pos, index) => (
                <PositionLine
                  key={`capital-${pos.symbol}-${pos.tradeId || index}`}
                  symbol={pos.symbol}
                  side={pos.side}
                  entryPrice={safeNumber(pos.entryPrice)}
                  currentPrice={safeNumber(pos.currentPrice, safeNumber(pos.entryPrice))}
                  pnlPercent={safeNumber(pos.pnlPercent)}
                  exchange={pos.exchange}
                  tradeId={pos.tradeId}
                />
              ))
            ) : (
              <div className="font-mono text-[11px] text-muted-foreground">No open Capital positions</div>
            )}
          </div>
          <div className="mt-3 space-y-2">
            <div className="font-mono text-[10px] uppercase tracking-wide text-muted-foreground">Shadow Validation</div>
            {capitalShadows.length > 0 ? (
              capitalShadows.slice(0, 4).map((shadow, index) => (
                <ShadowLine
                  key={`capital-shadow-${shadow.symbol}-${index}`}
                  symbol={shadow.symbol}
                  side={shadow.side}
                  entryPrice={safeNumber(shadow.entryPrice)}
                  currentPrice={safeNumber(shadow.currentPrice, safeNumber(shadow.entryPrice))}
                  movePercent={safeNumber(shadow.movePercent)}
                  targetMovePercent={safeNumber(shadow.targetMovePercent)}
                  exchange={shadow.exchange}
                  validated={Boolean(shadow.validated)}
                  ageSeconds={safeNumber(shadow.ageSeconds)}
                />
              ))
            ) : (
              <div className="font-mono text-[11px] text-muted-foreground">No active Capital shadows</div>
            )}
          </div>
        </div>

        <div className="rounded border border-border/40 bg-muted/20 p-3">
          <div className="mb-2 font-mono text-xs font-semibold text-foreground">TOP 5 WINNERS</div>
          <div className="space-y-2">
            {topWinningTrades.length > 0 ? (
              topWinningTrades.map((trade, index) => (
                <div key={`${trade.exchange || 'local'}-${trade.tradeId || trade.symbol}-${index}`} className="rounded border border-border/40 bg-background/60 px-3 py-2 font-mono text-[10px]">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-semibold text-foreground">
                      #{index + 1} {trade.symbol} {trade.side}
                    </span>
                    <span className="text-success">{formatSigned(trade.pnl, 2, trade.exchange === 'capital' ? '£' : '$')}</span>
                  </div>
                  <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-muted-foreground">
                    <span>{trade.exchange || 'local'}</span>
                    <span>{formatClock(trade.time)}</span>
                    <span>Hold {formatAge(trade.holdSeconds)}</span>
                    <span>ID {trade.tradeId || 'n/a'}</span>
                  </div>
                </div>
              ))
            ) : (
              <div className="font-mono text-[11px] text-muted-foreground">No profitable closed trades yet</div>
            )}
          </div>
        </div>
      </div>

      <div className="mt-4 rounded border border-border/40 bg-background/60 p-3">
        <div className="mb-2 font-mono text-xs font-semibold text-foreground">ACCOUNT SUMMARY</div>
        <div className="grid gap-1.5 md:grid-cols-3">
          <ExchangeMetric label="Portfolio" value={`€${totalEquity.toFixed(2)}`} />
          <ExchangeMetric label="Available" value={`€${available.toFixed(2)}`} />
          <ExchangeMetric
            label="Session"
            value={formatSigned(totalPnl, 2, '€')}
            className={totalPnl >= 0 ? 'text-success' : 'text-destructive'}
          />
        </div>
        {state.latestMonitorLine && (
          <div className="mt-3 border-t border-border/30 pt-3 font-mono text-[11px] text-muted-foreground">
            {state.latestMonitorLine}
          </div>
        )}
      </div>
    </Card>
  );
}
