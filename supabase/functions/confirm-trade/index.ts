import { serve } from 'https://deno.land/std@0.168.0/http/server.ts';
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';
import { createHmac } from 'https://deno.land/std@0.168.0/node/crypto.ts';
import { decryptCredential } from '../_shared/credential_crypto.ts';

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};

interface TradeConfirmationResult {
  orderId: string;
  status: string;
  executedQty: number;
  executedPrice: number | null;
  fills: any[];
  commission: number;
  commissionAsset: string | null;
  side: string;
  isConfirmed: boolean;
}

async function confirmBinanceOrder(
  orderId: string,
  symbol: string,
  apiKey: string,
  apiSecret: string
): Promise<TradeConfirmationResult> {
  const timestamp = Date.now();
  const queryString = `symbol=${symbol}&orderId=${orderId}&timestamp=${timestamp}`;
  
  const signature = createHmac('sha256', apiSecret)
    .update(queryString)
    .digest('hex');
  
  const url = `https://api.binance.com/api/v3/order?${queryString}&signature=${signature}`;
  
  const response = await fetch(url, {
    headers: { 'X-MBX-APIKEY': apiKey },
  });
  
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Binance order query failed: ${response.status} - ${errorText}`);
  }
  
  const order = await response.json();
  const executedQty = Number(order.executedQty);
  const limitPrice = Number(order.price);
  const cumulativeQuote = Number(order.cummulativeQuoteQty);
  const executedPrice = Number.isFinite(limitPrice) && limitPrice > 0
    ? limitPrice
    : Number.isFinite(executedQty) && executedQty > 0 && Number.isFinite(cumulativeQuote)
      ? cumulativeQuote / executedQty
      : null;
  
  return {
    orderId: order.orderId.toString(),
    status: order.status,
    executedQty,
    executedPrice,
    fills: order.fills || [],
    commission: order.fills?.reduce((sum: number, f: any) => sum + parseFloat(f.commission), 0) || 0,
    commissionAsset: order.fills?.[0]?.commissionAsset ?? null,
    side: String(order.side || 'UNKNOWN'),
    isConfirmed: ['FILLED', 'PARTIALLY_FILLED', 'CANCELED', 'REJECTED', 'EXPIRED'].includes(order.status),
  };
}

serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response(null, { headers: corsHeaders });
  }

  try {
    const supabase = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? ''
    );
    
    const { trade_id, external_order_id, symbol, exchange, user_id } = await req.json();
    
    if (!external_order_id || !symbol) {
      throw new Error('Missing required fields: external_order_id, symbol');
    }

    const authHeader = req.headers.get('Authorization');
    const token = authHeader?.replace(/^Bearer\s+/i, '');
    if (!token) throw new Error('AUTHENTICATION_REQUIRED');
    const { data: { user }, error: authError } = await supabase.auth.getUser(token);
    if (authError || !user) throw new Error('INVALID_AUTHENTICATION');
    if (user_id && user_id !== user.id) throw new Error('USER_ID_MISMATCH');
    
    console.log(`[confirm-trade] Confirming order ${external_order_id} for ${symbol} on ${exchange}`);
    
    // Get user credentials
    const { data: session, error: sessionError } = await supabase
      .from('aureon_user_sessions')
      .select('binance_api_key_encrypted, binance_api_secret_encrypted, binance_iv')
      .eq('user_id', user.id)
      .single();
    
    if (sessionError || !session) {
      throw new Error('User session not found');
    }
    
    let confirmResult: TradeConfirmationResult;
    
    if (exchange === 'binance' || !exchange) {
      const apiKey = await decryptCredential(
        session.binance_api_key_encrypted,
        session.binance_iv || ''
      );
      const apiSecret = await decryptCredential(
        session.binance_api_secret_encrypted,
        session.binance_iv || ''
      );
      
      confirmResult = await confirmBinanceOrder(external_order_id, symbol, apiKey, apiSecret);
    } else {
      throw new Error(`Exchange ${exchange} confirmation not yet implemented`);
    }
    
    console.log(`[confirm-trade] Order status: ${confirmResult.status}, executed: ${confirmResult.executedQty}`);
    
    // Update trade audit log
    const stage = confirmResult.status === 'FILLED' ? 'FILLED' :
                  confirmResult.status === 'PARTIALLY_FILLED' ? 'PARTIALLY_FILLED' :
                  confirmResult.status === 'CANCELED' ? 'CANCELED' :
                  confirmResult.status === 'REJECTED' ? 'FAILED' : 'ORDER_CONFIRMED';
    
    const validationStatus = confirmResult.isConfirmed ? 'confirmed' : 'pending';
    
    const { error: auditError } = await supabase
      .from('trade_audit_log')
      .insert({
        trade_id: trade_id || crypto.randomUUID(),
        external_order_id,
        stage,
        exchange: exchange || 'binance',
        symbol,
        side: confirmResult.side,
        quantity: confirmResult.executedQty,
        executed_qty: confirmResult.executedQty,
        executed_price: confirmResult.executedPrice,
        commission: confirmResult.commission,
        commission_asset: confirmResult.commissionAsset,
        exchange_response: { ...confirmResult, truthStatus: 'live', generatedValues: false, collectedAt: new Date().toISOString() },
        validation_status: validationStatus,
        validation_message: `Order ${confirmResult.status} - Executed ${confirmResult.executedQty} @ ${confirmResult.executedPrice}`,
      });
    
    if (auditError) {
      console.error('[confirm-trade] Audit log error:', auditError);
    }
    
    // Update trading_executions if exists
    if (trade_id) {
      await supabase
        .from('trading_executions')
        .update({
          status: confirmResult.status === 'FILLED' ? 'executed' : confirmResult.status.toLowerCase(),
          executed_price: confirmResult.executedPrice,
          executed_quantity: confirmResult.executedQty,
          updated_at: new Date().toISOString(),
        })
        .eq('id', trade_id);
    }
    
    return new Response(
      JSON.stringify({
        success: true,
        confirmed: confirmResult.isConfirmed,
        orderId: confirmResult.orderId,
        status: confirmResult.status,
        executedQty: confirmResult.executedQty,
        executedPrice: confirmResult.executedPrice,
        commission: confirmResult.commission,
        commissionAsset: confirmResult.commissionAsset,
        fills: confirmResult.fills,
      }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    );
  } catch (error) {
    console.error('[confirm-trade] Error:', error);
    return new Response(
      JSON.stringify({ 
        success: false, 
        confirmed: false,
        error: error instanceof Error ? error.message : 'Unknown error' 
      }),
      { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    );
  }
});
