"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.RiskManager = void 0;
const DEFAULT_PARAMS = {
    initialEquity: 100000,
    maxPortfolioRisk: 0.03,
    maxLeverage: 5,
    circuitBreaker: 0.1,
    riskPerTradeCap: 0.04,
    kellyMultiplier: 1,
    minHoldMinutes: 45,
    maxHoldMinutes: 360,
};
const kellyCriterion = (winRate, rewardRisk) => {
    if (rewardRisk <= 0)
        return 0;
    return Math.max(0, Math.min(1, winRate - (1 - winRate) / rewardRisk));
};
class RiskManager {
    constructor(config = {}) {
        this.params = { ...DEFAULT_PARAMS, ...config };
        this.realizedEquity = this.params.initialEquity;
        this.peakEquity = this.params.initialEquity;
        this.state = {
            equity: this.params.initialEquity,
            maxDrawdown: 0,
            openPositions: [],
        };
    }
    reset(config = {}) {
        this.params = { ...DEFAULT_PARAMS, ...config };
        this.realizedEquity = this.params.initialEquity;
        this.peakEquity = this.params.initialEquity;
        this.state = {
            equity: this.params.initialEquity,
            maxDrawdown: 0,
            openPositions: [],
        };
    }
    getState() {
        return this.state;
    }
    evaluate(decision, snapshot) {
        if (decision.action === 'hold') {
            return null;
        }
        const direction = decision.action === 'buy' ? 'long' : 'short';
        const recentVolatility = snapshot.consolidatedOHLCV.high - snapshot.consolidatedOHLCV.low;
        const normalizedVol = Math.max(0.001, recentVolatility / snapshot.consolidatedOHLCV.close);
        const winRate = 0.55 * decision.confidence + 0.45 * Math.random();
        const rewardRisk = 1.5 + decision.confidence;
        const kellyFraction = kellyCriterion(winRate, rewardRisk) * this.params.kellyMultiplier;
        const baseRisk = Math.min(this.params.maxPortfolioRisk, kellyFraction * decision.positionSize);
        const riskFraction = Math.min(baseRisk, this.params.riskPerTradeCap);
        const riskBudget = this.state.equity * riskFraction;
        if (riskBudget <= 0) {
            return null;
        }
        const leverage = Math.min(this.params.maxLeverage, 1 / normalizedVol);
        const notional = riskBudget * leverage;
        const stopLossDistance = snapshot.consolidatedOHLCV.close * normalizedVol * 1.2;
        const takeProfitDistance = stopLossDistance * rewardRisk;
        const stopLoss = direction === 'long'
            ? snapshot.consolidatedOHLCV.close - stopLossDistance
            : snapshot.consolidatedOHLCV.close + stopLossDistance;
        const takeProfit = direction === 'long'
            ? snapshot.consolidatedOHLCV.close + takeProfitDistance
            : snapshot.consolidatedOHLCV.close - takeProfitDistance;
        const baseHold = Math.round(60 + decision.confidence * 180);
        const holdMinutes = Math.max(this.params.minHoldMinutes, Math.min(this.params.maxHoldMinutes, baseHold));
        return {
            direction,
            notional,
            leverage,
            stopLoss,
            takeProfit,
            holdMinutes,
        };
    }
    registerFill(order, fillPrice, currentTime) {
        const size = order.notional / fillPrice;
        const position = {
            direction: order.direction,
            entryPrice: fillPrice,
            size,
            leverage: order.leverage,
            timestamp: currentTime,
            stopLoss: order.stopLoss,
            takeProfit: order.takeProfit,
            holdUntil: currentTime + order.holdMinutes,
        };
        this.state.openPositions.push(position);
    }
    liquidateAll(price) {
        let realized = 0;
        for (const position of this.state.openPositions) {
            const directionMultiplier = position.direction === 'long' ? 1 : -1;
            realized += (price - position.entryPrice) * position.size * directionMultiplier;
        }
        this.realizedEquity += realized;
        this.state.openPositions = [];
    }
    markToMarket(price, currentTime) {
        const activePositions = [];
        let unrealized = 0;
        for (const position of this.state.openPositions) {
            const directionMultiplier = position.direction === 'long' ? 1 : -1;
            const pnl = (price - position.entryPrice) * position.size * directionMultiplier;
            const stopHit = position.direction === 'long' ? price <= position.stopLoss : price >= position.stopLoss;
            const takeProfitHit = position.direction === 'long' ? price >= position.takeProfit : price <= position.takeProfit;
            const timeExpired = currentTime >= position.holdUntil;
            if (stopHit || takeProfitHit || timeExpired) {
                this.realizedEquity += pnl;
            }
            else {
                unrealized += pnl;
                activePositions.push(position);
            }
        }
        this.state.openPositions = activePositions;
        const currentEquity = this.realizedEquity + unrealized;
        this.state.equity = currentEquity;
        this.peakEquity = Math.max(this.peakEquity, currentEquity);
        const drawdown = this.peakEquity === 0 ? 0 : (this.peakEquity - currentEquity) / this.peakEquity;
        this.state.maxDrawdown = Math.max(this.state.maxDrawdown, drawdown);
        if (drawdown > this.params.circuitBreaker && this.state.openPositions.length > 0) {
            this.liquidateAll(price);
            this.state.equity = this.realizedEquity;
        }
    }
}
exports.RiskManager = RiskManager;
