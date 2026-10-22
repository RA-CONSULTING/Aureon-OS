
import { HistoricalDataPoint, AureonDataPoint, PrismStatus, OHLCV } from './types';
import { executeAurisLoop, analyzeResonance, AurisResonance } from './core/aurisSymbolicTaxonomy';

// --- NEXUS (COGNITIVE) SIMULATION ---

// This part of the simulation remains unchanged, modeling the historical cognitive trajectory.
class NexusSystem {
    kappa_t: number = 1.85; 

    step(C_t: number, stress_t: number) {
        const delta_kappa = -0.01 * (C_t / 10000) + 0.02 * stress_t;
        this.kappa_t = Math.max(0.1, Math.min(3.0, this.kappa_t + delta_kappa));
        return this.kappa_t;
    }
}

const gaelic_C_t_historical = (year: number): number => {
    if (year < 500) return 15000;
    if (year < 800) return 12000;
    if (year < 1300) return 8000;
    if (year < 1700) return 4000;
    if (year < 1900) return 2000;
    if (year < 2000) return 1000;
    return 1000 + (year - 2000) * 50;
};

const gaelic_stress_historical = (year: number): number => {
    if (year >= 800 && year < 1000) return 0.5;
    if (year >= 1500 && year < 1700) return 0.8;
    if (year >= 1750 && year < 1860) return 0.9;
    if (year >= 1900 && year < 1950) return 0.7;
    if (year >= 1950 && year < 2000) return 0.4;
    if (year >= 2000) return 0.3;
    return 0.1;
};

export const runGaelicHistoricalSimulation = () => {
    const system = new NexusSystem();
    const historicalData: HistoricalDataPoint[] = [];
    for (let year = -500; year <= 2025; year++) {
        const C_t = gaelic_C_t_historical(year);
        const stress_t = gaelic_stress_historical(year);
        const kappa_t = system.step(C_t, stress_t);
        historicalData.push({ year, cognitiveCapacity: 1 / kappa_t });
    }
    return historicalData;
};


// --- AUREON (FINANCIAL) SIMULATION ---

interface AureonInput {
    time: number;
    market: OHLCV;
    sentiment: number;
    policyRate: number;
    schumann: number;
    dataQuality: number;
}

// Generates a sophisticated, "live-like" input feed based on the specified data sources.
const generateAureonInputFeed = (length: number): AureonInput[] => {
    const data: AureonInput[] = [];
    let close = 160 + Math.random() * 20;
    let sentiment = 0;
    let policyRate = 0.025;

    for (let i = 0; i < length; i++) {
        const economicCycle = Math.sin(i * Math.PI / 180) * 0.1;
        const policyCycle = Math.sin(i * Math.PI / 360);
        policyRate = 0.025 + policyCycle * 0.02;

        sentiment += (Math.random() - 0.5) * 0.1 - sentiment * 0.05 + economicCycle * 0.05;
        sentiment = Math.max(-1, Math.min(1, sentiment));

        const volatility = 1 + Math.abs(sentiment) * 1.5 + Math.random() * 0.5;

        const open = close;
        let move = (Math.random() - 0.5 + sentiment * 0.2 - (policyRate - 0.025) * 10) * volatility;
        
        let dataQuality = 1.0;
        if (Math.random() < 0.02) { // 2% chance of a major shock event
            move += (Math.random() > 0.5 ? 1 : -1) * (15 + Math.random() * 20);
            sentiment = Math.sign(move) * Math.random() * 0.8;
            dataQuality -= 0.5; // Shock event impacts data integrity
        }
        
        if (Math.random() < 0.05) {
            dataQuality -= Math.random() * 0.2; // Minor data anomalies
        }


        close = Math.max(10, open + move);
        const high = Math.max(open, close) + Math.random() * volatility * 2;
        const low = Math.min(open, close) - Math.random() * volatility * 2;
        
        const baseVolume = 1000000;
        const activityVolume = Math.abs(move) * 200000 + (high - low) * 100000;
        const volume = baseVolume + activityVolume + Math.random() * 500000;
        
        const schumann = 7.83 + Math.sin(i / 10) * 0.5 + (Math.random() - 0.5) * 0.2;

        data.push({ time: i, market: { open, high, low, close, volume }, sentiment, policyRate, schumann, dataQuality });
    }
    return data;
};

// Calculates rolling average and standard deviation
const rollingStats = (data: number[], window: number) => {
    if (data.length < window) return { avg: data.reduce((a,b)=>a+b,0)/data.length || 0, std: 0 };
    const slice = data.slice(-window);
    const avg = slice.reduce((a,b)=>a+b,0) / window;
    const std = Math.sqrt(slice.map(x => Math.pow(x - avg, 2)).reduce((a,b)=>a+b,0) / window);
    return { avg, std };
};

