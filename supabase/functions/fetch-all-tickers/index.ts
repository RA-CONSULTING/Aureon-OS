import { fetchLiveJson, requireFiniteNumber, requireFreshTimestamp } from '../_shared/real_data.ts';

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};

interface TickerData {
  symbol: string;
  exchange: 'binance' | 'kraken';
  price: number;
  bidPrice: number;
  askPrice: number;
  volume: number;
  volumeUsd: number;
  high24h: number;
  low24h: number;
  priceChange24h: number;
  volatility: number;
  momentum: number;
  spread: number;
  timestamp: number;
  truthStatus: 'real_derived';
  sourceId: string;
  sourceTimestamp: string;
  generatedValues: false;
}

const MAX_AGE_MS = 5 * 60 * 1000;
const BINANCE_URL = 'https://api.binance.com/api/v3/ticker/24hr';

function finite(value: unknown, name: string): number {
  return requireFiniteNumber(Number(value), name);
}

function validateMarketNumbers(values: number[], exchange: string, symbol: string): void {
  if (values.some((value) => !Number.isFinite(value)) || values[0] <= 0 || values[1] < 0 || values[2] < 0 || values[3] < 0) {
    throw new Error(`${exchange.toUpperCase()}_INVALID_TICKER:${symbol}`);
  }
}

