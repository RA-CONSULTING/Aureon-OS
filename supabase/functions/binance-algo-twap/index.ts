import { serve } from 'https://deno.land/std@0.168.0/http/server.ts';
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';
import { createHmac } from 'https://deno.land/std@0.177.0/node/crypto.ts';
import { decryptCredential } from '../_shared/credential_crypto.ts';
import { fetchLiveJson, requireFiniteNumber, requireFreshTimestamp } from '../_shared/real_data.ts';

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};
const BINANCE_BASE = 'https://api.binance.com';
const MAX_SOURCE_AGE_MS = 5 * 60 * 1000;

function signRequest(query: string, secret: string): string {
  return createHmac('sha256', secret).update(query).digest('hex');
}

function positive(value: unknown, name: string): number {
  const numberValue = requireFiniteNumber(value, name);
  if (numberValue <= 0) throw new Error(`${name.toUpperCase()}_MUST_BE_POSITIVE`);
  return numberValue;
}

function signedQuery(params: Record<string, string | number>, secret: string): string {
  const query = new URLSearchParams(Object.entries(params).map(([key, value]) => [key, String(value)])).toString();
  return `${query}&signature=${signRequest(query, secret)}`;
}

async function providerTime(): Promise<{ timestamp: number; sourceTimestamp: string }> {
  const payload = await fetchLiveJson<{ serverTime: number }>(`${BINANCE_BASE}/api/v3/time`);
  const timestamp = positive(payload.serverTime, 'binance.serverTime');
  const sourceTimestamp = new Date(timestamp).toISOString();
  requireFreshTimestamp(sourceTimestamp, MAX_SOURCE_AGE_MS, 'binance.serverTime');
  return { timestamp, sourceTimestamp };
}

async function authenticatedBinance(
  req: Request,
): Promise<{
  userId: string;
  apiKey: string;
  apiSecret: string;
  supabase: any;
}> {
  const supabaseUrl = Deno.env.get('SUPABASE_URL')?.trim();
  const serviceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')?.trim();
  const anonKey = Deno.env.get('SUPABASE_ANON_KEY')?.trim();
  if (!supabaseUrl || !serviceKey || !anonKey) throw new Error('SUPABASE_RUNTIME_NOT_CONFIGURED');
  const token = req.headers.get('Authorization')?.replace(/^Bearer\s+/i, '');
  if (!token) throw new Error('AUTHENTICATION_REQUIRED');
  const authClient = createClient(supabaseUrl, anonKey);
  const { data: { user }, error: authError } = await authClient.auth.getUser(token);
  if (authError || !user) throw new Error('INVALID_AUTHENTICATION');

  const supabase = createClient(supabaseUrl, serviceKey);
  const { data: session, error: sessionError } = await supabase
    .from('aureon_user_sessions')
    .select('is_trading_active, trading_mode, binance_api_key_encrypted, binance_api_secret_encrypted, binance_iv')
    .eq('user_id', user.id)
    .single();
  if (sessionError || !session) throw new Error('USER_TRADING_SESSION_NOT_FOUND');
  if (session.is_trading_active !== true || session.trading_mode !== 'live') {
    throw new Error('PRODUCTION_LIVE_MODE_REQUIRED');
  }
  const apiKey = await decryptCredential(session.binance_api_key_encrypted, session.binance_iv || '');
  const apiSecret = await decryptCredential(session.binance_api_secret_encrypted, session.binance_iv || '');
  return { userId: user.id, apiKey, apiSecret, supabase };
}

async function binanceRequest(
  path: string,
  method: 'GET' | 'POST' | 'DELETE',
  params: Record<string, string | number>,
  apiKey: string,
  apiSecret: string,
): Promise<any> {
  const response = await fetch(`${BINANCE_BASE}${path}?${signedQuery(params, apiSecret)}`, {
    method,
    headers: { 'X-MBX-APIKEY': apiKey },
  });
  const payload = await response.json().catch(() => null);
  if (!response.ok || payload?.success === false || payload?.code < 0) {
    throw new Error(`BINANCE_TWAP_HTTP_${response.status}:${payload?.code ?? 'unknown'}`);
  }
  return payload;
}

