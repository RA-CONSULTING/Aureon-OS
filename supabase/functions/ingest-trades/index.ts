import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};

interface TradeRecord {
  transaction_id: string;
  exchange: string;
  symbol: string;
  side: 'BUY' | 'SELL';
  price: number;
  quantity: number;
  quote_qty?: number;
  fee?: number;
  fee_asset?: string;
  timestamp: string;
  pnl?: number;
  is_win?: boolean;
}

serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response(null, { headers: corsHeaders });
  }

  try {
    const supabaseUrl = Deno.env.get('SUPABASE_URL') ?? '';
    const supabaseServiceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? '';

    if (!supabaseUrl || !supabaseServiceKey) {
      console.error('[ingest-trades] Missing env vars');
      return new Response(JSON.stringify({ error: 'Server configuration error' }), {
        status: 500,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    const body = await req.json();
    const trades: TradeRecord[] = Array.isArray(body.trades) ? body.trades : body.trade ? [body.trade] : [];
    const userId = body.user_id;
    const truthStatus = body.truth_status;
    const sourceId = String(body.source_id || '').trim();
    const sourceTimestamp = String(body.source_timestamp || '').trim();
    const generatedValues = body.generated_values;

    const configuredIngestToken = Deno.env.get('AUREON_INGEST_TOKEN')?.trim();
    const suppliedIngestToken = req.headers.get('x-aureon-ingest-token')?.trim();
    if (!configuredIngestToken) throw new Error('AUREON_INGEST_TOKEN_NOT_CONFIGURED');
    if (!suppliedIngestToken || suppliedIngestToken !== configuredIngestToken) {
      return new Response(JSON.stringify({ error: 'Unauthorized' }), {
        status: 401,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    if (trades.length === 0) {
      return new Response(JSON.stringify({ error: 'No trades provided' }), {
        status: 400,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }
    if (!userId || !sourceId || !sourceTimestamp || !['live', 'real_derived'].includes(truthStatus) || generatedValues !== false) {
      return new Response(JSON.stringify({ error: 'REAL_DATA_PROVENANCE_REQUIRED' }), {
        status: 400,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }
    const sourceAgeMs = Date.now() - Date.parse(sourceTimestamp);
    if (!Number.isFinite(sourceAgeMs) || sourceAgeMs < -300000 || sourceAgeMs > 300000) {
      return new Response(JSON.stringify({ error: 'LIVE_SOURCE_TIMESTAMP_STALE' }), {
        status: 409,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    for (const trade of trades) {
      if (!trade.transaction_id || !trade.exchange || !trade.symbol || !trade.timestamp ||
          !['BUY', 'SELL'].includes(trade.side) || !Number.isFinite(Number(trade.price)) ||
          Number(trade.price) <= 0 || !Number.isFinite(Number(trade.quantity)) || Number(trade.quantity) <= 0 ||
          !Number.isFinite(Number(trade.fee)) || !trade.fee_asset) {
        return new Response(JSON.stringify({ error: 'INCOMPLETE_PROVIDER_TRADE_RECEIPT' }), {
          status: 400,
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        });
      }
    }

    console.log(`[ingest-trades] Ingesting ${trades.length} trades for user: ${userId || 'system'}`);

    const supabase = createClient(supabaseUrl, supabaseServiceKey);

    // Map trades to trade_records format
    const records = trades.map((t) => ({
      transaction_id: t.transaction_id,
      exchange: t.exchange,
      symbol: t.symbol,
      side: t.side,
      price: t.price,
      quantity: t.quantity,
      quote_qty: t.quote_qty ?? t.price * t.quantity,
      fee: t.fee,
      fee_asset: t.fee_asset,
      timestamp: t.timestamp,
      user_id: userId,
      pnl: t.pnl ?? null,
      is_win: t.is_win ?? null,
      truth_status: truthStatus,
      source_id: sourceId,
      source_timestamp: sourceTimestamp,
      generated_values: false,
    }));

    // Upsert trades (avoid duplicates based on transaction_id)
    const { data, error } = await supabase
      .from('trade_records')
      .upsert(records, { onConflict: 'transaction_id' })
      .select();

    if (error) {
      console.error('[ingest-trades] Upsert error:', error);
      return new Response(JSON.stringify({ error: error.message }), {
        status: 500,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    console.log(`[ingest-trades] Successfully ingested ${data?.length || 0} trades`);

    // Calculate summary stats
    const totalTrades = data?.length || 0;
    const wins = data?.filter((t: any) => t.is_win === true).length || 0;
    const decidedTrades = data?.filter((t: any) => typeof t.is_win === 'boolean').length ?? 0;
    const winRate = decidedTrades > 0 ? Number((wins / decidedTrades * 100).toFixed(1)) : null;

    return new Response(JSON.stringify({
      success: true,
      ingested: totalTrades,
      wins,
      winRate,
      trades: data,
      truthStatus,
      sourceId,
      sourceTimestamp,
      generatedValues: false,
    }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    });
  } catch (error: unknown) {
    console.error('[ingest-trades] Error:', error);
    const message = error instanceof Error ? error.message : 'Unknown error';
    return new Response(JSON.stringify({ error: message }), {
      status: 500,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    });
  }
});
