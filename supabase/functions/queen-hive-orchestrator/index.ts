import { serve } from 'https://deno.land/std@0.168.0/http/server.ts';
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};

const SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'DOGEUSDT'];
const AGENTS_PER_HIVE = SYMBOLS.length;
const SOURCE_MAX_AGE_MS = 5 * 60 * 1000;

type NativeSignal = {
  id: string;
  signal_type: string;
  tier: number;
  strength: number;
  confidence: number;
  lighthouse_l: number;
  cross_scale_coherence: number;
  metadata: Record<string, unknown>;
  created_at: string;
  truth_status: 'real_derived';
  source_id: string;
  source_timestamp: string;
  generated_values: false;
};

function freshTimestamp(value: unknown): string | null {
  const timestamp = String(value || '');
  const age = Date.now() - Date.parse(timestamp);
  return Number.isFinite(age) && age >= -300000 && age <= SOURCE_MAX_AGE_MS ? timestamp : null;
}

function finitePositive(value: unknown): number | null {
  const numberValue = Number(value);
  return Number.isFinite(numberValue) && numberValue > 0 ? numberValue : null;
}

function finiteNonNegative(value: unknown): number | null {
  const numberValue = Number(value);
  return Number.isFinite(numberValue) && numberValue >= 0 ? numberValue : null;
}

function decimalPlaces(step: number): number {
  const text = step.toFixed(12).replace(/0+$/, '');
  const dot = text.indexOf('.');
  return dot === -1 ? 0 : text.length - dot - 1;
}

function floorToStep(value: number, step: number): number {
  const precision = decimalPlaces(step);
  return Number((Math.floor(value / step) * step).toFixed(precision));
}

