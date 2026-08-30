import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";
import { createHmac } from "https://deno.land/std@0.177.0/node/crypto.ts";
import { decryptCredential } from "../_shared/credential_crypto.ts";

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};

const EXCLUDED_ASSETS = new Set(['USDT', 'USDC', 'BUSD', 'TUSD', 'FDUSD', 'USDP', 'DAI', 'EUR', 'GBP', 'USD']);

const normalizeSymbols = (input: string[]) =>
  Array.from(new Set((input || []).map((s) => String(s).toUpperCase().trim()))).filter(Boolean);

async function deriveSymbolsFromBalances(apiKey: string, apiSecret: string, maxSymbols = 25): Promise<string[]> {
  try {
    console.log('[fetch-trades] Discovering symbols from balances...');
    const timestamp = Date.now();
    const queryString = `timestamp=${timestamp}`;
    const signature = createHmac('sha256', apiSecret).update(queryString).digest('hex');

    const resp = await fetch(`https://api.binance.com/api/v3/account?${queryString}&signature=${signature}`, {
      headers: { 'X-MBX-APIKEY': apiKey },
    });

    if (!resp.ok) {
      const t = await resp.text();
      console.log('[fetch-trades] Balance discovery failed:', resp.status, t);
      return [];
    }

    const data = await resp.json();
    const assets: string[] = (data?.balances || [])
      .map((b: any) => ({ asset: String(b.asset || ''), total: Number(b.free || 0) + Number(b.locked || 0) }))
      .filter((b: any) => b.asset && b.total > 0)
      .map((b: any) => b.asset)
      .filter((a: string) => !EXCLUDED_ASSETS.has(a));

    const candidates = assets.slice(0, maxSymbols).map((a) => `${a}USDT`);
    console.log('[fetch-trades] Discovered symbols:', candidates);
    return normalizeSymbols(candidates);
  } catch (e) {
    console.log('[fetch-trades] Balance discovery error:', e);
    return [];
  }
}

serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response(null, { headers: corsHeaders });
  }

  try {
    const supabaseUrl = Deno.env.get('SUPABASE_URL') ?? '';
    const supabaseAnonKey = Deno.env.get('SUPABASE_ANON_KEY') ?? '';
    const supabaseServiceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? '';

    if (!supabaseUrl || !supabaseAnonKey || !supabaseServiceKey) {
      return new Response(JSON.stringify({ error: 'Server configuration error' }), {
        status: 500,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    const supabaseClient = createClient(
      supabaseUrl,
      supabaseAnonKey,
      { global: { headers: { Authorization: req.headers.get('Authorization')! } } }
    );

    const { data: { user }, error: authError } = await supabaseClient.auth.getUser();
    if (authError || !user) {
      return new Response(JSON.stringify({ error: 'Unauthorized' }), {
        status: 401,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    console.log('[fetch-trades] Request from user:', user.id);

    const body = await req.json().catch(() => ({} as any));
    const symbolsRaw = Array.isArray(body?.symbols) ? (body.symbols as string[]) : undefined;
    const limitRaw = Number(body?.limit ?? 50);

    // FIRST: Load and decrypt credentials BEFORE using them
    const service = createClient(supabaseUrl, supabaseServiceKey);
    const { data: session, error: sessionError } = await service
      .from('aureon_user_sessions')
      .select('binance_api_key_encrypted, binance_api_secret_encrypted, binance_iv')
      .eq('user_id', user.id)
      .single();

    if (sessionError || !session) {
      console.log('[fetch-trades] No session found for user:', user.id);
      return new Response(JSON.stringify({ error: 'No trading session found. Please re-login.' }), {
        status: 404,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    if (!session.binance_api_key_encrypted || !session.binance_api_secret_encrypted || !session.binance_iv) {
      console.log('[fetch-trades] Missing Binance credentials for user:', user.id);
      return new Response(JSON.stringify({ error: 'No Binance credentials saved. Add them in Settings → API Credentials.' }), {
        status: 400,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    // Decrypt credentials FIRST
    const apiKey = await decryptCredential(session.binance_api_key_encrypted, session.binance_iv);
    const apiSecret = await decryptCredential(session.binance_api_secret_encrypted, session.binance_iv);
    console.log('[fetch-trades] Credentials decrypted successfully');

    // NOW derive symbols using the decrypted credentials
    let symbols = symbolsRaw && symbolsRaw.length > 0 ? normalizeSymbols(symbolsRaw) : [];
    if (symbols.length === 0) {
      const discovered = await deriveSymbolsFromBalances(apiKey, apiSecret, 25);
      symbols = discovered;
    }
    if (symbols.length === 0) {
      return new Response(JSON.stringify({
        error: 'TRADE_SYMBOL_UNIVERSE_REQUIRED',
        truthStatus: 'no_data',
        generatedValues: false,
      }), {
        status: 409,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    const limit = Number.isFinite(limitRaw) ? Math.min(500, Math.max(1, limitRaw)) : 50;
    const perSymbolLimit = Math.min(50, Math.max(1, Math.ceil(limit / Math.max(1, symbols.length))));

    console.log('[fetch-trades] Fetching trades for symbols:', symbols);
    console.log('[fetch-trades] Per-symbol limit:', perSymbolLimit);

    // Fetch trades from multiple symbols
    const allTrades: any[] = [];
    
    for (const symbol of symbols) {
      try {
        const timestamp = Date.now();
        const queryString = `symbol=${symbol}&limit=${perSymbolLimit}&timestamp=${timestamp}`;
        const signature = createHmac('sha256', apiSecret).update(queryString).digest('hex');

        const response = await fetch(
          `https://api.binance.com/api/v3/myTrades?${queryString}&signature=${signature}`,
          { headers: { 'X-MBX-APIKEY': apiKey } }
        );

        if (response.ok) {
          const trades = await response.json();
          console.log(`[fetch-trades] ${symbol}: ${trades.length} trades`);
          allTrades.push(...trades);
        } else {
          const errorText = await response.text();
          console.log(`[fetch-trades] ${symbol}: no trades (${errorText})`);
        }
      } catch (err) {
        console.error(`[fetch-trades] Error fetching ${symbol}:`, err);
      }
    }

    console.log(`[fetch-trades] Total trades fetched: ${allTrades.length}`);
    
    // Sort by time descending
    const trades = allTrades.sort((a, b) => b.time - a.time).slice(0, limit);

    // Store new trades in database
    const tradeRecords = trades.map((t: any) => ({
      transaction_id: `binance:${t.symbol}:${String(t.id)}`,
      exchange: 'binance',
      symbol: t.symbol,
      side: t.isBuyer ? 'BUY' : 'SELL',
      price: parseFloat(t.price),
      quantity: parseFloat(t.qty),
      quote_qty: parseFloat(t.quoteQty),
      fee: parseFloat(t.commission),
      fee_asset: t.commissionAsset,
      timestamp: new Date(t.time).toISOString(),
      user_id: user.id,
      truth_status: 'live',
      source_id: 'binance:/api/v3/myTrades',
      source_timestamp: new Date(t.time).toISOString(),
      generated_values: false,
    }));

    // Upsert trades (avoid duplicates)
    let upsertedCount = 0;
    for (const record of tradeRecords) {
      const { error: upsertError } = await supabaseClient
        .from('trade_records')
        .upsert(record, { onConflict: 'transaction_id' });
      
      if (!upsertError) upsertedCount++;
      else console.log('[fetch-trades] Upsert error:', upsertError.message);
    }

    console.log(`[fetch-trades] Upserted ${upsertedCount}/${tradeRecords.length} trades to DB`);

    return new Response(JSON.stringify({
      trades: tradeRecords,
      count: tradeRecords.length,
      truthStatus: 'live',
      sourceId: 'binance:/api/v3/myTrades',
      sourceTimestamp: tradeRecords.length > 0 ? tradeRecords[0].source_timestamp : null,
      generatedValues: false,
    }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    });
  } catch (error: unknown) {
    console.error('[fetch-trades] Error:', error);
    const message = error instanceof Error ? error.message : 'Unknown error';
    return new Response(JSON.stringify({ error: message }), {
      status: 500,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    });
  }
});
