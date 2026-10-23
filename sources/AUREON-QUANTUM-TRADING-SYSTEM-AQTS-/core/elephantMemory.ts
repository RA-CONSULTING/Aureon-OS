import { existsSync, readFileSync, writeFileSync, appendFileSync, mkdirSync } from 'fs';
import path from 'path';

export interface SymbolStats {
  symbol: string;
  hunts: number;
  trades: number;
  profitTotal: number;
  wins: number;
  losses: number;
  lastProfit: number;
  lastHuntAt: number; // epoch ms
  lastVolume?: number;
  lastChange?: number;
}

export interface ElephantConfig {
  storePath: string; // JSON file path
  historyPath: string; // JSONL file path
  cooldownMinutes: number; // avoid re-hunting too soon
  lossStreakLimit: number; // optional blacklist threshold
}

export class ElephantMemory {
  private memory: Record<string, SymbolStats> = {};
  private cfg: ElephantConfig;

  constructor(config?: Partial<ElephantConfig>) {
    const artifacts = path.resolve(process.cwd(), 'artifacts');
    try { mkdirSync(artifacts, { recursive: true }); } catch {}

    this.cfg = {
      storePath: config?.storePath || path.join(artifacts, 'elephant_memory.json'),
      historyPath: config?.historyPath || path.join(artifacts, 'hunt_history.jsonl'),
      cooldownMinutes: config?.cooldownMinutes ?? 15,
      lossStreakLimit: config?.lossStreakLimit ?? 3,
    };
    this.load();
  }

  private load() {
    if (existsSync(this.cfg.storePath)) {
      try {
        this.memory = JSON.parse(readFileSync(this.cfg.storePath, 'utf8')) || {};
      } catch {
        this.memory = {};
      }
    }
  }

  private save() {
    writeFileSync(this.cfg.storePath, JSON.stringify(this.memory, null, 2));
  }

  private now(): number { return Date.now(); }

  rememberHunt(symbol: string, meta?: { volume?: number; change?: number; hunter?: string; round?: number }) {
    const s = this.ensure(symbol);
    s.hunts += 1;
    s.lastHuntAt = this.now();
    if (meta?.volume !== undefined) s.lastVolume = meta.volume;
    if (meta?.change !== undefined) s.lastChange = meta.change;
    this.save();

    // Append to history JSONL
    const rec = {
      ts: new Date().toISOString(),
      type: 'hunt',
      symbol,
      meta: meta || {},
    };
    appendFileSync(this.cfg.historyPath, JSON.stringify(rec) + '\n');
  }

  rememberResult(symbol: string, result: { trades?: number; profit?: number }) {
    const s = this.ensure(symbol);
    const trades = result.trades ?? 0;
    const profit = result.profit ?? 0;
    s.trades += trades;
    s.profitTotal += profit;
    s.lastProfit = profit;
    if (profit > 0) s.wins += 1; else if (profit < 0) s.losses += 1;
    this.save();

    const rec = {
      ts: new Date().toISOString(),
      type: 'result',
      symbol,
      trades,
      profit,
    };
    appendFileSync(this.cfg.historyPath, JSON.stringify(rec) + '\n');
  }

  shouldAvoid(symbol: string): boolean {
    const s = this.memory[symbol];
    if (!s) return false;
    const ms = this.cfg.cooldownMinutes * 60 * 1000;
    if (s.lastHuntAt && this.now() - s.lastHuntAt < ms) return true;
    // Optional blacklist by consecutive losses
    if (s.losses >= this.cfg.lossStreakLimit && s.lastProfit <= 0) return true;
    return false;
  }

  getSymbolStats(symbol: string): SymbolStats | undefined {
    return this.memory[symbol];
  }

  private ensure(symbol: string): SymbolStats {
    if (!this.memory[symbol]) {
      this.memory[symbol] = {
        symbol,
        hunts: 0,
        trades: 0,
        profitTotal: 0,
        wins: 0,
        losses: 0,
        lastProfit: 0,
        lastHuntAt: 0,
      };
    }
    return this.memory[symbol];
  }
}

export default ElephantMemory;
