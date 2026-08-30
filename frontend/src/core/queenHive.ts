/**
 * Queen Hive compatibility export.
 *
 * Historical CSV-return compounding has been removed from the production
 * bundle. QueenHive now shares the provider-observed, no-data-safe store used
 * by the browser integration.
 */

import {
  QueenHiveBrowser,
  type QueenHiveConfig,
  type QueenHiveState,
  type HiveMetrics,
} from './queenHiveBrowser';

export type { QueenHiveConfig, QueenHiveState, HiveMetrics };

export class QueenHive extends QueenHiveBrowser {
  constructor(config: QueenHiveConfig = {}) {
    super(config);
  }

  public run(_maxSteps: number, _logInterval: number = 1000): QueenHiveState {
    return this.getState();
  }
}
