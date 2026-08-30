import { serve } from "https://deno.land/std@0.168.0/http/server.ts";

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};

interface ExchangeStatus {
  exchange: string;
  status: 'LIVE' | 'UNCONFIGURED' | 'OFFLINE' | 'ERROR';
  hasCredentials: boolean;
  lastPrice?: number;
  lastTimestamp?: number;
  latencyMs?: number;
  errorMessage?: string;
}

interface VerificationResult {
  success: boolean;
  timestamp: number;
  exchanges: ExchangeStatus[];
  overallStatus: 'ALL_LIVE' | 'PARTIAL_LIVE' | 'UNCONFIGURED' | 'OFFLINE';
  priceVariance?: number;
  warnings: string[];
  truthStatus: 'live' | 'no_data';
  generatedValues: false;
}

/**
 * VERIFY EXCHANGE CONNECTIVITY
 * 
 * Actually calls each exchange API to confirm:
 * 1. Credentials are configured
 * 2. Real data is being returned (not mock/demo)
 * 3. Price data matches between exchanges (sanity check)
 */
serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response(null, { headers: corsHeaders });
  }

  const startTime = Date.now();
  const exchanges: ExchangeStatus[] = [];
  const warnings: string[] = [];

  try {
    // ============= BINANCE VERIFICATION =============
    const binanceStatus = await verifyBinance();
    exchanges.push(binanceStatus);
    if (binanceStatus.status === 'UNCONFIGURED') {
      warnings.push('BINANCE: No production API credentials configured');
    }

    // ============= KRAKEN VERIFICATION =============
    const krakenStatus = await verifyKraken();
    exchanges.push(krakenStatus);
    if (krakenStatus.status === 'UNCONFIGURED') {
      warnings.push('KRAKEN: No production API credentials configured');
    }

    // ============= ALPACA VERIFICATION =============
    const alpacaStatus = await verifyAlpaca();
    exchanges.push(alpacaStatus);
    if (alpacaStatus.status === 'UNCONFIGURED') {
      warnings.push('ALPACA: No production API credentials configured');
    }

    // ============= CAPITAL.COM VERIFICATION =============
    const capitalStatus = await verifyCapital();
    exchanges.push(capitalStatus);
    if (capitalStatus.status === 'UNCONFIGURED') {
      warnings.push('CAPITAL.COM: No production API credentials configured');
    }

    // Calculate price variance between exchanges (sanity check)
    const livePrices = exchanges
      .filter(e => e.status === 'LIVE' && e.lastPrice)
      .map(e => e.lastPrice!);
    
    let priceVariance = 0;
    if (livePrices.length >= 2) {
      const avgPrice = livePrices.reduce((a, b) => a + b, 0) / livePrices.length;
      const maxDeviation = Math.max(...livePrices.map(p => Math.abs(p - avgPrice) / avgPrice));
      priceVariance = maxDeviation * 100;
      
      if (priceVariance > 5) {
        warnings.push(`PRICE VARIANCE: ${priceVariance.toFixed(2)}% deviation between exchanges - possible data issue`);
      }
    }

    // Determine overall status
    const liveCount = exchanges.filter(e => e.status === 'LIVE').length;
    const unconfiguredCount = exchanges.filter(e => e.status === 'UNCONFIGURED').length;
    
    let overallStatus: VerificationResult['overallStatus'];
    if (liveCount === exchanges.length) {
      overallStatus = 'ALL_LIVE';
    } else if (liveCount > 0) {
      overallStatus = 'PARTIAL_LIVE';
    } else if (unconfiguredCount === exchanges.length) {
      overallStatus = 'UNCONFIGURED';
    } else {
      overallStatus = 'OFFLINE';
    }

    const result: VerificationResult = {
      success: overallStatus === 'ALL_LIVE',
      timestamp: Date.now(),
      exchanges,
      overallStatus,
      priceVariance,
      warnings,
      truthStatus: overallStatus === 'ALL_LIVE' ? 'live' : 'no_data',
      generatedValues: false,
    };

    console.log(`[verify-exchange-connectivity] Status: ${overallStatus} | Live: ${liveCount}/${exchanges.length} | Latency: ${Date.now() - startTime}ms`);

    return new Response(JSON.stringify(result), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      status: result.success ? 200 : 503,
    });

  } catch (error) {
    console.error('[verify-exchange-connectivity] Error:', error);
    return new Response(JSON.stringify({
      success: false,
      timestamp: Date.now(),
      exchanges,
      overallStatus: 'OFFLINE',
      warnings: [error instanceof Error ? error.message : 'Unknown error'],
    }), {
      status: 500,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    });
  }
});

