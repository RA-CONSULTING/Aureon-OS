import { AureonDataPoint, CoherenceDataPoint, PrismStatus } from '../types';
import { DataIngestionEngine, DataIngestionSnapshot } from './dataIngestion';
import { DecisionFusionLayer, DecisionSignal } from './decisionFusion';
import { ExecutionEngine, ExecutionReport } from './executionEngine';
import { PerformanceSnapshot, PerformanceTracker } from './performanceTracker';
import { AQTSConfig, DeepPartial, defaultAQTSConfig, mergeConfig } from './config';
import { LighthouseEvent, QGITAEngine } from './qgitaEngine';
import { PortfolioState, RiskAdjustedOrder, RiskManager } from './riskManagement';

export interface AQTSOutput {
  snapshot: DataIngestionSnapshot;
  lighthouseEvent: LighthouseEvent | null;
  decision: DecisionSignal;
  order: RiskAdjustedOrder | null;
  execution: ExecutionReport | null;
  performance: PerformanceSnapshot | null;
  aureonPoint: AureonDataPoint;
  nexusPoint: CoherenceDataPoint;
}

const derivePrismStatus = (confidence: number, spreads: number): PrismStatus => {
  if (confidence > 0.8 && spreads < 0.0015) return 'Gold';
  if (confidence < 0.45 || spreads > 0.003) return 'Red';
  return 'Blue';
};

export class AQTSOrchestrator {
  private config: AQTSConfig;
  private ingestion: DataIngestionEngine;
  private qgita: QGITAEngine;
  private decisionLayer: DecisionFusionLayer;
  private riskManager: RiskManager;
  private execution: ExecutionEngine;
  private performance = new PerformanceTracker();
  private lastAureon: AureonDataPoint | null = null;
  private time = 0;

  constructor(configOverrides: DeepPartial<AQTSConfig> = {}) {
    this.config = mergeConfig(defaultAQTSConfig, configOverrides);
    this.ingestion = new DataIngestionEngine(this.config.ingestion);
    this.qgita = new QGITAEngine(this.config.qgita);
    this.decisionLayer = new DecisionFusionLayer(this.config.decision);
    this.riskManager = new RiskManager(this.config.risk);
    this.execution = new ExecutionEngine(this.config.execution);
  }

  reset(configOverrides: DeepPartial<AQTSConfig> = {}) {
    this.config = mergeConfig(defaultAQTSConfig, configOverrides);
    this.ingestion = new DataIngestionEngine(this.config.ingestion);
    this.qgita = new QGITAEngine(this.config.qgita);
    this.decisionLayer = new DecisionFusionLayer(this.config.decision);
    this.riskManager = new RiskManager(this.config.risk);
    this.execution = new ExecutionEngine(this.config.execution);
    this.performance = new PerformanceTracker();
    this.lastAureon = null;
    this.time = 0;
  }

  getPortfolioState(): PortfolioState {
    return this.riskManager.getState();
  }

  next(): AQTSOutput {
    const snapshot = this.ingestion.next();
    this.qgita.register(snapshot);
    const lighthouseEvent = this.qgita.evaluate();
    const decision = this.decisionLayer.decide(snapshot, lighthouseEvent);
    const order = this.riskManager.evaluate(decision, snapshot);

    let executionReport: ExecutionReport | null = null;
    let performanceSnapshot: PerformanceSnapshot | null = null;

    if (order) {
      executionReport = this.execution.execute(order, snapshot);
      this.riskManager.registerFill(order, executionReport.averagePrice, this.time);
      performanceSnapshot = this.performance.update(
        executionReport,
        order,
        snapshot.consolidatedOHLCV.close
      );
    }

    this.riskManager.markToMarket(snapshot.consolidatedOHLCV.close, this.time);

    const averageSpread = snapshot.exchangeFeeds.reduce((acc, f) => acc + f.spread, 0) / snapshot.exchangeFeeds.length;
    const confidence = lighthouseEvent?.confidence ?? 0.3;
    const prismStatus = derivePrismStatus(confidence, averageSpread);

    const baseIntegrity = Math.max(0, 1 - snapshot.macro.liquidations24h / 400e6);
    const sentimentBalance = 0.5 + decision.sentimentScore / 2;
    const dataIntegrity = Math.max(0, Math.min(1, (baseIntegrity + sentimentBalance) / 2));

    const volumeExpansion = snapshot.consolidatedOHLCV.volume / 1e9;
    const crystalCoherence = Math.max(0, Math.min(1, dataIntegrity * (1 - averageSpread * 1000) + volumeExpansion * 0.05));
    const polarisBaseline = (this.lastAureon?.polarisBaseline ?? 0.5) * 0.7 + crystalCoherence * 0.3;
    const choeranceDrift = crystalCoherence - polarisBaseline;
    const pingPong = Math.tanh(snapshot.onChain.exchangeFlows / 5000);
    const gravReflection = 0.5 + Math.sin(this.time / 50) * 0.3;
    const unityIndex = Math.max(0, Math.min(1, (dataIntegrity + crystalCoherence + sentimentBalance) / 3));

    let inerchaVector = 0;
    if (this.lastAureon) {
      const diff =
        (dataIntegrity - this.lastAureon.dataIntegrity) ** 2 +
        (crystalCoherence - this.lastAureon.crystalCoherence) ** 2 +
        (choeranceDrift - this.lastAureon.choeranceDrift) ** 2;
      inerchaVector = Math.sqrt(diff);
    }

    const aureonPoint: AureonDataPoint = {
      time: this.time,
      market: snapshot.consolidatedOHLCV,
      sentiment: decision.sentimentScore,
      policyRate: snapshot.macro.fundingRateAverage,
      dataIntegrity,
      crystalCoherence,
      celestialModulators: gravReflection,
      polarisBaseline,
      choeranceDrift,
      pingPong,
      gravReflection,
      unityIndex,
      inerchaVector,
      coherenceIndex: unityIndex * dataIntegrity,
      prismStatus,
    };

    const cognitiveCapacity = Math.max(0.1, 1 - averageSpread * 150 - (1 - unityIndex) * 0.5);
    const systemRigidity = Math.max(0.2, 1.2 - cognitiveCapacity * 0.5);
    const sporeConcentration = Math.max(1000, snapshot.macro.liquidations24h / 1e6 * 10 + sentimentBalance * 2000);

    const nexusPoint: CoherenceDataPoint = {
      time: this.time,
      cognitiveCapacity,
      systemRigidity,
      sporeConcentration,
    };

    this.lastAureon = aureonPoint;
    this.time += 1;

    return {
      snapshot,
      lighthouseEvent,
      decision,
      order,
      execution: executionReport,
      performance: performanceSnapshot,
      aureonPoint,
      nexusPoint,
    };
  }
}
