import { serve } from 'https://deno.land/std@0.168.0/http/server.ts';

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};

serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response(null, { headers: corsHeaders });
  }

  try {
    const { symbol: rawSymbol } = await req.json();
    const symbol = String(rawSymbol || '').trim().toUpperCase();
    if (!/^[A-Z0-9]{5,20}$/.test(symbol)) throw new Error('VALID_MARKET_SYMBOL_REQUIRED');

    // Fetch real market data from Binance public API
    const tickerResponse = await fetch(
      `https://api.binance.com/api/v3/ticker/24hr?symbol=${symbol}`
    );

    if (!tickerResponse.ok) {
      throw new Error(`BINANCE_TICKER_HTTP_${tickerResponse.status}`);
    }

    const ticker = await tickerResponse.json();

    // Calculate derived metrics
    const price = parseFloat(ticker.lastPrice);
    const volume = parseFloat(ticker.volume);
    const priceChange = parseFloat(ticker.priceChangePercent);
    const highPrice = parseFloat(ticker.highPrice);
    const lowPrice = parseFloat(ticker.lowPrice);
    
    // Volatility approximation from high-low range
    const volatility = (highPrice - lowPrice) / price;
    
    // Momentum from price change
    const momentum = priceChange / 100;
    
    // Spread approximation
    const spread = parseFloat(ticker.askPrice) - parseFloat(ticker.bidPrice);
    const spreadPercent = spread / price;
    const providerTimestamp = Number(ticker.closeTime);
    const providerAgeMs = Date.now() - providerTimestamp;
    const observedNumbers = [price, volume, priceChange, highPrice, lowPrice, volatility, momentum, spread, spreadPercent];
    if (observedNumbers.some((value) => !Number.isFinite(value)) || price <= 0 || volume < 0 ||
        !Number.isFinite(providerTimestamp) || providerAgeMs < -300000 || providerAgeMs > 300000) {
      throw new Error('INVALID_OR_STALE_BINANCE_TICKER');
    }
    const sourceTimestamp = new Date(providerTimestamp).toISOString();

    const marketData = {
      symbol,
      price,
      volume,
      volatility,
      momentum,
      spread: spreadPercent,
      priceChange,
      highPrice,
      lowPrice,
      timestamp: providerTimestamp,
      truthStatus: 'real_derived',
      sourceId: 'binance:/api/v3/ticker/24hr',
      sourceTimestamp,
      generatedValues: false,
    };

    console.log(`[get-user-market-data] ${symbol}: $${price.toFixed(2)}, vol: ${volatility.toFixed(4)}, mom: ${momentum.toFixed(4)}`);

    return new Response(JSON.stringify(marketData), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    });
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    console.error('[get-user-market-data] Error:', errorMessage);
    
    return new Response(
      JSON.stringify({
        error: errorMessage,
        truthStatus: 'no_data',
        generatedValues: false,
      }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    );
  }
});
