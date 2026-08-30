import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2.49.4";
import { createHmac } from "node:crypto";
import { decryptCredential } from "../_shared/credential_crypto.ts";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

function isPrintableAscii(s: string) {
  if (!s) return false;
  if (/[\s\x00-\x1F\x7F]/.test(s)) return false;
  return /^[\x21-\x7E]+$/.test(s);
}

interface SpotPosition {
  asset: string;
  free: number;
  locked: number;
  total: number;
  usdValue: number | null;
  valuationTruthStatus: "real_derived" | "no_data";
  exchange: string;
}

serve(async (req) => {
  if (req.method === "OPTIONS") {
    return new Response(null, { headers: corsHeaders });
  }

  try {
    const authHeader = req.headers.get("Authorization");
    if (!authHeader) {
      return new Response(JSON.stringify({ error: "Missing authorization" }), {
        status: 401,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    const supabaseUrl = Deno.env.get("SUPABASE_URL")!;
    const supabaseAnonKey = Deno.env.get("SUPABASE_ANON_KEY")!;
    const supabaseServiceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;

    const anonSupabase = createClient(supabaseUrl, supabaseAnonKey);
    const token = authHeader.replace("Bearer ", "");
    const { data: { user }, error: authError } = await anonSupabase.auth.getUser(token);

    if (authError || !user) {
      return new Response(JSON.stringify({ error: "Unauthorized" }), {
        status: 401,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    const supabase = createClient(supabaseUrl, supabaseServiceKey);

    const { data: session, error: sessionError } = await supabase
      .from("aureon_user_sessions")
      .select("binance_api_key_encrypted, binance_api_secret_encrypted, binance_iv, kraken_api_key_encrypted, kraken_api_secret_encrypted, kraken_iv")
      .eq("user_id", user.id)
      .single();

    if (sessionError || !session) {
      return new Response(JSON.stringify({ error: "No session found" }), {
        status: 404,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    // Fetch prices for USD conversion
    const pricesRes = await fetch("https://api.binance.com/api/v3/ticker/price");
    const allPrices = pricesRes.ok ? await pricesRes.json() : [];
    const tetherRes = await fetch("https://api.coingecko.com/api/v3/simple/price?ids=tether&vs_currencies=usd");
    const tetherPayload = tetherRes.ok ? await tetherRes.json() : {};
    const tetherUsd = Number(tetherPayload?.tether?.usd);
    const priceMap: Record<string, number> = {};
    for (const p of allPrices) priceMap[p.symbol] = parseFloat(p.price);

    function getUsdValue(asset: string, total: number): number | null {
      if (asset === "USD") return total;
      if (!Number.isFinite(tetherUsd) || tetherUsd <= 0) return null;
      if (asset === "USDT") return total * tetherUsd;
      const usdtPair = `${asset}USDT`;
      const btcPair = `${asset}BTC`;
      if (priceMap[usdtPair]) return total * priceMap[usdtPair] * tetherUsd;
      if (priceMap[btcPair] && priceMap["BTCUSDT"]) return total * priceMap[btcPair] * priceMap["BTCUSDT"] * tetherUsd;
      return null;
    }

    const allPositions: SpotPosition[] = [];
    const errors: string[] = [];

    // ========== BINANCE ==========
    if (session.binance_api_key_encrypted && session.binance_api_secret_encrypted && session.binance_iv) {
      try {
        const binanceApiKey = (await decryptCredential(session.binance_api_key_encrypted, session.binance_iv)).trim();
        const binanceApiSecret = (await decryptCredential(session.binance_api_secret_encrypted, session.binance_iv)).trim();

        if (isPrintableAscii(binanceApiKey) && isPrintableAscii(binanceApiSecret) && binanceApiKey.length >= 16) {
          const timestamp = Date.now();
          const queryString = `timestamp=${timestamp}`;
          const signature = createHmac("sha256", binanceApiSecret).update(queryString).digest("hex");

          const accountRes = await fetch(`https://api.binance.com/api/v3/account?${queryString}&signature=${signature}`, {
            headers: { "X-MBX-APIKEY": binanceApiKey },
          });

          if (accountRes.ok) {
            const accountData = await accountRes.json();
            const balances = accountData.balances || [];
            for (const b of balances) {
              const free = parseFloat(b.free || "0");
              const locked = parseFloat(b.locked || "0");
              const total = free + locked;
              if (total > 0) {
                const usdValue = getUsdValue(b.asset, total);
                allPositions.push({
                  asset: b.asset,
                  free,
                  locked,
                  total,
                  usdValue,
                  valuationTruthStatus: usdValue === null ? "no_data" : "real_derived",
                  exchange: "binance",
                });
              }
            }
          } else {
            errors.push(`Binance: ${accountRes.status}`);
          }
        } else {
          errors.push("Binance: Invalid credentials");
        }
      } catch (e: any) {
        errors.push(`Binance: ${e.message}`);
      }
    }

    // ========== KRAKEN ==========
    // IMPORTANT: Avoid hammering Kraken private endpoints.
    // We reuse the existing database-backed cache populated by the portfolio balance fetch.
    // This prevents concurrent Balance calls (which can instantly trigger Kraken rate limits).
    {
      try {
        const { data: cachedRow } = await supabase
          .from("exchange_balance_cache")
          .select("balance_data, cached_at")
          .eq("user_id", user.id)
          .eq("exchange", "kraken")
          .single();

        const cachedAt = cachedRow?.cached_at ? new Date(cachedRow.cached_at).getTime() : 0;
        const isFresh = cachedAt > 0 && Date.now() - cachedAt < 5 * 60 * 1000; // 5 minutes
        const cachedBalance = cachedRow?.balance_data as any;

        if (isFresh && cachedBalance?.truthStatus === "live" && cachedBalance?.generatedValues === false && Array.isArray(cachedBalance?.assets)) {
          for (const a of cachedBalance.assets) {
            const free = parseFloat(String(a.free ?? 0));
            const locked = parseFloat(String(a.locked ?? 0));
            const total = free + locked;
            if (total > 0) {
              const usdValue = Number(a.usdValue);
              allPositions.push({
                asset: String(a.asset),
                free,
                locked,
                total,
                usdValue: Number.isFinite(usdValue) ? usdValue : null,
                valuationTruthStatus: Number.isFinite(usdValue) ? "real_derived" : "no_data",
                exchange: "kraken",
              });
            }
          }
        } else {
          // Don’t call Kraken here; portfolio sync will populate the cache.
          errors.push("Kraken: Waiting for portfolio sync (rate-limit protection)");
        }
      } catch (e: any) {
        errors.push(`Kraken: ${e?.message || "Cache read failed"}`);
      }
    }

    // Sort by USD value descending
    allPositions.sort((a, b) => (b.usdValue ?? -1) - (a.usdValue ?? -1));
    const valuedPositions = allPositions.filter((p) => p.usdValue !== null);
    const totalUsdValue = valuedPositions.length === allPositions.length
      ? valuedPositions.reduce((sum, p) => sum + (p.usdValue as number), 0)
      : null;

    return new Response(
      JSON.stringify({
        success: true,
        positions: allPositions,
        totalUsdValue,
        positionCount: allPositions.length,
        truthStatus: "live",
        valuationTruthStatus: totalUsdValue === null ? "no_data" : "real_derived",
        sourceTimestamp: new Date().toISOString(),
        generatedValues: false,
        exchanges: {
          binance: allPositions.filter((p) => p.exchange === "binance").length > 0,
          kraken: allPositions.filter((p) => p.exchange === "kraken").length > 0,
        },
        errors: errors.length > 0 ? errors : undefined,
      }),
      { headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  } catch (error: any) {
    console.error("fetch-open-positions error:", error);
    return new Response(JSON.stringify({ error: error?.message || String(error) }), {
      status: 500,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }
});
