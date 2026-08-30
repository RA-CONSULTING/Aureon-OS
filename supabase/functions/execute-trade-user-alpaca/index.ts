import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";
import { decryptCredential } from "../_shared/credential_crypto.ts";

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};

serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response(null, { headers: corsHeaders });
  }

  console.log('[execute-trade-user-alpaca] Request received');

  try {
    const supabaseUrl = Deno.env.get('SUPABASE_URL')!;
    const supabaseAnonKey = Deno.env.get('SUPABASE_ANON_KEY')!;
    const supabaseServiceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;

    // Verify user
    const authHeader = req.headers.get('Authorization');
    const token = authHeader?.replace('Bearer ', '');

    if (!token) {
      return new Response(
        JSON.stringify({ error: 'Unauthorized' }),
        { status: 401, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      );
    }

    const anonSupabase = createClient(supabaseUrl, supabaseAnonKey);
    const { data: { user }, error: authError } = await anonSupabase.auth.getUser(token);

    if (authError || !user) {
      return new Response(
        JSON.stringify({ error: 'Unauthorized' }),
        { status: 401, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      );
    }

    const body = await req.json();
    const { symbol, side, quantity, orderType = 'market', timeInForce = 'gtc', limitPrice, dryRun = false } = body;

    if (!symbol || !side || !quantity) {
      return new Response(
        JSON.stringify({ error: 'Missing required parameters: symbol, side, quantity' }),
        { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      );
    }

    // Get user's Alpaca credentials
    const supabase = createClient(supabaseUrl, supabaseServiceKey);
    const { data: session, error: sessionError } = await supabase
      .from('aureon_user_sessions')
      .select('alpaca_api_key_encrypted, alpaca_secret_key_encrypted, alpaca_iv')
      .eq('user_id', user.id)
      .single();

    if (sessionError || !session) {
      return new Response(
        JSON.stringify({ error: 'No session found' }),
        { status: 404, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      );
    }

    if (!session.alpaca_api_key_encrypted || !session.alpaca_secret_key_encrypted || !session.alpaca_iv) {
      return new Response(
        JSON.stringify({ error: 'Alpaca credentials not configured' }),
        { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      );
    }

    // Decrypt credentials
    const apiKey = await decryptCredential(session.alpaca_api_key_encrypted, session.alpaca_iv);
    const secretKey = await decryptCredential(session.alpaca_secret_key_encrypted, session.alpaca_iv);

    if (dryRun) {
      return new Response(
        JSON.stringify({
          success: false,
          error: 'PRODUCTION_LIVE_EXECUTION_REQUIRED',
          truthStatus: 'no_data',
          generatedValues: false,
        }),
        { status: 409, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      );
    }

    // Execute real trade on Alpaca
    const baseUrl = 'https://api.alpaca.markets';
    const orderPayload: Record<string, any> = {
      symbol: symbol.replace('/', ''),
      qty: quantity.toString(),
      side: side.toLowerCase(),
      type: orderType,
      time_in_force: timeInForce,
    };

    if (orderType === 'limit' && limitPrice) {
      orderPayload.limit_price = limitPrice.toString();
    }

    console.log('[execute-trade-user-alpaca] Placing order:', orderPayload);

    const response = await fetch(`${baseUrl}/v2/orders`, {
      method: 'POST',
      headers: {
        'APCA-API-KEY-ID': apiKey,
        'APCA-API-SECRET-KEY': secretKey,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(orderPayload),
    });

    const data = await response.json();

    if (!response.ok) {
      console.error('[execute-trade-user-alpaca] Alpaca error:', data);
      return new Response(
        JSON.stringify({ error: data.message || 'Trade execution failed' }),
        { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      );
    }

    console.log('[execute-trade-user-alpaca] Order placed:', data.id);

    return new Response(
      JSON.stringify({
        success: true,
        exchange: 'alpaca',
        orderId: data.id,
        symbol,
        side,
        quantity,
        orderType,
        status: data.status,
        filledQty: data.filled_qty,
        filledAvgPrice: data.filled_avg_price,
        truthStatus: 'live',
        sourceId: 'alpaca:/v2/orders',
        sourceTimestamp: response.headers.get('date') || new Date().toISOString(),
        generatedValues: false,
      }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    );

  } catch (error) {
    console.error('[execute-trade-user-alpaca] Error:', error);
    return new Response(
      JSON.stringify({ error: 'Internal error executing Alpaca trade' }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    );
  }
});