// Calculates rolling correlation
const rollingCorrelation = (x: number[], y: number[], window: number): number => {
    if (x.length < window || y.length < window) return 0;
    const sx = x.slice(-window);
    const sy = y.slice(-window);
    const meanX = sx.reduce((a, b) => a + b, 0) / window;
    const meanY = sy.reduce((a, b) => a + b, 0) / window;
    let num = 0, denX = 0, denY = 0;
    for (let i = 0; i < window; i++) {
        num += (sx[i] - meanX) * (sy[i] - meanY);
        denX += (sx[i] - meanX) ** 2;
        denY += (sy[i] - meanY) ** 2;
    }
    return denX === 0 || denY === 0 ? 0 : num / Math.sqrt(denX * denY);
};


export const runAureonSimulation = (length: number): AureonDataPoint[] => {
    const inputFeed = generateAureonInputFeed(length);
    const aureonData: AureonDataPoint[] = [];
    
    const cciHistory: number[] = [];
    const schumannHistory: number[] = [];

    for (let i = 0; i < length; i++) {
        const input = inputFeed[i];
        const { market, sentiment, policyRate, schumann, dataQuality } = input;
        const lastMarket = i > 0 ? inputFeed[i-1].market : market;

        // Dₜ: Data Integrity - Based on input dataQuality proxy.
        const dataIntegrity = dataQuality;
        
        // Cₜ: Crystal Coherence - Volume confirms price direction + body/wick ratio.
        const body = Math.abs(market.close - market.open);
        const range = market.high - market.low;
        const bodyRatio = range > 0 ? body / range : 0; // High ratio = decisive move
        const isUpDay = market.close > market.open;
        const isVolConfirm = isUpDay ? market.volume > lastMarket.volume : market.volume < lastMarket.volume * 0.9;
        const crystalCoherence = dataIntegrity * (0.4 + (isVolConfirm ? 0.3 : 0) + bodyRatio * 0.3);
        cciHistory.push(crystalCoherence);
        schumannHistory.push(schumann);

        // Celestial Modulators (slow sine wave)
        const celestialModulators = 0.5 + 0.5 * Math.sin(i / 365);
        
        // ΔCₜ & Φₜ: Polaris Baseline & Choerance Drift
        const cciStats = rollingStats(cciHistory, 60);
        const polarisBaseline = cciStats.avg;
        const choeranceDrift = Math.atan((crystalCoherence - polarisBaseline) / (cciStats.std + 0.01));
        
        // Pₜ & Gₜ: Ping-Pong & Grav Reflection
        const pingPong = rollingCorrelation(cciHistory, schumannHistory, 30);
        const gravReflection = 0.5 + 0.5 * Math.cos(i / 180); // Abstracted as another slow cycle

        // Uₜ & 𝓘ₜ: Unity & Inercha
        const stateVector = [dataIntegrity, crystalCoherence, choeranceDrift, pingPong, gravReflection];
        const avg = stateVector.reduce((a,b) => a+b, 0) / stateVector.length;
        const variance = stateVector.reduce((a, b) => a + (b - avg)**2, 0) / stateVector.length;
        const unityIndex = Math.max(0, 1 - Math.sqrt(variance));

        let inerchaVector = 0;
        if (aureonData.length > 0) {
            const lastState = aureonData[i-1];
            const lastVector = [lastState.dataIntegrity, lastState.crystalCoherence, lastState.choeranceDrift, lastState.pingPong, lastState.gravReflection];
            inerchaVector = Math.sqrt(stateVector.reduce((sum, val, idx) => sum + (val - lastVector[idx])**2, 0));
        }
        
        // Coherence Index
        const coherenceIndex = unityIndex * dataIntegrity;

        // Prism Status
        let prismStatus: PrismStatus = 'Blue';
        if (dataIntegrity < 0.6 || inerchaVector > 0.5) {
            prismStatus = 'Red';
        } else if (unityIndex > 0.9 && crystalCoherence > 0.7) {
            prismStatus = 'Gold';
        }

        // Build Aureon data point
        const aureonPoint: AureonDataPoint = {
            time: i, market, sentiment, policyRate, dataIntegrity, crystalCoherence, celestialModulators,
            polarisBaseline, choeranceDrift, pingPong, gravReflection, unityIndex,
            inerchaVector, coherenceIndex, prismStatus,
        };

        // Execute the 9-node Auris loop
        const enhancedState = executeAurisLoop(aureonPoint);

        // Merge enhanced state back into aureonPoint
        Object.assign(aureonPoint, enhancedState);

        aureonData.push(aureonPoint);
    }

    return aureonData;
};
