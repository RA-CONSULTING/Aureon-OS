import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";
import { decryptCredential as decryptStoredCredential } from "../_shared/credential_crypto.ts";

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};

// Rate limit configuration per exchange (in milliseconds)
const RATE_LIMITS = {
  binance: 10000,    // 10 seconds between calls
  kraken: 300000,    // 5 MINUTES (Kraken is strict; avoid "EAPI:Rate limit exceeded")
  alpaca: 15000,     // 15 seconds
  capital: 60000,    // 60 seconds (Capital.com is strict)
};

// Database-backed cache table name
const BALANCE_CACHE_TABLE = 'exchange_balance_cache';

interface CachedBalanceData {
  exchange: string;
  user_id: string;
  balance_data: ExchangeBalance;
  cached_at: string;
}

// Check database cache for exchange balance
async function getDbCachedBalance(
  supabase: any,
  userId: string,
  exchange: string
): Promise<{ data: ExchangeBalance | null; canFetch: boolean; cachedAt?: string; hasRow?: boolean }> {
  try {
    const { data, error } = await supabase
      .from(BALANCE_CACHE_TABLE)
      .select('*')
      .eq('user_id', userId)
      .eq('exchange', exchange)
      .single();

    if (error || !data) {
      return { data: null, canFetch: true, hasRow: false };
    }

    const cachedAtIso = data.cached_at as string;
    const cachedAt = new Date(cachedAtIso).getTime();
    const elapsed = Date.now() - cachedAt;
    const rateLimit = RATE_LIMITS[exchange as keyof typeof RATE_LIMITS] || 30000;

    const balanceData = data.balance_data as ExchangeBalance | null;
    const sourceTime = balanceData?.sourceTimestamp ? new Date(balanceData.sourceTimestamp).getTime() : Number.NaN;
    const sourceAge = Number.isFinite(sourceTime) ? Date.now() - sourceTime : Number.POSITIVE_INFINITY;

    // If the cached payload is an error/offline result, avoid hammering the exchange.
    // We allow quicker retry for "Invalid nonce" (fixable), but respect strict backoff for rate limits.
    const isErrorPayload =
      !balanceData ||
      balanceData.connected === false ||
      !Array.isArray(balanceData.assets) ||
      balanceData.truthStatus !== 'live' ||
      balanceData.generatedValues !== false ||
      sourceAge < 0 ||
      sourceAge >= 300000;

    if (isErrorPayload) {
      const errorText = typeof balanceData?.error === 'string' ? balanceData.error : '';
      const isRateLimit = /rate limit exceeded/i.test(errorText);
      const isInvalidNonce = /invalid nonce/i.test(errorText);
      const isFetching = /fetch(ing)? in progress|fetching\.\.\./i.test(errorText);

      const backoffMs =
        isRateLimit ? rateLimit :
        isInvalidNonce ? 15000 :
        isFetching ? 5000 :
        60000;

      const canFetch = elapsed >= backoffMs;

      return {
        data:
          elapsed < 300000 && balanceData
            ? {
                ...balanceData,
                error: canFetch
                  ? balanceData.error
                  : `${balanceData.error || 'Cached error'} (retry in ${Math.max(0, Math.ceil((backoffMs - elapsed) / 1000))}s)`,
              }
            : null,
        canFetch,
        cachedAt: cachedAtIso,
        hasRow: true,
      };
    }

    // Can fetch if rate limit has passed
    const canFetch = elapsed >= rateLimit;

    // Return cached data if not too stale (5 minutes max)
    if (elapsed < 300000 && balanceData) {
      return {
        data: {
          ...balanceData,
          error: canFetch ? undefined : `Cached ${Math.round(elapsed / 1000)}s ago (rate limited)`,
        },
        canFetch,
        cachedAt: cachedAtIso,
        hasRow: true,
      };
    }

    return { data: null, canFetch: true, cachedAt: cachedAtIso, hasRow: true };
  } catch {
    return { data: null, canFetch: true, hasRow: false };
  }
}

