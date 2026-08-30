import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { fetchLiveJson, requireFiniteNumber } from '../_shared/real_data.ts'

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

/**
 * Get Kraken Balances Edge Function
 * Prime Sentinel: GARY LECKEY 02111991
 * 
 * Fetches account balances from Kraken exchange
 */
serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response(null, { headers: corsHeaders });
  }

  try {
    const krakenApiKey = Deno.env.get('KRAKEN_API_KEY');
    const krakenApiSecret = Deno.env.get('KRAKEN_API_SECRET');

    // NO DEMO MODE - Return explicit error if no credentials
    // This prevents silent fallback to fake data
    if (!krakenApiKey || !krakenApiSecret) {
      console.error('[get-kraken-balances] ❌ NO CREDENTIALS - Cannot fetch real balances');
      return new Response(
        JSON.stringify({
          success: false,
          exchange: 'kraken',
          error: 'NO_CREDENTIALS',
          message: 'Kraken API credentials not configured. Cannot fetch live balances.',
          dataSource: 'NONE',
          mode: 'error'
        }),
        { 
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
          status: 401 
        }
      );
    }

    // Production Kraken API call
    const nonce = Date.now().toString();
    const apiPath = '/0/private/Balance';
    const apiData = `nonce=${nonce}`;

    // Create signature
    const encoder = new TextEncoder();
    const sha256Hash = await crypto.subtle.digest(
      'SHA-256',
      encoder.encode(nonce + apiData)
    );
    
    const apiSecretDecoded = Uint8Array.from(atob(krakenApiSecret), c => c.charCodeAt(0));
    const key = await crypto.subtle.importKey(
      'raw',
      apiSecretDecoded,
      { name: 'HMAC', hash: 'SHA-512' },
      false,
      ['sign']
    );
    
    const pathBytes = encoder.encode(apiPath);
    const combined = new Uint8Array(pathBytes.length + sha256Hash.byteLength);
    combined.set(pathBytes);
    combined.set(new Uint8Array(sha256Hash), pathBytes.length);
    
    const signature = await crypto.subtle.sign('HMAC', key, combined);
    const signatureBase64 = btoa(String.fromCharCode(...new Uint8Array(signature)));

    const response = await fetch(`https://api.kraken.com${apiPath}`, {
      method: 'POST',
      headers: {
        'API-Key': krakenApiKey,
        'API-Sign': signatureBase64,
        'Content-Type': 'application/x-www-form-urlencoded'
      },
      body: apiData
    });

    if (!response.ok) {
      throw new Error(`Kraken API error: ${response.status}`);
    }

    const data = await response.json();

    if (data.error && data.error.length > 0) {
      throw new Error(`Kraken error: ${data.error.join(', ')}`);
    }

    // Complete Kraken asset mapping (from Python aureon_unified_ecosystem.py)
    const krakenAssetMap: Record<string, string> = {
      'XXBT': 'BTC', 'XETH': 'ETH', 'XXLM': 'XLM', 'XXRP': 'XRP',
      'XLTC': 'LTC', 'XZEC': 'ZEC', 'XXMR': 'XMR', 'XREP': 'REP',
      'XMLN': 'MLN', 'XETC': 'ETC', 'XDAO': 'DAO', 'XICN': 'ICN',
      'ZUSD': 'USD', 'ZEUR': 'EUR', 'ZGBP': 'GBP', 'ZJPY': 'JPY',
      'ZCAD': 'CAD', 'ZAUD': 'AUD', 'XDOGE': 'DOGE', 'XBT': 'BTC',
    };
    
    const normalizeKrakenAsset = (asset: string): string => {
      if (krakenAssetMap[asset]) return krakenAssetMap[asset];
      // Remove X/Z prefix if 4 chars, otherwise keep as-is
      if (asset.length === 4 && (asset.startsWith('X') || asset.startsWith('Z'))) {
        return asset.substring(1);
      }
      return asset;
    };
    
    const rawBalances = Object.entries(data.result || {}).map(([asset, balance]) => ({
      asset: normalizeKrakenAsset(asset),
      free: requireFiniteNumber(balance, `balance.${asset}`),
      locked: 0,
      total: requireFiniteNumber(balance, `balance.${asset}`),
    })).filter(balance => balance.total !== 0);

    const assetPairsUrl = 'https://api.kraken.com/0/public/AssetPairs';
    const assetPairsPayload = await fetchLiveJson<any>(assetPairsUrl);
    if (assetPairsPayload.error?.length) throw new Error(`Kraken AssetPairs error: ${assetPairsPayload.error.join(', ')}`);
    const usdPairs = new Map<string, string>();
    for (const [pairId, pair] of Object.entries<any>(assetPairsPayload.result || {})) {
      const wsname = String(pair.wsname || '');
      const [base, quote] = wsname.split('/');
      if (base && quote === 'USD') usdPairs.set(normalizeKrakenAsset(base), pairId);
    }

    const requestedPairs = [...new Set(rawBalances.map(balance => usdPairs.get(balance.asset)).filter(Boolean))] as string[];
    let tickerResult: Record<string, any> = {};
    if (requestedPairs.length) {
      const tickerUrl = `https://api.kraken.com/0/public/Ticker?pair=${encodeURIComponent(requestedPairs.join(','))}`;
      const tickerPayload = await fetchLiveJson<any>(tickerUrl);
      if (tickerPayload.error?.length) throw new Error(`Kraken Ticker error: ${tickerPayload.error.join(', ')}`);
      tickerResult = tickerPayload.result || {};
    }

    const collectedAt = new Date().toISOString();
    const balances = rawBalances.map(balance => {
      const pairId = usdPairs.get(balance.asset);
      const ticker = pairId ? tickerResult[pairId] : null;
      const usdPrice = balance.asset === 'USD' ? 1 : ticker?.c?.[0] == null ? null : requireFiniteNumber(ticker.c[0], `ticker.${balance.asset}`);
      return {
        ...balance,
        usdPrice,
        usdValue: usdPrice === null ? null : balance.total * usdPrice,
        valuationTruthStatus: usdPrice === null ? 'no_data' : 'live',
        valuationSource: usdPrice === null ? null : balance.asset === 'USD' ? 'Kraken account denomination' : `Kraken ${pairId} ticker`,
      };
    });
    const valuedBalances = balances.filter(balance => balance.usdValue !== null);
    const totalUsdValue = valuedBalances.reduce((sum, balance) => sum + Number(balance.usdValue), 0);
    const valuationComplete = valuedBalances.length === balances.length;

    console.log(`Fetched ${balances.length} Kraken balances`);

    return new Response(
      JSON.stringify({
        success: true,
        exchange: 'kraken',
        balances,
        totalUsdValue,
        valuationComplete,
        mode: 'live',
        truthStatus: 'live',
        sourceId: 'kraken_private_and_public',
        sourceUrls: ['https://api.kraken.com/0/private/Balance', assetPairsUrl, 'https://api.kraken.com/0/public/Ticker'],
        collectedAt,
        generatedValues: false
      }),
      { 
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        status: 200 
      }
    );

  } catch (error) {
    console.error('Kraken balances error:', error);
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    return new Response(
      JSON.stringify({ 
        error: errorMessage,
        success: false,
        exchange: 'kraken'
      }),
      { 
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        status: 500 
      }
    );
  }
});
