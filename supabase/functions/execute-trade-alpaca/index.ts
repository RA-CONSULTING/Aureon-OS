import { serve } from "https://deno.land/std@0.168.0/http/server.ts";

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};

serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response(null, { headers: corsHeaders });
  }

  try {
    const apiKey = Deno.env.get('ALPACA_API_KEY');
    const apiSecret = Deno.env.get('ALPACA_SECRET_KEY');

    if (!apiKey || !apiSecret) {
      return new Response(
        JSON.stringify({ error: 'Alpaca credentials not configured' }),
        { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 400 }
      );
    }

    const body = await req.json();
    const { symbol, side, quantity, orderType = 'market', timeInForce = 'gtc', limitPrice } = body;

    if (!symbol || !side || !quantity) {
      return new Response(
        JSON.stringify({ error: 'Missing required parameters: symbol, side, quantity' }),
        { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 400 }
      );
    }

    const baseUrl = 'https://api.alpaca.markets';

    const orderPayload: Record<string, any> = {
      symbol: symbol.replace('/', ''), // BTCUSD format for crypto
      qty: quantity.toString(),
      side: side.toLowerCase(),
      type: orderType,
      time_in_force: timeInForce,
    };

    if (orderType === 'limit' && limitPrice) {
      orderPayload.limit_price = limitPrice.toString();
    }

    console.log(`[execute-trade-alpaca] Placing ${side} ${orderType} order for ${quantity} ${symbol}`);

    const response = await fetch(`${baseUrl}/v2/orders`, {
      method: 'POST',
      headers: {
        'APCA-API-KEY-ID': apiKey,
        'APCA-API-SECRET-KEY': apiSecret,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(orderPayload),
    });

    const data = await response.json();

    if (!response.ok) {
      console.error('[execute-trade-alpaca] Alpaca API error:', data);
      return new Response(
        JSON.stringify({ error: 'Trade execution failed' }),
        { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 400 }
      );
    }

    console.log('[execute-trade-alpaca] Order placed successfully:', data.id);

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
    console.error('[execute-trade-alpaca] Error:', error);
    return new Response(
      JSON.stringify({ error: 'Internal error executing Alpaca trade' }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 500 }
    );
  }
});
