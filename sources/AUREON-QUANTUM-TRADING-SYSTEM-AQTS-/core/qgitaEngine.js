"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.QGITAEngine = void 0;
const DEFAULT_CONFIG = {
    fibonacciSequence: [5, 8, 13, 21, 34, 55],
    minConfidence: 0.35,
    neutralConfidence: 0.45,
    historyLimit: 300,
};
const computeDiscreteCurvature = (values) => {
    if (values.length < 3)
        return 0;
    let curvature = 0;
    for (let i = 1; i < values.length - 1; i++) {
        const prev = values[i - 1];
        const curr = values[i];
        const next = values[i + 1];
        curvature += Math.abs(next - 2 * curr + prev);
    }
    return curvature / (values.length - 2);
};
const normalize = (value, min, max) => {
    if (max === min)
        return 0;
    return Math.max(0, Math.min(1, (value - min) / (max - min)));
};
class QGITAEngine {
    constructor(config = {}) {
        this.history = [];
        this.config = { ...DEFAULT_CONFIG, ...config };
    }
    register(snapshot) {
        this.history.push(snapshot);
        if (this.history.length > this.config.historyLimit) {
            this.history.shift();
        }
    }
    evaluate() {
        if (this.history.length < Math.max(...this.config.fibonacciSequence)) {
            return null;
        }
        const closes = this.history.map(s => s.consolidatedOHLCV.close);
        const fibWindows = this.config.fibonacciSequence.map(length => {
            const slice = closes.slice(-length);
            const start = slice[0];
            const end = slice[slice.length - 1];
            const ratioAlignment = normalize(Math.abs(end - start) / (Math.max(end, start) || 1), 0, 0.12);
            const curvature = computeDiscreteCurvature(slice);
            return { length, ratioAlignment, curvature };
        });
        const timeLatticeScore = fibWindows.reduce((acc, window) => acc + window.ratioAlignment, 0) / fibWindows.length;
        const macroStates = this.history.slice(-21);
        const avgSentiment = macroStates.reduce((acc, s) => acc + s.sentiment.reduce((inner, v) => inner + v.score, 0), 0);
        const avgSentimentScore = normalize(avgSentiment / (macroStates.length * 3), -0.5, 0.5);
        const avgFunding = macroStates.reduce((acc, s) => acc + s.macro.fundingRateAverage, 0) / macroStates.length;
        const fundingScore = 1 - normalize(Math.abs(avgFunding), 0, 0.03);
        const volumeSeries = macroStates.map(s => s.consolidatedOHLCV.volume);
        const volumeCurvature = computeDiscreteCurvature(volumeSeries);
        const volatilityScore = 1 - normalize(volumeCurvature, 0, 1.5e12);
        const coherenceScore = Math.max(0, (avgSentimentScore + fundingScore + volatilityScore) / 3);
        const latest = this.history[this.history.length - 1];
        const whalePressure = normalize(latest.onChain.whaleAlerts, 0, 50);
        const liquidationPressure = normalize(latest.macro.liquidations24h, 0, 400e6);
        const spreadSkew = normalize(latest.exchangeFeeds.reduce((acc, feed) => acc + feed.spread, 0) / latest.exchangeFeeds.length, 0, 0.003);
        const anomalyScore = Math.min(1, (whalePressure + liquidationPressure + spreadSkew) / 3);
        const confidence = Math.max(0, Math.min(1, timeLatticeScore * 0.4 + coherenceScore * 0.4 + anomalyScore * 0.2));
        const lastClose = closes[closes.length - 1];
        const meanPrice = closes.slice(-21).reduce((acc, price) => acc + price, 0) / 21;
        let direction = 'neutral';
        if (confidence > Math.max(this.config.neutralConfidence, this.config.minConfidence + 0.2)) {
            direction = lastClose > meanPrice ? 'long' : 'short';
        }
        else if (confidence > this.config.neutralConfidence) {
            direction = lastClose > meanPrice ? 'neutral' : 'short';
        }
        if (confidence < this.config.minConfidence) {
            return null;
        }
        return {
            timestamp: latest.timestamp,
            direction,
            confidence,
            breakdown: { timeLatticeScore, coherenceScore, anomalyScore },
        };
    }
}
exports.QGITAEngine = QGITAEngine;
