import { readFileSync } from 'node:fs';
import { runBacktest } from '../core/backtester';
import { AQTSConfig, DeepPartial, defaultAQTSConfig, mergeConfig } from '../core/config';

const loadConfig = (path: string): DeepPartial<AQTSConfig> => {
  try {
    const raw = readFileSync(path, 'utf-8');
    return JSON.parse(raw) as DeepPartial<AQTSConfig>;
  } catch (error) {
    console.warn(`Unable to load config from ${path}: ${(error as Error).message}`);
    return {};
  }
};

const configPath = process.env.AQTS_CONFIG ?? 'config/config.example.json';
const steps = Number(process.env.AQTS_STEPS ?? 1440);
const iterations = Number(process.env.AQTS_ITERATIONS ?? 5);

const overrides = loadConfig(configPath);
const resolved = mergeConfig(defaultAQTSConfig, overrides);

console.log('🔁 AQTS Backtest');
console.log(`Iterations: ${iterations} | Steps: ${steps}`);
console.log('Mode:', resolved.mode);

const summary = runBacktest({ iterations, steps, config: overrides });

summary.iterations.forEach(iteration => {
  console.log(`\nIteration #${iteration.iteration}`);
  console.log('  Final Equity:', iteration.finalEquity.toFixed(2));
  console.log('  Max Drawdown:', (iteration.maxDrawdown * 100).toFixed(2) + '%');
  console.log('  Trades:', iteration.trades);
  console.log('  Win Rate:', (iteration.winRate * 100).toFixed(2) + '%');
  console.log('  Sharpe:', iteration.sharpe.toFixed(2));
  console.log('  Avg Confidence:', iteration.averageDecisionConfidence.toFixed(2));
});

console.log('\n📈 Aggregate Averages');
console.log('Equity:', summary.averages.equity.toFixed(2));
console.log('Drawdown:', (summary.averages.drawdown * 100).toFixed(2) + '%');
console.log('Win Rate:', (summary.averages.winRate * 100).toFixed(2) + '%');
console.log('Sharpe:', summary.averages.sharpe.toFixed(2));
console.log('Confidence:', summary.averages.confidence.toFixed(2));
console.log('Trades per Iteration:', summary.averages.trades.toFixed(2));

