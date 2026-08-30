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

  try {
    const supabaseUrl = Deno.env.get('SUPABASE_URL')!;
    const supabaseKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;
    const supabase = createClient(supabaseUrl, supabaseKey);

    // Get all active credentials
    const { data: credentials, error: credError } = await supabase
      .from('binance_credentials')
      .select('*')
      .eq('is_active', true);

    if (credError) throw credError;

    if (!credentials || credentials.length === 0) {
      return new Response(
        JSON.stringify({ success: false, error: 'No active Binance credentials found' }),
        { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 400 }
      );
    }

    // Fetch all current prices from Binance
    let priceMap: Record<string, number> = {};
    try {
      const priceResponse = await fetch('https://api.binance.com/api/v3/ticker/price');
      if (priceResponse.ok) {
        const prices = await priceResponse.json();
        priceMap = prices.reduce((acc: Record<string, number>, p: any) => {
          acc[p.symbol] = parseFloat(p.price);
          return acc;
        }, {});
        console.log(`✅ Fetched ${Object.keys(priceMap).length} price pairs`);
      }
    } catch (error) {
      console.error('Failed to fetch prices:', error);
    }
    const tetherResponse = await fetch('https://api.coingecko.com/api/v3/simple/price?ids=tether&vs_currencies=usd');
    const tetherPayload = tetherResponse.ok ? await tetherResponse.json() : {};
    const tetherUsd = Number(tetherPayload?.tether?.usd);

    // Fetch balances from all accounts (all 11 bots access the same wallet)
    const accountBalances = [];

    for (const cred of credentials) {
      const apiKey = await decryptCredential(cred.api_key_encrypted, 'v2');
      const apiSecret = await decryptCredential(cred.api_secret_encrypted, 'v2');

      try {
        // Get account balance from Binance
        const timestamp = Date.now();
        const queryString = `timestamp=${timestamp}`;
        
        // Sign request
        const crypto = await import("https://deno.land/std@0.177.0/crypto/mod.ts");
        const encoder = new TextEncoder();
        const key = await crypto.crypto.subtle.importKey(
          "raw",
          encoder.encode(apiSecret),
          { name: "HMAC", hash: "SHA-256" },
          false,
          ["sign"]
        );
        const signatureBuffer = await crypto.crypto.subtle.sign(
          "HMAC",
          key,
          encoder.encode(queryString)
        );
        const signature = Array.from(new Uint8Array(signatureBuffer))
          .map(b => b.toString(16).padStart(2, '0'))
          .join('');

        // Call Binance API
        const response = await fetch(
          `https://api.binance.com/api/v3/account?${queryString}&signature=${signature}`,
          {
            headers: {
              'X-MBX-APIKEY': apiKey,
            },
          }
        );

        if (!response.ok) {
          console.error(`Failed to fetch balance for ${cred.name}:`, await response.text());
          continue;
        }

        const accountData = await response.json();
        
        // Extract relevant balances and calculate USD value
        const balances: any = {};
        let accountUSDValue: number | null = 0;

        for (const balance of accountData.balances) {
          const free = parseFloat(balance.free);
          const locked = parseFloat(balance.locked);
          const total = free + locked;
          
          if (total > 0) {
            let usdValue: number | null = null;
            
            // Calculate USD value
            if (balance.asset === 'USDT' && Number.isFinite(tetherUsd) && tetherUsd > 0) {
              usdValue = total * tetherUsd;
            } else {
              // Try to find price in USDT pair
              const usdtSymbol = `${balance.asset}USDT`;
              if (priceMap[usdtSymbol]) {
                usdValue = Number.isFinite(tetherUsd) && tetherUsd > 0
                  ? total * priceMap[usdtSymbol] * tetherUsd
                  : null;
              } else {
                // Try BTC pair, then convert BTC to USDT
                const btcSymbol = `${balance.asset}BTC`;
                if (priceMap[btcSymbol] && priceMap['BTCUSDT']) {
                  usdValue = Number.isFinite(tetherUsd) && tetherUsd > 0
                    ? total * priceMap[btcSymbol] * priceMap['BTCUSDT'] * tetherUsd
                    : null;
                }
              }
            }
            
            balances[balance.asset] = {
              free,
              locked,
              total,
              usdValue,
              valuationTruthStatus: usdValue === null ? 'no_data' : 'real_derived'
            };
            
            accountUSDValue = accountUSDValue === null || usdValue === null
              ? null
              : accountUSDValue + usdValue;
          }
        }

        accountBalances.push({
          name: cred.name,
          balances,
          canTrade: accountData.canTrade,
          canWithdraw: accountData.canWithdraw,
          canDeposit: accountData.canDeposit,
          updateTime: accountData.updateTime,
        });

      } catch (error) {
        console.error(`Error fetching balance for ${cred.name}:`, error);
        accountBalances.push({
          name: cred.name,
          error: error instanceof Error ? error.message : 'Unknown error',
        });
      }
    }

    // All 11 accounts access the same wallet, so use only the first successful account's data
    const firstSuccessfulAccount = accountBalances.find(a => !a.error);
    let walletTotals = {
      USDT: 0,
      BTC: 0,
      ETH: 0,
      totalUSDValue: null as number | null
    };

    if (firstSuccessfulAccount && firstSuccessfulAccount.balances) {
      for (const [asset, balance] of Object.entries(firstSuccessfulAccount.balances)) {
        const bal = balance as { total: number; usdValue?: number | null };
        if (asset === 'USDT') walletTotals.USDT = bal.total;
        if (asset === 'BTC') walletTotals.BTC = bal.total;
        if (asset === 'ETH') walletTotals.ETH = bal.total;
      }
      const values = Object.values(firstSuccessfulAccount.balances)
        .map((entry: any) => entry.usdValue as number | null);
      const validValues = values.filter(
        (value): value is number => value !== null && Number.isFinite(value),
      );
      walletTotals.totalUSDValue = validValues.length === values.length
        ? validValues.reduce((sum, value) => sum + value, 0)
        : null;
    }

    console.log(`✅ Fetched balances from ${accountBalances.length} bots (1 shared wallet)`);
    console.log(`Wallet Totals - USDT: ${walletTotals.USDT.toFixed(2)}, BTC: ${walletTotals.BTC.toFixed(6)}, ETH: ${walletTotals.ETH.toFixed(6)}`);
    console.log('Portfolio valuation status:', walletTotals.totalUSDValue === null ? 'no_data' : 'real_derived');

    return new Response(
      JSON.stringify({
        success: true,
        accounts: accountBalances,
        totals: walletTotals,
        timestamp: new Date().toISOString(),
        truthStatus: 'live',
        valuationTruthStatus: walletTotals.totalUSDValue === null ? 'no_data' : 'real_derived',
        generatedValues: false,
      }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    );

  } catch (error) {
    console.error('Get balances error:', error);
    return new Response(
      JSON.stringify({ success: false, error: error instanceof Error ? error.message : 'Unknown error' }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 500 }
    );
  }
});