async function invokeOms(
  supabaseUrl: string,
  anonKey: string,
  authorization: string,
  body: Record<string, unknown>,
): Promise<any> {
  const response = await fetch(`${supabaseUrl}/functions/v1/oms-leaky-bucket`, {
    method: 'POST',
    headers: {
      Authorization: authorization,
      apikey: anonKey,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  });
  const payload = await response.json();
  if (!response.ok || payload?.success !== true) {
    throw new Error(`OMS_${String(body.action).toUpperCase()}_FAILED:${payload?.error || response.status}`);
  }
  return payload;
}

serve(async (req) => {
  if (req.method === 'OPTIONS') return new Response(null, { headers: corsHeaders });

  try {
    const supabaseUrl = Deno.env.get('SUPABASE_URL')?.trim();
    const serviceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')?.trim();
    const anonKey = Deno.env.get('SUPABASE_ANON_KEY')?.trim();
    if (!supabaseUrl || !serviceKey || !anonKey) throw new Error('SUPABASE_RUNTIME_NOT_CONFIGURED');

    const authorization = req.headers.get('Authorization');
    const token = authorization?.replace(/^Bearer\s+/i, '');
    if (!authorization || !token) throw new Error('AUTHENTICATION_REQUIRED');

    const supabase = createClient(supabaseUrl, serviceKey);
    const { data: { user }, error: userError } = await supabase.auth.getUser(token);
    if (userError || !user) throw new Error('INVALID_AUTHENTICATION');

    const body = await req.json();
    const action = String(body.action || '');

    if (action === 'start') {
      if (body.liveExecutionConfirmed !== true) throw new Error('EXPLICIT_LIVE_EXECUTION_CONFIRMATION_REQUIRED');

      const requestedCapital = finitePositive(body.initialCapital);
      if (requestedCapital === null) throw new Error('POSITIVE_CAPITAL_ALLOCATION_REQUIRED');

      const { data: observedSession, error: observedError } = await supabase
        .from('aureon_user_sessions')
        .select('total_equity_usd, measurement_truth_status, measurement_source_id, measurement_source_timestamp, measurement_generated_values')
        .eq('user_id', user.id)
        .single();
      const balanceTimestamp = freshTimestamp(observedSession?.measurement_source_timestamp);
      const liveEquity = finiteNonNegative(observedSession?.total_equity_usd);
      if (observedError || !observedSession || !balanceTimestamp || liveEquity === null ||
          !['live', 'real_derived'].includes(String(observedSession.measurement_truth_status)) ||
          observedSession.measurement_generated_values !== false) {
        throw new Error('FRESH_LIVE_EQUITY_SYNC_REQUIRED');
      }
      if (requestedCapital > liveEquity) throw new Error('CAPITAL_ALLOCATION_EXCEEDS_LIVE_EQUITY');

      const { data: rootHive, error: hiveError } = await supabase
        .from('hive_instances')
        .insert({
          generation: 0,
          initial_balance: requestedCapital,
          current_balance: requestedCapital,
          num_agents: AGENTS_PER_HIVE,
          status: 'active',
        })
        .select()
        .single();
      if (hiveError || !rootHive) throw new Error(`HIVE_CREATE_FAILED:${hiveError?.message || 'no row'}`);

      const agents = SYMBOLS.map((symbol, index) => ({
        hive_id: rootHive.id,
        agent_index: index,
        current_symbol: symbol,
        position_open: false,
      }));
      const { error: agentsError } = await supabase.from('hive_agents').insert(agents);
      if (agentsError) {
        await supabase.from('hive_instances').delete().eq('id', rootHive.id);
        throw new Error(`HIVE_AGENT_CREATE_FAILED:${agentsError.message}`);
      }

      const { data: hiveSession, error: sessionError } = await supabase
        .from('hive_sessions')
        .insert({
          user_id: user.id,
          root_hive_id: rootHive.id,
          initial_capital: requestedCapital,
          current_equity: liveEquity,
          status: 'running',
        })
        .select()
        .single();
      if (sessionError || !hiveSession) {
        await supabase.from('hive_instances').delete().eq('id', rootHive.id);
        throw new Error(`HIVE_SESSION_CREATE_FAILED:${sessionError?.message || 'no row'}`);
      }

      return new Response(JSON.stringify({
        success: true,
        session: hiveSession,
        message: 'Queen-Hive connected to fresh live equity and native QGITA routing',
        truthStatus: 'real_derived',
        sourceId: observedSession.measurement_source_id,
        sourceTimestamp: balanceTimestamp,
        generatedValues: false,
      }), { headers: { ...corsHeaders, 'Content-Type': 'application/json' } });
    }

    const sessionId = String(body.sessionId || '');
    if (!sessionId) throw new Error('SESSION_ID_REQUIRED');
    const { data: hiveSession, error: sessionError } = await supabase
      .from('hive_sessions')
      .select('*')
      .eq('id', sessionId)
      .eq('user_id', user.id)
      .single();
    if (sessionError || !hiveSession) throw new Error('SESSION_NOT_FOUND_OR_UNAUTHORIZED');

    if (action === 'stop') {
      const stoppedAt = new Date().toISOString();
      const { data: ownedHives, error: ownedHivesError } = await supabase
        .from('hive_instances')
        .select('id')
        .or(`id.eq.${hiveSession.root_hive_id},parent_hive_id.eq.${hiveSession.root_hive_id}`);
      if (ownedHivesError || !ownedHives) throw new Error('HIVE_STOP_SCOPE_READ_FAILED');
      const ownedHiveIds = ownedHives.map((row: any) => row.id);
      const { error: stopError } = await supabase
        .from('hive_sessions')
        .update({ status: 'stopped', stopped_at: stoppedAt })
        .eq('id', sessionId)
        .eq('user_id', user.id);
      if (stopError) throw new Error(`HIVE_STOP_FAILED:${stopError.message}`);
      const { error: hivesStopError } = await supabase
        .from('hive_instances').update({ status: 'stopped' }).in('id', ownedHiveIds);
      if (hivesStopError) throw new Error(`HIVE_INSTANCES_STOP_FAILED:${hivesStopError.message}`);
      const { error: cancelError } = await supabase.from('oms_order_queue').update({ status: 'cancelled', cancelled_at: stoppedAt })
        .eq('session_id', sessionId).eq('status', 'queued');
      if (cancelError) throw new Error(`HIVE_QUEUE_CANCEL_FAILED:${cancelError.message}`);
      return new Response(JSON.stringify({
        success: true,
        stoppedAt,
        truthStatus: 'live',
        sourceId: 'supabase:hive_sessions,oms_order_queue',
        sourceTimestamp: stoppedAt,
        generatedValues: false,
      }), { headers: { ...corsHeaders, 'Content-Type': 'application/json' } });
    }

    const { data: hives, error: hivesError } = await supabase
      .from('hive_instances')
      .select('*')
      .or(`id.eq.${hiveSession.root_hive_id},parent_hive_id.eq.${hiveSession.root_hive_id}`);
    if (hivesError || !hives) throw new Error(`HIVE_READ_FAILED:${hivesError?.message || 'no rows'}`);
    const hiveIds = hives.map((hive: any) => hive.id);
    const { data: agents, error: agentsError } = await supabase
      .from('hive_agents')
      .select('*')
      .in('hive_id', hiveIds);
    if (agentsError || !agents) throw new Error(`HIVE_AGENT_READ_FAILED:${agentsError?.message || 'no rows'}`);

    if (action === 'status') {
      const { data: observedSession, error: observedError } = await supabase
        .from('aureon_user_sessions')
        .select('total_equity_usd, measurement_truth_status, measurement_source_id, measurement_source_timestamp, measurement_generated_values')
        .eq('user_id', user.id)
        .single();
      const sourceTimestamp = freshTimestamp(observedSession?.measurement_source_timestamp);
      const liveEquity = finiteNonNegative(observedSession?.total_equity_usd);
      if (observedError || !sourceTimestamp || liveEquity === null ||
          !['live', 'real_derived'].includes(String(observedSession?.measurement_truth_status)) ||
          observedSession?.measurement_generated_values !== false) {
        throw new Error('FRESH_LIVE_EQUITY_SYNC_REQUIRED');
      }
      const { data: refreshedSession, error: refreshError } = await supabase
        .from('hive_sessions')
        .update({ current_equity: liveEquity })
        .eq('id', sessionId)
        .select()
        .single();
      if (refreshError || !refreshedSession) throw new Error('HIVE_EQUITY_REFRESH_FAILED');
      return new Response(JSON.stringify({
        success: true,
        session: refreshedSession,
        hives,
        agents,
        truthStatus: 'real_derived',
        sourceId: observedSession.measurement_source_id,
        sourceTimestamp,
        generatedValues: false,
      }), { headers: { ...corsHeaders, 'Content-Type': 'application/json' } });
    }

    if (action === 'step') {
      if (hiveSession.status !== 'running') throw new Error('HIVE_SESSION_NOT_RUNNING');
      const maxOrderUsd = finitePositive(Deno.env.get('QUEEN_HIVE_MAX_ORDER_USD'));
      const maxEquityFraction = finitePositive(Deno.env.get('QUEEN_HIVE_MAX_EQUITY_FRACTION'));
      if (maxOrderUsd === null || maxEquityFraction === null || maxEquityFraction > 1) {
        throw new Error('QUEEN_HIVE_LIVE_POSITION_LIMITS_NOT_CONFIGURED');
      }

      const cutoff = new Date(Date.now() - SOURCE_MAX_AGE_MS).toISOString();
      const { data: signalRows, error: signalError } = await supabase
        .from('qgita_signal_states')
        .select('id, signal_type, tier, strength, confidence, lighthouse_l, cross_scale_coherence, metadata, created_at, truth_status, source_id, source_timestamp, generated_values')
        .eq('user_id', user.id)
        .eq('truth_status', 'real_derived')
        .eq('generated_values', false)
        .gte('source_timestamp', cutoff)
        .order('source_timestamp', { ascending: false })
        .limit(1000);
      if (signalError) throw new Error(`QGITA_SIGNAL_READ_FAILED:${signalError.message}`);

      const tickerResponse = await fetch('https://api.binance.com/api/v3/ticker/24hr');
      if (!tickerResponse.ok) throw new Error(`BINANCE_TICKER_HTTP_${tickerResponse.status}`);
      const tickerRows = await tickerResponse.json();
      const tickerBySymbol = new Map<string, { price: number; sourceTimestamp: string }>();
      for (const row of tickerRows as any[]) {
        const symbol = String(row.symbol);
        const price = Number(row.lastPrice);
        const closeTime = Number(row.closeTime);
        const sourceTimestamp = new Date(closeTime).toISOString();
        if (SYMBOLS.includes(symbol) && Number.isFinite(price) && price > 0 &&
            Number.isFinite(closeTime) && freshTimestamp(sourceTimestamp)) {
          tickerBySymbol.set(symbol, { price, sourceTimestamp });
        }
      }

      const exchangeInfoResponse = await fetch(`https://api.binance.com/api/v3/exchangeInfo?symbols=${encodeURIComponent(JSON.stringify(SYMBOLS))}`);
      if (!exchangeInfoResponse.ok) throw new Error(`BINANCE_EXCHANGE_INFO_HTTP_${exchangeInfoResponse.status}`);
      const exchangeInfo = await exchangeInfoResponse.json();
      const rulesBySymbol = new Map<string, any>((exchangeInfo.symbols || []).map((row: any) => [row.symbol, row]));

      const latestBySymbol = new Map<string, NativeSignal>();
      for (const signal of (signalRows || []) as NativeSignal[]) {
        const symbol = String(signal.metadata?.symbol || '').toUpperCase();
        const sourceTimestamp = freshTimestamp(signal.source_timestamp);
        if (!SYMBOLS.includes(symbol) || latestBySymbol.has(symbol) || !sourceTimestamp ||
            signal.truth_status !== 'real_derived' || signal.generated_values !== false || !signal.source_id) continue;
        latestBySymbol.set(symbol, signal);
      }

      const queued: any[] = [];
      const skipped: any[] = [];
      for (const agent of agents) {
        const symbol = String(agent.current_symbol).toUpperCase();
        const signal = latestBySymbol.get(symbol);
        if (!signal) {
          skipped.push({ agentId: agent.id, symbol, reason: 'NO_FRESH_NATIVE_QGITA_SIGNAL' });
          continue;
        }
        const side = String(signal.signal_type).toUpperCase();
        const tier = Number(signal.tier);
        const coherence = Number(signal.cross_scale_coherence);
        const strength = Number(signal.strength);
        const confidenceRaw = Number(signal.confidence);
        const lighthouseValue = Number(signal.lighthouse_l);
        const sourceTimestamp = String(signal.source_timestamp);
        if (!['BUY', 'SELL'].includes(side) || !Number.isFinite(tier) || tier > 2 ||
            ![coherence, strength, confidenceRaw, lighthouseValue].every(Number.isFinite)) {
          skipped.push({ agentId: agent.id, symbol, reason: 'NATIVE_QGITA_NO_ACTION' });
          continue;
        }

        const ticker = tickerBySymbol.get(symbol);
        const price = ticker?.price;
        const symbolRules = rulesBySymbol.get(symbol);
        const lotSize = symbolRules?.filters?.find((filter: any) => filter.filterType === 'LOT_SIZE');
        const notionalRule = symbolRules?.filters?.find((filter: any) => ['NOTIONAL', 'MIN_NOTIONAL'].includes(filter.filterType));
        const stepSize = finitePositive(lotSize?.stepSize);
        const minQuantity = finitePositive(lotSize?.minQty);
        const minNotional = finitePositive(notionalRule?.minNotional);
        if (!price || !ticker || stepSize === null || minQuantity === null || minNotional === null) {
          skipped.push({ agentId: agent.id, symbol, reason: 'BINANCE_SYMBOL_RULES_MISSING' });
          continue;
        }

        const confidence = confidenceRaw > 1 ? confidenceRaw / 100 : confidenceRaw;
        const coherenceScale = Math.max(0, Math.min(1, coherence));
        const confidenceScale = Math.max(0, Math.min(1, confidence));
        const hive = hives.find((row: any) => row.id === agent.hive_id);
        const allocatedBalance = finitePositive(hive?.current_balance);
        if (allocatedBalance === null) {
          skipped.push({ agentId: agent.id, symbol, reason: 'LIVE_HIVE_ALLOCATION_MISSING' });
          continue;
        }
        const orderUsd = Math.min(maxOrderUsd, allocatedBalance * maxEquityFraction) * coherenceScale * confidenceScale;
        const quantity = floorToStep(orderUsd / price, stepSize);
        if (quantity < minQuantity || quantity * price < minNotional) {
          skipped.push({ agentId: agent.id, symbol, reason: 'ORDER_BELOW_LIVE_EXCHANGE_MINIMUM' });
          continue;
        }

        const priority = Math.max(0, Math.min(100, Math.round(confidenceScale * 100)));
        try {
          const oms = await invokeOms(supabaseUrl, anonKey, authorization, {
            action: 'enqueue',
            sessionId,
            hiveId: agent.hive_id,
            agentId: agent.id,
            symbol,
            side,
            quantity,
            price,
            priority,
            metadata: {
              signalStrength: strength,
              coherence,
              lighthouseValue,
              qgitaSignalId: signal.id,
              truthStatus: 'real_derived',
              sourceId: `qgita_signal:${signal.id}:${signal.source_id}+binance:/api/v3/ticker/24hr`,
              sourceTimestamp: [sourceTimestamp, ticker.sourceTimestamp].sort()[0],
              marketSourceId: 'binance:/api/v3/ticker/24hr',
              marketSourceTimestamp: ticker.sourceTimestamp,
              generatedValues: false,
            },
          });
          queued.push({ agentId: agent.id, symbol, side, quantity, price, orderId: oms.orderId, qgitaSignalId: signal.id });
        } catch (error) {
          const message = error instanceof Error ? error.message : String(error);
          if (/duplicate|unique/i.test(message)) skipped.push({ agentId: agent.id, symbol, reason: 'SIGNAL_ALREADY_ROUTED' });
          else throw error;
        }
      }

      const execution = queued.length > 0
        ? await invokeOms(supabaseUrl, anonKey, authorization, { action: 'process' })
        : {
            processed: 0,
            failed: 0,
            results: [],
            truthStatus: 'no_data',
            sourceId: 'qgita_signal_states',
            sourceTimestamp: signalRows?.[0]?.source_timestamp ?? null,
            generatedValues: false,
          };
      const stepTimestamp = new Date().toISOString();
      const { data: updatedSession, error: updateError } = await supabase
        .from('hive_sessions')
        .update({
          steps_executed: Number(hiveSession.steps_executed ?? 0) + 1,
          total_trades: Number(hiveSession.total_trades ?? 0) + Number(execution.processed ?? 0),
          last_step_at: stepTimestamp,
        })
        .eq('id', sessionId)
        .select()
        .single();
      if (updateError || !updatedSession) throw new Error(`HIVE_STEP_UPDATE_FAILED:${updateError?.message || 'no row'}`);

      return new Response(JSON.stringify({
        success: true,
        step: updatedSession.steps_executed,
        trades: Number(execution.processed ?? 0),
        equity: Number(updatedSession.current_equity),
        hives: hives.length,
        agents: agents.length,
        queued,
        skipped,
        execution,
        truthStatus: 'real_derived',
        sourceId: 'qgita_signal_states,binance:/api/v3/ticker/24hr,/api/v3/exchangeInfo,/api/v3/order',
        sourceTimestamp: Array.from(tickerBySymbol.values()).map((row) => row.sourceTimestamp).sort()[0] ?? null,
        generatedValues: false,
      }), { headers: { ...corsHeaders, 'Content-Type': 'application/json' } });
    }

    throw new Error(`UNKNOWN_ACTION:${action}`);
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    console.error('[queen-hive-orchestrator] Error:', message);
    return new Response(JSON.stringify({
      success: false,
      error: message,
      truthStatus: 'no_data',
      generatedValues: false,
    }), { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } });
  }
});