serve(async (req) => {
  if (req.method === 'OPTIONS') return new Response(null, { headers: corsHeaders });

  try {
    const { userId, apiKey, apiSecret, supabase } = await authenticatedBinance(req);
    const body = await req.json();
    const action = String(body.action || '');

    if (action === 'place') {
      if (body.liveExecutionConfirmed !== true) throw new Error('LIVE_EXECUTION_CONFIRMATION_REQUIRED');
      if (body.truthStatus !== 'real_derived' || body.generatedValues !== false || !String(body.sourceId || '').trim()) {
        throw new Error('FRESH_REAL_MARKET_PROVENANCE_REQUIRED');
      }
      requireFreshTimestamp(String(body.sourceTimestamp || ''), MAX_SOURCE_AGE_MS, 'sourceTimestamp');
      const symbol = String(body.symbol || '').toUpperCase();
      const side = String(body.side || '').toUpperCase();
      if (!/^[A-Z0-9]{5,20}$/.test(symbol) || !['BUY', 'SELL'].includes(side)) {
        throw new Error('INVALID_TWAP_SYMBOL_OR_SIDE');
      }
      const quantity = positive(body.quantity, 'quantity');
      const duration = positive(body.duration, 'duration');
      if (!Number.isInteger(duration)) throw new Error('DURATION_MUST_BE_INTEGER_SECONDS');
      const requestedLimit = body.limitPrice == null ? null : positive(body.limitPrice, 'limitPrice');

      const ticker = await fetchLiveJson<any>(`${BINANCE_BASE}/api/v3/ticker/24hr?symbol=${encodeURIComponent(symbol)}`);
      const providerPrice = positive(ticker.lastPrice, 'binance.lastPrice');
      const tickerTimestamp = new Date(positive(ticker.closeTime, 'binance.closeTime')).toISOString();
      requireFreshTimestamp(tickerTimestamp, MAX_SOURCE_AGE_MS, 'binance.closeTime');
      const maxDeviationBps = positive(Deno.env.get('EXECUTION_MAX_PRICE_DEVIATION_BPS'), 'EXECUTION_MAX_PRICE_DEVIATION_BPS');
      if (requestedLimit !== null && Math.abs(requestedLimit - providerPrice) / providerPrice * 10_000 > maxDeviationBps) {
        throw new Error('TWAP_LIMIT_PRICE_DOES_NOT_MATCH_LIVE_BINANCE_PRICE');
      }

      if (body.huntSessionId) {
        const { data: hunt, error: huntError } = await supabase.from('hunt_sessions')
          .select('id').eq('id', body.huntSessionId).eq('user_id', userId).single();
        if (huntError || !hunt) throw new Error('HUNT_SESSION_NOT_FOUND_OR_UNAUTHORIZED');
      }

      const clientAlgoId = crypto.randomUUID().replace(/-/g, '');
      const clock = await providerTime();
      const params: Record<string, string | number> = {
        symbol,
        side,
        quantity,
        duration,
        clientAlgoId,
        timestamp: clock.timestamp,
      };
      if (requestedLimit !== null) params.limitPrice = requestedLimit;
      const receipt = await binanceRequest('/sapi/v1/algo/spot/newOrderTwap', 'POST', params, apiKey, apiSecret);
      const acceptedAt = await providerTime();
      const algoId = receipt.algoId == null ? null : positive(receipt.algoId, 'binance.algoId');

      const { data: twapOrder, error: insertError } = await supabase.from('twap_orders').insert({
        user_id: userId,
        client_algo_id: String(receipt.clientAlgoId || clientAlgoId),
        algo_id: algoId,
        hunt_session_id: body.huntSessionId ?? null,
        oms_order_id: body.omsOrderId ?? null,
        symbol,
        side,
        total_quantity: quantity,
        duration_seconds: duration,
        limit_price: requestedLimit,
        algo_status: String(receipt.algoStatus || receipt.status || 'ACCEPTED'),
        book_time: acceptedAt.sourceTimestamp,
        truth_status: 'live',
        source_id: 'binance:/sapi/v1/algo/spot/newOrderTwap',
        source_timestamp: acceptedAt.sourceTimestamp,
        generated_values: false,
      }).select().single();
      if (insertError || !twapOrder) throw new Error(`TWAP_RECEIPT_PERSIST_FAILED:${insertError?.message || 'no row'}`);

      return new Response(JSON.stringify({
        success: true,
        twapOrderId: twapOrder.id,
        clientAlgoId: twapOrder.client_algo_id,
        algoId: twapOrder.algo_id,
        algoStatus: twapOrder.algo_status,
        truthStatus: 'live',
        sourceId: twapOrder.source_id,
        sourceTimestamp: twapOrder.source_timestamp,
        generatedValues: false,
      }), { headers: { ...corsHeaders, 'Content-Type': 'application/json' } });
    }

    if (!['sync', 'cancel'].includes(action)) throw new Error(`UNKNOWN_ACTION:${action}`);
    const twapOrderId = String(body.twapOrderId || '');
    const { data: twapOrder, error: fetchError } = await supabase.from('twap_orders')
      .select('*').eq('id', twapOrderId).eq('user_id', userId).single();
    if (fetchError || !twapOrder?.algo_id) throw new Error('TWAP_ORDER_NOT_FOUND_OR_UNAUTHORIZED');

    const clock = await providerTime();
    if (action === 'cancel') {
      const receipt = await binanceRequest('/sapi/v1/algo/spot/order', 'DELETE', {
        algoId: twapOrder.algo_id,
        timestamp: clock.timestamp,
      }, apiKey, apiSecret);
      const providerReceiptTime = await providerTime();
      const { error: updateError } = await supabase.from('twap_orders').update({
        algo_status: String(receipt.algoStatus || receipt.status || 'CANCELLED'),
        end_time: providerReceiptTime.sourceTimestamp,
        source_id: 'binance:/sapi/v1/algo/spot/order:DELETE',
        source_timestamp: providerReceiptTime.sourceTimestamp,
        truth_status: 'live',
        generated_values: false,
      }).eq('id', twapOrderId).eq('user_id', userId);
      if (updateError) throw new Error(`TWAP_CANCEL_RECEIPT_PERSIST_FAILED:${updateError.message}`);
      return new Response(JSON.stringify({
        success: true,
        algoStatus: String(receipt.algoStatus || receipt.status || 'CANCELLED'),
        truthStatus: 'live',
        sourceId: 'binance:/sapi/v1/algo/spot/order:DELETE',
        sourceTimestamp: providerReceiptTime.sourceTimestamp,
        generatedValues: false,
      }), { headers: { ...corsHeaders, 'Content-Type': 'application/json' } });
    }

    const receipt = await binanceRequest('/sapi/v1/algo/spot/subOrders', 'GET', {
      algoId: twapOrder.algo_id,
      timestamp: clock.timestamp,
    }, apiKey, apiSecret);
    const providerReceiptTime = await providerTime();
    const rows = Array.isArray(receipt.subOrders) ? receipt.subOrders : [];
    const inserts = rows.map((sub: any) => {
      const sourceTimestamp = new Date(positive(sub.bookTime, 'subOrder.bookTime')).toISOString();
      requireFreshTimestamp(sourceTimestamp, 365 * 24 * 60 * 60 * 1000, 'subOrder.bookTime');
      return {
        user_id: userId,
        twap_order_id: twapOrderId,
        sub_id: String(sub.subId),
        order_id: String(sub.orderId),
        symbol: String(sub.symbol),
        side: String(sub.side),
        order_status: String(sub.orderStatus),
        executed_quantity: requireFiniteNumber(sub.executedQty, 'subOrder.executedQty'),
        executed_amount: requireFiniteNumber(sub.executedAmt, 'subOrder.executedAmt'),
        orig_quantity: positive(sub.origQty, 'subOrder.origQty'),
        avg_price: sub.avgPrice == null ? null : requireFiniteNumber(sub.avgPrice, 'subOrder.avgPrice'),
        fee_amount: sub.feeAmt == null ? null : requireFiniteNumber(sub.feeAmt, 'subOrder.feeAmt'),
        fee_asset: sub.feeAsset == null ? null : String(sub.feeAsset),
        book_time: sourceTimestamp,
        time_in_force: sub.timeInForce == null ? null : String(sub.timeInForce),
        truth_status: 'live',
        source_id: 'binance:/sapi/v1/algo/spot/subOrders',
        source_timestamp: sourceTimestamp,
        generated_values: false,
      };
    });
    if (inserts.length > 0) {
      const { error: upsertError } = await supabase.from('twap_sub_orders').upsert(inserts, {
        onConflict: 'twap_order_id,sub_id',
      });
      if (upsertError) throw new Error(`TWAP_SUBORDER_RECEIPT_PERSIST_FAILED:${upsertError.message}`);
    }

    const executedQuantity = receipt.executedQty == null
      ? null
      : requireFiniteNumber(receipt.executedQty, 'receipt.executedQty');
    const executedAmount = receipt.executedAmt == null
      ? null
      : requireFiniteNumber(receipt.executedAmt, 'receipt.executedAmt');
    const { error: updateError } = await supabase.from('twap_orders').update({
      executed_quantity: executedQuantity,
      executed_amount: executedAmount,
      avg_price: executedQuantity !== null && executedAmount !== null && executedQuantity > 0
        ? executedAmount / executedQuantity
        : null,
      algo_status: String(receipt.algoStatus || receipt.status || twapOrder.algo_status),
      source_id: 'binance:/sapi/v1/algo/spot/subOrders',
      source_timestamp: providerReceiptTime.sourceTimestamp,
      truth_status: 'live',
      generated_values: false,
      updated_at: providerReceiptTime.sourceTimestamp,
    }).eq('id', twapOrderId).eq('user_id', userId);
    if (updateError) throw new Error(`TWAP_SYNC_RECEIPT_PERSIST_FAILED:${updateError.message}`);

    return new Response(JSON.stringify({
      success: true,
      subOrdersCount: rows.length,
      executedQuantity,
      executedAmount,
      truthStatus: 'live',
      sourceId: 'binance:/sapi/v1/algo/spot/subOrders',
      sourceTimestamp: providerReceiptTime.sourceTimestamp,
      generatedValues: false,
    }), { headers: { ...corsHeaders, 'Content-Type': 'application/json' } });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    return new Response(JSON.stringify({
      success: false,
      error: message,
      truthStatus: 'no_data',
      generatedValues: false,
    }), {
      status: /AUTHENTICATION/.test(message) ? 401 : 409,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    });
  }
});
