/**
 * Terminal Sync Hook
 * Prime Sentinel: GARY LECKEY 02111991
 * 
 * Reads REAL data from database tables populated by Python terminal
 * via ingest-terminal-state endpoint
 * 
 * PUBLIC LIVE FEED - No authentication required
 */

import { useEffect, useCallback, useRef } from 'react';
import { supabase } from '@/integrations/supabase/client';
import { globalSystemsManager } from '@/core/globalSystemsManager';
import { terminalStateUrls } from '@/config/serviceEndpoints';

// Public live feed user ID - data pushed from Python terminal
const LIVE_FEED_USER_ID = '69e5567f-7ad1-42af-860f-3709ef1f5935';
const ENV_LOCAL_TERMINAL_ENDPOINT = import.meta.env.VITE_LOCAL_TERMINAL_URL as string | undefined;
const DEFAULT_LOCAL_TERMINAL_ENDPOINTS = [
  ENV_LOCAL_TERMINAL_ENDPOINT,
  '/api/terminal-state', // production: nginx proxies /api to the gateway
  ...terminalStateUrls,
].filter((value): value is string => Boolean(value));
const TERMINAL_SYNC_DEBUG = (import.meta.env.VITE_TERMINAL_SYNC_DEBUG as string | undefined) === '1';

interface WakeUpManifest {
  runtime_feed_url?: string;
}

const uniqueStrings = (values: Array<string | undefined>): string[] =>
  Array.from(new Set(values.map((value) => String(value || '').trim()).filter(Boolean)));

const loadLocalTerminalEndpoints = async (): Promise<string[]> => {
  try {
    const response = await fetch('/aureon_wake_up_manifest.json', { cache: 'no-store' });
    if (!response.ok) return DEFAULT_LOCAL_TERMINAL_ENDPOINTS;
    const manifest = (await response.json()) as WakeUpManifest;
    return uniqueStrings([manifest.runtime_feed_url, ...DEFAULT_LOCAL_TERMINAL_ENDPOINTS]);
  } catch {
    return DEFAULT_LOCAL_TERMINAL_ENDPOINTS;
  }
};

interface RuntimeStats {
  runtime_minutes: number;
  peak_equity: number;
  current_drawdown: number;
  max_drawdown: number;
  avg_hold_time_minutes?: number;
  mycelium_hives: number;
  mycelium_agents: number;
  mycelium_generation: number;
  max_generation: number;
  queen_state: string;
  queen_pnl: number;
  scout_count: number;
  split_count: number;
  entry_threshold: number;
  exit_threshold: number;
  risk_multiplier: number;
  tp_multiplier: number;
  ws_connected: boolean;
  ws_message_count: number;
  gaia_purity: number;
  gaia_carrier_phi: number;
  latest_monitor_line?: string;
  status_lines?: string[];
}

interface LocalTerminalState {
  ok?: boolean;
  generated_at?: string;
  queen_voice?: {
    ts?: string;
    mode?: string;
    text?: string;
    lines?: string[];
  };
  kraken?: any;
  capital?: any;
  combined?: any;
  portfolio_value: number;
  peak_equity: number;
  current_drawdown: number;
  max_drawdown: number;
  total_trades: number;
  wins: number;
  avg_hold_time?: number;
  positions?: Array<{
    symbol: string;
    side: string;
    trade_id?: string;
    deal_id?: string;
    entry_price: number;
    quantity: number;
    current_price?: number;
    unrealized_pnl?: number;
    opened_at?: string;
  }>;
  recent_trades?: Array<{
    time: string;
    side: string;
    symbol: string;
    quantity: number;
    pnl: number;
    success: boolean;
    trade_id?: string;
    hold_seconds?: number;
    reason?: string;
  }>;
  coherence?: number;
  lambda?: number;
  gaia_state?: string;
  gaia_frequency?: number;
  gaia_purity?: number;
  gaia_carrier_phi?: number;
  gaia_432_lock?: number;
  hnc_frequency?: number;
  hnc_market_state?: string;
  hnc_coherence_percent?: number;
  hnc_modifier?: number;
  trading_mode?: string;
  entry_threshold?: number;
  exit_threshold?: number;
  risk_multiplier?: number;
  tp_multiplier?: number;
  mycelium_hives?: number;
  mycelium_agents?: number;
  mycelium_generation?: number;
  max_generation?: number;
  queen_state?: string;
  queen_pnl?: number;
  compounded?: number;
  harvested?: number;
  pool_total?: number;
  pool_available?: number;
  scout_count?: number;
  split_count?: number;
  runtime_minutes?: number;
  ws_connected?: boolean;
  ws_message_count?: number;
  latest_monitor_line?: string;
  status_lines?: string[];
}

