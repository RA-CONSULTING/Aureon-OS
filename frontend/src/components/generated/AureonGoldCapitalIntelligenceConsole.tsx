import { useEffect, useMemo, useState } from "react";
import { Activity, AlertTriangle, Building2, CheckCircle2, ExternalLink, Gauge, LineChart, Radio, RefreshCw, ShieldCheck } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { ScrollArea } from "@/components/ui/scroll-area";

type JsonMap = Record<string, any>;

const REFRESH_MS = 7500;
const REPORT_URL = "/aureon_gold_capital_intelligence_company.json";

async function fetchJson(url: string): Promise<JsonMap> {
  try {
    const response = await fetch(url, { cache: "no-store" });
    if (!response.ok) return {};
    return await response.json();
  } catch {
    return {};
  }
}

function hasPayload(value: unknown): value is JsonMap {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function fmtNumber(value: unknown, digits = 2): string {
  const number = Number(value);
  if (!Number.isFinite(number)) return "0";
  return number.toLocaleString(undefined, { maximumFractionDigits: digits, minimumFractionDigits: digits });
}

function fmtPercent(value: unknown): string {
  const number = Number(value || 0);
  if (!Number.isFinite(number)) return "0%";
  return `${Math.round(number * 100)}%`;
}

function toneForStatus(status: string): string {
  const lower = status.toLowerCase();
  if (lower.includes("blocked") || lower.includes("stale")) return "border-amber-500/30 bg-amber-500/10 text-amber-200";
  if (lower.includes("ready") || lower.includes("shadow")) return "border-emerald-500/30 bg-emerald-500/10 text-emerald-200";
  return "border-cyan-500/30 bg-cyan-500/10 text-cyan-200";
}

function Pill({ label, tone = "border-border bg-muted/40 text-muted-foreground" }: { label: string; tone?: string }) {
  return (
    <Badge variant="outline" className={`min-w-0 max-w-full justify-start truncate rounded-md px-2 py-1 text-[11px] font-medium ${tone}`}>
      {label}
    </Badge>
  );
}

function Metric({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="min-w-0 rounded-md border border-border/70 bg-background/45 p-3">
      <div className="truncate text-[11px] uppercase tracking-normal text-muted-foreground">{label}</div>
      <div className="mt-1 truncate text-lg font-semibold text-foreground">{value}</div>
      {hint ? <div className="mt-1 truncate text-xs text-muted-foreground">{hint}</div> : null}
    </div>
  );
}

export function AureonGoldCapitalIntelligenceConsole({
  runtimeGoldProof,
  runtimeConnected = false,
  runtimeClearancePending = false,
  runtimeStaleReason = "",
}: {
  runtimeGoldProof?: JsonMap;
  runtimeConnected?: boolean;
  runtimeClearancePending?: boolean;
  runtimeStaleReason?: string;
} = {}) {
  const [report, setReport] = useState<JsonMap>({});
  const [lastLoadedAt, setLastLoadedAt] = useState("");

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      const payload = await fetchJson(REPORT_URL);
      if (cancelled) return;
      setReport(payload);
      setLastLoadedAt(new Date().toLocaleTimeString());
    };
    load();
    const timer = window.setInterval(load, REFRESH_MS);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, []);

  const summary = hasPayload(report.summary) ? report.summary : {};
  const target = hasPayload(report.target) ? report.target : {};
  const decision = hasPayload(report.decision) ? report.decision : {};
  const verifiedRealDataGate = hasPayload(report.verified_real_data_gate) ? report.verified_real_data_gate : {};
  const verifiedDataBlockers = Array.isArray(verifiedRealDataGate.blockers) ? verifiedRealDataGate.blockers : [];
  const verifiedSourceChecks = Array.isArray(verifiedRealDataGate.source_checks) ? verifiedRealDataGate.source_checks : [];
  const verifiedSignalChecks = Array.isArray(verifiedRealDataGate.signal_checks) ? verifiedRealDataGate.signal_checks : [];
  const goldSignalFreshnessMatrix = hasPayload(report.gold_signal_freshness_matrix) ? report.gold_signal_freshness_matrix : {};
  const goldSignalFreshnessRows = Array.isArray(goldSignalFreshnessMatrix.rows) ? goldSignalFreshnessMatrix.rows : [];
  const goldSignalFreshnessBlockers = Array.isArray(goldSignalFreshnessMatrix.blockers) ? goldSignalFreshnessMatrix.blockers : [];
  const goldTickerSourceMesh = hasPayload(report.gold_ticker_source_mesh) ? report.gold_ticker_source_mesh : {};
  const goldTickerSourceLanes = Array.isArray(goldTickerSourceMesh.lanes) ? goldTickerSourceMesh.lanes : [];
  const goldProjectionIntervalValidation = hasPayload(report.gold_projection_interval_validation) ? report.gold_projection_interval_validation : {};
  const goldProjectionIntervals = Array.isArray(goldProjectionIntervalValidation.intervals) ? goldProjectionIntervalValidation.intervals : [];
  const goldProjectionBlockers = Array.isArray(goldProjectionIntervalValidation.blockers) ? goldProjectionIntervalValidation.blockers : [];
  const goldEvolvingProjectionPath = hasPayload(report.gold_evolving_projection_path) ? report.gold_evolving_projection_path : {};
  const evolvingProjectionHorizons = Array.isArray(goldEvolvingProjectionPath.horizons) ? goldEvolvingProjectionPath.horizons : [];
  const evolvingProjectionBlockers = Array.isArray(goldEvolvingProjectionPath.blockers) ? goldEvolvingProjectionPath.blockers : [];
  const goldDynamicMarketEdgeStream = hasPayload(report.gold_dynamic_market_edge_stream) ? report.gold_dynamic_market_edge_stream : {};
  const dynamicEdgeRows = Array.isArray(goldDynamicMarketEdgeStream.stream_rows) ? goldDynamicMarketEdgeStream.stream_rows : [];
  const dynamicEdgeBlockers = Array.isArray(goldDynamicMarketEdgeStream.blockers) ? goldDynamicMarketEdgeStream.blockers : [];
  const dynamicEdgeCandidate = hasPayload(goldDynamicMarketEdgeStream.action_candidate) ? goldDynamicMarketEdgeStream.action_candidate : {};
  const dynamicEdgeTriggerMap = hasPayload(goldDynamicMarketEdgeStream.edge_trigger_map) ? goldDynamicMarketEdgeStream.edge_trigger_map : {};
  const goldHncHistoryFutureBridge = hasPayload(report.gold_hnc_history_future_bridge) ? report.gold_hnc_history_future_bridge : {};
  const historyFutureAnalogs = Array.isArray(goldHncHistoryFutureBridge.historical_analogs) ? goldHncHistoryFutureBridge.historical_analogs : [];
  const historyFutureWindows = Array.isArray(goldHncHistoryFutureBridge.future_windows) ? goldHncHistoryFutureBridge.future_windows : [];
  const historyFutureBlockers = Array.isArray(goldHncHistoryFutureBridge.blockers) ? goldHncHistoryFutureBridge.blockers : [];
  const historyFuturePacket = hasPayload(goldHncHistoryFutureBridge.hnc_compile_packet) ? goldHncHistoryFutureBridge.hnc_compile_packet : {};
  const goldCreativeDreamEngine = hasPayload(report.gold_creative_dream_hypothesis_engine) ? report.gold_creative_dream_hypothesis_engine : {};
  const creativeDreams = Array.isArray(goldCreativeDreamEngine.dreams) ? goldCreativeDreamEngine.dreams : [];
  const creativeDreamQueue = Array.isArray(goldCreativeDreamEngine.validation_queue) ? goldCreativeDreamEngine.validation_queue : [];
  const creativeDreamBlockers = Array.isArray(goldCreativeDreamEngine.blockers) ? goldCreativeDreamEngine.blockers : [];
  const goldProbabilityProjectionForecast = hasPayload(report.gold_probability_projection_forecast) ? report.gold_probability_projection_forecast : {};
  const probabilityTruthDiscipline = hasPayload(goldProbabilityProjectionForecast.truth_discipline) ? goldProbabilityProjectionForecast.truth_discipline : {};
  const probabilityForecastDistribution = hasPayload(goldProbabilityProjectionForecast.forecast_distribution) ? goldProbabilityProjectionForecast.forecast_distribution : {};
  const probabilityValidatedForecast = hasPayload(goldProbabilityProjectionForecast.validated_forecast) ? goldProbabilityProjectionForecast.validated_forecast : {};
  const probabilityOrganismInputs = hasPayload(goldProbabilityProjectionForecast.organism_inputs) ? goldProbabilityProjectionForecast.organism_inputs : {};
  const probabilityForecastClaims = Array.isArray(goldProbabilityProjectionForecast.forecast_claims) ? goldProbabilityProjectionForecast.forecast_claims : [];
  const probabilityContradictions = Array.isArray(goldProbabilityProjectionForecast.contradiction_matrix) ? goldProbabilityProjectionForecast.contradiction_matrix : [];
  const probabilityForecastBlockers = Array.isArray(goldProbabilityProjectionForecast.blockers) ? goldProbabilityProjectionForecast.blockers : [];
  const goldHncActionCoherenceGate = hasPayload(report.gold_hnc_action_coherence_gate) ? report.gold_hnc_action_coherence_gate : {};
  const goldPortfolioUpliftGuard = hasPayload(report.gold_portfolio_uplift_guard) ? report.gold_portfolio_uplift_guard : {};
  const goldPortfolioUpliftBlockers = Array.isArray(goldPortfolioUpliftGuard.blockers) ? goldPortfolioUpliftGuard.blockers : [];
  const goldLiveStreamDeck = hasPayload(report.gold_live_stream_command_deck) ? report.gold_live_stream_command_deck : {};
  const liveDeckTarget = hasPayload(goldLiveStreamDeck.target) ? goldLiveStreamDeck.target : {};
  const liveDeckNow = hasPayload(goldLiveStreamDeck.what_am_i_doing_now) ? goldLiveStreamDeck.what_am_i_doing_now : {};
  const liveDeckNext = hasPayload(goldLiveStreamDeck.what_am_i_doing_next) ? goldLiveStreamDeck.what_am_i_doing_next : {};
  const liveDeckAct = hasPayload(goldLiveStreamDeck.what_will_i_act_on) ? goldLiveStreamDeck.what_will_i_act_on : {};
  const liveDeckResult = hasPayload(goldLiveStreamDeck.act_result) ? goldLiveStreamDeck.act_result : {};
  const liveCapitalProfile = hasPayload(goldLiveStreamDeck.capital_data_profile) ? goldLiveStreamDeck.capital_data_profile : {};
  const liveLeverageMargin = hasPayload(goldLiveStreamDeck.leverage_margin_status) ? goldLiveStreamDeck.leverage_margin_status : {};
  const liveHncFeedback = hasPayload(goldLiveStreamDeck.hnc_feedback_loop) ? goldLiveStreamDeck.hnc_feedback_loop : {};
  const liveStreamChannels = Array.isArray(goldLiveStreamDeck.stream_channels) ? goldLiveStreamDeck.stream_channels : [];
  const liveChartStreams = Array.isArray(goldLiveStreamDeck.chart_streams) ? goldLiveStreamDeck.chart_streams : [];
  const liveDeckBlockers = Array.isArray(goldLiveStreamDeck.blockers) ? goldLiveStreamDeck.blockers : [];
  const goldMarginSignalActionLoop = hasPayload(report.gold_margin_signal_action_loop) ? report.gold_margin_signal_action_loop : {};
  const marginSignalPipeline = Array.isArray(goldMarginSignalActionLoop.signal_to_action_pipeline) ? goldMarginSignalActionLoop.signal_to_action_pipeline : [];
  const marginSignalBlockers = Array.isArray(goldMarginSignalActionLoop.blockers) ? goldMarginSignalActionLoop.blockers : [];
  const marginSignalIntent = hasPayload(goldMarginSignalActionLoop.margin_intent) ? goldMarginSignalActionLoop.margin_intent : {};
  const marginSignalAuthority = hasPayload(goldMarginSignalActionLoop.action_authority) ? goldMarginSignalActionLoop.action_authority : {};
  const marginSignalHncFeedback = hasPayload(goldMarginSignalActionLoop.hnc_auris_node_feedback) ? goldMarginSignalActionLoop.hnc_auris_node_feedback : {};
  const goldProcessLogicFlowGuard = hasPayload(report.gold_process_logic_flow_guard) ? report.gold_process_logic_flow_guard : {};
  const processFlowGates = Array.isArray(goldProcessLogicFlowGuard.gate_sequence) ? goldProcessLogicFlowGuard.gate_sequence : [];
  const processFlowViolations = Array.isArray(goldProcessLogicFlowGuard.violations) ? goldProcessLogicFlowGuard.violations : [];
  const processAuthorityChecks = Array.isArray(goldProcessLogicFlowGuard.action_authority_checks) ? goldProcessLogicFlowGuard.action_authority_checks : [];
  const processFirstBlockedGate = hasPayload(goldProcessLogicFlowGuard.first_blocked_gate) ? goldProcessLogicFlowGuard.first_blocked_gate : {};
  const goldDataSensemakingRouter = hasPayload(report.gold_data_sensemaking_router) ? report.gold_data_sensemaking_router : {};
  const sensemakingSourceRoutes = Array.isArray(goldDataSensemakingRouter.source_routes) ? goldDataSensemakingRouter.source_routes : [];
  const sensemakingMeaningPackets = Array.isArray(goldDataSensemakingRouter.meaning_packets) ? goldDataSensemakingRouter.meaning_packets : [];
  const sensemakingDriverRoutes = Array.isArray(goldDataSensemakingRouter.driver_routes) ? goldDataSensemakingRouter.driver_routes : [];
  const sensemakingBlockers = Array.isArray(goldDataSensemakingRouter.blockers) ? goldDataSensemakingRouter.blockers : [];
  const threePFloorGate = hasPayload(report.three_p_profit_floor_gate) ? report.three_p_profit_floor_gate : {};
  const threePFloorBlockers = Array.isArray(threePFloorGate.blockers) ? threePFloorGate.blockers : [];
  const goldActionCommand = hasPayload(report.gold_action_command) ? report.gold_action_command : {};
  const goldAction = hasPayload(goldActionCommand.act) ? goldActionCommand.act : {};
  const goldActionWho = hasPayload(goldActionCommand.who) ? goldActionCommand.who : {};
  const goldActionWhat = hasPayload(goldActionCommand.what) ? goldActionCommand.what : {};
  const goldActionWhen = hasPayload(goldActionCommand.when) ? goldActionCommand.when : {};
  const goldActionHow = hasPayload(goldActionCommand.how) ? goldActionCommand.how : {};
  const goldProofChain = Array.isArray(goldActionCommand.proof_chain) ? goldActionCommand.proof_chain : [];
  const commandSystems = Array.isArray(goldActionCommand.command_systems) ? goldActionCommand.command_systems : [];
  const goldShadowFocus = hasPayload(report.gold_shadow_trading_focus) ? report.gold_shadow_trading_focus : {};
  const goldShadowPromotionGate = hasPayload(goldShadowFocus.promotion_gate) ? goldShadowFocus.promotion_gate : {};
  const goldShadowCandidates = Array.isArray(goldShadowFocus.shadow_candidates) ? goldShadowFocus.shadow_candidates : [];
  const goldShadowContextItems = Array.isArray(goldShadowFocus.context_only_shadow_items) ? goldShadowFocus.context_only_shadow_items : [];
  const goldShadowExcludedItems = Array.isArray(goldShadowFocus.excluded_shadow_items) ? goldShadowFocus.excluded_shadow_items : [];
  const goldShadowEnergyLanes = Array.isArray(goldShadowFocus.energy_context_lanes) ? goldShadowFocus.energy_context_lanes : [];
  const goldShadowFocusRules = Array.isArray(goldShadowFocus.focus_rules) ? goldShadowFocus.focus_rules : [];
  const cognitiveRoute = hasPayload(report.hnc_auris_quantum_probability_route) ? report.hnc_auris_quantum_probability_route : {};
  const cognitiveHnc = hasPayload(cognitiveRoute.hnc) ? cognitiveRoute.hnc : {};
  const cognitiveAurisNodes = hasPayload(cognitiveRoute.auris_nodes) ? cognitiveRoute.auris_nodes : {};
  const cognitiveLambda = hasPayload(cognitiveRoute.lambda_system) ? cognitiveRoute.lambda_system : {};
  const cognitiveQuantum = hasPayload(cognitiveRoute.quantum_systems) ? cognitiveRoute.quantum_systems : {};
  const cognitiveProbability = hasPayload(cognitiveRoute.probability_systems) ? cognitiveRoute.probability_systems : {};
  const cognitiveRouteSurfaces = Array.isArray(cognitiveRoute.route_surfaces) ? cognitiveRoute.route_surfaces : [];
  const cognitiveRouteBlockers = Array.isArray(cognitiveRoute.blockers) ? cognitiveRoute.blockers : [];
  const hftSpeedGate = hasPayload(report.hft_speed_prediction_gate) ? report.hft_speed_prediction_gate : {};
  const hftPredictionValidation = hasPayload(hftSpeedGate.prediction_validation) ? hftSpeedGate.prediction_validation : {};
  const hftLatencyChecks = Array.isArray(hftSpeedGate.latency_checks) ? hftSpeedGate.latency_checks : [];
  const hftRouteSurfaces = Array.isArray(hftSpeedGate.route_surfaces) ? hftSpeedGate.route_surfaces : [];
  const hftBlockers = Array.isArray(hftSpeedGate.blockers) ? hftSpeedGate.blockers : [];
  const historicalStress = hasPayload(report.gold_historical_stress_test) ? report.gold_historical_stress_test : {};
  const historicalStressValidation = hasPayload(historicalStress.prediction_validation) ? historicalStress.prediction_validation : {};
  const historicalStressScenarios = Array.isArray(historicalStress.scenarios) ? historicalStress.scenarios : [];
  const historicalStressSurfaces = Array.isArray(historicalStress.route_surfaces) ? historicalStress.route_surfaces : [];
  const historicalStressBlockers = Array.isArray(historicalStress.blockers) ? historicalStress.blockers : [];
  const price = hasPayload(report.price_energy_hypothesis) ? report.price_energy_hypothesis : {};
  const blockers = Array.isArray(report.blockers) ? report.blockers : [];
  const roles = Array.isArray(report.company_roles) ? report.company_roles : [];
  const signals = Array.isArray(report.signals) ? report.signals : [];
  const sourceEvidence = Array.isArray(report.source_evidence) ? report.source_evidence : [];
  const nextActions = Array.isArray(report.next_actions) ? report.next_actions : [];
  const sourcePackets = Array.isArray(report.source_packets) ? report.source_packets : [];
  const goldIntelligenceMap = Array.isArray(report.gold_intelligence_map) ? report.gold_intelligence_map : [];
  const localResearchPackets = Array.isArray(report.local_research_packets) ? report.local_research_packets : [];
  const intelligenceGaps = Array.isArray(report.intelligence_gaps) ? report.intelligence_gaps : [];
  const toolActivationPlan = Array.isArray(report.tool_activation_plan) ? report.tool_activation_plan : [];
  const crossMarketDrivers = Array.isArray(report.cross_market_driver_matrix) ? report.cross_market_driver_matrix : [];
  const goldExchangeOptimization = hasPayload(report.gold_exchange_optimization) ? report.gold_exchange_optimization : {};
  const optimizedVenues = Array.isArray(goldExchangeOptimization.venues) ? goldExchangeOptimization.venues : [];
  const exchangeWatchlists = Array.isArray(goldExchangeOptimization.related_asset_watchlist) ? goldExchangeOptimization.related_asset_watchlist : [];
  const exchangeMonitorContracts = Array.isArray(goldExchangeOptimization.monitoring_contract) ? goldExchangeOptimization.monitoring_contract : [];
  const exchangeOptimizationBlockers = Array.isArray(goldExchangeOptimization.blockers) ? goldExchangeOptimization.blockers : [];
  const marginTraderUnity = hasPayload(report.gold_margin_trader_unity) ? report.gold_margin_trader_unity : {};
  const marginRoles = Array.isArray(marginTraderUnity.margin_roles) ? marginTraderUnity.margin_roles : [];
  const marginDirectives = Array.isArray(marginTraderUnity.mission_directives) ? marginTraderUnity.mission_directives : [];
  const marginSurfaces = Array.isArray(marginTraderUnity.route_surfaces) ? marginTraderUnity.route_surfaces : [];
  const marginBlockers = Array.isArray(marginTraderUnity.blockers) ? marginTraderUnity.blockers : [];
  const marginCommand = hasPayload(marginTraderUnity.margin_command) ? marginTraderUnity.margin_command : {};
  const historicalSignalLab = hasPayload(report.historical_signal_lab) ? report.historical_signal_lab : {};
  const historicalReplayLanes = Array.isArray(historicalSignalLab.replay_lanes) ? historicalSignalLab.replay_lanes : [];
  const leadLagCandidates = Array.isArray(historicalSignalLab.lead_lag_candidates) ? historicalSignalLab.lead_lag_candidates : [];
  const orderbookEvidence = hasPayload(historicalSignalLab.orderbook_evidence) ? historicalSignalLab.orderbook_evidence : {};
  const orderbookSamples = Array.isArray(orderbookEvidence.samples) ? orderbookEvidence.samples : [];
  const hypothesisTests = Array.isArray(historicalSignalLab.hypothesis_tests) ? historicalSignalLab.hypothesis_tests : [];
  const goldPriorityWorkbench = hasPayload(report.gold_priority_workbench) ? report.gold_priority_workbench : {};
  const priorityArtifactManifest = hasPayload(goldPriorityWorkbench.artifact_manifest) ? goldPriorityWorkbench.artifact_manifest : {};
  const priorityDataQueue = Array.isArray(goldPriorityWorkbench.data_priority_queue) ? goldPriorityWorkbench.data_priority_queue : [];
  const forecastPoints = Array.isArray(goldPriorityWorkbench.forecast_points) ? goldPriorityWorkbench.forecast_points : [];
  const swarmIntelligence = hasPayload(report.swarm_intelligence) ? report.swarm_intelligence : {};
  const swarmAgents = Array.isArray(swarmIntelligence.agents) ? swarmIntelligence.agents : [];
  const swarmCompileGate = hasPayload(swarmIntelligence.compile_gate) ? swarmIntelligence.compile_gate : {};
  const agentCodingSupport = hasPayload(report.gold_agent_coding_support) ? report.gold_agent_coding_support : {};
  const agentChatLanes = Array.isArray(agentCodingSupport.chat_lanes) ? agentCodingSupport.chat_lanes : [];
  const agentToolLanes = Array.isArray(agentCodingSupport.tool_lanes) ? agentCodingSupport.tool_lanes : [];
  const agentMonitorTargets = Array.isArray(agentCodingSupport.monitor_targets) ? agentCodingSupport.monitor_targets : [];
  const agentSupportArtifacts = Array.isArray(agentCodingSupport.support_artifacts) ? agentCodingSupport.support_artifacts : [];
  const agentSupportSurfaces = Array.isArray(agentCodingSupport.route_surfaces) ? agentCodingSupport.route_surfaces : [];
  const agentSupportBlockers = Array.isArray(agentCodingSupport.blockers) ? agentCodingSupport.blockers : [];
  const marketUniverse = hasPayload(report.gold_market_universe) ? report.gold_market_universe : {};
  const marketBuckets = hasPayload(marketUniverse.bucket_counts) ? marketUniverse.bucket_counts : {};
  const energyPercent = Math.max(0, Math.min(100, Number(decision.gold_energy_score || summary.gold_energy_score || 0) * 100));
  const confidencePercent = Math.max(0, Math.min(100, Number(decision.confidence || summary.confidence || 0) * 100));
  const coveragePercent = Math.max(0, Math.min(100, Number(summary.gold_intelligence_coverage_score || 0) * 100));
  const liveRuntimeProof = hasPayload(runtimeGoldProof) ? runtimeGoldProof : {};
  const liveGoldSource = hasPayload(liveRuntimeProof.fresh_gold_data_source) ? liveRuntimeProof.fresh_gold_data_source : {};
  const liveGoldProofReady = Boolean(liveRuntimeProof.gold_runtime_candidate_ready || liveGoldSource.ready);
  const liveCandidateSide = String(liveRuntimeProof.candidate_side || dynamicEdgeCandidate.side || decision.direction_guess || summary.direction_guess || "HOLD");
  const liveCandidateSymbol = String(liveRuntimeProof.candidate_symbol || liveGoldSource.normalized_symbol || target.symbol || summary.target_symbol || "GOLD");
  const liveCandidateConfidence = Number(liveRuntimeProof.candidate_confidence ?? liveGoldSource.confidence ?? decision.confidence ?? summary.confidence ?? 0);
  const effectiveMidPrice = liveGoldSource.reference_price ?? liveGoldSource.price ?? price.mid_price;
  const effectiveSnapshotAge = liveGoldSource.age_sec ?? summary.capital_snapshot_age_sec;
  const effectiveSnapshotFresh = Boolean(liveGoldSource.ready || summary.capital_snapshot_fresh);
  const effectiveRuntimeLabel = runtimeConnected
    ? runtimeClearancePending
      ? "checking"
      : "live"
    : summary.runtime_stale
      ? "stale"
      : "fresh";
  const effectiveRuntimeHint = runtimeConnected && liveGoldProofReady
    ? `${liveCandidateSymbol} ${liveCandidateSide}`
    : String(runtimeStaleReason || summary.stale_reason || "runtime evidence");
  const effectiveCapitalProfile = {
    ...liveCapitalProfile,
    bid: liveGoldSource.bid ?? liveCapitalProfile.bid,
    ask: liveGoldSource.ask ?? liveCapitalProfile.ask,
    mid_price: liveGoldSource.reference_price ?? liveCapitalProfile.mid_price,
    spread: liveGoldSource.spread ?? liveCapitalProfile.spread,
    spread_pct: liveGoldSource.spread_pct ?? liveCapitalProfile.spread_pct,
    snapshot_age_seconds: liveGoldSource.age_sec ?? liveCapitalProfile.snapshot_age_seconds,
    snapshot_fresh: Boolean(liveGoldSource.ready || liveCapitalProfile.snapshot_fresh),
    market_status: liveCapitalProfile.market_status || (liveGoldSource.ready ? "TRADEABLE" : undefined),
  };
  const effectiveFloorEntry = liveGoldSource.reference_price ?? threePFloorGate.entry_level;
  const effectiveMarginEntry = liveGoldSource.reference_price ?? marginSignalIntent.entry_level;
  const effectiveShadowEntry = liveGoldSource.reference_price ?? goldShadowPromotionGate.entry_level;
  const effectiveNextEdgeStep = liveGoldSource.ready
    ? "validate interval projection"
    : String(goldDynamicMarketEdgeStream.next_action || "refresh").replace(/_/g, " ");
  const liveDynamicEdgeRows = dynamicEdgeRows.map((row: JsonMap) => {
    const text = `${String(row.id || "")} ${String(row.label || "")}`.toLowerCase();
    if (!liveGoldSource.ready || !(text.includes("capital") && (text.includes("gold") || text.includes("xau")))) {
      return row;
    }
    return {
      ...row,
      fresh: true,
      age_seconds: liveGoldSource.age_sec,
      edge_score: Math.max(Number(row.edge_score || 0), Number(liveGoldSource.confidence || 0)),
    };
  });
  const staleManifestBlockers = new Set([
    "runtime_stale",
    "capital_gold_snapshot_stale",
    "verified_real_data_gate_blocking",
  ]);
  const visibleBlockingTruth = liveGoldProofReady
    ? blockers.filter((blocker: JsonMap) => !staleManifestBlockers.has(String(blocker.id || "")))
    : blockers;
  const liveProofSupersedesBlocker = (blocker: JsonMap) => {
    if (!liveGoldProofReady) return false;
    const text = `${String(blocker.id || "")} ${String(blocker.reason || "")}`.toLowerCase();
    return (
      text.includes("runtime_stale") ||
      text.includes("runtime is stale") ||
      text.includes("runtime stale") ||
      text.includes("runtime_not_fresh") ||
      text.includes("runtime not fresh") ||
      text.includes("runtime_stale_blocks") ||
      text.includes("tick_in_progress_stalled") ||
      text.includes("runtime freshness is required") ||
      text.includes("restore a fresh tick") ||
      text.includes("trust_decision_shadow_until_runtime_fresh") ||
      text.includes("trust_decision_wait_for_runtime_clearance") ||
      text.includes("capital_gold_snapshot") ||
      text.includes("capital_gold_live_quote_missing_or_stale") ||
      text.includes("capital gold stream not fresh") ||
      text.includes("capital gold target stream/profile is not fresh") ||
      text.includes("capital_gold_profile_stale") ||
      text.includes("capital gold profile/snapshot is not fresh") ||
      text.includes("fresh gold bid/ask is required")
    );
  };
  const liveThreePFloorBlockers = threePFloorBlockers.filter((blocker: JsonMap) => !liveProofSupersedesBlocker(blocker));
  const liveDeckVisibleBlockers = liveDeckBlockers.filter((blocker: JsonMap) => !liveProofSupersedesBlocker(blocker));
  const liveMarginSignalBlockers = marginSignalBlockers.filter((blocker: JsonMap) => !liveProofSupersedesBlocker(blocker));
  const liveMarginUnityBlockers = marginBlockers.filter((blocker: JsonMap) => !liveProofSupersedesBlocker(blocker));
  const liveDynamicEdgeBlockers = dynamicEdgeBlockers.filter((blocker: JsonMap) => !liveProofSupersedesBlocker(blocker));
  const effectiveDecisionReason = liveGoldProofReady
    ? `Terminal-state has fresh Capital GOLD proof for ${liveCandidateSymbol}; action remains shadow/held until interval validation allows a BUY/SELL GOLD intent.`
    : String(decision.reason || "Waiting for Aureon to publish the gold decision packet.");

  const actionTone = useMemo(() => {
    if (decision.live_trade_allowed) return "border-red-500/30 bg-red-500/10 text-red-200";
    if (decision.shadow_observation_allowed) return "border-emerald-500/30 bg-emerald-500/10 text-emerald-200";
    return "border-amber-500/30 bg-amber-500/10 text-amber-200";
  }, [decision.live_trade_allowed, decision.shadow_observation_allowed]);

  return (
    <Card className="bg-card/85" data-testid="gold-capital-intelligence-console">
      <CardHeader className="space-y-3 pb-3">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0">
            <CardTitle className="flex min-w-0 items-center gap-2 text-xl">
              <Building2 className="h-5 w-5 shrink-0 text-yellow-300" />
              <span className="truncate">Gold Capital Intelligence Company</span>
            </CardTitle>
            <p className="mt-1 max-w-4xl text-sm text-muted-foreground">
              Aureon gathers Capital GOLD, exchange, macro-gap, HNC/Auris, runtime, and shadow-validation evidence into one read-only price-energy thesis.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
          <Pill label={String(report.status || "waiting_for_gold_report")} tone={toneForStatus(String(report.status || ""))} />
          <Pill label={`loaded ${lastLoadedAt || "waiting"}`} tone="border-cyan-500/30 bg-cyan-500/10 text-cyan-200" />
          <Pill label={`${Math.round(REFRESH_MS / 1000)}s refresh`} tone="border-slate-500/30 bg-slate-500/10 text-slate-200" />
          <Pill label={runtimeConnected ? "terminal-state linked" : "manifest only"} tone={runtimeConnected ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200" : "border-amber-500/30 bg-amber-500/10 text-amber-200"} />
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <Pill label={`target ${String(target.symbol || summary.target_symbol || "GOLD")}`} tone="border-yellow-500/30 bg-yellow-500/10 text-yellow-100" />
          <Pill label={`epic ${String(target.epic || summary.target_epic || "GOLD")}`} tone="border-yellow-500/30 bg-yellow-500/10 text-yellow-100" />
          <Pill label={decision.live_trade_allowed ? "live trade allowed" : "live trade blocked"} tone={decision.live_trade_allowed ? "border-red-500/30 bg-red-500/10 text-red-200" : "border-emerald-500/30 bg-emerald-500/10 text-emerald-200"} />
          <Pill label={decision.shadow_observation_allowed ? "shadow observation allowed" : "shadow observation held"} tone={actionTone} />
          <Pill label="not financial advice" tone="border-blue-500/30 bg-blue-500/10 text-blue-200" />
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-9">
          <Metric label="Mid Price" value={`$${fmtNumber(effectiveMidPrice, 2)}`} hint={`${String(price.currency || "USD")} ${liveGoldSource.ready ? "terminal-state quote" : "Capital snapshot"}`} />
          <Metric label="Hypothesis Range" value={`$${fmtNumber(price.hypothesis_low, 0)} - $${fmtNumber(price.hypothesis_high, 0)}`} hint={String(price.band_reason || "awaiting range proof")} />
          <Metric label="Direction Guess" value={liveCandidateSide} hint={String(liveGoldSource.side_reason || summary.action_posture || "shadow observe")} />
          <Metric label="Runtime" value={effectiveRuntimeLabel} hint={effectiveRuntimeHint} />
          <Metric label="Capital Snapshot" value={effectiveSnapshotFresh ? "fresh" : "stale"} hint={`${fmtNumber(effectiveSnapshotAge, 0)}s old`} />
          <Metric label="Gold Intel Map" value={`${fmtNumber(summary.gold_intelligence_surface_ready_count, 0)}/${fmtNumber(summary.gold_intelligence_surface_count, 0)}`} hint={`${Math.round(coveragePercent)}% coverage`} />
          <Metric label="Replay Lanes" value={`${fmtNumber(summary.historical_signal_ready_count, 0)}/${fmtNumber(summary.historical_signal_lane_count, 0)}`} hint={String(summary.historical_signal_status || "historical lab")} />
          <Metric label="Real Data" value={summary.verified_real_data_action_allowed ? "passed" : "blocked"} hint={`${fmtNumber(summary.verified_real_data_fresh_source_count, 0)}/${fmtNumber(summary.verified_real_data_required_source_count, 0)} fresh`} />
          <Metric label="Swarm Agents" value={`${fmtNumber(summary.gold_swarm_active_agent_count, 0)}/${fmtNumber(summary.gold_swarm_agent_count, 0)}`} hint={String(summary.gold_swarm_compile_state || "compile gate")} />
        </div>

        <div className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
          <section className="rounded-md border border-border/70 bg-background/35 p-4">
            <div className="flex items-center justify-between gap-3">
              <div className="flex min-w-0 items-center gap-2">
                <Gauge className="h-4 w-4 shrink-0 text-yellow-300" />
                <h3 className="truncate text-sm font-semibold">Price Energy Thesis</h3>
              </div>
              <Pill label={`confidence ${fmtPercent(decision.confidence || summary.confidence)}`} tone="border-cyan-500/30 bg-cyan-500/10 text-cyan-200" />
            </div>
            <div className="mt-4 space-y-3">
              <div>
                <div className="mb-1 flex justify-between gap-2 text-xs text-muted-foreground">
                  <span>Gold energy score</span>
                  <span>{Math.round(energyPercent)}%</span>
                </div>
                <Progress value={energyPercent} />
              </div>
              <div>
                <div className="mb-1 flex justify-between gap-2 text-xs text-muted-foreground">
                  <span>Confidence</span>
                  <span>{Math.round(confidencePercent)}%</span>
                </div>
                <Progress value={confidencePercent} />
              </div>
              <p className="text-sm text-muted-foreground">{effectiveDecisionReason}</p>
            </div>
          </section>

          <section className="rounded-md border border-emerald-500/30 bg-emerald-500/5 p-4">
            <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
              <div className="flex min-w-0 items-center gap-2">
                <ShieldCheck className="h-4 w-4 shrink-0 text-emerald-300" />
                <h3 className="truncate text-sm font-semibold">3p Profit Floor Gate</h3>
              </div>
              <div className="flex flex-wrap gap-2">
                <Pill label={String(threePFloorGate.state || "floor waiting")} tone={toneForStatus(String(threePFloorGate.state || ""))} />
                <Pill label={`${String(threePFloorGate.side || "HOLD")}`} tone="border-yellow-500/30 bg-yellow-500/10 text-yellow-100" />
              </div>
            </div>
            <div className="mt-3 grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
              <Metric label="Floor" value={`${fmtNumber(threePFloorGate.profit_floor_account_currency, 2)}`} hint={String(threePFloorGate.profit_floor_label || "net")} />
              <Metric label="Entry" value={`${fmtNumber(effectiveFloorEntry, 2)}`} hint={liveGoldSource.ready ? "terminal-state quote" : String(threePFloorGate.entry_instruction || "entry")} />
              <Metric label="Target" value={`${fmtNumber(threePFloorGate.target_level, 2)}`} hint="shadow target" />
              <Metric label="Size" value={`${fmtNumber(threePFloorGate.suggested_shadow_size, 4)}`} hint="shadow only" />
            </div>
            <div className="mt-3 grid gap-2 sm:grid-cols-3">
              <div className="rounded border border-border/40 bg-background/35 p-2 text-xs">
                <div className="text-muted-foreground">minimum move</div>
                <div className="font-semibold">{fmtNumber(threePFloorGate.minimum_price_move_for_floor_at_min_size, 4)}</div>
              </div>
              <div className="rounded border border-border/40 bg-background/35 p-2 text-xs">
                <div className="text-muted-foreground">cost/unit</div>
                <div className="font-semibold">{fmtNumber(threePFloorGate.known_cost_per_unit, 4)}</div>
              </div>
              <div className="rounded border border-border/40 bg-background/35 p-2 text-xs">
                <div className="text-muted-foreground">estimated net</div>
                <div className="font-semibold">{fmtNumber(threePFloorGate.estimated_net_at_suggested_size, 4)}</div>
              </div>
            </div>
            <div className="mt-3 grid gap-2 md:grid-cols-2">
              {liveThreePFloorBlockers.slice(0, 4).map((blocker: JsonMap) => (
                <div key={String(blocker.id || blocker.reason)} className="rounded-md border border-amber-500/20 bg-amber-500/5 p-2">
                  <div className="truncate text-xs font-medium text-amber-100">{String(blocker.id || "blocker")}</div>
                  <div className="mt-1 line-clamp-2 text-[11px] text-muted-foreground">{String(blocker.reason || "")}</div>
                </div>
              ))}
            </div>
          </section>

          <section className="rounded-md border border-border/70 bg-background/35 p-4">
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-amber-300" />
              <h3 className="text-sm font-semibold">Blocking Truth</h3>
            </div>
            <div className="mt-3 grid gap-2 md:grid-cols-2">
              {visibleBlockingTruth.length ? (
                visibleBlockingTruth.slice(0, 6).map((blocker: JsonMap) => (
                  <div key={String(blocker.id || blocker.reason)} className="rounded-md border border-amber-500/20 bg-amber-500/5 p-3">
                    <div className="truncate text-sm font-medium text-amber-100">{String(blocker.id || "blocker")}</div>
                    <div className="mt-1 line-clamp-2 text-xs text-muted-foreground">{String(blocker.reason || "No reason published.")}</div>
                  </div>
                ))
              ) : (
                <div className="rounded-md border border-emerald-500/20 bg-emerald-500/5 p-3 text-sm text-emerald-200">No blocking gold evidence currently reported.</div>
              )}
            </div>
          </section>
        </div>

        <section className="rounded-md border border-cyan-500/30 bg-cyan-500/5 p-4">
          <div className="mb-3 flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
            <div className="flex min-w-0 items-center gap-2">
              <Radio className="h-4 w-4 shrink-0 text-cyan-300" />
              <h3 className="truncate text-sm font-semibold">GOLD Live Stream Command Deck</h3>
            </div>
            <div className="flex flex-wrap gap-2">
              <Pill label={String(goldLiveStreamDeck.status || "live deck waiting")} tone={toneForStatus(String(goldLiveStreamDeck.status || ""))} />
              <Pill label={String(liveDeckTarget.targeting_state || "targeting waiting").replace(/_/g, " ")} tone="border-yellow-500/30 bg-yellow-500/10 text-yellow-100" />
              <Pill label={`${fmtNumber(liveStreamChannels.length, 0)} streams`} tone="border-cyan-500/30 bg-cyan-500/10 text-cyan-200" />
            </div>
          </div>
          <p className="mb-3 text-sm text-muted-foreground">
            Read-only live GOLD analytics: what Aureon is doing now, what comes next, what it would act on, the result, Capital profile, leverage/margin status, chart streams, and the HNC/Auris feedback loop.
          </p>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-6">
            <Metric label="Doing Now" value={String(liveDeckNow.state || "hold")} hint={String(liveDeckResult.state || "result held").replace(/_/g, " ")} />
            <Metric label="Doing Next" value={String(liveDeckNext.targeting || "refresh").replace(/_/g, " ")} hint={String(liveDeckNext.next_refresh_action || "next action")} />
            <Metric label="Act On" value={String(liveDeckAct.candidate || "Capital GOLD")} hint={`${String(liveDeckAct.side || "HOLD")} ${String(liveDeckAct.allowed_action || "hold")}`} />
            <Metric label="Capital Profile" value={effectiveCapitalProfile.snapshot_fresh ? "fresh" : "stale"} hint={`${fmtNumber(effectiveCapitalProfile.snapshot_age_seconds, 0)}s old`} />
            <Metric label="Leverage" value={fmtNumber(liveLeverageMargin.leverage_estimate, 2)} hint={`margin ${fmtNumber(liveLeverageMargin.margin_factor_pct, 2)}%`} />
            <Metric label="Min Margin" value={fmtNumber(liveLeverageMargin.margin_required_for_min_deal, 2)} hint="for min deal" />
          </div>
          <div className="mt-4 grid gap-4 xl:grid-cols-[1fr_1fr]">
            <div className="grid gap-3">
              <div className="rounded-md border border-border/60 bg-background/50 p-3">
                <div className="text-sm font-medium">Capital Data Profile</div>
                <div className="mt-2 grid gap-2 md:grid-cols-3 text-xs">
                  <div className="rounded border border-border/40 bg-background/35 p-2">
                    <div className="text-muted-foreground">bid / ask</div>
                    <div className="font-semibold">{fmtNumber(effectiveCapitalProfile.bid, 2)} / {fmtNumber(effectiveCapitalProfile.ask, 2)}</div>
                  </div>
                  <div className="rounded border border-border/40 bg-background/35 p-2">
                    <div className="text-muted-foreground">spread</div>
                    <div className="font-semibold">{fmtNumber(effectiveCapitalProfile.spread, 5)}</div>
                  </div>
                  <div className="rounded border border-border/40 bg-background/35 p-2">
                    <div className="text-muted-foreground">market</div>
                    <div className="font-semibold">{String(effectiveCapitalProfile.market_status || "unknown")}</div>
                  </div>
                  <div className="rounded border border-border/40 bg-background/35 p-2">
                    <div className="text-muted-foreground">min deal</div>
                    <div className="font-semibold">{fmtNumber(effectiveCapitalProfile.minimum_deal_size, 4)}</div>
                  </div>
                  <div className="rounded border border-border/40 bg-background/35 p-2">
                    <div className="text-muted-foreground">margin state</div>
                    <div className="font-semibold">{String(liveLeverageMargin.margin_unity_state || "held").replace(/_/g, " ")}</div>
                  </div>
                  <div className="rounded border border-border/40 bg-background/35 p-2">
                    <div className="text-muted-foreground">mutation</div>
                    <div className="font-semibold">{liveLeverageMargin.margin_order_allowed ? "armed" : "blocked"}</div>
                  </div>
                </div>
              </div>
              <div className="rounded-md border border-border/60 bg-background/50 p-3">
                <div className="text-sm font-medium">What Happens Next</div>
                <div className="mt-2 grid gap-2">
                  {liveDeckVisibleBlockers.length ? liveDeckVisibleBlockers.slice(0, 4).map((blocker: JsonMap) => (
                    <div key={String(blocker.id || blocker.reason)} className="rounded border border-amber-500/30 bg-amber-500/10 p-2 text-xs text-amber-100">
                      <div className="font-medium">{String(blocker.id || "blocker").replace(/_/g, " ")}</div>
                      <div className="mt-1 line-clamp-2">{String(blocker.reason || "")}</div>
                    </div>
                  )) : <div className="rounded border border-emerald-500/30 bg-emerald-500/10 p-2 text-xs text-emerald-100">Terminal-state GOLD proof is fresh; live order mutation still stays behind interval validation and runtime authority gates.</div>}
                </div>
              </div>
            </div>
            <div className="grid gap-3">
              <div className="rounded-md border border-border/60 bg-background/50 p-3">
                <div className="text-sm font-medium">Live Stream Channels</div>
                <ScrollArea className="mt-2 h-48 pr-3">
                  <div className="grid gap-2">
                    {liveStreamChannels.map((channel: JsonMap) => (
                      <div key={String(channel.id || channel.label)} className="rounded border border-border/40 bg-background/35 p-2 text-xs">
                        <div className="flex items-start justify-between gap-2">
                          <div className="min-w-0">
                            <div className="truncate font-medium">{String(channel.label || channel.id)}</div>
                            <div className="mt-1 line-clamp-2 text-muted-foreground">{String(channel.next_action || "")}</div>
                          </div>
                          <Pill label={String(channel.status || "waiting")} tone={channel.fresh ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200" : "border-amber-500/30 bg-amber-500/10 text-amber-200"} />
                        </div>
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              </div>
              <div className="rounded-md border border-border/60 bg-background/50 p-3">
                <div className="text-sm font-medium">Chart Analytics And HNC Feedback</div>
                <div className="mt-2 grid gap-2 md:grid-cols-2">
                  {liveChartStreams.map((chart: JsonMap) => (
                    <div key={String(chart.id || chart.label)} className="rounded border border-border/40 bg-background/35 p-2 text-xs">
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <div className="truncate font-medium">{String(chart.label || chart.id)}</div>
                          <div className="mt-1 truncate text-muted-foreground">{String(chart.chart_type || "chart")}</div>
                        </div>
                        <Pill label={chart.fresh ? "fresh" : "held"} tone={chart.fresh ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200" : "border-amber-500/30 bg-amber-500/10 text-amber-200"} />
                      </div>
                    </div>
                  ))}
                </div>
                <div className="mt-2 line-clamp-2 text-xs text-muted-foreground">{String(liveHncFeedback.how || "HNC feedback waits for fresh proof.")}</div>
              </div>
            </div>
          </div>
        </section>

        <section className="rounded-md border border-yellow-500/30 bg-yellow-500/5 p-4">
          <div className="mb-3 flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
            <div className="flex min-w-0 items-center gap-2">
              <Gauge className="h-4 w-4 shrink-0 text-yellow-300" />
              <h3 className="truncate text-sm font-semibold">GOLD Margin Signal Action Loop</h3>
            </div>
            <div className="flex flex-wrap gap-2">
              <Pill label={String(goldMarginSignalActionLoop.status || "action loop waiting")} tone={toneForStatus(String(goldMarginSignalActionLoop.status || ""))} />
              <Pill label={String(goldMarginSignalActionLoop.acting_state || "held").replace(/_/g, " ")} tone="border-yellow-500/30 bg-yellow-500/10 text-yellow-100" />
              <Pill label={`${fmtNumber(goldMarginSignalActionLoop.ready_stage_count, 0)}/${fmtNumber(goldMarginSignalActionLoop.stage_count, 0)} stages`} tone="border-cyan-500/30 bg-cyan-500/10 text-cyan-200" />
            </div>
          </div>
          <p className="mb-3 text-sm text-muted-foreground">
            This is the proof bridge from GOLD intelligence into margin action: signals, intervals, HNC/Auris, margin unity, portfolio uplift, and the action command must all agree before a shadow margin intent can be published.
          </p>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-6">
            <Metric label="Acting State" value={String(goldMarginSignalActionLoop.acting_state || "held").replace(/_/g, " ")} hint={String(goldMarginSignalActionLoop.next_action || "next action")} />
            <Metric label="Ready Stages" value={`${fmtNumber(goldMarginSignalActionLoop.ready_stage_count, 0)}/${fmtNumber(goldMarginSignalActionLoop.stage_count, 0)}`} hint="signal to action" />
            <Metric label="Shadow Intent" value={marginSignalAuthority.shadow_margin_intent_allowed ? "allowed" : "held"} hint={String(marginSignalIntent.intent_state || "held for proof").replace(/_/g, " ")} />
            <Metric label="Margin Side" value={String(marginSignalIntent.side || "HOLD")} hint={`${String(marginSignalIntent.target_venue || "Capital.com")} ${String(marginSignalIntent.target_symbol || "GOLD")}`} />
            <Metric label="Live Margin" value={marginSignalAuthority.margin_order_allowed ? "armed" : "blocked"} hint="existing gates only" />
            <Metric label="HNC Feedback" value={String(marginSignalHncFeedback.feedback_action || "waiting").replace(/_/g, " ")} hint={`nodes ${fmtNumber(marginSignalHncFeedback.node_count, 0)}`} />
          </div>
          <div className="mt-4 grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
            <div className="rounded-md border border-border/60 bg-background/50 p-3">
              <div className="mb-2 text-sm font-medium">Signal To Action Pipeline</div>
              <div className="grid gap-2 lg:grid-cols-2">
                {marginSignalPipeline.map((stage: JsonMap) => (
                  <div key={String(stage.id || stage.label)} className="rounded border border-border/40 bg-background/35 p-2 text-xs">
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <div className="truncate font-medium">{String(stage.label || stage.id)}</div>
                        <div className="mt-1 line-clamp-2 text-muted-foreground">{String(stage.proof || "")}</div>
                      </div>
                      <Pill label={stage.ready ? "ready" : "held"} tone={stage.ready ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200" : "border-amber-500/30 bg-amber-500/10 text-amber-200"} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
            <div className="grid gap-3">
              <div className="rounded-md border border-border/60 bg-background/50 p-3">
                <div className="text-sm font-medium">Margin Intent</div>
                <div className="mt-2 grid gap-2 md:grid-cols-2 text-xs">
                  <div className="rounded border border-border/40 bg-background/35 p-2">
                    <div className="text-muted-foreground">entry / target</div>
                    <div className="font-semibold">{fmtNumber(effectiveMarginEntry, 2)} / {fmtNumber(marginSignalIntent.target_level, 2)}</div>
                  </div>
                  <div className="rounded border border-border/40 bg-background/35 p-2">
                    <div className="text-muted-foreground">shadow size</div>
                    <div className="font-semibold">{fmtNumber(marginSignalIntent.suggested_shadow_size, 4)}</div>
                  </div>
                  <div className="rounded border border-border/40 bg-background/35 p-2">
                    <div className="text-muted-foreground">3p floor</div>
                    <div className="font-semibold">{fmtNumber(marginSignalIntent.expected_floor, 2)}</div>
                  </div>
                  <div className="rounded border border-border/40 bg-background/35 p-2">
                    <div className="text-muted-foreground">mutation</div>
                    <div className="font-semibold">{marginSignalIntent.order_mutation_allowed ? "armed" : "blocked"}</div>
                  </div>
                </div>
                <div className="mt-2 line-clamp-2 text-xs text-muted-foreground">{String(marginSignalIntent.hold_reason || marginSignalAuthority.authority_note || "Waiting for proof.")}</div>
              </div>
              <div className="rounded-md border border-border/60 bg-background/50 p-3">
                <div className="text-sm font-medium">HNC/Auris Node Feedback</div>
                <div className="mt-2 text-xs text-muted-foreground">
                  Aureon feeds the current margin intent state, blocker ids, and interval proof back through the cognitive layer before confidence can rise.
                </div>
                <div className="mt-2 grid gap-2">
                  {liveMarginSignalBlockers.slice(0, 4).map((blocker: JsonMap) => (
                    <div key={String(blocker.id || blocker.reason)} className="rounded border border-amber-500/30 bg-amber-500/10 p-2 text-xs text-amber-100">
                      <div className="font-medium">{String(blocker.id || "blocker").replace(/_/g, " ")}</div>
                      <div className="mt-1 line-clamp-2">{String(blocker.reason || "")}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="rounded-md border border-teal-500/30 bg-teal-500/5 p-4">
          <div className="mb-3 flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
            <div className="flex min-w-0 items-center gap-2">
              <ShieldCheck className="h-4 w-4 shrink-0 text-teal-300" />
              <h3 className="truncate text-sm font-semibold">GOLD Process Logic Flow Guard</h3>
            </div>
            <div className="flex flex-wrap gap-2">
              <Pill label={String(goldProcessLogicFlowGuard.status || "flow guard waiting")} tone={goldProcessLogicFlowGuard.flow_correct ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200" : "border-amber-500/30 bg-amber-500/10 text-amber-200"} />
              <Pill label={String(goldProcessLogicFlowGuard.flow_state || "flow held").replace(/_/g, " ")} tone="border-teal-500/30 bg-teal-500/10 text-teal-100" />
              <Pill label={`${fmtNumber(goldProcessLogicFlowGuard.ready_gate_count, 0)}/${fmtNumber(goldProcessLogicFlowGuard.gate_count, 0)} gates`} tone="border-cyan-500/30 bg-cyan-500/10 text-cyan-200" />
            </div>
          </div>
          <p className="mb-3 text-sm text-muted-foreground">
            This guard checks process order. Blocked upstream proof is acceptable only when every downstream action gate stays held; any fake pass or authority leak is surfaced here.
          </p>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-6">
            <Metric label="Flow Correct" value={goldProcessLogicFlowGuard.flow_correct ? "yes" : "attention"} hint={String(goldProcessLogicFlowGuard.flow_state || "flow")} />
            <Metric label="Ready Gates" value={`${fmtNumber(goldProcessLogicFlowGuard.ready_gate_count, 0)}/${fmtNumber(goldProcessLogicFlowGuard.gate_count, 0)}`} hint="ordered chain" />
            <Metric label="Fake Passes" value={fmtNumber(goldProcessLogicFlowGuard.fake_pass_count, 0)} hint="must stay zero" />
            <Metric label="First Blocked" value={String(processFirstBlockedGate.id || "none").replace(/_/g, " ")} hint={String(processFirstBlockedGate.state || "state")} />
            <Metric label="All Gates" value={goldProcessLogicFlowGuard.all_gates_ready ? "ready" : "held"} hint="before shadow intent" />
            <Metric label="Next Check" value={String(goldProcessLogicFlowGuard.next_validation_action || "inspect").replace(/_/g, " ")} hint="validation action" />
          </div>
          <div className="mt-4 grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
            <div className="rounded-md border border-border/60 bg-background/50 p-3">
              <div className="mb-2 text-sm font-medium">Gate Sequence</div>
              <div className="grid gap-2 lg:grid-cols-2">
                {processFlowGates.map((gate: JsonMap) => (
                  <div key={String(gate.id || gate.order)} className="rounded border border-border/40 bg-background/35 p-2 text-xs">
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <div className="truncate font-medium">{fmtNumber(gate.order, 0)}. {String(gate.label || gate.id)}</div>
                        <div className="mt-1 line-clamp-2 text-muted-foreground">{String(gate.proof || "")}</div>
                      </div>
                      <Pill label={gate.ready ? "ready" : "held"} tone={gate.ready ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200" : "border-amber-500/30 bg-amber-500/10 text-amber-200"} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
            <div className="grid gap-3">
              <div className="rounded-md border border-border/60 bg-background/50 p-3">
                <div className="text-sm font-medium">Authority Leak Checks</div>
                <div className="mt-2 grid gap-2">
                  {processAuthorityChecks.slice(0, 6).map((check: JsonMap) => (
                    <div key={String(check.id)} className="rounded border border-border/40 bg-background/35 p-2 text-xs">
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <div className="truncate font-medium">{String(check.id || "authority").replace(/_/g, " ")}</div>
                          <div className="mt-1 line-clamp-2 text-muted-foreground">{String(check.reason || "")}</div>
                        </div>
                        <Pill label={check.allowed ? "leak" : "blocked"} tone={check.allowed ? "border-red-500/30 bg-red-500/10 text-red-200" : "border-emerald-500/30 bg-emerald-500/10 text-emerald-200"} />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
              <div className="rounded-md border border-border/60 bg-background/50 p-3">
                <div className="text-sm font-medium">Flow Violations</div>
                <div className="mt-2 grid gap-2">
                  {processFlowViolations.length ? processFlowViolations.slice(0, 5).map((violation: JsonMap) => (
                    <div key={String(violation.id || violation.reason)} className="rounded border border-red-500/30 bg-red-500/10 p-2 text-xs text-red-100">
                      <div className="font-medium">{String(violation.id || "violation").replace(/_/g, " ")}</div>
                      <div className="mt-1 line-clamp-2">{String(violation.reason || "")}</div>
                    </div>
                  )) : <div className="rounded border border-emerald-500/30 bg-emerald-500/10 p-2 text-xs text-emerald-100">No process-order violation or authority leak reported.</div>}
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="rounded-md border border-blue-500/30 bg-blue-500/5 p-4">
          <div className="mb-3 flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
            <div className="flex min-w-0 items-center gap-2">
              <Radio className="h-4 w-4 shrink-0 text-blue-300" />
              <h3 className="truncate text-sm font-semibold">GOLD Data Sensemaking Router</h3>
            </div>
            <div className="flex flex-wrap gap-2">
              <Pill label={String(goldDataSensemakingRouter.status || "sensemaking waiting")} tone={toneForStatus(String(goldDataSensemakingRouter.status || ""))} />
              <Pill label={String(goldDataSensemakingRouter.sensemaking_state || "reading").replace(/_/g, " ")} tone="border-blue-500/30 bg-blue-500/10 text-blue-100" />
              <Pill label={`${fmtNumber(goldDataSensemakingRouter.routed_source_count, 0)}/${fmtNumber(goldDataSensemakingRouter.source_count, 0)} routed`} tone="border-cyan-500/30 bg-cyan-500/10 text-cyan-200" />
            </div>
          </div>
          <p className="mb-3 text-sm text-muted-foreground">
            This router proves Aureon is reading data, classifying what it means for GOLD, and sending each packet to the gate that needs it.
          </p>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-6">
            <Metric label="Sensemaking Score" value={fmtPercent(goldDataSensemakingRouter.sensemaking_score)} hint="read plus routed" />
            <Metric label="Present Sources" value={`${fmtNumber(goldDataSensemakingRouter.present_source_count, 0)}/${fmtNumber(goldDataSensemakingRouter.source_count, 0)}`} hint="readable" />
            <Metric label="Fresh Sources" value={fmtNumber(goldDataSensemakingRouter.fresh_source_count, 0)} hint="not stale" />
            <Metric label="Routed Sources" value={fmtNumber(goldDataSensemakingRouter.routed_source_count, 0)} hint="has destination" />
            <Metric label="Destinations" value={fmtNumber(goldDataSensemakingRouter.destination_count, 0)} hint="gates fed" />
            <Metric label="Router Blockers" value={fmtNumber(sensemakingBlockers.length, 0)} hint="stale or unmapped" />
          </div>
          <div className="mt-4 grid gap-4 xl:grid-cols-[1fr_1fr]">
            <div className="rounded-md border border-border/60 bg-background/50 p-3">
              <div className="mb-2 text-sm font-medium">Source Routes</div>
              <ScrollArea className="h-56 pr-3">
                <div className="grid gap-2">
                  {sensemakingSourceRoutes.map((route: JsonMap) => (
                    <div key={String(route.id || route.path)} className="rounded border border-border/40 bg-background/35 p-2 text-xs">
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <div className="truncate font-medium">{String(route.id || "source").replace(/_/g, " ")}</div>
                          <div className="mt-1 line-clamp-2 text-muted-foreground">{String(route.meaning || "")}</div>
                          <div className="mt-1 truncate text-muted-foreground">{(Array.isArray(route.destinations) ? route.destinations : []).slice(0, 4).join(" -> ")}</div>
                        </div>
                        <Pill label={route.route_ready ? "routed" : "held"} tone={route.route_ready ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200" : "border-amber-500/30 bg-amber-500/10 text-amber-200"} />
                      </div>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            </div>
            <div className="grid gap-3">
              <div className="rounded-md border border-border/60 bg-background/50 p-3">
                <div className="text-sm font-medium">Meaning Packets</div>
                <div className="mt-2 grid gap-2">
                  {sensemakingMeaningPackets.map((packet: JsonMap) => (
                    <div key={String(packet.id || packet.destination)} className="rounded border border-border/40 bg-background/35 p-2 text-xs">
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <div className="truncate font-medium">{String(packet.id || "packet").replace(/_/g, " ")}</div>
                          <div className="mt-1 line-clamp-2 text-muted-foreground">{String(packet.meaning || "")}</div>
                        </div>
                        <Pill label={packet.ready ? "ready" : "held"} tone={packet.ready ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200" : "border-amber-500/30 bg-amber-500/10 text-amber-200"} />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
              <div className="rounded-md border border-border/60 bg-background/50 p-3">
                <div className="text-sm font-medium">Driver Placement</div>
                <div className="mt-2 grid gap-2">
                  {sensemakingDriverRoutes.slice(0, 5).map((driver: JsonMap) => (
                    <div key={String(driver.id || driver.label)} className="rounded border border-border/40 bg-background/35 p-2 text-xs">
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <div className="truncate font-medium">{String(driver.label || driver.id)}</div>
                          <div className="mt-1 truncate text-muted-foreground">{String(driver.action_use || "")}</div>
                        </div>
                        <Pill label={String(driver.destination || "destination").replace(/_/g, " ")} tone="border-blue-500/30 bg-blue-500/10 text-blue-100" />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
              <div className="rounded-md border border-border/60 bg-background/50 p-3">
                <div className="text-sm font-medium">Sensemaking Blockers</div>
                <div className="mt-2 grid gap-2">
                  {sensemakingBlockers.length ? sensemakingBlockers.slice(0, 4).map((blocker: JsonMap) => (
                    <div key={String(blocker.id || blocker.reason)} className="rounded border border-amber-500/30 bg-amber-500/10 p-2 text-xs text-amber-100">
                      <div className="font-medium">{String(blocker.id || "blocker").replace(/_/g, " ")}</div>
                      <div className="mt-1 line-clamp-2">{String(blocker.reason || "")}</div>
                    </div>
                  )) : <div className="rounded border border-emerald-500/30 bg-emerald-500/10 p-2 text-xs text-emerald-100">All readable data has a GOLD destination route.</div>}
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="rounded-md border border-cyan-500/30 bg-cyan-500/5 p-4">
          <div className="mb-3 flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
            <div className="flex min-w-0 items-center gap-2">
              <ShieldCheck className="h-4 w-4 shrink-0 text-cyan-300" />
              <h3 className="truncate text-sm font-semibold">Verified Real Data Gate</h3>
            </div>
            <div className="flex flex-wrap gap-2">
              <Pill label={String(verifiedRealDataGate.status || "data gate waiting")} tone={summary.verified_real_data_action_allowed ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200" : "border-amber-500/30 bg-amber-500/10 text-amber-200"} />
              <Pill label={`${fmtNumber(summary.verified_real_data_fresh_source_count, 0)}/${fmtNumber(summary.verified_real_data_required_source_count, 0)} fresh sources`} tone="border-cyan-500/30 bg-cyan-500/10 text-cyan-200" />
              <Pill label={`${fmtNumber(verifiedSignalChecks.filter((item: JsonMap) => item.verified_for_action).length, 0)}/${fmtNumber(verifiedSignalChecks.length, 0)} action signals`} tone="border-yellow-500/30 bg-yellow-500/10 text-yellow-100" />
            </div>
          </div>
          <div className="grid gap-3 xl:grid-cols-[0.9fr_1.1fr]">
            <div className="rounded-md border border-border/60 bg-background/50 p-3">
              <div className="text-sm font-medium">Policy</div>
              <div className="mt-1 text-xs text-muted-foreground">{String(verifiedRealDataGate.policy || "Only fresh verified market/runtime evidence can unlock action.")}</div>
              <div className="mt-3 grid gap-2 md:grid-cols-2">
                {verifiedDataBlockers.slice(0, 4).map((blocker: JsonMap) => (
                  <div key={String(blocker.id || blocker.reason)} className="rounded-md border border-amber-500/20 bg-amber-500/5 p-2">
                    <div className="truncate text-xs font-medium text-amber-100">{String(blocker.id || "blocker")}</div>
                    <div className="mt-1 line-clamp-2 text-[11px] text-muted-foreground">{String(blocker.reason || "")}</div>
                  </div>
                ))}
              </div>
            </div>
            <ScrollArea className="h-52 pr-3">
              <div className="grid gap-2 lg:grid-cols-2">
                {verifiedSourceChecks.map((source: JsonMap) => (
                  <div key={String(source.id || source.source_status)} className="rounded-md border border-border/60 bg-background/50 p-3">
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <div className="truncate text-sm font-medium">{String(source.id || "source").replace(/_/g, " ")}</div>
                        <div className="mt-1 text-xs text-muted-foreground">{fmtNumber(source.age_seconds, 0)}s / {fmtNumber(source.max_age_seconds, 0)}s</div>
                      </div>
                      <Pill label={source.fresh ? "fresh" : "blocked"} tone={source.fresh ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200" : "border-amber-500/30 bg-amber-500/10 text-amber-200"} />
                    </div>
                  </div>
                ))}
              </div>
            </ScrollArea>
          </div>
        </section>

        <section className="rounded-md border border-emerald-500/30 bg-emerald-500/5 p-4">
          <div className="mb-3 flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
            <div className="flex min-w-0 items-center gap-2">
              <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-300" />
              <h3 className="truncate text-sm font-semibold">GOLD Fresh Signal Validation</h3>
            </div>
            <div className="flex flex-wrap gap-2">
              <Pill label={String(goldSignalFreshnessMatrix.status || "freshness waiting")} tone={toneForStatus(String(goldSignalFreshnessMatrix.status || ""))} />
              <Pill label={`${fmtNumber(summary.gold_projection_validated_interval_count || goldProjectionIntervalValidation.validated_interval_count, 0)}/${fmtNumber(summary.gold_projection_required_interval_count || goldProjectionIntervalValidation.required_interval_count, 0)} intervals`} tone="border-yellow-500/30 bg-yellow-500/10 text-yellow-100" />
              <Pill label={goldHncActionCoherenceGate.action_coherence_allowed ? "HNC can raise" : "HNC holds"} tone={goldHncActionCoherenceGate.action_coherence_allowed ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200" : "border-amber-500/30 bg-amber-500/10 text-amber-200"} />
            </div>
          </div>
          <p className="mb-3 text-sm text-muted-foreground">
            No GOLD signal, projection, HNC score, margin idea, or portfolio-growth claim may influence action unless the source lanes are fresh and the projection has passed tick, 1m, 5m, 15m, 1h, and session validation.
          </p>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-6">
            <Metric label="Fresh Sources" value={`${fmtNumber(summary.gold_ticker_source_fresh_lane_count || goldTickerSourceMesh.fresh_lane_count, 0)}/${fmtNumber(summary.gold_ticker_source_lane_count || goldTickerSourceMesh.lane_count, 0)}`} hint="ticker mesh" />
            <Metric label="Fresh Rows" value={`${fmtNumber(summary.gold_signal_fresh_row_count || goldSignalFreshnessMatrix.fresh_row_count, 0)}/${fmtNumber(summary.gold_signal_row_count || goldSignalFreshnessMatrix.row_count, 0)}`} hint="signals" />
            <Metric label="Action Rows" value={fmtNumber(summary.gold_signal_action_influence_row_count || goldSignalFreshnessMatrix.action_influence_row_count, 0)} hint="source-linked" />
            <Metric label="Hit Rate" value={goldProjectionIntervalValidation.hit_rate == null ? "held" : fmtPercent(goldProjectionIntervalValidation.hit_rate)} hint="intervals" />
            <Metric label="Shadow P/L" value={fmtNumber(goldPortfolioUpliftGuard.validated_shadow_p_l_effect || summary.gold_portfolio_uplift_shadow_pl, 5)} hint="validated only" />
            <Metric label="Order Intent" value={goldPortfolioUpliftGuard.order_intent_consideration_allowed ? "consider" : "blocked"} hint="3p plus risk" />
          </div>
          <div className="mt-4 grid gap-4 xl:grid-cols-[1fr_1fr]">
            <div className="grid gap-3">
              <div className="rounded-md border border-border/60 bg-background/50 p-3">
                <div className="text-sm font-medium">Ticker Source Mesh</div>
                <ScrollArea className="mt-2 h-52 pr-3">
                  <div className="grid gap-2">
                    {goldTickerSourceLanes.map((lane: JsonMap) => (
                      <div key={String(lane.id || lane.label)} className="rounded border border-border/40 bg-background/35 p-2 text-xs">
                        <div className="flex items-start justify-between gap-2">
                          <div className="min-w-0">
                            <div className="truncate font-medium">{String(lane.label || lane.id)}</div>
                            <div className="mt-1 line-clamp-2 text-muted-foreground">{(Array.isArray(lane.symbols) ? lane.symbols : []).join(", ")} | {String(lane.venue || "")}</div>
                          </div>
                          <Pill label={lane.fresh ? "fresh" : "held"} tone={lane.fresh ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200" : "border-amber-500/30 bg-amber-500/10 text-amber-200"} />
                        </div>
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              </div>
              <div className="rounded-md border border-border/60 bg-background/50 p-3">
                <div className="text-sm font-medium">HNC/Auris Action Gate</div>
                <div className="mt-2 grid gap-2 md:grid-cols-2 text-xs">
                  <div className="rounded border border-border/40 bg-background/35 p-2">
                    <div className="text-muted-foreground">coherence</div>
                    <div className="font-semibold">{fmtPercent(goldHncActionCoherenceGate.auris_coherence)}</div>
                  </div>
                  <div className="rounded border border-border/40 bg-background/35 p-2">
                    <div className="text-muted-foreground">effect</div>
                    <div className="font-semibold">{String(goldHncActionCoherenceGate.confidence_effect || "hold")}</div>
                  </div>
                </div>
                <div className="mt-2 line-clamp-2 text-xs text-muted-foreground">{String(goldHncActionCoherenceGate.weapon_policy || "HNC/Auris cannot promote stale evidence.")}</div>
              </div>
            </div>
            <div className="grid gap-3">
              <div className="rounded-md border border-border/60 bg-background/50 p-3">
                <div className="text-sm font-medium">Projection Intervals</div>
                <div className="mt-2 grid gap-2 md:grid-cols-2">
                  {goldProjectionIntervals.map((interval: JsonMap) => (
                    <div key={String(interval.id || interval.label)} className="rounded border border-border/40 bg-background/35 p-2 text-xs">
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <div className="truncate font-medium">{String(interval.label || interval.id)}</div>
                          <div className="mt-1 truncate text-muted-foreground">{String(interval.forecast_direction || "waiting")} | {String(interval.hit_miss || "unvalidated")}</div>
                        </div>
                        <Pill label={interval.validated ? "validated" : "missing"} tone={interval.validated ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200" : "border-amber-500/30 bg-amber-500/10 text-amber-200"} />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
              <div className="rounded-md border border-border/60 bg-background/50 p-3">
                <div className="text-sm font-medium">Fresh-Proof Blockers</div>
                <div className="mt-2 grid gap-2">
                  {([...goldSignalFreshnessBlockers, ...goldProjectionBlockers, ...goldPortfolioUpliftBlockers] as JsonMap[]).slice(0, 6).map((blocker: JsonMap) => (
                    <div key={String(blocker.id || blocker.reason)} className="rounded border border-amber-500/30 bg-amber-500/10 p-2 text-xs text-amber-100">
                      <div className="font-medium">{String(blocker.id || "fresh proof blocker").replace(/_/g, " ")}</div>
                      <div className="mt-1 line-clamp-2">{String(blocker.reason || "")}</div>
                    </div>
                  ))}
                  {!goldSignalFreshnessBlockers.length && !goldProjectionBlockers.length && !goldPortfolioUpliftBlockers.length ? (
                    <div className="rounded border border-emerald-500/30 bg-emerald-500/10 p-2 text-xs text-emerald-100">Fresh signal, interval validation, and portfolio-uplift proof are passing.</div>
                  ) : null}
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="rounded-md border border-sky-500/30 bg-sky-500/5 p-4">
          <div className="mb-3 flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
            <div className="flex min-w-0 items-center gap-2">
              <LineChart className="h-4 w-4 shrink-0 text-sky-300" />
              <h3 className="truncate text-sm font-semibold">GOLD Evolving Projection Path</h3>
            </div>
            <div className="flex flex-wrap gap-2">
              <Pill label={String(goldEvolvingProjectionPath.status || "projection path waiting")} tone={toneForStatus(String(goldEvolvingProjectionPath.status || ""))} />
              <Pill label={`${fmtNumber(goldEvolvingProjectionPath.fresh_horizon_count, 0)}/${fmtNumber(goldEvolvingProjectionPath.horizon_count, 0)} fresh`} tone="border-cyan-500/30 bg-cyan-500/10 text-cyan-200" />
              <Pill label={goldEvolvingProjectionPath.live_evolving_ready ? "live validating" : "held"} tone={goldEvolvingProjectionPath.live_evolving_ready ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200" : "border-amber-500/30 bg-amber-500/10 text-amber-200"} />
            </div>
          </div>
          <p className="mb-3 text-sm text-muted-foreground">
            Rolling GOLD projections from seconds to months. Every horizon carries fresh-input proof, validation deadline, hit/miss state, confidence delta, and the next roll-forward action.
          </p>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-6">
            <Metric label="Horizons" value={fmtNumber(goldEvolvingProjectionPath.horizon_count, 0)} hint="seconds to months" />
            <Metric label="Fresh Horizons" value={fmtNumber(goldEvolvingProjectionPath.fresh_horizon_count, 0)} hint="input fresh" />
            <Metric label="Validated" value={fmtNumber(goldEvolvingProjectionPath.validated_horizon_count, 0)} hint="outcome checked" />
            <Metric label="Hit Rate" value={goldEvolvingProjectionPath.hit_rate == null ? "held" : fmtPercent(goldEvolvingProjectionPath.hit_rate)} hint="validated horizons" />
            <Metric label="Next Roll" value={String(goldEvolvingProjectionPath.next_roll_forward_action || "refresh").replace(/_/g, " ")} hint="live path" />
            <Metric label="Path Blockers" value={fmtNumber(evolvingProjectionBlockers.length, 0)} hint="missing/stale/miss" />
          </div>
          <div className="mt-4 grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
            <div className="rounded-md border border-border/60 bg-background/50 p-3">
              <div className="mb-2 text-sm font-medium">Second-To-Month Horizon Ladder</div>
              <ScrollArea className="h-60 pr-3">
                <div className="grid gap-2 lg:grid-cols-2">
                  {evolvingProjectionHorizons.map((horizon: JsonMap) => (
                    <div key={String(horizon.id || horizon.label)} className="rounded border border-border/40 bg-background/35 p-2 text-xs">
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <div className="truncate font-medium">{String(horizon.label || horizon.id)}</div>
                          <div className="mt-1 truncate text-muted-foreground">{String(horizon.validation_state || "waiting").replace(/_/g, " ")} | {String(horizon.hit_miss || "unvalidated")}</div>
                          <div className="mt-1 line-clamp-2 text-muted-foreground">{String(horizon.next_action || "")}</div>
                        </div>
                        <Pill label={horizon.input_fresh ? "fresh" : "stale"} tone={horizon.input_fresh ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200" : "border-amber-500/30 bg-amber-500/10 text-amber-200"} />
                      </div>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            </div>
            <div className="rounded-md border border-border/60 bg-background/50 p-3">
              <div className="text-sm font-medium">Projection Path Blockers</div>
              <div className="mt-2 grid gap-2">
                {evolvingProjectionBlockers.length ? evolvingProjectionBlockers.slice(0, 8).map((blocker: JsonMap) => (
                  <div key={String(blocker.id || blocker.reason)} className="rounded border border-amber-500/30 bg-amber-500/10 p-2 text-xs text-amber-100">
                    <div className="font-medium">{String(blocker.id || "blocker").replace(/_/g, " ")}</div>
                    <div className="mt-1 line-clamp-2">{String(blocker.reason || "")}</div>
                  </div>
                )) : <div className="rounded border border-emerald-500/30 bg-emerald-500/10 p-2 text-xs text-emerald-100">All projection horizons are rolling forward cleanly.</div>}
              </div>
            </div>
          </div>
        </section>

        <section className="rounded-md border border-cyan-500/30 bg-cyan-500/5 p-4">
          <div className="mb-3 flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
            <div className="flex min-w-0 items-center gap-2">
              <Activity className="h-4 w-4 shrink-0 text-cyan-300" />
              <h3 className="truncate text-sm font-semibold">GOLD Dynamic Market Edge Stream</h3>
            </div>
            <div className="flex flex-wrap gap-2">
              <Pill label={String(goldDynamicMarketEdgeStream.status || "edge stream waiting")} tone={toneForStatus(String(goldDynamicMarketEdgeStream.status || ""))} />
              <Pill label={`${fmtNumber(goldDynamicMarketEdgeStream.fresh_stream_count, 0)}/${fmtNumber(goldDynamicMarketEdgeStream.stream_lane_count, 0)} streams`} tone="border-cyan-500/30 bg-cyan-500/10 text-cyan-200" />
              <Pill label={dynamicEdgeCandidate.shadow_intent_allowed ? "shadow edge ready" : "watching"} tone={dynamicEdgeCandidate.shadow_intent_allowed ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200" : "border-amber-500/30 bg-amber-500/10 text-amber-200"} />
            </div>
          </div>
          <p className="mb-3 text-sm text-muted-foreground">
            Live GOLD edge watch: Capital GOLD is the target stream, related markets are confirmation lanes, and waveform movement can only become shadow intent after fresh proof, interval validation, HNC/Auris, and 3p portfolio gates pass.
          </p>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-6">
            <Metric label="Edge Score" value={fmtPercent(goldDynamicMarketEdgeStream.edge_score)} hint={String(goldDynamicMarketEdgeStream.edge_state || "watching").replace(/_/g, " ")} />
            <Metric label="Target Fresh" value={liveGoldSource.ready || goldDynamicMarketEdgeStream.target_stream_fresh ? "yes" : "no"} hint={liveGoldSource.ready ? "terminal-state GOLD" : "Capital GOLD"} />
            <Metric label="Context Fresh" value={fmtNumber(goldDynamicMarketEdgeStream.context_fresh_count, 0)} hint="related lanes" />
            <Metric label="Waveform" value={String(goldDynamicMarketEdgeStream.waveform_state || "waiting").replace(/_/g, " ")} hint="move timing" />
            <Metric label="Candidate Side" value={liveCandidateSide} hint={`${String(dynamicEdgeCandidate.state || "held").replace(/_/g, " ")} / ${fmtPercent(liveCandidateConfidence)}`} />
            <Metric label="Next Edge Step" value={effectiveNextEdgeStep} hint="shadow only" />
          </div>
          <div className="mt-4 grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
            <div className="rounded-md border border-border/60 bg-background/50 p-3">
              <div className="mb-2 text-sm font-medium">Streaming Edge Lanes</div>
              <ScrollArea className="h-60 pr-3">
                <div className="grid gap-2 lg:grid-cols-2">
                  {liveDynamicEdgeRows.map((row: JsonMap) => (
                    <div key={String(row.id || row.label)} className="rounded border border-border/40 bg-background/35 p-2 text-xs">
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <div className="truncate font-medium">{String(row.label || row.id)}</div>
                          <div className="mt-1 line-clamp-2 text-muted-foreground">{(Array.isArray(row.symbols) ? row.symbols : []).join(", ")} | {String(row.edge_use || "")}</div>
                          <div className="mt-1 text-muted-foreground">score {fmtPercent(row.edge_score)} | age {fmtNumber(row.age_seconds, 0)}s</div>
                        </div>
                        <Pill label={row.fresh ? "fresh" : "refresh"} tone={row.fresh ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200" : "border-amber-500/30 bg-amber-500/10 text-amber-200"} />
                      </div>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            </div>
            <div className="grid gap-3">
              <div className="rounded-md border border-border/60 bg-background/50 p-3">
                <div className="text-sm font-medium">Edge Trigger Map</div>
                <div className="mt-2 grid gap-2 text-xs">
                  <div className="rounded border border-border/40 bg-background/35 p-2">
                    <div className="text-muted-foreground">side</div>
                    <div className="font-semibold">{String(liveRuntimeProof.candidate_side || dynamicEdgeTriggerMap.side || dynamicEdgeCandidate.side || "HOLD")}</div>
                  </div>
                  <div className="rounded border border-border/40 bg-background/35 p-2">
                    <div className="text-muted-foreground">fresh / validated horizons</div>
                    <div className="font-semibold">{fmtNumber(dynamicEdgeTriggerMap.fresh_horizons, 0)} / {fmtNumber(dynamicEdgeTriggerMap.validated_horizons, 0)}</div>
                  </div>
                  <div className="rounded border border-border/40 bg-background/35 p-2">
                    <div className="text-muted-foreground">Auris coherence</div>
                    <div className="font-semibold">{fmtPercent(dynamicEdgeTriggerMap.auris_coherence)}</div>
                  </div>
                  <div className="rounded border border-border/40 bg-background/35 p-2">
                    <div className="text-muted-foreground">margin authority</div>
                    <div className="font-semibold">{dynamicEdgeCandidate.margin_order_allowed ? "armed" : "blocked"}</div>
                  </div>
                </div>
              </div>
              <div className="rounded-md border border-border/60 bg-background/50 p-3">
                <div className="text-sm font-medium">Edge Blockers</div>
                <div className="mt-2 grid gap-2">
                  {liveDynamicEdgeBlockers.length ? liveDynamicEdgeBlockers.slice(0, 8).map((blocker: JsonMap) => (
                    <div key={String(blocker.id || blocker.reason)} className="rounded border border-amber-500/30 bg-amber-500/10 p-2 text-xs text-amber-100">
                      <div className="font-medium">{String(blocker.id || "blocker").replace(/_/g, " ")}</div>
                      <div className="mt-1 line-clamp-2">{String(blocker.reason || "")}</div>
                    </div>
                  )) : <div className="rounded border border-emerald-500/30 bg-emerald-500/10 p-2 text-xs text-emerald-100">Dynamic edge stream is clean for shadow validation.</div>}
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="rounded-md border border-violet-500/30 bg-violet-500/5 p-4">
          <div className="mb-3 flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
            <div className="flex min-w-0 items-center gap-2">
              <LineChart className="h-4 w-4 shrink-0 text-violet-300" />
              <h3 className="truncate text-sm font-semibold">GOLD HNC History Future Bridge</h3>
            </div>
            <div className="flex flex-wrap gap-2">
              <Pill label={String(goldHncHistoryFutureBridge.status || "history future waiting")} tone={toneForStatus(String(goldHncHistoryFutureBridge.status || ""))} />
              <Pill label={String(goldHncHistoryFutureBridge.future_claim_state || "history context").replace(/_/g, " ")} tone={goldHncHistoryFutureBridge.bridge_ready ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200" : "border-amber-500/30 bg-amber-500/10 text-amber-200"} />
              <Pill label="HNC/Auris" tone="border-violet-500/30 bg-violet-500/10 text-violet-100" />
            </div>
          </div>
          <p className="mb-3 text-sm text-muted-foreground">
            Historical GOLD replay becomes a future hypothesis only through HNC/Auris. Validated rows, replay lanes, waveform memory, dynamic edge proof, and Auris coherence must agree before history can raise confidence.
          </p>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-6">
            <Metric label="Memory Score" value={fmtPercent(goldHncHistoryFutureBridge.historical_memory_score)} hint="history signal" />
            <Metric label="Validated History" value={fmtNumber(goldHncHistoryFutureBridge.validated_history_count, 0)} hint={`hit ${goldHncHistoryFutureBridge.historical_hit_rate == null ? "held" : fmtPercent(goldHncHistoryFutureBridge.historical_hit_rate)}`} />
            <Metric label="Replay Lanes" value={`${fmtNumber(goldHncHistoryFutureBridge.ready_replay_lane_count, 0)}/${fmtNumber(goldHncHistoryFutureBridge.replay_lane_count, 0)}`} hint="historical map" />
            <Metric label="Future Windows" value={fmtNumber(historyFutureWindows.length, 0)} hint="seconds to months" />
            <Metric label="Auris" value={fmtPercent(goldHncHistoryFutureBridge.auris_coherence)} hint={String(goldHncHistoryFutureBridge.hnc_confidence_effect || "hold")} />
            <Metric label="Bridge" value={goldHncHistoryFutureBridge.bridge_ready ? "ready" : "held"} hint={String(historyFuturePacket.act || "hold").replace(/_/g, " ")} />
          </div>
          <div className="mt-4 grid gap-4 xl:grid-cols-[1fr_1fr]">
            <div className="rounded-md border border-border/60 bg-background/50 p-3">
              <div className="mb-2 text-sm font-medium">Historical Analogs</div>
              <ScrollArea className="h-56 pr-3">
                <div className="grid gap-2">
                  {historyFutureAnalogs.map((analog: JsonMap) => (
                    <div key={String(analog.id || analog.label)} className="rounded border border-border/40 bg-background/35 p-2 text-xs">
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <div className="truncate font-medium">{String(analog.label || analog.id)}</div>
                          <div className="mt-1 line-clamp-2 text-muted-foreground">{String(analog.future_use || "")}</div>
                          <div className="mt-1 line-clamp-2 text-muted-foreground">{String(analog.next_action || "")}</div>
                        </div>
                        <Pill label={String(analog.state || "waiting").replace(/_/g, " ")} tone={String(analog.state || "").includes("ready") ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200" : "border-amber-500/30 bg-amber-500/10 text-amber-200"} />
                      </div>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            </div>
            <div className="grid gap-3">
              <div className="rounded-md border border-border/60 bg-background/50 p-3">
                <div className="text-sm font-medium">Future Windows</div>
                <div className="mt-2 grid gap-2 md:grid-cols-2">
                  {historyFutureWindows.slice(0, 8).map((window: JsonMap) => (
                    <div key={String(window.id || window.label)} className="rounded border border-border/40 bg-background/35 p-2 text-xs">
                      <div className="truncate font-medium">{String(window.label || window.id)}</div>
                      <div className="mt-1 truncate text-muted-foreground">{String(window.validation_state || "waiting").replace(/_/g, " ")}</div>
                      <Pill label={window.ready ? "ready" : "held"} tone={window.ready ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200" : "border-amber-500/30 bg-amber-500/10 text-amber-200"} />
                    </div>
                  ))}
                </div>
              </div>
              <div className="rounded-md border border-border/60 bg-background/50 p-3">
                <div className="text-sm font-medium">History Future Blockers</div>
                <div className="mt-2 grid gap-2">
                  {historyFutureBlockers.length ? historyFutureBlockers.slice(0, 8).map((blocker: JsonMap) => (
                    <div key={String(blocker.id || blocker.reason)} className="rounded border border-amber-500/30 bg-amber-500/10 p-2 text-xs text-amber-100">
                      <div className="font-medium">{String(blocker.id || "blocker").replace(/_/g, " ")}</div>
                      <div className="mt-1 line-clamp-2">{String(blocker.reason || "")}</div>
                    </div>
                  )) : <div className="rounded border border-emerald-500/30 bg-emerald-500/10 p-2 text-xs text-emerald-100">History-to-future bridge is passing for shadow evidence.</div>}
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="rounded-md border border-fuchsia-500/30 bg-fuchsia-500/5 p-4">
          <div className="mb-3 flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
            <div className="flex min-w-0 items-center gap-2">
              <Activity className="h-4 w-4 shrink-0 text-fuchsia-300" />
              <h3 className="truncate text-sm font-semibold">GOLD Creative Dream Hypothesis Engine</h3>
            </div>
            <div className="flex flex-wrap gap-2">
              <Pill label={String(goldCreativeDreamEngine.status || "dream engine waiting")} tone={toneForStatus(String(goldCreativeDreamEngine.status || ""))} />
              <Pill label={`${fmtNumber(goldCreativeDreamEngine.ready_dream_count, 0)}/${fmtNumber(goldCreativeDreamEngine.dream_count, 0)} dreams`} tone="border-fuchsia-500/30 bg-fuchsia-500/10 text-fuchsia-100" />
              <Pill label={goldCreativeDreamEngine.action_influence_allowed ? "action influence" : "idea only"} tone={goldCreativeDreamEngine.action_influence_allowed ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200" : "border-amber-500/30 bg-amber-500/10 text-amber-200"} />
            </div>
          </div>
          <p className="mb-3 text-sm text-muted-foreground">
            More ideas means more search paths, but every dream stays non-mutating until fresh sources, interval validation, HNC/Auris coherence, and the 3p floor can prove it.
          </p>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-6">
            <Metric label="Dream Count" value={fmtNumber(goldCreativeDreamEngine.dream_count, 0)} hint="creative breadth" />
            <Metric label="Ready Dreams" value={fmtNumber(goldCreativeDreamEngine.ready_dream_count, 0)} hint="shadow validation" />
            <Metric label="Creativity" value={fmtPercent(goldCreativeDreamEngine.average_creativity_score)} hint="idea spread" />
            <Metric label="Evidence" value={fmtPercent(goldCreativeDreamEngine.average_evidence_score)} hint="proof grounding" />
            <Metric label="Research Packets" value={fmtNumber(goldCreativeDreamEngine.research_packet_count, 0)} hint="local source packets" />
            <Metric label="Action Influence" value={goldCreativeDreamEngine.action_influence_allowed ? "allowed" : "blocked"} hint="idea only" />
          </div>
          <div className="mt-4 grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
            <div className="rounded-md border border-border/60 bg-background/50 p-3">
              <div className="mb-2 text-sm font-medium">Dream Bank</div>
              <ScrollArea className="h-64 pr-3">
                <div className="grid gap-2">
                  {creativeDreams.map((dream: JsonMap) => (
                    <div key={String(dream.id || dream.title)} className="rounded border border-border/40 bg-background/35 p-2 text-xs">
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <div className="truncate font-medium">{String(dream.title || dream.id)}</div>
                          <div className="mt-1 line-clamp-2 text-muted-foreground">{String(dream.premise || "")}</div>
                          <div className="mt-1 flex flex-wrap gap-1">
                            <Pill label={String(dream.imagination_lane || "dream").replace(/_/g, " ")} tone="border-fuchsia-500/30 bg-fuchsia-500/10 text-fuchsia-100" />
                            <Pill label={`c ${fmtPercent(dream.creativity_score)}`} tone="border-border/60 bg-background/70 text-muted-foreground" />
                            <Pill label={`e ${fmtPercent(dream.evidence_score)}`} tone="border-border/60 bg-background/70 text-muted-foreground" />
                          </div>
                        </div>
                        <Pill label={String(dream.state || "waiting").replace(/_/g, " ")} tone={String(dream.state || "").includes("ready") ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200" : "border-amber-500/30 bg-amber-500/10 text-amber-200"} />
                      </div>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            </div>
            <div className="grid gap-3">
              <div className="rounded-md border border-border/60 bg-background/50 p-3">
                <div className="text-sm font-medium">Validation Queue</div>
                <div className="mt-2 grid gap-2">
                  {creativeDreamQueue.slice(0, 6).map((item: JsonMap) => (
                    <div key={String(item.dream_id || item.priority)} className="rounded border border-border/40 bg-background/35 p-2 text-xs">
                      <div className="flex items-center justify-between gap-2">
                        <div className="truncate font-medium">{String(item.dream_id || "dream").replace(/_/g, " ")}</div>
                        <Pill label={String(item.priority || "medium")} tone={String(item.priority || "").includes("high") ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200" : "border-amber-500/30 bg-amber-500/10 text-amber-200"} />
                      </div>
                      <div className="mt-1 line-clamp-2 text-muted-foreground">{String(item.next_validation_action || "")}</div>
                    </div>
                  ))}
                </div>
              </div>
              <div className="rounded-md border border-border/60 bg-background/50 p-3">
                <div className="text-sm font-medium">Dream Blockers</div>
                <div className="mt-2 grid gap-2">
                  {creativeDreamBlockers.length ? creativeDreamBlockers.slice(0, 6).map((blocker: JsonMap) => (
                    <div key={String(blocker.id || blocker.reason)} className="rounded border border-amber-500/30 bg-amber-500/10 p-2 text-xs text-amber-100">
                      <div className="font-medium">{String(blocker.id || "blocker").replace(/_/g, " ")}</div>
                      <div className="mt-1 line-clamp-2">{String(blocker.reason || "")}</div>
                    </div>
                  )) : <div className="rounded border border-emerald-500/30 bg-emerald-500/10 p-2 text-xs text-emerald-100">Dream breadth is ready for shadow validation queueing.</div>}
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="rounded-md border border-indigo-500/30 bg-indigo-500/5 p-4">
          <div className="mb-3 flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
            <div className="flex min-w-0 items-center gap-2">
              <LineChart className="h-4 w-4 shrink-0 text-indigo-300" />
              <h3 className="truncate text-sm font-semibold">GOLD Probability Projection Forecast</h3>
            </div>
            <div className="flex flex-wrap gap-2">
              <Pill label={String(goldProbabilityProjectionForecast.status || "probability forecast waiting")} tone={toneForStatus(String(goldProbabilityProjectionForecast.status || ""))} />
              <Pill label={String(probabilityTruthDiscipline.truth_status || "hypothesis").replace(/_/g, " ")} tone={probabilityTruthDiscipline.truth_claim_allowed ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200" : "border-amber-500/30 bg-amber-500/10 text-amber-200"} />
              <Pill label={String(probabilityForecastDistribution.calibrated_direction || "HOLD")} tone="border-indigo-500/30 bg-indigo-500/10 text-indigo-100" />
            </div>
          </div>
          <p className="mb-3 text-sm text-muted-foreground">
            Forecasts stay probabilistic: Aureon shows BUY/SELL/HOLD distribution, validated claims, contradictions, and truth discipline before any forecast can influence a margin action.
          </p>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-6">
            <Metric label="Calibrated Direction" value={String(probabilityForecastDistribution.calibrated_direction || "HOLD")} hint={`confidence ${fmtPercent(probabilityForecastDistribution.calibrated_confidence)}`} />
            <Metric label="BUY Probability" value={fmtPercent(probabilityForecastDistribution.buy_probability)} hint="weighted claims" />
            <Metric label="SELL Probability" value={fmtPercent(probabilityForecastDistribution.sell_probability)} hint="weighted claims" />
            <Metric label="HOLD Probability" value={fmtPercent(probabilityForecastDistribution.hold_probability)} hint="uncertainty lane" />
            <Metric label="Validated Claims" value={fmtNumber(probabilityValidatedForecast.validated_claim_count, 0)} hint={`hit rate ${probabilityValidatedForecast.hit_rate == null ? "held" : fmtPercent(probabilityValidatedForecast.hit_rate)}`} />
            <Metric label="Truth Claim" value={probabilityTruthDiscipline.truth_claim_allowed ? "allowed" : "blocked"} hint="no fake certainty" />
          </div>
          <div className="mt-4 grid gap-4 xl:grid-cols-[0.95fr_1.05fr]">
            <div className="grid gap-3">
              <div className="rounded-md border border-border/60 bg-background/50 p-3">
                <div className="text-sm font-medium">Truth Discipline</div>
                <div className="mt-2 text-xs text-muted-foreground">{String(probabilityTruthDiscipline.operator_language || "Use probability, proof, blockers, and next validation action.")}</div>
                <div className="mt-3 grid gap-2 md:grid-cols-2 text-xs">
                  <div className="rounded border border-border/40 bg-background/35 p-2">
                    <div className="text-muted-foreground">quality score</div>
                    <div className="font-semibold">{fmtPercent(probabilityForecastDistribution.organism_quality_score)}</div>
                  </div>
                  <div className="rounded border border-border/40 bg-background/35 p-2">
                    <div className="text-muted-foreground">action influence</div>
                    <div className="font-semibold">{probabilityValidatedForecast.action_influence_allowed ? "allowed" : "blocked"}</div>
                  </div>
                  <div className="rounded border border-border/40 bg-background/35 p-2">
                    <div className="text-muted-foreground">fresh lanes</div>
                    <div className="font-semibold">{fmtNumber(probabilityOrganismInputs.fresh_ticker_lanes, 0)} / {fmtNumber(probabilityOrganismInputs.ticker_lanes, 0)}</div>
                  </div>
                  <div className="rounded border border-border/40 bg-background/35 p-2">
                    <div className="text-muted-foreground">active agents</div>
                    <div className="font-semibold">{fmtNumber(probabilityOrganismInputs.active_swarm_agents, 0)}</div>
                  </div>
                </div>
              </div>
              <div className="rounded-md border border-border/60 bg-background/50 p-3">
                <div className="text-sm font-medium">Forecast Blockers</div>
                <div className="mt-2 grid gap-2">
                  {probabilityForecastBlockers.length ? probabilityForecastBlockers.slice(0, 5).map((blocker: JsonMap) => (
                    <div key={String(blocker.id || blocker.reason)} className="rounded border border-amber-500/30 bg-amber-500/10 p-2 text-xs text-amber-100">
                      <div className="font-medium">{String(blocker.id || "blocker").replace(/_/g, " ")}</div>
                      <div className="mt-1 line-clamp-2">{String(blocker.reason || "")}</div>
                    </div>
                  )) : <div className="rounded border border-emerald-500/30 bg-emerald-500/10 p-2 text-xs text-emerald-100">Probability forecast gates are passing.</div>}
                </div>
              </div>
            </div>
            <div className="grid gap-3">
              <div className="rounded-md border border-border/60 bg-background/50 p-3">
                <div className="text-sm font-medium">Probability Forecast Claims</div>
                <ScrollArea className="mt-2 h-48 pr-3">
                  <div className="grid gap-2">
                    {probabilityForecastClaims.map((claim: JsonMap) => (
                      <div key={String(claim.id || claim.interval)} className="rounded border border-border/40 bg-background/35 p-2 text-xs">
                        <div className="flex items-start justify-between gap-2">
                          <div className="min-w-0">
                            <div className="truncate font-medium">{String(claim.interval || "interval")} {String(claim.side || "HOLD")}</div>
                            <div className="mt-1 truncate text-muted-foreground">prob {fmtPercent(claim.probability)} | confidence {fmtPercent(claim.confidence)}</div>
                          </div>
                          <Pill label={String(claim.truth_status || "hypothesis").replace(/_/g, " ")} tone={String(claim.truth_status || "").includes("hit") ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200" : String(claim.truth_status || "").includes("miss") ? "border-amber-500/30 bg-amber-500/10 text-amber-200" : "border-slate-500/30 bg-slate-500/10 text-slate-200"} />
                        </div>
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              </div>
              <div className="rounded-md border border-border/60 bg-background/50 p-3">
                <div className="text-sm font-medium">Contradiction Checks</div>
                <div className="mt-2 grid gap-2">
                  {probabilityContradictions.length ? probabilityContradictions.slice(0, 5).map((item: JsonMap) => (
                    <div key={String(item.id || item.reason)} className="rounded border border-amber-500/30 bg-amber-500/10 p-2 text-xs text-amber-100">
                      <div className="font-medium">{String(item.id || "contradiction").replace(/_/g, " ")}</div>
                      <div className="mt-1 line-clamp-2">{String(item.reason || "")}</div>
                    </div>
                  )) : <div className="rounded border border-emerald-500/30 bg-emerald-500/10 p-2 text-xs text-emerald-100">No forecast contradictions published.</div>}
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="rounded-md border border-purple-500/30 bg-purple-500/5 p-4">
          <div className="mb-3 flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
            <div className="flex min-w-0 items-center gap-2">
              <ShieldCheck className="h-4 w-4 shrink-0 text-purple-300" />
              <h3 className="truncate text-sm font-semibold">HNC/Auris Quantum Probability Route</h3>
            </div>
            <div className="flex flex-wrap gap-2">
              <Pill label={String(cognitiveRoute.status || "cognitive route waiting")} tone={cognitiveRoute.route_passed ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200" : "border-amber-500/30 bg-amber-500/10 text-amber-200"} />
              <Pill label={cognitiveRoute.route_passed ? "route passed" : "route blocking"} tone={cognitiveRoute.route_passed ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200" : "border-amber-500/30 bg-amber-500/10 text-amber-200"} />
              <Pill label="non-mutating" tone="border-blue-500/30 bg-blue-500/10 text-blue-200" />
            </div>
          </div>
          <p className="mb-3 text-sm text-muted-foreground">
            GOLD shadow logic must pass through Auris nodes, lambda history, HNC proof, quantum route context, and probability evidence before any candidate can be promoted.
          </p>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-6">
            <Metric label="Auris Nodes" value={`${fmtNumber(cognitiveAurisNodes.node_count, 0)}/9`} hint={`coherence ${fmtPercent(cognitiveAurisNodes.coherence)}`} />
            <Metric label="Lambda" value={cognitiveLambda.fresh ? "fresh" : "held"} hint={`latest ${fmtNumber(cognitiveLambda.latest_lambda, 3)}`} />
            <Metric label="HNC" value={cognitiveHnc.passed ? "passing" : "held"} hint={`score ${fmtNumber(cognitiveHnc.master_formula_score, 3)}`} />
            <Metric label="Quantum" value={`${fmtNumber(cognitiveQuantum.present_surface_count, 0)}/${fmtNumber(cognitiveQuantum.surface_count, 0)}`} hint={String(cognitiveQuantum.packet_policy || "metadata")} />
            <Metric label="Probability" value={`${fmtNumber(cognitiveProbability.present_surface_count, 0)}/${fmtNumber(cognitiveProbability.surface_count, 0)}`} hint={`${fmtNumber(cognitiveProbability.gold_row_count, 0)} GOLD rows`} />
            <Metric label="Blockers" value={fmtNumber(cognitiveRouteBlockers.length, 0)} hint="route gate" />
          </div>
          <div className="mt-4 grid gap-4 xl:grid-cols-[0.95fr_1.05fr]">
            <div className="rounded-md border border-border/60 bg-background/50 p-3">
              <div className="text-sm font-medium">Route Blockers</div>
              <div className="mt-2 grid gap-2 md:grid-cols-2">
                {cognitiveRouteBlockers.length ? (
                  cognitiveRouteBlockers.slice(0, 6).map((blocker: JsonMap) => (
                    <div key={String(blocker.id || blocker.reason)} className="rounded border border-amber-500/20 bg-amber-500/5 p-2 text-xs">
                      <div className="truncate font-medium text-amber-100">{String(blocker.id || "blocker").replace(/_/g, " ")}</div>
                      <div className="mt-1 line-clamp-2 text-muted-foreground">{String(blocker.reason || "")}</div>
                    </div>
                  ))
                ) : (
                  <div className="rounded border border-emerald-500/20 bg-emerald-500/5 p-2 text-xs text-emerald-200">Auris, lambda, HNC, quantum, and probability route is passing.</div>
                )}
              </div>
            </div>
            <ScrollArea className="h-52 pr-3">
              <div className="grid gap-2 lg:grid-cols-2">
                {cognitiveRouteSurfaces.map((surface: JsonMap) => (
                  <div key={String(surface.id || surface.path)} className="rounded-md border border-border/60 bg-background/50 p-3">
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <div className="truncate text-sm font-medium">{String(surface.id || "route surface").replace(/_/g, " ")}</div>
                        <div className="mt-1 truncate text-xs text-muted-foreground">{String(surface.family || "family")} | {String(surface.route_use || "route")}</div>
                      </div>
                      <Pill label={surface.present ? "present" : "missing"} tone={surface.present ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200" : "border-red-500/30 bg-red-500/10 text-red-200"} />
                    </div>
                    <div className="mt-2 line-clamp-2 text-xs text-muted-foreground">{String(surface.role || "")}</div>
                  </div>
                ))}
              </div>
            </ScrollArea>
          </div>
        </section>

        <section className="rounded-md border border-sky-500/30 bg-sky-500/5 p-4">
          <div className="mb-3 flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
            <div className="flex min-w-0 items-center gap-2">
              <Gauge className="h-4 w-4 shrink-0 text-sky-300" />
              <h3 className="truncate text-sm font-semibold">HFT Speed And Validated Predictions Gate</h3>
            </div>
            <div className="flex flex-wrap gap-2">
              <Pill label={String(hftSpeedGate.status || "speed gate waiting")} tone={hftSpeedGate.gate_passed ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200" : "border-amber-500/30 bg-amber-500/10 text-amber-200"} />
              <Pill label={`${fmtNumber(hftSpeedGate.latency_budget_ms, 0)}ms budget`} tone="border-sky-500/30 bg-sky-500/10 text-sky-100" />
              <Pill label="validated predictions required" tone="border-yellow-500/30 bg-yellow-500/10 text-yellow-100" />
            </div>
          </div>
          <p className="mb-3 text-sm text-muted-foreground">
            High-frequency GOLD logic is only trusted when the inputs are fast enough and the prediction stream has fresh, outcome-validated GOLD/XAU rows.
          </p>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-6">
            <Metric label="Speed Score" value={fmtPercent(hftSpeedGate.speed_score)} hint="latency plus validation" />
            <Metric label="Fresh Predictions" value={fmtNumber(hftPredictionValidation.fresh_gold_prediction_count, 0)} hint="GOLD/XAU only" />
            <Metric label="Validated" value={fmtNumber(hftPredictionValidation.validated_gold_prediction_count, 0)} hint="outcome checked" />
            <Metric label="Correct Validated" value={fmtNumber(hftPredictionValidation.validated_correct_gold_prediction_count, 0)} hint="positive proof" />
            <Metric label="Speed Surfaces" value={`${fmtNumber(hftSpeedGate.present_surface_count, 0)}/${fmtNumber(hftSpeedGate.surface_count, 0)}`} hint="repo route" />
            <Metric label="Blockers" value={fmtNumber(hftBlockers.length, 0)} hint="promotion gate" />
          </div>
          <div className="mt-4 grid gap-4 xl:grid-cols-[0.95fr_1.05fr]">
            <div className="rounded-md border border-border/60 bg-background/50 p-3">
              <div className="text-sm font-medium">Speed Blockers</div>
              <div className="mt-2 grid gap-2 md:grid-cols-2">
                {hftBlockers.length ? (
                  hftBlockers.slice(0, 6).map((blocker: JsonMap) => (
                    <div key={String(blocker.id || blocker.reason)} className="rounded border border-amber-500/20 bg-amber-500/5 p-2 text-xs">
                      <div className="truncate font-medium text-amber-100">{String(blocker.id || "blocker").replace(/_/g, " ")}</div>
                      <div className="mt-1 line-clamp-2 text-muted-foreground">{String(blocker.reason || "")}</div>
                    </div>
                  ))
                ) : (
                  <div className="rounded border border-emerald-500/20 bg-emerald-500/5 p-2 text-xs text-emerald-200">Speed and validated prediction gate is passing.</div>
                )}
              </div>
            </div>
            <ScrollArea className="h-52 pr-3">
              <div className="grid gap-2 lg:grid-cols-2">
                {hftLatencyChecks.map((check: JsonMap) => (
                  <div key={String(check.id || check.status)} className="rounded-md border border-border/60 bg-background/50 p-3">
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <div className="truncate text-sm font-medium">{String(check.id || "latency").replace(/_/g, " ")}</div>
                        <div className="mt-1 truncate text-xs text-muted-foreground">{fmtNumber(check.age_ms, 0)}ms / {fmtNumber(check.max_age_ms, 0)}ms</div>
                      </div>
                      <Pill label={check.fresh_for_hft ? "fast" : "held"} tone={check.fresh_for_hft ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200" : "border-amber-500/30 bg-amber-500/10 text-amber-200"} />
                    </div>
                  </div>
                ))}
                {hftRouteSurfaces.slice(0, 6).map((surface: JsonMap) => (
                  <div key={String(surface.id || surface.path)} className="rounded-md border border-border/60 bg-background/50 p-3">
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <div className="truncate text-sm font-medium">{String(surface.id || "speed surface").replace(/_/g, " ")}</div>
                        <div className="mt-1 line-clamp-2 text-xs text-muted-foreground">{String(surface.role || "")}</div>
                      </div>
                      <Pill label={surface.present ? "present" : "missing"} tone={surface.present ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200" : "border-red-500/30 bg-red-500/10 text-red-200"} />
                    </div>
                  </div>
                ))}
              </div>
            </ScrollArea>
          </div>
        </section>

        <section className="rounded-md border border-indigo-500/30 bg-indigo-500/5 p-4">
          <div className="mb-3 flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
            <div className="flex min-w-0 items-center gap-2">
              <LineChart className="h-4 w-4 shrink-0 text-indigo-300" />
              <h3 className="truncate text-sm font-semibold">Gold Historical Stress Test</h3>
            </div>
            <div className="flex flex-wrap gap-2">
              <Pill label={String(historicalStress.status || "historical stress waiting")} tone={historicalStress.stress_passed ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200" : "border-amber-500/30 bg-amber-500/10 text-amber-200"} />
              <Pill label="real rows only" tone="border-indigo-500/30 bg-indigo-500/10 text-indigo-100" />
              <Pill label={historicalStress.live_order_allowed ? "live allowed" : "live blocked"} tone="border-emerald-500/30 bg-emerald-500/10 text-emerald-200" />
            </div>
          </div>
          <p className="mb-3 text-sm text-muted-foreground">
            Historical proof is a separate replay gate: GOLD/XAU prediction rows must be timestamped, outcome-validated, and replayable through existing backtest/history surfaces before the system can claim handover-ready shadow logic.
          </p>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-6">
            <Metric label="Prediction Rows" value={fmtNumber(historicalStressValidation.row_count, 0)} hint="GOLD/XAU only" />
            <Metric label="Validated Rows" value={fmtNumber(historicalStressValidation.validated_count, 0)} hint="outcome checked" />
            <Metric label="Correct Rows" value={fmtNumber(historicalStressValidation.validated_correct_count, 0)} hint="direction proof" />
            <Metric label="Historical Hit Rate" value={historicalStressValidation.hit_rate === null || historicalStressValidation.hit_rate === undefined ? "0%" : fmtPercent(historicalStressValidation.hit_rate)} hint="minimum 55%" />
            <Metric label="Stress Scenarios" value={`${fmtNumber(historicalStressScenarios.filter((scenario: JsonMap) => scenario.state === "passed").length, 0)}/${fmtNumber(historicalStressScenarios.length, 0)}`} hint="replay checks" />
            <Metric label="Replay Surfaces" value={`${fmtNumber(historicalStress.present_surface_count, 0)}/${fmtNumber(historicalStress.surface_count, 0)}`} hint="repo route" />
          </div>
          <div className="mt-4 grid gap-4 xl:grid-cols-[1fr_1fr]">
            <div className="rounded-md border border-border/60 bg-background/50 p-3">
              <div className="text-sm font-medium">Stress Scenarios</div>
              <div className="mt-2 grid gap-2">
                {historicalStressScenarios.length ? (
                  historicalStressScenarios.map((scenario: JsonMap) => (
                    <div key={String(scenario.id || scenario.label)} className="rounded border border-border/50 bg-background/40 p-2 text-xs">
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <div className="truncate font-medium">{String(scenario.label || scenario.id || "scenario")}</div>
                          <div className="mt-1 line-clamp-2 text-muted-foreground">{String(scenario.proof || "")}</div>
                        </div>
                        <Pill label={String(scenario.state || "waiting")} tone={scenario.state === "passed" ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200" : "border-amber-500/30 bg-amber-500/10 text-amber-200"} />
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="rounded border border-amber-500/20 bg-amber-500/5 p-2 text-xs text-amber-100">No historical stress scenarios are published yet.</div>
                )}
              </div>
            </div>
            <div className="rounded-md border border-border/60 bg-background/50 p-3">
              <div className="text-sm font-medium">Historical Blockers</div>
              <div className="mt-2 grid gap-2 md:grid-cols-2">
                {historicalStressBlockers.length ? (
                  historicalStressBlockers.slice(0, 6).map((blocker: JsonMap) => (
                    <div key={String(blocker.id || blocker.reason)} className="rounded border border-amber-500/20 bg-amber-500/5 p-2 text-xs">
                      <div className="truncate font-medium text-amber-100">{String(blocker.id || "blocker").replace(/_/g, " ")}</div>
                      <div className="mt-1 line-clamp-2 text-muted-foreground">{String(blocker.reason || "")}</div>
                    </div>
                  ))
                ) : (
                  <div className="rounded border border-emerald-500/20 bg-emerald-500/5 p-2 text-xs text-emerald-200">Historical replay gate is passing for shadow evidence.</div>
                )}
              </div>
              <div className="mt-3 grid gap-2 md:grid-cols-2">
                {historicalStressSurfaces.slice(0, 6).map((surface: JsonMap) => (
                  <div key={String(surface.id || surface.path)} className="rounded border border-border/40 bg-background/35 p-2 text-xs">
                    <div className="flex items-center justify-between gap-2">
                      <div className="truncate font-medium">{String(surface.id || "surface").replace(/_/g, " ")}</div>
                      <Pill label={surface.present ? "present" : "missing"} tone={surface.present ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200" : "border-red-500/30 bg-red-500/10 text-red-200"} />
                    </div>
                    <div className="mt-1 line-clamp-2 text-muted-foreground">{String(surface.role || "")}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section className="rounded-md border border-cyan-500/30 bg-cyan-500/5 p-4">
          <div className="mb-3 flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
            <div className="flex items-center gap-2">
              <Radio className="h-4 w-4 text-cyan-300" />
              <h3 className="text-sm font-semibold">Gold Agent Coding Support</h3>
            </div>
            <div className="flex flex-wrap gap-2">
              <Pill label={String(agentCodingSupport.status || "agent support waiting")} tone={agentCodingSupport.support_ready ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200" : "border-amber-500/30 bg-amber-500/10 text-amber-200"} />
              <Pill label={`${fmtNumber(summary.gold_agent_chat_lane_count || agentChatLanes.length, 0)} chat lanes`} tone="border-cyan-500/30 bg-cyan-500/10 text-cyan-200" />
              <Pill label={`${fmtNumber(summary.gold_agent_tool_lane_count || agentToolLanes.length, 0)} tool lanes`} tone="border-yellow-500/30 bg-yellow-500/10 text-yellow-100" />
            </div>
          </div>
          <p className="mb-3 text-sm text-muted-foreground">
            GOLD agents can use the coding organism, capability forge, dynamic prompt filter, ThoughtBus, and monitor surfaces to request tools, publish evidence, and keep the whole GOLD mission visible without bypassing live-trading gates.
          </p>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
            <Metric label="Support Surfaces" value={`${fmtNumber(agentCodingSupport.present_surface_count, 0)}/${fmtNumber(agentCodingSupport.surface_count, 0)}`} hint="code routes" />
            <Metric label="Support Artifacts" value={`${fmtNumber(agentCodingSupport.present_artifact_count, 0)}/${fmtNumber(agentCodingSupport.artifact_count, 0)}`} hint="public/state proof" />
            <Metric label="Fresh Artifacts" value={fmtNumber(agentCodingSupport.fresh_artifact_count, 0)} hint="15m freshness" />
            <Metric label="Monitor Targets" value={fmtNumber(summary.gold_agent_monitor_target_count || agentMonitorTargets.length, 0)} hint="GOLD gates watched" />
            <Metric label="Support Blockers" value={fmtNumber(agentSupportBlockers.length, 0)} hint="agent lane holds" />
          </div>
          <div className="mt-4 grid gap-4 xl:grid-cols-[0.95fr_1.05fr]">
            <div className="grid gap-3">
              <div className="rounded-md border border-border/60 bg-background/50 p-3">
                <div className="text-sm font-medium">Agent Chat Lanes</div>
                <div className="mt-2 grid gap-2">
                  {agentChatLanes.map((lane: JsonMap) => (
                    <div key={String(lane.id || lane.label)} className="rounded border border-border/50 bg-background/40 p-2 text-xs">
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <div className="truncate font-medium">{String(lane.label || lane.id)}</div>
                          <div className="mt-1 line-clamp-2 text-muted-foreground">{String(lane.use_for_gold || "")}</div>
                        </div>
                        <Pill label={String(lane.status || "waiting")} tone={toneForStatus(String(lane.status || ""))} />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
              <div className="rounded-md border border-border/60 bg-background/50 p-3">
                <div className="text-sm font-medium">Agent Tool Lanes</div>
                <div className="mt-2 grid gap-2">
                  {agentToolLanes.map((lane: JsonMap) => (
                    <div key={String(lane.id || lane.label)} className="rounded border border-border/50 bg-background/40 p-2 text-xs">
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <div className="truncate font-medium">{String(lane.label || lane.id)}</div>
                          <div className="mt-1 line-clamp-2 text-muted-foreground">{String(lane.use_for_gold || "")}</div>
                        </div>
                        <Pill label={String(lane.status || "waiting")} tone={toneForStatus(String(lane.status || ""))} />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
            <div className="grid gap-3">
              <div className="rounded-md border border-border/60 bg-background/50 p-3">
                <div className="text-sm font-medium">Gold Monitor Targets</div>
                <div className="mt-2 grid gap-2 md:grid-cols-2">
                  {agentMonitorTargets.map((target: JsonMap) => (
                    <div key={String(target.id || target.label)} className="rounded border border-border/50 bg-background/40 p-2 text-xs">
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <div className="truncate font-medium">{String(target.label || target.id)}</div>
                          <div className="mt-1 line-clamp-2 text-muted-foreground">{String(target.agent_action || "")}</div>
                        </div>
                        <Pill label={target.ready ? "ready" : "held"} tone={target.ready ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200" : "border-amber-500/30 bg-amber-500/10 text-amber-200"} />
                      </div>
                      <div className="mt-1 truncate text-muted-foreground">{String(target.status || "")}</div>
                    </div>
                  ))}
                </div>
              </div>
              <ScrollArea className="h-52 pr-3">
                <div className="grid gap-2 md:grid-cols-2">
                  {agentSupportArtifacts.map((artifact: JsonMap) => (
                    <div key={String(artifact.id || artifact.path)} className="rounded-md border border-border/60 bg-background/50 p-3">
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <div className="truncate text-sm font-medium">{String(artifact.id || "artifact").replace(/_/g, " ")}</div>
                          <div className="mt-1 truncate text-xs text-muted-foreground">{String(artifact.status || "status")}</div>
                        </div>
                        <Pill label={artifact.present ? artifact.fresh ? "fresh" : "stale" : "missing"} tone={artifact.present ? artifact.fresh ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200" : "border-amber-500/30 bg-amber-500/10 text-amber-200" : "border-red-500/30 bg-red-500/10 text-red-200"} />
                      </div>
                    </div>
                  ))}
                  {agentSupportSurfaces.slice(0, 8).map((surface: JsonMap) => (
                    <div key={String(surface.id || surface.path)} className="rounded-md border border-border/60 bg-background/50 p-3">
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <div className="truncate text-sm font-medium">{String(surface.id || "surface").replace(/_/g, " ")}</div>
                          <div className="mt-1 truncate text-xs text-muted-foreground">{String(surface.family || "support")}</div>
                        </div>
                        <Pill label={surface.present ? "present" : "missing"} tone={surface.present ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200" : "border-red-500/30 bg-red-500/10 text-red-200"} />
                      </div>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            </div>
          </div>
        </section>

        <section className="rounded-md border border-yellow-500/30 bg-yellow-500/5 p-4">
          <div className="mb-3 flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
            <div className="flex min-w-0 items-center gap-2">
              <ShieldCheck className="h-4 w-4 shrink-0 text-yellow-300" />
              <h3 className="truncate text-sm font-semibold">Gold Action Command</h3>
            </div>
            <div className="flex flex-wrap gap-2">
              <Pill label={String(goldActionCommand.status || "command waiting")} tone={toneForStatus(String(goldActionCommand.status || ""))} />
              <Pill label={String(goldAction.state || "hold")} tone="border-yellow-500/30 bg-yellow-500/10 text-yellow-100" />
              <Pill label={`${fmtNumber(commandSystems.length, 0)} command systems`} tone="border-cyan-500/30 bg-cyan-500/10 text-cyan-200" />
            </div>
          </div>
          <div className="grid gap-3 xl:grid-cols-[0.95fr_1.05fr]">
            <div className="grid gap-2 md:grid-cols-2">
              <div className="rounded-md border border-border/60 bg-background/50 p-3">
                <div className="text-[11px] uppercase tracking-normal text-muted-foreground">who</div>
                <div className="mt-1 text-sm font-medium">{String(goldActionWho.commander || "Gold Strategy Steward")}</div>
                <div className="mt-1 text-xs text-muted-foreground">{fmtNumber(goldActionWho.active_agent_count, 0)} active / {fmtNumber(goldActionWho.attention_agent_count, 0)} attention agents</div>
              </div>
              <div className="rounded-md border border-border/60 bg-background/50 p-3">
                <div className="text-[11px] uppercase tracking-normal text-muted-foreground">what</div>
                <div className="mt-1 line-clamp-2 text-sm font-medium">{String(goldActionWhat.mission || "Best allowed action on Capital GOLD")}</div>
                <div className="mt-1 text-xs text-muted-foreground">{String(goldActionWhat.profit_floor || "3p floor")}</div>
              </div>
              <div className="rounded-md border border-border/60 bg-background/50 p-3">
                <div className="text-[11px] uppercase tracking-normal text-muted-foreground">when</div>
                <div className="mt-1 text-sm font-medium">{String(goldActionWhen.current_window || "hold")}</div>
                <div className="mt-1 line-clamp-2 text-xs text-muted-foreground">{(Array.isArray(goldActionWhen.open_conditions) ? goldActionWhen.open_conditions : []).slice(0, 2).join(" | ")}</div>
              </div>
              <div className="rounded-md border border-border/60 bg-background/50 p-3">
                <div className="text-[11px] uppercase tracking-normal text-muted-foreground">act</div>
                <div className="mt-1 text-sm font-medium">{String(goldAction.side || "HOLD")} - {String(goldAction.state || "hold")}</div>
                <div className="mt-1 line-clamp-2 text-xs text-muted-foreground">{String(goldAction.instruction || "Hold until proof is fresh.")}</div>
              </div>
            </div>
            <ScrollArea className="h-52 pr-3">
              <div className="grid gap-2 lg:grid-cols-2">
                {goldProofChain.map((item: JsonMap) => (
                  <div key={String(item.id || item.question)} className="rounded-md border border-border/60 bg-background/50 p-3">
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <div className="truncate text-sm font-medium">{String(item.id || "proof").replace(/_/g, " ")}</div>
                        <div className="mt-1 line-clamp-2 text-xs text-muted-foreground">{String(item.question || "")}</div>
                      </div>
                      <Pill label={String(item.state || "waiting")} tone={toneForStatus(String(item.state || ""))} />
                    </div>
                    <div className="mt-2 line-clamp-2 text-xs text-muted-foreground">{String(item.proof || "")}</div>
                  </div>
                ))}
              </div>
            </ScrollArea>
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            {(Array.isArray(goldActionHow.ready_driver_ids) ? goldActionHow.ready_driver_ids : []).slice(0, 6).map((driver: string) => (
              <Pill key={driver} label={String(driver).replace(/_/g, " ")} tone="border-emerald-500/30 bg-emerald-500/10 text-emerald-200" />
            ))}
            {commandSystems.slice(0, 5).map((system: JsonMap) => (
              <Pill key={String(system.id || system.path)} label={String(system.id || "command").replace(/_/g, " ")} />
            ))}
          </div>
        </section>

        <section className="rounded-md border border-yellow-500/30 bg-yellow-500/5 p-4">
          <div className="mb-3 flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
            <div className="flex min-w-0 items-center gap-2">
              <LineChart className="h-4 w-4 shrink-0 text-yellow-300" />
              <h3 className="truncate text-sm font-semibold">Gold Shadow Trading Focus</h3>
            </div>
            <div className="flex flex-wrap gap-2">
              <Pill label={String(goldShadowFocus.status || "shadow focus waiting")} tone={toneForStatus(String(goldShadowFocus.status || ""))} />
              <Pill label="gold and gold energy only" tone="border-yellow-500/30 bg-yellow-500/10 text-yellow-100" />
              <Pill label={String(goldShadowPromotionGate.state || "held_until_verified_real_data")} tone="border-cyan-500/30 bg-cyan-500/10 text-cyan-200" />
            </div>
          </div>
          <p className="mb-3 text-sm text-muted-foreground">
            The shadow lane treats Capital GOLD as the only tradable target candidate. Oil, energy, USD/rates, miners, VIX, crypto liquidity, and geopolitics are confirmation lanes until the real-data and 3p gates pass.
          </p>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            <Metric label="Gold Candidates" value={fmtNumber(goldShadowFocus.gold_related_shadow_count, 0)} hint="target lane only" />
            <Metric label="Context Items" value={fmtNumber(goldShadowFocus.context_shadow_count, 0)} hint="confirmation only" />
            <Metric label="Energy Lanes" value={fmtNumber(summary.gold_shadow_focus_energy_lane_count || goldShadowEnergyLanes.length, 0)} hint="gold drivers" />
            <Metric label="Excluded Generic Shadows" value={fmtNumber(goldShadowFocus.excluded_shadow_count, 0)} hint="not promoted" />
          </div>
          <div className="mt-4 grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
            <div className="grid gap-3">
              <div className="rounded-md border border-border/60 bg-background/50 p-3">
                <div className="flex items-center justify-between gap-2">
                  <div className="text-sm font-medium">Promotion Gate</div>
                  <Pill label={String(goldShadowPromotionGate.side || "HOLD")} tone="border-yellow-500/30 bg-yellow-500/10 text-yellow-100" />
                </div>
                <div className="mt-2 grid grid-cols-2 gap-2 text-[11px]">
                  <div className="rounded border border-border/40 bg-background/35 p-2">
                    <div className="text-muted-foreground">entry</div>
                    <div className="font-semibold">{fmtNumber(effectiveShadowEntry, 2)}</div>
                  </div>
                  <div className="rounded border border-border/40 bg-background/35 p-2">
                    <div className="text-muted-foreground">target</div>
                    <div className="font-semibold">{fmtNumber(goldShadowPromotionGate.target_level, 2)}</div>
                  </div>
                  <div className="rounded border border-border/40 bg-background/35 p-2">
                    <div className="text-muted-foreground">size</div>
                    <div className="font-semibold">{fmtNumber(goldShadowPromotionGate.suggested_shadow_size, 4)}</div>
                  </div>
                  <div className="rounded border border-border/40 bg-background/35 p-2">
                    <div className="text-muted-foreground">orders</div>
                    <div className="font-semibold">{goldShadowPromotionGate.order_mutation_allowed ? "armed" : "blocked"}</div>
                  </div>
                </div>
                <div className="mt-3 space-y-2">
                  {(Array.isArray(goldShadowPromotionGate.blockers) ? goldShadowPromotionGate.blockers : []).slice(0, 4).map((blocker: JsonMap) => (
                    <div key={String(blocker.id || blocker.reason)} className="rounded border border-amber-500/20 bg-amber-500/5 p-2 text-xs">
                      <div className="truncate font-medium text-amber-100">{String(blocker.id || "blocker").replace(/_/g, " ")}</div>
                      <div className="mt-1 line-clamp-2 text-muted-foreground">{String(blocker.reason || "")}</div>
                    </div>
                  ))}
                </div>
              </div>
              <div className="rounded-md border border-border/60 bg-background/50 p-3">
                <div className="text-sm font-medium">Active Gold Shadow Candidates</div>
                <div className="mt-2 space-y-2">
                  {goldShadowCandidates.length ? (
                    goldShadowCandidates.slice(0, 4).map((candidate: JsonMap) => (
                      <div key={`${String(candidate.source)}-${String(candidate.symbol)}-${String(candidate.side)}`} className="rounded border border-border/40 bg-background/35 p-2 text-xs">
                        <div className="truncate font-medium">{String(candidate.symbol || "GOLD")} {String(candidate.side || "CONTEXT")}</div>
                        <div className="mt-1 text-muted-foreground">confidence {fmtPercent(candidate.confidence)} | {String(candidate.source || "shadow")}</div>
                      </div>
                    ))
                  ) : (
                    <div className="rounded border border-amber-500/20 bg-amber-500/5 p-2 text-xs text-amber-100">No direct GOLD shadow candidate is ready.</div>
                  )}
                </div>
              </div>
            </div>
            <div className="grid gap-3">
              <ScrollArea className="h-64 pr-3">
                <div className="grid gap-2 lg:grid-cols-2">
                  {goldShadowEnergyLanes.map((lane: JsonMap) => (
                    <div key={String(lane.id || lane.label)} className="rounded-md border border-border/60 bg-background/50 p-3">
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <div className="truncate text-sm font-medium">{String(lane.label || lane.id)}</div>
                          <div className="mt-1 truncate text-xs text-muted-foreground">{String(lane.lane_role || "context")} | {String(lane.target_authority || "context")}</div>
                        </div>
                        <Pill label={String(lane.driver_state || "waiting")} tone={toneForStatus(String(lane.driver_state || ""))} />
                      </div>
                      <div className="mt-2 line-clamp-2 text-xs text-muted-foreground">{String(lane.next_action || "")}</div>
                    </div>
                  ))}
                </div>
              </ScrollArea>
              <div className="rounded-md border border-border/60 bg-background/50 p-3">
                <div className="text-sm font-medium">Focus Rules</div>
                <div className="mt-2 grid gap-2 md:grid-cols-2">
                  {goldShadowFocusRules.slice(0, 4).map((rule: string) => (
                    <div key={rule} className="rounded border border-border/40 bg-background/35 p-2 text-xs text-muted-foreground">{rule}</div>
                  ))}
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  {goldShadowContextItems.slice(0, 3).map((item: JsonMap) => (
                    <Pill key={`${String(item.source)}-${String(item.symbol)}-${String(item.relation_to_gold)}`} label={`${String(item.symbol || "context")} context`} />
                  ))}
                  {goldShadowExcludedItems.slice(0, 3).map((item: JsonMap) => (
                    <Pill key={`${String(item.source)}-${String(item.symbol)}-excluded`} label={`${String(item.symbol || "generic")} excluded`} tone="border-amber-500/30 bg-amber-500/10 text-amber-100" />
                  ))}
                </div>
              </div>
            </div>
          </div>
        </section>

        <div className="grid gap-4 xl:grid-cols-3">
          <section className="rounded-md border border-border/70 bg-background/35 p-4">
            <div className="mb-3 flex items-center gap-2">
              <LineChart className="h-4 w-4 text-cyan-300" />
              <h3 className="text-sm font-semibold">Signals</h3>
            </div>
            <ScrollArea className="h-64 pr-3">
              <div className="space-y-2">
                {signals.slice(0, 8).map((signal: JsonMap) => (
                  <div key={String(signal.id || signal.label)} className="rounded-md border border-border/60 bg-background/50 p-3">
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <div className="truncate text-sm font-medium">{String(signal.label || signal.id)}</div>
                        <div className="mt-1 line-clamp-2 text-xs text-muted-foreground">{String(signal.reason || "")}</div>
                      </div>
                      <Pill label={String(signal.direction || "signal")} tone={signal.fresh ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200" : "border-amber-500/30 bg-amber-500/10 text-amber-200"} />
                    </div>
                  </div>
                ))}
              </div>
            </ScrollArea>
          </section>

          <section className="rounded-md border border-border/70 bg-background/35 p-4">
            <div className="mb-3 flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-emerald-300" />
              <h3 className="text-sm font-semibold">Company Roles</h3>
            </div>
            <ScrollArea className="h-64 pr-3">
              <div className="space-y-2">
                {roles.slice(0, 12).map((role: JsonMap) => (
                  <div key={String(role.role)} className="rounded-md border border-border/60 bg-background/50 p-3">
                    <div className="truncate text-sm font-medium">{String(role.role || "role")}</div>
                    <div className="mt-1 text-xs text-muted-foreground">{String(role.department || "department")} | {String(role.authority || "authority")}</div>
                    <div className="mt-1 line-clamp-2 text-xs text-muted-foreground">{String(role.mission || "")}</div>
                  </div>
                ))}
              </div>
            </ScrollArea>
          </section>

          <section className="rounded-md border border-border/70 bg-background/35 p-4">
            <div className="mb-3 flex items-center gap-2">
              <Radio className="h-4 w-4 text-blue-300" />
              <h3 className="text-sm font-semibold">Next Actions</h3>
            </div>
            <ScrollArea className="h-64 pr-3">
              <div className="space-y-2">
                {nextActions.slice(0, 8).map((action: JsonMap) => (
                  <div key={String(action.id || action.action)} className="rounded-md border border-border/60 bg-background/50 p-3">
                    <div className="truncate text-sm font-medium">{String(action.id || "next_action")}</div>
                    <div className="mt-1 line-clamp-2 text-xs text-muted-foreground">{String(action.action || "")}</div>
                    <div className="mt-2 flex flex-wrap gap-2">
                      <Pill label={String(action.owner || "Aureon")} />
                      <Pill label={String(action.authority || "read_only")} />
                    </div>
                  </div>
                ))}
              </div>
            </ScrollArea>
          </section>
        </div>

        <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
          <section className="rounded-md border border-border/70 bg-background/35 p-4">
            <div className="mb-3 flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
              <div className="flex items-center gap-2">
                <Building2 className="h-4 w-4 text-yellow-300" />
                <h3 className="text-sm font-semibold">Gold Intelligence Coverage</h3>
              </div>
              <div className="flex flex-wrap gap-2">
                <Pill label={`${fmtNumber(summary.gold_intelligence_surface_ready_count, 0)}/${fmtNumber(summary.gold_intelligence_surface_count, 0)} organs mapped`} tone="border-yellow-500/30 bg-yellow-500/10 text-yellow-100" />
                <Pill label={`${fmtNumber(summary.local_research_packet_count, 0)} research packets`} tone="border-cyan-500/30 bg-cyan-500/10 text-cyan-200" />
              </div>
            </div>
            <ScrollArea className="h-72 pr-3">
              <div className="grid gap-2 md:grid-cols-2">
                {goldIntelligenceMap.slice(0, 16).map((surface: JsonMap) => (
                  <div key={String(surface.id || surface.path)} className="rounded-md border border-border/60 bg-background/50 p-3">
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <div className="truncate text-sm font-medium">{String(surface.id || "gold organ").replace(/_/g, " ")}</div>
                        <div className="mt-1 truncate text-xs text-muted-foreground">{String(surface.department || "department")} | {String(surface.tool_type || "tool")}</div>
                      </div>
                      <Pill label={String(surface.status || "waiting")} tone={surface.present ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200" : "border-red-500/30 bg-red-500/10 text-red-200"} />
                    </div>
                    <div className="mt-2 line-clamp-2 text-xs text-muted-foreground">{String(surface.use_for_gold || "")}</div>
                  </div>
                ))}
              </div>
            </ScrollArea>
          </section>

          <section className="rounded-md border border-border/70 bg-background/35 p-4">
            <div className="mb-3 flex items-center gap-2">
              <LineChart className="h-4 w-4 text-yellow-300" />
              <h3 className="text-sm font-semibold">Gold Market Universe</h3>
            </div>
            <div className="grid gap-2 sm:grid-cols-2">
              {Object.entries(marketBuckets).map(([bucket, count]) => (
                <div key={bucket} className="rounded-md border border-border/60 bg-background/50 p-3">
                  <div className="truncate text-[11px] uppercase tracking-normal text-muted-foreground">{bucket.replace(/_/g, " ")}</div>
                  <div className="mt-1 text-lg font-semibold">{fmtNumber(count, 0)}</div>
                </div>
              ))}
            </div>
            <div className="mt-4 space-y-2">
              <div className="text-xs font-medium text-muted-foreground">Intelligence gaps</div>
              {intelligenceGaps.length ? (
                intelligenceGaps.slice(0, 5).map((gap: JsonMap) => (
                  <div key={String(gap.id || gap.gap)} className="rounded-md border border-amber-500/20 bg-amber-500/5 p-2">
                    <div className="truncate text-xs font-medium text-amber-100">{String(gap.id || "gap")}</div>
                    <div className="mt-1 line-clamp-2 text-[11px] text-muted-foreground">{String(gap.next_action || gap.gap || "")}</div>
                  </div>
                ))
              ) : (
                <div className="rounded-md border border-emerald-500/20 bg-emerald-500/5 p-2 text-xs text-emerald-200">No gold intelligence gaps reported.</div>
              )}
            </div>
          </section>
        </div>

        <section className="rounded-md border border-border/70 bg-background/35 p-4">
          <div className="mb-3 flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
            <div className="flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-emerald-300" />
              <h3 className="text-sm font-semibold">Gold Swarm Intelligence</h3>
            </div>
            <div className="flex flex-wrap gap-2">
              <Pill label={String(swarmIntelligence.status || "swarm waiting")} tone={swarmIntelligence.status === "gold_swarm_active" ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200" : "border-amber-500/30 bg-amber-500/10 text-amber-200"} />
              <Pill label={`compile ${String(swarmCompileGate.state || "waiting")}`} tone="border-cyan-500/30 bg-cyan-500/10 text-cyan-200" />
            </div>
          </div>
          <ScrollArea className="h-80 pr-3">
            <div className="grid gap-2 lg:grid-cols-3">
              {swarmAgents.map((agent: JsonMap) => (
                <div key={String(agent.id || agent.role)} className="rounded-md border border-border/60 bg-background/50 p-3">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <div className="truncate text-sm font-medium">{String(agent.role || agent.id)}</div>
                      <div className="mt-1 truncate text-xs text-muted-foreground">{String(agent.department || "department")} | {String(agent.mode || "mode")}</div>
                    </div>
                    <Pill label={String(agent.state || "waiting")} tone={agent.state === "active" ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200" : "border-amber-500/30 bg-amber-500/10 text-amber-200"} />
                  </div>
                  <div className="mt-2 line-clamp-2 text-xs text-muted-foreground">{String(agent.mission || "")}</div>
                  <div className="mt-2 flex flex-wrap gap-1">
                    {(Array.isArray(agent.assigned_driver_ids) ? agent.assigned_driver_ids : []).slice(0, 4).map((driver: string) => (
                      <Pill key={driver} label={String(driver).replace(/_/g, " ")} />
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </ScrollArea>
        </section>

        <section className="rounded-md border border-yellow-500/30 bg-yellow-500/5 p-4">
          <div className="mb-3 flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
            <div className="flex min-w-0 items-center gap-2">
              <LineChart className="h-4 w-4 shrink-0 text-yellow-300" />
              <h3 className="truncate text-sm font-semibold">Gold Priority Workbench</h3>
            </div>
            <div className="flex flex-wrap gap-2">
              <Pill label={String(goldPriorityWorkbench.status || "priority waiting")} tone={toneForStatus(String(goldPriorityWorkbench.status || ""))} />
              <Pill label={`${fmtNumber(summary.gold_priority_data_queue_count, 0)} data tasks`} tone="border-yellow-500/30 bg-yellow-500/10 text-yellow-100" />
              <Pill label={`${fmtNumber(forecastPoints.length, 0)} forecast points`} tone="border-cyan-500/30 bg-cyan-500/10 text-cyan-200" />
            </div>
          </div>
          <div className="grid gap-4 xl:grid-cols-[0.85fr_1.15fr]">
            <div className="rounded-md border border-border/60 bg-background/50 p-3">
              <div className="text-sm font-medium">Forecast Artifacts</div>
              <div className="mt-2 grid gap-2 sm:grid-cols-2">
                {priorityArtifactManifest.html_url ? (
                  <a className="inline-flex items-center justify-center gap-2 rounded-md border border-cyan-500/30 bg-cyan-500/10 px-3 py-2 text-xs text-cyan-100 hover:bg-cyan-500/20" href={String(priorityArtifactManifest.html_url)} target="_blank" rel="noreferrer">
                    Open forecast dashboard <ExternalLink className="h-3.5 w-3.5" />
                  </a>
                ) : null}
                {priorityArtifactManifest.svg_url ? (
                  <a className="inline-flex items-center justify-center gap-2 rounded-md border border-yellow-500/30 bg-yellow-500/10 px-3 py-2 text-xs text-yellow-100 hover:bg-yellow-500/20" href={String(priorityArtifactManifest.svg_url)} target="_blank" rel="noreferrer">
                    Open chart SVG <ExternalLink className="h-3.5 w-3.5" />
                  </a>
                ) : null}
              </div>
              <div className="mt-3 grid grid-cols-3 gap-2 text-[11px]">
                <div className="rounded border border-border/40 bg-background/35 p-2">
                  <div className="text-muted-foreground">focus</div>
                  <div className="truncate font-semibold">{String(goldPriorityWorkbench.priority_focus || "GOLD")}</div>
                </div>
                <div className="rounded border border-border/40 bg-background/35 p-2">
                  <div className="text-muted-foreground">handover</div>
                  <div className="truncate font-semibold">{String((goldPriorityWorkbench.chart_contract || {}).handover || "review")}</div>
                </div>
                <div className="rounded border border-border/40 bg-background/35 p-2">
                  <div className="text-muted-foreground">authority</div>
                  <div className="truncate font-semibold">{String((goldPriorityWorkbench.chart_contract || {}).authority || "read-only")}</div>
                </div>
              </div>
            </div>
            <ScrollArea className="h-56 pr-3">
              <div className="grid gap-2 lg:grid-cols-2">
                {priorityDataQueue.map((item: JsonMap) => (
                  <div key={String(item.id || item.agent)} className="rounded-md border border-border/60 bg-background/50 p-3">
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <div className="truncate text-sm font-medium">{String(item.id || "gold data task").replace(/_/g, " ")}</div>
                        <div className="mt-1 truncate text-xs text-muted-foreground">{String(item.agent || "agent")}</div>
                      </div>
                      <Pill label={String(item.priority || "P?")} tone="border-yellow-500/30 bg-yellow-500/10 text-yellow-100" />
                    </div>
                    <div className="mt-2 line-clamp-2 text-xs text-muted-foreground">{String(item.data_needed || "")}</div>
                    <div className="mt-1 line-clamp-2 text-xs text-muted-foreground">{String(item.proof_required || "")}</div>
                  </div>
                ))}
              </div>
            </ScrollArea>
          </div>
        </section>

        <section className="rounded-md border border-emerald-500/30 bg-emerald-500/5 p-4">
          <div className="mb-3 flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
            <div className="flex items-center gap-2">
              <Radio className="h-4 w-4 text-emerald-300" />
              <h3 className="text-sm font-semibold">Gold Exchange Optimization</h3>
            </div>
            <div className="flex flex-wrap gap-2">
              <Pill label={String(goldExchangeOptimization.status || "exchange optimization waiting")} tone={toneForStatus(String(goldExchangeOptimization.status || ""))} />
              <Pill label={`${fmtNumber(summary.gold_exchange_ready_venue_count || goldExchangeOptimization.ready_venue_count, 0)}/${fmtNumber(summary.gold_exchange_venue_count || goldExchangeOptimization.venue_count, 0)} venues`} tone="border-emerald-500/30 bg-emerald-500/10 text-emerald-200" />
              <Pill label={`${fmtNumber(summary.gold_exchange_watchlist_bucket_count || exchangeWatchlists.length, 0)} watchlists`} tone="border-cyan-500/30 bg-cyan-500/10 text-cyan-200" />
            </div>
          </div>
          <p className="mb-3 text-sm text-muted-foreground">
            Capital.com is the primary GOLD target venue. Alpaca, Binance, Kraken, energy, USD/rates, equities, crypto liquidity, and macro feeds are monitored as confirmation lanes only unless a separate authority gate allows more.
          </p>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
            <Metric label="Optimization Score" value={fmtPercent(goldExchangeOptimization.optimization_score || summary.gold_exchange_optimization_score)} hint="venue coverage" />
            <Metric label="Ready Venues" value={`${fmtNumber(goldExchangeOptimization.ready_venue_count, 0)}/${fmtNumber(goldExchangeOptimization.venue_count, 0)}`} hint="monitoring route" />
            <Metric label="Watchlist Buckets" value={fmtNumber(exchangeWatchlists.length, 0)} hint="related assets" />
            <Metric label="Monitor Contracts" value={fmtNumber(exchangeMonitorContracts.length, 0)} hint="cadence lanes" />
            <Metric label="Exchange Blockers" value={fmtNumber(exchangeOptimizationBlockers.length, 0)} hint="holds visible" />
          </div>
          <div className="mt-4 grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
            <ScrollArea className="h-72 pr-3">
              <div className="grid gap-2 lg:grid-cols-2">
                {optimizedVenues.map((venue: JsonMap) => (
                  <div key={String(venue.id || venue.label)} className="rounded-md border border-border/60 bg-background/50 p-3">
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <div className="truncate text-sm font-medium">{String(venue.label || venue.id)}</div>
                        <div className="mt-1 truncate text-xs text-muted-foreground">{String(venue.role || "exchange role").replace(/_/g, " ")}</div>
                      </div>
                      <Pill label={venue.ready_for_gold_monitoring ? "optimized" : "attention"} tone={venue.ready_for_gold_monitoring ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200" : "border-amber-500/30 bg-amber-500/10 text-amber-200"} />
                    </div>
                    <div className="mt-2 line-clamp-2 text-xs text-muted-foreground">{String(venue.target_authority || "")}</div>
                    <div className="mt-2 flex flex-wrap gap-1">
                      {(Array.isArray(venue.watch_symbols) ? venue.watch_symbols : []).slice(0, 6).map((symbol: string) => (
                        <Pill key={`${String(venue.id)}-${symbol}`} label={symbol} />
                      ))}
                    </div>
                    <div className="mt-2 grid grid-cols-3 gap-2 text-[11px]">
                      <div className="rounded border border-border/40 bg-background/35 p-2">
                        <div className="text-muted-foreground">feed</div>
                        <div className="font-semibold">{venue.fresh_feed ? "fresh" : "held"}</div>
                      </div>
                      <div className="rounded border border-border/40 bg-background/35 p-2">
                        <div className="text-muted-foreground">map</div>
                        <div className="font-semibold">{venue.usable_for_mapping ? "yes" : "no"}</div>
                      </div>
                      <div className="rounded border border-border/40 bg-background/35 p-2">
                        <div className="text-muted-foreground">budget</div>
                        <div className="font-semibold">{fmtNumber(venue.freshness_budget_seconds, 0)}s</div>
                      </div>
                    </div>
                    {(Array.isArray(venue.blockers) ? venue.blockers : []).length ? (
                      <div className="mt-2 line-clamp-2 text-xs text-amber-100">{(venue.blockers || []).slice(0, 3).join(", ")}</div>
                    ) : null}
                  </div>
                ))}
              </div>
            </ScrollArea>
            <div className="grid gap-3">
              <div className="rounded-md border border-border/60 bg-background/50 p-3">
                <div className="text-sm font-medium">Related Asset Watchlists</div>
                <div className="mt-2 grid gap-2">
                  {exchangeWatchlists.map((item: JsonMap) => (
                    <div key={String(item.bucket || item.venue)} className="rounded border border-border/40 bg-background/35 p-2 text-xs">
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <div className="truncate font-medium">{String(item.bucket || "watchlist").replace(/_/g, " ")}</div>
                          <div className="mt-1 line-clamp-2 text-muted-foreground">{(Array.isArray(item.symbols) ? item.symbols : []).join(", ")}</div>
                        </div>
                        <Pill label={String(item.authority || "context")} />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
              <div className="rounded-md border border-border/60 bg-background/50 p-3">
                <div className="text-sm font-medium">Dynamic Monitor Contracts</div>
                <div className="mt-2 grid gap-2">
                  {exchangeMonitorContracts.map((contract: JsonMap) => (
                    <div key={String(contract.id || contract.cadence_seconds)} className="rounded border border-border/40 bg-background/35 p-2 text-xs">
                      <div className="flex items-center justify-between gap-2">
                        <div className="truncate font-medium">{String(contract.id || "monitor").replace(/_/g, " ")}</div>
                        <Pill label={`${fmtNumber(contract.cadence_seconds, 0)}s`} tone="border-cyan-500/30 bg-cyan-500/10 text-cyan-200" />
                      </div>
                      <div className="mt-1 line-clamp-2 text-muted-foreground">{(Array.isArray(contract.inputs) ? contract.inputs : []).join(", ")}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="rounded-md border border-yellow-500/30 bg-yellow-500/5 p-4">
          <div className="mb-3 flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
            <div className="flex items-center gap-2">
              <Gauge className="h-4 w-4 text-yellow-300" />
              <h3 className="text-sm font-semibold">Gold Margin Trader Unity</h3>
            </div>
            <div className="flex flex-wrap gap-2">
              <Pill label={String(marginTraderUnity.status || "margin unity waiting")} tone={toneForStatus(String(marginTraderUnity.status || ""))} />
              <Pill label={String(marginTraderUnity.unity_state || "gold_margin_unity_held")} tone={toneForStatus(String(marginTraderUnity.unity_state || ""))} />
              <Pill label={`${fmtNumber(summary.gold_margin_unity_present_surface_count || marginTraderUnity.present_surface_count, 0)}/${fmtNumber(summary.gold_margin_unity_surface_count || marginTraderUnity.surface_count, 0)} surfaces`} tone="border-cyan-500/30 bg-cyan-500/10 text-cyan-200" />
            </div>
          </div>
          <p className="mb-3 text-sm text-muted-foreground">
            The margin trader stack is commanded as one Capital GOLD lane. Crypto, ETF/miner, oil/energy, USD/rates, equities, and geopolitics stay as context; margin sizing stays shadow-only until fresh verified proof clears every gate.
          </p>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
            <Metric label="Target Venue" value={String(marginTraderUnity.target_venue || "Capital.com")} hint={String(marginTraderUnity.target_symbol || "GOLD")} />
            <Metric label="Margin Roles" value={fmtNumber(marginRoles.length, 0)} hint="workers unified" />
            <Metric label="Unity Surfaces" value={`${fmtNumber(marginTraderUnity.present_surface_count, 0)}/${fmtNumber(marginTraderUnity.surface_count, 0)}`} hint="repo routes" />
            <Metric label="Unity Blockers" value={fmtNumber(liveMarginUnityBlockers.length, 0)} hint="proof holds" />
            <Metric label="Order Authority" value={marginCommand.live_order_allowed || marginCommand.margin_order_allowed ? "armed" : "blocked"} hint="shadow before live" />
          </div>
          <div className="mt-4 grid gap-4 xl:grid-cols-[1fr_1fr]">
            <div className="grid gap-3">
              <div className="rounded-md border border-border/60 bg-background/50 p-3">
                <div className="text-sm font-medium">Margin Roles</div>
                <div className="mt-2 grid gap-2">
                  {marginRoles.map((role: JsonMap) => (
                    <div key={String(role.surface_id || role.role)} className="rounded border border-border/40 bg-background/35 p-2 text-xs">
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <div className="truncate font-medium">{String(role.role || "Margin worker")}</div>
                          <div className="mt-1 line-clamp-2 text-muted-foreground">{String(role.job || "")}</div>
                        </div>
                        <Pill label={String(role.surface_id || "surface").replace(/_/g, " ")} />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
              <div className="rounded-md border border-border/60 bg-background/50 p-3">
                <div className="text-sm font-medium">Mission Directives</div>
                <div className="mt-2 grid gap-2">
                  {marginDirectives.map((directive: JsonMap) => (
                    <div key={String(directive.id || directive.directive)} className="rounded border border-border/40 bg-background/35 p-2 text-xs">
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <div className="truncate font-medium">{String(directive.id || "directive").replace(/_/g, " ")}</div>
                          <div className="mt-1 line-clamp-2 text-muted-foreground">{String(directive.directive || "")}</div>
                        </div>
                        <Pill label={String(directive.state || "active")} tone={toneForStatus(String(directive.state || ""))} />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
            <div className="grid gap-3">
              <div className="rounded-md border border-border/60 bg-background/50 p-3">
                <div className="text-sm font-medium">Margin Surface Map</div>
                <ScrollArea className="mt-2 h-52 pr-3">
                  <div className="grid gap-2">
                    {marginSurfaces.map((surface: JsonMap) => (
                      <div key={String(surface.id || surface.path)} className="rounded border border-border/40 bg-background/35 p-2 text-xs">
                        <div className="flex items-start justify-between gap-2">
                          <div className="min-w-0">
                            <div className="truncate font-medium">{String(surface.id || "surface").replace(/_/g, " ")}</div>
                            <div className="mt-1 truncate text-muted-foreground">{String(surface.role || "")}</div>
                          </div>
                          <Pill label={surface.present ? "present" : "missing"} tone={surface.present ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200" : "border-red-500/30 bg-red-500/10 text-red-200"} />
                        </div>
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              </div>
              <div className="rounded-md border border-border/60 bg-background/50 p-3">
                <div className="text-sm font-medium">Margin Blocking Truth</div>
                <div className="mt-2 grid gap-2">
                  {liveMarginUnityBlockers.length ? liveMarginUnityBlockers.slice(0, 6).map((blocker: JsonMap) => (
                    <div key={String(blocker.id || blocker.reason)} className="rounded border border-amber-500/30 bg-amber-500/10 p-2 text-xs text-amber-100">
                      <div className="font-medium">{String(blocker.id || "margin blocker").replace(/_/g, " ")}</div>
                      <div className="mt-1 line-clamp-2">{String(blocker.reason || "")}</div>
                    </div>
                  )) : <div className="rounded border border-emerald-500/30 bg-emerald-500/10 p-2 text-xs text-emerald-100">No margin-unity blockers. Live mutation still stays behind the runtime authority gates.</div>}
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="rounded-md border border-border/70 bg-background/35 p-4">
          <div className="mb-3 flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
            <div className="flex items-center gap-2">
              <LineChart className="h-4 w-4 text-yellow-300" />
              <h3 className="text-sm font-semibold">Historical Signal Lab</h3>
            </div>
            <div className="flex flex-wrap gap-2">
              <Pill label={String(historicalSignalLab.status || "historical lab waiting")} tone={toneForStatus(String(historicalSignalLab.status || ""))} />
              <Pill label={`${fmtNumber(summary.historical_signal_ready_count, 0)}/${fmtNumber(summary.historical_signal_lane_count, 0)} lanes mapped`} tone="border-yellow-500/30 bg-yellow-500/10 text-yellow-100" />
              <Pill label={`${fmtNumber(summary.lead_lag_candidate_count, 0)} lead/lag`} tone="border-cyan-500/30 bg-cyan-500/10 text-cyan-200" />
            </div>
          </div>
          <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
            <ScrollArea className="h-80 pr-3">
              <div className="grid gap-2 lg:grid-cols-2">
                {historicalReplayLanes.map((lane: JsonMap) => (
                  <div key={String(lane.id || lane.label)} className="rounded-md border border-border/60 bg-background/50 p-3">
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <div className="truncate text-sm font-medium">{String(lane.label || lane.id)}</div>
                        <div className="mt-1 line-clamp-2 text-xs text-muted-foreground">{String(lane.source || "")}</div>
                      </div>
                      <Pill label={String(lane.state || "waiting")} tone={toneForStatus(String(lane.state || ""))} />
                    </div>
                    <div className="mt-2 line-clamp-2 text-xs text-muted-foreground">{String(lane.why_it_matters || "")}</div>
                    <div className="mt-2 line-clamp-2 text-xs text-muted-foreground">{String(lane.next_action || "")}</div>
                  </div>
                ))}
              </div>
            </ScrollArea>
            <div className="grid gap-3">
              <div className="rounded-md border border-border/60 bg-background/50 p-3">
                <div className="flex items-center justify-between gap-2">
                  <div className="text-sm font-medium">Cross-Asset Lead/Lag</div>
                  <Pill label={String(historicalSignalLab.lead_lag_state || "waiting")} tone={toneForStatus(String(historicalSignalLab.lead_lag_state || ""))} />
                </div>
                <div className="mt-2 space-y-2">
                  {leadLagCandidates.slice(0, 3).map((candidate: JsonMap) => (
                    <div key={`${String(candidate.leader)}-${String(candidate.follower)}-${String(candidate.symbol)}`} className="rounded border border-border/40 bg-background/35 p-2 text-xs">
                      <div className="truncate font-medium">{String(candidate.leader || "?")}{" -> "}{String(candidate.follower || candidate.symbol || "?")}</div>
                      <div className="mt-1 text-muted-foreground">corr {fmtNumber(candidate.correlation, 2)} | lag {fmtNumber(candidate.lag_seconds, 0)}s | {String(candidate.relationship_to_gold || "context")}</div>
                    </div>
                  ))}
                </div>
              </div>
              <div className="rounded-md border border-border/60 bg-background/50 p-3">
                <div className="flex items-center justify-between gap-2">
                  <div className="text-sm font-medium">Order-Book Pressure Replay</div>
                  <Pill label={String(summary.orderbook_signal_state || "waiting")} tone={toneForStatus(String(summary.orderbook_signal_state || ""))} />
                </div>
                <div className="mt-2 grid grid-cols-3 gap-2 text-[11px]">
                  <div className="rounded border border-border/40 bg-background/35 p-2">
                    <div className="text-muted-foreground">samples</div>
                    <div className="font-semibold">{fmtNumber(orderbookEvidence.sample_count, 0)}</div>
                  </div>
                  <div className="rounded border border-border/40 bg-background/35 p-2">
                    <div className="text-muted-foreground">direct gold</div>
                    <div className="font-semibold">{fmtNumber(orderbookEvidence.gold_sample_count, 0)}</div>
                  </div>
                  <div className="rounded border border-border/40 bg-background/35 p-2">
                    <div className="text-muted-foreground">available</div>
                    <div className="font-semibold">{fmtNumber(orderbookEvidence.available_count, 0)}</div>
                  </div>
                </div>
                <div className="mt-2 space-y-2">
                  {orderbookSamples.slice(0, 2).map((sample: JsonMap) => (
                    <div key={`${String(sample.symbol)}-${String(sample.side)}-${String(sample.orderbook_alignment)}`} className="rounded border border-border/40 bg-background/35 p-2 text-xs">
                      <div className="truncate font-medium">{String(sample.symbol || "symbol")} {String(sample.side || "")}</div>
                      <div className="mt-1 text-muted-foreground">score {fmtPercent(sample.orderbook_score)} | {String(sample.orderbook_alignment || "alignment")}</div>
                    </div>
                  ))}
                </div>
              </div>
              <div className="rounded-md border border-border/60 bg-background/50 p-3">
                <div className="flex items-center justify-between gap-2">
                  <div className="text-sm font-medium">Chart/OHLC Replay</div>
                  <Pill label={String(summary.chart_replay_state || "waiting")} tone={toneForStatus(String(summary.chart_replay_state || ""))} />
                </div>
                <div className="mt-2 line-clamp-3 text-xs text-muted-foreground">
                  Hypothesis tests: {hypothesisTests.slice(0, 3).map((test: JsonMap) => String(test.id || "test").replace(/_/g, " ")).join(", ") || "waiting for replay tests"}
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="rounded-md border border-border/70 bg-background/35 p-4">
          <div className="mb-3 flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
            <div className="flex items-center gap-2">
              <LineChart className="h-4 w-4 text-yellow-300" />
              <h3 className="text-sm font-semibold">Cross-Market Gold Drivers</h3>
            </div>
            <div className="flex flex-wrap gap-2">
              <Pill label={`${fmtNumber(summary.cross_market_driver_ready_count, 0)}/${fmtNumber(summary.cross_market_driver_count, 0)} ready`} tone="border-yellow-500/30 bg-yellow-500/10 text-yellow-100" />
              <Pill label={`score ${fmtPercent(summary.cross_market_driver_score)}`} tone="border-cyan-500/30 bg-cyan-500/10 text-cyan-200" />
            </div>
          </div>
          <ScrollArea className="h-80 pr-3">
            <div className="grid gap-2 lg:grid-cols-2">
              {crossMarketDrivers.map((driver: JsonMap) => (
                <div key={String(driver.id || driver.label)} className="rounded-md border border-border/60 bg-background/50 p-3">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <div className="truncate text-sm font-medium">{String(driver.label || driver.id)}</div>
                      <div className="mt-1 line-clamp-2 text-xs text-muted-foreground">{String(driver.driver_role || "")}</div>
                    </div>
                    <Pill label={String(driver.driver_state || "driver")} tone={driver.driver_state === "ready_shadow_driver" ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200" : "border-amber-500/30 bg-amber-500/10 text-amber-200"} />
                  </div>
                  <div className="mt-3 grid grid-cols-3 gap-2 text-[11px]">
                    <div className="rounded border border-border/40 bg-background/35 p-2">
                      <div className="text-muted-foreground">score</div>
                      <div className="font-semibold">{fmtPercent(driver.score)}</div>
                    </div>
                    <div className="rounded border border-border/40 bg-background/35 p-2">
                      <div className="text-muted-foreground">assets</div>
                      <div className="font-semibold">{fmtNumber(driver.asset_hit_count, 0)}</div>
                    </div>
                    <div className="rounded border border-border/40 bg-background/35 p-2">
                      <div className="text-muted-foreground">fresh</div>
                      <div className="font-semibold">{driver.fresh ? "yes" : "no"}</div>
                    </div>
                  </div>
                  <div className="mt-2 line-clamp-2 text-xs text-muted-foreground">{String(driver.next_action || "")}</div>
                </div>
              ))}
            </div>
          </ScrollArea>
        </section>

        <section className="rounded-md border border-border/70 bg-background/35 p-4">
          <div className="mb-3 flex items-center gap-2">
            <Radio className="h-4 w-4 text-blue-300" />
            <h3 className="text-sm font-semibold">Tool Activation Plan</h3>
          </div>
          <div className="grid gap-3 lg:grid-cols-4">
            {toolActivationPlan.slice(0, 8).map((item: JsonMap) => (
              <div key={String(item.id || item.phase)} className="rounded-md border border-border/60 bg-background/50 p-3">
                <div className="truncate text-sm font-medium">{String(item.phase || item.id || "phase").replace(/_/g, " ")}</div>
                <div className="mt-1 line-clamp-2 text-xs text-muted-foreground">{String(item.expected_output || "")}</div>
                <div className="mt-2 flex flex-wrap gap-1">
                  {(Array.isArray(item.tools) ? item.tools : []).slice(0, 4).map((tool: string) => (
                    <Pill key={tool} label={String(tool).replace(/_/g, " ")} />
                  ))}
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-md border border-border/70 bg-background/35 p-4">
          <div className="mb-3 flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-emerald-300" />
              <h3 className="text-sm font-semibold">Evidence And Reference Packets</h3>
            </div>
            <a className="inline-flex items-center gap-2 text-xs text-cyan-200 hover:text-cyan-100" href={REPORT_URL} target="_blank" rel="noreferrer">
              Open public report
              <ExternalLink className="h-3.5 w-3.5" />
            </a>
          </div>
          <div className="grid gap-3 lg:grid-cols-2">
            <div className="space-y-2">
              {sourceEvidence.slice(0, 5).map((source: JsonMap) => (
                <div key={String(source.id || source.path)} className="rounded-md border border-border/60 bg-background/50 p-3">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <div className="truncate text-sm font-medium">{String(source.id || "source")}</div>
                      <div className="mt-1 truncate text-xs text-muted-foreground">{String(source.status || "present")}</div>
                    </div>
                    <Pill label={source.present ? "present" : "missing"} tone={source.present ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200" : "border-red-500/30 bg-red-500/10 text-red-200"} />
                  </div>
                </div>
              ))}
            </div>
            <div className="space-y-2">
              {[...sourcePackets, ...localResearchPackets].slice(0, 8).map((packet: JsonMap) => (
                <div key={String(packet.title || packet.id || packet.source_url || packet.path)} className="rounded-md border border-border/60 bg-background/50 p-3">
                  <div className="truncate text-sm font-medium">{String(packet.title || packet.id || "reference packet")}</div>
                  <div className="mt-1 line-clamp-2 text-xs text-muted-foreground">{String(packet.guidance || "")}</div>
                  {packet.source_url ? (
                    <a className="mt-2 inline-flex items-center gap-1 text-xs text-cyan-200 hover:text-cyan-100" href={String(packet.source_url)} target="_blank" rel="noreferrer">
                      reference only <ExternalLink className="h-3 w-3" />
                    </a>
                  ) : null}
                </div>
              ))}
            </div>
          </div>
        </section>

        <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
          <RefreshCw className="h-3.5 w-3.5" />
          <span>Evidence refreshes from {REPORT_URL}. This panel does not place trades, reveal credentials, or mutate Capital.com state.</span>
        </div>
      </CardContent>
    </Card>
  );
}
