/**
 * Ingest Terminal State
 * Prime Sentinel: GARY LECKEY 02111991
 * 
 * Receives comprehensive terminal state from Python system
 * and updates all relevant database tables for web dashboard mirroring
 */

import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};

interface TerminalState {
  user_id: string;
  truth_status: 'live' | 'real_derived';
  source_id: string;
  source_timestamp: string;
  generated_values: false;
  
  // Portfolio
  portfolio_value: number;
  portfolio_currency: 'USD';
  peak_equity: number;
  current_drawdown: number;
  max_drawdown: number;
  
  // Trades
  trades?: Array<{
    symbol: string;
    side: string;
    price: number;
    quantity: number;
    fee: number;
    fee_asset: string;
    timestamp: string;
    transaction_id: string;
    pnl?: number;
    is_win?: boolean;
    exchange: string;
  }>;
  recent_trades?: Array<{
    time: string;
    side: string;
    symbol: string;
    quantity: number;
    pnl: number;
    success: boolean;
    hold_seconds?: number;
    reason?: string;
  }>;
  total_trades: number;
  wins: number;
  win_rate: number;
  avg_hold_time: number;
  
  // Positions
  positions?: Array<{
    symbol: string;
    side: string;
    entry_price: number;
    quantity: number;
    current_price: number;
    unrealized_pnl: number;
    exchange: string;
  }>;
  
  // Coherence/HNC/Gaia
  coherence: number;
  lambda: number;
  gaia_state: string;
  gaia_frequency: number;
  gaia_purity: number;
  gaia_carrier_phi: number;
  gaia_432_lock: number;
  hnc_frequency: number;
  hnc_market_state: string;
  hnc_coherence_percent: number;
  hnc_modifier: number;
  
  // Mycelium
  mycelium_hives: number;
  mycelium_agents: number;
  mycelium_generation: number;
  max_generation: number;
  queen_state: string;
  queen_pnl: number;
  
  // Capital
  compounded: number;
  harvested: number;
  pool_total?: number;
  pool_available: number;
  scout_count: number;
  split_count: number;
  
  // Trading Mode
  trading_mode: string;
  is_trading_active: boolean;
  entry_threshold: number;
  exit_threshold: number;
  risk_multiplier: number;
  tp_multiplier: number;
  
  // Meta
  runtime_minutes: number;
  ws_connected: boolean;
  ws_message_count: number;
  latest_monitor_line: string;
  status_lines: string[];
}

serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response(null, { headers: corsHeaders });
  }

  try {
    const supabaseUrl = Deno.env.get('SUPABASE_URL')!;
    const supabaseKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;
    const supabase = createClient(supabaseUrl, supabaseKey);

    const state: TerminalState = await req.json();

    const configuredIngestToken = Deno.env.get('AUREON_INGEST_TOKEN')?.trim();
    const suppliedIngestToken = req.headers.get('x-aureon-ingest-token')?.trim();
    if (!configuredIngestToken) throw new Error('AUREON_INGEST_TOKEN_NOT_CONFIGURED');
    if (!suppliedIngestToken || suppliedIngestToken !== configuredIngestToken) {
      return new Response(JSON.stringify({ error: 'Unauthorized' }), {
        status: 401,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }
    
    if (!state.user_id) {
      return new Response(JSON.stringify({ error: 'user_id required' }), {
        status: 400,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      });
    }
    const sourceAgeMs = Date.now() - Date.parse(state.source_timestamp);
    const requiredNumbers = [
      state.portfolio_value,
      state.peak_equity,
      state.current_drawdown,
      state.max_drawdown,
      state.total_trades,
      state.wins,
      state.win_rate,
      state.avg_hold_time,
      state.coherence,
      state.lambda,
      state.gaia_frequency,
      state.gaia_432_lock,
      state.hnc_frequency,
      state.hnc_coherence_percent,
      state.hnc_modifier,
      state.mycelium_hives,
      state.mycelium_agents,
      state.mycelium_generation,
      state.max_generation,
      state.queen_pnl,
      state.compounded,
      state.harvested,
      state.pool_available,
      state.scout_count,
      state.split_count,
      state.entry_threshold,
      state.exit_threshold,
      state.risk_multiplier,
      state.tp_multiplier,
      state.runtime_minutes,
      state.ws_message_count,
      state.gaia_purity,
      state.gaia_carrier_phi,
    ];
    if (!['live', 'real_derived'].includes(state.truth_status) || state.generated_values !== false ||
        !state.source_id || !Number.isFinite(sourceAgeMs) || sourceAgeMs < -300000 || sourceAgeMs > 300000 ||
        state.portfolio_currency !== 'USD' || state.trading_mode !== 'live' ||
        typeof state.is_trading_active !== 'boolean' || typeof state.ws_connected !== 'boolean' ||
        typeof state.latest_monitor_line !== 'string' || !Array.isArray(state.status_lines) ||
        requiredNumbers.some((value) => !Number.isFinite(Number(value)))) {
      return new Response(JSON.stringify({ error: 'REAL_FRESH_TERMINAL_STATE_REQUIRED' }), {
        status: 409,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    console.log('[IngestTerminalState] Received from Python:', {
      user_id: state.user_id,
      portfolio: state.portfolio_value,
      trades: state.total_trades,
      wins: state.wins,
      coherence: state.coherence,
      runtime: state.runtime_minutes
    });

    const now = new Date().toISOString();
    const results: Record<string, any> = {};

    // 1. Update aureon_user_sessions with all metrics
    const sessionPayload: Record<string, unknown> = {
      user_id: state.user_id,
      total_equity_usd: state.portfolio_value,
      current_coherence: state.coherence,
      current_lighthouse_signal: state.hnc_frequency,
      prism_state: state.gaia_state,
      prism_level: state.gaia_frequency,
      dominant_node: state.queen_state,
      total_trades: state.total_trades,
      winning_trades: state.wins,
      trading_mode: state.trading_mode,
      is_trading_active: state.is_trading_active,
      measurement_truth_status: state.truth_status,
      measurement_source_id: state.source_id,
      measurement_source_timestamp: state.source_timestamp,
      measurement_collected_at: now,
      measurement_generated_values: false,
      updated_at: now,
    };
    if (Number.isFinite(Number(state.lambda))) sessionPayload.current_lambda = state.lambda;
    if (Array.isArray(state.recent_trades)) sessionPayload.recent_trades = state.recent_trades;

    const { error: sessionError } = await supabase
      .from('aureon_user_sessions')
      .upsert(sessionPayload, { onConflict: 'user_id' });

    if (sessionError) {
      console.error('[IngestTerminalState] Session update error:', sessionError);
      results.session = { error: sessionError.message };
    } else {
      results.session = { updated: true };
    }

    // 2. Upsert trades if provided
    if (state.trades && state.trades.length > 0) {
      const invalidTrade = state.trades.find((trade) =>
        !trade.transaction_id || !trade.exchange || !trade.symbol || !trade.timestamp ||
        !['BUY', 'SELL'].includes(trade.side.toUpperCase()) ||
        !Number.isFinite(Number(trade.price)) || Number(trade.price) <= 0 ||
        !Number.isFinite(Number(trade.quantity)) || Number(trade.quantity) <= 0 ||
        !Number.isFinite(Number(trade.fee)) || !trade.fee_asset
      );
      if (invalidTrade) throw new Error('INCOMPLETE_PROVIDER_TRADE_RECEIPT');
      const tradeRecords = state.trades.map(t => ({
        user_id: state.user_id,
        symbol: t.symbol,
        side: t.side.toUpperCase(),
        price: t.price,
        quantity: t.quantity,
        quote_qty: t.price * t.quantity,
        fee: t.fee,
        fee_asset: t.fee_asset,
        exchange: t.exchange,
        timestamp: t.timestamp,
        transaction_id: t.transaction_id,
        pnl: t.pnl ?? null,
        is_win: t.is_win ?? null,
        truth_status: state.truth_status,
        source_id: state.source_id,
        source_timestamp: state.source_timestamp,
        generated_values: false,
      }));

      const { error: tradesError, count } = await supabase
        .from('trade_records')
        .upsert(tradeRecords, { 
          onConflict: 'transaction_id',
          ignoreDuplicates: true 
        });

      if (tradesError) {
        console.error('[IngestTerminalState] Trades upsert error:', tradesError);
        results.trades = { error: tradesError.message };
      } else {
        results.trades = { upserted: tradeRecords.length };
      }
    }

    // 3. Upsert positions if provided
    if (Array.isArray(state.positions)) {
      const invalidPosition = state.positions.find((position) =>
        !position.exchange || !position.symbol || !['LONG', 'SHORT', 'BUY', 'SELL'].includes(position.side.toUpperCase()) ||
        !Number.isFinite(Number(position.entry_price)) || Number(position.entry_price) <= 0 ||
        !Number.isFinite(Number(position.current_price)) || Number(position.current_price) <= 0 ||
        !Number.isFinite(Number(position.quantity)) || Number(position.quantity) <= 0 ||
        !Number.isFinite(Number(position.unrealized_pnl))
      );
      if (invalidPosition) throw new Error('INCOMPLETE_PROVIDER_POSITION_SNAPSHOT');

      const currentSymbols = state.positions.map(p => p.symbol);
      let closeQuery = supabase
        .from('trading_positions')
        .update({ status: 'closed', updated_at: now })
        .eq('user_id', state.user_id)
        .eq('status', 'open');
      if (currentSymbols.length > 0) {
        closeQuery = closeQuery.not('symbol', 'in', `(${currentSymbols.join(',')})`);
      }
      await closeQuery;

      // Upsert current positions
      for (const pos of state.positions) {
        const { error: posError } = await supabase
          .from('trading_positions')
          .upsert({
            user_id: state.user_id,
            symbol: pos.symbol,
            side: pos.side.toUpperCase(),
            entry_price: pos.entry_price,
            quantity: pos.quantity,
            position_value_usdt: Number(pos.current_price) * Number(pos.quantity),
            current_price: pos.current_price,
            unrealized_pnl: pos.unrealized_pnl,
            status: 'open',
            exchange: pos.exchange,
            truth_status: state.truth_status,
            source_id: state.source_id,
            source_timestamp: state.source_timestamp,
            generated_values: false,
            updated_at: now,
          }, { 
            onConflict: 'user_id,symbol',
          });

        if (posError) {
          console.error('[IngestTerminalState] Position upsert error:', posError);
        }
      }
      results.positions = { upserted: state.positions.length };
    }

    // 4. Insert HNC detection state
    const { error: hncError } = await supabase
      .from('hnc_detection_states')
      .insert({
        user_id: state.user_id,
        temporal_id: `terminal_${state.user_id}_${Date.parse(state.source_timestamp)}`,
        harmonic_fidelity: state.hnc_coherence_percent,
        imperial_yield: state.hnc_modifier,
        bridge_status: state.hnc_market_state,
        schumann_power: state.gaia_frequency,
        love_power: state.gaia_432_lock,
        anchor_power: state.coherence,
        unity_power: state.lambda,
        distortion_power: state.gaia_state === 'DISTORTION' ? 1 : 0,
        is_lighthouse_detected: state.coherence > 0.45,
        timestamp: state.source_timestamp,
        truth_status: state.truth_status,
        source_id: state.source_id,
        source_timestamp: state.source_timestamp,
        generated_values: false,
      });

    if (hncError) {
      console.error('[IngestTerminalState] HNC insert error:', hncError);
      results.hnc = { error: hncError.message };
    } else {
      results.hnc = { inserted: true };
    }

    // 5. Store runtime/mycelium state in a system stats record
    const runtimeStats = {
      user_id: state.user_id,
      runtime_minutes: state.runtime_minutes,
      peak_equity: state.peak_equity,
      current_drawdown: state.current_drawdown,
      max_drawdown: state.max_drawdown,
      avg_hold_time_minutes: state.avg_hold_time,
      mycelium_hives: state.mycelium_hives,
      mycelium_agents: state.mycelium_agents,
      mycelium_generation: state.mycelium_generation,
      max_generation: state.max_generation,
      queen_state: state.queen_state,
      queen_pnl: state.queen_pnl,
      scout_count: state.scout_count,
      split_count: state.split_count,
      entry_threshold: state.entry_threshold,
      exit_threshold: state.exit_threshold,
      risk_multiplier: state.risk_multiplier,
      tp_multiplier: state.tp_multiplier,
      ws_connected: state.ws_connected,
      ws_message_count: state.ws_message_count,
      gaia_purity: state.gaia_purity,
      gaia_carrier_phi: state.gaia_carrier_phi,
      latest_monitor_line: state.latest_monitor_line,
      status_lines: state.status_lines,
      source_timestamp: state.source_timestamp,
      truth_status: state.truth_status,
      generated_values: false,
    };

    // Store in local_system_logs as JSON for now (can create dedicated table later)
    const { error: statsError } = await supabase
      .from('aureon_runtime_observations')
      .insert({
        user_id: state.user_id,
        payload: runtimeStats,
        truth_status: state.truth_status,
        source_id: state.source_id,
        source_timestamp: state.source_timestamp,
        collected_at: now,
        generated_values: false,
      });

    if (statsError) {
      console.error('[IngestTerminalState] Stats insert error:', statsError);
      results.stats = { error: statsError.message };
    } else {
      results.stats = { inserted: true };
    }

    console.log('[IngestTerminalState] Completed:', results);

    const failedComponents = Object.entries(results)
      .filter(([, value]) => Boolean((value as any)?.error))
      .map(([name]) => name);

    return new Response(JSON.stringify({
      success: failedComponents.length === 0,
      timestamp: now,
      results,
      failedComponents,
      truthStatus: state.truth_status,
      sourceId: state.source_id,
      sourceTimestamp: state.source_timestamp,
      generatedValues: false,
    }), {
      status: failedComponents.length === 0 ? 200 : 500,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });

  } catch (error) {
    console.error('[IngestTerminalState] Error:', error);
    return new Response(JSON.stringify({
      success: false,
      error: error instanceof Error ? error.message : String(error),
      truthStatus: 'no_data',
      generatedValues: false,
    }), {
      status: 500,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });
  }
});