// Optimistic lock to prevent concurrent "fresh" fetches across parallel edge invocations.
// We acquire the lock by atomically bumping cached_at (or inserting a placeholder row).
async function acquireFetchLock(
  supabase: any,
  userId: string,
  exchange: string,
  prevCachedAt?: string,
  existingData?: ExchangeBalance | null
): Promise<boolean> {
  const nowIso = new Date().toISOString();
  const placeholder: ExchangeBalance =
    existingData ?? ({
      exchange,
      connected: false,
      assets: [],
      totalUsd: null,
      truthStatus: 'no_data',
      sourceTimestamp: null,
      generatedValues: false,
      error: 'Fetching...',
    } as ExchangeBalance);

  // If a row exists, attempt a compare-and-swap on cached_at.
  if (prevCachedAt) {
    const { count } = await supabase
      .from(BALANCE_CACHE_TABLE)
      .update({ cached_at: nowIso, balance_data: placeholder }, { count: 'exact' })
      .eq('user_id', userId)
      .eq('exchange', exchange)
      .eq('cached_at', prevCachedAt);

    if (count === 1) return true;
    return false;
  }

  // If no row exists, try to insert. Unique constraint (user_id, exchange) prevents races.
  const { error } = await supabase.from(BALANCE_CACHE_TABLE).insert({
    user_id: userId,
    exchange,
    balance_data: placeholder,
    cached_at: nowIso,
  });

  if (!error) return true;

  // Another invocation probably inserted first.
  return false;
}


// Save balance to database cache
async function setDbCachedBalance(
  supabase: any, 
  userId: string, 
  exchange: string, 
  balanceData: ExchangeBalance
): Promise<void> {
  try {
    await supabase
      .from(BALANCE_CACHE_TABLE)
      .upsert({
        user_id: userId,
        exchange: exchange,
        balance_data: balanceData,
        cached_at: new Date().toISOString()
      }, { 
        onConflict: 'user_id,exchange' 
      });
  } catch (e) {
    console.error(`[get-user-balances] Failed to cache ${exchange} balance:`, e);
  }
}

// Move interface before cache functions that reference it
interface ExchangeBalance {
  exchange: string;
  connected: boolean;
  assets: Array<{ asset: string; free: number; locked: number; usdValue: number | null; valuationTruthStatus: "real_derived" | "no_data" }>;
  totalUsd: number | null;
  truthStatus: "live" | "no_data";
  sourceTimestamp: string | null;
  generatedValues: false;
  error?: string;
}

function noDataBalance(exchange: string, error: string): ExchangeBalance {
  return {
    exchange,
    connected: false,
    assets: [],
    totalUsd: null,
    truthStatus: "no_data",
    sourceTimestamp: null,
    generatedValues: false,
    error,
  };
}

function liveBalance(
  exchange: string,
  assets: ExchangeBalance["assets"],
  sourceTimestamp: string,
): ExchangeBalance {
  const valuations = assets.map((asset) => asset.usdValue);
  const totalUsd = valuations.every((value) => value !== null && Number.isFinite(value))
    ? (valuations as number[]).reduce((sum, value) => sum + value, 0)
    : null;
  return {
    exchange,
    connected: true,
    assets,
    totalUsd,
    truthStatus: "live",
    sourceTimestamp,
    generatedValues: false,
  };
}


