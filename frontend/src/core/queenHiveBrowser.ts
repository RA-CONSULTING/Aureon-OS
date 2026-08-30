/**
 * Browser compatibility store for provider-observed Queen Hive snapshots.
 *
 * The former implementation embedded invented trade returns and mutated
 * equity in the browser. This store is read-only until a complete live
 * Supabase/provider snapshot is adopted.
 */

export interface HiveMetrics {
  id: string;
  generation: number;
  agents: number;
  equity: number;
  harvestedCapital: number;
  trades: number;
  successfulAgents: number;
  stage: string;
  age: number;
  profitMultiplier: number;
}

export interface QueenHiveState {
  timestamp: number;
  totalHives: number | null;
  totalAgents: number | null;
  totalEquity: number | null;
  totalHarvested: number | null;
  hives: HiveMetrics[];
  generation: number | null;
  splitEvents: Array<{ step: number; newHiveId: string; spawnCapital: number }>;
  truthStatus: 'live' | 'provider_observed' | 'no_data';
  generatedValues: false;
  sourceId: string | null;
  sourceEventId: string | null;
  sourceTimestamp: string | null;
  reason: string | null;
}

export interface QueenHiveConfig {
  maxAgeMs?: number;
}

const noDataState = (): QueenHiveState => ({
  timestamp: Date.now(),
  totalHives: null,
  totalAgents: null,
  totalEquity: null,
  totalHarvested: null,
  hives: [],
  generation: null,
  splitEvents: [],
  truthStatus: 'no_data',
  generatedValues: false,
  sourceId: null,
  sourceEventId: null,
  sourceTimestamp: null,
  reason: 'no_live_queen_hive_snapshot',
});

export class QueenHiveBrowser {
  private state: QueenHiveState = noDataState();
  private readonly maxAgeMs: number;
  private listeners: Array<(state: QueenHiveState) => void> = [];

  constructor(config: QueenHiveConfig = {}) {
    this.maxAgeMs = config.maxAgeMs ?? 30_000;
  }

  public ingestLiveState(candidate: QueenHiveState): QueenHiveState {
    if (!candidate || candidate.generatedValues !== false) {
      throw new Error('Queen Hive snapshot must declare generatedValues=false');
    }
    if (!['live', 'provider_observed'].includes(candidate.truthStatus)) {
      throw new Error('Queen Hive snapshot must be provider-observed');
    }
    if (!candidate.sourceId || !candidate.sourceEventId || !candidate.sourceTimestamp) {
      throw new Error('Queen Hive snapshot requires complete provenance');
    }
    const sourceMs = Date.parse(candidate.sourceTimestamp);
    if (!Number.isFinite(sourceMs) || Math.abs(Date.now() - sourceMs) > this.maxAgeMs) {
      throw new Error('Queen Hive snapshot is stale or has an invalid timestamp');
    }
    const requiredNumbers = [
      candidate.totalHives,
      candidate.totalAgents,
      candidate.totalEquity,
      candidate.totalHarvested,
      candidate.generation,
    ];
    if (requiredNumbers.some(value => value === null || !Number.isFinite(value))) {
      throw new Error('Queen Hive snapshot is missing measured totals');
    }
    this.state = {
      ...candidate,
      hives: [...candidate.hives],
      splitEvents: [...candidate.splitEvents],
      reason: null,
    };
    this.notifyListeners();
    return this.getState();
  }

  public registerWithHiveMind(): void {
    // Registration is performed only by the live Supabase hook after read-back.
  }

  public step(): QueenHiveState {
    return this.getState();
  }

  public simulate(_steps: number): QueenHiveState[] {
    return [this.getState()];
  }

  public getState(): QueenHiveState {
    if (
      this.state.sourceTimestamp &&
      Date.now() - Date.parse(this.state.sourceTimestamp) > this.maxAgeMs
    ) {
      this.state = {
        ...noDataState(),
        reason: 'queen_hive_snapshot_stale',
      };
    }
    return {
      ...this.state,
      hives: [...this.state.hives],
      splitEvents: [...this.state.splitEvents],
    };
  }

  public getTotalEquity(): number | null {
    return this.getState().totalEquity;
  }

  public getHiveCount(): number | null {
    return this.getState().totalHives;
  }

  public getGeneration(): number | null {
    return this.getState().generation;
  }

  public loadTradeReturns(_returns: number[]): void {
    throw new Error('Browser-generated trade returns are prohibited');
  }

  public subscribe(listener: (state: QueenHiveState) => void): () => void {
    this.listeners.push(listener);
    return () => {
      this.listeners = this.listeners.filter(item => item !== listener);
    };
  }

  public reset(): void {
    this.state = noDataState();
    this.notifyListeners();
  }

  private notifyListeners(): void {
    const state = this.getState();
    this.listeners.forEach(listener => listener(state));
  }
}

export function createQueenHive(config?: QueenHiveConfig): QueenHiveBrowser {
  return new QueenHiveBrowser(config);
}

let globalQueenHive: QueenHiveBrowser | null = null;

export function getGlobalQueenHive(): QueenHiveBrowser {
  if (!globalQueenHive) globalQueenHive = new QueenHiveBrowser();
  return globalQueenHive;
}
