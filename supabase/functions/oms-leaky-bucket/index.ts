import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";
import { createHmac } from "node:crypto";
import { decryptCredential } from "../_shared/credential_crypto.ts";

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};

serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response(null, { headers: corsHeaders });
  }

  try {
    const supabaseUrl = Deno.env.get('SUPABASE_URL')!;
    const supabaseKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;
    const supabase = createClient(supabaseUrl, supabaseKey);

    const authHeader = req.headers.get('Authorization');
    if (!authHeader) {
      throw new Error('Missing authorization header');
    }

    const token = authHeader.replace('Bearer ', '');
    const { data: { user }, error: userError } = await supabase.auth.getUser(token);
    if (userError || !user) {
      throw new Error('Unauthorized');
    }

    const { action, ...params } = await req.json();
    console.log(`OMS ${action} request:`, { user: user.id, params });

    if (action === 'enqueue') {
      // === ADD ORDER TO QUEUE ===
      const { sessionId, hiveId, agentId, symbol, side, quantity, price, priority, metadata } = params;

      if (!sessionId || !hiveId || !agentId || !symbol || !side || !quantity || !price ||
          !Number.isInteger(Number(priority)) || Number(priority) < 0 || Number(priority) > 100) {
        throw new Error('Missing required order parameters');
      }
      const sourceTimestamp = String(metadata?.sourceTimestamp || '');
      const sourceAgeMs = Date.now() - Date.parse(sourceTimestamp);
      if (!['live', 'real_derived'].includes(metadata?.truthStatus) || metadata?.generatedValues !== false ||
          !metadata?.sourceId || !Number.isFinite(sourceAgeMs) || sourceAgeMs < -300000 || sourceAgeMs > 300000 ||
          !Number.isFinite(Number(metadata?.signalStrength)) || !Number.isFinite(Number(metadata?.coherence)) ||
          !Number.isFinite(Number(metadata?.lighthouseValue))) {
        throw new Error('FRESH_REAL_ORDER_PROVENANCE_REQUIRED');
      }

      // Verify session ownership
      const { data: session } = await supabase
        .from('hive_sessions')
        .select('id')
        .eq('id', sessionId)
        .eq('user_id', user.id)
        .single();

      if (!session) {
        throw new Error('Session not found or unauthorized');
      }

      // Insert into queue
      const { data: order, error: orderError } = await supabase
        .from('oms_order_queue')
        .insert({
          session_id: sessionId,
          hive_id: hiveId,
          agent_id: agentId,
          symbol,
          side,
          quantity,
          price,
          priority: Number(priority),
          signal_strength: metadata?.signalStrength,
          coherence: metadata?.coherence,
          lighthouse_value: metadata?.lighthouseValue,
          truth_status: metadata.truthStatus,
          source_id: metadata.sourceId,
          source_timestamp: sourceTimestamp,
          generated_values: false,
          status: 'queued',
        })
        .select()
        .single();

      if (orderError) {
        console.error('Failed to enqueue order:', orderError);
        if (orderError.code === '23505') throw new Error('SIGNAL_ALREADY_ROUTED');
        throw new Error(`ORDER_QUEUE_WRITE_FAILED:${orderError.message}`);
      }

      console.log(`✅ Order enqueued: ${order.id} | ${symbol} ${side} ${quantity} @ ${price}`);

      return new Response(
        JSON.stringify({
          success: true,
          orderId: order.id,
          position: await getQueuePosition(supabase, order.id),
        }),
        { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      );
    }

    if (action === 'process') {
      // === PROCESS QUEUED ORDERS (LEAKY BUCKET) ===
      const exchangeInfoResponse = await fetch('https://api.binance.com/api/v3/exchangeInfo');
      if (!exchangeInfoResponse.ok) throw new Error(`BINANCE_EXCHANGE_INFO_HTTP_${exchangeInfoResponse.status}`);
      const exchangeInfo = await exchangeInfoResponse.json();
      const orderRateLimit = (exchangeInfo?.rateLimits || []).find(
        (item: any) => item.rateLimitType === 'ORDERS' && item.interval === 'SECOND',
      );
      const rateLimit = Number(orderRateLimit?.limit);
      const intervalSeconds = Number(orderRateLimit?.intervalNum);
      if (!Number.isFinite(rateLimit) || rateLimit <= 0 || !Number.isFinite(intervalSeconds) || intervalSeconds <= 0) {
        throw new Error('BINANCE_ORDER_RATE_LIMIT_MISSING');
      }
      const windowDurationMs = intervalSeconds * 1000;
      const now = new Date();
      const windowStart = new Date(now.getTime() - windowDurationMs);

      // Count orders in current window
      const { count: ordersInWindow, error: ordersInWindowError } = await supabase
        .from('oms_order_queue')
        .select('*', { count: 'exact', head: true })
        .eq('status', 'executed')
        .gte('executed_at', windowStart.toISOString());

      if (ordersInWindowError || ordersInWindow === null) throw new Error('OMS_RATE_WINDOW_READ_FAILED');
      const availableSlots = Math.max(0, rateLimit - ordersInWindow);

      if (availableSlots <= 0) {
        return new Response(
          JSON.stringify({
            success: true,
            processed: 0,
            reason: 'Rate limit reached',
            availableSlots: 0,
            nextWindowIn: windowDurationMs,
            truthStatus: 'live',
            sourceId: 'binance:/api/v3/exchangeInfo',
            sourceTimestamp: exchangeInfoResponse.headers.get('date'),
            generatedValues: false,
          }),
          { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
        );
      }

      // Get orders to process (highest priority first)
      const { data: orders, error: ordersError } = await supabase
        .from('oms_order_queue')
        .select('*, hive_sessions!inner(user_id)')
        .eq('status', 'queued')
        .eq('hive_sessions.user_id', user.id)
        .order('priority', { ascending: false })
        .order('queued_at', { ascending: true })
        .limit(Math.min(availableSlots, 10)); // Process max 10 at a time
      if (ordersError) throw new Error(`OMS_QUEUE_READ_FAILED:${ordersError.message}`);

      if (!orders || orders.length === 0) {
        return new Response(
          JSON.stringify({
            success: true,
            processed: 0,
            reason: 'No orders in queue',
            availableSlots,
            truthStatus: 'no_data',
            sourceId: 'supabase:oms_order_queue',
            sourceTimestamp: new Date().toISOString(),
            generatedValues: false,
          }),
          { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
        );
      }

      let processed = 0;
      let failed = 0;
      const results = [];

      const { data: userSession, error: userSessionError } = await supabase
        .from('aureon_user_sessions')
        .select('binance_api_key_encrypted, binance_api_secret_encrypted, binance_iv')
        .eq('user_id', user.id)
        .single();
      if (userSessionError || !userSession?.binance_api_key_encrypted || !userSession?.binance_api_secret_encrypted) {
        throw new Error('BINANCE_CREDENTIALS_NOT_CONFIGURED');
      }
      const binanceApiKey = await decryptCredential(userSession.binance_api_key_encrypted, userSession.binance_iv || '');
      const binanceApiSecret = await decryptCredential(userSession.binance_api_secret_encrypted, userSession.binance_iv || '');

      for (const order of orders) {
        try {
          // Mark as processing
          const { error: processingError } = await supabase
            .from('oms_order_queue')
            .update({ status: 'processing' })
            .eq('id', order.id);
          if (processingError) throw new Error(`OMS_PROCESSING_STATE_WRITE_FAILED:${processingError.message}`);

          const timestamp = Date.now();
          const queryString = new URLSearchParams({
            symbol: String(order.symbol).toUpperCase(),
            side: String(order.side).toUpperCase(),
            type: 'MARKET',
            quantity: String(order.quantity),
            newOrderRespType: 'FULL',
            timestamp: String(timestamp),
          }).toString();
          const signature = createHmac('sha256', binanceApiSecret).update(queryString).digest('hex');
          const exchangeResponse = await fetch(
            `https://api.binance.com/api/v3/order?${queryString}&signature=${signature}`,
            { method: 'POST', headers: { 'X-MBX-APIKEY': binanceApiKey } },
          );
          const receipt = await exchangeResponse.json();
          if (!exchangeResponse.ok) {
            throw new Error(`BINANCE_ORDER_HTTP_${exchangeResponse.status}:${receipt?.msg || 'unknown'}`);
          }
          const executedQuantity = Number(receipt.executedQty);
          const cumulativeQuote = Number(receipt.cummulativeQuoteQty);
          const fills = Array.isArray(receipt.fills) ? receipt.fills : [];
          const fillQuantity = fills.reduce((sum: number, fill: any) => sum + Number(fill.qty), 0);
          const fillQuote = fills.reduce(
            (sum: number, fill: any) => sum + Number(fill.qty) * Number(fill.price),
            0,
          );
          const executedPrice = fillQuantity > 0
            ? fillQuote / fillQuantity
            : executedQuantity > 0 && cumulativeQuote > 0
              ? cumulativeQuote / executedQuantity
              : Number.NaN;
          if (receipt.status !== 'FILLED' || !Number.isFinite(executedQuantity) || executedQuantity <= 0 ||
              !Number.isFinite(executedPrice) || executedPrice <= 0 || !receipt.orderId) {
            throw new Error(`BINANCE_ORDER_NOT_FILLED:${receipt.status || 'unknown'}`);
          }
          const sourceTimestamp = exchangeResponse.headers.get('date') || new Date().toISOString();

          // Update order status
          const { error: executionWriteError } = await supabase
            .from('oms_order_queue')
            .update({
              status: 'executed',
              executed_at: new Date().toISOString(),
              executed_price: executedPrice,
              executed_quantity: executedQuantity,
              exchange_order_id: String(receipt.orderId),
              truth_status: 'live',
              source_id: 'binance:/api/v3/order',
              source_timestamp: sourceTimestamp,
              generated_values: false,
            })
            .eq('id', order.id);
          if (executionWriteError) {
            throw new Error(`LIVE_ORDER_FILLED_QUEUE_RECONCILIATION_REQUIRED:${receipt.orderId}:${executionWriteError.message}`);
          }

          const { error: tradeWriteError } = await supabase
            .from('hive_trades')
            .insert({
              session_id: order.session_id,
              hive_id: order.hive_id,
              agent_id: order.agent_id,
              symbol: order.symbol,
              side: order.side,
              entry_price: executedPrice,
              quantity: executedQuantity,
              status: 'open',
              truth_status: 'live',
              source_id: 'binance:/api/v3/order',
              source_timestamp: sourceTimestamp,
              generated_values: false,
            });
          if (tradeWriteError) {
            results.push({
              orderId: order.id,
              exchangeOrderId: String(receipt.orderId),
              truthStatus: 'live',
              sourceTimestamp,
              generatedValues: false,
              reconciliationRequired: true,
              error: `HIVE_TRADE_WRITE_FAILED:${tradeWriteError.message}`,
            });
            processed++;
            continue;
          }

          processed++;
          results.push({
            orderId: order.id,
            symbol: order.symbol,
            side: order.side,
            executedPrice,
            executedQuantity,
            exchangeOrderId: String(receipt.orderId),
            truthStatus: 'live',
            sourceTimestamp,
            generatedValues: false,
          });

          console.log(`✅ Order executed: ${order.symbol} ${order.side} ${executedQuantity} @ ${executedPrice}`);
        } catch (error) {
          console.error(`Failed to execute order ${order.id}:`, error);

          const errorMessage = error instanceof Error ? error.message : 'Unknown error';
          if (errorMessage.startsWith('LIVE_ORDER_FILLED_')) {
            results.push({ orderId: order.id, reconciliationRequired: true, error: errorMessage });
            continue;
          }
          await supabase
            .from('oms_order_queue')
            .update({
              status: 'failed',
              error_message: errorMessage,
            })
            .eq('id', order.id);
          failed++;
        }
      }

      // Record metrics
      const { count: queueDepth, error: queueDepthError } = await supabase
        .from('oms_order_queue')
        .select('*', { count: 'exact', head: true })
        .eq('status', 'queued');
      if (queueDepthError || queueDepth === null) throw new Error('OMS_QUEUE_DEPTH_READ_FAILED');

      await supabase
        .from('oms_execution_metrics')
        .insert({
          queue_depth: queueDepth ?? 0,
          current_window_orders: (ordersInWindow ?? 0) + processed,
          rate_limit_utilization: ((ordersInWindow ?? 0) + processed) / rateLimit,
          orders_executed_last_minute: processed,
          orders_failed_last_minute: failed,
        });

      return new Response(
        JSON.stringify({
          success: true,
          processed,
          availableSlots: availableSlots - processed,
          results,
          failed,
          truthStatus: 'live',
          sourceId: 'binance:/api/v3/exchangeInfo,/api/v3/order',
          sourceTimestamp: exchangeInfoResponse.headers.get('date') || new Date().toISOString(),
          generatedValues: false,
        }),
        { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      );
    }

    if (action === 'status') {
      // === GET QUEUE STATUS ===
      const { sessionId } = params;
      const { data: ownedSession } = await supabase
        .from('hive_sessions')
        .select('id')
        .eq('id', sessionId)
        .eq('user_id', user.id)
        .single();
      if (!ownedSession) throw new Error('Session not found or unauthorized');

      const exchangeInfoResponse = await fetch('https://api.binance.com/api/v3/exchangeInfo');
      if (!exchangeInfoResponse.ok) throw new Error(`BINANCE_EXCHANGE_INFO_HTTP_${exchangeInfoResponse.status}`);
      const exchangeInfo = await exchangeInfoResponse.json();
      const orderRateLimit = (exchangeInfo?.rateLimits || []).find(
        (item: any) => item.rateLimitType === 'ORDERS' && item.interval === 'SECOND',
      );
      const rateLimit = Number(orderRateLimit?.limit);
      const intervalSeconds = Number(orderRateLimit?.intervalNum);
      if (!Number.isFinite(rateLimit) || rateLimit <= 0 || !Number.isFinite(intervalSeconds) || intervalSeconds <= 0) {
        throw new Error('BINANCE_ORDER_RATE_LIMIT_MISSING');
      }
      const windowDurationMs = intervalSeconds * 1000;

      // Queue depth
      const { count: queueDepth, error: queueDepthError } = await supabase
        .from('oms_order_queue')
        .select('*', { count: 'exact', head: true })
        .eq('status', 'queued')
        .eq('session_id', sessionId);

      // Processing count
      const { count: processing, error: processingError } = await supabase
        .from('oms_order_queue')
        .select('*', { count: 'exact', head: true })
        .eq('status', 'processing')
        .eq('session_id', sessionId);

      // Rate limit status
      const now = new Date();
      const windowStart = new Date(now.getTime() - windowDurationMs);

      const { count: ordersInWindow, error: windowCountError } = await supabase
        .from('oms_order_queue')
        .select('*', { count: 'exact', head: true })
        .eq('status', 'executed')
        .gte('executed_at', windowStart.toISOString());
      if (queueDepthError || processingError || windowCountError || queueDepth === null || processing === null || ordersInWindow === null) {
        throw new Error('OMS_STATUS_READ_FAILED');
      }

      const availableSlots = rateLimit - (ordersInWindow ?? 0);

      // Recent metrics
      const { data: metrics } = await supabase
        .from('oms_execution_metrics')
        .select('*')
        .order('timestamp', { ascending: false })
        .limit(1)
        .single();

      return new Response(
        JSON.stringify({
          success: true,
          queueDepth,
          processing,
          rateLimit: {
            limit: rateLimit,
            used: ordersInWindow ?? 0,
            available: availableSlots,
            utilization: ((ordersInWindow ?? 0) / rateLimit) * 100,
            windowDurationMs,
          },
          metrics: metrics ?? null,
          truthStatus: 'live',
          sourceId: 'binance:/api/v3/exchangeInfo',
          sourceTimestamp: exchangeInfoResponse.headers.get('date') || new Date().toISOString(),
          generatedValues: false,
        }),
        { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      );
    }

    if (action === 'cancel') {
      // === CANCEL ORDER ===
      const { orderId } = params;

      const { data: order } = await supabase
        .from('oms_order_queue')
        .select('*, hive_sessions!inner(user_id)')
        .eq('id', orderId)
        .single();

      if (!order || order.hive_sessions.user_id !== user.id) {
        throw new Error('Order not found or unauthorized');
      }

      if (order.status !== 'queued') {
        throw new Error(`Cannot cancel order with status: ${order.status}`);
      }

      await supabase
        .from('oms_order_queue')
        .update({
          status: 'cancelled',
          cancelled_at: new Date().toISOString(),
        })
        .eq('id', orderId);

      return new Response(
        JSON.stringify({ success: true, message: 'Order cancelled' }),
        { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      );
    }

    throw new Error(`Unknown action: ${action}`);

  } catch (error) {
    console.error('OMS error:', error);
    return new Response(
      JSON.stringify({ success: false, error: error instanceof Error ? error.message : 'Unknown error' }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 500 }
    );
  }
});

async function getQueuePosition(supabase: any, orderId: string): Promise<number> {
  const { data: order, error: orderError } = await supabase
    .from('oms_order_queue')
    .select('priority, queued_at')
    .eq('id', orderId)
    .single();

  if (orderError || !order) throw new Error('OMS_QUEUE_POSITION_ORDER_READ_FAILED');

  const { count, error: countError } = await supabase
    .from('oms_order_queue')
    .select('*', { count: 'exact', head: true })
    .eq('status', 'queued')
    .or(`priority.gt.${order.priority},and(priority.eq.${order.priority},queued_at.lt.${order.queued_at})`);

  if (countError || count === null) throw new Error('OMS_QUEUE_POSITION_COUNT_FAILED');
  return count + 1;
}
