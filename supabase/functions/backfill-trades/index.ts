import { serve } from 'https://deno.land/std@0.168.0/http/server.ts';
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2.49.4';
import { createHmac } from 'node:crypto';
import { decryptCredential } from '../_shared/credential_crypto.ts';

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};

function normalizeSymbols(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return [...new Set(value.map((item) => String(item).trim().toUpperCase()))]
    .filter((symbol) => /^[A-Z0-9]{5,20}$/.test(symbol))
    .slice(0, 20);
}

function requireFinite(value: unknown, field: string, allowZero = false): number {
  const numberValue = Number(value);
  if (!Number.isFinite(numberValue) || (allowZero ? numberValue < 0 : numberValue <= 0)) {
    throw new Error(`INVALID_BINANCE_TRADE_RECEIPT:${field}`);
  }
  return numberValue;
}

serve(async (req) => {
  if (req.method === 'OPTIONS') return new Response(null, { headers: corsHeaders });

  try {
    const authorization = req.headers.get('Authorization');
    const token = authorization?.replace(/^Bearer\s+/i, '');
    if (!token) throw new Error('AUTHENTICATION_REQUIRED');

    const supabaseUrl = Deno.env.get('SUPABASE_URL')?.trim();
    const serviceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')?.trim();
    if (!supabaseUrl || !serviceKey) throw new Error('SUPABASE_RUNTIME_NOT_CONFIGURED');
    const supabase = createClient(supabaseUrl, serviceKey);
    const { data: { user }, error: authError } = await supabase.auth.getUser(token);
    if (authError || !user) throw new Error('INVALID_AUTHENTICATION');

    const body = await req.json().catch(() => ({}));
    let symbols = normalizeSymbols(body.symbols);
    const { data: session, error: sessionError } = await supabase
      .from('aureon_user_sessions')
      .select('binance_api_key_encrypted, binance_api_secret_encrypted, binance_iv')
      .eq('user_id', user.id)
      .single();
    if (sessionError || !session?.binance_api_key_encrypted || !session?.binance_api_secret_encrypted) {
      throw new Error('BINANCE_CREDENTIALS_NOT_CONFIGURED');
    }
    const apiKey = await decryptCredential(session.binance_api_key_encrypted, session.binance_iv || '');
    const apiSecret = await decryptCredential(session.binance_api_secret_encrypted, session.binance_iv || '');

    if (symbols.length === 0) {
      const timestamp = Date.now();
      const queryString = `timestamp=${timestamp}`;
      const signature = createHmac('sha256', apiSecret).update(queryString).digest('hex');
      const response = await fetch(`https://api.binance.com/api/v3/account?${queryString}&signature=${signature}`, {
        headers: { 'X-MBX-APIKEY': apiKey },
      });
      if (!response.ok) throw new Error(`BINANCE_ACCOUNT_HTTP_${response.status}`);
      const account = await response.json();
      if (!Array.isArray(account?.balances)) throw new Error('BINANCE_ACCOUNT_BALANCES_MISSING');
      symbols = normalizeSymbols(account.balances
        .filter((balance: any) => Number(balance.free) > 0 || Number(balance.locked) > 0)
        .filter((balance: any) => !['USDT', 'USDC', 'BUSD', 'FDUSD', 'USD'].includes(String(balance.asset).toUpperCase()))
        .map((balance: any) => `${String(balance.asset).toUpperCase()}USDT`));
    }

    if (symbols.length === 0) {
      return new Response(JSON.stringify({
        success: false,
        error: 'TRADE_SYMBOL_UNIVERSE_REQUIRED',
        truthStatus: 'no_data',
        generatedValues: false,
      }), { status: 409, headers: { ...corsHeaders, 'Content-Type': 'application/json' } });
    }

    const records: Array<Record<string, unknown>> = [];
    const providerErrors: Array<{ symbol: string; status: number; message: string }> = [];
    for (const symbol of symbols) {
      const timestamp = Date.now();
      const queryString = `symbol=${symbol}&limit=500&timestamp=${timestamp}`;
      const signature = createHmac('sha256', apiSecret).update(queryString).digest('hex');
      const response = await fetch(`https://api.binance.com/api/v3/myTrades?${queryString}&signature=${signature}`, {
        headers: { 'X-MBX-APIKEY': apiKey },
      });
      const payload = await response.json();
      if (!response.ok) {
        providerErrors.push({ symbol, status: response.status, message: String(payload?.msg || 'unknown') });
        continue;
      }
      if (!Array.isArray(payload)) throw new Error(`BINANCE_TRADE_ARRAY_MISSING:${symbol}`);
      for (const trade of payload) {
        const tradeId = String(trade.id ?? '');
        const tradeTime = Number(trade.time);
        const price = requireFinite(trade.price, `${symbol}.price`);
        const quantity = requireFinite(trade.qty, `${symbol}.qty`);
        const quoteQuantity = requireFinite(trade.quoteQty, `${symbol}.quoteQty`, true);
        const fee = requireFinite(trade.commission, `${symbol}.commission`, true);
        if (!tradeId || !Number.isFinite(tradeTime) || !trade.commissionAsset) {
          throw new Error(`INCOMPLETE_BINANCE_TRADE_RECEIPT:${symbol}`);
        }
        const sourceTimestamp = new Date(tradeTime).toISOString();
        records.push({
          transaction_id: `binance:${symbol}:${tradeId}`,
          exchange: 'binance',
          symbol,
          side: trade.isBuyer === true ? 'BUY' : 'SELL',
          price,
          quantity,
          quote_qty: quoteQuantity,
          fee,
          fee_asset: String(trade.commissionAsset),
          timestamp: sourceTimestamp,
          user_id: user.id,
          truth_status: 'live',
          source_id: 'binance:/api/v3/myTrades',
          source_timestamp: sourceTimestamp,
          generated_values: false,
        });
      }
    }

    if (records.length > 0) {
      const { error: writeError } = await supabase
        .from('trade_records')
        .upsert(records, { onConflict: 'transaction_id', ignoreDuplicates: true });
      if (writeError) throw new Error(`TRADE_BACKFILL_WRITE_FAILED:${writeError.message}`);
    }

    const sourceTimestamp = records.length > 0
      ? String(records.map((record) => record.source_timestamp).sort((a, b) => Date.parse(String(b)) - Date.parse(String(a)))[0])
      : null;
    return new Response(JSON.stringify({
      success: providerErrors.length === 0,
      receiptsRead: records.length,
      symbolsProcessed: symbols.length,
      providerErrors,
      truthStatus: records.length > 0 ? 'live' : 'no_data',
      sourceId: 'binance:/api/v3/myTrades',
      sourceTimestamp,
      generatedValues: false,
    }), {
      status: providerErrors.length === 0 ? 200 : 502,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    console.error('[backfill-trades]', message);
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