async function fetchBinanceBalances(apiKey: string, apiSecret: string): Promise<ExchangeBalance> {
  try {
    const timestamp = Date.now();
    const queryString = `timestamp=${timestamp}`;
    
    const encoder = new TextEncoder();
    const key = await crypto.subtle.importKey(
      'raw',
      encoder.encode(apiSecret),
      { name: 'HMAC', hash: 'SHA-256' },
      false,
      ['sign']
    );
    const signature = await crypto.subtle.sign('HMAC', key, encoder.encode(queryString));
    const signatureHex = Array.from(new Uint8Array(signature))
      .map(b => b.toString(16).padStart(2, '0'))
      .join('');

    const response = await fetch(
      `https://api.binance.com/api/v3/account?${queryString}&signature=${signatureHex}`,
      { headers: { 'X-MBX-APIKEY': apiKey } }
    );

    if (!response.ok) {
      throw new Error(`Binance API error: ${response.status}`);
    }

    const data = await response.json();
    
    // Get prices for USD conversion
    const pricesRes = await fetch('https://api.binance.com/api/v3/ticker/price');
    if (!pricesRes.ok) throw new Error(`Binance ticker API error: ${pricesRes.status}`);
    const prices = await pricesRes.json();
    const priceMap: Record<string, number> = {};
    prices.forEach((p: { symbol: string; price: string }) => {
      priceMap[p.symbol] = parseFloat(p.price);
    });

    const tetherRes = await fetch('https://api.coingecko.com/api/v3/simple/price?ids=tether&vs_currencies=usd');
    if (!tetherRes.ok) throw new Error(`CoinGecko tether price error: ${tetherRes.status}`);
    const tetherPayload = await tetherRes.json();
    const tetherUsd = Number(tetherPayload?.tether?.usd);
    if (!Number.isFinite(tetherUsd) || tetherUsd <= 0) throw new Error('CoinGecko tether USD price missing');

    const assets: ExchangeBalance['assets'] = [];

    for (const bal of data.balances) {
      const free = parseFloat(bal.free);
      const locked = parseFloat(bal.locked);
      if (free > 0 || locked > 0) {
        let usdValue: number | null = null;
        if (bal.asset === 'USD') {
          usdValue = free + locked;
        } else if (bal.asset === 'USDT') {
          usdValue = (free + locked) * tetherUsd;
        } else if (priceMap[`${bal.asset}USDT`]) {
          usdValue = (free + locked) * priceMap[`${bal.asset}USDT`] * tetherUsd;
        }
        assets.push({
          asset: bal.asset,
          free,
          locked,
          usdValue,
          valuationTruthStatus: usdValue === null ? 'no_data' : 'real_derived',
        });
      }
    }

    return liveBalance('binance', assets, response.headers.get('date') || new Date().toISOString());
  } catch (error) {
    console.error('[get-user-balances] Binance error:', error);
    return noDataBalance('binance', String(error));
  }
}

// Kraken asset name mapping - matches Python kraken_client.py
const KRAKEN_ASSET_MAP: Record<string, string> = {
  'XXBT': 'BTC',
  'XBT': 'BTC',
  'XETH': 'ETH',
  'XXLM': 'XLM',
  'XLTC': 'LTC',
  'XXRP': 'XRP',
  'XXDG': 'DOGE',
  'XZEC': 'ZEC',
  'XREP': 'REP',
  'XETC': 'ETC',
  'XMLN': 'MLN',
  'XXMR': 'XMR',
  'ZUSD': 'USD',
  'ZEUR': 'EUR',
  'ZGBP': 'GBP',
  'ZCAD': 'CAD',
  'ZJPY': 'JPY',
  'ZAUD': 'AUD',
  'USDT': 'USDT',
  'USDC': 'USDC',
  'DAI': 'DAI',
  'DOT': 'DOT',
  'SOL': 'SOL',
  'ADA': 'ADA',
  'MATIC': 'MATIC',
  'ATOM': 'ATOM',
  'LINK': 'LINK',
  'UNI': 'UNI',
  'AVAX': 'AVAX',
  'SHIB': 'SHIB',
  'TRX': 'TRX',
  'NEAR': 'NEAR',
  'APE': 'APE',
  'SAND': 'SAND',
  'MANA': 'MANA',
  'CRV': 'CRV',
  'AAVE': 'AAVE',
  'FTM': 'FTM',
  'GRT': 'GRT',
  'ALGO': 'ALGO',
  'XTZ': 'XTZ',
  'EOS': 'EOS',
  'FLOW': 'FLOW',
  'AXS': 'AXS',
  'CHZ': 'CHZ',
  'ENJ': 'ENJ',
  'BAT': 'BAT',
  'COMP': 'COMP',
  'MKR': 'MKR',
  'SNX': 'SNX',
  'YFI': 'YFI',
  'SUSHI': 'SUSHI',
  '1INCH': '1INCH',
  'OCEAN': 'OCEAN',
  'STORJ': 'STORJ',
  'OMG': 'OMG',
  'ZRX': 'ZRX',
  'KNC': 'KNC',
  'KEEP': 'KEEP',
  'ANT': 'ANT',
  'REN': 'REN',
  'LRC': 'LRC',
  'KAVA': 'KAVA',
  'WAVES': 'WAVES',
  'ICX': 'ICX',
  'NANO': 'NANO',
  'OMG.S': 'OMG',
  'SC': 'SC',
  'QTUM': 'QTUM',
  'LSK': 'LSK',
  'BABY': 'BABY',
  'BABY.S': 'BABY',
};