async function verifyBinance(): Promise<ExchangeStatus> {
  const apiKey = Deno.env.get('BINANCE_API_KEY');
  const apiSecret = Deno.env.get('BINANCE_API_SECRET');
  
  if (!apiKey || !apiSecret) {
    return {
      exchange: 'binance',
      status: 'UNCONFIGURED',
      hasCredentials: false,
      errorMessage: 'No API credentials configured',
    };
  }

  try {
    const startMs = Date.now();
    const response = await fetch('https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT', {
      headers: { 'X-MBX-APIKEY': apiKey },
    });
    const latencyMs = Date.now() - startMs;

    if (!response.ok) {
      return {
        exchange: 'binance',
        status: 'ERROR',
        hasCredentials: true,
        latencyMs,
        errorMessage: `API error: ${response.status}`,
      };
    }

    const data = await response.json();
    return {
      exchange: 'binance',
      status: 'LIVE',
      hasCredentials: true,
      lastPrice: parseFloat(data.price),
      lastTimestamp: Date.now(),
      latencyMs,
    };
  } catch (error) {
    return {
      exchange: 'binance',
      status: 'OFFLINE',
      hasCredentials: true,
      errorMessage: error instanceof Error ? error.message : 'Connection failed',
    };
  }
}

async function verifyKraken(): Promise<ExchangeStatus> {
  const apiKey = Deno.env.get('KRAKEN_API_KEY');
  const apiSecret = Deno.env.get('KRAKEN_API_SECRET');
  
  if (!apiKey || !apiSecret) {
    return {
      exchange: 'kraken',
      status: 'UNCONFIGURED',
      hasCredentials: false,
      errorMessage: 'No API credentials configured',
    };
  }

  try {
    const startMs = Date.now();
    // Public endpoint to verify connectivity
    const response = await fetch('https://api.kraken.com/0/public/Ticker?pair=XBTUSD');
    const latencyMs = Date.now() - startMs;

    if (!response.ok) {
      return {
        exchange: 'kraken',
        status: 'ERROR',
        hasCredentials: true,
        latencyMs,
        errorMessage: `API error: ${response.status}`,
      };
    }

    const data = await response.json();
    if (data.error && data.error.length > 0) {
      return {
        exchange: 'kraken',
        status: 'ERROR',
        hasCredentials: true,
        latencyMs,
        errorMessage: data.error.join(', '),
      };
    }

    const ticker = data.result?.XXBTZUSD || data.result?.XBTUSD;
    const lastPrice = ticker?.c?.[0] ? parseFloat(ticker.c[0]) : undefined;

    return {
      exchange: 'kraken',
      status: 'LIVE',
      hasCredentials: true,
      lastPrice,
      lastTimestamp: Date.now(),
      latencyMs,
    };
  } catch (error) {
    return {
      exchange: 'kraken',
      status: 'OFFLINE',
      hasCredentials: true,
      errorMessage: error instanceof Error ? error.message : 'Connection failed',
    };
  }
}

async function verifyAlpaca(): Promise<ExchangeStatus> {
  const apiKey = Deno.env.get('ALPACA_API_KEY');
  const apiSecret = Deno.env.get('ALPACA_SECRET_KEY');
  
  if (!apiKey || !apiSecret) {
    return {
      exchange: 'alpaca',
      status: 'UNCONFIGURED',
      hasCredentials: false,
      errorMessage: 'No API credentials configured',
    };
  }

  try {
    const startMs = Date.now();
    const response = await fetch('https://api.alpaca.markets/v2/account', {
      headers: {
        'APCA-API-KEY-ID': apiKey,
        'APCA-API-SECRET-KEY': apiSecret,
      },
    });
    const latencyMs = Date.now() - startMs;

    if (!response.ok) {
      return {
        exchange: 'alpaca',
        status: 'ERROR',
        hasCredentials: true,
        latencyMs,
        errorMessage: `API error: ${response.status}`,
      };
    }

    return {
      exchange: 'alpaca',
      status: 'LIVE',
      hasCredentials: true,
      lastTimestamp: Date.now(),
      latencyMs,
    };
  } catch (error) {
    return {
      exchange: 'alpaca',
      status: 'OFFLINE',
      hasCredentials: true,
      errorMessage: error instanceof Error ? error.message : 'Connection failed',
    };
  }
}

async function verifyCapital(): Promise<ExchangeStatus> {
  const apiKey = Deno.env.get('CAPITAL_API_KEY');
  const password = Deno.env.get('CAPITAL_PASSWORD');
  const identifier = Deno.env.get('CAPITAL_IDENTIFIER');
  
  if (!apiKey || !password || !identifier) {
    return {
      exchange: 'capital',
      status: 'UNCONFIGURED',
      hasCredentials: false,
      errorMessage: 'No API credentials configured',
    };
  }

  try {
    const startMs = Date.now();
    const response = await fetch('https://api-capital.backend-capital.com/api/v1/ping', {
      headers: {
        'X-CAP-API-KEY': apiKey,
      },
    });
    const latencyMs = Date.now() - startMs;

    if (!response.ok) {
      return {
        exchange: 'capital',
        status: 'ERROR',
        hasCredentials: true,
        latencyMs,
        errorMessage: `API error: ${response.status}`,
      };
    }

    return {
      exchange: 'capital',
      status: 'LIVE',
      hasCredentials: true,
      lastTimestamp: Date.now(),
      latencyMs,
    };
  } catch (error) {
    return {
      exchange: 'capital',
      status: 'OFFLINE',
      hasCredentials: true,
      errorMessage: error instanceof Error ? error.message : 'Connection failed',
    };
  }
}
