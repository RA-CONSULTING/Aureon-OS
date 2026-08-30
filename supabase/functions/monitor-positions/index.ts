import { serve } from 'https://deno.land/std@0.168.0/http/server.ts';
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};

const SOURCE_MAX_AGE_MS = 60_000;

function finitePositive(value: unknown, field: string): number {
  const numberValue = Number(value);
  if (!Number.isFinite(numberValue) || numberValue <= 0) {
    throw new Error(`INVALID_POSITION_VALUE:${field}`);
  }
  return numberValue;
}

serve(async (req) => {
  if (req.method === 'OPTIONS') return new Response(null, { headers: corsHeaders });

  try {
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
    const { data: positions, error: positionsError } = await supabase
      .from('trading_positions')
      .select('*')
      .eq('user_id', user.id)
      .eq('status', 'open');
    if (positionsError) throw new Error(`POSITION_READ_FAILED:${positionsError.message}`);

    if (!positions || positions.length === 0) {
      return new Response(JSON.stringify({
        success: true,
        monitored: 0,
        updated: 0,
        triggers: [],
        truthStatus: 'no_data',
        sourceId: 'supabase:trading_positions',
        sourceTimestamp: new Date().toISOString(),
        generatedValues: false,
      }), { headers: { ...corsHeaders, 'Content-Type': 'application/json' } });
    }

    const observations = new Map<string, { price: number; sourceTimestamp: string }>();
    for (const symbol of [...new Set(positions.map((position: any) => String(position.symbol).toUpperCase()))]) {
      const response = await fetch(`https://api.binance.com/api/v3/ticker/price?symbol=${encodeURIComponent(symbol)}`);
      if (!response.ok) throw new Error(`BINANCE_TICKER_HTTP_${response.status}:${symbol}`);
      const sourceTimestamp = response.headers.get('date') || '';
      const sourceAgeMs = Date.now() - Date.parse(sourceTimestamp);
      const payload = await response.json();
      const price = finitePositive(payload?.price, `${symbol}.price`);
      if (!Number.isFinite(sourceAgeMs) || sourceAgeMs < -300000 || sourceAgeMs > SOURCE_MAX_AGE_MS) {
        throw new Error(`BINANCE_TICKER_STALE:${symbol}`);
      }
      observations.set(symbol, { price, sourceTimestamp });
    }

    const updated: Array<Record<string, unknown>> = [];
    const triggers: Array<Record<string, unknown>> = [];
    for (const position of positions) {
      if (String(position.exchange || '').toLowerCase() !== 'binance') {
        throw new Error(`POSITION_PROVIDER_MONITOR_NOT_CONNECTED:${position.exchange || 'missing'}`);
      }
      const symbol = String(position.symbol).toUpperCase();
      const observation = observations.get(symbol);
      if (!observation) throw new Error(`BINANCE_TICKER_MISSING:${symbol}`);
      const entryPrice = finitePositive(position.entry_price, `${symbol}.entry_price`);
      const quantity = finitePositive(position.quantity, `${symbol}.quantity`);
      const side = String(position.side).toUpperCase();
      if (!['LONG', 'SHORT'].includes(side)) throw new Error(`INVALID_POSITION_SIDE:${symbol}`);

      const unrealizedPnl = side === 'LONG'
        ? (observation.price - entryPrice) * quantity
        : (entryPrice - observation.price) * quantity;

      const { error: updateError } = await supabase
        .from('trading_positions')
        .update({
          current_price: observation.price,
          unrealized_pnl: unrealizedPnl,
          truth_status: 'real_derived',
          source_id: 'binance:/api/v3/ticker/price',
          source_timestamp: observation.sourceTimestamp,
          generated_values: false,
          updated_at: new Date().toISOString(),
        })
        .eq('id', position.id)
        .eq('user_id', user.id);
      if (updateError) throw new Error(`POSITION_UPDATE_FAILED:${position.id}:${updateError.message}`);

      const stopLoss = position.stop_loss_price == null ? null : finitePositive(position.stop_loss_price, `${symbol}.stop_loss`);
      const takeProfit = position.take_profit_price == null ? null : finitePositive(position.take_profit_price, `${symbol}.take_profit`);
      const stopTriggered = stopLoss !== null && (side === 'LONG' ? observation.price <= stopLoss : observation.price >= stopLoss);
      const takeTriggered = takeProfit !== null && (side === 'LONG' ? observation.price >= takeProfit : observation.price <= takeProfit);
      if (stopTriggered || takeTriggered) {
        triggers.push({
          positionId: position.id,
          symbol,
          trigger: stopTriggered ? 'STOP_LOSS' : 'TAKE_PROFIT',
          observedPrice: observation.price,
          advisoryOnly: true,
          reason: 'No exchange close order was submitted by this monitor',
        });
      }
      updated.push({ positionId: position.id, symbol, currentPrice: observation.price, unrealizedPnl });
    }

    const sourceTimestamp = [...observations.values()]
      .map((item) => item.sourceTimestamp)
      .sort((a, b) => Date.parse(a) - Date.parse(b))[0];
    return new Response(JSON.stringify({
      success: true,
      monitored: positions.length,
      updated: updated.length,
      positions: updated,
      triggers,
      truthStatus: 'real_derived',
      sourceId: 'binance:/api/v3/ticker/price',
      sourceTimestamp,
      generatedValues: false,
    }), { headers: { ...corsHeaders, 'Content-Type': 'application/json' } });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    console.error('[monitor-positions]', message);
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