function cleanKrakenAsset(krakenName: string): string {
  // First check direct mapping
  if (KRAKEN_ASSET_MAP[krakenName]) {
    return KRAKEN_ASSET_MAP[krakenName];
  }
  
  // Handle staked assets (e.g., ETH2.S, DOT.S)
  const unstaked = krakenName.replace(/\.S$/, '');
  if (KRAKEN_ASSET_MAP[unstaked]) {
    return KRAKEN_ASSET_MAP[unstaked];
  }
  
  // Legacy prefix stripping for unknown assets
  let cleaned = krakenName;
  
  // Handle XX prefix (e.g., XXBT -> BTC is already mapped, but XXABC -> ABC)
  if (cleaned.startsWith('XX') && cleaned.length > 2) {
    cleaned = cleaned.slice(2);
  }
  // Handle single X prefix but preserve XRP, XLM, XTZ, XDG (DOGE)
  else if (cleaned.startsWith('X') && cleaned.length > 1 && 
           !['XRP', 'XLM', 'XTZ', 'XDG'].includes(cleaned)) {
    cleaned = cleaned.slice(1);
  }
  // Handle Z prefix for fiat (ZUSD, ZEUR etc) - already mapped above
  else if (cleaned.startsWith('Z') && cleaned.length > 1) {
    cleaned = cleaned.slice(1);
  }
  
  return cleaned;
}