const toNumber = (value: unknown, fallback = 0): number => {
  const num = Number(value);
  return Number.isFinite(num) ? num : fallback;
};

const toStringList = (value: unknown): string[] =>
  Array.isArray(value) ? value.map((item) => String(item ?? '')).filter(Boolean) : [];

const confidenceWord = (value: unknown): string => {
  const score = toNumber(value);
  if (score >= 0.85) return 'very strong';
  if (score >= 0.65) return 'strong';
  if (score >= 0.45) return 'building';
  if (score > 0) return 'tentative';
  return 'unclear';
};

const buildFallbackQueenVoice = (localState: LocalTerminalState): { ts: string; mode: string; text: string; lines: string[] } => {
  const ts = String(localState.generated_at || new Date().toISOString());
  const kraken = localState.kraken || {};
  const capital = localState.capital || {};
  const decision = kraken.decision_snapshot || {};
  const capitalTarget = capital.target_snapshot || {};
  const capitalCandidates = Array.isArray(capital.candidate_snapshot) ? capital.candidate_snapshot : [];
  const krakenPositions = Array.isArray(kraken.positions) ? kraken.positions : [];
  const capitalPositions = Array.isArray(capital.positions) ? capital.positions : [];
  const openCount = toNumber(localState.combined?.open_positions || (krakenPositions.length + capitalPositions.length));
  const lines: string[] = [];

  if (openCount > 0) {
    lines.push(`Summary. I am managing ${openCount} live position${openCount === 1 ? '' : 's'} across Kraken and Capital.`);
  } else {
    lines.push('Summary. I am flat on both exchanges and waiting for the next clean strike.');
  }

  if (krakenPositions.length > 0) {
    const parts = krakenPositions.slice(0, 2).map((pos: any) => `${String(pos.symbol || pos.pair || '?')} ${String(pos.side || pos.direction || '?').toUpperCase()}`);
    lines.push(`Kraken update. I am managing ${parts.join(' and ')}.`);
  } else if (decision?.decision && decision?.symbol) {
    lines.push(
      `Kraken update. I am leaning toward ${String(decision.symbol)} ${String(decision.side || '').toLowerCase()} ` +
      `with a ${confidenceWord(decision.decision.confidence)} read.`,
    );
  } else {
    lines.push('Kraken update. I am watching for a cleaner crypto entry.');
  }

  if (capitalPositions.length > 0) {
    const parts = capitalPositions.slice(0, 2).map((pos: any) => `${String(pos.symbol || '?')} ${String(pos.direction || pos.side || '?').toUpperCase()}`);
    lines.push(`Capital update. I am managing ${parts.join(' and ')}.`);
  } else if (capitalTarget?.symbol) {
    lines.push(
      `Capital update. I am stalking ${String(capitalTarget.symbol)} ${String(capitalTarget.direction || '').toUpperCase()}.`,
    );
    if (capitalTarget.preflight_reason) {
      lines.push('Capital is still waiting because exchange checks are blocking entry.');
    }
  } else if (capitalCandidates.length > 0) {
    const top = capitalCandidates[0] || {};
    lines.push(
      `Capital update. My next candidate is ${String(top.symbol || '?')} ${String(top.direction || '').toUpperCase()} if the current leader fails.`,
    );
  } else {
    lines.push('Capital update. I am waiting for a valid CFD setup.');
  }

  if (openCount > 0) {
    lines.push('I am watching the open positions closely and waiting for clean profit exits.');
  }

  return {
    ts,
    mode: String(kraken.queen_state || 'HOLD'),
    text: lines.join(' '),
    lines,
  };
};