Deno.serve(async (req) => {
  if (req.method === 'OPTIONS') return new Response(null, { headers: corsHeaders });

  try {
    const body = await req.json().catch(() => ({}));
    const exchanges = Array.isArray(body.exchanges) ? body.exchanges : ['binance'];
    const symbols = Array.isArray(body.symbols)
      ? body.symbols.map((value: unknown) => String(value).toUpperCase()).filter((value: string) => /^[A-Z0-9]{5,20}$/.test(value))
      : null;
    const limit = Number(body.limit ?? 100);
    if (!Number.isInteger(limit) || limit < 1 || limit > 1000) {
      throw new Error('INVALID_LIMIT');
    }
    if (exchanges.some((exchange: unknown) => !['binance', 'kraken'].includes(String(exchange)))) {
      throw new Error('INVALID_EXCHANGE');
    }

    const allTickers: TickerData[] = [];
    const providerErrors: Array<{ exchange: string; error: string }> = [];

    if (exchanges.includes('binance')) {
      try {
        const rows = await fetchLiveJson<any[]>(BINANCE_URL);
        if (!Array.isArray(rows)) throw new Error('BINANCE_TICKER_RESPONSE_INVALID');
        let selected = symbols
          ? rows.filter((row) => symbols.includes(String(row.symbol)))
          : rows
            .filter((row) => String(row.symbol).endsWith('USDT') && Number(row.quoteVolume) > 100000)
            .sort((a, b) => Number(b.quoteVolume) - Number(a.quoteVolume))
            .slice(0, limit);

        for (const row of selected) {
          try {
            const symbol = String(row.symbol);
            const price = finite(row.lastPrice, `${symbol}.lastPrice`);
            const bidPrice = finite(row.bidPrice, `${symbol}.bidPrice`);
            const askPrice = finite(row.askPrice, `${symbol}.askPrice`);
            const volume = finite(row.volume, `${symbol}.volume`);
            const volumeUsd = finite(row.quoteVolume, `${symbol}.quoteVolume`);
            const high24h = finite(row.highPrice, `${symbol}.highPrice`);
            const low24h = finite(row.lowPrice, `${symbol}.lowPrice`);
            const priceChange24h = finite(row.priceChangePercent, `${symbol}.priceChangePercent`);
            const closeTime = finite(row.closeTime, `${symbol}.closeTime`);
            const sourceTimestamp = new Date(closeTime).toISOString();
            requireFreshTimestamp(sourceTimestamp, MAX_AGE_MS, `${symbol}.closeTime`);
            validateMarketNumbers([price, bidPrice, askPrice, volume, volumeUsd, high24h, low24h], 'binance', symbol);
            if (askPrice < bidPrice) throw new Error(`BINANCE_CROSSED_BOOK:${symbol}`);
            allTickers.push({
              symbol,
              exchange: 'binance',
              price,
              bidPrice,
              askPrice,
              volume,
              volumeUsd,
              high24h,
              low24h,
              priceChange24h,
              volatility: (high24h - low24h) / price,
              momentum: priceChange24h / 100,
              spread: (askPrice - bidPrice) / price,
              timestamp: closeTime,
              truthStatus: 'real_derived',
              sourceId: 'binance:/api/v3/ticker/24hr',
              sourceTimestamp,
              generatedValues: false,
            });
          } catch (error) {
            providerErrors.push({ exchange: 'binance', error: error instanceof Error ? error.message : String(error) });
          }
        }
      } catch (error) {
        providerErrors.push({ exchange: 'binance', error: error instanceof Error ? error.message : String(error) });
      }
    }

    if (exchanges.includes('kraken')) {
      try {
        const pairNames = ['XBTUSD', 'ETHUSD', 'SOLUSD', 'XRPUSD', 'DOGEUSD', 'ADAUSD', 'DOTUSD', 'AVAXUSD', 'LINKUSD', 'LTCUSD'];
        const [clock, payload] = await Promise.all([
          fetchLiveJson<any>('https://api.kraken.com/0/public/Time'),
          fetchLiveJson<any>(`https://api.kraken.com/0/public/Ticker?pair=${pairNames.join(',')}`),
        ]);
        if (clock?.error?.length || payload?.error?.length) throw new Error('KRAKEN_PROVIDER_ERROR');
        const providerTime = finite(clock?.result?.unixtime, 'kraken.unixtime') * 1000;
        const sourceTimestamp = new Date(providerTime).toISOString();
        requireFreshTimestamp(sourceTimestamp, MAX_AGE_MS, 'kraken.unixtime');
        const pairMap: Record<string, string> = {
          XXBTZUSD: 'BTCUSDT', XBTUSD: 'BTCUSDT', XETHZUSD: 'ETHUSDT', ETHUSD: 'ETHUSDT',
          SOLUSD: 'SOLUSDT', XRPUSD: 'XRPUSDT', DOGEUSD: 'DOGEUSDT', ADAUSD: 'ADAUSDT',
          DOTUSD: 'DOTUSDT', AVAXUSD: 'AVAXUSDT', LINKUSD: 'LINKUSDT', LTCUSD: 'LTCUSDT',
        };
        for (const [pair, raw] of Object.entries(payload?.result ?? {}) as Array<[string, any]>) {
          try {
            const symbol = pairMap[pair];
            if (!symbol || (symbols && !symbols.includes(symbol))) continue;
            const price = finite(raw.c?.[0], `${pair}.close`);
            const bidPrice = finite(raw.b?.[0], `${pair}.bid`);
            const askPrice = finite(raw.a?.[0], `${pair}.ask`);
            const volume = finite(raw.v?.[1], `${pair}.volume`);
            const high24h = finite(raw.h?.[1], `${pair}.high`);
            const low24h = finite(raw.l?.[1], `${pair}.low`);
            const open = finite(raw.o, `${pair}.open`);
            const volumeUsd = volume * price;
            validateMarketNumbers([price, bidPrice, askPrice, volume, volumeUsd, high24h, low24h, open], 'kraken', symbol);
            if (askPrice < bidPrice || open <= 0) throw new Error(`KRAKEN_INVALID_BOOK:${symbol}`);
            const priceChange24h = ((price - open) / open) * 100;
            allTickers.push({
              symbol,
              exchange: 'kraken',
              price,
              bidPrice,
              askPrice,
              volume,
              volumeUsd,
              high24h,
              low24h,
              priceChange24h,
              volatility: (high24h - low24h) / price,
              momentum: priceChange24h / 100,
              spread: (askPrice - bidPrice) / price,
              timestamp: providerTime,
              truthStatus: 'real_derived',
              sourceId: 'kraken:/0/public/Ticker+/0/public/Time',
              sourceTimestamp,
              generatedValues: false,
            });
          } catch (error) {
            providerErrors.push({ exchange: 'kraken', error: error instanceof Error ? error.message : String(error) });
          }
        }
      } catch (error) {
        providerErrors.push({ exchange: 'kraken', error: error instanceof Error ? error.message : String(error) });
      }
    }

    allTickers.sort((a, b) => b.volumeUsd - a.volumeUsd);
    if (allTickers.length === 0) {
      return new Response(JSON.stringify({
        success: false,
        truthStatus: 'no_data',
        generatedValues: false,
        providerErrors,
      }), { status: 503, headers: { ...corsHeaders, 'Content-Type': 'application/json' } });
    }

    const exchangeBreakdown: Record<string, number> = {};
    for (const ticker of allTickers) exchangeBreakdown[ticker.exchange] = (exchangeBreakdown[ticker.exchange] ?? 0) + 1;
    const avgVolatility = allTickers.reduce((sum, ticker) => sum + ticker.volatility, 0) / allTickers.length;
    const avgSpread = allTickers.reduce((sum, ticker) => sum + ticker.spread, 0) / allTickers.length;
    return new Response(JSON.stringify({
      success: true,
      truthStatus: 'real_derived',
      generatedValues: false,
      partial: providerErrors.length > 0,
      tickers: allTickers,
      stats: {
        totalTickers: allTickers.length,
        exchangeBreakdown,
        avgVolatility,
        avgSpread,
        topSymbol: allTickers[0].symbol,
        topVolume: allTickers[0].volumeUsd,
      },
      providerErrors,
      collectedAt: new Date().toISOString(),
    }), { headers: { ...corsHeaders, 'Content-Type': 'application/json' } });
  } catch (error) {
    return new Response(JSON.stringify({
      success: false,
      error: error instanceof Error ? error.message : String(error),
      truthStatus: 'no_data',
      generatedValues: false,
    }), { status: 409, headers: { ...corsHeaders, 'Content-Type': 'application/json' } });
  }
});