async function fetchKrakenBalances(apiKey: string, apiSecret: string): Promise<ExchangeBalance> {
  try {
    // Kraken requires a strictly increasing integer nonce.
    // Using nanosecond-scale BigInt reduces collision risk under concurrent calls.
    const nonce = (BigInt(Date.now()) * 1000000n).toString();
    const path = '/0/private/Balance';
    const postData = `nonce=${nonce}`;

    const encoder = new TextEncoder();
    const secretDecoded = Uint8Array.from(atob(apiSecret), c => c.charCodeAt(0));

    const sha256Hash = await crypto.subtle.digest('SHA-256', encoder.encode(nonce + postData));
    const message = new Uint8Array([...encoder.encode(path), ...new Uint8Array(sha256Hash)]);

    const hmacKey = await crypto.subtle.importKey('raw', secretDecoded, { name: 'HMAC', hash: 'SHA-512' }, false, ['sign']);
    const signature = await crypto.subtle.sign('HMAC', hmacKey, message);
    const signatureB64 = btoa(String.fromCharCode(...new Uint8Array(signature)));

    const response = await fetch(`https://api.kraken.com${path}`, {
      method: 'POST',
      headers: {
        'API-Key': apiKey,
        'API-Sign': signatureB64,
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: postData,
    });
    if (!response.ok) throw new Error(`Kraken balance API error: ${response.status}`);

    const data = await response.json();
    console.log('[get-user-balances] Kraken raw balances:', JSON.stringify(data.result));
    
    if (data.error && data.error.length > 0) {
      throw new Error(data.error[0]);
    }

    // Fetch ALL Kraken ticker prices for USD conversion
    const priceMap: Record<string, number> = {};
    try {
      const tickerRes = await fetch('https://api.kraken.com/0/public/Ticker');
      if (!tickerRes.ok) throw new Error(`Kraken ticker API error: ${tickerRes.status}`);
      const tickerData = await tickerRes.json();
      
      if (tickerData.result) {
        for (const [pair, ticker] of Object.entries(tickerData.result)) {
          const t = ticker as any;
          const price = Number(t.c?.[0]);
          
          // Store USD pairs for conversion
          if (pair.includes('USD')) {
            // Extract base asset - handle various Kraken pair formats
            // XXBTZUSD, XETHZUSD, SOLUSD, ADAUSD, etc.
            let base = pair;
            
            // Remove USD suffix variants
            base = base.replace(/ZUSD$/, '').replace(/USD$/, '');
            
            // Clean the base using our mapping
            const cleanBase = cleanKrakenAsset(base);
            
            if (Number.isFinite(price) && price > 0) {
              priceMap[cleanBase] = price;
              priceMap[base] = price;
            }
          }
        }
      }
      console.log('[get-user-balances] Kraken prices loaded:', Object.keys(priceMap).slice(0, 20).join(', '), '...');
    } catch (priceError) {
      console.warn('[get-user-balances] Failed to fetch Kraken prices:', priceError);
    }

    const assets: ExchangeBalance['assets'] = [];

    // Process ALL balances from Kraken
    for (const [rawAsset, balance] of Object.entries(data.result || {})) {
      const amount = parseFloat(balance as string);
      
      if (amount > 0) {
        // Use proper asset mapping
        const displayAsset = cleanKrakenAsset(rawAsset);
        let usdValue: number | null = null;
        
        if (displayAsset === 'USD') {
          usdValue = amount;
        } else {
          const price = priceMap[displayAsset] ?? priceMap[rawAsset];
          usdValue = Number.isFinite(price) && price > 0 ? amount * price : null;
        }
        
        assets.push({
          asset: displayAsset,
          free: amount,
          locked: 0,
          usdValue,
          valuationTruthStatus: usdValue === null ? 'no_data' : 'real_derived',
        });
      }
    }

    return liveBalance('kraken', assets, response.headers.get('date') || new Date().toISOString());
  } catch (error) {
    console.error('[get-user-balances] Kraken error:', error);
    return noDataBalance('kraken', String(error));
  }
}

async function fetchAlpacaBalances(apiKey: string, secretKey: string): Promise<ExchangeBalance> {
  try {
    const response = await fetch('https://api.alpaca.markets/v2/account', {
      headers: {
        'APCA-API-KEY-ID': apiKey,
        'APCA-API-SECRET-KEY': secretKey,
      },
    });

    if (!response.ok) {
      throw new Error(`Alpaca API error: ${response.status}`);
    }

    const data = await response.json();
    const equity = Number(data.equity);
    if (!Number.isFinite(equity)) throw new Error('Alpaca equity missing');

    return liveBalance('alpaca', [{
      asset: 'USD_EQUITY',
      free: equity,
      locked: 0,
      usdValue: equity,
      valuationTruthStatus: 'real_derived',
    }], response.headers.get('date') || new Date().toISOString());
  } catch (error) {
    console.error('[get-user-balances] Alpaca error:', error);
    return noDataBalance('alpaca', String(error));
  }
}

async function fetchCapitalBalances(apiKey: string, password: string, identifier: string): Promise<ExchangeBalance> {
  try {
    // Create session
    const sessionRes = await fetch('https://api-capital.backend-capital.com/api/v1/session', {
      method: 'POST',
      headers: {
        'X-CAP-API-KEY': apiKey,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ identifier, password }),
    });

    if (!sessionRes.ok) {
      throw new Error(`Capital.com auth failed: ${sessionRes.status}`);
    }

    const cst = sessionRes.headers.get('CST');
    const securityToken = sessionRes.headers.get('X-SECURITY-TOKEN');

    if (!cst || !securityToken) {
      throw new Error('Missing auth tokens');
    }

    // Get accounts
    const accountsRes = await fetch('https://api-capital.backend-capital.com/api/v1/accounts', {
      headers: {
        'X-CAP-API-KEY': apiKey,
        'CST': cst,
        'X-SECURITY-TOKEN': securityToken,
      },
    });
    if (!accountsRes.ok) throw new Error(`Capital.com accounts API error: ${accountsRes.status}`);

    const accountsData = await accountsRes.json();
    const accounts = accountsData.accounts || [];
    const fxRes = await fetch('https://open.er-api.com/v6/latest/USD');
    if (!fxRes.ok) throw new Error(`FX provider error: ${fxRes.status}`);
    const fxData = await fxRes.json();
    const fxRates = fxData?.rates ?? {};
    const assets: ExchangeBalance['assets'] = [];

    for (const acc of accounts) {
      const balance = Number(acc.balance?.balance);
      if (!Number.isFinite(balance)) throw new Error('Capital.com account balance missing');
      const currency = String(acc.currency || '').toUpperCase();
      const fxRate = currency === 'USD' ? 1 : Number(fxRates[currency]);
      const usdValue = Number.isFinite(fxRate) && fxRate > 0 ? balance / fxRate : null;
      assets.push({
        asset: currency || 'UNKNOWN',
        free: balance,
        locked: 0,
        usdValue,
        valuationTruthStatus: usdValue === null ? 'no_data' : 'real_derived',
      });
    }

    return liveBalance('capital', assets, accountsRes.headers.get('date') || new Date().toISOString());
  } catch (error) {
    console.error('[get-user-balances] Capital.com error:', error);
    return noDataBalance('capital', String(error));
  }
}

serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response(null, { headers: corsHeaders });
  }

  console.log('[get-user-balances] Request received');

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

    console.log('[get-user-balances] User verified:', user.id);

    // Get user's credentials
    const supabase = createClient(supabaseUrl, supabaseServiceKey);
    const { data: session, error: sessionError } = await supabase
      .from('aureon_user_sessions')
      .select('*')
      .eq('user_id', user.id)
      .single();

    if (sessionError || !session) {
      return new Response(
        JSON.stringify({ error: 'No session found' }),
        { status: 404, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      );
    }

    const balances: ExchangeBalance[] = [];
    const fetchPromises: Promise<ExchangeBalance>[] = [];

    // === Use USER-SAVED credentials (never global/shared secrets) ===
    const userCreds = {
      binance: { apiKey: null as string | null, apiSecret: null as string | null },
      kraken: { apiKey: null as string | null, apiSecret: null as string | null },
      alpaca: { apiKey: null as string | null, apiSecret: null as string | null },
      capital: { apiKey: null as string | null, password: null as string | null, identifier: null as string | null },
    };

    // Binance
    if (session.binance_api_key_encrypted && session.binance_api_secret_encrypted && session.binance_iv) {
      userCreds.binance.apiKey = await decryptStoredCredential(session.binance_api_key_encrypted, session.binance_iv);
      userCreds.binance.apiSecret = await decryptStoredCredential(session.binance_api_secret_encrypted, session.binance_iv);
    }

    // Kraken
    if (session.kraken_api_key_encrypted && session.kraken_api_secret_encrypted && session.kraken_iv) {
      userCreds.kraken.apiKey = await decryptStoredCredential(session.kraken_api_key_encrypted, session.kraken_iv);
      userCreds.kraken.apiSecret = await decryptStoredCredential(session.kraken_api_secret_encrypted, session.kraken_iv);
    }

    // Alpaca
    if (session.alpaca_api_key_encrypted && session.alpaca_secret_key_encrypted && session.alpaca_iv) {
      userCreds.alpaca.apiKey = await decryptStoredCredential(session.alpaca_api_key_encrypted, session.alpaca_iv);
      userCreds.alpaca.apiSecret = await decryptStoredCredential(session.alpaca_secret_key_encrypted, session.alpaca_iv);
    }

    // Capital.com
    if (session.capital_api_key_encrypted && session.capital_password_encrypted && session.capital_identifier_encrypted && session.capital_iv) {
      userCreds.capital.apiKey = await decryptStoredCredential(session.capital_api_key_encrypted, session.capital_iv);
      userCreds.capital.password = await decryptStoredCredential(session.capital_password_encrypted, session.capital_iv);
      userCreds.capital.identifier = await decryptStoredCredential(session.capital_identifier_encrypted, session.capital_iv);
    }

    console.log('[get-user-balances] Using user credentials:', {
      binance: !!userCreds.binance.apiKey,
      kraken: !!userCreds.kraken.apiKey,
      alpaca: !!userCreds.alpaca.apiKey,
      capital: !!userCreds.capital.apiKey,
    });

    // Fetch Binance balances with database-backed rate limiting
    if (userCreds.binance.apiKey && userCreds.binance.apiSecret) {
      const binanceCache = await getDbCachedBalance(supabase, user.id, 'binance');
      if (binanceCache.canFetch) {
        fetchPromises.push(
          fetchBinanceBalances(userCreds.binance.apiKey, userCreds.binance.apiSecret)
            .then(async (result) => { 
              await setDbCachedBalance(supabase, user.id, 'binance', result); 
              return result; 
            })
        );
      } else if (binanceCache.data) {
        balances.push(binanceCache.data);
      } else {
        balances.push(noDataBalance('binance', 'Rate limited, no cache'));
      }
    } else {
      balances.push(noDataBalance('binance', 'Not configured'));
    }

    // Fetch Kraken balances with database-backed rate limiting (2 MINUTES to avoid rate limit)
    if (userCreds.kraken.apiKey && userCreds.kraken.apiSecret) {
      const krakenCache = await getDbCachedBalance(supabase, user.id, 'kraken');

      if (krakenCache.canFetch) {
        // Acquire a cross-invocation lock so only ONE edge invocation hits Kraken when the window opens.
        const locked = await acquireFetchLock(
          supabase,
          user.id,
          'kraken',
          krakenCache.hasRow ? krakenCache.cachedAt : undefined,
          krakenCache.data
        );

        if (locked) {
          console.log('[get-user-balances] Kraken: fetching fresh data');
          fetchPromises.push(
            fetchKrakenBalances(userCreds.kraken.apiKey, userCreds.kraken.apiSecret)
              .then(async (result) => {
                await setDbCachedBalance(supabase, user.id, 'kraken', result);
                return result;
              })
          );
        } else if (krakenCache.data) {
          console.log('[get-user-balances] Kraken: fetch already in progress, using cached data');
          balances.push({
            ...krakenCache.data,
            error: krakenCache.data.error || 'Fetch in progress',
          });
        } else {
          balances.push(noDataBalance('kraken', 'Fetch in progress'));
        }
      } else if (krakenCache.data) {
        console.log('[get-user-balances] Kraken: using cached data (rate limited)');
        balances.push(krakenCache.data);
      } else {
        balances.push(noDataBalance('kraken', 'Rate limited, no cache'));
      }
    } else {
      balances.push(noDataBalance('kraken', 'Not configured'));
    }

    // Fetch Alpaca balances with database-backed rate limiting
    if (userCreds.alpaca.apiKey && userCreds.alpaca.apiSecret) {
      const alpacaCache = await getDbCachedBalance(supabase, user.id, 'alpaca');
      if (alpacaCache.canFetch) {
        fetchPromises.push(
          fetchAlpacaBalances(userCreds.alpaca.apiKey, userCreds.alpaca.apiSecret)
            .then(async (result) => { 
              await setDbCachedBalance(supabase, user.id, 'alpaca', result); 
              return result; 
            })
        );
      } else if (alpacaCache.data) {
        balances.push(alpacaCache.data);
      } else {
        balances.push(noDataBalance('alpaca', 'Rate limited, no cache'));
      }
    } else {
      balances.push(noDataBalance('alpaca', 'Not configured'));
    }

    // Fetch Capital.com balances with database-backed rate limiting (60s minimum)
    if (userCreds.capital.apiKey && userCreds.capital.password && userCreds.capital.identifier) {
      const capitalCache = await getDbCachedBalance(supabase, user.id, 'capital');
      if (capitalCache.canFetch) {
        fetchPromises.push(
          fetchCapitalBalances(userCreds.capital.apiKey, userCreds.capital.password, userCreds.capital.identifier)
            .then(async (result) => { 
              await setDbCachedBalance(supabase, user.id, 'capital', result); 
              return result; 
            })
        );
      } else if (capitalCache.data) {
        console.log('[get-user-balances] Capital.com: using cached data (rate limited)');
        balances.push(capitalCache.data);
      } else {
        balances.push(noDataBalance('capital', 'Rate limited, no cache'));
      }
    } else {
      balances.push(noDataBalance('capital', 'Not configured'));
    }

    // Wait for all fetches
    const fetchedBalances = await Promise.all(fetchPromises);
    balances.push(...fetchedBalances);

    const configuredExchanges = Object.entries(userCreds)
      .filter(([, credentials]) => Boolean(credentials.apiKey))
      .map(([exchange]) => exchange);
    const connectedExchanges = balances.filter(b => b.connected).map(b => b.exchange);
    const configuredBalanceRows = configuredExchanges.map(
      (exchange) => balances.find((balance) => balance.exchange === exchange),
    );
    const allConfiguredLive = configuredBalanceRows.length > 0 && configuredBalanceRows.every(
      (balance) => balance?.connected === true &&
        balance.truthStatus === 'live' &&
        balance.generatedValues === false &&
        balance.totalUsd !== null,
    );
    const totalEquityUsd = allConfiguredLive
      ? configuredBalanceRows.reduce((sum, balance) => sum + (balance?.totalUsd as number), 0)
      : null;

    console.log('[get-user-balances] Fetched balances from', connectedExchanges.length, 'exchanges, total:', totalEquityUsd);

    // CRITICAL: Update aureon_user_sessions with fetched balance so trading system can use it
    if (totalEquityUsd !== null) {
      const sourceTimestamps = configuredBalanceRows
        .map((balance) => balance?.sourceTimestamp)
        .filter((value): value is string => Boolean(value));
      const oldestSourceTimestamp = sourceTimestamps.sort()[0];
      const { error: updateError } = await supabase
        .from('aureon_user_sessions')
        .update({
          total_equity_usd: totalEquityUsd,
          measurement_truth_status: 'real_derived',
          measurement_source_id: configuredExchanges.map((exchange) => `${exchange}:account`).join(','),
          measurement_source_timestamp: oldestSourceTimestamp,
          measurement_collected_at: new Date().toISOString(),
          measurement_generated_values: false,
          updated_at: new Date().toISOString()
        })
        .eq('user_id', user.id);
      
      if (updateError) {
        console.error('[get-user-balances] Failed to update session balance:', updateError);
      } else {
        console.log('[get-user-balances] Updated session balance to:', totalEquityUsd);
      }
    }

    return new Response(
      JSON.stringify({
        success: totalEquityUsd !== null,
        balances,
        totalEquityUsd,
        connectedExchanges,
        configuredExchanges,
        truthStatus: totalEquityUsd === null ? 'no_data' : 'real_derived',
        generatedValues: false,
      }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: totalEquityUsd === null ? 503 : 200 }
    );

  } catch (error) {
    console.error('[get-user-balances] Error:', error);
    return new Response(
      JSON.stringify({ error: 'Failed to fetch balances' }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    );
  }
});