export function useTerminalSync(enabled: boolean = true, intervalMs: number = 5000) {
  const lastSyncRef = useRef<number>(0);
  const sessionStartRef = useRef<number>(Date.now());

  const fetchLocalTerminalState = useCallback(async (): Promise<LocalTerminalState | null> => {
    try {
      const endpoints = await loadLocalTerminalEndpoints();
      for (const endpoint of endpoints) {
        const response = await fetch(endpoint, { cache: 'no-store' });
        if (!response.ok) continue;
        const data = await response.json();
        if (!data) continue;
        return data as LocalTerminalState;
      }
      return null;
    } catch {
      return null;
    }
  }, []);

  // Fetch session data from aureon_user_sessions (populated by Python)
  const fetchSessionData = useCallback(async () => {
    try {
      const { data, error } = await supabase
        .from('aureon_user_sessions')
        .select('*')
        .eq('user_id', LIVE_FEED_USER_ID)
        .single();

      if (error && error.code !== 'PGRST116') {
        if (TERMINAL_SYNC_DEBUG) {
          console.warn('[TerminalSync] Session fetch unavailable:', error);
        }
        return null;
      }

      return data;
    } catch (err) {
      if (TERMINAL_SYNC_DEBUG) {
        console.warn('[TerminalSync] Session unavailable:', err);
      }
      return null;
    }
  }, []);

  // Fetch latest HNC state (populated by Python)
  const fetchHncState = useCallback(async () => {
    try {
      const { data, error } = await supabase
        .from('hnc_detection_states')
        .select('*')
        .order('timestamp', { ascending: false })
        .limit(1)
        .single();

      if (error && error.code !== 'PGRST116') {
        return null;
      }

      return data;
    } catch (err) {
      return null;
    }
  }, []);

  // Fetch trade statistics from trade_records (populated by Python)
  const fetchTradeStats = useCallback(async () => {
    try {
      const { data: trades, error } = await supabase
        .from('trade_records')
        .select('id, is_win, pnl')
        .eq('user_id', LIVE_FEED_USER_ID);

      if (error || !trades) {
        return { total: 0, wins: 0, winRate: 0, totalPnl: 0 };
      }

      const total = trades.length;
      const wins = trades.filter(t => t.is_win === true).length;
      const winRate = total > 0 ? (wins / total) * 100 : 0;
      const totalPnl = trades.reduce((sum, t) => sum + (t.pnl || 0), 0);

      return { total, wins, winRate, totalPnl };
    } catch (err) {
      return { total: 0, wins: 0, winRate: 0, totalPnl: 0 };
    }
  }, []);

  // Fetch open positions (populated by Python)
  const fetchPositions = useCallback(async () => {
    try {
      const { data, error } = await supabase
        .from('trading_positions')
        .select('*')
        .eq('user_id', LIVE_FEED_USER_ID)
        .eq('status', 'open');

      if (error) return [];
      return data || [];
    } catch (err) {
      return [];
    }
  }, []);

  // Fetch latest runtime stats from local_system_logs
  const fetchRuntimeStats = useCallback(async (): Promise<RuntimeStats | null> => {
    try {
      const { data, error } = await supabase
        .from('local_system_logs')
        .select('parsed_data')
        .eq('module', 'terminal_state')
        .eq('log_type', 'runtime_stats')
        .order('timestamp', { ascending: false })
        .limit(1)
        .single();

      if (error || !data?.parsed_data) return null;
      
      const stats = data.parsed_data as unknown as RuntimeStats;
      if (stats && typeof stats.runtime_minutes === 'number') {
        return stats;
      }
      return null;
    } catch (err) {
      return null;
    }
  }, []);

  const syncTerminalData = useCallback(async () => {
    const now = Date.now();
    if (now - lastSyncRef.current < 1000) return; // Throttle to 1s minimum
    lastSyncRef.current = now;

    const localState = await fetchLocalTerminalState();
    if (localState) {
      if (localState.kraken && localState.capital) {
        const kraken = localState.kraken || {};
        const capital = localState.capital || {};
        const combined = localState.combined || {};
        const krakenStatusLines = toStringList(kraken.status_lines);
        const capitalStatusLines = toStringList(capital.status_lines);
        const unifiedStatusLines = toStringList(localState.status_lines);

        const krakenPositions = Array.isArray(kraken.positions) ? kraken.positions.map((p: any) => {
          const entryPrice = toNumber(p.entry_price || 0);
          const currentPrice = toNumber(p.current_price || entryPrice || 0);
          const rawPct = entryPrice > 0 ? ((currentPrice - entryPrice) / entryPrice) * 100 : 0;
          const sideRaw = String(p.side || '').toUpperCase();
          const isShort = sideRaw === 'SELL' || sideRaw === 'SHORT';
          return {
            symbol: String(p.symbol || p.pair || ''),
            entryPrice,
            currentPrice,
            pnlPercent: isShort ? -rawPct : rawPct,
            side: (isShort ? 'SHORT' : 'LONG') as 'LONG' | 'SHORT',
            exchange: 'kraken',
            tradeId: String(p.trade_id || p.transaction_id || ''),
            openedAt: String(p.opened_at || ''),
          };
        }) : [];

        const capitalPositions = Array.isArray(capital.positions) ? capital.positions.map((p: any) => ({
          symbol: String(p.symbol || ''),
          entryPrice: toNumber(p.entry_price || 0),
          currentPrice: toNumber(p.current_price || p.entry_price || 0),
          pnlPercent: toNumber(p.pnl_pct || 0),
          side: (String(p.direction || 'BUY').toUpperCase() === 'SELL' ? 'SHORT' : 'LONG') as 'LONG' | 'SHORT',
          exchange: 'capital',
          tradeId: String(p.deal_id || ''),
          openedAt: '',
        })) : [];

        const activePositions = [...krakenPositions, ...capitalPositions];

        const krakenShadows = Array.isArray(kraken.shadows) ? kraken.shadows.map((s: any) => ({
          symbol: String(s.symbol || s.pair || ''),
          side: (String(s.side || s.direction || 'BUY').toUpperCase() === 'SELL' ? 'SHORT' : 'LONG') as 'LONG' | 'SHORT',
          entryPrice: toNumber(s.entry_price || 0),
          currentPrice: toNumber(s.current_price || s.entry_price || 0),
          movePercent: toNumber(s.current_move_pct || 0),
          targetMovePercent: toNumber(s.target_move_pct || 0),
          exchange: 'kraken',
          validated: Boolean(s.validated),
          ageSeconds: toNumber(s.age_secs || 0),
        })) : [];

        const capitalShadows = Array.isArray(capital.shadows) ? capital.shadows.map((s: any) => ({
          symbol: String(s.symbol || ''),
          side: (String(s.direction || 'BUY').toUpperCase() === 'SELL' ? 'SHORT' : 'LONG') as 'LONG' | 'SHORT',
          entryPrice: toNumber(s.entry_price || 0),
          currentPrice: toNumber(s.current_price || s.entry_price || 0),
          movePercent: toNumber(s.current_move_pct || 0),
          targetMovePercent: toNumber(s.target_move_pct || 0),
          exchange: 'capital',
          validated: Boolean(s.validated),
          ageSeconds: toNumber(s.age_secs || 0),
        })) : [];

        const shadowTrades = [...krakenShadows, ...capitalShadows];

        const krakenTrades = Array.isArray(kraken.recent_trades) ? kraken.recent_trades.map((trade: any) => ({
          time: String(trade?.time || trade?.closed_at || ''),
          side: String(trade?.side || 'BUY'),
          symbol: String(trade?.symbol || trade?.pair || ''),
          quantity: Number(trade?.quantity || trade?.volume || 0),
          pnl: Number(trade?.pnl || trade?.net_pnl || 0),
          success: Number(trade?.pnl || trade?.net_pnl || 0) >= 0,
          exchange: 'kraken',
          tradeId: String(trade?.trade_id || trade?.transaction_id || ''),
          holdSeconds: Number(trade?.hold_seconds || 0),
          reason: String(trade?.reason || ''),
        })) : [];

        const capitalTrades = Array.isArray(capital.recent_closed_trades) ? capital.recent_closed_trades.map((trade: any) => ({
          time: String(trade?.closed_at || ''),
          side: String(trade?.direction || 'BUY'),
          symbol: String(trade?.symbol || ''),
          quantity: Number(trade?.size || 0),
          pnl: Number(trade?.net_pnl || 0),
          success: Number(trade?.net_pnl || 0) >= 0,
          exchange: 'capital',
          tradeId: String(trade?.deal_id || ''),
          holdSeconds: Number(trade?.age_secs || 0),
          reason: String(trade?.reason || ''),
        })) : [];

        const recentTrades = [...capitalTrades, ...krakenTrades].slice(0, 8);
        const krakenReason = String(
          kraken.equity_reason || kraken.error || combined.kraken_equity_reason || ''
        );
        const krakenEquity = toNumber(kraken.portfolio_value || kraken.equity || combined.kraken_equity || 0);
        const capitalEquity = toNumber(capital.equity_gbp || combined.capital_equity_gbp || 0);
        const equityNote = krakenReason && krakenEquity <= 0 ? krakenReason : '';
        const totalEquity = equityNote ? 0 : (krakenEquity > 0 ? krakenEquity : capitalEquity);
        const krakenFree = toNumber(kraken.pool_available || kraken.free_margin || 0);
        const capitalFree = toNumber(capital.free_gbp || 0);
        const availableBalance = krakenFree > 0 ? krakenFree : capitalFree;
        const krakenPnl = toNumber(kraken.compounded || kraken.session_profit || combined.kraken_session_pnl || 0);
        const capitalPnl = toNumber(capital.stats?.total_pnl_gbp || combined.capital_session_pnl_gbp || 0);
        const totalPnl = krakenPnl !== 0 ? krakenPnl : capitalPnl;
        const latestMonitorLine = String(
          localState.latest_monitor_line
          || capital.latest_monitor_line
          || kraken.latest_monitor_line
          || ''
        );
        const statusLines = unifiedStatusLines.length > 0
          ? unifiedStatusLines
          : [...krakenStatusLines, ...capitalStatusLines].slice(-16);
        const totalTrades = toNumber(kraken.total_trades || 0) + toNumber(capital.stats?.trades_closed || 0);
        const winningTrades = toNumber(kraken.wins || 0) + toNumber(capital.stats?.winning_trades || 0);

        globalSystemsManager.setPartialState({
          totalEquity,
          equityNote,
          availableBalance,
          peakEquity: toNumber(kraken.peak_equity || totalEquity || 0),
          currentDrawdownPercent: toNumber(kraken.current_drawdown || 0),
          maxDrawdownPercent: toNumber(kraken.max_drawdown || 0),
          totalTrades,
          winningTrades,
          totalPnl,
          cyclePnl: totalPnl,
          cyclePnlPercent: totalEquity > 0 ? (totalPnl / totalEquity) * 100 : 0,
          avgHoldTimeMinutes: toNumber(kraken.avg_hold_time || 0),
          activePositions,
          shadowTrades,
          sessionStartTime: sessionStartRef.current,
          coherence: toNumber(kraken.coherence || 0),
          lambda: toNumber(kraken.lambda || 0),
          gaiaLatticeState: ((kraken.gaia_state || 'NEUTRAL').toUpperCase()) as 'COHERENT' | 'DISTORTION' | 'NEUTRAL',
          gaiaFrequency: toNumber(kraken.gaia_frequency || 432),
          purityPercent: toNumber(kraken.gaia_purity || 0),
          carrierWavePhi: toNumber(kraken.gaia_carrier_phi || 0),
          harmonicLock432: toNumber(kraken.gaia_432_lock || 0),
          hncFrequency: toNumber(kraken.hnc_frequency || 432),
          hncMarketState: ((kraken.hnc_market_state || 'CONSOLIDATION').toUpperCase()) as 'CONSOLIDATION' | 'TRENDING' | 'VOLATILE' | 'BREAKOUT',
          hncCoherencePercent: toNumber(kraken.hnc_coherence_percent || 0),
          hncModifier: toNumber(kraken.hnc_modifier || 0.8),
          tradingMode: ((kraken.trading_mode || 'BALANCED').toUpperCase()) as 'AGGRESSIVE' | 'CONSERVATIVE' | 'BALANCED',
          entryCoherenceThreshold: toNumber(kraken.entry_threshold || 0),
          exitCoherenceThreshold: toNumber(kraken.exit_threshold || 0),
          riskMultiplier: toNumber(kraken.risk_multiplier || 1),
          takeProfitMultiplier: toNumber(kraken.tp_multiplier || 1),
          myceliumHives: toNumber(kraken.mycelium_hives || 0),
          myceliumAgents: toNumber(kraken.mycelium_agents || 0),
          myceliumGeneration: toNumber(kraken.mycelium_generation || 0),
          maxGeneration: toNumber(kraken.max_generation || 0),
          queenState: ((kraken.queen_state || 'HOLD').toUpperCase()) as 'HOLD' | 'BUY' | 'SELL',
          queenPnl: toNumber(kraken.queen_pnl || 0),
          compoundedCapital: toNumber(kraken.compounded || 0),
          harvestedCapital: toNumber(kraken.harvested || 0),
          poolTotal: toNumber(kraken.pool_total || totalEquity || 0),
          poolAvailable: toNumber(kraken.pool_available || availableBalance || 0),
          scoutCount: toNumber(kraken.scout_count || 0),
          splitCount: toNumber(kraken.split_count || 0),
          wsConnected: Boolean(kraken.ws_connected || localState.ws_connected),
          wsMessageCount: toNumber(kraken.ws_message_count || localState.ws_message_count || 0),
          latestMonitorLine,
          statusLines,
          recentTrades,
          lastDataReceived: localState.generated_at ? Date.parse(String(localState.generated_at)) : Date.now(),
          queenVoice: localState.queen_voice ? {
            ts: String(localState.queen_voice.ts || ''),
            mode: String(localState.queen_voice.mode || 'HOLD'),
            text: String(localState.queen_voice.text || ''),
            lines: Array.isArray(localState.queen_voice.lines) ? localState.queen_voice.lines.map((line) => String(line || '')) : [],
          } : buildFallbackQueenVoice(localState),
          unifiedMarketSummary: {
            krakenEquity: equityNote ? 0 : toNumber(combined.kraken_equity || krakenEquity || 0),
            krakenEquityReason: equityNote,
            capitalEquityGbp: toNumber(combined.capital_equity_gbp || capitalEquity || 0),
            krakenSessionPnl: toNumber(combined.kraken_session_pnl || krakenPnl || 0),
            capitalSessionPnlGbp: toNumber(combined.capital_session_pnl_gbp || capitalPnl || 0),
            openPositions: toNumber(combined.open_positions || activePositions.length),
            capitalOpenPositions: capitalPositions.length,
            krakenOpenPositions: krakenPositions.length,
            capitalRecentCloses: Array.isArray(capital.recent_closed_trades) ? capital.recent_closed_trades.slice(-3).reverse() : [],
            capitalCandidates: Array.isArray(capital.candidate_snapshot) ? capital.candidate_snapshot.slice(0, 3) : [],
            krakenShadows: krakenShadows.length,
            capitalShadows: capitalShadows.length,
            capitalRiskEnvelope: capital.capital_risk_envelope || combined.capital_risk_envelope || {},
            capitalTradeEvidence: capital.capital_trade_evidence || combined.capital_trade_evidence || {},
            capitalConfidenceRatchet: capital.capital_confidence_ratchet || combined.capital_confidence_ratchet || {},
            capitalUnifiedWaveformCheck: capital.capital_unified_waveform_check || combined.capital_unified_waveform_check || {},
            capitalNoLossHoldQueue: capital.capital_no_loss_hold_queue || combined.capital_no_loss_hold_queue || {},
          },
        });

        console.log('[TerminalSync] Unified trader synced:', {
          krakenPositions: krakenPositions.length,
          capitalPositions: capitalPositions.length,
          totalPositions: activePositions.length,
        });
        return;
      }

      const mappedPositions = (localState.positions || []).map((p) => {
        const entryPrice = Number(p.entry_price || 0);
        const currentPrice = Number(p.current_price || entryPrice);
        const rawPct = entryPrice > 0 ? ((currentPrice - entryPrice) / entryPrice) * 100 : 0;
        const isShort = String(p.side || '').toUpperCase() === 'SELL';
        return {
          symbol: p.symbol,
          entryPrice,
          currentPrice,
          pnlPercent: isShort ? -rawPct : rawPct,
          side: (isShort ? 'SHORT' : 'LONG') as 'LONG' | 'SHORT',
        };
      });

        const recentTrades = Array.isArray(localState.recent_trades) ? localState.recent_trades.map((trade) => ({
          time: String(trade?.time || ''),
          side: String(trade?.side || 'BUY'),
          symbol: String(trade?.symbol || ''),
          quantity: Number(trade?.quantity || 0),
          pnl: Number(trade?.pnl || 0),
          success: Boolean(trade?.success),
          exchange: undefined,
          tradeId: String(trade?.trade_id || ''),
          holdSeconds: Number(trade?.hold_seconds || 0),
          reason: String(trade?.reason || ''),
        })) : [];

      const totalPnl = Number(localState.compounded || 0);
      globalSystemsManager.setPartialState({
        totalEquity: Number(localState.portfolio_value || 0),
        peakEquity: Number(localState.peak_equity || localState.portfolio_value || 0),
        currentDrawdownPercent: Number(localState.current_drawdown || 0),
        maxDrawdownPercent: Number(localState.max_drawdown || 0),
        totalTrades: Number(localState.total_trades || 0),
        winningTrades: Number(localState.wins || 0),
        totalPnl,
        cyclePnl: totalPnl,
        cyclePnlPercent: localState.portfolio_value > 0 ? (totalPnl / localState.portfolio_value) * 100 : 0,
        avgHoldTimeMinutes: Number(localState.avg_hold_time || 0),
        activePositions: mappedPositions,
        sessionStartTime: sessionStartRef.current,
        coherence: Number(localState.coherence || 0),
        lambda: Number(localState.lambda || 0),
        gaiaLatticeState: ((localState.gaia_state || 'NEUTRAL').toUpperCase()) as 'COHERENT' | 'DISTORTION' | 'NEUTRAL',
        gaiaFrequency: Number(localState.gaia_frequency || 432),
        purityPercent: Number(localState.gaia_purity || 0),
        carrierWavePhi: Number(localState.gaia_carrier_phi || 0),
        harmonicLock432: Number(localState.gaia_432_lock || 0),
        hncFrequency: Number(localState.hnc_frequency || 432),
        hncMarketState: ((localState.hnc_market_state || 'CONSOLIDATION').toUpperCase()) as 'CONSOLIDATION' | 'TRENDING' | 'VOLATILE' | 'BREAKOUT',
        hncCoherencePercent: Number(localState.hnc_coherence_percent || 0),
        hncModifier: Number(localState.hnc_modifier || 0.8),
        tradingMode: ((localState.trading_mode || 'BALANCED').toUpperCase()) as 'AGGRESSIVE' | 'CONSERVATIVE' | 'BALANCED',
        entryCoherenceThreshold: Number(localState.entry_threshold || 0),
        exitCoherenceThreshold: Number(localState.exit_threshold || 0),
        riskMultiplier: Number(localState.risk_multiplier || 1),
        takeProfitMultiplier: Number(localState.tp_multiplier || 1),
        myceliumHives: Number(localState.mycelium_hives || 0),
        myceliumAgents: Number(localState.mycelium_agents || 0),
        myceliumGeneration: Number(localState.mycelium_generation || 0),
        maxGeneration: Number(localState.max_generation || 0),
        queenState: ((localState.queen_state || 'HOLD').toUpperCase()) as 'HOLD' | 'BUY' | 'SELL',
        queenPnl: Number(localState.queen_pnl || 0),
        compoundedCapital: totalPnl,
        harvestedCapital: Number(localState.harvested || 0),
        poolTotal: Number(localState.pool_total || localState.portfolio_value || 0),
        poolAvailable: Number(localState.pool_available || 0),
        scoutCount: Number(localState.scout_count || 0),
        splitCount: Number(localState.split_count || 0),
        wsConnected: Boolean(localState.ws_connected),
        wsMessageCount: Number(localState.ws_message_count || 0),
        latestMonitorLine: localState.latest_monitor_line || '',
        statusLines: localState.status_lines || [],
        recentTrades,
        lastDataReceived: localState.generated_at ? Date.parse(String(localState.generated_at)) : Date.now(),
        queenVoice: localState.queen_voice ? {
          ts: String(localState.queen_voice.ts || ''),
          mode: String(localState.queen_voice.mode || 'HOLD'),
          text: String(localState.queen_voice.text || ''),
          lines: Array.isArray(localState.queen_voice.lines) ? localState.queen_voice.lines.map((line) => String(line || '')) : [],
        } : buildFallbackQueenVoice(localState),
      });

      console.log('[TerminalSync] Local trader synced:', {
        equity: Number(localState.portfolio_value || 0).toFixed(2),
        trades: localState.total_trades || 0,
        wins: localState.wins || 0,
        positions: mappedPositions.length,
      });
      return;
    }

    // Fetch all data in parallel from DB (populated by Python)
    const [session, hncState, tradeStats, positions, runtimeStats] = await Promise.all([
      fetchSessionData(),
      fetchHncState(),
      fetchTradeStats(),
      fetchPositions(),
      fetchRuntimeStats(),
    ]);

    if (!session) {
      console.log('[TerminalSync] No session data - waiting for Python to push...');
      return;
    }

    // Map positions to display format
    const mappedPositions = positions.map(p => ({
      symbol: p.symbol,
      entryPrice: Number(p.entry_price),
      currentPrice: Number(p.current_price) || Number(p.entry_price),
      pnlPercent: p.current_price && p.entry_price 
        ? ((Number(p.current_price) - Number(p.entry_price)) / Number(p.entry_price)) * 100 
        : 0,
      side: (p.side === 'BUY' ? 'LONG' : 'SHORT') as 'LONG' | 'SHORT',
    }));

    // Determine Gaia state from HNC data
    const gaiaState = hncState?.distortion_power > 0 ? 'DISTORTION' : 
                      (session.current_coherence || 0) > 0.45 ? 'COHERENT' : 'NEUTRAL';

    // Update global state with REAL data from Python
    globalSystemsManager.setPartialState({
      // Portfolio from session (pushed by Python)
      totalEquity: session.total_equity_usdt || 0,
      peakEquity: runtimeStats?.peak_equity || session.total_equity_usdt || 0,
      currentDrawdownPercent: runtimeStats?.current_drawdown || 0,
      maxDrawdownPercent: runtimeStats?.max_drawdown || 0,
      
      // Trade stats from trade_records (pushed by Python)
      totalTrades: session.total_trades || tradeStats.total,
      winningTrades: session.winning_trades || tradeStats.wins,
      totalPnl: session.total_pnl_usdt || tradeStats.totalPnl || 0,
      cyclePnl: session.total_pnl_usdt || tradeStats.totalPnl || 0,
      cyclePnlPercent: session.total_equity_usdt > 0 
        ? ((session.total_pnl_usdt || tradeStats.totalPnl || 0) / session.total_equity_usdt) * 100 
        : 0,
      avgHoldTimeMinutes: runtimeStats?.avg_hold_time_minutes || 0,
      recentTrades: Array.isArray(session.recent_trades) ? (session.recent_trades as Array<any>).map((trade) => ({
        time: String(trade?.time || ''),
        side: String(trade?.side || 'BUY'),
        symbol: String(trade?.symbol || ''),
        quantity: Number(trade?.quantity || 0),
        pnl: Number(trade?.pnl || 0),
        success: Boolean(trade?.success),
      })) : [],
      
      // Positions from trading_positions (pushed by Python)
      activePositions: mappedPositions,
      
      // Session timing
      sessionStartTime: sessionStartRef.current,
      lastDataReceived: Date.now(),
      
      // Coherence/Lambda from session
      coherence: session.current_coherence || 0,
      lambda: session.current_lambda || 0,
      
      // Gaia state
      gaiaLatticeState: gaiaState as 'COHERENT' | 'DISTORTION' | 'NEUTRAL',
      gaiaFrequency: hncState?.schumann_power || (session.prism_level || 440),
      purityPercent: runtimeStats?.gaia_purity || 0,
      carrierWavePhi: runtimeStats?.gaia_carrier_phi || 0,
      harmonicLock432: hncState?.love_power || 0,
      
      // HNC state
      hncFrequency: session.current_lighthouse_signal || 318,
      hncMarketState: (hncState?.bridge_status || 'CONSOLIDATION') as 'CONSOLIDATION' | 'TRENDING' | 'VOLATILE' | 'BREAKOUT',
      hncCoherencePercent: hncState?.harmonic_fidelity || (session.current_coherence || 0) * 100,
      hncModifier: hncState?.imperial_yield || 0.8,
      
      // Trading mode
      tradingMode: (session.trading_mode || 'BALANCED') as 'AGGRESSIVE' | 'CONSERVATIVE' | 'BALANCED',
      entryCoherenceThreshold: runtimeStats?.entry_threshold || 0.2,
      exitCoherenceThreshold: runtimeStats?.exit_threshold || 0.15,
      riskMultiplier: runtimeStats?.risk_multiplier || 0.5,
      takeProfitMultiplier: runtimeStats?.tp_multiplier || 0.8,
      
      // Mycelium swarm
      myceliumHives: runtimeStats?.mycelium_hives || 1,
      myceliumAgents: runtimeStats?.mycelium_agents || 5,
      myceliumGeneration: runtimeStats?.mycelium_generation || 0,
      maxGeneration: runtimeStats?.max_generation || 0,
      queenState: (runtimeStats?.queen_state || session.dominant_node || 'HOLD') as 'HOLD' | 'BUY' | 'SELL',
      queenPnl: runtimeStats?.queen_pnl || 0,
      
      // Capital
      compoundedCapital: session.total_pnl_usdt || 0,
      harvestedCapital: session.gas_tank_balance || 0,
      poolAvailable: session.available_balance_usdt || 0,
      scoutCount: runtimeStats?.scout_count || 0,
      splitCount: runtimeStats?.split_count || 0,
      
      // WebSocket (from runtime stats)
      wsConnected: runtimeStats?.ws_connected || false,
      wsMessageCount: runtimeStats?.ws_message_count || 0,
      latestMonitorLine: runtimeStats?.latest_monitor_line || '',
      statusLines: runtimeStats?.status_lines || [],
    });

    console.log('[TerminalSync] DB data synced:', { 
      equity: (session.total_equity_usdt || 0).toFixed(2),
      trades: session.total_trades || tradeStats.total,
      wins: session.winning_trades || tradeStats.wins,
      winRate: ((session.winning_trades || tradeStats.wins) / Math.max(1, session.total_trades || tradeStats.total) * 100).toFixed(1) + '%',
      coherence: ((session.current_coherence || 0) * 100).toFixed(1) + '%',
      positions: positions.length,
    });
  }, [fetchLocalTerminalState, fetchSessionData, fetchHncState, fetchTradeStats, fetchPositions, fetchRuntimeStats]);

  useEffect(() => {
    if (!enabled) return;

    // Initial sync
    syncTerminalData();

    // Set up interval for continuous sync
    const interval = setInterval(syncTerminalData, intervalMs);

    return () => clearInterval(interval);
  }, [enabled, intervalMs, syncTerminalData]);

  return { syncNow: syncTerminalData };
}
