"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.DataIngestionEngine = void 0;
const DEFAULT_CONFIG = {
    initialPrice: 42000,
    exchanges: [
        { name: 'Binance', liquidityWeight: 1.0, latencyMs: 25 },
        { name: 'Coinbase', liquidityWeight: 0.8, latencyMs: 35 },
        { name: 'Kraken', liquidityWeight: 0.6, latencyMs: 40 },
        { name: 'Bybit', liquidityWeight: 0.9, latencyMs: 32 },
        { name: 'KuCoin', liquidityWeight: 0.5, latencyMs: 45 },
    ],
};
const KEYWORDS = ['ETF', 'halving', 'regulation', 'bull-run', 'whale', 'leverage'];
const pickKeywords = () => {
    const shuffled = [...KEYWORDS].sort(() => Math.random() - 0.5);
    return shuffled.slice(0, 3);
};
const randomBetween = (min, max) => min + Math.random() * (max - min);
class DataIngestionEngine {
    constructor(config = {}) {
        this.config = { ...DEFAULT_CONFIG, ...config };
        this.price = this.config.initialPrice;
    }
    next() {
        const volatility = randomBetween(0.002, 0.012);
        const drift = randomBetween(-0.004, 0.006);
        this.price = Math.max(1000, this.price * (1 + drift + volatility * (Math.random() - 0.5)));
        const exchangeFeeds = this.config.exchanges.map((exchange, idx) => {
            const liquidityScale = 1 + exchange.liquidityWeight * 0.5;
            const priceNoise = (Math.random() - 0.5) * 0.002 * this.price / liquidityScale;
            const price = this.price + priceNoise;
            const volume24h = randomBetween(50, 500) * 1e6 * liquidityScale * (1 + idx * 0.05);
            const fundingRate = randomBetween(-0.02, 0.02) / liquidityScale;
            const spread = Math.abs(priceNoise) / this.price;
            return {
                exchange: exchange.name,
                price,
                volume24h,
                fundingRate,
                spread,
                latencyMs: exchange.latencyMs,
            };
        });
        const bestBid = Math.max(...exchangeFeeds.map(f => f.price)) * (1 - 0.0008);
        const bestAsk = Math.min(...exchangeFeeds.map(f => f.price)) * (1 + 0.0008);
        const orderBookDepth = Array.from({ length: 10 }, (_, i) => {
            const side = i % 2 === 0 ? 'bid' : 'ask';
            const spreadOffset = side === 'bid' ? -0.5 : 0.5;
            const price = (side === 'bid' ? bestBid : bestAsk) + spreadOffset * i;
            const size = randomBetween(5, 75) * (10 - i);
            return { price, size, side };
        });
        const onChain = {
            activeAddresses: randomBetween(800000, 1200000),
            exchangeFlows: randomBetween(-2000, 2000),
            whaleAlerts: randomBetween(5, 30),
        };
        const sentiment = [
            { source: 'twitter', score: randomBetween(-1, 1), trendingKeywords: pickKeywords() },
            { source: 'reddit', score: randomBetween(-0.8, 0.8), trendingKeywords: pickKeywords() },
            { source: 'telegram', score: randomBetween(-0.6, 0.6), trendingKeywords: pickKeywords() },
        ];
        const newsSources = ['CoinDesk', 'CoinTelegraph', 'Bloomberg', 'Decrypt'];
        const news = newsSources.map(source => ({
            source,
            title: `${source}: ${pickKeywords()[0]} momentum intensifies`,
            impactScore: randomBetween(0, 1),
        }));
        const macro = {
            fearGreedIndex: randomBetween(10, 90),
            fundingRateAverage: exchangeFeeds.reduce((acc, feed) => acc + feed.fundingRate, 0) / exchangeFeeds.length,
            liquidations24h: randomBetween(50, 250) * 1e6,
        };
        const open = this.price * (1 - drift);
        const high = Math.max(open, this.price) * (1 + volatility * 1.5);
        const low = Math.min(open, this.price) * (1 - volatility * 1.5);
        const close = this.price;
        const volume = exchangeFeeds.reduce((acc, feed) => acc + feed.volume24h, 0) / 24;
        return {
            timestamp: Date.now(),
            exchangeFeeds,
            orderBookDepth,
            onChain,
            sentiment,
            news,
            macro,
            consolidatedOHLCV: { open, high, low, close, volume },
        };
    }
}
exports.DataIngestionEngine = DataIngestionEngine;
