import { serve } from 'https://deno.land/std@0.168.0/http/server.ts';
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};

serve(async (req) => {
  if (req.method === 'OPTIONS') return new Response(null, { headers: corsHeaders });

  const startedAt = new Date().toISOString();
  try {
    const supabaseUrl = Deno.env.get('SUPABASE_URL')?.trim();
    const serviceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')?.trim();
    const anonKey = Deno.env.get('SUPABASE_ANON_KEY')?.trim();
    if (!supabaseUrl || !serviceKey || !anonKey) throw new Error('SUPABASE_RUNTIME_NOT_CONFIGURED');

    const authorization = req.headers.get('Authorization');
    const token = authorization?.replace(/^Bearer\s+/i, '');
    if (!authorization || !token) throw new Error('AUTHENTICATION_REQUIRED');

    const supabase = createClient(supabaseUrl, serviceKey);
    const { data: { user }, error: authError } = await supabase.auth.getUser(token);
    if (authError || !user) throw new Error('INVALID_AUTHENTICATION');

    const body = await req.json();
    const externalOrderId = String(body.external_order_id || '').trim();
    const symbol = String(body.symbol || '').trim().toUpperCase();
    const exchange = String(body.exchange || 'binance').trim().toLowerCase();
    const tradeId = body.trade_id ? String(body.trade_id) : undefined;
    if (!externalOrderId || !symbol) throw new Error('PROVIDER_ORDER_ID_AND_SYMBOL_REQUIRED');
    if (body.user_id && body.user_id !== user.id) throw new Error('USER_ID_MISMATCH');
    if (exchange !== 'binance') throw new Error(`UNSUPPORTED_LIVE_CONFIRMATION_EXCHANGE:${exchange}`);

    const confirmResponse = await fetch(`${supabaseUrl}/functions/v1/confirm-trade`, {
      method: 'POST',
      headers: {
        Authorization: authorization,
        apikey: anonKey,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        trade_id: tradeId,
        external_order_id: externalOrderId,
        symbol,
        exchange,
        user_id: user.id,
      }),
    });
    const confirmation = await confirmResponse.json();
    if (!confirmResponse.ok || confirmation?.success !== true) {
      throw new Error(`LIVE_PROVIDER_CONFIRMATION_FAILED:${confirmation?.error || confirmResponse.status}`);
    }
    if (!confirmation.orderId || !confirmation.status) {
      throw new Error('LIVE_PROVIDER_CONFIRMATION_INCOMPLETE');
    }

    const finishedAt = new Date().toISOString();
    return new Response(JSON.stringify({
      success: true,
      validationType: 'provider_order_readback',
      confirmation,
      trace: {
        startTime: startedAt,
        endTime: finishedAt,
        steps: [{
          step: 1,
          name: 'BinanceOrderReadback',
          status: 'success',
          sourceId: 'binance:/api/v3/order',
          sourceTimestamp: finishedAt,
        }],
      },
      truthStatus: 'live',
      sourceId: 'binance:/api/v3/order',
      sourceTimestamp: finishedAt,
      generatedValues: false,
    }), { headers: { ...corsHeaders, 'Content-Type': 'application/json' } });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    console.error('[force-validated-trade] Live validation failed:', message);
    return new Response(JSON.stringify({
      success: false,
      error: message,
      truthStatus: 'no_data',
      generatedValues: false,
      trace: { startTime: startedAt, endTime: new Date().toISOString(), steps: [] },
    }), { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } });
  }
});
