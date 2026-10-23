import { readFileSync } from 'node:fs';
import { AQTSOrchestrator } from '../core/aqtsOrchestrator';
import { AQTSConfig, DeepPartial, defaultAQTSConfig, mergeConfig } from '../core/config';

const loadConfig = (path: string): DeepPartial<AQTSConfig> => {
  try {
    const raw = readFileSync(path, 'utf-8');
    const parsed = JSON.parse(raw) as DeepPartial<AQTSConfig>;
    return parsed;
  } catch (error) {
    console.warn(`Unable to load config from ${path}: ${(error as Error).message}`);
    return {};
  }
};

const configPath = process.env.AQTS_CONFIG ?? 'config/config.example.json';
const steps = Number(process.env.AQTS_STEPS ?? 25);

const overrides = loadConfig(configPath);
const resolvedConfig = mergeConfig(defaultAQTSConfig, overrides);

console.log('🚀 AQTS Simulation Starting');
console.log('Mode:', resolvedConfig.mode);
console.log('Trading Pairs:', resolvedConfig.tradingPairs.join(', '));

const orchestrator = new AQTSOrchestrator(overrides);

for (let i = 0; i < steps; i++) {
  const output = orchestrator.next();
  const price = output.snapshot.consolidatedOHLCV.close.toFixed(2);
  const action = output.decision.action.toUpperCase();
  const confidence = output.decision.confidence.toFixed(2);
  const orderSize = output.order ? output.order.notional.toFixed(2) : '0.00';
  const signal = output.lighthouseEvent?.confidence.toFixed(2) ?? '0.00';

  console.log(
    `#${i + 1} | Price: ${price} | Action: ${action} | QGITA: ${signal} | Confidence: ${confidence} | Notional: ${orderSize}`
  );
}

const portfolio = orchestrator.getPortfolioState();
console.log('\n📊 Portfolio Summary');
console.log('Equity:', portfolio.equity.toFixed(2));
console.log('Open Positions:', portfolio.openPositions.length);
console.log('Max Drawdown:', (portfolio.maxDrawdown * 100).toFixed(2) + '%');

