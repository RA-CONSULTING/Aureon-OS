import { type ReactNode, useEffect, useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  Brain,
  Calculator,
  Clock,
  Database,
  Eye,
  FileText,
  Gauge,
  LineChart,
  Lock,
  Map,
  Radio,
  RefreshCcw,
  Search,
  Server,
  Settings,
  ShieldCheck,
} from "lucide-react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "@/components/theme-provider";
import { TooltipProvider } from "@/components/ui/tooltip";
import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { AureonGeneratedOperationalConsole } from "@/components/generated/AureonGeneratedOperationalConsole";
import { AureonWorkOrderExecutionConsole } from "@/components/generated/AureonWorkOrderExecutionConsole";
import { AureonCodingAgentSkillBaseConsole } from "@/components/generated/AureonCodingAgentSkillBaseConsole";
import { AureonCodingOrganismConsole } from "@/components/generated/AureonCodingOrganismConsole";
import { AureonDirectorCapabilityBridgeConsole } from "@/components/generated/AureonDirectorCapabilityBridgeConsole";
import { AureonAgentCompanyConsole } from "@/components/generated/AureonAgentCompanyConsole";
import { AureonGoldCapitalIntelligenceConsole } from "@/components/generated/AureonGoldCapitalIntelligenceConsole";
import { ExchangeCredentialsManager } from "@/components/ExchangeCredentialsManager";
import { RepoNavigationPanel } from "@/components/RepoNavigationPanel";
import {
  CapabilitySwitchboardManifest,
  FrontendScreenPlan,
  FrontendEvolutionQueueManifest,
  loadUnifiedFrontendState,
  OrganismDomainPulse,
  SaaSInventoryManifest,
  SaaSInventorySummary,
  surfacesForScreen,
  UnifiedFrontendState,
} from "@/services/aureonAutonomousFrontend";

const queryClient = new QueryClient();
const ENV_LOCAL_TERMINAL_ENDPOINT = import.meta.env.VITE_LOCAL_TERMINAL_URL as string | undefined;
const DEFAULT_RUNTIME_ENDPOINTS = [
  ENV_LOCAL_TERMINAL_ENDPOINT,
  "/api/terminal-state", // production: nginx proxies /api to the gateway
  "http://127.0.0.1:8791/api/terminal-state",
  "http://127.0.0.1:8790/api/terminal-state",
].filter((value): value is string => Boolean(value));
const MANIFEST_REFRESH_MS = 15000;
const RUNTIME_REFRESH_MS = 2500;
const FAST_PANEL_REFRESH_MS = 5000;
const MARKET_PANEL_REFRESH_MS = 7500;
const UI_CLOCK_REFRESH_MS = 5000;

interface RuntimeObservation {
  connected: boolean;
  clearancePending: boolean;
  endpoint?: string;
  generatedAt?: string;
  stale?: boolean;
  staleReason?: string;
  statusLines: string[];
  metrics: Array<{ label: string; value: string }>;
  clearances: string[];
  details: Array<{ label: string; value: string }>;
  data?: Record<string, unknown>;
  flight?: Record<string, unknown>;
  goldRuntimeTradeProof?: Record<string, unknown>;
}

interface TradingIntelligenceChecklistRow {
  system: string;
  category: string;
  facet: string;
  wire_path: string;
  evidence_source: string;
  last_timestamp?: string;
  present: boolean;
  active_this_cycle: boolean;
  fresh: boolean;
  usable_for_decision: boolean;
  fed_to_decision_logic: boolean;
  blocker?: string;
  downstream_stage: string;
}

interface TradingIntelligenceChecklist {
  status?: string;
  generated_at?: string;
  summary?: {
    runtime_fresh?: boolean;
    runtime_stale?: boolean;
    stale_reason?: string;
    system_count?: number;
    present_count?: number;
    active_count?: number;
    fresh_usable_count?: number;
    stale_or_blocked_count?: number;
    decision_fed_count?: number;
    direct_live_systems_passing?: number;
    hnc_auris_passing?: number;
    counter_intelligence_passing?: number;
    profit_timing_passing?: number;
    metacognitive_context_passing?: number;
    metacognitive_data_context?: {
      present?: boolean;
      usable_for_metacognition?: boolean;
      usable_for_live_decision?: boolean;
      decision_blocker?: string;
      mapping_complete?: boolean;
      coverage_percent?: number;
      configured_reachable_source_count?: number;
      usable_source_count?: number;
      decision_usable_source_count?: number;
      active_live_source_count?: number;
      fresh_exchange_count?: number;
      waveform_history_exchange_count?: number;
      live_ticker_count?: number;
      history_rows?: number;
      fresh_domain_count?: number;
      usable_domain_count?: number;
      cognitive_cleanliness_score?: number;
      planetary_context_ready?: boolean;
      exchange_waveform_ready?: boolean;
      state_phrase?: string;
      evidence_sources?: string[];
    };
    evidence_self_trust_score?: number;
    decision_self_trust_score?: number;
    decision_posture?: string;
    trust_to_decide?: boolean;
    trust_to_shadow?: boolean;
    trust_to_act?: boolean;
    top_blockers?: Array<Record<string, unknown>>;
  };
  decision_trust?: {
    evidence_self_trust_score?: number;
    live_action_trust_score?: number;
    trust_to_decide?: boolean;
    trust_to_shadow?: boolean;
    trust_to_act?: boolean;
    posture?: string;
    synthetic_affect_state?: string;
    not_fear_reason?: string;
    self_instruction?: string;
  };
  rows?: TradingIntelligenceChecklistRow[];
}

interface ExchangeMonitoringChecklistRow {
  exchange: string;
  label: string;
  markets?: string[];
  connected: boolean;
  cache_present: boolean;
  cache_active: boolean;
  cache_fresh: boolean;
  ticker_count: number;
  action_plan_venue_count: number;
  known_venues?: string[];
  waveform_history_active: boolean;
  feeds_decision_logic: boolean;
  usable_for_fast_money: boolean;
  monitored_now?: string[];
  missing?: string[];
  required_for_fast_money?: string[];
  last_timestamp?: string | number;
  age_sec?: number | null;
}

interface ExchangeMonitoringChecklist {
  status?: string;
  generated_at?: string;
  summary?: {
    runtime_stale?: boolean;
    stale_reason?: string;
    exchange_count?: number;
    connected_exchange_count?: number;
    active_exchange_count?: number;
    fresh_exchange_count?: number;
    decision_fed_exchange_count?: number;
    fast_money_usable_exchange_count?: number;
    waveform_history_exchange_count?: number;
    total_tickers_monitored?: number;
    top_missing?: Array<Record<string, unknown>>;
  };
  rows?: ExchangeMonitoringChecklistRow[];
}

interface ExchangeDataCapabilityRow {
  exchange: string;
  label: string;
  system_role?: string;
  markets?: string[];
  trading_modes?: string[];
  data_channels?: Array<{
    name: string;
    source?: string;
    status?: string;
    optimization_use?: string;
  }>;
  leveraged_for?: string[];
  optimization_bias?: string;
  current_state?: {
    connected?: boolean;
    active_feed?: boolean;
    fresh_feed?: boolean;
    ticker_count?: number;
    decision_fed?: boolean;
    fast_money_usable?: boolean;
    waveform_history_active?: boolean;
    credential_state?: string;
    usable_for_mapping?: boolean;
    usable_for_decision?: boolean;
  };
  optimization_policy?: {
    safe_calls_per_min?: number;
    execution_reserved_per_min?: number;
    market_data_budget_per_min?: number;
    cash_usd_estimate?: number;
    position_count?: number;
    cash_or_position_active?: boolean;
    data_boost_eligible?: boolean;
    stream_preferred?: boolean;
    recommended_mode?: string;
  };
  gaps?: string[];
  next_optimization?: string;
}

interface ExchangeDataCapabilityMatrix {
  status?: string;
  generated_at?: string;
  summary?: {
    exchange_count?: number;
    connected_exchange_count?: number;
    fresh_feed_count?: number;
    decision_fed_count?: number;
    fast_money_usable_count?: number;
    waveform_ready_count?: number;
    cash_active_exchange_count?: number;
    data_boost_eligible_count?: number;
    official_rate_limit_profile_count?: number;
    total_ticker_count?: number;
    runtime_stale?: boolean;
    runtime_booting?: boolean;
    trading_ready?: boolean;
    data_ready?: boolean;
    preflight_overall?: string;
    stale_reason?: string;
  };
  rows?: ExchangeDataCapabilityRow[];
}

interface GlobalFinancialCoverageRow {
  domain: string;
  coverage: string;
  live_count: number;
  history_count: number;
  fresh: boolean;
  usable: boolean;
  missing?: string[];
  next_action?: string;
}

interface DataOceanSourceStatus {
  source_id: string;
  title: string;
  category: string;
  asset_classes?: string[];
  credential_state: string;
  active: boolean;
  fresh: boolean;
  usable_for_mapping: boolean;
  usable_for_decision?: boolean;
  decision_blocker?: string;
  row_count: number;
  governor_action: string;
  reason?: string;
  next_action?: string;
}

interface GlobalFinancialCoverageMap {
  status?: string;
  generated_at?: string;
  summary?: {
    domain_count?: number;
    usable_domain_count?: number;
    fresh_domain_count?: number;
    live_ticker_count?: number;
    active_live_source_count?: number;
    fresh_exchange_count?: number;
    decision_fed_exchange_count?: number;
    history_db_present?: boolean;
    history_db_size_bytes?: number;
    total_history_rows?: number;
    source_count?: number;
    configured_reachable_source_count?: number;
    usable_source_count?: number;
    decision_usable_source_count?: number;
    fresh_source_count?: number;
    credential_missing_source_count?: number;
    coverage_percent?: number;
    accounted_percent?: number;
    mapping_complete?: boolean;
    top_missing?: Array<Record<string, unknown>>;
  };
  rows?: GlobalFinancialCoverageRow[];
  source_registry?: DataOceanSourceStatus[];
}

interface HNCPacketSecurityComparison {
  status?: string;
  generated_at?: string;
  summary?: {
    current_hnc_score?: number;
    current_swarm_score?: number;
    current_hnc_rating?: string;
    current_swarm_rating?: string;
    compared_methods?: number;
    beats_plaintext_by?: number;
    below_os_keychain_by?: number;
    below_kms_hsm_by?: number;
    breaker_passed?: boolean;
    swarm_breaker_passed?: boolean;
    swarm_beats_hnc_by?: number;
    swarm_below_kms_hsm_by?: number;
    main_weakness?: string;
    top_recommendation?: string;
  };
  rows?: Array<{
    method: string;
    score: number;
    category?: string;
    confidentiality?: string;
    integrity?: string;
    key_management?: string;
    aureon_fit?: string;
    limitation?: string;
  }>;
}

interface WakeUpManifest {
  runtime_feed_url?: string;
  runtime_flight_test_url?: string;
  runtime_reboot_advice_url?: string;
}

interface LiveGoalTradeAudit {
  status?: string;
  generated_at?: string;
  mode?: string;
  data_capture?: {
    state?: string;
    age_sec?: number | null;
    fresh_for_order_action?: boolean;
    source_count?: number;
    active_source_count?: number;
    ticker_count?: number;
    gold_related_ticker_count?: number;
    supporting_ticker_count?: number;
    gold_related_tickers?: Array<Record<string, unknown>>;
    blockers?: string[];
  };
  capital_gold_profile?: {
    state?: string;
    gold_asset_count?: number;
    best_gold_asset?: Record<string, unknown>;
    blockers?: string[];
  };
  order_intent_proof?: {
    state?: string;
    intent_count?: number;
    fresh_intent_count?: number;
    gold_intent_count?: number;
    intent_packet_fresh?: boolean;
    non_gold_intents_rejected_for_gold_proof?: boolean;
    best_gold_intent?: Record<string, unknown>;
    latest_intents?: Array<Record<string, unknown>>;
    blockers?: string[];
  };
  runtime_candidate_proof?: {
    gold_runtime_candidate_ready?: boolean;
    capital_cfd_route_visible?: boolean;
    capital_cfd_route_ready?: boolean;
    gold_intent_publish_reason?: string;
    intent_packet_fresh?: boolean;
    gold_runtime_trade_proof?: Record<string, unknown>;
    runtime_stall_diagnostic?: Record<string, unknown>;
  };
  executor_gate?: {
    state?: string;
    trading_ready?: boolean;
    data_ready?: boolean;
    stale?: boolean;
    stale_reason?: string;
    tick_phase?: string;
    trade_path_state?: string;
    executor_enabled?: boolean;
    live_action_clearance?: string;
    blockers?: string[];
    attempted_count?: number;
    submitted_count?: number;
    held_count?: number;
    blocked_count?: number;
  };
  order_lifecycle_proof?: {
    state?: string;
    present?: boolean;
    event_count?: number;
    lifecycle_count?: number;
    active_lifecycle_count?: number;
    completed_lifecycle_count?: number;
    latest_status?: string;
    latest_lifecycle_id?: string;
    latest_deal_id?: string;
    active_lifecycles?: Array<Record<string, unknown>>;
    missing_links?: string[];
    blockers?: string[];
    snapshot?: Record<string, unknown>;
  };
  order_lifecycle_stress_proof?: {
    state?: string;
    present?: boolean;
    generated_at?: string;
    status?: string;
    case_count?: number;
    passed_count?: number;
    failed_count?: number;
    requirement_count?: number;
    covered_requirement_count?: number;
    coverage_percent?: number;
    capital_gold_path_certified?: boolean;
    duplicate_route_blocked?: boolean;
    restart_recovery_certified?: boolean;
    close_verification_enforced?: boolean;
    partial_fill_certified?: boolean;
    failure_state_mapping_certified?: boolean;
    no_live_mutation?: boolean;
    no_ui_mutation_controls?: boolean;
    mock_broker_status?: string;
    mock_broker_certified?: boolean;
    sandbox_paper_status?: string;
    sandbox_paper_certified?: boolean;
    sandbox_paper_case_count?: number;
    sandbox_paper_passed_count?: number;
    sandbox_paper_requirement_count?: number;
    sandbox_paper_covered_requirement_count?: number;
    sandbox_environment_guard_passed?: boolean;
    sandbox_no_production_order_endpoints?: boolean;
    sandbox_probe_mode?: string;
    sandbox_paper_missing_requirements?: string[];
    sandbox_paper_blockers?: string[];
    proof_tiers?: Record<string, Record<string, unknown>>;
    missing_requirements?: string[];
    blockers?: string[];
    cases?: Array<Record<string, unknown>>;
    sandbox_paper_cases?: Array<Record<string, unknown>>;
    sandbox_paper_requirements?: Array<Record<string, unknown>>;
    snapshot?: Record<string, unknown>;
  };
  live_trade_signal_fabric_proof?: {
    state?: string;
    present?: boolean;
    generated_at?: string;
    status?: string;
    thoughtbus_receiving?: boolean;
    mycelium_receiving?: boolean;
    active_trace_count?: number;
    complete_trace_count?: number;
    broken_trace_count?: number;
    live_order_submitted_count?: number;
    broker_ack_count?: number;
    position_open_count?: number;
    outcome_recorded_count?: number;
    p95_phase_latency_ms?: number;
    api_rate_pressure_count?: number;
    latest_live_trade_trace?: Record<string, unknown>;
    blockers?: string[];
    snapshot?: Record<string, unknown>;
  };
  live_trade_signal_fabric_stress_proof?: {
    state?: string;
    present?: boolean;
    generated_at?: string;
    status?: string;
    trace_count?: number;
    certified_trace_count?: number;
    complete_trace_count?: number;
    broken_chain_count?: number;
    broker_requirement_gap_count?: number;
    rate_budget_missing_count?: number;
    api_rate_pressure_count?: number;
    stale_trace_count?: number;
    bus_delivery_count?: number;
    mycelium_delivery_count?: number;
    blockers?: string[];
    snapshot?: Record<string, unknown>;
  };
  goal_trade_proof?: {
    proof_state?: string;
    live_trade_produced?: boolean;
    live_trade_attempted?: boolean;
    gold_order_intent_ready?: boolean;
    intent_packet_fresh?: boolean;
    gold_runtime_candidate_ready?: boolean;
    capital_cfd_route_visible?: boolean;
    capital_cfd_route_ready?: boolean;
    gold_intent_publish_reason?: string;
    fresh_data_ready?: boolean;
    executor_ready?: boolean;
    dry_run_executor_proof_ready?: boolean;
    handover_ready?: boolean;
    blockers?: string[];
    next_action?: string;
  };
  capital_3p_live_execution_certification_proof?: Record<string, unknown>;
  capital_3p_blocker_burndown_proof?: Record<string, unknown>;
  performance_readiness_proof?: Record<string, unknown>;
}

interface OrderLifecycleStressAudit {
  status?: string;
  generated_at?: string;
  mode?: string;
  summary?: {
    case_count?: number;
    passed_count?: number;
    failed_count?: number;
    requirement_count?: number;
    covered_requirement_count?: number;
    coverage_percent?: number;
    venue_count?: number;
    capital_gold_path_certified?: boolean;
    duplicate_route_blocked?: boolean;
    restart_recovery_certified?: boolean;
    multi_venue_recovery_certified?: boolean;
    close_verification_enforced?: boolean;
    partial_fill_certified?: boolean;
    stale_broker_proof_blocked?: boolean;
    failure_state_mapping_certified?: boolean;
    broker_requirement_matrix_complete?: boolean;
    no_live_mutation?: boolean;
    no_ui_mutation_controls?: boolean;
    mock_broker_status?: string;
    mock_broker_certified?: boolean;
    sandbox_paper_status?: string;
    sandbox_paper_certified?: boolean;
    sandbox_paper_case_count?: number;
    sandbox_paper_passed_count?: number;
    sandbox_paper_requirement_count?: number;
    sandbox_paper_covered_requirement_count?: number;
    sandbox_environment_guard_passed?: boolean;
    sandbox_no_production_order_endpoints?: boolean;
    sandbox_probe_mode?: string;
    sandbox_paper_missing_requirements?: string[];
    sandbox_paper_blockers?: string[];
    proof_tiers?: Record<string, Record<string, unknown>>;
    broker_correlation_fields?: string[];
    broker_requirement_matrix_by_venue?: Record<string, Record<string, unknown>>;
    blocker_count?: number;
  };
  blockers?: string[];
  missing_requirements?: string[];
  requirements?: Array<Record<string, unknown>>;
  cases?: Array<Record<string, unknown>>;
  sandbox_paper_cases?: Array<Record<string, unknown>>;
  sandbox_paper_requirements?: Array<Record<string, unknown>>;
  proof_tiers?: Record<string, Record<string, unknown>>;
  manual_boundaries?: string[];
  sandbox_manual_boundaries?: string[];
}

interface CapitalEcosystemIntelligenceCompany {
  status?: string;
  generated_at?: string;
  mode?: string;
  goal?: Record<string, unknown>;
  summary?: {
    three_p_goal?: number;
    candidate_count?: number;
    trade_ready_candidate_count?: number;
    net_positive_candidate_count?: number;
    revenue_intent_candidate_count?: number;
    three_p_intent_eligible_count?: number;
    false_positive_reject_count?: number;
    active_watchlist_count?: number;
    active_watchlist_limit?: number;
    bench_watchlist_count?: number;
    bench_watchlist_limit?: number;
    gold_preserved?: boolean;
    shadow_hedge_count?: number;
    shadow_hedges_only?: boolean;
    close_first_opportunity_count?: number;
    three_p_close_opportunity_count?: number;
    active_capital_position_count?: number;
    active_lifecycle_route_count?: number;
    duplicate_route_blocked_count?: number;
    top_velocity_score?: number;
    blocker_count?: number;
    no_external_hedge_mutation?: boolean;
    existing_runtime_gates_authoritative?: boolean;
  };
  watchlists?: {
    active_stream_watchlist?: Array<Record<string, unknown>>;
    bench_watchlist?: Array<Record<string, unknown>>;
    active_symbols?: string[];
    bench_symbols?: string[];
    active_limit?: number;
    bench_limit?: number;
  };
  top_velocity_candidates?: Array<Record<string, unknown>>;
  shadow_hedges?: Array<Record<string, unknown>>;
  close_first_opportunities?: Array<Record<string, unknown>>;
  lifecycle?: Record<string, unknown>;
  blockers?: string[];
  manual_boundaries?: string[];
}

interface CapitalRevenueLogicStressAudit {
  status?: string;
  generated_at?: string;
  mode?: string;
  summary?: {
    three_p_goal?: number;
    candidate_count?: number;
    trade_ready_candidate_count?: number;
    net_positive_candidate_count?: number;
    three_p_floor_passed_count?: number;
    intent_eligible_candidate_count?: number;
    candidate_level_intent_eligible_count?: number;
    three_p_intent_eligible_count?: number;
    false_positive_reject_count?: number;
    active_watchlist_count?: number;
    bench_watchlist_count?: number;
    close_first_opportunity_count?: number;
    three_p_close_opportunity_count?: number;
    active_capital_position_count?: number;
    duplicate_route_blocked_count?: number;
    shadow_confirmation_count?: number;
    external_shadow_only?: boolean;
    live_gates_blocking?: boolean;
    capital_live_gates_armed?: boolean;
    no_live_mutation?: boolean;
  };
  candidate_revenue_proof?: Record<string, unknown>;
  net_positive_candidates?: Array<Record<string, unknown>>;
  rejected_false_positives?: Array<Record<string, unknown>>;
  capital_order_intent_readiness?: Record<string, unknown>;
  external_confirmation_proof?: Record<string, unknown>;
  close_first_proof?: Record<string, unknown>;
  lifecycle_proof?: Record<string, unknown>;
  runtime_gate_proof?: Record<string, unknown>;
  blockers?: string[];
  manual_boundaries?: string[];
  source_paths?: Record<string, unknown>;
}

interface CapitalRevenueLiveGateReadinessAudit {
  status?: string;
  generated_at?: string;
  mode?: string;
  summary?: {
    three_p_goal?: number;
    net_positive_candidate_count?: number;
    ready_now_candidate_count?: number;
    three_p_ready_candidate_count?: number;
    blocked_candidate_count?: number;
    missing_gate_count?: number;
    runtime_gates_clear?: boolean;
    capital_live_gates_armed?: boolean;
    recovered_exit_clear?: boolean;
    duplicate_routes_blocked?: boolean;
    broker_correlation_complete?: boolean;
    external_shadow_only?: boolean;
    no_live_mutation?: boolean;
  };
  current_live_gate_readiness?: Record<string, unknown>;
  candidate_readiness_rows?: Array<Record<string, unknown>>;
  gate_clear_stress_cases?: Array<Record<string, unknown>>;
  broker_requirement_baseline?: Record<string, unknown>;
  runtime_gate_proof?: Record<string, unknown>;
  lifecycle_gate_proof?: Record<string, unknown>;
  close_first_exit_proof?: Record<string, unknown>;
  external_confirmation_proof?: Record<string, unknown>;
  blockers?: string[];
  manual_boundaries?: string[];
  source_paths?: Record<string, unknown>;
}

interface CapitalThreePLiveExecutionCertificationAudit {
  status?: string;
  generated_at?: string;
  mode?: string;
  summary?: {
    three_p_goal?: number;
    net_positive_candidate_count?: number;
    ready_for_intent_count?: number;
    fresh_snapshot_candidate_count?: number;
    duplicate_route_blocked_count?: number;
    recovered_position_count?: number;
    recovered_exit_clear?: boolean;
    capital_live_gates_armed?: boolean;
    executor_ready?: boolean;
    broker_correlation_complete?: boolean;
    capital_broker_requirements_certified?: boolean;
    external_confirmation_shadow_only?: boolean;
    no_external_mutation?: boolean;
    no_live_mutation?: boolean;
    blocker_count?: number;
  };
  candidate_execution_rows?: Array<Record<string, unknown>>;
  fresh_snapshot_proof?: Record<string, unknown>;
  duplicate_route_proof?: Record<string, unknown>;
  recovered_exit_proof?: Record<string, unknown>;
  capital_broker_requirement_proof?: Record<string, unknown>;
  external_confirmation_requirement_proof?: Record<string, unknown>;
  live_executor_readiness?: Record<string, unknown>;
  blockers?: string[];
  manual_boundaries?: string[];
  source_paths?: Record<string, unknown>;
}

interface CapitalThreePBlockerBurndownAudit {
  status?: string;
  generated_at?: string;
  mode?: string;
  summary?: {
    three_p_goal?: number;
    candidate_count?: number;
    ready_for_capital_intent_count?: number;
    fresh_snapshot_candidate_count?: number;
    stale_snapshot_candidate_count?: number;
    duplicate_route_blocked_count?: number;
    recovered_position_count?: number;
    recovered_exit_clear?: boolean;
    external_live_intent_count?: number;
    external_executor_attempt_count?: number;
    external_live_route_leak?: boolean;
    runtime_artifact_mismatch?: boolean;
    capital_only_live_execution?: boolean;
    shadow_confirmation_count?: number;
    live_gates_armed?: boolean;
    no_broker_mutation_from_audit?: boolean;
    blocker_count?: number;
  };
  candidate_burndown_rows?: Array<Record<string, unknown>>;
  fresh_snapshot_proof?: Record<string, unknown>;
  duplicate_route_proof?: Record<string, unknown>;
  recovered_exit_proof?: Record<string, unknown>;
  capital_only_execution_guard?: Record<string, unknown>;
  external_confirmation_rows?: Array<Record<string, unknown>>;
  runtime_reconciliation?: Record<string, unknown>;
  blockers?: string[];
  manual_boundaries?: string[];
  source_paths?: Record<string, unknown>;
}

interface PerformanceReadinessAudit {
  status?: string;
  generated_at?: string;
  mode?: string;
  summary?: {
    script_count?: number;
    scripts_wired_count?: number;
    organism_registered_count?: number;
    artifact_count?: number;
    artifact_present_count?: number;
    super_sweep_pass?: boolean;
    super_sweep_steps?: string;
    full_suite_pass?: boolean;
    latency_stress_pass?: boolean;
    latency_p95_observed_ms?: number;
    latency_p95_budget_ms?: number;
    threshold_pass_cases?: number;
    threshold_fail_cases?: number;
    api_concurrency_valid_exchange_count?: number;
    api_concurrency_total_recommended_calls_per_min?: number;
    api_rate_benchmark_valid_exchange_count?: number;
    no_broker_mutation?: boolean;
    blocker_count?: number;
  };
  script_wiring?: Array<Record<string, unknown>>;
  artifact_wiring?: Record<string, unknown>;
  blockers?: string[];
  manual_boundaries?: string[];
  source_paths?: Record<string, unknown>;
}

interface AureonMurgeUnityBridge {
  status?: string;
  generated_at?: string;
  mode?: string;
  summary?: {
    track_count?: number;
    staged_track_count?: number;
    missing_track_count?: number;
    adapter_row_count?: number;
    collision_count?: number;
    online_requirement_count?: number;
    unity_ready?: boolean;
    hidden_activation?: boolean;
  };
  unity_track_rows?: Array<Record<string, unknown>>;
  organism_adapter_rows?: Array<Record<string, unknown>>;
  collision_rows?: Array<Record<string, unknown>>;
  online_requirement_baseline?: Array<Record<string, unknown>>;
  next_unity_actions?: Array<Record<string, unknown>>;
  blockers?: string[];
  manual_boundaries?: string[];
  source_paths?: Record<string, unknown>;
}

interface AureonMurgeRuntimeActivationStressAudit {
  status?: string;
  generated_at?: string;
  mode?: string;
  summary?: {
    service_count?: number;
    service_present_count?: number;
    service_health_pass_count?: number;
    dependency_ready_count?: number;
    dependency_check_count?: number;
    npm_audit_present_count?: number;
    npm_high_vulnerability_count?: number;
    npm_critical_vulnerability_count?: number;
    local_launch_ready?: boolean;
    web_health_passed?: boolean;
    runtime_health_passed?: boolean;
    desktop_gate_enabled?: boolean;
    activation_gate_enabled_count?: number;
    terminal_guard_count?: number;
    terminal_guard_passing_count?: number;
    electron_security_pass_count?: number;
    electron_security_check_count?: number;
    windows_launcher_present?: boolean;
    host_bash_assumption_removed?: boolean;
    collision_count?: number;
    unity_ready?: boolean;
    thoughtbus_mycelium_required?: boolean;
    blocker_count?: number;
    no_trading_gate_bypass?: boolean;
    no_cloud_deploy?: boolean;
    no_credential_migration?: boolean;
  };
  activation_service_rows?: Array<Record<string, unknown>>;
  activation_gate_rows?: Array<Record<string, unknown>>;
  package_readiness_rows?: Array<Record<string, unknown>>;
  dependency_readiness_rows?: Array<Record<string, unknown>>;
  launch_log_rows?: Array<Record<string, unknown>>;
  npm_audit_rows?: Array<Record<string, unknown>>;
  windows_compatibility_rows?: Array<Record<string, unknown>>;
  terminal_sandbox_guard_rows?: Array<Record<string, unknown>>;
  electron_security_rows?: Array<Record<string, unknown>>;
  online_requirement_baseline?: Array<Record<string, unknown>>;
  unity_collision_rows?: Array<Record<string, unknown>>;
  fabric_visibility_proof?: Record<string, unknown>;
  next_activation_actions?: Array<Record<string, unknown>>;
  blockers?: string[];
  manual_boundaries?: string[];
  source_paths?: Record<string, unknown>;
}

interface LiveTradeSignalFabric {
  status?: string;
  generated_at?: string;
  mode?: string;
  summary?: {
    event_count?: number;
    thoughtbus_receiving?: boolean;
    mycelium_receiving?: boolean;
    active_trace_count?: number;
    complete_trace_count?: number;
    broken_trace_count?: number;
    live_order_submitted_count?: number;
    broker_ack_count?: number;
    position_open_count?: number;
    outcome_recorded_count?: number;
    p95_phase_latency_ms?: number;
    api_rate_pressure_count?: number;
  };
  thoughtbus_proof?: Record<string, unknown>;
  mycelium_proof?: Record<string, unknown>;
  active_traces?: Array<Record<string, unknown>>;
  phase_counts?: Record<string, number>;
  broken_chains?: Array<Record<string, unknown>>;
  rate_pressure?: Array<Record<string, unknown>>;
  latest_live_trade_trace?: Record<string, unknown>;
  source_paths?: Record<string, unknown>;
}

interface LiveTradeSignalFabricStressAudit {
  status?: string;
  generated_at?: string;
  mode?: string;
  summary?: {
    event_count?: number;
    trace_count?: number;
    certified_trace_count?: number;
    complete_trace_count?: number;
    broken_chain_count?: number;
    missing_required_phase_count?: number;
    stable_id_gap_count?: number;
    broker_requirement_gap_count?: number;
    rate_budget_missing_count?: number;
    api_rate_pressure_count?: number;
    stale_trace_count?: number;
    bus_delivery_count?: number;
    mycelium_delivery_count?: number;
    thoughtbus_receiving?: boolean;
    mycelium_receiving?: boolean;
    p95_phase_latency_ms?: number;
    no_broker_mutation?: boolean;
    burn_down_ready?: boolean;
    chain_certification_state?: string;
    capital_a_to_b_ready?: boolean;
    recovered_trace_count?: number;
    publisher_gap_count?: number;
    api_budget_gap_count?: number;
    broker_gap_count?: number;
    complete_capital_chain_count?: number;
    producer_repair_row_count?: number;
    rate_budget_certified_count?: number;
    rate_budget_uncertified_count?: number;
    recovered_broker_truth_count?: number;
    external_live_route_leak_count?: number;
    executor_gate_respected?: boolean;
    no_direct_broker_mutation?: boolean;
    producer_burndown_state?: string;
    producer_wired_count?: number;
    producer_silent_count?: number;
    producer_rate_missing_count?: number;
    publisher_owner?: string;
    dedupe_applied?: boolean;
    dedupe_applied_count?: number;
    session_scope?: Record<string, unknown>;
    session_broken_trace_count?: number;
    session_api_budget_gap_count?: number;
    session_complete_capital_chain_count?: number;
    session_external_live_route_leak_count?: number;
    speed_scope?: string;
    speed_real_data_only_mode?: boolean;
    speed_trace_count?: number;
    speed_session_trace_count?: number;
    speed_complete_to_position_count?: number;
    speed_session_complete_to_position_count?: number;
    speed_outcome_recorded_count?: number;
    speed_session_outcome_recorded_count?: number;
    speed_positive_gain_count?: number;
    speed_session_positive_gain_count?: number;
    speed_a_to_b_fastest_ms?: number;
    speed_a_to_b_p50_ms?: number;
    speed_a_to_b_p95_ms?: number;
    speed_a_to_gain_fastest_ms?: number;
    speed_a_to_gain_p50_ms?: number;
    speed_a_to_gain_p95_ms?: number;
    speed_round_trip_to_outcome_fastest_ms?: number;
    speed_round_trip_to_outcome_p50_ms?: number;
    speed_round_trip_to_outcome_p95_ms?: number;
    speed_repeat_cycle_fastest_ms?: number;
    speed_repeat_cycle_p50_ms?: number;
    speed_repeat_cycle_p95_ms?: number;
    speed_latest_state?: string;
    speed_current_answer?: string;
  };
  trace_certification_rows?: Array<Record<string, unknown>>;
  burn_down_rows?: Array<Record<string, unknown>>;
  producer_repair_rows?: Array<Record<string, unknown>>;
  producer_wiring_rows?: Array<Record<string, unknown>>;
  publisher_heartbeat_rows?: Array<Record<string, unknown>>;
  next_live_trace_requirements?: Array<Record<string, unknown>>;
  fresh_capital_trace_candidate?: Record<string, unknown>;
  producer_burndown_state?: string;
  rate_budget_certification_rows?: Array<Record<string, unknown>>;
  recovered_broker_truth_rows?: Array<Record<string, unknown>>;
  chain_certification_state?: string;
  capital_a_to_b_ready?: boolean;
  recovered_trace_rows?: Array<Record<string, unknown>>;
  publisher_gap_rows?: Array<Record<string, unknown>>;
  api_budget_gap_rows?: Array<Record<string, unknown>>;
  broker_requirement_gap_rows?: Array<Record<string, unknown>>;
  next_repair_actions?: Array<Record<string, unknown>>;
  broker_requirement_proof?: Record<string, unknown>;
  phase_order_proof?: Record<string, unknown>;
  api_rate_budget_proof?: Record<string, unknown>;
  bus_mycelium_proof?: Record<string, unknown>;
  stale_phase_proof?: Record<string, unknown>;
  session_scope?: Record<string, unknown>;
  session_trace_rows?: Array<Record<string, unknown>>;
  session_broken_trace_count?: number;
  session_api_budget_gap_count?: number;
  a_to_b_gain_speed_proof?: Record<string, unknown>;
  speed_trace_rows?: Array<Record<string, unknown>>;
  speed_session_trace_rows?: Array<Record<string, unknown>>;
  speed_latency_rows?: Array<Record<string, unknown>>;
  speed_missing_phase_rows?: Array<Record<string, unknown>>;
  speed_repeat_cycle_rows?: Array<Record<string, unknown>>;
  blockers?: string[];
  source_paths?: Record<string, unknown>;
}

interface SwarmSearchMappingStressAudit {
  status?: string;
  generated_at?: string;
  mode?: string;
  summary?: {
    source_system_count?: number;
    wired_source_system_count?: number;
    browser_mapping_count?: number;
    browser_mapping_present_count?: number;
    data_capture_artifact_count?: number;
    data_capture_artifact_present_count?: number;
    fabric_event_count?: number;
    keyword_search_active?: boolean;
    latest_keyword_query?: string | null;
    keyword_scanned_file_count?: number;
    keyword_match_file_count?: number;
    keyword_match_count?: number;
    online_research_cinema_active?: boolean;
    online_research_topic?: string | null;
    online_research_source_count?: number;
    online_research_frame_count?: number;
    online_research_motion_ready?: boolean;
    online_research_paper_created?: boolean;
    research_coding_artifacts_created?: boolean;
    research_generated_file_count?: number;
    research_metacognition_active?: boolean;
    metacognitive_concept_count?: number;
    metacognitive_understood_concept_count?: number;
    metacognitive_route_count?: number;
    metacognitive_ready_route_count?: number;
    metacognitive_unknown_count?: number;
    metacognitive_test_action_count?: number;
    metacognitive_understanding_published?: boolean;
    phase_seen_count?: number;
    phase_expected_count?: number;
    thoughtbus_receiving?: boolean;
    mycelium_receiving?: boolean;
    live_search_capture_active?: boolean;
    no_synthetic_capture?: boolean;
    no_new_trading_gate?: boolean;
    no_external_mutation?: boolean;
  };
  source_system_rows?: Array<Record<string, unknown>>;
  browser_mapping_rows?: Array<Record<string, unknown>>;
  data_capture_rows?: Array<Record<string, unknown>>;
  keyword_search_rows?: Array<Record<string, unknown>>;
  online_research_rows?: Array<Record<string, unknown>>;
  online_research_motion_picture?: Record<string, unknown>;
  online_research_paper?: Record<string, unknown>;
  research_coding_handoff?: Record<string, unknown>;
  research_generated_file_rows?: Array<Record<string, unknown>>;
  research_metacognition?: Record<string, unknown>;
  research_metacognition_concept_rows?: Array<Record<string, unknown>>;
  research_metacognition_route_rows?: Array<Record<string, unknown>>;
  research_metacognition_unknown_rows?: Array<Record<string, unknown>>;
  research_metacognition_test_action_rows?: Array<Record<string, unknown>>;
  phase_rows?: Array<Record<string, unknown>>;
  recent_search_events?: Array<Record<string, unknown>>;
  next_actions?: Array<Record<string, unknown>>;
  manual_boundaries?: string[];
  source_paths?: Record<string, unknown>;
}

interface ParallelStrategyUnity {
  status?: string;
  generated_at?: string;
  mode?: string;
  summary?: {
    worker_count?: number;
    healthy_worker_count?: number;
    latest_signal_count?: number;
    latest_intent_count?: number;
    request_lease_count?: number;
    request_denied_count?: number;
    intent_queue_count?: number;
    executable_intent_count?: number;
    minimum_net_profit_gbp?: number;
    unified_executor_authoritative?: boolean;
    direct_broker_mutation_allowed?: boolean;
    thoughtbus_mycelium_publish_enabled?: boolean;
    ghost_dance_enabled?: boolean;
    ghost_dance_protocol?: string;
    ghost_phase_count?: number;
    ghost_phase_collision_count?: number;
    api_key_lock_family_count?: number;
    ghost_phase_spread_sec?: number;
    harmonic_api_piano_enabled?: boolean;
    harmonic_api_piano_protocol?: string;
    harmonic_tempo_multiplier?: number;
    harmonic_coherence_blend?: number;
    piano_key_count?: number;
    piano_play_now_count?: number;
    song_stop_guard?: string;
    rainbow_harmonic_ladder_enabled?: boolean;
    rainbow_harmonic_ladder_protocol?: string;
    rainbow_ladder_step_count?: number;
    rainbow_worker_ladder_count?: number;
    rainbow_base_frequency_hz?: number;
    rainbow_song_continuity_guard?: string;
    power_station_request_governor_enabled?: boolean;
    power_station_request_protocol?: string;
    power_station_request_count?: number;
    power_station_outbound_request_count?: number;
    power_station_internal_request_count?: number;
    power_station_authority_violation_count?: number;
  };
  shared_goal?: Record<string, unknown>;
  ghost_dance?: Record<string, unknown>;
  harmonic_api_piano?: Record<string, unknown>;
  rainbow_harmonic_ladder?: Record<string, unknown>;
  power_station_request_governor?: Record<string, unknown>;
  piano_key_rows?: Array<Record<string, unknown>>;
  rainbow_ladder_rows?: Array<Record<string, unknown>>;
  rainbow_worker_rows?: Array<Record<string, unknown>>;
  worker_rows?: Array<Record<string, unknown>>;
  api_lease_rows?: Array<Record<string, unknown>>;
  ghost_dance_lease_rows?: Array<Record<string, unknown>>;
  rainbow_harmonic_lease_rows?: Array<Record<string, unknown>>;
  power_station_request_rows?: Array<Record<string, unknown>>;
  venue_budget_rows?: Array<Record<string, unknown>>;
  strategy_intent_rows?: Array<Record<string, unknown>>;
  manual_boundaries?: string[];
  source_paths?: Record<string, unknown>;
}

interface ParallelStrategyUnityStressAudit {
  status?: string;
  generated_at?: string;
  mode?: string;
  summary?: {
    worker_count?: number;
    healthy_worker_count?: number;
    stale_worker_count?: number;
    attention_worker_count?: number;
    intent_count?: number;
    executable_intent_count?: number;
    missing_intent_contract_count?: number;
    lease_count?: number;
    denied_lease_count?: number;
    api_budget_gap_count?: number;
    mutation_leak_count?: number;
    denied_mutation_proof_count?: number;
    duplicate_route_count?: number;
    strategy_agreement_count?: number;
    strategy_disagreement_count?: number;
    ghost_dance_enabled?: boolean;
    ghost_phase_count?: number;
    ghost_unique_phase_count?: number;
    ghost_api_key_lock_family_count?: number;
    ghost_phase_collision_count?: number;
    ghost_missing_phase_count?: number;
    ghost_stale_historical_intent_phase_count?: number;
    harmonic_api_piano_enabled?: boolean;
    harmonic_tempo_multiplier?: number;
    harmonic_coherence_blend?: number;
    piano_key_count?: number;
    piano_play_now_count?: number;
    piano_missing_proof_count?: number;
    piano_stale_historical_intent_count?: number;
    song_stop_risk_count?: number;
    rainbow_harmonic_ladder_enabled?: boolean;
    rainbow_ladder_step_count?: number;
    rainbow_worker_ladder_count?: number;
    rainbow_base_frequency_hz?: number;
    rainbow_missing_proof_count?: number;
    rainbow_stale_historical_intent_count?: number;
    rainbow_song_continuity_risk_count?: number;
    power_station_request_governor_enabled?: boolean;
    power_station_request_count?: number;
    power_station_outbound_request_count?: number;
    power_station_internal_request_count?: number;
    power_station_missing_proof_count?: number;
    power_station_stale_historical_intent_count?: number;
    power_station_authority_violation_count?: number;
    audit_self_validation_passed?: boolean;
    audit_self_validation_failed_count?: number;
    audit_self_validation_check_count?: number;
    audit_self_validation_proof_basis?: string;
    audit_replay_validation_passed?: boolean;
    audit_replay_validation_failed_count?: number;
    audit_replay_validation_check_count?: number;
    audit_integrity_validation_passed?: boolean;
    audit_integrity_validation_failed_count?: number;
    audit_integrity_validation_check_count?: number;
    audit_validation_quorum_passed?: boolean;
    audit_validation_quorum_failed_count?: number;
    audit_validation_quorum_check_count?: number;
    audit_validation_quorum_pass_count?: number;
    audit_validation_quorum_required_count?: number;
    audit_artifact_provenance_passed?: boolean;
    audit_artifact_provenance_failed_count?: number;
    audit_artifact_provenance_check_count?: number;
    audit_artifact_provenance_json_match_count?: number;
    audit_artifact_provenance_json_artifact_count?: number;
    audit_served_artifact_passed?: boolean;
    audit_served_artifact_checked?: boolean;
    audit_served_artifact_core_matches?: boolean;
    audit_served_artifact_failed_count?: number;
    audit_served_artifact_check_count?: number;
    audit_freshness_sla_passed?: boolean;
    audit_freshness_sla_failed_count?: number;
    audit_freshness_sla_check_count?: number;
    audit_freshness_sla_age_sec?: number;
    audit_freshness_sla_validator_span_sec?: number;
    audit_operator_surface_passed?: boolean;
    audit_operator_surface_failed_count?: number;
    audit_operator_surface_check_count?: number;
    audit_operator_surface_required_panel_count?: number;
    audit_operator_surface_mutation_control_count?: number;
    audit_test_coverage_passed?: boolean;
    audit_test_coverage_failed_count?: number;
    audit_test_coverage_check_count?: number;
    audit_test_coverage_validator_test_count?: number;
    audit_test_coverage_validator_expected_count?: number;
    audit_repair_coverage_passed?: boolean;
    audit_repair_coverage_failed_count?: number;
    audit_repair_coverage_check_count?: number;
    audit_repair_coverage_repair_action_count?: number;
    audit_repair_coverage_generic_repair_count?: number;
    audit_runtime_repair_readiness_passed?: boolean;
    audit_runtime_repair_readiness_failed_count?: number;
    audit_runtime_repair_readiness_check_count?: number;
    audit_runtime_repair_readiness_guarded_command_line_count?: number;
    audit_runtime_repair_readiness_unsafe_command_count?: number;
    audit_runtime_repair_readiness_post_restart_check_count?: number;
    audit_repair_acceptance_passed?: boolean;
    audit_repair_acceptance_failed_count?: number;
    audit_repair_acceptance_check_count?: number;
    audit_repair_acceptance_acceptance_row_count?: number;
    audit_repair_acceptance_missing_acceptance_count?: number;
    audit_repair_acceptance_unmapped_blocker_count?: number;
    audit_consistency_matrix_passed?: boolean;
    audit_consistency_matrix_failed_count?: number;
    audit_consistency_matrix_check_count?: number;
    audit_consistency_matrix_validator_count?: number;
    audit_consistency_matrix_validator_pass_count?: number;
    audit_consistency_matrix_inconsistent_validator_count?: number;
    audit_evidence_lineage_passed?: boolean;
    audit_evidence_lineage_failed_count?: number;
    audit_evidence_lineage_check_count?: number;
    audit_evidence_lineage_source_path_count?: number;
    audit_evidence_lineage_output_file_count?: number;
    audit_evidence_lineage_section_row_count?: number;
    audit_evidence_lineage_missing_lineage_count?: number;
    audit_validator_closure_passed?: boolean;
    audit_validator_closure_failed_count?: number;
    audit_validator_closure_check_count?: number;
    audit_validator_closure_validator_count?: number;
    audit_validator_closure_source_check_count?: number;
    audit_validator_closure_failed_source_count?: number;
    audit_public_contract_passed?: boolean;
    audit_public_contract_failed_count?: number;
    audit_public_contract_check_count?: number;
    audit_public_contract_required_summary_field_count?: number;
    audit_public_contract_required_array_field_count?: number;
    audit_validation_chain_passed?: boolean;
    audit_validation_chain_failed_count?: number;
    audit_validation_chain_check_count?: number;
    audit_validation_chain_validator_count?: number;
    audit_validation_chain_validator_pass_count?: number;
    runtime_alignment?: boolean;
    runtime_reload_required?: boolean;
    runtime_code_wired?: boolean;
    runtime_embeds_parallel_unity?: boolean;
    runtime_embeds_parallel_intents?: boolean;
    state_snapshots_present?: boolean;
    process_discovery_available?: boolean;
    unified_market_trader_process_count?: number;
    parallel_strategy_supervisor_process_count?: number;
    wrong_python_process_count?: number;
    source_stale_process_count?: number;
    single_owner_repair_ready?: boolean;
    guarded_repair_command_ready?: boolean;
    restart_stop_target_count?: number;
    restart_start_target_count?: number;
    post_restart_check_count?: number;
    fabric_visible?: boolean;
    thoughtbus_receiving?: boolean;
    mycelium_receiving?: boolean;
    minimum_net_profit_gbp?: number;
    unified_executor_authoritative?: boolean;
    direct_broker_mutation_allowed?: boolean;
    blocker_count?: number;
  };
  artifact_rows?: Array<Record<string, unknown>>;
  worker_stress_rows?: Array<Record<string, unknown>>;
  intent_contract_rows?: Array<Record<string, unknown>>;
  lease_contract_rows?: Array<Record<string, unknown>>;
  api_budget_stress_rows?: Array<Record<string, unknown>>;
  mutation_authority_rows?: Array<Record<string, unknown>>;
  denied_mutation_proof_rows?: Array<Record<string, unknown>>;
  strategy_agreement_rows?: Array<Record<string, unknown>>;
  ghost_dance_proof?: Record<string, unknown>;
  ghost_phase_rows?: Array<Record<string, unknown>>;
  ghost_phase_collision_rows?: Array<Record<string, unknown>>;
  ghost_missing_worker_phase_rows?: Array<Record<string, unknown>>;
  ghost_missing_lease_phase_rows?: Array<Record<string, unknown>>;
  ghost_missing_intent_phase_rows?: Array<Record<string, unknown>>;
  ghost_stale_historical_intent_phase_rows?: Array<Record<string, unknown>>;
  harmonic_api_piano_proof?: Record<string, unknown>;
  piano_key_rows?: Array<Record<string, unknown>>;
  piano_missing_worker_rows?: Array<Record<string, unknown>>;
  piano_missing_lease_rows?: Array<Record<string, unknown>>;
  piano_missing_intent_rows?: Array<Record<string, unknown>>;
  piano_stale_historical_intent_rows?: Array<Record<string, unknown>>;
  piano_song_stop_risk_rows?: Array<Record<string, unknown>>;
  rainbow_harmonic_ladder_proof?: Record<string, unknown>;
  rainbow_ladder_rows?: Array<Record<string, unknown>>;
  rainbow_worker_ladder_rows?: Array<Record<string, unknown>>;
  rainbow_missing_worker_rows?: Array<Record<string, unknown>>;
  rainbow_missing_lease_rows?: Array<Record<string, unknown>>;
  rainbow_missing_intent_rows?: Array<Record<string, unknown>>;
  rainbow_stale_historical_intent_rows?: Array<Record<string, unknown>>;
  rainbow_song_continuity_risk_rows?: Array<Record<string, unknown>>;
  power_station_request_proof?: Record<string, unknown>;
  power_station_request_rows?: Array<Record<string, unknown>>;
  power_station_missing_worker_rows?: Array<Record<string, unknown>>;
  power_station_missing_lease_rows?: Array<Record<string, unknown>>;
  power_station_missing_intent_rows?: Array<Record<string, unknown>>;
  power_station_stale_historical_intent_rows?: Array<Record<string, unknown>>;
  power_station_authority_violation_rows?: Array<Record<string, unknown>>;
  audit_self_validation_proof?: Record<string, unknown>;
  audit_self_validation_rows?: Array<Record<string, unknown>>;
  audit_self_validation_failed_rows?: Array<Record<string, unknown>>;
  audit_replay_validation_proof?: Record<string, unknown>;
  audit_replay_validation_rows?: Array<Record<string, unknown>>;
  audit_replay_validation_failed_rows?: Array<Record<string, unknown>>;
  audit_integrity_validation_proof?: Record<string, unknown>;
  audit_integrity_validation_rows?: Array<Record<string, unknown>>;
  audit_integrity_validation_failed_rows?: Array<Record<string, unknown>>;
  audit_validation_quorum_proof?: Record<string, unknown>;
  audit_validation_quorum_rows?: Array<Record<string, unknown>>;
  audit_validation_quorum_failed_rows?: Array<Record<string, unknown>>;
  audit_artifact_provenance_proof?: Record<string, unknown>;
  audit_artifact_provenance_rows?: Array<Record<string, unknown>>;
  audit_artifact_provenance_failed_rows?: Array<Record<string, unknown>>;
  audit_served_artifact_proof?: Record<string, unknown>;
  audit_served_artifact_rows?: Array<Record<string, unknown>>;
  audit_served_artifact_failed_rows?: Array<Record<string, unknown>>;
  audit_freshness_sla_proof?: Record<string, unknown>;
  audit_freshness_sla_rows?: Array<Record<string, unknown>>;
  audit_freshness_sla_failed_rows?: Array<Record<string, unknown>>;
  audit_operator_surface_proof?: Record<string, unknown>;
  audit_operator_surface_rows?: Array<Record<string, unknown>>;
  audit_operator_surface_failed_rows?: Array<Record<string, unknown>>;
  audit_test_coverage_proof?: Record<string, unknown>;
  audit_test_coverage_rows?: Array<Record<string, unknown>>;
  audit_test_coverage_failed_rows?: Array<Record<string, unknown>>;
  audit_test_coverage_validator_rows?: Array<Record<string, unknown>>;
  audit_repair_coverage_proof?: Record<string, unknown>;
  audit_repair_coverage_rows?: Array<Record<string, unknown>>;
  audit_repair_coverage_failed_rows?: Array<Record<string, unknown>>;
  audit_runtime_repair_readiness_proof?: Record<string, unknown>;
  audit_runtime_repair_readiness_rows?: Array<Record<string, unknown>>;
  audit_runtime_repair_readiness_failed_rows?: Array<Record<string, unknown>>;
  audit_repair_acceptance_proof?: Record<string, unknown>;
  audit_repair_acceptance_rows?: Array<Record<string, unknown>>;
  audit_repair_acceptance_failed_rows?: Array<Record<string, unknown>>;
  audit_repair_acceptance_blocker_rows?: Array<Record<string, unknown>>;
  audit_consistency_matrix_proof?: Record<string, unknown>;
  audit_consistency_matrix_rows?: Array<Record<string, unknown>>;
  audit_consistency_matrix_failed_rows?: Array<Record<string, unknown>>;
  audit_consistency_matrix_validator_rows?: Array<Record<string, unknown>>;
  audit_evidence_lineage_proof?: Record<string, unknown>;
  audit_evidence_lineage_rows?: Array<Record<string, unknown>>;
  audit_evidence_lineage_failed_rows?: Array<Record<string, unknown>>;
  audit_evidence_lineage_section_rows?: Array<Record<string, unknown>>;
  audit_validator_closure_proof?: Record<string, unknown>;
  audit_validator_closure_rows?: Array<Record<string, unknown>>;
  audit_validator_closure_failed_rows?: Array<Record<string, unknown>>;
  audit_validator_closure_source_rows?: Array<Record<string, unknown>>;
  audit_public_contract_proof?: Record<string, unknown>;
  audit_public_contract_rows?: Array<Record<string, unknown>>;
  audit_public_contract_failed_rows?: Array<Record<string, unknown>>;
  audit_validation_chain_proof?: Record<string, unknown>;
  audit_validation_chain_rows?: Array<Record<string, unknown>>;
  audit_validation_chain_failed_rows?: Array<Record<string, unknown>>;
  audit_validation_chain_validator_rows?: Array<Record<string, unknown>>;
  executor_dedupe_rows?: Array<Record<string, unknown>>;
  stale_intent_rows?: Array<Record<string, unknown>>;
  runtime_alignment_proof?: Record<string, unknown>;
  runtime_alignment_burndown_rows?: Array<Record<string, unknown>>;
  runtime_process_proof?: Record<string, unknown>;
  runtime_process_rows?: Array<Record<string, unknown>>;
  runtime_process_burndown_rows?: Array<Record<string, unknown>>;
  single_owner_repair_plan?: Record<string, unknown>;
  single_owner_stop_target_rows?: Array<Record<string, unknown>>;
  single_owner_start_target_rows?: Array<Record<string, unknown>>;
  post_restart_check_rows?: Array<Record<string, unknown>>;
  single_owner_guard_validation_rows?: Array<Record<string, unknown>>;
  guarded_repair_command_lines?: string[];
  guarded_repair_command_preview?: string;
  fabric_visibility_proof?: Record<string, unknown>;
  shared_goal_proof?: Record<string, unknown>;
  next_repair_actions?: Array<Record<string, unknown>>;
  blockers?: string[];
  manual_boundaries?: string[];
  source_paths?: Record<string, unknown>;
}

interface CapitalEcosystemLiveDryStressAudit {
  status?: string;
  generated_at?: string;
  mode?: string;
  summary?: {
    runtime_fresh?: boolean;
    active_watchlist_count?: number;
    bench_watchlist_count?: number;
    candidate_count?: number;
    active_lifecycle_route_count?: number;
    duplicate_routes_blocked?: boolean;
    duplicate_route_blocked_count?: number;
    close_first_opportunity_count?: number;
    shadow_hedge_count?: number;
    shadow_hedges_only?: boolean;
    broker_correlation_complete?: boolean;
    lifecycle_continuity_complete?: boolean;
    recovered_position_count?: number;
    recovered_positions_certified?: boolean;
    recovery_certification_status?: string;
    recovered_upstream_context_missing_count?: number;
    recovered_position_close_first_covered?: boolean;
    recovered_duplicate_route_blocking_active?: boolean;
    recovered_close_chain_status?: string;
    recovered_close_request_count?: number;
    recovered_close_acknowledged_count?: number;
    recovered_position_absence_verified_count?: number;
    recovered_outcome_recorded_count?: number;
    recovered_exit_blockers?: string[];
    capital_watchlist_within_limit?: boolean;
    lifecycle_stress_certified?: boolean;
    exchange_matrix_rows?: number;
    stream_cache_ticker_count?: number;
    no_live_mutation?: boolean;
  };
  runtime_proof?: Record<string, unknown>;
  capital_watchlist_proof?: Record<string, unknown>;
  lifecycle_route_proof?: Record<string, unknown>;
  recovered_position_proof?: Record<string, unknown>;
  recovered_exit_readiness_proof?: Record<string, unknown>;
  broker_correlation_proof?: Record<string, unknown>;
  close_first_proof?: Record<string, unknown>;
  shadow_hedge_proof?: Record<string, unknown>;
  lifecycle_stress_proof?: Record<string, unknown>;
  blockers?: string[];
  manual_boundaries?: string[];
  source_paths?: Record<string, unknown>;
}

const screenIcons: Record<string, typeof Activity> = {
  overview: Eye,
  trading: LineChart,
  accounting: Calculator,
  research: Search,
  saas_security: ShieldCheck,
  self_improvement: Brain,
  admin: Settings,
};

const statusTone: Record<string, string> = {
  wired: "border-success/30 bg-success/10 text-success",
  partial: "border-primary/30 bg-primary/10 text-primary",
  orphaned: "border-warning/30 bg-warning/10 text-warning",
  legacy: "border-warning/30 bg-warning/10 text-warning",
  generated_output: "border-primary/30 bg-primary/10 text-primary",
  security_blocker: "border-destructive/30 bg-destructive/10 text-destructive",
  unknown: "border-border bg-muted/20 text-muted-foreground",
};

const safetyTone: Record<string, string> = {
  observation: "border-success/30 bg-success/10 text-success",
  credential_or_auth_boundary: "border-warning/30 bg-warning/10 text-warning",
  live_trading_boundary: "border-destructive/30 bg-destructive/10 text-destructive",
  payment_or_kyc_boundary: "border-destructive/30 bg-destructive/10 text-destructive",
  manual_filing_boundary: "border-warning/30 bg-warning/10 text-warning",
  admin_or_tenant_boundary: "border-warning/30 bg-warning/10 text-warning",
};

type DashboardTabId = "overview" | "repo-map" | "live-ops" | "coding" | "trading" | "security" | "inventory" | "agents" | "evidence";
type BlockerFilter = "all" | "critical" | "security" | "runtime" | "stale";
type WorkOrderFilter = "all" | "blocked" | "ready" | "archive" | "screen";
type SurfaceFilter = "all" | "observation" | "security" | "live" | "credential" | "missing";
type EvidenceFilter = "all" | "audit" | "public" | "runtime" | "report";

interface DashboardTabConfig {
  id: DashboardTabId;
  title: string;
  summary: string;
  icon: typeof Activity;
}

const dashboardTabs: DashboardTabConfig[] = [
  { id: "overview", title: "Overview", summary: "Health, blockers, runtime, and next actions.", icon: Eye },
  { id: "repo-map", title: "Repo Map", summary: "Whole-repo systems, capability routes, and public contract.", icon: Map },
  { id: "live-ops", title: "Live Ops", summary: "Runtime shell, interfaces, and live telemetry.", icon: Radio },
  { id: "coding", title: "Coding", summary: "Prompt lane, forge, tests, and handover proof.", icon: Settings },
  { id: "trading", title: "Trading", summary: "Trading state, exchange checks, and risk gates.", icon: LineChart },
  { id: "security", title: "Security", summary: "Boundaries, credentials, blockers, and safe routes.", icon: ShieldCheck },
  { id: "inventory", title: "Inventory", summary: "Work orders, screens, surfaces, and migration queue.", icon: Database },
  { id: "agents", title: "Agents", summary: "Aureon company, role map, and capability switchboard.", icon: Brain },
  { id: "evidence", title: "Evidence", summary: "Artifacts, public manifests, reports, and proofs.", icon: FileText },
];

const blockerFilterOptions: Array<{ id: BlockerFilter; label: string }> = [
  { id: "all", label: "All" },
  { id: "critical", label: "Critical" },
  { id: "security", label: "Security" },
  { id: "runtime", label: "Runtime" },
  { id: "stale", label: "Stale" },
];

const workOrderFilterOptions: Array<{ id: WorkOrderFilter; label: string }> = [
  { id: "all", label: "All" },
  { id: "blocked", label: "Blocked" },
  { id: "ready", label: "Ready" },
  { id: "archive", label: "Archive" },
  { id: "screen", label: "Screen" },
];

const surfaceFilterOptions: Array<{ id: SurfaceFilter; label: string }> = [
  { id: "all", label: "All" },
  { id: "observation", label: "Observation" },
  { id: "security", label: "Security" },
  { id: "live", label: "Live" },
  { id: "credential", label: "Credential" },
  { id: "missing", label: "Missing" },
];

const evidenceFilterOptions: Array<{ id: EvidenceFilter; label: string }> = [
  { id: "all", label: "All" },
  { id: "audit", label: "Audit" },
  { id: "public", label: "Public" },
  { id: "runtime", label: "Runtime" },
  { id: "report", label: "Report" },
];

function normalizeDashboardTab(hashOrValue?: string): DashboardTabId {
  const raw = String(hashOrValue || "")
    .replace(/^#\/?/, "")
    .trim()
    .toLowerCase();
  return dashboardTabs.some((tab) => tab.id === raw) ? (raw as DashboardTabId) : "overview";
}

interface SecurityBlockerWorkOrder {
  title: string;
  workOrder: string;
  sourcePath: string;
  target: string;
  priority: string;
  status: string;
  reason: string;
  nextStep: string;
  boundaries: string[];
}

const screenSecurityBlockers: Record<string, SecurityBlockerWorkOrder[]> = {
  trading: [
    {
      title: "Orca Command Center Trading blocker",
      workOrder: "Wire Orca Command Center into Trading",
      sourcePath: "aureon/bots/orca_command_center.py",
      target: "Trading",
      priority: "P100",
      status: "blocked_security_review",
      reason: "The Orca command center initializes exchange clients, reads live positions, subscribes to ThoughtBus intelligence, and presents hunting/kill-cycle trading state. Trading exposes the work order as evidence only until a non-mutating adapter is reviewed.",
      nextStep: "Extract read-only Orca position, exchange-readiness, signal, whale-detection, predator-alert, and kill-cycle evidence, then mount that adapter with all order, launcher, exchange mutation, and credential surfaces removed.",
      boundaries: [
        "read-only observation",
        "no live trading",
        "no order mutation",
        "no official filing",
        "no payment",
        "no credential reveal",
        "no external mutation",
      ],
    },
    {
      title: "AutonomousTradingGuide Trading blocker",
      workOrder: "Wire Autonomoustradingguide into Trading",
      sourcePath: "frontend/src/components/AutonomousTradingGuide.tsx",
      target: "Trading",
      priority: "P100",
      status: "blocked_security_review",
      reason: "The legacy guide documents autonomous execution, exchange API permissions, live-fire activation language, and signed Binance account-check code. Trading exposes the work order as evidence only until the guidance is adapted into a current Aureon read-only operating checklist.",
      nextStep: "Extract the useful risk, permission, paper/live transition, and execution-readiness guidance into a current read-only Trading checklist, with secret examples redacted and no activation, key-entry, or order controls mounted.",
      boundaries: [
        "read-only observation",
        "no live trading",
        "no order mutation",
        "no API key entry",
        "no credential reveal",
        "no official filing",
        "no payment",
        "no external mutation",
      ],
    },
    {
      title: "BinanceCredentialsSettings Trading blocker",
      workOrder: "Wire Binancecredentialssettings into Trading",
      sourcePath: "frontend/src/components/BinanceCredentialsSettings.tsx",
      target: "Trading",
      priority: "P100",
      status: "blocked_security_review",
      reason: "The existing settings panel accepts Binance API key and secret values, stores credentials through the Binance credential hook, and links operators to external Binance API management. Trading exposes the work order as evidence only until credential handling is mounted through the reviewed key-management flow.",
      nextStep: "Extract read-only Binance credential readiness, encryption policy, withdrawal-disabled policy, and setup-status evidence, then route any key add/update workflow through the dedicated secure credential manager instead of this legacy panel.",
      boundaries: [
        "read-only observation",
        "no live trading",
        "no order mutation",
        "no API key entry",
        "no credential storage mutation",
        "no credential reveal",
        "no external credential workflow",
        "no external mutation",
      ],
    },
  ],
  overview: [
    {
      title: "WarRoomDashboard Overview blocker",
      workOrder: "Wire Warroomdashboard into Overview",
      sourcePath: "frontend/src/components/WarRoomDashboard.tsx",
      target: "Overview",
      priority: "P100",
      status: "blocked_security_review",
      reason: "The existing dashboard contains interactive trading and launcher controls, so Overview exposes the work order as evidence only until the non-mutating adapter is reviewed.",
      nextStep: "Extract a read-only telemetry adapter after security review, then mount that adapter instead of the interactive control surface.",
      boundaries: [
        "read-only observation",
        "no live trading",
        "no official filing",
        "no payment",
        "no credential reveal",
        "no external mutation",
      ],
    },
    {
      title: "GasTankDisplay Overview blocker",
      workOrder: "Wire Gastankdisplay into Overview",
      sourcePath: "frontend/src/components/warroom/GasTankDisplay.tsx",
      target: "Overview",
      priority: "P100",
      status: "blocked_security_review",
      reason: "The existing gas tank panel displays user balance and fee state but also exposes top-up payment controls, so Overview shows the work order as evidence only until a redacted read-only adapter is reviewed.",
      nextStep: "Extract gas-tank health, balance visibility policy, membership tier, and fee-burn status into a read-only adapter with all top-up and payment mutation paths removed.",
      boundaries: [
        "read-only observation",
        "no live trading",
        "no official filing",
        "no payment",
        "no top-up mutation",
        "no credential reveal",
        "no external mutation",
      ],
    },
  ],
  saas_security: [
    {
      title: "AdminKYCDashboard SaaS Security blocker",
      workOrder: "Wire Adminkycdashboard into SaaS Security",
      sourcePath: "frontend/src/components/AdminKYCDashboard.tsx",
      target: "SaaS Security",
      priority: "P100",
      status: "blocked_security_review",
      reason: "The existing dashboard reads KYC records, creates signed identity-document URLs, and can approve or reject applications through Supabase functions. SaaS Security exposes the work order as evidence only until a non-mutating adapter is reviewed.",
      nextStep: "Extract redacted read-only KYC queue health and review-state metrics, then mount that adapter instead of the admin mutation surface.",
      boundaries: [
        "read-only observation",
        "no live trading",
        "no official filing",
        "no payment",
        "no credential reveal",
        "no KYC document reveal",
        "no external mutation",
      ],
    },
    {
      title: "AdminPaymentVerification SaaS Security blocker",
      workOrder: "Wire Adminpaymentverification into SaaS Security",
      sourcePath: "frontend/src/components/AdminPaymentVerification.tsx",
      target: "SaaS Security",
      priority: "P100",
      status: "blocked_security_review",
      reason: "The existing dashboard reads payment transactions and can invoke payment-verification functions that affect user access. SaaS Security exposes the work order as evidence only until a non-mutating adapter is reviewed.",
      nextStep: "Extract redacted read-only payment queue health, verification-state counts, and access-impact evidence, then mount that adapter with every verify or payment mutation path removed.",
      boundaries: [
        "read-only observation",
        "no live trading",
        "no official filing",
        "no payment",
        "no payment verification mutation",
        "no credential reveal",
        "no external mutation",
      ],
    },
    {
      title: "AuthForm SaaS Security blocker",
      workOrder: "Wire Authform into SaaS Security",
      sourcePath: "frontend/src/components/AuthForm.tsx",
      target: "SaaS Security",
      priority: "P100",
      status: "blocked_security_review",
      reason: "The existing form can create auth sessions and accepts exchange API key material. SaaS Security exposes the work order as evidence only until a redacted, non-mutating onboarding adapter is reviewed.",
      nextStep: "Extract auth readiness, password-policy, tenant-session, and API-key onboarding checklist evidence without rendering sign-in controls, secret inputs, or session mutation calls.",
      boundaries: [
        "read-only observation",
        "no live trading",
        "no official filing",
        "no payment",
        "no auth/session mutation",
        "no credential reveal",
        "no external mutation",
      ],
    },
    {
      title: "APIKeySecurityGuide SaaS Security blocker",
      workOrder: "Wire Apikeysecurityguide into SaaS Security",
      sourcePath: "frontend/src/components/auth/APIKeySecurityGuide.tsx",
      target: "SaaS Security",
      priority: "P100",
      status: "blocked_security_review",
      reason: "The existing guide points operators toward external exchange key workflows and permission setup. SaaS Security exposes the work order as evidence only until a read-only guidance adapter is reviewed.",
      nextStep: "Extract redacted exchange-key setup guidance, withdrawal-disabled policy, and validation checklist evidence without collecting, revealing, or changing credentials.",
      boundaries: [
        "read-only observation",
        "no live trading",
        "no official filing",
        "no payment",
        "no credential reveal",
        "no external mutation",
      ],
    },
  ],
  self_improvement: [
    {
      title: "Aureon Command Center Self-Improvement blocker",
      workOrder: "Wire Aureon Command Center into Self-Improvement",
      sourcePath: "aureon/command_centers/aureon_command_center.py",
      target: "Self-Improvement",
      priority: "P100",
      status: "blocked_security_review",
      reason: "The command center can launch and supervise runtime processes, including trading subprocess paths. Self-Improvement exposes the work order as evidence only until a non-mutating status adapter is reviewed.",
      nextStep: "Extract read-only command-center health, process-state, tool inventory, and audit evidence, then mount that adapter with launch, stop, apply, restart, or mutation controls removed.",
      boundaries: [
        "read-only observation",
        "no live trading",
        "no official filing",
        "no payment",
        "no credential reveal",
        "no process mutation",
        "no external mutation",
      ],
    },
    {
      title: "Aureon Queen Realtime Command Center Self-Improvement blocker",
      workOrder: "Wire Aureon Queen Realtime Command Center into Self-Improvement",
      sourcePath: "aureon/command_centers/aureon_queen_realtime_command_center.py",
      target: "Self-Improvement",
      priority: "P100",
      status: "blocked_security_review",
      reason: "The realtime command center streams live bot, PnL, position, subsystem, and log evidence from command-center code paths. Self-Improvement shows the boundary before any interactive adapter is generated.",
      nextStep: "Create a read-only status card for stream freshness, subsystem health, Queen commentary state, and report paths, with process control and exchange mutation surfaces excluded.",
      boundaries: [
        "read-only observation",
        "no live trading",
        "no official filing",
        "no payment",
        "no credential reveal",
        "no process mutation",
        "no external mutation",
      ],
    },
  ],
};

function asNumber(value: unknown, fallback = 0): number {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : fallback;
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

function asRecordArray(value: unknown): Array<Record<string, unknown>> {
  return Array.isArray(value)
    ? value.filter((item): item is Record<string, unknown> => Boolean(item && typeof item === "object" && !Array.isArray(item)))
    : [];
}

function formatCompact(value: unknown): string {
  return asNumber(value).toLocaleString();
}

function readinessPercent(summary: SaaSInventoryManifest["summary"]): number {
  const total = Math.max(1, asNumber(summary?.surface_count));
  const blockers = asNumber(summary?.security_blocker_count);
  const orphaned = asNumber(summary?.orphaned_frontend_count);
  const weightedGaps = blockers * 25 + orphaned * 0.12;
  return Math.max(0, Math.min(100, Math.round(100 - (weightedGaps / total) * 100)));
}

function uniqueStrings(values: Array<string | undefined>): string[] {
  return Array.from(new Set(values.map((value) => String(value || "").trim()).filter(Boolean)));
}

async function fetchJsonOrNull<T>(url: string, signal?: AbortSignal): Promise<T | null> {
  try {
    const response = await fetch(url, { cache: "no-store", signal });
    if (!response.ok) return null;
    return (await response.json()) as T;
  } catch {
    return null;
  }
}

async function loadWakeUpManifest(signal?: AbortSignal): Promise<WakeUpManifest | null> {
  return fetchJsonOrNull<WakeUpManifest>("/aureon_wake_up_manifest.json", signal);
}

async function loadTradingIntelligenceChecklist(signal?: AbortSignal): Promise<TradingIntelligenceChecklist | null> {
  return fetchJsonOrNull<TradingIntelligenceChecklist>("/aureon_trading_intelligence_checklist.json", signal);
}

async function loadExchangeMonitoringChecklist(signal?: AbortSignal): Promise<ExchangeMonitoringChecklist | null> {
  return fetchJsonOrNull<ExchangeMonitoringChecklist>("/aureon_exchange_monitoring_checklist.json", signal);
}

async function loadExchangeDataCapabilityMatrix(signal?: AbortSignal): Promise<ExchangeDataCapabilityMatrix | null> {
  return fetchJsonOrNull<ExchangeDataCapabilityMatrix>("/aureon_exchange_data_capability_matrix.json", signal);
}

async function loadGlobalFinancialCoverageMap(signal?: AbortSignal): Promise<GlobalFinancialCoverageMap | null> {
  return fetchJsonOrNull<GlobalFinancialCoverageMap>("/aureon_global_financial_coverage_map.json", signal);
}

async function loadHNCPacketSecurityComparison(signal?: AbortSignal): Promise<HNCPacketSecurityComparison | null> {
  return fetchJsonOrNull<HNCPacketSecurityComparison>("/aureon_hnc_packet_security_comparison.json", signal);
}

async function loadLiveGoalTradeAudit(signal?: AbortSignal): Promise<LiveGoalTradeAudit | null> {
  return fetchJsonOrNull<LiveGoalTradeAudit>("/aureon_live_goal_trade_audit.json", signal);
}

async function loadOrderLifecycleStressAudit(signal?: AbortSignal): Promise<OrderLifecycleStressAudit | null> {
  return fetchJsonOrNull<OrderLifecycleStressAudit>("/aureon_order_lifecycle_stress_audit.json", signal);
}

async function loadCapitalEcosystemIntelligence(signal?: AbortSignal): Promise<CapitalEcosystemIntelligenceCompany | null> {
  return fetchJsonOrNull<CapitalEcosystemIntelligenceCompany>("/aureon_capital_ecosystem_intelligence_company.json", signal);
}

async function loadCapitalRevenueLogicStressAudit(signal?: AbortSignal): Promise<CapitalRevenueLogicStressAudit | null> {
  return fetchJsonOrNull<CapitalRevenueLogicStressAudit>("/aureon_capital_revenue_logic_stress_audit.json", signal);
}

async function loadCapitalRevenueLiveGateReadinessAudit(signal?: AbortSignal): Promise<CapitalRevenueLiveGateReadinessAudit | null> {
  return fetchJsonOrNull<CapitalRevenueLiveGateReadinessAudit>("/aureon_capital_revenue_live_gate_readiness_audit.json", signal);
}

async function loadCapitalThreePLiveExecutionCertificationAudit(signal?: AbortSignal): Promise<CapitalThreePLiveExecutionCertificationAudit | null> {
  return fetchJsonOrNull<CapitalThreePLiveExecutionCertificationAudit>("/aureon_capital_3p_live_execution_certification_audit.json", signal);
}

async function loadCapitalThreePBlockerBurndownAudit(signal?: AbortSignal): Promise<CapitalThreePBlockerBurndownAudit | null> {
  return fetchJsonOrNull<CapitalThreePBlockerBurndownAudit>("/aureon_capital_3p_blocker_burndown_audit.json", signal);
}

async function loadPerformanceReadinessAudit(signal?: AbortSignal): Promise<PerformanceReadinessAudit | null> {
  return fetchJsonOrNull<PerformanceReadinessAudit>("/aureon_performance_readiness_audit.json", signal);
}

async function loadAureonMurgeUnityBridge(signal?: AbortSignal): Promise<AureonMurgeUnityBridge | null> {
  return fetchJsonOrNull<AureonMurgeUnityBridge>("/aureon_murge_unity_bridge.json", signal);
}

async function loadAureonMurgeRuntimeActivationStressAudit(signal?: AbortSignal): Promise<AureonMurgeRuntimeActivationStressAudit | null> {
  return fetchJsonOrNull<AureonMurgeRuntimeActivationStressAudit>("/aureon_murge_runtime_activation_stress_audit.json", signal);
}

async function loadLiveTradeSignalFabric(signal?: AbortSignal): Promise<LiveTradeSignalFabric | null> {
  return fetchJsonOrNull<LiveTradeSignalFabric>("/aureon_live_trade_signal_fabric.json", signal);
}

async function loadLiveTradeSignalFabricStressAudit(signal?: AbortSignal): Promise<LiveTradeSignalFabricStressAudit | null> {
  return fetchJsonOrNull<LiveTradeSignalFabricStressAudit>("/aureon_live_trade_signal_fabric_stress_audit.json", signal);
}

async function loadSwarmSearchMappingStressAudit(signal?: AbortSignal): Promise<SwarmSearchMappingStressAudit | null> {
  return fetchJsonOrNull<SwarmSearchMappingStressAudit>("/aureon_swarm_search_mapping_stress_audit.json", signal);
}

async function loadParallelStrategyUnity(signal?: AbortSignal): Promise<ParallelStrategyUnity | null> {
  return fetchJsonOrNull<ParallelStrategyUnity>("/aureon_parallel_strategy_unity.json", signal);
}

async function loadParallelStrategyUnityStressAudit(signal?: AbortSignal): Promise<ParallelStrategyUnityStressAudit | null> {
  return fetchJsonOrNull<ParallelStrategyUnityStressAudit>("/aureon_parallel_strategy_unity_stress_audit.json", signal);
}

async function loadCapitalLiveDryStressAudit(signal?: AbortSignal): Promise<CapitalEcosystemLiveDryStressAudit | null> {
  return fetchJsonOrNull<CapitalEcosystemLiveDryStressAudit>("/aureon_capital_ecosystem_live_dry_stress_audit.json", signal);
}

function flightTestUrlFor(endpoint: string, manifest?: WakeUpManifest | null): string {
  if (manifest?.runtime_flight_test_url) return manifest.runtime_flight_test_url;
  return endpoint.replace(/\/api\/terminal-state$/, "/api/flight-test");
}

function runtimeStatusLines(data: any, flight: any): string[] {
  const existing = Array.isArray(data?.status_lines)
    ? data.status_lines.map((line: unknown) => String(line || "")).filter(Boolean)
    : [];
  if (existing.length) return existing;

  const watchdog = data?.runtime_watchdog || {};
  const advice = flight?.reboot_advice || {};
  const lines = [
    `Runtime feed: connected${data?.ok === false ? " with runtime clearance pending" : ""}`,
    `Trading ready: ${Boolean(data?.trading_ready)}; data ready: ${Boolean(data?.data_ready)}`,
  ];
  if (data?.stale || watchdog?.tick_stale) {
    lines.push(`Runtime check: ${String(data?.stale_reason || watchdog?.tick_stale_reason || "runtime_stale")}`);
  }
  if (watchdog?.last_tick_age_sec !== undefined) {
    lines.push(`Tick age: ${formatCompact(watchdog.last_tick_age_sec)}s`);
  }
  if (advice?.decision) {
    lines.push(`Reboot advice: ${String(advice.decision)} (${String(advice.reason || "no reason")})`);
  }
  return lines;
}

function runtimeClearances(data: any, flight: any): string[] {
  const watchdog = data?.runtime_watchdog || {};
  const checks = flight?.checks || {};
  const advice = flight?.reboot_advice || {};
  const clearances: string[] = [];
  const shouldReboot = advice?.should_reboot === true || checks?.pending_restart === true;
  if (data?.booting) clearances.push("runtime_booting");
  if (data?.stale || watchdog?.tick_stale) clearances.push("runtime_stale");
  if (watchdog?.tick_stale_reason || data?.stale_reason) clearances.push(String(data?.stale_reason || watchdog.tick_stale_reason));
  if (asNumber(data?.combined?.open_positions || checks?.open_positions || watchdog?.open_positions) > 0 || checks?.open_positions === true || watchdog?.open_positions === true) {
    clearances.push("open_positions");
  }
  if (shouldReboot && (checks?.downtime_window === false || checks?.downtime_window_open === false || advice?.downtime_window === false)) {
    clearances.push("downtime_window_false");
  }
  if (shouldReboot && advice?.can_reboot_now === false) clearances.push(String(advice.reason || "reboot_held"));
  return uniqueStrings(clearances);
}

function runtimeDetails(data: any, flight: any): Array<{ label: string; value: string }> {
  const watchdog = data?.runtime_watchdog || {};
  const advice = flight?.reboot_advice || {};
  const governor = data?.api_governor?.exchanges || {};
  const actionPlan = data?.exchange_action_plan || {};
  const venues = actionPlan?.venues || {};
  const latestIntents = actionPlan?.latest_published || {};
  const latestExecution = actionPlan?.latest_execution || {};
  const modelCoverage = actionPlan?.model_coverage || {};
  const shadowTrading = data?.shadow_trading || actionPlan?.shadow_trading || {};
  const hncProof = data?.hnc_cognitive_proof || actionPlan?.hnc_cognitive_proof || {};
  const details = [
    { label: "tick age", value: watchdog?.last_tick_age_sec !== undefined ? `${formatCompact(watchdog.last_tick_age_sec)}s` : "unknown" },
    { label: "stale reason", value: String(data?.stale_reason || watchdog?.tick_stale_reason || "none") },
    { label: "reboot", value: String(advice?.decision || "unknown") },
    { label: "positions", value: formatCompact(data?.combined?.open_positions || 0) },
  ];
  if (actionPlan?.venue_count !== undefined || Object.keys(venues).length) {
    details.push({
      label: "venues ready",
      value: `${formatCompact(actionPlan?.ready_venue_count || 0)}/${formatCompact(actionPlan?.venue_count || Object.keys(venues).length)}`,
    });
  }
  if (actionPlan?.mode) {
    details.push({ label: "intent mode", value: String(actionPlan.mode).replace("runtime_gated_", "") });
  }
  if (actionPlan?.trade_path_state) {
    details.push({ label: "trade path", value: String(actionPlan.trade_path_state).replaceAll("_", " ") });
  }
  if (modelCoverage?.available_model_count !== undefined || modelCoverage?.ready_route_count !== undefined) {
    details.push({
      label: "models",
      value: `${formatCompact(modelCoverage?.available_model_count || 0)} linked / ${formatCompact(modelCoverage?.ready_route_count || 0)} routes`,
    });
  }
  if (latestIntents?.intent_count !== undefined || actionPlan?.order_intents_published !== undefined) {
    details.push({
      label: "order intents",
      value: formatCompact(latestIntents?.intent_count || actionPlan?.order_intents_published || 0),
    });
  }
  if (latestExecution?.submitted_count !== undefined || latestExecution?.blocked_count !== undefined) {
    details.push({
      label: "executor",
      value: `${formatCompact(latestExecution?.submitted_count || 0)} sent / ${formatCompact(latestExecution?.delegated_count || 0)} delegated / ${formatCompact(latestExecution?.held_count ?? latestExecution?.blocked_count ?? 0)} held`,
    });
  }
  if (shadowTrading?.shadow_count !== undefined || shadowTrading?.active_shadow_count !== undefined) {
    details.push({
      label: "shadow trades",
      value: `${formatCompact(shadowTrading?.shadow_opened_count || 0)} opened / ${formatCompact(shadowTrading?.active_shadow_count || 0)} active`,
    });
  }
  if (shadowTrading?.validated_shadow_count !== undefined || shadowTrading?.self_measurement?.agent_average_score !== undefined) {
    details.push({
      label: "shadow proof",
      value: `${formatCompact(shadowTrading?.validated_shadow_count || 0)} validated / ${Math.round(asNumber(shadowTrading?.self_measurement?.agent_average_score) * 100)}% agent score`,
    });
  }
  if (hncProof?.step_count !== undefined || hncProof?.passed_count !== undefined) {
    details.push({
      label: "HNC flow",
      value: `${formatCompact(hncProof?.passed_count || 0)}/${formatCompact(hncProof?.step_count || 0)} ${String(hncProof?.status || "checking")}`,
    });
  }
  if (hncProof?.auris_nodes?.node_count !== undefined || hncProof?.auris_nodes?.coherence !== undefined) {
    details.push({
      label: "Auris nodes",
      value: `${formatCompact(hncProof?.auris_nodes?.node_count || 0)} nodes / ${Math.round(asNumber(hncProof?.auris_nodes?.coherence) * 100)}% coherence`,
    });
  }
  if (hncProof?.master_formula?.score !== undefined) {
    details.push({
      label: "master formula",
      value: `${Math.round(asNumber(hncProof?.master_formula?.score) * 100)}% ${hncProof?.master_formula?.passed ? "passing" : "attention"}`,
    });
  }
  for (const name of ["kraken", "capital", "alpaca", "binance"]) {
    if (governor?.[name]?.utilization !== undefined) {
      details.push({ label: `${name} api`, value: `${Math.round(asNumber(governor[name].utilization) * 100)}%` });
    }
  }
  return details;
}

function runtimeModeLabel(data: any): string {
  const actionPlan = data?.exchange_action_plan || {};
  const latestExecution = actionPlan?.latest_execution || data?.latest_execution || {};
  if (latestExecution?.live_action_clearance === "cleared") return "live action cleared";
  if ((actionPlan?.latest_published?.intent_count || actionPlan?.order_intents_published) > 0) return "intent published";
  if (actionPlan?.order_intent_publish_enabled && actionPlan?.trade_path_state === "available") return "runtime gated action";
  if (actionPlan?.mode) return String(actionPlan.mode).replaceAll("_", " ");
  if (data?.ok === false) return "clearance pending";
  return String(data?.trading_mode || data?.queen_state || "observe");
}

async function loadRuntimeObservation(): Promise<RuntimeObservation> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 10000);

  try {
    const manifest = await loadWakeUpManifest(controller.signal);
    const endpoints = uniqueStrings([manifest?.runtime_feed_url, ...DEFAULT_RUNTIME_ENDPOINTS]);
    for (const endpoint of endpoints) {
      const data = await fetchJsonOrNull<any>(endpoint, controller.signal);
      if (!data) continue;
      const flight = await fetchJsonOrNull<any>(flightTestUrlFor(endpoint, manifest), controller.signal);
      const clearances = runtimeClearances(data, flight);
      const actionPlan = data?.exchange_action_plan || {};
      const goldRuntimeTradeProof = (
        (data?.gold_runtime_trade_proof && typeof data.gold_runtime_trade_proof === "object" ? data.gold_runtime_trade_proof : null) ||
        (actionPlan?.gold_runtime_trade_proof && typeof actionPlan.gold_runtime_trade_proof === "object" ? actionPlan.gold_runtime_trade_proof : null)
      ) as Record<string, unknown> | null;
      const freshGoldSource = (
        goldRuntimeTradeProof?.fresh_gold_data_source && typeof goldRuntimeTradeProof.fresh_gold_data_source === "object"
          ? goldRuntimeTradeProof.fresh_gold_data_source as Record<string, unknown>
          : null
      );
      const runtimeObservationReady = Boolean(
        data?.runtime_observation_ready ||
        (goldRuntimeTradeProof?.gold_runtime_candidate_ready && freshGoldSource?.ready)
      );
      return {
        connected: true,
        clearancePending: !runtimeObservationReady && (data?.ok === false || clearances.length > 0),
        endpoint,
        generatedAt: String(data?.generated_at || data?.dashboard_generated_at || new Date().toISOString()),
        stale: Boolean(data?.stale || data?.runtime_watchdog?.tick_stale),
        staleReason: String(data?.stale_reason || data?.runtime_watchdog?.tick_stale_reason || ""),
        statusLines: runtimeStatusLines(data, flight),
        metrics: [
          { label: "portfolio", value: formatCompact(data?.portfolio_value || data?.combined?.equity || data?.combined?.capital_equity_gbp || 0) },
          { label: "open positions", value: formatCompact(data?.combined?.open_positions || data?.positions?.length || 0) },
          { label: "trades", value: formatCompact(data?.total_trades || 0) },
          { label: "mode", value: runtimeModeLabel(data) },
        ],
        clearances,
        details: runtimeDetails(data, flight),
        data,
        flight: flight || undefined,
        goldRuntimeTradeProof: goldRuntimeTradeProof || undefined,
      };
    }
    return {
      connected: false,
      clearancePending: false,
      statusLines: ["Runtime feed unavailable. Start Aureon ignition to stream live status."],
      metrics: [],
      clearances: [],
      details: [],
    };
  } catch {
    return {
      connected: false,
      clearancePending: false,
      statusLines: ["Runtime feed unavailable. The unified shell is showing manifest/audit state only."],
      metrics: [],
      clearances: [],
      details: [],
    };
  } finally {
    window.clearTimeout(timeout);
  }
}

function Pill({ label, tone = "outline" }: { label: string; tone?: string }) {
  return (
    <span className={`inline-flex min-h-6 items-center rounded-md border px-2 py-0.5 text-[11px] font-medium ${tone}`}>
      {label}
    </span>
  );
}

function MetricTile({
  label,
  value,
  icon: Icon,
  tone = "text-foreground",
}: {
  label: string;
  value: string;
  icon: typeof Activity;
  tone?: string;
}) {
  return (
    <Card className="min-h-[88px] bg-card/80">
      <CardContent className="flex h-full flex-col justify-between p-3">
        <div className="flex items-center justify-between gap-3">
          <div className="text-xs uppercase text-muted-foreground">{label}</div>
          <Icon className={`h-4 w-4 ${tone}`} />
        </div>
        <div className={`mt-3 text-xl font-semibold ${tone}`}>{value}</div>
      </CardContent>
    </Card>
  );
}

function SecurityBlockerCard({ blocker }: { blocker: SecurityBlockerWorkOrder }) {
  return (
    <Card className="border-warning/30 bg-warning/10">
      <CardHeader className="pb-3">
        <CardTitle className="flex flex-wrap items-center gap-2 text-base">
          <Lock className="h-4 w-4 text-warning" />
          {blocker.title}
          <Pill label={blocker.priority} tone="border-warning/40 bg-warning/15 text-warning" />
          <Pill label={blocker.status} tone="border-destructive/35 bg-destructive/10 text-destructive" />
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-3 lg:grid-cols-[1fr_1fr_1fr]">
          <div className="rounded-md border border-border/40 bg-black/25 p-3">
            <div className="text-[11px] uppercase text-muted-foreground">work order</div>
            <div className="mt-1 text-sm font-semibold">{blocker.workOrder}</div>
            <div className="mt-2 font-mono text-[11px] text-muted-foreground">{blocker.sourcePath}</div>
          </div>
          <div className="rounded-md border border-border/40 bg-black/25 p-3">
            <div className="text-[11px] uppercase text-muted-foreground">target screen</div>
            <div className="mt-1 text-sm font-semibold">{blocker.target}</div>
            <div className="mt-2 text-xs text-warning/80">{blocker.reason}</div>
          </div>
          <div className="rounded-md border border-border/40 bg-black/25 p-3">
            <div className="text-[11px] uppercase text-muted-foreground">next action</div>
            <div className="mt-1 text-xs text-foreground/85">{blocker.nextStep}</div>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          {blocker.boundaries.map((boundary) => (
            <Pill key={boundary} label={boundary} tone="border-warning/30 bg-warning/10 text-warning" />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function SaaSCredentialManagementPanel({ comparison }: { comparison: HNCPacketSecurityComparison | null }) {
  return (
    <section className="space-y-4 rounded-md border border-success/30 bg-success/5 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="flex items-center gap-2 text-base font-semibold">
            <Lock className="h-4 w-4 text-success" />
            Secure exchange key management
          </h2>
          <p className="mt-1 max-w-4xl text-sm text-muted-foreground">
            Users can add, test, or update Binance, Kraken, Alpaca, and Capital credentials through the local .env path and optional user vault sync. Saved secrets are never printed back into the console.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Pill label="add or update keys" tone={statusTone.wired} />
          <Pill label="stored values hidden" tone="border-success/30 bg-success/10 text-success" />
          <Pill label="withdrawals must stay disabled" tone="border-warning/30 bg-warning/10 text-warning" />
        </div>
      </div>
      <HNCPacketSecurityComparisonPanel comparison={comparison} />
      <ExchangeCredentialsManager />
    </section>
  );
}

function HNCPacketSecurityComparisonPanel({ comparison }: { comparison: HNCPacketSecurityComparison | null }) {
  const summary = comparison?.summary || {};
  const topRows = (comparison?.rows || [])
    .slice()
    .sort((a, b) => asNumber(b.score) - asNumber(a.score))
    .slice(0, 4);
  return (
    <Card className="border-primary/30 bg-primary/5">
      <CardHeader className="pb-3">
        <CardTitle className="flex flex-wrap items-center justify-between gap-2 text-base">
          <span className="flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 text-primary" />
            HNC packet security comparison
          </span>
          <Pill
            label={summary.breaker_passed ? "breaker passed" : "waiting for report"}
            tone={summary.breaker_passed ? statusTone.wired : statusTone.partial}
          />
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="grid gap-2 sm:grid-cols-4">
          <div className="rounded-md border border-border/40 bg-black/20 p-3">
            <div className="text-[11px] uppercase text-muted-foreground">swarm score</div>
            <div className="mt-1 font-mono text-sm font-semibold">{summary.current_swarm_score ?? summary.current_hnc_score ?? "n/a"}/100</div>
          </div>
          <div className="rounded-md border border-border/40 bg-black/20 p-3">
            <div className="text-[11px] uppercase text-muted-foreground">compared</div>
            <div className="mt-1 font-mono text-sm font-semibold">{summary.compared_methods ?? 0} methods</div>
          </div>
          <div className="rounded-md border border-border/40 bg-black/20 p-3">
            <div className="text-[11px] uppercase text-muted-foreground">vs HNC v1</div>
            <div className="mt-1 font-mono text-sm font-semibold">+{summary.swarm_beats_hnc_by ?? 0}</div>
          </div>
          <div className="rounded-md border border-border/40 bg-black/20 p-3">
            <div className="text-[11px] uppercase text-muted-foreground">below KMS/HSM</div>
            <div className="mt-1 font-mono text-sm font-semibold">-{summary.swarm_below_kms_hsm_by ?? summary.below_kms_hsm_by ?? 0}</div>
          </div>
        </div>
        {summary.top_recommendation ? (
          <div className="rounded-md border border-border/40 bg-black/20 p-3 text-xs text-foreground/85">
            <span className="font-semibold">Next security upgrade: </span>
            {summary.top_recommendation}
          </div>
        ) : null}
        <div className="grid gap-2 lg:grid-cols-2">
          {topRows.map((row) => (
            <div key={row.method} className="rounded-md border border-border/40 bg-muted/10 p-3">
              <div className="flex items-center justify-between gap-2">
                <div className="text-sm font-semibold">{row.method}</div>
                <Badge variant="outline">{row.score}/100</Badge>
              </div>
              <div className="mt-2 text-xs text-muted-foreground">{row.aureon_fit}</div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function CapitalEcosystemIntelligencePanel({ ecosystem }: { ecosystem: CapitalEcosystemIntelligenceCompany | null }) {
  const summary = ecosystem?.summary || {};
  const topCandidates = asRecordArray(ecosystem?.top_velocity_candidates);
  const activeWatchlist = asRecordArray(ecosystem?.watchlists?.active_stream_watchlist);
  const shadowHedges = asRecordArray(ecosystem?.shadow_hedges);
  const closeFirst = asRecordArray(ecosystem?.close_first_opportunities);
  const blockers = ((ecosystem?.blockers || []) as string[]).filter(Boolean);
  const ready = String(ecosystem?.status || "").includes("ready") && blockers.length === 0;

  return (
    <Card className="border-primary/30 bg-primary/5">
      <CardHeader className="pb-3">
        <CardTitle className="flex flex-wrap items-center justify-between gap-2 text-base">
          <span className="flex items-center gap-2">
            <LineChart className="h-4 w-4 text-primary" />
            Capital Ecosystem Intelligence
          </span>
          <div className="flex flex-wrap gap-1">
            <Pill label={ready ? "ecosystem ready" : "ecosystem attention"} tone={ready ? statusTone.wired : statusTone.orphaned} />
            <Pill label={`${formatCompact(summary.active_watchlist_count)}/${formatCompact(summary.active_watchlist_limit || 40)} active`} tone="border-primary/30 bg-primary/10 text-primary" />
            <Pill label={`${formatCompact(summary.bench_watchlist_count)}/${formatCompact(summary.bench_watchlist_limit || 100)} bench`} tone="border-border bg-muted/20 text-muted-foreground" />
            <Pill label="/aureon_capital_ecosystem_intelligence_company.json" tone="border-primary/30 bg-primary/10 text-primary" />
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
          {[
            ["Candidates", summary.candidate_count],
            ["Trade ready", summary.trade_ready_candidate_count],
            ["Top velocity", summary.top_velocity_score],
            ["Shadow hedges", summary.shadow_hedge_count],
            ["Close first", summary.close_first_opportunity_count],
            ["Active routes", summary.active_lifecycle_route_count],
            ["GOLD preserved", summary.gold_preserved ? "yes" : "held"],
            ["Runtime gates", summary.existing_runtime_gates_authoritative ? "authoritative" : "attention"],
          ].map(([label, value]) => (
            <div key={String(label)} className="rounded-md border border-border/40 bg-black/20 p-3">
              <div className="text-[11px] uppercase text-muted-foreground">{String(label)}</div>
              <div className="mt-1 font-mono text-sm font-semibold text-primary">
                {typeof value === "number" ? formatCompact(value) : String(value ?? "0")}
              </div>
            </div>
          ))}
        </div>

        <div className="grid gap-3 xl:grid-cols-[1.1fr_0.9fr]">
          <div className="space-y-2">
            <div className="flex items-center justify-between gap-2">
              <div className="text-xs uppercase text-muted-foreground">Top velocity candidates</div>
              <Pill label="fast profit velocity" tone="border-primary/30 bg-primary/10 text-primary" />
            </div>
            <div className="grid gap-2 md:grid-cols-2">
              {topCandidates.length ? topCandidates.slice(0, 8).map((item) => (
                <div key={String(item.candidate_id || item.symbol)} className="rounded-md border border-border/40 bg-muted/10 px-3 py-2 text-xs">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium">{String(item.symbol || item.epic || "capital")}</span>
                    <span className="font-mono text-primary">{formatCompact(item.fast_profit_velocity_score)}</span>
                  </div>
                  <div className="mt-1 truncate text-muted-foreground">
                    {String(item.side || "WATCH")} / {String(item.asset_class || "cfd")} / spread {formatCompact(item.spread_pct)}
                  </div>
                </div>
              )) : (
                <div className="rounded-md border border-border/40 bg-muted/10 p-4 text-sm text-muted-foreground">
                  Capital ecosystem evidence is pending.
                </div>
              )}
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between gap-2">
              <div className="text-xs uppercase text-muted-foreground">Active 40 watchlist</div>
              <Pill label={summary.gold_preserved ? "GOLD kept" : "GOLD held"} tone={summary.gold_preserved ? statusTone.wired : statusTone.orphaned} />
            </div>
            <div className="flex flex-wrap gap-1">
              {activeWatchlist.length ? activeWatchlist.slice(0, 40).map((item) => (
                <Pill key={String(item.candidate_id || item.symbol)} label={String(item.symbol || "capital")} tone="border-border bg-muted/20 text-muted-foreground" />
              )) : (
                <Pill label="watchlist pending" tone={statusTone.orphaned} />
              )}
            </div>
          </div>
        </div>

        <div className="grid gap-3 lg:grid-cols-2">
          <div className="space-y-2">
            <div className="flex items-center justify-between gap-2">
              <div className="text-xs uppercase text-muted-foreground">Shadow hedge map</div>
              <Pill
                label={summary.no_external_hedge_mutation ? "shadow only" : "mutation attention"}
                tone={summary.no_external_hedge_mutation ? statusTone.wired : statusTone.security_blocker}
              />
            </div>
            <div className="grid gap-2">
              {shadowHedges.length ? shadowHedges.slice(0, 6).map((item) => (
                <div key={String(item.hedge_candidate_id || item.target_candidate_id)} className="rounded-md border border-border/40 bg-black/20 px-3 py-2 text-xs">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium">{String(item.source_exchange || "exchange")} -&gt; {String(item.target_symbol || "capital")}</span>
                    <span className="font-mono text-muted-foreground">{formatCompact(item.hedge_confidence)}</span>
                  </div>
                  <div className="mt-1 truncate text-muted-foreground">{String(item.hedge_side || "WATCH")} / {String(item.authority || "shadow_only")}</div>
                </div>
              )) : (
                <div className="rounded-md border border-border/40 bg-muted/10 p-4 text-sm text-muted-foreground">
                  Shadow hedge map pending.
                </div>
              )}
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between gap-2">
              <div className="text-xs uppercase text-muted-foreground">Close-first opportunities</div>
              <Pill label={`${formatCompact(closeFirst.length)} visible`} tone="border-border bg-muted/20 text-muted-foreground" />
            </div>
            <div className="grid gap-2">
              {closeFirst.length ? closeFirst.slice(0, 6).map((item) => (
                <div key={String(item.lifecycle_id || item.route_key)} className="rounded-md border border-border/40 bg-black/20 px-3 py-2 text-xs">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium">{String(item.symbol || "Capital position")}</span>
                    <span className="font-mono text-muted-foreground">{String(item.current_status || "monitor")}</span>
                  </div>
                  <div className="mt-1 truncate text-muted-foreground">{String(item.deal_id || item.route_key || "existing runtime close gate required")}</div>
                </div>
              )) : (
                <div className="rounded-md border border-border/40 bg-muted/10 p-4 text-sm text-muted-foreground">
                  No Capital close-first opportunities are visible in lifecycle state.
                </div>
              )}
            </div>
          </div>
        </div>

        {blockers.length ? (
          <div className="flex flex-wrap gap-1">
            {blockers.slice(0, 8).map((blocker) => (
              <Pill key={blocker} label={blocker.replace(/_/g, " ")} tone={statusTone.security_blocker} />
            ))}
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}

function CapitalThreePMissionPanel({
  ecosystem,
  revenue,
  liveGate,
  liveDry,
}: {
  ecosystem: CapitalEcosystemIntelligenceCompany | null;
  revenue: CapitalRevenueLogicStressAudit | null;
  liveGate: CapitalRevenueLiveGateReadinessAudit | null;
  liveDry: CapitalEcosystemLiveDryStressAudit | null;
}) {
  const ecosystemSummary = ecosystem?.summary || {};
  const revenueSummary = revenue?.summary || {};
  const liveGateSummary = liveGate?.summary || {};
  const liveDrySummary = liveDry?.summary || {};
  const netRows = asRecordArray(revenue?.net_positive_candidates);
  const rejectRows = asRecordArray(revenue?.rejected_false_positives);
  const closeRows = asRecordArray(ecosystem?.close_first_opportunities);
  const shadowRows = asRecordArray(ecosystem?.shadow_hedges);
  const readinessRows = asRecordArray(liveGate?.candidate_readiness_rows);
  const missionBlockers = uniqueStrings([
    ...((revenue?.blockers || []) as string[]),
    ...((liveGate?.blockers || []) as string[]),
    ...((liveDry?.blockers || []) as string[]),
  ]);
  const threePGoal = revenueSummary.three_p_goal ?? ecosystemSummary.three_p_goal ?? liveGateSummary.three_p_goal ?? 0.03;
  const liveArmed = Boolean(liveGateSummary.capital_live_gates_armed ?? revenueSummary.capital_live_gates_armed);
  const readyNow = asNumber(liveGateSummary.ready_now_candidate_count);

  return (
    <Card className="border-success/30 bg-success/5">
      <CardHeader className="pb-3">
        <CardTitle className="flex flex-wrap items-center justify-between gap-2 text-base">
          <span className="flex items-center gap-2">
            <Gauge className="h-4 w-4 text-success" />
            Capital 3p Mission
          </span>
          <div className="flex flex-wrap gap-1">
            <Pill label={`3p floor GBP ${formatCompact(threePGoal)}`} tone="border-success/30 bg-success/10 text-success" />
            <Pill label={liveArmed ? "live gates armed" : "live gates held"} tone={liveArmed ? statusTone.wired : statusTone.orphaned} />
            <Pill label={`${formatCompact(readyNow)} ready now`} tone={readyNow ? statusTone.wired : statusTone.orphaned} />
            <Pill label="read-only evidence" tone="border-primary/30 bg-primary/10 text-primary" />
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-5">
          {[
            ["Universe", ecosystemSummary.candidate_count],
            ["Trade ready", ecosystemSummary.trade_ready_candidate_count],
            ["3p candidates", revenueSummary.three_p_floor_passed_count ?? revenueSummary.net_positive_candidate_count],
            ["Intent eligible", revenueSummary.three_p_intent_eligible_count ?? revenueSummary.intent_eligible_candidate_count],
            ["False rejects", revenueSummary.false_positive_reject_count],
            ["Active watchlist", `${formatCompact(ecosystemSummary.active_watchlist_count)}/${formatCompact(ecosystemSummary.active_watchlist_limit || 40)}`],
            ["Bench", `${formatCompact(ecosystemSummary.bench_watchlist_count)}/${formatCompact(ecosystemSummary.bench_watchlist_limit || 100)}`],
            ["Open positions", liveDrySummary.recovered_position_count ?? ecosystemSummary.active_capital_position_count],
            ["Close first", revenueSummary.three_p_close_opportunity_count ?? ecosystemSummary.close_first_opportunity_count],
            ["Duplicate blocks", revenueSummary.duplicate_route_blocked_count ?? ecosystemSummary.duplicate_route_blocked_count],
            ["Mutation controls", "none"],
          ].map(([label, value]) => (
            <div key={String(label)} className="rounded-md border border-border/40 bg-black/20 p-3">
              <div className="text-[11px] uppercase text-muted-foreground">{String(label)}</div>
              <div className="mt-1 font-mono text-sm font-semibold text-success">
                {typeof value === "number" ? formatCompact(value) : String(value ?? "0")}
              </div>
            </div>
          ))}
        </div>

        <div className="grid gap-3 xl:grid-cols-[1.05fr_0.95fr]">
          <div className="space-y-2">
            <div className="flex items-center justify-between gap-2">
              <div className="text-xs uppercase text-muted-foreground">Top 3p-eligible candidates</div>
              <Pill label="Capital only" tone="border-success/30 bg-success/10 text-success" />
            </div>
            <div className="grid gap-2 md:grid-cols-2">
              {netRows.length ? netRows.slice(0, 8).map((item) => (
                <div key={String(item.candidate_id || item.route_key || item.symbol)} className="rounded-md border border-border/40 bg-muted/10 px-3 py-2 text-xs">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium">{String(item.symbol || item.epic || "capital")}</span>
                    <span className="font-mono text-success">{formatCompact(item.expected_net_revenue)}</span>
                  </div>
                  <div className="mt-1 truncate text-muted-foreground">
                    {String(item.side || "WATCH")} / 3p {String(item.three_p_floor_passed ?? "unknown")} / route {String(item.route_key || "pending")}
                  </div>
                </div>
              )) : (
                <div className="rounded-md border border-border/40 bg-muted/10 p-4 text-sm text-muted-foreground">
                  No Capital candidate currently clears the 3p net floor.
                </div>
              )}
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between gap-2">
              <div className="text-xs uppercase text-muted-foreground">Gate state and rejects</div>
              <Pill label={`${formatCompact(missionBlockers.length)} blockers`} tone={missionBlockers.length ? statusTone.security_blocker : statusTone.wired} />
            </div>
            <div className="grid gap-2">
              {readinessRows.length ? readinessRows.slice(0, 4).map((item) => {
                const missing = Array.isArray(item.missing_live_gate_ids) ? item.missing_live_gate_ids.map((gate) => String(gate)).filter(Boolean) : [];
                return (
                  <div key={String(item.candidate_id || item.route_key || item.symbol)} className="rounded-md border border-border/40 bg-black/20 px-3 py-2 text-xs">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-medium">{String(item.symbol || "candidate")}</span>
                      <Pill label={item.ready_now ? "ready" : "held"} tone={item.ready_now ? statusTone.wired : statusTone.orphaned} />
                    </div>
                    <div className="mt-1 truncate text-muted-foreground">{missing.slice(0, 4).join(", ") || "all live gates clear"}</div>
                  </div>
                );
              }) : rejectRows.length ? rejectRows.slice(0, 4).map((item) => (
                <div key={String(item.candidate_id || item.route_key || item.symbol)} className="rounded-md border border-border/40 bg-black/20 px-3 py-2 text-xs">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium">{String(item.symbol || "reject")}</span>
                    <span className="font-mono text-muted-foreground">{formatCompact(item.expected_net_revenue)}</span>
                  </div>
                  <div className="mt-1 truncate text-muted-foreground">
                    {Array.isArray(item.revenue_blockers) ? item.revenue_blockers.map(String).slice(0, 3).join(", ") : "3p/cost gate"}
                  </div>
                </div>
              )) : (
                <div className="rounded-md border border-border/40 bg-muted/10 p-4 text-sm text-muted-foreground">
                  Live-gate rows are pending.
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="grid gap-3 lg:grid-cols-2">
          <div className="space-y-2">
            <div className="flex items-center justify-between gap-2">
              <div className="text-xs uppercase text-muted-foreground">Close-first rows</div>
              <Pill label={`${formatCompact(closeRows.length)} positions`} tone={closeRows.length ? statusTone.wired : statusTone.orphaned} />
            </div>
            <div className="grid gap-2">
              {closeRows.length ? closeRows.slice(0, 5).map((item) => (
                <div key={String(item.lifecycle_id || item.route_key || item.deal_id)} className="rounded-md border border-border/40 bg-black/20 px-3 py-2 text-xs">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium">{String(item.symbol || "Capital position")}</span>
                    <span className="font-mono text-muted-foreground">{String(item.current_status || "monitor")}</span>
                  </div>
                  <div className="mt-1 truncate text-muted-foreground">{String(item.close_priority || "monitor existing position")}</div>
                </div>
              )) : (
                <div className="rounded-md border border-border/40 bg-muted/10 p-4 text-sm text-muted-foreground">
                  No close-first rows are visible.
                </div>
              )}
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between gap-2">
              <div className="text-xs uppercase text-muted-foreground">Shadow confirmation rows</div>
              <Pill label="no external order intent" tone={statusTone.wired} />
            </div>
            <div className="grid gap-2">
              {shadowRows.length ? shadowRows.slice(0, 5).map((item) => (
                <div key={String(item.hedge_candidate_id || item.target_candidate_id || item.target_symbol)} className="rounded-md border border-border/40 bg-black/20 px-3 py-2 text-xs">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium">{String(item.source_exchange || "exchange")} -&gt; {String(item.target_symbol || "Capital")}</span>
                    <span className="font-mono text-muted-foreground">{formatCompact(item.hedge_confidence)}</span>
                  </div>
                  <div className="mt-1 truncate text-muted-foreground">{String(item.authority || "shadow_only")}</div>
                </div>
              )) : (
                <div className="rounded-md border border-border/40 bg-muted/10 p-4 text-sm text-muted-foreground">
                  Shadow confirmation rows are pending.
                </div>
              )}
            </div>
          </div>
        </div>

        {missionBlockers.length ? (
          <div className="flex flex-wrap gap-1">
            {missionBlockers.slice(0, 12).map((blocker) => (
              <Pill key={blocker} label={blocker.replace(/_/g, " ")} tone={statusTone.security_blocker} />
            ))}
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}

function CapitalThreePLiveExecutionCertificationPanel({ audit }: { audit: CapitalThreePLiveExecutionCertificationAudit | null }) {
  const summary = audit?.summary || {};
  const rows = asRecordArray(audit?.candidate_execution_rows);
  const fresh = asRecord(audit?.fresh_snapshot_proof);
  const duplicate = asRecord(audit?.duplicate_route_proof);
  const recovered = asRecord(audit?.recovered_exit_proof);
  const broker = asRecord(audit?.capital_broker_requirement_proof);
  const external = asRecord(audit?.external_confirmation_requirement_proof);
  const executor = asRecord(audit?.live_executor_readiness);
  const blockers = ((audit?.blockers || []) as string[]).filter(Boolean);
  const ready = audit?.status === "capital_3p_live_execution_certified" && blockers.length === 0;
  const statusLabel = String(audit?.status || "3p execution pending").replace(/_/g, " ");
  const rowBlockers = (value: unknown) => (Array.isArray(value) ? value.map((item) => String(item)).filter(Boolean) : []);

  return (
    <Card className="border-success/30 bg-success/5">
      <CardHeader className="pb-3">
        <CardTitle className="flex flex-wrap items-center justify-between gap-2 text-base">
          <span className="flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 text-success" />
            3p Live Execution Certification
          </span>
          <div className="flex flex-wrap gap-1">
            <Pill label={statusLabel} tone={ready ? statusTone.wired : statusTone.orphaned} />
            <Pill label={`${formatCompact(summary.ready_for_intent_count)} ready for intent`} tone={summary.ready_for_intent_count ? statusTone.wired : statusTone.orphaned} />
            <Pill label={`${formatCompact(summary.net_positive_candidate_count)} 3p candidates`} tone="border-success/30 bg-success/10 text-success" />
            <Pill label="/aureon_capital_3p_live_execution_certification_audit.json" tone="border-primary/30 bg-primary/10 text-primary" />
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-5">
          {[
            ["3p floor", `GBP ${formatCompact(summary.three_p_goal ?? 0.03)}`],
            ["Fresh snapshots", summary.fresh_snapshot_candidate_count],
            ["Duplicate blocks", summary.duplicate_route_blocked_count],
            ["Recovered positions", summary.recovered_position_count],
            ["Recovered exit", summary.recovered_exit_clear ? "clear" : "held"],
            ["Live gates", summary.capital_live_gates_armed ? "armed" : "held"],
            ["Executor", summary.executor_ready ? "ready" : "held"],
            ["Broker proof", summary.capital_broker_requirements_certified ? "certified" : "attention"],
            ["External", summary.no_external_mutation ? "shadow only" : "attention"],
            ["Mutation controls", "none"],
          ].map(([label, value]) => (
            <div key={String(label)} className="rounded-md border border-border/40 bg-black/20 p-3">
              <div className="text-[11px] uppercase text-muted-foreground">{String(label)}</div>
              <div className="mt-1 font-mono text-sm font-semibold text-success">
                {typeof value === "number" ? formatCompact(value) : String(value ?? "0")}
              </div>
            </div>
          ))}
        </div>

        <div className="grid gap-3 xl:grid-cols-[1.15fr_0.85fr]">
          <div className="space-y-2">
            <div className="flex items-center justify-between gap-2">
              <div className="text-xs uppercase text-muted-foreground">Why not live now</div>
              <Pill label="existing executor path only" tone="border-success/30 bg-success/10 text-success" />
            </div>
            <div className="grid gap-2 md:grid-cols-2">
              {rows.length ? rows.slice(0, 8).map((item) => {
                const missing = rowBlockers(item.missing_execution_gate_ids);
                return (
                  <div key={String(item.candidate_id || item.route_key || item.symbol)} className="rounded-md border border-border/40 bg-muted/10 px-3 py-2 text-xs">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-medium">{String(item.symbol || item.epic || "capital")}</span>
                      <span className="font-mono text-success">{formatCompact(item.expected_net_revenue)}</span>
                    </div>
                    <div className="mt-1 truncate text-muted-foreground">
                      {String(item.side || "WATCH")} / {String(item.execution_state || "blocked before intent").replace(/_/g, " ")}
                    </div>
                    <div className="mt-2 flex flex-wrap gap-1">
                      {missing.length ? missing.slice(0, 5).map((gate) => (
                        <Pill key={gate} label={gate.replace(/_/g, " ")} tone={statusTone.security_blocker} />
                      )) : (
                        <Pill label="ready for existing executor intent" tone={statusTone.wired} />
                      )}
                    </div>
                    {item.next_required_evidence ? (
                      <div className="mt-2 text-muted-foreground">{String(item.next_required_evidence)}</div>
                    ) : null}
                  </div>
                );
              }) : (
                <div className="rounded-md border border-border/40 bg-muted/10 p-4 text-sm text-muted-foreground">
                  No net-positive 3p Capital candidates are visible.
                </div>
              )}
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between gap-2">
              <div className="text-xs uppercase text-muted-foreground">Capital broker proof</div>
              <Pill label={summary.capital_broker_requirements_certified ? "stress certified" : "attention"} tone={summary.capital_broker_requirements_certified ? statusTone.wired : statusTone.orphaned} />
            </div>
            <div className="grid gap-2">
              {[
                ["watchlist", `${formatCompact(fresh.active_watchlist_count)}/${formatCompact(fresh.active_watchlist_limit || 40)} epics`],
                ["snapshot proof", `${formatCompact(fresh.fresh_snapshot_candidate_count)} fresh / ${formatCompact(fresh.stale_snapshot_candidate_count)} stale`],
                ["active routes", formatCompact(duplicate.active_lifecycle_count)],
                ["recovered chain", String(recovered.recovered_close_chain_status || "unknown").replace(/_/g, " ")],
                ["close requests", formatCompact(recovered.recovered_close_request_count)],
                ["outcomes", formatCompact(recovered.recovered_outcome_recorded_count)],
                ["deal id rule", broker.deal_id_required ? "required" : "attention"],
                ["position absence", broker.position_absence_and_pnl_required_for_close ? "plus P/L" : "attention"],
                ["external venues", external.external_shadow_only ? "confirmation only" : "attention"],
                ["executor packet", String(executor.order_intent_packet_status || "unknown").replace(/_/g, " ")],
              ].map(([label, value]) => (
                <div key={String(label)} className="rounded-md border border-border/40 bg-black/20 px-3 py-2 text-xs">
                  <div className="flex items-center justify-between gap-2">
                    <span className="uppercase text-muted-foreground">{String(label)}</span>
                    <span className="font-mono text-foreground/90">{String(value ?? "0")}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {blockers.length ? (
          <div className="flex flex-wrap gap-1">
            {blockers.slice(0, 12).map((blocker) => (
              <Pill key={blocker} label={blocker.replace(/_/g, " ")} tone={statusTone.security_blocker} />
            ))}
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}

function CapitalThreePBlockerBurndownPanel({ audit }: { audit: CapitalThreePBlockerBurndownAudit | null }) {
  const summary = audit?.summary || {};
  const rows = asRecordArray(audit?.candidate_burndown_rows);
  const guard = asRecord(audit?.capital_only_execution_guard);
  const runtime = asRecord(audit?.runtime_reconciliation);
  const fresh = asRecord(audit?.fresh_snapshot_proof);
  const duplicate = asRecord(audit?.duplicate_route_proof);
  const recovered = asRecord(audit?.recovered_exit_proof);
  const externalRows = asRecordArray(audit?.external_confirmation_rows);
  const blockers = ((audit?.blockers || []) as string[]).filter(Boolean);
  const ready = audit?.status === "capital_3p_ready" && blockers.length === 0;
  const statusLabel = String(audit?.status || "3p burn-down pending").replace(/_/g, " ");
  const rowBlockers = (value: unknown) => (Array.isArray(value) ? value.map((item) => String(item)).filter(Boolean) : []);

  return (
    <Card className="border-warning/30 bg-warning/5">
      <CardHeader className="pb-3">
        <CardTitle className="flex flex-wrap items-center justify-between gap-2 text-base">
          <span className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-warning" />
            3p Blocker Burn-Down
          </span>
          <div className="flex flex-wrap gap-1">
            <Pill label={statusLabel} tone={ready ? statusTone.wired : statusTone.security_blocker} />
            <Pill label={`${formatCompact(summary.ready_for_capital_intent_count)} ready`} tone={summary.ready_for_capital_intent_count ? statusTone.wired : statusTone.orphaned} />
            <Pill label={`${formatCompact(summary.blocker_count)} blockers`} tone={summary.blocker_count ? statusTone.security_blocker : statusTone.wired} />
            <Pill label="/aureon_capital_3p_blocker_burndown_audit.json" tone="border-primary/30 bg-primary/10 text-primary" />
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-5">
          {[
            ["3p floor", `GBP ${formatCompact(summary.three_p_goal ?? 0.03)}`],
            ["Candidates", summary.candidate_count],
            ["Fresh / stale", `${formatCompact(summary.fresh_snapshot_candidate_count)} / ${formatCompact(summary.stale_snapshot_candidate_count)}`],
            ["Duplicate routes", summary.duplicate_route_blocked_count],
            ["Recovered positions", summary.recovered_position_count],
            ["Recovered exit", summary.recovered_exit_clear ? "clear" : "held"],
            ["External intents", summary.external_live_intent_count],
            ["External attempts", summary.external_executor_attempt_count],
            ["Capital-only", summary.capital_only_live_execution ? "yes" : "no"],
            ["Mutation from audit", summary.no_broker_mutation_from_audit ? "none" : "attention"],
          ].map(([label, value]) => (
            <div key={String(label)} className="rounded-md border border-border/40 bg-black/20 p-3">
              <div className="text-[11px] uppercase text-muted-foreground">{String(label)}</div>
              <div className="mt-1 font-mono text-sm font-semibold text-warning">
                {typeof value === "number" ? formatCompact(value) : String(value ?? "0")}
              </div>
            </div>
          ))}
        </div>

        <div className="grid gap-3 xl:grid-cols-[1.2fr_0.8fr]">
          <div className="space-y-2">
            <div className="flex items-center justify-between gap-2">
              <div className="text-xs uppercase text-muted-foreground">Capital candidate burn-down</div>
              <Pill label="Capital executor only" tone="border-warning/30 bg-warning/10 text-warning" />
            </div>
            <div className="grid gap-2 md:grid-cols-2">
              {rows.length ? rows.slice(0, 8).map((item) => {
                const missing = rowBlockers(item.missing_burndown_gate_ids);
                return (
                  <div key={String(item.candidate_id || item.route_key || item.symbol)} className="rounded-md border border-border/40 bg-muted/10 px-3 py-2 text-xs">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-medium">{String(item.symbol || item.epic || "capital")}</span>
                      <span className="font-mono text-warning">{formatCompact(item.expected_net_revenue)}</span>
                    </div>
                    <div className="mt-1 truncate text-muted-foreground">
                      {String(item.side || "WATCH")} / {String(item.route_key || "route pending")}
                    </div>
                    <div className="mt-2 grid grid-cols-2 gap-1 text-[11px] text-muted-foreground">
                      <span>bid/ask {item.bid_ask_fresh ? "fresh" : "stale"}</span>
                      <span>OHLC {item.ohlc_profile_fresh ? "fresh" : "stale"}</span>
                      <span>route {item.active_route_conflict ? "blocked" : "clear"}</span>
                      <span>lifecycle {String(item.lifecycle_state || "unknown").replace(/_/g, " ")}</span>
                    </div>
                    <div className="mt-2 flex flex-wrap gap-1">
                      {missing.length ? missing.slice(0, 5).map((gate) => (
                        <Pill key={gate} label={gate.replace(/_/g, " ")} tone={statusTone.security_blocker} />
                      )) : (
                        <Pill label="ready for Capital intent" tone={statusTone.wired} />
                      )}
                    </div>
                    {item.next_required_evidence ? (
                      <div className="mt-2 text-muted-foreground">{String(item.next_required_evidence)}</div>
                    ) : null}
                  </div>
                );
              }) : (
                <div className="rounded-md border border-border/40 bg-muted/10 p-4 text-sm text-muted-foreground">
                  No Capital 3p burn-down candidates are visible.
                </div>
              )}
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between gap-2">
              <div className="text-xs uppercase text-muted-foreground">Runtime reconciliation</div>
              <Pill label={runtime.runtime_artifact_mismatch ? "mismatch" : "reconciled"} tone={runtime.runtime_artifact_mismatch ? statusTone.security_blocker : statusTone.wired} />
            </div>
            <div className="grid gap-2">
              {[
                ["watchlist", `${formatCompact(fresh.active_watchlist_count)}/${formatCompact(fresh.active_watchlist_limit || 40)} epics`],
                ["stream limit", fresh.watchlist_within_capital_stream_limit ? "within limit" : "over limit"],
                ["active routes", formatCompact(duplicate.active_lifecycle_route_count)],
                ["duplicate rule", String(duplicate.clearance_rule || "broker absence/outcome")],
                ["recovered chain", String(recovered.recovered_close_chain_status || "unknown").replace(/_/g, " ")],
                ["live gates", runtime.live_gates_armed ? "armed" : "held"],
                ["external live rows", formatCompact((guard.external_live_rows as unknown[] | undefined)?.length || 0)],
                ["shadow rows", formatCompact(summary.shadow_confirmation_count)],
                ["artifact match", runtime.runtime_artifact_mismatch ? "attention" : "ok"],
              ].map(([label, value]) => (
                <div key={String(label)} className="rounded-md border border-border/40 bg-black/20 px-3 py-2 text-xs">
                  <div className="flex items-center justify-between gap-2">
                    <span className="uppercase text-muted-foreground">{String(label)}</span>
                    <span className="max-w-[12rem] truncate text-right font-mono text-foreground/90">{String(value ?? "0")}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {externalRows.some((row) => String(row.status || "").includes("leak")) ? (
          <div className="space-y-2">
            <div className="text-xs uppercase text-muted-foreground">External route leak evidence</div>
            <div className="grid gap-2 md:grid-cols-3">
              {externalRows.filter((row) => String(row.status || "").includes("leak")).slice(0, 6).map((item, index) => (
                <div key={`${String(item.route_key || item.venue || "external")}-${index}`} className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium">{String(item.venue || "external")}</span>
                    <span className="font-mono text-destructive">{String(item.leak_type || "leak").replace(/_/g, " ")}</span>
                  </div>
                  <div className="mt-1 truncate text-muted-foreground">{String(item.route_key || item.symbol || "route missing")}</div>
                  {item.reason ? <div className="mt-1 text-muted-foreground">{String(item.reason)}</div> : null}
                </div>
              ))}
            </div>
          </div>
        ) : null}

        {blockers.length ? (
          <div className="flex flex-wrap gap-1">
            {blockers.slice(0, 12).map((blocker) => (
              <Pill key={blocker} label={blocker.replace(/_/g, " ")} tone={statusTone.security_blocker} />
            ))}
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}

function PerformanceReadinessPanel({ audit }: { audit: PerformanceReadinessAudit | null }) {
  const summary = audit?.summary || {};
  const scriptRows = asRecordArray(audit?.script_wiring);
  const artifactRows: Array<Record<string, unknown> & { key: string; present?: unknown; path?: unknown }> = Object.entries(audit?.artifact_wiring || {}).map(([key, value]) => ({
    key,
    ...asRecord(value),
  }));
  const blockers = ((audit?.blockers || []) as string[]).filter(Boolean);
  const ready = audit?.status === "performance_readiness_wired" && blockers.length === 0;
  const statusLabel = String(audit?.status || "performance readiness pending").replace(/_/g, " ");
  const refsCount = (value: unknown) => (Array.isArray(value) ? value.length : 0);
  const allScriptsWired = Boolean(summary.script_count && summary.scripts_wired_count === summary.script_count);

  return (
    <Card className="border-primary/30 bg-primary/5">
      <CardHeader className="pb-3">
        <CardTitle className="flex flex-wrap items-center justify-between gap-2 text-base">
          <span className="flex items-center gap-2">
            <Gauge className="h-4 w-4 text-primary" />
            Performance Readiness
          </span>
          <div className="flex flex-wrap gap-1">
            <Pill label={statusLabel} tone={ready ? statusTone.wired : statusTone.orphaned} />
            <Pill label={`${formatCompact(summary.scripts_wired_count)}/${formatCompact(summary.script_count)} scripts`} tone={allScriptsWired ? statusTone.wired : statusTone.orphaned} />
            <Pill label={summary.no_broker_mutation ? "no broker mutation" : "mutation check attention"} tone={summary.no_broker_mutation ? statusTone.wired : statusTone.security_blocker} />
            <Pill label="/aureon_performance_readiness_audit.json" tone="border-primary/30 bg-primary/10 text-primary" />
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-5">
          {[
            ["Organism registered", `${formatCompact(summary.organism_registered_count)}/${formatCompact(summary.script_count)}`],
            ["Artifacts present", `${formatCompact(summary.artifact_present_count)}/${formatCompact(summary.artifact_count)}`],
            ["Super sweep", summary.super_sweep_pass ? `pass ${summary.super_sweep_steps || ""}` : "attention"],
            ["Full suite", summary.full_suite_pass ? "pass" : "attention"],
            ["Latency p95", `${formatCompact(summary.latency_p95_observed_ms)} / ${formatCompact(summary.latency_p95_budget_ms)} ms`],
            ["Threshold cases", `${formatCompact(summary.threshold_pass_cases)} pass / ${formatCompact(summary.threshold_fail_cases)} fail`],
            ["API exchanges", summary.api_concurrency_valid_exchange_count],
            ["Calls/min", summary.api_concurrency_total_recommended_calls_per_min],
            ["Rate benchmark", `${formatCompact(summary.api_rate_benchmark_valid_exchange_count)} valid`],
            ["Blockers", summary.blocker_count],
          ].map(([label, value]) => (
            <div key={String(label)} className="rounded-md border border-border/40 bg-black/20 p-3">
              <div className="text-[11px] uppercase text-muted-foreground">{String(label)}</div>
              <div className="mt-1 font-mono text-sm font-semibold text-primary">
                {typeof value === "number" ? formatCompact(value) : String(value ?? "0")}
              </div>
            </div>
          ))}
        </div>

        <div className="grid gap-3 xl:grid-cols-[1.15fr_0.85fr]">
          <div className="space-y-2">
            <div className="flex items-center justify-between gap-2">
              <div className="text-xs uppercase text-muted-foreground">Latest diagnostic scripts</div>
              <Pill label="organism validation domain" tone="border-primary/30 bg-primary/10 text-primary" />
            </div>
            <div className="grid gap-2 md:grid-cols-2">
              {scriptRows.length ? scriptRows.map((row) => {
                const wired = Boolean(row.wired);
                return (
                  <div key={String(row.path || row.module)} className="rounded-md border border-border/40 bg-muted/10 px-3 py-2 text-xs">
                    <div className="flex items-center justify-between gap-2">
                      <span className="truncate font-medium">{String(row.path || "diagnostic")}</span>
                      <Pill label={wired ? "wired" : "attention"} tone={wired ? statusTone.wired : statusTone.orphaned} />
                    </div>
                    <div className="mt-1 truncate text-muted-foreground">{String(row.module || "module pending")}</div>
                    <div className="mt-2 grid grid-cols-2 gap-1 text-[11px] text-muted-foreground">
                      <span>present {row.present ? "yes" : "no"}</span>
                      <span>organism {row.organism_registered ? "yes" : "no"}</span>
                      <span>refs {formatCompact(refsCount(row.referenced_by))}</span>
                      <span className="truncate">{String(row.organism_topic || "topic pending")}</span>
                    </div>
                  </div>
                );
              }) : (
                <div className="rounded-md border border-border/40 bg-muted/10 p-4 text-sm text-muted-foreground">
                  Performance diagnostic wiring has not published yet.
                </div>
              )}
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between gap-2">
              <div className="text-xs uppercase text-muted-foreground">Generated stress artifacts</div>
              <Pill label={summary.full_suite_pass ? "suite passing" : "suite attention"} tone={summary.full_suite_pass ? statusTone.wired : statusTone.orphaned} />
            </div>
            <div className="grid gap-2">
              {artifactRows.slice(0, 10).map((row) => (
                <div key={String(row.key)} className="rounded-md border border-border/40 bg-black/20 px-3 py-2 text-xs">
                  <div className="flex items-center justify-between gap-2">
                    <span className="truncate uppercase text-muted-foreground">{String(row.key).replace(/_/g, " ")}</span>
                    <span className={row.present ? "font-mono text-primary" : "font-mono text-warning"}>{row.present ? "present" : "missing"}</span>
                  </div>
                  <div className="mt-1 truncate text-muted-foreground">{String(row.path || "")}</div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {blockers.length ? (
          <div className="flex flex-wrap gap-1">
            {blockers.slice(0, 12).map((blocker) => (
              <Pill key={blocker} label={blocker.replace(/_/g, " ")} tone={statusTone.security_blocker} />
            ))}
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}

function AureonMurgeUnityPanel({ bridge }: { bridge: AureonMurgeUnityBridge | null }) {
  const summary = bridge?.summary || {};
  const tracks = asRecordArray(bridge?.unity_track_rows);
  const adapters = asRecordArray(bridge?.organism_adapter_rows);
  const collisions = asRecordArray(bridge?.collision_rows);
  const requirements = asRecordArray(bridge?.online_requirement_baseline);
  const actions = asRecordArray(bridge?.next_unity_actions);
  const blockers = ((bridge?.blockers || []) as string[]).filter(Boolean);
  const ready = Boolean(summary.unity_ready) && blockers.length === 0;
  const statusLabel = String(bridge?.status || "unity bridge pending").replace(/_/g, " ");

  return (
    <Card className="border-primary/30 bg-primary/5">
      <CardHeader className="pb-3">
        <CardTitle className="flex flex-wrap items-center justify-between gap-2 text-base">
          <span className="flex items-center gap-2">
            <Server className="h-4 w-4 text-primary" />
            Aureon MURGE Unity Bridge
          </span>
          <div className="flex flex-wrap gap-1">
            <Pill label={statusLabel} tone={ready ? statusTone.wired : statusTone.orphaned} />
            <Pill label={`${formatCompact(summary.staged_track_count)}/${formatCompact(summary.track_count)} tracks staged`} tone="border-primary/30 bg-primary/10 text-primary" />
            <Pill label={`${formatCompact(summary.collision_count)} collisions`} tone={summary.collision_count ? statusTone.security_blocker : statusTone.wired} />
            <Pill label="/aureon_murge_unity_bridge.json" tone="border-primary/30 bg-primary/10 text-primary" />
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-6">
          {[
            ["tracks", summary.track_count],
            ["staged", summary.staged_track_count],
            ["missing", summary.missing_track_count],
            ["adapters", summary.adapter_row_count],
            ["online gates", summary.online_requirement_count],
            ["hidden activation", summary.hidden_activation ? "yes" : "no"],
          ].map(([label, value]) => (
            <div key={String(label)} className="rounded-md border border-border/40 bg-black/20 p-3">
              <div className="text-[11px] uppercase text-muted-foreground">{String(label)}</div>
              <div className="mt-1 font-mono text-sm font-semibold text-primary">
                {typeof value === "number" ? formatCompact(value) : String(value ?? "0")}
              </div>
            </div>
          ))}
        </div>

        <div className="grid gap-3 xl:grid-cols-[1.05fr_0.95fr]">
          <div className="space-y-2">
            <div className="flex items-center justify-between gap-2">
              <div className="text-xs uppercase text-muted-foreground">Unity tracks</div>
              <Pill label="namespaced, no overwrite" tone="border-primary/30 bg-primary/10 text-primary" />
            </div>
            <div className="grid gap-2 md:grid-cols-2">
              {tracks.length ? tracks.slice(0, 8).map((row) => (
                <div key={String(row.track_id || row.target)} className="rounded-md border border-border/40 bg-muted/10 px-3 py-2 text-xs">
                  <div className="flex items-center justify-between gap-2">
                    <span className="truncate font-medium">{String(row.track_id || "track").replace(/_/g, " ")}</span>
                    <Pill label={row.staged ? "staged" : "missing"} tone={row.staged ? statusTone.wired : statusTone.security_blocker} />
                  </div>
                  <div className="mt-1 truncate text-muted-foreground">{String(row.target || row.path || "")}</div>
                  <div className="mt-1 font-mono text-[11px] text-muted-foreground">{formatCompact(row.file_count)} files</div>
                </div>
              )) : (
                <div className="rounded-md border border-border/40 bg-muted/10 p-4 text-sm text-muted-foreground">
                  MURGE unity tracks are pending.
                </div>
              )}
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between gap-2">
              <div className="text-xs uppercase text-muted-foreground">Adapter relation</div>
              <Pill label={`${formatCompact(adapters.length)} rows`} tone="border-primary/30 bg-primary/10 text-primary" />
            </div>
            <div className="grid gap-2">
              {adapters.length ? adapters.slice(0, 6).map((row) => (
                <div key={String(row.track_id)} className="rounded-md border border-border/40 bg-black/20 px-3 py-2 text-xs">
                  <div className="flex items-center justify-between gap-2">
                    <span className="truncate font-medium">{String(row.track_id || "adapter").replace(/_/g, " ")}</span>
                    <span className="font-mono text-muted-foreground">{String(row.status || "pending")}</span>
                  </div>
                  <div className="mt-1 truncate text-muted-foreground">{String(row.adapter || "adapter path pending")}</div>
                </div>
              )) : (
                <div className="rounded-md border border-border/40 bg-muted/10 p-4 text-sm text-muted-foreground">
                  Adapter rows are pending.
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="grid gap-3 lg:grid-cols-3">
          <div className="space-y-2">
            <div className="text-xs uppercase text-muted-foreground">Collision review</div>
            <div className="grid gap-2">
              {collisions.length ? collisions.slice(0, 4).map((row) => (
                <div key={String(row.path)} className="rounded-md border border-border/40 bg-black/20 px-3 py-2 text-xs">
                  <div className="font-medium">{String(row.path || "collision")}</div>
                  <div className="mt-1 truncate text-muted-foreground">{String(row.merge_action || row.collision_reason || "review required")}</div>
                </div>
              )) : (
                <div className="rounded-md border border-border/40 bg-muted/10 p-4 text-sm text-muted-foreground">
                  No direct path collisions.
                </div>
              )}
            </div>
          </div>

          <div className="space-y-2">
            <div className="text-xs uppercase text-muted-foreground">Online baseline</div>
            <div className="grid gap-2">
              {requirements.slice(0, 4).map((row) => (
                <div key={String(row.surface)} className="rounded-md border border-border/40 bg-black/20 px-3 py-2 text-xs">
                  <div className="font-medium">{String(row.surface || "requirement").replace(/_/g, " ")}</div>
                  <div className="mt-1 truncate text-muted-foreground">{String(row.unity_gate || row.source || "")}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="space-y-2">
            <div className="text-xs uppercase text-muted-foreground">Next unity actions</div>
            <div className="grid gap-2">
              {actions.slice(0, 5).map((row) => (
                <div key={String(row.id)} className="rounded-md border border-border/40 bg-black/20 px-3 py-2 text-xs">
                  <div className="font-mono text-primary">{String(row.priority || "P?")} {String(row.id || "")}</div>
                  <div className="mt-1 text-muted-foreground">{String(row.action || "wire next adapter")}</div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {blockers.length ? (
          <div className="flex flex-wrap gap-1">
            {blockers.slice(0, 10).map((blocker) => (
              <Pill key={blocker} label={blocker.replace(/_/g, " ")} tone={statusTone.security_blocker} />
            ))}
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}

function AureonMurgeRuntimeActivationPanel({ audit }: { audit: AureonMurgeRuntimeActivationStressAudit | null }) {
  const summary = audit?.summary || {};
  const services = asRecordArray(audit?.activation_service_rows);
  const gates = asRecordArray(audit?.activation_gate_rows);
  const dependencies = asRecordArray(audit?.dependency_readiness_rows);
  const launchLogs = asRecordArray(audit?.launch_log_rows);
  const npmAuditRows = asRecordArray(audit?.npm_audit_rows);
  const terminalRows = asRecordArray(audit?.terminal_sandbox_guard_rows);
  const electronRows = asRecordArray(audit?.electron_security_rows);
  const windowsRows = asRecordArray(audit?.windows_compatibility_rows);
  const actions = asRecordArray(audit?.next_activation_actions);
  const blockers = ((audit?.blockers || []) as string[]).filter(Boolean);
  const ready = Boolean(summary.local_launch_ready) && blockers.length === 0;
  const statusLabel = String(audit?.status || "runtime activation pending").replace(/_/g, " ");

  return (
    <Card className="border-primary/30 bg-primary/5">
      <CardHeader className="pb-3">
        <CardTitle className="flex flex-wrap items-center justify-between gap-2 text-base">
          <span className="flex items-center gap-2">
            <Radio className="h-4 w-4 text-primary" />
            MURGE Runtime Activation
          </span>
          <div className="flex flex-wrap gap-1">
            <Pill label={statusLabel} tone={ready ? statusTone.wired : statusTone.orphaned} />
            <Pill label={`${formatCompact(summary.service_health_pass_count)}/${formatCompact(summary.service_count)} health`} tone={summary.service_health_pass_count === summary.service_count ? statusTone.wired : statusTone.orphaned} />
            <Pill label={summary.no_trading_gate_bypass ? "no trading bypass" : "gate attention"} tone={summary.no_trading_gate_bypass ? statusTone.wired : statusTone.security_blocker} />
            <Pill label="/aureon_murge_runtime_activation_stress_audit.json" tone="border-primary/30 bg-primary/10 text-primary" />
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-6">
          {[
            ["services", `${formatCompact(summary.service_present_count)}/${formatCompact(summary.service_count)}`],
            ["dependencies", `${formatCompact(summary.dependency_ready_count)}/${formatCompact(summary.dependency_check_count)}`],
            ["npm high", summary.npm_high_vulnerability_count],
            ["web health", summary.web_health_passed ? "pass" : "pending"],
            ["runtime health", summary.runtime_health_passed ? "pass" : "pending"],
            ["terminal guards", `${formatCompact(summary.terminal_guard_passing_count)}/${formatCompact(summary.terminal_guard_count)}`],
            ["electron", `${formatCompact(summary.electron_security_pass_count)}/${formatCompact(summary.electron_security_check_count)}`],
            ["collisions", summary.collision_count],
          ].map(([label, value]) => (
            <div key={String(label)} className="rounded-md border border-border/40 bg-black/20 p-3">
              <div className="text-[11px] uppercase text-muted-foreground">{String(label)}</div>
              <div className="mt-1 font-mono text-sm font-semibold text-primary">
                {typeof value === "number" ? formatCompact(value) : String(value ?? "0")}
              </div>
            </div>
          ))}
        </div>

        <div className="grid gap-3 xl:grid-cols-[1.1fr_0.9fr]">
          <div className="space-y-2">
            <div className="flex items-center justify-between gap-2">
              <div className="text-xs uppercase text-muted-foreground">Local services</div>
              <Pill label="localhost only" tone="border-primary/30 bg-primary/10 text-primary" />
            </div>
            <div className="grid gap-2 md:grid-cols-3">
              {services.length ? services.map((row) => (
                <div key={String(row.id)} className="rounded-md border border-border/40 bg-muted/10 px-3 py-2 text-xs">
                  <div className="flex items-center justify-between gap-2">
                    <span className="truncate font-medium">{String(row.label || row.id || "service")}</span>
                    <Pill label={String(row.status || "pending").replace(/_/g, " ")} tone={row.health_ok ? statusTone.wired : row.present ? statusTone.orphaned : statusTone.security_blocker} />
                  </div>
                  <div className="mt-1 truncate font-mono text-[11px] text-muted-foreground">{String(row.command || "")}</div>
                  <div className="mt-1 text-[11px] text-muted-foreground">port {String(row.port || "n/a")}</div>
                </div>
              )) : (
                <div className="rounded-md border border-border/40 bg-muted/10 p-4 text-sm text-muted-foreground">
                  Activation service rows are pending.
                </div>
              )}
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between gap-2">
              <div className="text-xs uppercase text-muted-foreground">Activation gates</div>
              <Pill label={`${formatCompact(summary.activation_gate_enabled_count)} enabled`} tone={summary.activation_gate_enabled_count ? statusTone.orphaned : statusTone.wired} />
            </div>
            <div className="grid gap-2">
              {gates.map((row) => (
                <div key={String(row.gate)} className="rounded-md border border-border/40 bg-black/20 px-3 py-2 text-xs">
                  <div className="flex items-center justify-between gap-2">
                    <span className="truncate font-mono">{String(row.gate || "gate")}</span>
                    <Pill label={row.enabled ? "enabled" : "guarded off"} tone={row.enabled ? statusTone.orphaned : statusTone.wired} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="grid gap-3 lg:grid-cols-2">
          <div className="space-y-2">
            <div className="flex items-center justify-between gap-2">
              <div className="text-xs uppercase text-muted-foreground">Dependency readiness</div>
              <Pill label="npm ci lockfile baseline" tone="border-primary/30 bg-primary/10 text-primary" />
            </div>
            <div className="grid gap-2">
              {dependencies.length ? dependencies.map((row) => {
                const missing = Array.isArray(row.missing_modules) ? row.missing_modules.map(String).filter(Boolean) : [];
                return (
                  <div key={String(row.id)} className="rounded-md border border-border/40 bg-black/20 px-3 py-2 text-xs">
                    <div className="flex items-center justify-between gap-2">
                      <span className="truncate font-medium">{String(row.id || "dependencies").replace(/_/g, " ")}</span>
                      <Pill label={String(row.status || "pending").replace(/_/g, " ")} tone={missing.length ? statusTone.orphaned : statusTone.wired} />
                    </div>
                    <div className="mt-1 truncate font-mono text-[11px] text-muted-foreground">{String(row.install_command || "npm ci")}</div>
                    {missing.length ? <div className="mt-1 line-clamp-2 text-muted-foreground">missing {missing.slice(0, 5).join(", ")}</div> : null}
                  </div>
                );
              }) : (
                <div className="rounded-md border border-border/40 bg-muted/10 p-4 text-sm text-muted-foreground">
                  Dependency readiness rows are pending.
                </div>
              )}
            </div>
          </div>
          <div className="space-y-2">
            <div className="text-xs uppercase text-muted-foreground">NPM audit and launch logs</div>
            <div className="grid gap-2">
              {npmAuditRows.length ? npmAuditRows.map((row) => (
                <div key={String(row.id)} className="rounded-md border border-border/40 bg-black/20 px-3 py-2 text-xs">
                  <div className="flex items-center justify-between gap-2">
                    <span className="truncate font-medium">{String(row.id || "npm audit").replace(/_/g, " ")}</span>
                    <Pill label={String(row.status || "pending").replace(/_/g, " ")} tone={asNumber(row.high_vulnerabilities) || asNumber(row.critical_vulnerabilities) ? statusTone.security_blocker : statusTone.wired} />
                  </div>
                  <div className="mt-1 text-muted-foreground">
                    high {formatCompact(row.high_vulnerabilities)} / critical {formatCompact(row.critical_vulnerabilities)} / total {formatCompact(row.total_vulnerabilities)}
                  </div>
                </div>
              )) : null}
              {launchLogs.length ? launchLogs.map((row) => (
                <div key={String(row.service)} className="rounded-md border border-border/40 bg-black/20 px-3 py-2 text-xs">
                  <div className="flex items-center justify-between gap-2">
                    <span className="truncate font-medium">{String(row.service || "service")}</span>
                    <span className="font-mono text-muted-foreground">{String(row.status || "pending")}</span>
                  </div>
                  <div className="mt-1 truncate text-muted-foreground">{String(row.stderr_path || row.stdout_path || "")}</div>
                </div>
              )) : null}
            </div>
          </div>
        </div>

        <div className="grid gap-3 lg:grid-cols-3">
          <div className="space-y-2">
            <div className="text-xs uppercase text-muted-foreground">Windows guard</div>
            <div className="grid gap-2">
              {windowsRows.slice(0, 4).map((row) => (
                <div key={String(row.id)} className="rounded-md border border-border/40 bg-black/20 px-3 py-2 text-xs">
                  <div className="font-medium">{String(row.id || "windows").replace(/_/g, " ")}</div>
                  <div className="mt-1 truncate text-muted-foreground">{String(row.status || row.platform || "pending")}</div>
                </div>
              ))}
            </div>
          </div>
          <div className="space-y-2">
            <div className="text-xs uppercase text-muted-foreground">Terminal and sandbox</div>
            <div className="grid gap-2">
              {terminalRows.map((row) => (
                <div key={String(row.surface)} className="rounded-md border border-border/40 bg-black/20 px-3 py-2 text-xs">
                  <div className="flex items-center justify-between gap-2">
                    <span className="truncate">{String(row.surface || "surface").replace(/_/g, " ")}</span>
                    <Pill label={row.code_guard_present ? "guard present" : "guard missing"} tone={row.code_guard_present ? statusTone.wired : statusTone.security_blocker} />
                  </div>
                  <div className="mt-1 truncate text-muted-foreground">{String(row.status || "")}</div>
                </div>
              ))}
            </div>
          </div>
          <div className="space-y-2">
            <div className="text-xs uppercase text-muted-foreground">Electron and next actions</div>
            <div className="grid gap-2">
              {electronRows.slice(0, 4).map((row) => (
                <div key={String(row.check)} className="rounded-md border border-border/40 bg-black/20 px-3 py-2 text-xs">
                  <div className="flex items-center justify-between gap-2">
                    <span className="truncate">{String(row.check || "check").replace(/_/g, " ")}</span>
                    <Pill label={row.passing ? "pass" : "attention"} tone={row.passing ? statusTone.wired : statusTone.security_blocker} />
                  </div>
                </div>
              ))}
              {actions.slice(0, 2).map((row) => (
                <div key={String(row.id)} className="rounded-md border border-border/40 bg-muted/10 px-3 py-2 text-xs">
                  <div className="font-mono text-primary">{String(row.priority || "P?")} {String(row.id || "")}</div>
                  <div className="mt-1 line-clamp-2 text-muted-foreground">{String(row.action || "")}</div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {blockers.length ? (
          <div className="flex flex-wrap gap-1">
            {blockers.slice(0, 12).map((blocker) => (
              <Pill key={blocker} label={blocker.replace(/_/g, " ")} tone={statusTone.security_blocker} />
            ))}
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}

function ParallelTradingSystemsPanel({ unity, stress }: { unity: ParallelStrategyUnity | null; stress: ParallelStrategyUnityStressAudit | null }) {
  const summary = unity?.summary || {};
  const stressSummary = stress?.summary || {};
  const workers = asRecordArray(unity?.worker_rows);
  const leases = asRecordArray(unity?.api_lease_rows);
  const ghostState = asRecord(unity?.ghost_dance);
  const pianoState = asRecord(unity?.harmonic_api_piano);
  const rainbowState = asRecord(unity?.rainbow_harmonic_ladder);
  const ghostPhaseRows = asRecordArray(stress?.ghost_phase_rows).length ? asRecordArray(stress?.ghost_phase_rows) : asRecordArray(ghostState.worker_phase_rows);
  const pianoKeyRows = asRecordArray(stress?.piano_key_rows).length ? asRecordArray(stress?.piano_key_rows) : (asRecordArray(unity?.piano_key_rows).length ? asRecordArray(unity?.piano_key_rows) : asRecordArray(pianoState.piano_key_rows));
  const rainbowRows = asRecordArray(stress?.rainbow_worker_ladder_rows).length ? asRecordArray(stress?.rainbow_worker_ladder_rows) : (asRecordArray(unity?.rainbow_worker_rows).length ? asRecordArray(unity?.rainbow_worker_rows) : asRecordArray(rainbowState.worker_phase_rows));
  const rainbowMissingRows = [
    ...asRecordArray(stress?.rainbow_missing_worker_rows),
    ...asRecordArray(stress?.rainbow_missing_lease_rows),
    ...asRecordArray(stress?.rainbow_missing_intent_rows),
  ];
  const rainbowHistoricalRows = asRecordArray(stress?.rainbow_stale_historical_intent_rows);
  const rainbowRiskRows = asRecordArray(stress?.rainbow_song_continuity_risk_rows);
  const powerRows = asRecordArray(stress?.power_station_request_rows).length ? asRecordArray(stress?.power_station_request_rows) : asRecordArray(unity?.power_station_request_rows);
  const powerMissingRows = [
    ...asRecordArray(stress?.power_station_missing_worker_rows),
    ...asRecordArray(stress?.power_station_missing_lease_rows),
    ...asRecordArray(stress?.power_station_missing_intent_rows),
  ];
  const powerHistoricalRows = asRecordArray(stress?.power_station_stale_historical_intent_rows);
  const powerAuthorityRows = asRecordArray(stress?.power_station_authority_violation_rows);
  const auditSelfValidationRows = asRecordArray(stress?.audit_self_validation_rows);
  const auditSelfValidationFailedRows = asRecordArray(stress?.audit_self_validation_failed_rows);
  const auditReplayValidationRows = asRecordArray(stress?.audit_replay_validation_rows);
  const auditReplayValidationFailedRows = asRecordArray(stress?.audit_replay_validation_failed_rows);
  const auditIntegrityValidationRows = asRecordArray(stress?.audit_integrity_validation_rows);
  const auditIntegrityValidationFailedRows = asRecordArray(stress?.audit_integrity_validation_failed_rows);
  const auditValidationQuorumRows = asRecordArray(stress?.audit_validation_quorum_rows);
  const auditValidationQuorumFailedRows = asRecordArray(stress?.audit_validation_quorum_failed_rows);
  const auditArtifactProvenanceRows = asRecordArray(stress?.audit_artifact_provenance_rows);
  const auditArtifactProvenanceFailedRows = asRecordArray(stress?.audit_artifact_provenance_failed_rows);
  const auditServedArtifactRows = asRecordArray(stress?.audit_served_artifact_rows);
  const auditServedArtifactFailedRows = asRecordArray(stress?.audit_served_artifact_failed_rows);
  const auditFreshnessSlaRows = asRecordArray(stress?.audit_freshness_sla_rows);
  const auditFreshnessSlaFailedRows = asRecordArray(stress?.audit_freshness_sla_failed_rows);
  const auditOperatorSurfaceRows = asRecordArray(stress?.audit_operator_surface_rows);
  const auditOperatorSurfaceFailedRows = asRecordArray(stress?.audit_operator_surface_failed_rows);
  const auditTestCoverageRows = asRecordArray(stress?.audit_test_coverage_rows);
  const auditTestCoverageFailedRows = asRecordArray(stress?.audit_test_coverage_failed_rows);
  const auditTestCoverageValidatorRows = asRecordArray(stress?.audit_test_coverage_validator_rows);
  const auditRepairCoverageRows = asRecordArray(stress?.audit_repair_coverage_rows);
  const auditRepairCoverageFailedRows = asRecordArray(stress?.audit_repair_coverage_failed_rows);
  const auditRuntimeRepairReadinessRows = asRecordArray(stress?.audit_runtime_repair_readiness_rows);
  const auditRuntimeRepairReadinessFailedRows = asRecordArray(stress?.audit_runtime_repair_readiness_failed_rows);
  const auditRepairAcceptanceRows = asRecordArray(stress?.audit_repair_acceptance_rows);
  const auditRepairAcceptanceFailedRows = asRecordArray(stress?.audit_repair_acceptance_failed_rows);
  const auditRepairAcceptanceBlockerRows = asRecordArray(stress?.audit_repair_acceptance_blocker_rows);
  const auditConsistencyMatrixRows = asRecordArray(stress?.audit_consistency_matrix_rows);
  const auditConsistencyMatrixFailedRows = asRecordArray(stress?.audit_consistency_matrix_failed_rows);
  const auditConsistencyMatrixValidatorRows = asRecordArray(stress?.audit_consistency_matrix_validator_rows);
  const auditEvidenceLineageRows = asRecordArray(stress?.audit_evidence_lineage_rows);
  const auditEvidenceLineageFailedRows = asRecordArray(stress?.audit_evidence_lineage_failed_rows);
  const auditEvidenceLineageSectionRows = asRecordArray(stress?.audit_evidence_lineage_section_rows);
  const auditValidatorClosureRows = asRecordArray(stress?.audit_validator_closure_rows);
  const auditValidatorClosureFailedRows = asRecordArray(stress?.audit_validator_closure_failed_rows);
  const auditValidatorClosureSourceRows = asRecordArray(stress?.audit_validator_closure_source_rows);
  const auditPublicContractRows = asRecordArray(stress?.audit_public_contract_rows);
  const auditPublicContractFailedRows = asRecordArray(stress?.audit_public_contract_failed_rows);
  const auditValidationChainRows = asRecordArray(stress?.audit_validation_chain_rows);
  const auditValidationChainFailedRows = asRecordArray(stress?.audit_validation_chain_failed_rows);
  const auditValidationChainValidatorRows = asRecordArray(stress?.audit_validation_chain_validator_rows);
  const ghostCollisionRows = asRecordArray(stress?.ghost_phase_collision_rows);
  const ghostMissingRows = [
    ...asRecordArray(stress?.ghost_missing_worker_phase_rows),
    ...asRecordArray(stress?.ghost_missing_lease_phase_rows),
    ...asRecordArray(stress?.ghost_missing_intent_phase_rows),
  ];
  const ghostHistoricalRows = asRecordArray(stress?.ghost_stale_historical_intent_phase_rows);
  const pianoMissingRows = [
    ...asRecordArray(stress?.piano_missing_worker_rows),
    ...asRecordArray(stress?.piano_missing_lease_rows),
    ...asRecordArray(stress?.piano_missing_intent_rows),
  ];
  const pianoHistoricalRows = asRecordArray(stress?.piano_stale_historical_intent_rows);
  const pianoSongStopRows = asRecordArray(stress?.piano_song_stop_risk_rows);
  const venues = asRecordArray(unity?.venue_budget_rows);
  const intents = asRecordArray(unity?.strategy_intent_rows);
  const stressWorkers = asRecordArray(stress?.worker_stress_rows);
  const mutationRows = asRecordArray(stress?.mutation_authority_rows);
  const budgetRows = asRecordArray(stress?.api_budget_stress_rows);
  const intentContractRows = asRecordArray(stress?.intent_contract_rows);
  const runtimeBurnDownRows = asRecordArray(stress?.runtime_alignment_burndown_rows);
  const runtimeProcessRows = asRecordArray(stress?.runtime_process_rows);
  const runtimeProcessBurnDownRows = asRecordArray(stress?.runtime_process_burndown_rows);
  const stopTargetRows = asRecordArray(stress?.single_owner_stop_target_rows);
  const startTargetRows = asRecordArray(stress?.single_owner_start_target_rows);
  const postRestartRows = asRecordArray(stress?.post_restart_check_rows);
  const guardValidationRows = asRecordArray(stress?.single_owner_guard_validation_rows);
  const guardedCommandLines = Array.isArray(stress?.guarded_repair_command_lines) ? stress.guarded_repair_command_lines : [];
  const repairRows = asRecordArray(stress?.next_repair_actions);
  const sourcePaths = asRecord(unity?.source_paths);
  const directMutation = Boolean(summary.direct_broker_mutation_allowed);
  const allHealthy = asNumber(summary.worker_count) > 0 && asNumber(summary.worker_count) === asNumber(summary.healthy_worker_count);
  const stressCertified = stress?.status === "parallel_strategy_stress_certified";
  const active = Boolean(allHealthy && summary.unified_executor_authoritative && !directMutation && (!stress || stressCertified));
  const statusLabel = String(unity?.status || "parallel strategy unity pending").replace(/_/g, " ");
  const stressLabel = String(stress?.status || "stress audit pending").replace(/_/g, " ");

  return (
    <Card className="border-primary/30 bg-primary/5">
      <CardHeader className="pb-3">
        <CardTitle className="flex flex-wrap items-center justify-between gap-2 text-base">
          <span className="flex items-center gap-2">
            <Radio className="h-4 w-4 text-primary" />
            Parallel Trading Systems
          </span>
          <div className="flex flex-wrap gap-1">
            <Pill label={statusLabel} tone={active ? statusTone.wired : statusTone.orphaned} />
            <Pill label={summary.unified_executor_authoritative ? "one executor" : "executor attention"} tone={summary.unified_executor_authoritative ? statusTone.wired : statusTone.security_blocker} />
            <Pill label={directMutation ? "direct mutation leak" : "workers signal only"} tone={directMutation ? statusTone.security_blocker : statusTone.wired} />
            <Pill label={stressLabel} tone={stressCertified ? statusTone.wired : statusTone.orphaned} />
            <Pill label="/aureon_parallel_strategy_unity.json" tone="border-primary/30 bg-primary/10 text-primary" />
            <Pill label="/aureon_parallel_strategy_unity_stress_audit.json" tone="border-primary/30 bg-primary/10 text-primary" />
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-6">
          {[
            ["workers", `${formatCompact(summary.healthy_worker_count)}/${formatCompact(summary.worker_count)}`],
            ["signals", summary.latest_signal_count],
            ["worker intents", summary.latest_intent_count],
            ["intent queue", summary.intent_queue_count],
            ["3p executable", summary.executable_intent_count],
            ["leases", summary.request_lease_count],
            ["denied leases", summary.request_denied_count],
            ["3p goal", `GBP ${Number(summary.minimum_net_profit_gbp ?? 0.03).toFixed(2)}`],
            ["ThoughtBus/Mycelium", summary.thoughtbus_mycelium_publish_enabled ? "publishing" : "pending"],
            ["mode", unity?.mode || "pending"],
            ["request broker", sourcePaths.request_broker_public || "/aureon_unified_exchange_request_broker.json"],
            ["strategy intents", sourcePaths.strategy_intents_public || "/aureon_unified_strategy_intents.json"],
            ["stress blockers", stressSummary.blocker_count],
            ["stress stale workers", stressSummary.stale_worker_count],
            ["intent gaps", stressSummary.missing_intent_contract_count],
            ["budget gaps", stressSummary.api_budget_gap_count],
            ["mutation leaks", stressSummary.mutation_leak_count],
            ["strategy agreement", stressSummary.strategy_agreement_count],
            ["strategy disagreement", stressSummary.strategy_disagreement_count],
            ["Ghost Dance", summary.ghost_dance_enabled ? "active" : "attention"],
            ["ghost phases", summary.ghost_phase_count ?? stressSummary.ghost_phase_count],
            ["API locks", summary.api_key_lock_family_count ?? stressSummary.ghost_api_key_lock_family_count],
            ["phase collisions", summary.ghost_phase_collision_count ?? stressSummary.ghost_phase_collision_count],
            ["old ghost rows", stressSummary.ghost_stale_historical_intent_phase_count],
            ["Harmonic Piano", summary.harmonic_api_piano_enabled ? "active" : "attention"],
            ["tempo", summary.harmonic_tempo_multiplier ?? stressSummary.harmonic_tempo_multiplier],
            ["piano keys", summary.piano_key_count ?? stressSummary.piano_key_count],
            ["song-stop risk", stressSummary.song_stop_risk_count],
            ["Rainbow Ladder", summary.rainbow_harmonic_ladder_enabled ? "active" : "attention"],
            ["rainbow steps", summary.rainbow_ladder_step_count ?? stressSummary.rainbow_ladder_step_count],
            ["base Hz", summary.rainbow_base_frequency_hz ?? stressSummary.rainbow_base_frequency_hz],
            ["rainbow gaps", stressSummary.rainbow_missing_proof_count],
            ["Power Station", summary.power_station_request_governor_enabled ? "governing" : "attention"],
            ["PS requests", summary.power_station_request_count ?? stressSummary.power_station_request_count],
            ["PS outbound", summary.power_station_outbound_request_count ?? stressSummary.power_station_outbound_request_count],
            ["PS gaps", stressSummary.power_station_missing_proof_count],
            ["self validation", stressSummary.audit_self_validation_passed ? "passed" : "attention"],
            ["self checks", stressSummary.audit_self_validation_check_count],
            ["self failures", stressSummary.audit_self_validation_failed_count],
            ["replay validation", stressSummary.audit_replay_validation_passed ? "passed" : "attention"],
            ["replay checks", stressSummary.audit_replay_validation_check_count],
            ["replay failures", stressSummary.audit_replay_validation_failed_count],
            ["integrity validation", stressSummary.audit_integrity_validation_passed ? "passed" : "attention"],
            ["integrity checks", stressSummary.audit_integrity_validation_check_count],
            ["integrity failures", stressSummary.audit_integrity_validation_failed_count],
            ["validation quorum", stressSummary.audit_validation_quorum_passed ? "passed" : "attention"],
            ["quorum", `${formatCompact(stressSummary.audit_validation_quorum_pass_count)}/${formatCompact(stressSummary.audit_validation_quorum_required_count)}`],
            ["quorum failures", stressSummary.audit_validation_quorum_failed_count],
            ["artifact provenance", stressSummary.audit_artifact_provenance_passed ? "passed" : "attention"],
            ["artifact hashes", `${formatCompact(stressSummary.audit_artifact_provenance_json_match_count)}/${formatCompact(stressSummary.audit_artifact_provenance_json_artifact_count)}`],
            ["artifact failures", stressSummary.audit_artifact_provenance_failed_count],
            ["served artifact", stressSummary.audit_served_artifact_passed ? "passed" : "attention"],
            ["served checked", stressSummary.audit_served_artifact_checked ? "yes" : "fixture skip"],
            ["served failures", stressSummary.audit_served_artifact_failed_count],
            ["freshness SLA", stressSummary.audit_freshness_sla_passed ? "passed" : "attention"],
            ["audit age", `${formatCompact(stressSummary.audit_freshness_sla_age_sec)}s`],
            ["freshness failures", stressSummary.audit_freshness_sla_failed_count],
            ["operator surface", stressSummary.audit_operator_surface_passed ? "passed" : "attention"],
            ["surface panels", stressSummary.audit_operator_surface_required_panel_count],
            ["surface controls", stressSummary.audit_operator_surface_mutation_control_count],
            ["test coverage", stressSummary.audit_test_coverage_passed ? "passed" : "attention"],
            ["validator tests", `${formatCompact(stressSummary.audit_test_coverage_validator_test_count)}/${formatCompact(stressSummary.audit_test_coverage_validator_expected_count)}`],
            ["coverage failures", stressSummary.audit_test_coverage_failed_count],
            ["repair coverage", stressSummary.audit_repair_coverage_passed ? "passed" : "attention"],
            ["repair rows", stressSummary.audit_repair_coverage_repair_action_count],
            ["generic repairs", stressSummary.audit_repair_coverage_generic_repair_count],
            ["runtime repair", stressSummary.audit_runtime_repair_readiness_passed ? "ready" : "attention"],
            ["guard lines", stressSummary.audit_runtime_repair_readiness_guarded_command_line_count],
            ["unsafe command", stressSummary.audit_runtime_repair_readiness_unsafe_command_count],
            ["repair acceptance", stressSummary.audit_repair_acceptance_passed ? "mapped" : "attention"],
            ["acceptance rows", stressSummary.audit_repair_acceptance_acceptance_row_count],
            ["missing accepts", stressSummary.audit_repair_acceptance_missing_acceptance_count],
            ["consistency matrix", stressSummary.audit_consistency_matrix_passed ? "passed" : "attention"],
            ["matrix validators", `${formatCompact(stressSummary.audit_consistency_matrix_validator_pass_count)}/${formatCompact(stressSummary.audit_consistency_matrix_validator_count)}`],
            ["matrix drift", stressSummary.audit_consistency_matrix_inconsistent_validator_count],
            ["evidence lineage", stressSummary.audit_evidence_lineage_passed ? "passed" : "attention"],
            ["lineage sections", stressSummary.audit_evidence_lineage_section_row_count],
            ["lineage missing", stressSummary.audit_evidence_lineage_missing_lineage_count],
            ["validator closure", stressSummary.audit_validator_closure_passed ? "passed" : "attention"],
            ["closure validators", stressSummary.audit_validator_closure_validator_count],
            ["closure sources", stressSummary.audit_validator_closure_source_check_count],
            ["public contract", stressSummary.audit_public_contract_passed ? "passed" : "attention"],
            ["contract fields", stressSummary.audit_public_contract_required_summary_field_count],
            ["contract failures", stressSummary.audit_public_contract_failed_count],
            ["validation chain", stressSummary.audit_validation_chain_passed ? "passed" : "attention"],
            ["validator mirrors", `${formatCompact(stressSummary.audit_validation_chain_validator_pass_count)}/${formatCompact(stressSummary.audit_validation_chain_validator_count)}`],
            ["chain failures", stressSummary.audit_validation_chain_failed_count],
            ["runtime aligned", stressSummary.runtime_alignment ? "yes" : "attention"],
            ["runtime reload", stressSummary.runtime_reload_required ? "required" : "not required"],
            ["code wired", stressSummary.runtime_code_wired ? "yes" : "attention"],
            ["state snapshots", stressSummary.state_snapshots_present ? "present" : "attention"],
            ["UMT processes", stressSummary.unified_market_trader_process_count],
            ["supervisor processes", stressSummary.parallel_strategy_supervisor_process_count],
            ["wrong python", stressSummary.wrong_python_process_count],
            ["repair ready", stressSummary.single_owner_repair_ready ? "yes" : "attention"],
            ["guarded command", stressSummary.guarded_repair_command_ready ? "ready" : "attention"],
            ["stop targets", stressSummary.restart_stop_target_count],
            ["fabric visible", stressSummary.fabric_visible ? "yes" : "attention"],
          ].map(([label, value]) => (
            <div key={String(label)} className="rounded-md border border-border/40 bg-black/20 p-3">
              <div className="text-[11px] uppercase text-muted-foreground">{String(label)}</div>
              <div className="mt-1 truncate font-mono text-sm font-semibold text-primary">
                {typeof value === "number" ? formatCompact(value) : String(value ?? "0")}
              </div>
            </div>
          ))}
        </div>

        <div className="rounded-md border border-primary/20 bg-black/20 p-3">
          <div className="mb-2 flex items-center justify-between gap-2">
            <div className="text-xs uppercase text-muted-foreground">Stress audit burn-down</div>
            <div className="flex flex-wrap gap-1">
              <Pill label={stressCertified ? "certified" : "attention"} tone={stressCertified ? statusTone.wired : statusTone.orphaned} />
              <Pill label={stressSummary.unified_executor_authoritative ? "executor owner proven" : "executor proof attention"} tone={stressSummary.unified_executor_authoritative ? statusTone.wired : statusTone.security_blocker} />
              <Pill label={stressSummary.direct_broker_mutation_allowed ? "direct mutation leak" : "no direct worker mutation"} tone={stressSummary.direct_broker_mutation_allowed ? statusTone.security_blocker : statusTone.wired} />
            </div>
          </div>
          <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-4">
            {[
              ["healthy workers", `${formatCompact(stressSummary.healthy_worker_count)}/${formatCompact(stressSummary.worker_count)}`],
              ["missing intent fields", stressSummary.missing_intent_contract_count],
              ["API budget gaps", stressSummary.api_budget_gap_count],
              ["mutation leaks", stressSummary.mutation_leak_count],
              ["denied mutation proof", stressSummary.denied_mutation_proof_count],
              ["duplicate routes", stressSummary.duplicate_route_count],
              ["ghost phases", stressSummary.ghost_unique_phase_count ?? summary.ghost_phase_count],
              ["ghost missing", stressSummary.ghost_missing_phase_count],
              ["ghost historical", stressSummary.ghost_stale_historical_intent_phase_count],
              ["ghost collisions", stressSummary.ghost_phase_collision_count],
              ["piano keys", stressSummary.piano_key_count ?? summary.piano_key_count],
              ["piano play now", stressSummary.piano_play_now_count ?? summary.piano_play_now_count],
              ["piano missing", stressSummary.piano_missing_proof_count],
              ["piano historical", stressSummary.piano_stale_historical_intent_count],
              ["song-stop risks", stressSummary.song_stop_risk_count],
              ["rainbow ladder", stressSummary.rainbow_harmonic_ladder_enabled ? "active" : "attention"],
              ["rainbow missing", stressSummary.rainbow_missing_proof_count],
              ["rainbow risks", stressSummary.rainbow_song_continuity_risk_count],
              ["power station", stressSummary.power_station_request_governor_enabled ? "active" : "attention"],
              ["PS requests", stressSummary.power_station_request_count],
              ["PS authority", stressSummary.power_station_authority_violation_count],
              ["self validation", stressSummary.audit_self_validation_passed ? "passed" : "attention"],
              ["self checks", stressSummary.audit_self_validation_check_count],
              ["self failures", stressSummary.audit_self_validation_failed_count],
              ["replay validation", stressSummary.audit_replay_validation_passed ? "passed" : "attention"],
              ["replay checks", stressSummary.audit_replay_validation_check_count],
              ["replay failures", stressSummary.audit_replay_validation_failed_count],
              ["integrity validation", stressSummary.audit_integrity_validation_passed ? "passed" : "attention"],
              ["integrity checks", stressSummary.audit_integrity_validation_check_count],
              ["integrity failures", stressSummary.audit_integrity_validation_failed_count],
              ["validation quorum", stressSummary.audit_validation_quorum_passed ? "passed" : "attention"],
              ["quorum", `${formatCompact(stressSummary.audit_validation_quorum_pass_count)}/${formatCompact(stressSummary.audit_validation_quorum_required_count)}`],
              ["quorum failures", stressSummary.audit_validation_quorum_failed_count],
              ["artifact provenance", stressSummary.audit_artifact_provenance_passed ? "passed" : "attention"],
              ["artifact hashes", `${formatCompact(stressSummary.audit_artifact_provenance_json_match_count)}/${formatCompact(stressSummary.audit_artifact_provenance_json_artifact_count)}`],
              ["artifact failures", stressSummary.audit_artifact_provenance_failed_count],
              ["served artifact", stressSummary.audit_served_artifact_passed ? "passed" : "attention"],
              ["served checked", stressSummary.audit_served_artifact_checked ? "yes" : "fixture skip"],
              ["served failures", stressSummary.audit_served_artifact_failed_count],
              ["freshness SLA", stressSummary.audit_freshness_sla_passed ? "passed" : "attention"],
              ["audit age", `${formatCompact(stressSummary.audit_freshness_sla_age_sec)}s`],
              ["freshness failures", stressSummary.audit_freshness_sla_failed_count],
              ["operator surface", stressSummary.audit_operator_surface_passed ? "passed" : "attention"],
              ["surface panels", stressSummary.audit_operator_surface_required_panel_count],
              ["surface controls", stressSummary.audit_operator_surface_mutation_control_count],
              ["test coverage", stressSummary.audit_test_coverage_passed ? "passed" : "attention"],
              ["validator tests", `${formatCompact(stressSummary.audit_test_coverage_validator_test_count)}/${formatCompact(stressSummary.audit_test_coverage_validator_expected_count)}`],
              ["coverage failures", stressSummary.audit_test_coverage_failed_count],
              ["repair coverage", stressSummary.audit_repair_coverage_passed ? "passed" : "attention"],
              ["repair rows", stressSummary.audit_repair_coverage_repair_action_count],
              ["generic repairs", stressSummary.audit_repair_coverage_generic_repair_count],
              ["runtime repair", stressSummary.audit_runtime_repair_readiness_passed ? "ready" : "attention"],
              ["guard lines", stressSummary.audit_runtime_repair_readiness_guarded_command_line_count],
              ["unsafe command", stressSummary.audit_runtime_repair_readiness_unsafe_command_count],
              ["repair acceptance", stressSummary.audit_repair_acceptance_passed ? "mapped" : "attention"],
              ["acceptance rows", stressSummary.audit_repair_acceptance_acceptance_row_count],
              ["missing accepts", stressSummary.audit_repair_acceptance_missing_acceptance_count],
              ["consistency matrix", stressSummary.audit_consistency_matrix_passed ? "passed" : "attention"],
              ["matrix validators", `${formatCompact(stressSummary.audit_consistency_matrix_validator_pass_count)}/${formatCompact(stressSummary.audit_consistency_matrix_validator_count)}`],
              ["matrix drift", stressSummary.audit_consistency_matrix_inconsistent_validator_count],
              ["evidence lineage", stressSummary.audit_evidence_lineage_passed ? "passed" : "attention"],
              ["lineage sections", stressSummary.audit_evidence_lineage_section_row_count],
              ["lineage missing", stressSummary.audit_evidence_lineage_missing_lineage_count],
              ["validator closure", stressSummary.audit_validator_closure_passed ? "passed" : "attention"],
              ["closure validators", stressSummary.audit_validator_closure_validator_count],
              ["closure sources", stressSummary.audit_validator_closure_source_check_count],
              ["public contract", stressSummary.audit_public_contract_passed ? "passed" : "attention"],
              ["contract fields", stressSummary.audit_public_contract_required_summary_field_count],
              ["contract failures", stressSummary.audit_public_contract_failed_count],
              ["validation chain", stressSummary.audit_validation_chain_passed ? "passed" : "attention"],
              ["validator mirrors", `${formatCompact(stressSummary.audit_validation_chain_validator_pass_count)}/${formatCompact(stressSummary.audit_validation_chain_validator_count)}`],
              ["chain failures", stressSummary.audit_validation_chain_failed_count],
              ["runtime alignment", stressSummary.runtime_alignment ? "aligned" : "attention"],
              ["runtime reload", stressSummary.runtime_reload_required ? "required" : "not required"],
              ["code wired", stressSummary.runtime_code_wired ? "yes" : "attention"],
              ["terminal unity", stressSummary.runtime_embeds_parallel_unity ? "embedded" : "missing"],
              ["terminal intents", stressSummary.runtime_embeds_parallel_intents ? "embedded" : "missing"],
              ["UMT processes", stressSummary.unified_market_trader_process_count],
              ["supervisor process", stressSummary.parallel_strategy_supervisor_process_count],
              ["wrong python", stressSummary.wrong_python_process_count],
              ["repair ready", stressSummary.single_owner_repair_ready ? "yes" : "attention"],
              ["guarded command", stressSummary.guarded_repair_command_ready ? "ready" : "attention"],
              ["stop targets", stressSummary.restart_stop_target_count],
              ["start targets", stressSummary.restart_start_target_count],
              ["post checks", stressSummary.post_restart_check_count],
              ["fabric visibility", stressSummary.fabric_visible ? "visible" : "attention"],
            ].map(([label, value]) => (
              <div key={String(label)} className="rounded-md border border-border/40 bg-muted/10 px-3 py-2 text-xs">
                <div className="uppercase text-muted-foreground">{String(label)}</div>
                <div className="mt-1 truncate font-mono text-primary">{typeof value === "number" ? formatCompact(value) : String(value ?? "0")}</div>
              </div>
            ))}
          </div>
          {ghostPhaseRows.length ? (
            <div className="mt-3 space-y-2 rounded-md border border-primary/20 bg-primary/5 p-3">
              <div className="flex items-center justify-between gap-2">
                <div className="text-xs uppercase text-muted-foreground">Ghost Dance API phase protocol</div>
                <div className="flex flex-wrap gap-1">
                  <Pill label={summary.ghost_dance_enabled || stressSummary.ghost_dance_enabled ? "phase active" : "phase attention"} tone={summary.ghost_dance_enabled || stressSummary.ghost_dance_enabled ? statusTone.wired : statusTone.orphaned} />
                  <Pill label={`${formatCompact(stressSummary.ghost_phase_collision_count ?? summary.ghost_phase_collision_count)} collision(s)`} tone={asNumber(stressSummary.ghost_phase_collision_count ?? summary.ghost_phase_collision_count) ? statusTone.security_blocker : statusTone.wired} />
                  <Pill label={`${formatCompact(stressSummary.ghost_api_key_lock_family_count ?? summary.api_key_lock_family_count)} API locks`} tone="border-primary/30 bg-primary/10 text-primary" />
                  <Pill label={`${formatCompact(stressSummary.ghost_stale_historical_intent_phase_count)} old rows`} tone="border-slate-500/30 bg-slate-500/10 text-slate-200" />
                </div>
              </div>
              <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-4">
                {ghostPhaseRows.slice(0, 8).map((row, index) => (
                  <div key={`ghost-phase-${String(row.worker_id || index)}`} className="rounded-md border border-border/40 bg-black/20 px-3 py-2 text-xs">
                    <div className="flex items-center justify-between gap-2">
                      <span className="truncate font-medium">{String(row.worker_id || "worker").replace(/_/g, " ")}</span>
                      <Pill label={`phase ${String(row.ghost_phase_index ?? "?")}/${String(row.ghost_phase_count ?? "?")}`} tone="border-primary/30 bg-primary/10 text-primary" />
                    </div>
                    <div className="mt-1 truncate text-muted-foreground">{String(row.api_key_lock_family || "api lock pending")}</div>
                    <div className="mt-1 grid grid-cols-2 gap-1 text-[11px] text-muted-foreground">
                      <span>offset {String(row.ghost_phase_offset_sec ?? "0")}s</span>
                      <span>wait {String(row.scheduled_after_ms ?? "0")}ms</span>
                    </div>
                  </div>
                ))}
              </div>
              {[...ghostCollisionRows, ...ghostMissingRows, ...ghostHistoricalRows].length ? (
                <div className="grid gap-2 md:grid-cols-2">
                  {ghostCollisionRows.slice(0, 2).map((row, index) => (
                    <div key={`ghost-collision-${String(row.api_key_lock_family || index)}`} className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs">
                      <div className="font-medium">Ghost phase collision</div>
                      <div className="mt-1 truncate text-muted-foreground">{String(row.api_key_lock_family || "api lock")} phase {String(row.ghost_phase_index ?? "?")}</div>
                    </div>
                  ))}
                  {ghostMissingRows.slice(0, 2).map((row, index) => (
                    <div key={`ghost-missing-${String(row.worker_id || row.lease_id || index)}`} className="rounded-md border border-warning/30 bg-warning/10 px-3 py-2 text-xs">
                      <div className="font-medium">Ghost phase proof missing</div>
                      <div className="mt-1 truncate text-muted-foreground">{String(row.worker_id || row.lease_id || "row")} missing {String((row.missing_fields as string[] | undefined)?.join(", ") || "phase proof")}</div>
                    </div>
                  ))}
                  {ghostHistoricalRows.slice(0, 2).map((row, index) => (
                    <div key={`ghost-historical-${String(row.intent_id || index)}`} className="rounded-md border border-slate-500/30 bg-slate-500/10 px-3 py-2 text-xs">
                      <div className="font-medium">Historical intent before Ghost Dance</div>
                      <div className="mt-1 truncate text-muted-foreground">{String(row.worker_id || "worker")} missing {String((row.missing_fields as string[] | undefined)?.join(", ") || "phase proof")}</div>
                    </div>
                  ))}
                </div>
              ) : null}
            </div>
          ) : null}
          {pianoKeyRows.length ? (
            <div className="mt-3 space-y-2 rounded-md border border-primary/20 bg-primary/5 p-3">
              <div className="flex items-center justify-between gap-2">
                <div className="text-xs uppercase text-muted-foreground">Harmonic API Piano</div>
                <div className="flex flex-wrap gap-1">
                  <Pill label={summary.harmonic_api_piano_enabled || stressSummary.harmonic_api_piano_enabled ? "tempo active" : "tempo attention"} tone={summary.harmonic_api_piano_enabled || stressSummary.harmonic_api_piano_enabled ? statusTone.wired : statusTone.orphaned} />
                  <Pill label={`tempo ${String(summary.harmonic_tempo_multiplier ?? stressSummary.harmonic_tempo_multiplier ?? "0")}`} tone="border-primary/30 bg-primary/10 text-primary" />
                  <Pill label={`${formatCompact(stressSummary.song_stop_risk_count)} song-stop risk`} tone={asNumber(stressSummary.song_stop_risk_count) ? statusTone.security_blocker : statusTone.wired} />
                </div>
              </div>
              <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-4">
                {pianoKeyRows.slice(0, 8).map((row, index) => (
                  <div key={`piano-key-${String(row.piano_key_id || row.worker_id || index)}`} className="rounded-md border border-border/40 bg-black/20 px-3 py-2 text-xs">
                    <div className="flex items-center justify-between gap-2">
                      <span className="truncate font-medium">{String(row.worker_id || "worker").replace(/_/g, " ")}</span>
                      <Pill label={`key ${String(row.piano_key_rank ?? "?")}`} tone="border-primary/30 bg-primary/10 text-primary" />
                    </div>
                    <div className="mt-1 truncate text-muted-foreground">{String(row.piano_key_id || row.api_key_lock_family || "api key lock")}</div>
                    <div className="mt-1 grid grid-cols-2 gap-1 text-[11px] text-muted-foreground">
                      <span>velocity {String(row.piano_velocity_score ?? "0")}</span>
                      <span>wait {String(row.scheduled_after_ms ?? "0")}ms</span>
                      <span>window {String(row.api_play_window_ms ?? "0")}ms</span>
                      <span>{String(row.song_stop_guard || "cooldown")}</span>
                    </div>
                  </div>
                ))}
              </div>
              {[...pianoMissingRows, ...pianoHistoricalRows, ...pianoSongStopRows].length ? (
                <div className="grid gap-2 md:grid-cols-2">
                  {pianoSongStopRows.slice(0, 2).map((row, index) => (
                    <div key={`piano-risk-${String(row.piano_key_id || index)}`} className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs">
                      <div className="font-medium">Song-stop risk</div>
                      <div className="mt-1 truncate text-muted-foreground">{String(row.worker_id || "worker")} {String(row.song_stop_guard || "risk")}</div>
                    </div>
                  ))}
                  {pianoMissingRows.slice(0, 2).map((row, index) => (
                    <div key={`piano-missing-${String(row.worker_id || row.lease_id || index)}`} className="rounded-md border border-warning/30 bg-warning/10 px-3 py-2 text-xs">
                      <div className="font-medium">Piano tempo proof missing</div>
                      <div className="mt-1 truncate text-muted-foreground">{String(row.worker_id || row.lease_id || "row")} missing {String((row.missing_fields as string[] | undefined)?.join(", ") || "tempo proof")}</div>
                    </div>
                  ))}
                  {pianoHistoricalRows.slice(0, 2).map((row, index) => (
                    <div key={`piano-historical-${String(row.intent_id || index)}`} className="rounded-md border border-slate-500/30 bg-slate-500/10 px-3 py-2 text-xs">
                      <div className="font-medium">Historical intent before Piano tempo</div>
                      <div className="mt-1 truncate text-muted-foreground">{String(row.worker_id || "worker")} missing {String((row.missing_fields as string[] | undefined)?.join(", ") || "tempo proof")}</div>
                    </div>
                  ))}
                </div>
              ) : null}
            </div>
          ) : null}
          {rainbowRows.length ? (
            <div className="mt-3 space-y-2 rounded-md border border-success/20 bg-success/5 p-3">
              <div className="flex items-center justify-between gap-2">
                <div className="text-xs uppercase text-muted-foreground">Rainbow Harmonic Frequency Ladder</div>
                <div className="flex flex-wrap gap-1">
                  <Pill label={summary.rainbow_harmonic_ladder_enabled || stressSummary.rainbow_harmonic_ladder_enabled ? "ladder active" : "ladder attention"} tone={summary.rainbow_harmonic_ladder_enabled || stressSummary.rainbow_harmonic_ladder_enabled ? statusTone.wired : statusTone.orphaned} />
                  <Pill label={`${formatCompact(summary.rainbow_ladder_step_count ?? stressSummary.rainbow_ladder_step_count)} steps`} tone="border-success/30 bg-success/10 text-success" />
                  <Pill label={`${String(summary.rainbow_base_frequency_hz ?? stressSummary.rainbow_base_frequency_hz ?? "0")} Hz base`} tone="border-success/30 bg-success/10 text-success" />
                  <Pill label={`${formatCompact(stressSummary.rainbow_song_continuity_risk_count)} continuity risk`} tone={asNumber(stressSummary.rainbow_song_continuity_risk_count) ? statusTone.security_blocker : statusTone.wired} />
                </div>
              </div>
              <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-4">
                {rainbowRows.slice(0, 8).map((row, index) => (
                  <div key={`rainbow-row-${String(row.harmony_lane_id || row.worker_id || index)}`} className="rounded-md border border-border/40 bg-black/20 px-3 py-2 text-xs">
                    <div className="flex items-center justify-between gap-2">
                      <span className="truncate font-medium">{String(row.worker_id || "worker").replace(/_/g, " ")}</span>
                      <Pill label={String(row.rainbow_step_name || "step").replace(/_/g, " ")} tone="border-success/30 bg-success/10 text-success" />
                    </div>
                    <div className="mt-1 truncate text-muted-foreground">{String(row.harmony_lane_id || "harmony lane")}</div>
                    <div className="mt-1 grid grid-cols-2 gap-1 text-[11px] text-muted-foreground">
                      <span>{String(row.rainbow_frequency_hz ?? "0")} Hz</span>
                      <span>{String(row.request_tempo_band || "tempo")}</span>
                      <span>{String(row.request_phase_role || "phase")}</span>
                      <span>{String(row.song_continuity_guard || "guard")}</span>
                    </div>
                  </div>
                ))}
              </div>
              {[...rainbowMissingRows, ...rainbowHistoricalRows, ...rainbowRiskRows].length ? (
                <div className="grid gap-2 md:grid-cols-2">
                  {rainbowRiskRows.slice(0, 2).map((row, index) => (
                    <div key={`rainbow-risk-${String(row.harmony_lane_id || index)}`} className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs">
                      <div className="font-medium">Rainbow continuity risk</div>
                      <div className="mt-1 truncate text-muted-foreground">{String(row.worker_id || "worker")} {String(row.song_continuity_guard || "risk")}</div>
                    </div>
                  ))}
                  {rainbowMissingRows.slice(0, 2).map((row, index) => (
                    <div key={`rainbow-missing-${String(row.worker_id || row.lease_id || index)}`} className="rounded-md border border-warning/30 bg-warning/10 px-3 py-2 text-xs">
                      <div className="font-medium">Rainbow ladder proof missing</div>
                      <div className="mt-1 truncate text-muted-foreground">{String(row.worker_id || row.lease_id || "row")} missing {String((row.missing_fields as string[] | undefined)?.join(", ") || "ladder proof")}</div>
                    </div>
                  ))}
                  {rainbowHistoricalRows.slice(0, 2).map((row, index) => (
                    <div key={`rainbow-historical-${String(row.intent_id || index)}`} className="rounded-md border border-slate-500/30 bg-slate-500/10 px-3 py-2 text-xs">
                      <div className="font-medium">Historical intent before Rainbow Ladder</div>
                      <div className="mt-1 truncate text-muted-foreground">{String(row.worker_id || "worker")} missing {String((row.missing_fields as string[] | undefined)?.join(", ") || "ladder proof")}</div>
                    </div>
                  ))}
                </div>
              ) : null}
            </div>
          ) : null}
          {powerRows.length ? (
            <div className="mt-3 space-y-2 rounded-md border border-primary/20 bg-primary/5 p-3">
              <div className="flex items-center justify-between gap-2">
                <div className="text-xs uppercase text-muted-foreground">Power Station Request Governor</div>
                <div className="flex flex-wrap gap-1">
                  <Pill label={summary.power_station_request_governor_enabled || stressSummary.power_station_request_governor_enabled ? "metadata governing" : "metadata attention"} tone={summary.power_station_request_governor_enabled || stressSummary.power_station_request_governor_enabled ? statusTone.wired : statusTone.orphaned} />
                  <Pill label={`${formatCompact(stressSummary.power_station_outbound_request_count ?? summary.power_station_outbound_request_count)} outbound`} tone="border-primary/30 bg-primary/10 text-primary" />
                  <Pill label={`${formatCompact(stressSummary.power_station_internal_request_count ?? summary.power_station_internal_request_count)} internal`} tone="border-primary/30 bg-primary/10 text-primary" />
                  <Pill label={`${formatCompact(stressSummary.power_station_authority_violation_count)} authority gaps`} tone={asNumber(stressSummary.power_station_authority_violation_count) ? statusTone.security_blocker : statusTone.wired} />
                </div>
              </div>
              <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-4">
                {powerRows.slice(0, 8).map((row, index) => (
                  <div key={`power-row-${String(row.lease_id || row.request_id || index)}`} className="rounded-md border border-border/40 bg-black/20 px-3 py-2 text-xs">
                    <div className="flex items-center justify-between gap-2">
                      <span className="truncate font-medium">{String(row.worker_id || "worker").replace(/_/g, " ")}</span>
                      <Pill label={String(row.request_class || "request").replace(/_/g, " ")} tone={row.request_owner_authority === "denied_non_executor_mutation" ? statusTone.security_blocker : "border-primary/30 bg-primary/10 text-primary"} />
                    </div>
                    <div className="mt-1 truncate text-muted-foreground">{String(row.request_direction || "direction")} / {String(row.request_governor_decision || "decision")}</div>
                    <div className="mt-1 grid grid-cols-2 gap-1 text-[11px] text-muted-foreground">
                      <span>{String(row.power_station_budget_tier || "budget")}</span>
                      <span>min {String(row.power_station_min_notional ?? "0")}</span>
                      <span>{String(row.request_owner_authority || "authority")}</span>
                      <span>{String(row.mutation_scope || "none")}</span>
                    </div>
                  </div>
                ))}
              </div>
              {[...powerAuthorityRows, ...powerMissingRows, ...powerHistoricalRows].length ? (
                <div className="grid gap-2 md:grid-cols-2">
                  {powerAuthorityRows.slice(0, 2).map((row, index) => (
                    <div key={`power-auth-${String(row.lease_id || index)}`} className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs">
                      <div className="font-medium">Power Station authority gap</div>
                      <div className="mt-1 truncate text-muted-foreground">{String(row.worker_id || "worker")} {String(row.operation_type || "mutation")}</div>
                    </div>
                  ))}
                  {powerMissingRows.slice(0, 2).map((row, index) => (
                    <div key={`power-missing-${String(row.worker_id || row.lease_id || index)}`} className="rounded-md border border-warning/30 bg-warning/10 px-3 py-2 text-xs">
                      <div className="font-medium">Power Station metadata missing</div>
                      <div className="mt-1 truncate text-muted-foreground">{String(row.worker_id || row.lease_id || "row")} missing {String((row.missing_fields as string[] | undefined)?.join(", ") || "metadata")}</div>
                    </div>
                  ))}
                  {powerHistoricalRows.slice(0, 2).map((row, index) => (
                    <div key={`power-historical-${String(row.intent_id || index)}`} className="rounded-md border border-slate-500/30 bg-slate-500/10 px-3 py-2 text-xs">
                      <div className="font-medium">Historical intent before Power Station governor</div>
                      <div className="mt-1 truncate text-muted-foreground">{String(row.worker_id || "worker")} missing {String((row.missing_fields as string[] | undefined)?.join(", ") || "metadata")}</div>
                    </div>
                  ))}
                </div>
              ) : null}
            </div>
          ) : null}
          {auditSelfValidationRows.length ? (
            <div className="mt-3 space-y-2 rounded-md border border-success/20 bg-success/5 p-3">
              <div className="flex items-center justify-between gap-2">
                <div className="text-xs uppercase text-muted-foreground">Audit Self-Validation</div>
                <div className="flex flex-wrap gap-1">
                  <Pill label={stressSummary.audit_self_validation_passed ? "self checked" : "self attention"} tone={stressSummary.audit_self_validation_passed ? statusTone.wired : statusTone.orphaned} />
                  <Pill label={`${formatCompact(stressSummary.audit_self_validation_check_count)} checks`} tone="border-success/30 bg-success/10 text-success" />
                  <Pill label={`${formatCompact(stressSummary.audit_self_validation_failed_count)} failed`} tone={asNumber(stressSummary.audit_self_validation_failed_count) ? statusTone.security_blocker : statusTone.wired} />
                  <Pill label={String(stressSummary.audit_self_validation_proof_basis || "proof basis pending").replace(/_/g, " ")} tone="border-success/30 bg-success/10 text-success" />
                </div>
              </div>
              <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-4">
                {auditSelfValidationRows.slice(0, 8).map((row, index) => (
                  <div key={`self-validation-${String(row.check || index)}`} className="rounded-md border border-border/40 bg-black/20 px-3 py-2 text-xs">
                    <div className="flex items-center justify-between gap-2">
                      <span className="truncate font-medium">{String(row.check || "self check").replace(/_/g, " ")}</span>
                      <Pill label={row.passing ? "pass" : "attention"} tone={row.passing ? statusTone.wired : statusTone.orphaned} />
                    </div>
                    <div className="mt-1 line-clamp-2 text-muted-foreground">{String(row.detail || "")}</div>
                  </div>
                ))}
              </div>
              {auditSelfValidationFailedRows.length ? (
                <div className="grid gap-2 md:grid-cols-2">
                  {auditSelfValidationFailedRows.slice(0, 4).map((row, index) => (
                    <div key={`self-validation-failed-${String(row.check || index)}`} className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs">
                      <div className="font-medium">{String(row.check || "failed self check").replace(/_/g, " ")}</div>
                      <div className="mt-1 line-clamp-2 text-muted-foreground">{String(row.detail || "self-validation mismatch")}</div>
                    </div>
                  ))}
                </div>
              ) : null}
            </div>
          ) : null}
          {auditReplayValidationRows.length ? (
            <div className="mt-3 space-y-2 rounded-md border border-primary/20 bg-primary/5 p-3">
              <div className="flex items-center justify-between gap-2">
                <div className="text-xs uppercase text-muted-foreground">Audit Replay Validation</div>
                <div className="flex flex-wrap gap-1">
                  <Pill label={stressSummary.audit_replay_validation_passed ? "replay checked" : "replay attention"} tone={stressSummary.audit_replay_validation_passed ? statusTone.wired : statusTone.orphaned} />
                  <Pill label={`${formatCompact(stressSummary.audit_replay_validation_check_count)} checks`} tone="border-primary/30 bg-primary/10 text-primary" />
                  <Pill label={`${formatCompact(stressSummary.audit_replay_validation_failed_count)} failed`} tone={asNumber(stressSummary.audit_replay_validation_failed_count) ? statusTone.security_blocker : statusTone.wired} />
                </div>
              </div>
              <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-4">
                {auditReplayValidationRows.slice(0, 8).map((row, index) => (
                  <div key={`replay-validation-${String(row.check || index)}`} className="rounded-md border border-border/40 bg-black/20 px-3 py-2 text-xs">
                    <div className="flex items-center justify-between gap-2">
                      <span className="truncate font-medium">{String(row.check || "replay check").replace(/_/g, " ")}</span>
                      <Pill label={row.passing ? "pass" : "attention"} tone={row.passing ? statusTone.wired : statusTone.orphaned} />
                    </div>
                    <div className="mt-1 line-clamp-2 text-muted-foreground">{String(row.detail || "")}</div>
                    <div className="mt-1 grid grid-cols-2 gap-1 text-[11px] text-muted-foreground">
                      <span>expected {String(row.expected ?? "n/a")}</span>
                      <span>actual {String(row.actual ?? "n/a")}</span>
                    </div>
                  </div>
                ))}
              </div>
              {auditReplayValidationFailedRows.length ? (
                <div className="grid gap-2 md:grid-cols-2">
                  {auditReplayValidationFailedRows.slice(0, 4).map((row, index) => (
                    <div key={`replay-validation-failed-${String(row.check || index)}`} className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs">
                      <div className="font-medium">{String(row.check || "failed replay check").replace(/_/g, " ")}</div>
                      <div className="mt-1 line-clamp-2 text-muted-foreground">{String(row.detail || "audit replay mismatch")}</div>
                    </div>
                  ))}
                </div>
              ) : null}
            </div>
          ) : null}
          {auditIntegrityValidationRows.length ? (
            <div className="mt-3 space-y-2 rounded-md border border-primary/20 bg-primary/5 p-3">
              <div className="flex items-center justify-between gap-2">
                <div className="text-xs uppercase text-muted-foreground">Audit Integrity Triangulation</div>
                <div className="flex flex-wrap gap-1">
                  <Pill label={stressSummary.audit_integrity_validation_passed ? "integrity checked" : "integrity attention"} tone={stressSummary.audit_integrity_validation_passed ? statusTone.wired : statusTone.orphaned} />
                  <Pill label={`${formatCompact(stressSummary.audit_integrity_validation_check_count)} checks`} tone="border-primary/30 bg-primary/10 text-primary" />
                  <Pill label={`${formatCompact(stressSummary.audit_integrity_validation_failed_count)} failed`} tone={asNumber(stressSummary.audit_integrity_validation_failed_count) ? statusTone.security_blocker : statusTone.wired} />
                </div>
              </div>
              <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-4">
                {auditIntegrityValidationRows.slice(0, 8).map((row, index) => (
                  <div key={`integrity-validation-${String(row.check || index)}`} className="rounded-md border border-border/40 bg-black/20 px-3 py-2 text-xs">
                    <div className="flex items-center justify-between gap-2">
                      <span className="truncate font-medium">{String(row.check || "integrity check").replace(/_/g, " ")}</span>
                      <Pill label={row.passing ? "pass" : "attention"} tone={row.passing ? statusTone.wired : statusTone.orphaned} />
                    </div>
                    <div className="mt-1 line-clamp-2 text-muted-foreground">{String(row.detail || "")}</div>
                  </div>
                ))}
              </div>
              {auditIntegrityValidationFailedRows.length ? (
                <div className="grid gap-2 md:grid-cols-2">
                  {auditIntegrityValidationFailedRows.slice(0, 4).map((row, index) => (
                    <div key={`integrity-validation-failed-${String(row.check || index)}`} className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs">
                      <div className="font-medium">{String(row.check || "failed integrity check").replace(/_/g, " ")}</div>
                      <div className="mt-1 line-clamp-2 text-muted-foreground">{String(row.detail || "audit integrity mismatch")}</div>
                    </div>
                  ))}
                </div>
              ) : null}
            </div>
          ) : null}
          {auditValidationQuorumRows.length ? (
            <div className="mt-3 space-y-2 rounded-md border border-primary/20 bg-primary/5 p-3">
              <div className="flex items-center justify-between gap-2">
                <div className="text-xs uppercase text-muted-foreground">Audit Validation Quorum</div>
                <div className="flex flex-wrap gap-1">
                  <Pill label={stressSummary.audit_validation_quorum_passed ? "quorum trusted" : "quorum attention"} tone={stressSummary.audit_validation_quorum_passed ? statusTone.wired : statusTone.orphaned} />
                  <Pill label={`${formatCompact(stressSummary.audit_validation_quorum_pass_count)}/${formatCompact(stressSummary.audit_validation_quorum_required_count)} mirrors`} tone="border-primary/30 bg-primary/10 text-primary" />
                  <Pill label={`${formatCompact(stressSummary.audit_validation_quorum_failed_count)} failed`} tone={asNumber(stressSummary.audit_validation_quorum_failed_count) ? statusTone.security_blocker : statusTone.wired} />
                </div>
              </div>
              <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-4">
                {auditValidationQuorumRows.slice(0, 8).map((row, index) => (
                  <div key={`validation-quorum-${String(row.check || index)}`} className="rounded-md border border-border/40 bg-black/20 px-3 py-2 text-xs">
                    <div className="flex items-center justify-between gap-2">
                      <span className="truncate font-medium">{String(row.check || "quorum check").replace(/_/g, " ")}</span>
                      <Pill label={row.passing ? "pass" : "attention"} tone={row.passing ? statusTone.wired : statusTone.orphaned} />
                    </div>
                    <div className="mt-1 line-clamp-2 text-muted-foreground">{String(row.detail || "")}</div>
                  </div>
                ))}
              </div>
              {auditValidationQuorumFailedRows.length ? (
                <div className="grid gap-2 md:grid-cols-2">
                  {auditValidationQuorumFailedRows.slice(0, 4).map((row, index) => (
                    <div key={`validation-quorum-failed-${String(row.check || index)}`} className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs">
                      <div className="font-medium">{String(row.check || "failed quorum check").replace(/_/g, " ")}</div>
                      <div className="mt-1 line-clamp-2 text-muted-foreground">{String(row.detail || "validation quorum mismatch")}</div>
                    </div>
                  ))}
                </div>
              ) : null}
            </div>
          ) : null}
          {auditArtifactProvenanceRows.length ? (
            <div className="mt-3 space-y-2 rounded-md border border-primary/20 bg-primary/5 p-3">
              <div className="flex items-center justify-between gap-2">
                <div className="text-xs uppercase text-muted-foreground">Audit Artifact Provenance</div>
                <div className="flex flex-wrap gap-1">
                  <Pill label={stressSummary.audit_artifact_provenance_passed ? "artifacts matched" : "artifact attention"} tone={stressSummary.audit_artifact_provenance_passed ? statusTone.wired : statusTone.orphaned} />
                  <Pill label={`${formatCompact(stressSummary.audit_artifact_provenance_json_match_count)}/${formatCompact(stressSummary.audit_artifact_provenance_json_artifact_count)} hashes`} tone="border-primary/30 bg-primary/10 text-primary" />
                  <Pill label={`${formatCompact(stressSummary.audit_artifact_provenance_failed_count)} failed`} tone={asNumber(stressSummary.audit_artifact_provenance_failed_count) ? statusTone.security_blocker : statusTone.wired} />
                </div>
              </div>
              <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-4">
                {auditArtifactProvenanceRows.slice(0, 8).map((row, index) => (
                  <div key={`artifact-provenance-${String(row.check || index)}`} className="rounded-md border border-border/40 bg-black/20 px-3 py-2 text-xs">
                    <div className="flex items-center justify-between gap-2">
                      <span className="truncate font-medium">{String(row.check || "artifact check").replace(/_/g, " ")}</span>
                      <Pill label={row.passing ? "pass" : "attention"} tone={row.passing ? statusTone.wired : statusTone.orphaned} />
                    </div>
                    <div className="mt-1 line-clamp-2 text-muted-foreground">{String(row.detail || "")}</div>
                  </div>
                ))}
              </div>
              {auditArtifactProvenanceFailedRows.length ? (
                <div className="grid gap-2 md:grid-cols-2">
                  {auditArtifactProvenanceFailedRows.slice(0, 4).map((row, index) => (
                    <div key={`artifact-provenance-failed-${String(row.check || index)}`} className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs">
                      <div className="font-medium">{String(row.check || "failed artifact check").replace(/_/g, " ")}</div>
                      <div className="mt-1 line-clamp-2 text-muted-foreground">{String(row.detail || "artifact provenance mismatch")}</div>
                    </div>
                  ))}
                </div>
              ) : null}
            </div>
          ) : null}
          {auditServedArtifactRows.length ? (
            <div className="mt-3 space-y-2 rounded-md border border-slate-500/20 bg-slate-500/5 p-3">
              <div className="flex items-center justify-between gap-2">
                <div className="text-xs uppercase text-muted-foreground">Audit Served Artifact</div>
                <div className="flex flex-wrap gap-1">
                  <Pill label={stressSummary.audit_served_artifact_passed ? "served matched" : "served attention"} tone={stressSummary.audit_served_artifact_passed ? statusTone.wired : statusTone.orphaned} />
                  <Pill label={stressSummary.audit_served_artifact_checked ? "localhost checked" : "fixture skip"} tone="border-slate-500/30 bg-slate-500/10 text-slate-200" />
                  <Pill label={`${formatCompact(stressSummary.audit_served_artifact_failed_count)} failed`} tone={asNumber(stressSummary.audit_served_artifact_failed_count) ? statusTone.security_blocker : statusTone.wired} />
                </div>
              </div>
              <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-4">
                {auditServedArtifactRows.slice(0, 8).map((row, index) => (
                  <div key={`served-artifact-${String(row.check || index)}`} className="rounded-md border border-border/40 bg-black/20 px-3 py-2 text-xs">
                    <div className="flex items-center justify-between gap-2">
                      <span className="truncate font-medium">{String(row.check || "served check").replace(/_/g, " ")}</span>
                      <Pill label={row.passing ? "pass" : "attention"} tone={row.passing ? statusTone.wired : statusTone.orphaned} />
                    </div>
                    <div className="mt-1 line-clamp-2 text-muted-foreground">{String(row.detail || "")}</div>
                  </div>
                ))}
              </div>
              {auditServedArtifactFailedRows.length ? (
                <div className="grid gap-2 md:grid-cols-2">
                  {auditServedArtifactFailedRows.slice(0, 4).map((row, index) => (
                    <div key={`served-artifact-failed-${String(row.check || index)}`} className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs">
                      <div className="font-medium">{String(row.check || "failed served check").replace(/_/g, " ")}</div>
                      <div className="mt-1 line-clamp-2 text-muted-foreground">{String(row.detail || "served artifact mismatch")}</div>
                    </div>
                  ))}
                </div>
              ) : null}
            </div>
          ) : null}
          {auditFreshnessSlaRows.length ? (
            <div className="mt-3 space-y-2 rounded-md border border-success/20 bg-success/5 p-3">
              <div className="flex items-center justify-between gap-2">
                <div className="text-xs uppercase text-muted-foreground">Audit Freshness SLA</div>
                <div className="flex flex-wrap gap-1">
                  <Pill label={stressSummary.audit_freshness_sla_passed ? "fresh" : "stale attention"} tone={stressSummary.audit_freshness_sla_passed ? statusTone.wired : statusTone.orphaned} />
                  <Pill label={`${formatCompact(stressSummary.audit_freshness_sla_age_sec)}s age`} tone="border-success/30 bg-success/10 text-success" />
                  <Pill label={`${formatCompact(stressSummary.audit_freshness_sla_failed_count)} failed`} tone={asNumber(stressSummary.audit_freshness_sla_failed_count) ? statusTone.security_blocker : statusTone.wired} />
                </div>
              </div>
              <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-4">
                {auditFreshnessSlaRows.slice(0, 8).map((row, index) => (
                  <div key={`freshness-sla-${String(row.check || index)}`} className="rounded-md border border-border/40 bg-black/20 px-3 py-2 text-xs">
                    <div className="flex items-center justify-between gap-2">
                      <span className="truncate font-medium">{String(row.check || "freshness check").replace(/_/g, " ")}</span>
                      <Pill label={row.passing ? "pass" : "attention"} tone={row.passing ? statusTone.wired : statusTone.orphaned} />
                    </div>
                    <div className="mt-1 line-clamp-2 text-muted-foreground">{String(row.detail || "")}</div>
                  </div>
                ))}
              </div>
              {auditFreshnessSlaFailedRows.length ? (
                <div className="grid gap-2 md:grid-cols-2">
                  {auditFreshnessSlaFailedRows.slice(0, 4).map((row, index) => (
                    <div key={`freshness-sla-failed-${String(row.check || index)}`} className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs">
                      <div className="font-medium">{String(row.check || "failed freshness check").replace(/_/g, " ")}</div>
                      <div className="mt-1 line-clamp-2 text-muted-foreground">{String(row.detail || "freshness SLA mismatch")}</div>
                    </div>
                  ))}
                </div>
              ) : null}
            </div>
          ) : null}
          {auditOperatorSurfaceRows.length ? (
            <div className="mt-3 space-y-2 rounded-md border border-primary/20 bg-primary/5 p-3">
              <div className="flex items-center justify-between gap-2">
                <div className="text-xs uppercase text-muted-foreground">Audit Operator Surface</div>
                <div className="flex flex-wrap gap-1">
                  <Pill label={stressSummary.audit_operator_surface_passed ? "surface stable" : "surface attention"} tone={stressSummary.audit_operator_surface_passed ? statusTone.wired : statusTone.orphaned} />
                  <Pill label={`${formatCompact(stressSummary.audit_operator_surface_required_panel_count)} panels`} tone="border-primary/30 bg-primary/10 text-primary" />
                  <Pill label={`${formatCompact(stressSummary.audit_operator_surface_mutation_control_count)} controls`} tone={asNumber(stressSummary.audit_operator_surface_mutation_control_count) ? statusTone.security_blocker : statusTone.wired} />
                </div>
              </div>
              <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-4">
                {auditOperatorSurfaceRows.slice(0, 8).map((row, index) => (
                  <div key={`operator-surface-${String(row.check || index)}`} className="rounded-md border border-border/40 bg-black/20 px-3 py-2 text-xs">
                    <div className="flex items-center justify-between gap-2">
                      <span className="truncate font-medium">{String(row.check || "surface check").replace(/_/g, " ")}</span>
                      <Pill label={row.passing ? "pass" : "attention"} tone={row.passing ? statusTone.wired : statusTone.orphaned} />
                    </div>
                    <div className="mt-1 line-clamp-2 text-muted-foreground">{String(row.detail || "")}</div>
                  </div>
                ))}
              </div>
              {auditOperatorSurfaceFailedRows.length ? (
                <div className="grid gap-2 md:grid-cols-2">
                  {auditOperatorSurfaceFailedRows.slice(0, 4).map((row, index) => (
                    <div key={`operator-surface-failed-${String(row.check || index)}`} className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs">
                      <div className="font-medium">{String(row.check || "failed surface check").replace(/_/g, " ")}</div>
                      <div className="mt-1 line-clamp-2 text-muted-foreground">{String(row.detail || "operator surface mismatch")}</div>
                    </div>
                  ))}
                </div>
              ) : null}
            </div>
          ) : null}
          {auditTestCoverageRows.length ? (
            <div className="mt-3 space-y-2 rounded-md border border-success/20 bg-success/5 p-3">
              <div className="flex items-center justify-between gap-2">
                <div className="text-xs uppercase text-muted-foreground">Audit Test Coverage</div>
                <div className="flex flex-wrap gap-1">
                  <Pill label={stressSummary.audit_test_coverage_passed ? "tests mapped" : "test attention"} tone={stressSummary.audit_test_coverage_passed ? statusTone.wired : statusTone.orphaned} />
                  <Pill label={`${formatCompact(stressSummary.audit_test_coverage_validator_test_count)}/${formatCompact(stressSummary.audit_test_coverage_validator_expected_count)} validators`} tone="border-success/30 bg-success/10 text-success" />
                  <Pill label={`${formatCompact(stressSummary.audit_test_coverage_failed_count)} failed`} tone={asNumber(stressSummary.audit_test_coverage_failed_count) ? statusTone.security_blocker : statusTone.wired} />
                </div>
              </div>
              {auditTestCoverageValidatorRows.length ? (
                <div className="flex flex-wrap gap-1">
                  {auditTestCoverageValidatorRows.slice(0, 12).map((row) => (
                    <Pill
                      key={String(row.validator_id)}
                      label={`${String(row.validator_id || "validator").replace(/_/g, " ")} ${row.covered ? "covered" : "attention"}`}
                      tone={row.covered ? statusTone.wired : statusTone.orphaned}
                    />
                  ))}
                </div>
              ) : null}
              <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-4">
                {auditTestCoverageRows.slice(0, 8).map((row, index) => (
                  <div key={`test-coverage-${String(row.check || index)}`} className="rounded-md border border-border/40 bg-black/20 px-3 py-2 text-xs">
                    <div className="flex items-center justify-between gap-2">
                      <span className="truncate font-medium">{String(row.check || "coverage check").replace(/_/g, " ")}</span>
                      <Pill label={row.passing ? "pass" : "attention"} tone={row.passing ? statusTone.wired : statusTone.orphaned} />
                    </div>
                    <div className="mt-1 line-clamp-2 text-muted-foreground">{String(row.detail || "")}</div>
                  </div>
                ))}
              </div>
              {auditTestCoverageFailedRows.length ? (
                <div className="grid gap-2 md:grid-cols-2">
                  {auditTestCoverageFailedRows.slice(0, 4).map((row, index) => (
                    <div key={`test-coverage-failed-${String(row.check || index)}`} className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs">
                      <div className="font-medium">{String(row.check || "failed coverage check").replace(/_/g, " ")}</div>
                      <div className="mt-1 line-clamp-2 text-muted-foreground">{String(row.detail || "test coverage mismatch")}</div>
                    </div>
                  ))}
                </div>
              ) : null}
            </div>
          ) : null}
          {auditRepairCoverageRows.length ? (
            <div className="mt-3 space-y-2 rounded-md border border-warning/20 bg-warning/5 p-3">
              <div className="flex items-center justify-between gap-2">
                <div className="text-xs uppercase text-muted-foreground">Audit Repair Coverage</div>
                <div className="flex flex-wrap gap-1">
                  <Pill label={stressSummary.audit_repair_coverage_passed ? "repairs actionable" : "repair attention"} tone={stressSummary.audit_repair_coverage_passed ? statusTone.wired : statusTone.orphaned} />
                  <Pill label={`${formatCompact(stressSummary.audit_repair_coverage_repair_action_count)} repair rows`} tone="border-warning/30 bg-warning/10 text-warning" />
                  <Pill label={`${formatCompact(stressSummary.audit_repair_coverage_generic_repair_count)} generic`} tone={asNumber(stressSummary.audit_repair_coverage_generic_repair_count) ? statusTone.security_blocker : statusTone.wired} />
                </div>
              </div>
              <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-4">
                {auditRepairCoverageRows.slice(0, 8).map((row, index) => (
                  <div key={`repair-coverage-${String(row.check || index)}`} className="rounded-md border border-border/40 bg-black/20 px-3 py-2 text-xs">
                    <div className="flex items-center justify-between gap-2">
                      <span className="truncate font-medium">{String(row.check || "repair check").replace(/_/g, " ")}</span>
                      <Pill label={row.passing ? "pass" : "attention"} tone={row.passing ? statusTone.wired : statusTone.orphaned} />
                    </div>
                    <div className="mt-1 line-clamp-2 text-muted-foreground">{String(row.detail || "")}</div>
                  </div>
                ))}
              </div>
              {auditRepairCoverageFailedRows.length ? (
                <div className="grid gap-2 md:grid-cols-2">
                  {auditRepairCoverageFailedRows.slice(0, 4).map((row, index) => (
                    <div key={`repair-coverage-failed-${String(row.check || index)}`} className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs">
                      <div className="font-medium">{String(row.check || "failed repair check").replace(/_/g, " ")}</div>
                      <div className="mt-1 line-clamp-2 text-muted-foreground">{String(row.detail || "repair coverage mismatch")}</div>
                    </div>
                  ))}
                </div>
              ) : null}
            </div>
          ) : null}
          {auditRuntimeRepairReadinessRows.length ? (
            <div className="mt-3 space-y-2 rounded-md border border-warning/20 bg-warning/5 p-3">
              <div className="flex items-center justify-between gap-2">
                <div className="text-xs uppercase text-muted-foreground">Audit Runtime Repair Readiness</div>
                <div className="flex flex-wrap gap-1">
                  <Pill label={stressSummary.audit_runtime_repair_readiness_passed ? "guarded ready" : "guard attention"} tone={stressSummary.audit_runtime_repair_readiness_passed ? statusTone.wired : statusTone.orphaned} />
                  <Pill label={`${formatCompact(stressSummary.audit_runtime_repair_readiness_guarded_command_line_count)} lines`} tone="border-warning/30 bg-warning/10 text-warning" />
                  <Pill label={`${formatCompact(stressSummary.audit_runtime_repair_readiness_unsafe_command_count)} unsafe`} tone={asNumber(stressSummary.audit_runtime_repair_readiness_unsafe_command_count) ? statusTone.security_blocker : statusTone.wired} />
                </div>
              </div>
              <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-4">
                {auditRuntimeRepairReadinessRows.slice(0, 8).map((row, index) => (
                  <div key={`runtime-repair-readiness-${String(row.check || index)}`} className="rounded-md border border-border/40 bg-black/20 px-3 py-2 text-xs">
                    <div className="flex items-center justify-between gap-2">
                      <span className="truncate font-medium">{String(row.check || "runtime repair check").replace(/_/g, " ")}</span>
                      <Pill label={row.passing ? "pass" : "attention"} tone={row.passing ? statusTone.wired : statusTone.orphaned} />
                    </div>
                    <div className="mt-1 line-clamp-2 text-muted-foreground">{String(row.detail || "")}</div>
                  </div>
                ))}
              </div>
              {auditRuntimeRepairReadinessFailedRows.length ? (
                <div className="grid gap-2 md:grid-cols-2">
                  {auditRuntimeRepairReadinessFailedRows.slice(0, 4).map((row, index) => (
                    <div key={`runtime-repair-readiness-failed-${String(row.check || index)}`} className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs">
                      <div className="font-medium">{String(row.check || "failed runtime repair check").replace(/_/g, " ")}</div>
                      <div className="mt-1 line-clamp-2 text-muted-foreground">{String(row.detail || "runtime repair readiness mismatch")}</div>
                    </div>
                  ))}
                </div>
              ) : null}
            </div>
          ) : null}
          {auditRepairAcceptanceRows.length ? (
            <div className="mt-3 space-y-2 rounded-md border border-warning/20 bg-warning/5 p-3">
              <div className="flex items-center justify-between gap-2">
                <div className="text-xs uppercase text-muted-foreground">Audit Repair Acceptance</div>
                <div className="flex flex-wrap gap-1">
                  <Pill label={stressSummary.audit_repair_acceptance_passed ? "acceptance mapped" : "acceptance attention"} tone={stressSummary.audit_repair_acceptance_passed ? statusTone.wired : statusTone.orphaned} />
                  <Pill label={`${formatCompact(stressSummary.audit_repair_acceptance_acceptance_row_count)} blockers`} tone="border-warning/30 bg-warning/10 text-warning" />
                  <Pill label={`${formatCompact(stressSummary.audit_repair_acceptance_missing_acceptance_count)} missing`} tone={asNumber(stressSummary.audit_repair_acceptance_missing_acceptance_count) ? statusTone.security_blocker : statusTone.wired} />
                </div>
              </div>
              {auditRepairAcceptanceBlockerRows.length ? (
                <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-4">
                  {auditRepairAcceptanceBlockerRows.slice(0, 8).map((row, index) => (
                    <div key={`repair-acceptance-blocker-${String(row.blocker || index)}`} className="rounded-md border border-border/40 bg-black/20 px-3 py-2 text-xs">
                      <div className="flex items-center justify-between gap-2">
                        <span className="truncate font-medium">{String(row.blocker || "blocker").replace(/_/g, " ")}</span>
                        <Pill label={row.acceptance_ready ? "ready" : "attention"} tone={row.acceptance_ready ? statusTone.wired : statusTone.orphaned} />
                      </div>
                      <div className="mt-1 line-clamp-2 text-muted-foreground">
                        {String(Array.isArray(row.acceptance_requirements) ? row.acceptance_requirements.join(", ") : "acceptance proof")}
                      </div>
                    </div>
                  ))}
                </div>
              ) : null}
              <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-4">
                {auditRepairAcceptanceRows.slice(0, 8).map((row, index) => (
                  <div key={`repair-acceptance-${String(row.check || index)}`} className="rounded-md border border-border/40 bg-black/20 px-3 py-2 text-xs">
                    <div className="flex items-center justify-between gap-2">
                      <span className="truncate font-medium">{String(row.check || "acceptance check").replace(/_/g, " ")}</span>
                      <Pill label={row.passing ? "pass" : "attention"} tone={row.passing ? statusTone.wired : statusTone.orphaned} />
                    </div>
                    <div className="mt-1 line-clamp-2 text-muted-foreground">{String(row.detail || "")}</div>
                  </div>
                ))}
              </div>
              {auditRepairAcceptanceFailedRows.length ? (
                <div className="grid gap-2 md:grid-cols-2">
                  {auditRepairAcceptanceFailedRows.slice(0, 4).map((row, index) => (
                    <div key={`repair-acceptance-failed-${String(row.check || index)}`} className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs">
                      <div className="font-medium">{String(row.check || "failed acceptance check").replace(/_/g, " ")}</div>
                      <div className="mt-1 line-clamp-2 text-muted-foreground">{String(row.detail || "repair acceptance mismatch")}</div>
                    </div>
                  ))}
                </div>
              ) : null}
            </div>
          ) : null}
          {auditConsistencyMatrixRows.length ? (
            <div className="mt-3 space-y-2 rounded-md border border-primary/20 bg-primary/5 p-3">
              <div className="flex items-center justify-between gap-2">
                <div className="text-xs uppercase text-muted-foreground">Audit Consistency Matrix</div>
                <div className="flex flex-wrap gap-1">
                  <Pill label={stressSummary.audit_consistency_matrix_passed ? "matrix stable" : "matrix attention"} tone={stressSummary.audit_consistency_matrix_passed ? statusTone.wired : statusTone.orphaned} />
                  <Pill label={`${formatCompact(stressSummary.audit_consistency_matrix_validator_pass_count)}/${formatCompact(stressSummary.audit_consistency_matrix_validator_count)} validators`} tone="border-primary/30 bg-primary/10 text-primary" />
                  <Pill label={`${formatCompact(stressSummary.audit_consistency_matrix_inconsistent_validator_count)} drift`} tone={asNumber(stressSummary.audit_consistency_matrix_inconsistent_validator_count) ? statusTone.security_blocker : statusTone.wired} />
                </div>
              </div>
              {auditConsistencyMatrixValidatorRows.length ? (
                <div className="flex flex-wrap gap-1">
                  {auditConsistencyMatrixValidatorRows.slice(0, 14).map((row) => (
                    <Pill
                      key={String(row.validator_id)}
                      label={`${String(row.validator_id || "validator").replace(/_/g, " ")} ${row.matrix_consistent ? "consistent" : "drift"}`}
                      tone={row.matrix_consistent ? statusTone.wired : statusTone.orphaned}
                    />
                  ))}
                </div>
              ) : null}
              <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-4">
                {auditConsistencyMatrixRows.slice(0, 8).map((row, index) => (
                  <div key={`consistency-matrix-${String(row.check || index)}`} className="rounded-md border border-border/40 bg-black/20 px-3 py-2 text-xs">
                    <div className="flex items-center justify-between gap-2">
                      <span className="truncate font-medium">{String(row.check || "matrix check").replace(/_/g, " ")}</span>
                      <Pill label={row.passing ? "pass" : "attention"} tone={row.passing ? statusTone.wired : statusTone.orphaned} />
                    </div>
                    <div className="mt-1 line-clamp-2 text-muted-foreground">{String(row.detail || "")}</div>
                  </div>
                ))}
              </div>
              {auditConsistencyMatrixFailedRows.length ? (
                <div className="grid gap-2 md:grid-cols-2">
                  {auditConsistencyMatrixFailedRows.slice(0, 4).map((row, index) => (
                    <div key={`consistency-matrix-failed-${String(row.check || index)}`} className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs">
                      <div className="font-medium">{String(row.check || "failed matrix check").replace(/_/g, " ")}</div>
                      <div className="mt-1 line-clamp-2 text-muted-foreground">{String(row.detail || "audit consistency drift")}</div>
                    </div>
                  ))}
                </div>
              ) : null}
            </div>
          ) : null}
          {auditEvidenceLineageRows.length ? (
            <div className="mt-3 space-y-2 rounded-md border border-success/20 bg-success/5 p-3">
              <div className="flex items-center justify-between gap-2">
                <div className="text-xs uppercase text-muted-foreground">Audit Evidence Lineage</div>
                <div className="flex flex-wrap gap-1">
                  <Pill label={stressSummary.audit_evidence_lineage_passed ? "lineage stable" : "lineage attention"} tone={stressSummary.audit_evidence_lineage_passed ? statusTone.wired : statusTone.orphaned} />
                  <Pill label={`${formatCompact(stressSummary.audit_evidence_lineage_section_row_count)} sections`} tone="border-success/30 bg-success/10 text-success" />
                  <Pill label={`${formatCompact(stressSummary.audit_evidence_lineage_missing_lineage_count)} missing`} tone={asNumber(stressSummary.audit_evidence_lineage_missing_lineage_count) ? statusTone.security_blocker : statusTone.wired} />
                </div>
              </div>
              {auditEvidenceLineageSectionRows.length ? (
                <div className="flex flex-wrap gap-1">
                  {auditEvidenceLineageSectionRows.slice(0, 16).map((row, index) => (
                    <Pill
                      key={`lineage-section-${String(row.section_id || index)}`}
                      label={`${String(row.section_id || "section").replace(/_/g, " ")} ${row.lineage_present ? "traced" : "attention"}`}
                      tone={row.lineage_present ? statusTone.wired : statusTone.orphaned}
                    />
                  ))}
                </div>
              ) : null}
              <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-4">
                {auditEvidenceLineageRows.slice(0, 8).map((row, index) => (
                  <div key={`evidence-lineage-${String(row.check || index)}`} className="rounded-md border border-border/40 bg-black/20 px-3 py-2 text-xs">
                    <div className="flex items-center justify-between gap-2">
                      <span className="truncate font-medium">{String(row.check || "lineage check").replace(/_/g, " ")}</span>
                      <Pill label={row.passing ? "pass" : "attention"} tone={row.passing ? statusTone.wired : statusTone.orphaned} />
                    </div>
                    <div className="mt-1 line-clamp-2 text-muted-foreground">{String(row.detail || "")}</div>
                  </div>
                ))}
              </div>
              {auditEvidenceLineageFailedRows.length ? (
                <div className="grid gap-2 md:grid-cols-2">
                  {auditEvidenceLineageFailedRows.slice(0, 4).map((row, index) => (
                    <div key={`evidence-lineage-failed-${String(row.check || index)}`} className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs">
                      <div className="font-medium">{String(row.check || "failed lineage check").replace(/_/g, " ")}</div>
                      <div className="mt-1 line-clamp-2 text-muted-foreground">{String(row.detail || "evidence lineage mismatch")}</div>
                    </div>
                  ))}
                </div>
              ) : null}
            </div>
          ) : null}
          {auditValidatorClosureRows.length ? (
            <div className="mt-3 space-y-2 rounded-md border border-primary/20 bg-primary/5 p-3">
              <div className="flex items-center justify-between gap-2">
                <div className="text-xs uppercase text-muted-foreground">Audit Validator Closure</div>
                <div className="flex flex-wrap gap-1">
                  <Pill label={stressSummary.audit_validator_closure_passed ? "closure stable" : "closure attention"} tone={stressSummary.audit_validator_closure_passed ? statusTone.wired : statusTone.orphaned} />
                  <Pill label={`${formatCompact(stressSummary.audit_validator_closure_validator_count)} validators`} tone="border-primary/30 bg-primary/10 text-primary" />
                  <Pill label={`${formatCompact(stressSummary.audit_validator_closure_failed_source_count)} source gaps`} tone={asNumber(stressSummary.audit_validator_closure_failed_source_count) ? statusTone.security_blocker : statusTone.wired} />
                </div>
              </div>
              {auditValidatorClosureSourceRows.length ? (
                <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-3">
                  {auditValidatorClosureSourceRows.slice(0, 6).map((row, index) => (
                    <div key={`validator-closure-source-${String(row.source || index)}`} className="rounded-md border border-border/40 bg-black/20 px-3 py-2 text-xs">
                      <div className="flex items-center justify-between gap-2">
                        <span className="truncate font-medium">{String(row.source || "source").replace(/_/g, " ")}</span>
                        <Pill label={row.passing ? "closed" : "attention"} tone={row.passing ? statusTone.wired : statusTone.orphaned} />
                      </div>
                      <div className="mt-1 line-clamp-2 text-muted-foreground">{String(row.detail || "")}</div>
                    </div>
                  ))}
                </div>
              ) : null}
              <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-4">
                {auditValidatorClosureRows.slice(0, 8).map((row, index) => (
                  <div key={`validator-closure-${String(row.check || index)}`} className="rounded-md border border-border/40 bg-black/20 px-3 py-2 text-xs">
                    <div className="flex items-center justify-between gap-2">
                      <span className="truncate font-medium">{String(row.check || "closure check").replace(/_/g, " ")}</span>
                      <Pill label={row.passing ? "pass" : "attention"} tone={row.passing ? statusTone.wired : statusTone.orphaned} />
                    </div>
                    <div className="mt-1 line-clamp-2 text-muted-foreground">{String(row.detail || "")}</div>
                  </div>
                ))}
              </div>
              {auditValidatorClosureFailedRows.length ? (
                <div className="grid gap-2 md:grid-cols-2">
                  {auditValidatorClosureFailedRows.slice(0, 4).map((row, index) => (
                    <div key={`validator-closure-failed-${String(row.check || index)}`} className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs">
                      <div className="font-medium">{String(row.check || "failed closure check").replace(/_/g, " ")}</div>
                      <div className="mt-1 line-clamp-2 text-muted-foreground">{String(row.detail || "validator closure mismatch")}</div>
                    </div>
                  ))}
                </div>
              ) : null}
            </div>
          ) : null}
          {auditPublicContractRows.length ? (
            <div className="mt-3 space-y-2 rounded-md border border-primary/20 bg-primary/5 p-3">
              <div className="flex items-center justify-between gap-2">
                <div className="text-xs uppercase text-muted-foreground">Audit Public Contract</div>
                <div className="flex flex-wrap gap-1">
                  <Pill label={stressSummary.audit_public_contract_passed ? "contract stable" : "contract attention"} tone={stressSummary.audit_public_contract_passed ? statusTone.wired : statusTone.orphaned} />
                  <Pill label={`${formatCompact(stressSummary.audit_public_contract_required_summary_field_count)} fields`} tone="border-primary/30 bg-primary/10 text-primary" />
                  <Pill label={`${formatCompact(stressSummary.audit_public_contract_failed_count)} failed`} tone={asNumber(stressSummary.audit_public_contract_failed_count) ? statusTone.security_blocker : statusTone.wired} />
                </div>
              </div>
              <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-4">
                {auditPublicContractRows.slice(0, 8).map((row, index) => (
                  <div key={`public-contract-${String(row.check || index)}`} className="rounded-md border border-border/40 bg-black/20 px-3 py-2 text-xs">
                    <div className="flex items-center justify-between gap-2">
                      <span className="truncate font-medium">{String(row.check || "contract check").replace(/_/g, " ")}</span>
                      <Pill label={row.passing ? "pass" : "attention"} tone={row.passing ? statusTone.wired : statusTone.orphaned} />
                    </div>
                    <div className="mt-1 line-clamp-2 text-muted-foreground">{String(row.detail || "")}</div>
                  </div>
                ))}
              </div>
              {auditPublicContractFailedRows.length ? (
                <div className="grid gap-2 md:grid-cols-2">
                  {auditPublicContractFailedRows.slice(0, 4).map((row, index) => (
                    <div key={`public-contract-failed-${String(row.check || index)}`} className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs">
                      <div className="font-medium">{String(row.check || "failed contract check").replace(/_/g, " ")}</div>
                      <div className="mt-1 line-clamp-2 text-muted-foreground">{String(row.detail || "public contract mismatch")}</div>
                    </div>
                  ))}
                </div>
              ) : null}
            </div>
          ) : null}
          {auditValidationChainRows.length ? (
            <div className="mt-3 space-y-2 rounded-md border border-primary/20 bg-primary/5 p-3">
              <div className="flex items-center justify-between gap-2">
                <div className="text-xs uppercase text-muted-foreground">Audit Validation Chain</div>
                <div className="flex flex-wrap gap-1">
                  <Pill label={stressSummary.audit_validation_chain_passed ? "chain trusted" : "chain attention"} tone={stressSummary.audit_validation_chain_passed ? statusTone.wired : statusTone.orphaned} />
                  <Pill label={`${formatCompact(stressSummary.audit_validation_chain_validator_pass_count)}/${formatCompact(stressSummary.audit_validation_chain_validator_count)} validators`} tone="border-primary/30 bg-primary/10 text-primary" />
                  <Pill label={`${formatCompact(stressSummary.audit_validation_chain_failed_count)} failed`} tone={asNumber(stressSummary.audit_validation_chain_failed_count) ? statusTone.security_blocker : statusTone.wired} />
                </div>
              </div>
              {auditValidationChainValidatorRows.length ? (
                <div className="flex flex-wrap gap-1">
                  {auditValidationChainValidatorRows.slice(0, 8).map((row) => (
                    <Pill
                      key={String(row.validator_id)}
                      label={`${String(row.validator_id || "validator").replace(/_/g, " ")} ${row.passed ? "pass" : "attention"}`}
                      tone={row.passed ? statusTone.wired : statusTone.orphaned}
                    />
                  ))}
                </div>
              ) : null}
              <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-4">
                {auditValidationChainRows.slice(0, 8).map((row, index) => (
                  <div key={`validation-chain-${String(row.check || index)}`} className="rounded-md border border-border/40 bg-black/20 px-3 py-2 text-xs">
                    <div className="flex items-center justify-between gap-2">
                      <span className="truncate font-medium">{String(row.check || "chain check").replace(/_/g, " ")}</span>
                      <Pill label={row.passing ? "pass" : "attention"} tone={row.passing ? statusTone.wired : statusTone.orphaned} />
                    </div>
                    <div className="mt-1 line-clamp-2 text-muted-foreground">{String(row.detail || "")}</div>
                  </div>
                ))}
              </div>
              {auditValidationChainFailedRows.length ? (
                <div className="grid gap-2 md:grid-cols-2">
                  {auditValidationChainFailedRows.slice(0, 4).map((row, index) => (
                    <div key={`validation-chain-failed-${String(row.check || index)}`} className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs">
                      <div className="font-medium">{String(row.check || "failed chain check").replace(/_/g, " ")}</div>
                      <div className="mt-1 line-clamp-2 text-muted-foreground">{String(row.detail || "validation chain mismatch")}</div>
                    </div>
                  ))}
                </div>
              ) : null}
            </div>
          ) : null}
          {runtimeBurnDownRows.length ? (
            <div className="mt-3 grid gap-2 md:grid-cols-2 xl:grid-cols-3">
              {runtimeBurnDownRows.slice(0, 6).map((row, index) => (
                <div key={`runtime-${String(row.check || index)}`} className="rounded-md border border-border/40 bg-muted/10 px-3 py-2 text-xs">
                  <div className="flex items-center justify-between gap-2">
                    <span className="truncate font-medium">{String(row.check || "runtime check").replace(/_/g, " ")}</span>
                    <Pill label={row.passing ? "pass" : "attention"} tone={row.passing ? statusTone.wired : statusTone.orphaned} />
                  </div>
                  <div className="mt-1 line-clamp-2 text-muted-foreground">{String(row.detail || row.source || "")}</div>
                </div>
              ))}
            </div>
          ) : null}
          {runtimeProcessBurnDownRows.length ? (
            <div className="mt-3 grid gap-2 md:grid-cols-2 xl:grid-cols-4">
              {runtimeProcessBurnDownRows.slice(0, 4).map((row, index) => (
                <div key={`process-check-${String(row.check || index)}`} className="rounded-md border border-border/40 bg-muted/10 px-3 py-2 text-xs">
                  <div className="flex items-center justify-between gap-2">
                    <span className="truncate font-medium">{String(row.check || "process check").replace(/_/g, " ")}</span>
                    <Pill label={row.passing ? "pass" : "attention"} tone={row.passing ? statusTone.wired : statusTone.orphaned} />
                  </div>
                  <div className="mt-1 line-clamp-2 text-muted-foreground">{String(row.detail || row.source || "")}</div>
                </div>
              ))}
            </div>
          ) : null}
          {runtimeProcessRows.length ? (
            <div className="mt-3 grid gap-2 md:grid-cols-2">
              {runtimeProcessRows.slice(0, 4).map((row, index) => (
                <div key={`process-${String(row.pid || index)}`} className="rounded-md border border-border/40 bg-black/20 px-3 py-2 text-xs">
                  <div className="flex items-center justify-between gap-2">
                    <span className="truncate font-medium">{String(row.target || "runtime process").replace(/_/g, " ")}</span>
                    <Pill label={`PID ${String(row.pid || "n/a")}`} tone="border-primary/30 bg-primary/10 text-primary" />
                  </div>
                  <div className="mt-1 truncate text-muted-foreground">{String(row.exe || row.name || "")}</div>
                  <div className="mt-1 truncate font-mono text-[11px] text-muted-foreground">{String(row.command_line || "")}</div>
                </div>
              ))}
            </div>
          ) : null}
          {[...stopTargetRows, ...startTargetRows, ...postRestartRows].length ? (
            <div className="mt-3 space-y-2 rounded-md border border-primary/20 bg-primary/5 p-3">
              <div className="flex items-center justify-between gap-2">
                <div className="text-xs uppercase text-muted-foreground">Single-owner restart plan</div>
                <div className="flex flex-wrap gap-1">
                  <Pill label={stressSummary.single_owner_repair_ready ? "launcher ready" : "launcher attention"} tone={stressSummary.single_owner_repair_ready ? statusTone.wired : statusTone.orphaned} />
                  <Pill label={stressSummary.guarded_repair_command_ready ? "guarded command ready" : "guard attention"} tone={stressSummary.guarded_repair_command_ready ? statusTone.wired : statusTone.orphaned} />
                </div>
              </div>
              <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-3">
                {guardValidationRows.slice(0, 3).map((row, index) => (
                  <div key={`guard-row-${String(row.check || index)}`} className="rounded-md border border-success/30 bg-success/10 px-3 py-2 text-xs">
                    <div className="flex items-center justify-between gap-2">
                      <span className="truncate font-medium">{String(row.check || "guard check").replace(/_/g, " ")}</span>
                      <Pill label={row.passing ? "pass" : "attention"} tone={row.passing ? statusTone.wired : statusTone.orphaned} />
                    </div>
                    <div className="mt-1 truncate text-muted-foreground">{String(row.detail || "")}</div>
                  </div>
                ))}
                {stopTargetRows.slice(0, 4).map((row, index) => (
                  <div key={`stop-target-${String(row.pid || index)}`} className="rounded-md border border-warning/30 bg-warning/10 px-3 py-2 text-xs">
                    <div className="font-medium">Stop target PID {String(row.pid || "n/a")}</div>
                    <div className="mt-1 truncate text-muted-foreground">{String(row.reason || row.target || "")}</div>
                    <div className="mt-1 truncate font-mono text-[11px] text-muted-foreground">{String(row.command_preview || "")}</div>
                  </div>
                ))}
                {startTargetRows.slice(0, 3).map((row, index) => (
                  <div key={`start-target-${String(row.target || index)}`} className="rounded-md border border-primary/30 bg-primary/10 px-3 py-2 text-xs">
                    <div className="font-medium">{String(row.target || "start target").replace(/_/g, " ")}</div>
                    <div className="mt-1 truncate text-muted-foreground">{String(row.recommended_action || "")}</div>
                    <div className="mt-1 truncate font-mono text-[11px] text-muted-foreground">{String(row.command_preview || "")}</div>
                  </div>
                ))}
                {postRestartRows.slice(0, 3).map((row, index) => (
                  <div key={`post-check-${String(row.check || index)}`} className="rounded-md border border-border/40 bg-muted/10 px-3 py-2 text-xs">
                    <div className="font-medium">{String(row.check || "post check").replace(/_/g, " ")}</div>
                    <div className="mt-1 truncate text-muted-foreground">{String(row.expected || "")}</div>
                  </div>
                ))}
              </div>
              {guardedCommandLines.length ? (
                <div className="rounded-md border border-border/40 bg-black/30 p-3">
                  <div className="mb-2 text-xs uppercase text-muted-foreground">Guarded command preview</div>
                  <pre className="max-h-40 overflow-auto whitespace-pre-wrap break-words font-mono text-[11px] text-primary">
                    {guardedCommandLines.slice(0, 12).join("\n")}
                  </pre>
                </div>
              ) : null}
            </div>
          ) : null}
          {[...mutationRows, ...budgetRows, ...intentContractRows, ...repairRows].length ? (
            <div className="mt-3 grid gap-2 md:grid-cols-2">
              {mutationRows.slice(0, 2).map((row, index) => (
                <div key={`mutation-${String(row.lease_id || row.intent_id || index)}`} className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs">
                  <div className="font-medium">Mutation authority gap</div>
                  <div className="mt-1 truncate text-muted-foreground">{String(row.worker_id || "worker")} / {String(row.operation_type || row.route_key || "mutation")}</div>
                </div>
              ))}
              {budgetRows.slice(0, 2).map((row, index) => (
                <div key={`budget-${String(row.lease_id || row.venue || index)}`} className="rounded-md border border-warning/30 bg-warning/10 px-3 py-2 text-xs">
                  <div className="font-medium">API budget gap</div>
                  <div className="mt-1 truncate text-muted-foreground">{String(row.venue || "venue")} / {String(row.reason || row.state || "budget pressure")}</div>
                </div>
              ))}
              {intentContractRows.slice(0, 2).map((row, index) => (
                <div key={`intent-${String(row.intent_id || row.route_key || index)}`} className="rounded-md border border-warning/30 bg-warning/10 px-3 py-2 text-xs">
                  <div className="font-medium">Intent contract gap</div>
                  <div className="mt-1 truncate text-muted-foreground">{String(row.worker_id || "worker")} missing {String((row.missing_fields as string[] | undefined)?.join(", ") || "fields")}</div>
                </div>
              ))}
              {repairRows.slice(0, 3).map((row, index) => (
                <div key={`repair-${String(row.blocker || index)}`} className="rounded-md border border-border/40 bg-muted/10 px-3 py-2 text-xs">
                  <div className="font-medium">{String(row.owner || "parallel strategy unity")}</div>
                  <div className="mt-1 line-clamp-2 text-muted-foreground">{String(row.action || "inspect artifact rows")}</div>
                </div>
              ))}
            </div>
          ) : (
            <div className="mt-3 rounded-md border border-border/40 bg-muted/10 p-4 text-sm text-muted-foreground">
              Stress audit has no burn-down rows for the current parallel strategy artifact.
            </div>
          )}
          {stressWorkers.length ? (
            <div className="mt-3 flex flex-wrap gap-1">
              {stressWorkers.slice(0, 8).map((row) => (
                <Pill
                  key={String(row.worker_id)}
                  label={`${String(row.worker_id || "worker")} ${String(row.state || "pending").replace(/_/g, " ")}`}
                  tone={row.state === "worker_healthy" ? statusTone.wired : statusTone.orphaned}
                />
              ))}
            </div>
          ) : null}
        </div>

        <div className="grid gap-3 xl:grid-cols-[1.2fr_0.8fr]">
          <div className="space-y-2">
            <div className="flex items-center justify-between gap-2">
              <div className="text-xs uppercase text-muted-foreground">Worker heartbeats</div>
              <Pill label={allHealthy ? "all workers heartbeating" : "worker attention"} tone={allHealthy ? statusTone.wired : statusTone.orphaned} />
            </div>
            <div className="grid gap-2 md:grid-cols-2">
              {workers.length ? workers.slice(0, 8).map((worker) => {
                const api = asRecord(worker.api_budget_usage);
                return (
                  <div key={String(worker.worker_id || worker.label)} className="rounded-md border border-border/40 bg-muted/10 px-3 py-2 text-xs">
                    <div className="flex items-center justify-between gap-2">
                      <span className="truncate font-medium">{String(worker.label || worker.worker_id || "worker")}</span>
                      <Pill label={String(worker.strategy_status || "pending").replace(/_/g, " ")} tone={worker.strategy_status === "worker_healthy" ? statusTone.wired : statusTone.orphaned} />
                    </div>
                    <div className="mt-1 truncate text-muted-foreground">{String(worker.worker_id || "")} / PID {String(worker.pid || "n/a")}</div>
                    <div className="mt-2 grid grid-cols-2 gap-1 text-[11px] text-muted-foreground">
                      <span>venue {String(worker.venue || "internal")}</span>
                      <span>signals {formatCompact(worker.latest_signal_count)}</span>
                      <span>intents {formatCompact(worker.latest_intent_count)}</span>
                      <span>lease {String(api.lease_status || "pending")}</span>
                      <span className="col-span-2 truncate">route {String(worker.route_key || "waiting for candidate")}</span>
                    </div>
                  </div>
                );
              }) : (
                <div className="rounded-md border border-border/40 bg-muted/10 p-4 text-sm text-muted-foreground">
                  Parallel strategy supervisor has not published worker heartbeats yet.
                </div>
              )}
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between gap-2">
              <div className="text-xs uppercase text-muted-foreground">API request broker</div>
              <Pill label={asNumber(summary.request_denied_count) ? "budget attention" : "leases clean"} tone={asNumber(summary.request_denied_count) ? statusTone.orphaned : statusTone.wired} />
            </div>
            <div className="grid gap-2">
              {venues.length ? venues.slice(0, 6).map((venue) => (
                <div key={String(venue.venue)} className="rounded-md border border-border/40 bg-black/20 px-3 py-2 text-xs">
                  <div className="flex items-center justify-between gap-2">
                    <span className="uppercase text-muted-foreground">{String(venue.venue || "venue")}</span>
                    <span className="font-mono text-primary">{formatCompact(venue.rate_remaining)} left/min</span>
                  </div>
                  <div className="mt-1 text-muted-foreground">
                    used {formatCompact(venue.rate_used)} / limit {formatCompact(venue.rate_limit_per_min)} / leases {formatCompact(venue.lease_count)}
                  </div>
                </div>
              )) : (
                <div className="rounded-md border border-border/40 bg-muted/10 p-4 text-sm text-muted-foreground">
                  No API lease budget rows are visible yet.
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="grid gap-3 xl:grid-cols-[1fr_1fr]">
          <div className="space-y-2">
            <div className="flex items-center justify-between gap-2">
              <div className="text-xs uppercase text-muted-foreground">Unified strategy intent queue</div>
              <Pill label={`${formatCompact(intents.length)} rows`} tone={intents.length ? statusTone.wired : "border-border bg-muted/20 text-muted-foreground"} />
            </div>
            <div className="grid gap-2 md:grid-cols-2">
              {intents.length ? intents.slice(0, 6).map((intent) => {
                const blockers = Array.isArray(intent.blockers) ? intent.blockers.map(String).filter(Boolean) : [];
                return (
                  <div key={String(intent.intent_id || intent.route_key)} className="rounded-md border border-border/40 bg-black/20 px-3 py-2 text-xs">
                    <div className="flex items-center justify-between gap-2">
                      <span className="truncate font-medium">{String(intent.symbol || intent.route_key || "intent")}</span>
                      <Pill label={String(intent.side || "HOLD")} tone={intent.three_p_floor_passed && !blockers.length ? statusTone.wired : statusTone.orphaned} />
                    </div>
                    <div className="mt-1 truncate text-muted-foreground">{String(intent.worker_id || "worker")} / {String(intent.route_key || "")}</div>
                    <div className="mt-2 grid grid-cols-2 gap-1 text-[11px] text-muted-foreground">
                      <span>net {Number(intent.expected_net_revenue ?? 0).toFixed(5)}</span>
                      <span>confidence {Math.round(asNumber(intent.confidence) * 100)}%</span>
                      <span>3p {intent.three_p_floor_passed ? "pass" : "held"}</span>
                      <span>{intent.requires_unified_executor ? "unified executor" : "attention"}</span>
                    </div>
                    {blockers.length ? (
                      <div className="mt-2 flex flex-wrap gap-1">
                        {blockers.slice(0, 3).map((blocker) => (
                          <Pill key={blocker} label={blocker.replace(/_/g, " ")} tone={statusTone.security_blocker} />
                        ))}
                      </div>
                    ) : null}
                  </div>
                );
              }) : (
                <div className="rounded-md border border-border/40 bg-muted/10 p-4 text-sm text-muted-foreground">
                  No strategy intents have reached the shared queue in the current artifact.
                </div>
              )}
            </div>
          </div>

          <div className="space-y-2">
            <div className="text-xs uppercase text-muted-foreground">Recent API leases</div>
            <div className="grid gap-2">
              {leases.length ? leases.slice(0, 6).map((lease) => (
                <div key={String(lease.lease_id || lease.request_id)} className="rounded-md border border-border/40 bg-black/20 px-3 py-2 text-xs">
                  <div className="flex items-center justify-between gap-2">
                    <span className="truncate font-medium">{String(lease.worker_id || "worker")}</span>
                    <Pill label={String(lease.status || "pending")} tone={lease.status === "granted" ? statusTone.wired : statusTone.orphaned} />
                  </div>
                  <div className="mt-1 truncate text-muted-foreground">
                    {String(lease.venue || "venue")} / {String(lease.operation_type || "operation")} / {String(lease.reason || "lease")}
                  </div>
                  <div className="mt-1 truncate text-muted-foreground">remaining {formatCompact(lease.rate_remaining)} / idempotency {String(lease.idempotency_key || "")}</div>
                </div>
              )) : (
                <div className="rounded-md border border-border/40 bg-muted/10 p-4 text-sm text-muted-foreground">
                  No request leases have been recorded yet.
                </div>
              )}
            </div>
          </div>
        </div>

        {unity?.manual_boundaries?.length ? (
          <div className="flex flex-wrap gap-1">
            {unity.manual_boundaries.slice(0, 5).map((boundary) => (
              <Pill key={boundary} label={boundary} tone="border-border bg-muted/20 text-muted-foreground" />
            ))}
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}

function LiveSignalFabricPanel({
  fabric,
  stress,
  audit,
}: {
  fabric: LiveTradeSignalFabric | null;
  stress: LiveTradeSignalFabricStressAudit | null;
  audit: LiveGoalTradeAudit | null;
}) {
  const proofSnapshot = asRecord(audit?.live_trade_signal_fabric_proof?.snapshot);
  const proof = audit?.live_trade_signal_fabric_proof || {};
  const stressProof = audit?.live_trade_signal_fabric_stress_proof || {};
  const stressSnapshot = asRecord(stressProof.snapshot);
  const stressSource = stress || (Object.keys(stressSnapshot).length ? (stressSnapshot as LiveTradeSignalFabricStressAudit) : null);
  const source = fabric || (Object.keys(proofSnapshot).length ? (proofSnapshot as LiveTradeSignalFabric) : null);
  const summary = source?.summary || {};
  const stressSummary = stressSource?.summary || {};
  const thoughtbus = asRecord(source?.thoughtbus_proof);
  const mycelium = asRecord(source?.mycelium_proof);
  const traces = asRecordArray(source?.active_traces);
  const stressRows = asRecordArray(stressSource?.trace_certification_rows);
  const burnDownRows = asRecordArray(stressSource?.burn_down_rows);
  const producerRepairRows = asRecordArray(stressSource?.producer_repair_rows);
  const producerWiringRows = asRecordArray(stressSource?.producer_wiring_rows);
  const publisherHeartbeatRows = asRecordArray(stressSource?.publisher_heartbeat_rows);
  const nextLiveTraceRequirements = asRecordArray(stressSource?.next_live_trace_requirements);
  const freshCapitalTraceCandidate = asRecord(stressSource?.fresh_capital_trace_candidate);
  const rateBudgetCertificationRows = asRecordArray(stressSource?.rate_budget_certification_rows);
  const recoveredBrokerTruthRows = asRecordArray(stressSource?.recovered_broker_truth_rows);
  const recoveredTraceRows = asRecordArray(stressSource?.recovered_trace_rows);
  const publisherGapRows = asRecordArray(stressSource?.publisher_gap_rows);
  const apiBudgetGapRows = asRecordArray(stressSource?.api_budget_gap_rows);
  const brokerGapRows = asRecordArray(stressSource?.broker_requirement_gap_rows);
  const sessionScope = asRecord(stressSummary.session_scope || stressSource?.session_scope);
  const speedProof = asRecord(stressSource?.a_to_b_gain_speed_proof);
  const speedRows = asRecordArray(stressSource?.speed_trace_rows);
  const speedLatencyRows = asRecordArray(stressSource?.speed_latency_rows);
  const speedMissingRows = asRecordArray(stressSource?.speed_missing_phase_rows);
  const speedRepeatRows = asRecordArray(stressSource?.speed_repeat_cycle_rows);
  const repairRows = asRecordArray(stressSource?.next_repair_actions);
  const broken = asRecordArray(source?.broken_chains);
  const ratePressure = asRecordArray(source?.rate_pressure);
  const phases = Object.entries(source?.phase_counts || {});
  const blockers = [...(((proof.blockers || []) as string[]).filter(Boolean)), ...(((stressSource?.blockers || stressProof.blockers || []) as string[]).filter(Boolean))];
  const active = Boolean(summary.thoughtbus_receiving && summary.mycelium_receiving && !summary.broken_trace_count && !summary.api_rate_pressure_count && !stressSummary.broker_requirement_gap_count && !stressSummary.rate_budget_missing_count);
  const statusLabel = String(source?.status || proof.status || proof.state || "signal fabric pending").replace(/_/g, " ");
  const stressStatusLabel = String(stressSource?.status || stressProof.status || stressProof.state || "stress pending").replace(/_/g, " ");

  return (
    <Card className="border-success/30 bg-success/5">
      <CardHeader className="pb-3">
        <CardTitle className="flex flex-wrap items-center justify-between gap-2 text-base">
          <span className="flex items-center gap-2">
            <Brain className="h-4 w-4 text-success" />
            Live Signal Fabric
          </span>
          <div className="flex flex-wrap gap-1">
            <Pill label={statusLabel} tone={active ? statusTone.wired : statusTone.orphaned} />
            <Pill label={summary.thoughtbus_receiving ? "ThoughtBus receiving" : "ThoughtBus attention"} tone={summary.thoughtbus_receiving ? statusTone.wired : statusTone.orphaned} />
            <Pill label={summary.mycelium_receiving ? "Mycelium receiving" : "Mycelium attention"} tone={summary.mycelium_receiving ? statusTone.wired : statusTone.orphaned} />
            <Pill label="/aureon_live_trade_signal_fabric.json" tone="border-primary/30 bg-primary/10 text-primary" />
            <Pill label="/aureon_live_trade_signal_fabric_stress_audit.json" tone="border-primary/30 bg-primary/10 text-primary" />
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-5">
          {[
            ["events", summary.event_count],
            ["active traces", summary.active_trace_count],
            ["complete traces", summary.complete_trace_count],
            ["broken chains", summary.broken_trace_count],
            ["submitted", summary.live_order_submitted_count],
            ["broker ack", summary.broker_ack_count],
            ["open positions", summary.position_open_count],
            ["outcomes", summary.outcome_recorded_count],
            ["p95 latency", `${formatCompact(summary.p95_phase_latency_ms)} ms`],
            ["rate pressure", summary.api_rate_pressure_count],
            ["stress", stressStatusLabel],
            ["certified traces", `${formatCompact(stressSummary.certified_trace_count)}/${formatCompact(stressSummary.trace_count)}`],
            ["broker gaps", stressSummary.broker_requirement_gap_count],
            ["rate gaps", stressSummary.rate_budget_missing_count],
            ["stale traces", stressSummary.stale_trace_count],
            ["burn-down", stressSummary.burn_down_ready ? "ready" : "attention"],
            ["chain state", stressSummary.chain_certification_state || stressSource?.chain_certification_state || "pending"],
            ["Capital A-to-B", stressSummary.capital_a_to_b_ready || stressSource?.capital_a_to_b_ready ? "ready" : "not ready"],
            ["publisher gaps", stressSummary.publisher_gap_count],
            ["producer repairs", stressSummary.producer_repair_row_count],
            ["recovered traces", stressSummary.recovered_trace_count],
            ["recovered broker", stressSummary.recovered_broker_truth_count],
            ["rate certified", `${formatCompact(stressSummary.rate_budget_certified_count)}/${formatCompact(asNumber(stressSummary.rate_budget_certified_count) + asNumber(stressSummary.rate_budget_uncertified_count))}`],
            ["external leaks", stressSummary.external_live_route_leak_count],
            ["Capital chains", stressSummary.complete_capital_chain_count],
              ["producer state", stressSummary.producer_burndown_state || stressSource?.producer_burndown_state || "pending"],
              ["wired producers", stressSummary.producer_wired_count],
              ["silent producers", stressSummary.producer_silent_count],
              ["rate-missing producers", stressSummary.producer_rate_missing_count],
              ["publisher owner", stressSummary.publisher_owner || "pending"],
              ["dedupe applied", stressSummary.dedupe_applied ? "yes" : "no"],
              ["dedupe count", stressSummary.dedupe_applied_count],
              ["session traces", asNumber(sessionScope.trace_count)],
              ["session broken", stressSummary.session_broken_trace_count || asNumber(stressSource?.session_broken_trace_count)],
              ["session rate gaps", stressSummary.session_api_budget_gap_count || asNumber(stressSource?.session_api_budget_gap_count)],
              ["speed scope", stressSummary.speed_scope || speedProof.scope || "pending"],
              ["A-to-open p50", stressSummary.speed_a_to_b_p50_ms != null ? `${formatCompact(stressSummary.speed_a_to_b_p50_ms)} ms` : "waiting"],
              ["A-to-open p95", stressSummary.speed_a_to_b_p95_ms != null ? `${formatCompact(stressSummary.speed_a_to_b_p95_ms)} ms` : "waiting"],
              ["A-to-gain p50", stressSummary.speed_a_to_gain_p50_ms != null ? `${formatCompact(stressSummary.speed_a_to_gain_p50_ms)} ms` : "waiting"],
              ["gain traces", stressSummary.speed_positive_gain_count],
              ["repeat p50", stressSummary.speed_repeat_cycle_p50_ms != null ? `${formatCompact(stressSummary.speed_repeat_cycle_p50_ms)} ms` : "waiting"],
            ].map(([label, value]) => (
            <div key={String(label)} className="rounded-md border border-border/40 bg-black/20 p-3">
              <div className="text-[11px] uppercase text-muted-foreground">{String(label)}</div>
              <div className="mt-1 font-mono text-sm font-semibold text-success">
                {typeof value === "number" ? formatCompact(value) : String(value ?? "0")}
              </div>
            </div>
          ))}
        </div>

        <div className="rounded-md border border-primary/20 bg-black/20 p-3">
          <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
            <div>
              <div className="text-xs uppercase text-muted-foreground">A-to-B Gain Speed</div>
              <div className="mt-1 text-sm text-primary">
                {String(stressSummary.speed_current_answer || speedProof.answer || "Waiting for signal-to-gain timing evidence.")}
              </div>
            </div>
            <div className="flex flex-wrap gap-1">
              <Pill label={String(stressSummary.speed_latest_state || speedProof.latest_state || "speed pending").replace(/_/g, " ")} tone={asNumber(stressSummary.speed_positive_gain_count) ? statusTone.wired : statusTone.orphaned} />
              <Pill label={stressSummary.speed_real_data_only_mode || speedProof.real_data_only ? "real data only" : "fabric evidence"} tone="border-primary/30 bg-primary/10 text-primary" />
              <Pill label="no direct mutation" tone={statusTone.wired} />
            </div>
          </div>
          <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-6">
            {[
              ["A-to-open fastest", stressSummary.speed_a_to_b_fastest_ms != null ? `${formatCompact(stressSummary.speed_a_to_b_fastest_ms)} ms` : "waiting"],
              ["A-to-open p50", stressSummary.speed_a_to_b_p50_ms != null ? `${formatCompact(stressSummary.speed_a_to_b_p50_ms)} ms` : "waiting"],
              ["A-to-open p95", stressSummary.speed_a_to_b_p95_ms != null ? `${formatCompact(stressSummary.speed_a_to_b_p95_ms)} ms` : "waiting"],
              ["A-to-gain fastest", stressSummary.speed_a_to_gain_fastest_ms != null ? `${formatCompact(stressSummary.speed_a_to_gain_fastest_ms)} ms` : "waiting"],
              ["A-to-gain p50", stressSummary.speed_a_to_gain_p50_ms != null ? `${formatCompact(stressSummary.speed_a_to_gain_p50_ms)} ms` : "waiting"],
              ["repeat p50", stressSummary.speed_repeat_cycle_p50_ms != null ? `${formatCompact(stressSummary.speed_repeat_cycle_p50_ms)} ms` : "waiting"],
            ].map(([label, value]) => (
              <div key={String(label)} className="rounded-md border border-border/40 bg-muted/10 px-3 py-2 text-xs">
                <div className="uppercase text-muted-foreground">{String(label)}</div>
                <div className="mt-1 font-mono text-primary">{String(value ?? "waiting")}</div>
              </div>
            ))}
          </div>
          <div className="mt-3 grid gap-2 xl:grid-cols-3">
            <div className="rounded-md border border-border/40 bg-muted/10 p-3 text-xs">
              <div className="mb-2 flex items-center justify-between gap-2">
                <span className="uppercase text-muted-foreground">Fastest traces</span>
                <Pill label={`${formatCompact(speedRows.length)} traces`} tone={speedRows.length ? statusTone.wired : statusTone.orphaned} />
              </div>
              {speedRows.length ? speedRows.slice(0, 4).map((row, index) => (
                <div key={`${String(row.trace_id || "speed")}-${index}`} className="mt-2 border-t border-border/30 pt-2">
                  <div className="flex items-center justify-between gap-2">
                    <span className="truncate font-medium">{String(row.symbol || row.route_key || "trace")}</span>
                    <span className={row.positive_gain_recorded ? "font-mono text-success" : "font-mono text-warning"}>{String(row.speed_state || "waiting").replace(/_/g, " ")}</span>
                  </div>
                  <div className="mt-1 grid grid-cols-2 gap-1 text-[11px] text-muted-foreground">
                    <span>A-open {row.a_to_b_ms != null ? `${formatCompact(row.a_to_b_ms)}ms` : "waiting"}</span>
                    <span>A-gain {row.a_to_gain_ms != null ? `${formatCompact(row.a_to_gain_ms)}ms` : "waiting"}</span>
                    <span>latest {String(row.latest_phase || "pending").replace(/_/g, " ")}</span>
                    <span>P/L {String(row.net_pnl ?? "pending")}</span>
                  </div>
                </div>
              )) : <div className="text-muted-foreground">No speed trace rows are published yet.</div>}
            </div>
            <div className="rounded-md border border-border/40 bg-muted/10 p-3 text-xs">
              <div className="mb-2 flex items-center justify-between gap-2">
                <span className="uppercase text-muted-foreground">Slowest phase pairs</span>
                <Pill label={`${formatCompact(speedLatencyRows.length)} pairs`} tone={speedLatencyRows.length ? statusTone.wired : statusTone.orphaned} />
              </div>
              {speedLatencyRows.length ? speedLatencyRows.slice(0, 4).map((row, index) => (
                <div key={`${String(row.phase_pair || "pair")}-${index}`} className="mt-2 border-t border-border/30 pt-2">
                  <div className="truncate font-medium">{String(row.phase_pair || "phase pair").replace(/_/g, " ")}</div>
                  <div className="mt-1 grid grid-cols-3 gap-1 text-[11px] text-muted-foreground">
                    <span>p50 {formatCompact(row.p50_ms)}ms</span>
                    <span>p95 {formatCompact(row.p95_ms)}ms</span>
                    <span>n {formatCompact(row.sample_count)}</span>
                  </div>
                </div>
              )) : <div className="text-muted-foreground">No phase-pair timing is complete yet.</div>}
            </div>
            <div className="rounded-md border border-border/40 bg-muted/10 p-3 text-xs">
              <div className="mb-2 flex items-center justify-between gap-2">
                <span className="uppercase text-muted-foreground">Waiting for speed proof</span>
                <Pill label={`${formatCompact(speedMissingRows.length)} rows`} tone={speedMissingRows.length ? statusTone.orphaned : statusTone.wired} />
              </div>
              {speedMissingRows.length ? speedMissingRows.slice(0, 4).map((row, index) => {
                const missing = Array.isArray(row.missing_speed_phases) ? row.missing_speed_phases.map(String).filter(Boolean) : [];
                return (
                  <div key={`${String(row.trace_id || "missing")}-${index}`} className="mt-2 border-t border-border/30 pt-2">
                    <div className="truncate font-medium">{String(row.symbol || row.route_key || "trace")}</div>
                    <div className="mt-1 truncate text-muted-foreground">{missing.map((item) => item.replace(/_/g, " ")).join(", ") || "speed proof pending"}</div>
                  </div>
                );
              }) : <div className="text-muted-foreground">Current speed scope has no missing speed rows.</div>}
              {speedRepeatRows.length ? (
                <div className="mt-3 border-t border-border/30 pt-2 text-[11px] text-muted-foreground">
                  repeat-cycle rows {formatCompact(speedRepeatRows.length)}
                </div>
              ) : null}
            </div>
          </div>
        </div>

        <div className="rounded-md border border-success/20 bg-black/20 p-3">
          <div className="mb-2 flex items-center justify-between gap-2">
            <div className="text-xs uppercase text-muted-foreground">Stress certification</div>
            <Pill label={stressStatusLabel} tone={stressSummary.certified_trace_count && !stressSummary.broker_requirement_gap_count && !stressSummary.rate_budget_missing_count ? statusTone.wired : statusTone.orphaned} />
          </div>
          <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-4">
            {[
              ["missing phases", stressSummary.missing_required_phase_count],
              ["stable ID gaps", stressSummary.stable_id_gap_count],
              ["bus deliveries", stressSummary.bus_delivery_count],
              ["mycelium deliveries", stressSummary.mycelium_delivery_count],
            ].map(([label, value]) => (
              <div key={String(label)} className="rounded-md border border-border/40 bg-muted/10 px-3 py-2 text-xs">
                <div className="uppercase text-muted-foreground">{String(label)}</div>
                <div className="mt-1 font-mono text-success">{formatCompact(value as number)}</div>
              </div>
            ))}
          </div>
          {stressRows.length ? (
            <div className="mt-3 grid gap-2 md:grid-cols-2">
              {stressRows.slice(0, 4).map((row) => {
                const rowBlockers = Array.isArray(row.blockers) ? row.blockers.map(String).filter(Boolean) : [];
                return (
                  <div key={String(row.trace_id || row.lifecycle_id)} className="rounded-md border border-border/40 bg-muted/10 px-3 py-2 text-xs">
                    <div className="flex items-center justify-between gap-2">
                      <span className="truncate font-medium">{String(row.symbol || row.route_key || "stress trace")}</span>
                      <Pill label={String(row.trace_health || row.latest_phase || "pending").replace(/_/g, " ")} tone={rowBlockers.length ? statusTone.orphaned : statusTone.wired} />
                    </div>
                    <div className="mt-1 truncate font-mono text-[11px] text-muted-foreground">{String(row.trace_id || "")}</div>
                    <div className="mt-2 grid grid-cols-2 gap-1 text-[11px] text-muted-foreground">
                      <span>next {String(row.next_required_phase || "complete")}</span>
                      <span>broker {String(row.last_broker_proof || "pending")}</span>
                      <span>max latency {formatCompact(row.max_phase_latency_ms)}ms</span>
                      <span>P/L {String(row.last_net_pnl ?? "pending")}</span>
                    </div>
                    {rowBlockers.length ? (
                      <div className="mt-2 flex flex-wrap gap-1">
                        {rowBlockers.slice(0, 5).map((blocker) => (
                          <Pill key={blocker} label={blocker.replace(/_/g, " ")} tone={statusTone.security_blocker} />
                        ))}
                      </div>
                    ) : null}
                  </div>
                );
              })}
            </div>
          ) : null}
        </div>

        <div className="rounded-md border border-warning/20 bg-black/20 p-3">
          <div className="mb-2 flex items-center justify-between gap-2">
            <div className="text-xs uppercase text-muted-foreground">Burn-down action rows</div>
            <div className="flex flex-wrap gap-1">
              <Pill label={stressSummary.no_direct_broker_mutation ? "no direct broker mutation" : "mutation proof attention"} tone={stressSummary.no_direct_broker_mutation ? statusTone.wired : statusTone.security_blocker} />
              <Pill label={stressSummary.executor_gate_respected ? "executor gate respected" : "executor gate attention"} tone={stressSummary.executor_gate_respected ? statusTone.wired : statusTone.security_blocker} />
            </div>
          </div>
          <div className="grid gap-2 md:grid-cols-2">
            {burnDownRows.length ? burnDownRows.slice(0, 6).map((row) => {
              const missing = Array.isArray(row.missing_required_phases) ? row.missing_required_phases.map(String).filter(Boolean) : [];
              const ids = Array.isArray(row.stable_id_gaps) ? row.stable_id_gaps.map(String).filter(Boolean) : [];
              const rate = Array.isArray(row.rate_budget_missing_phases) ? row.rate_budget_missing_phases.map(String).filter(Boolean) : [];
              const broker = Array.isArray(row.broker_requirement_gaps) ? row.broker_requirement_gaps.map(String).filter(Boolean) : [];
              const gaps = [...missing, ...ids, ...rate, ...broker];
              return (
                <div key={String(row.trace_id || row.route_key || row.latest_phase)} className="rounded-md border border-border/40 bg-muted/10 px-3 py-2 text-xs">
                  <div className="flex items-center justify-between gap-2">
                    <span className="truncate font-medium">{String(row.symbol || row.route_key || "trade flow")}</span>
                    <Pill label={String(row.classification || "attention").replace(/_/g, " ")} tone={row.classification === "complete_chain" ? statusTone.wired : statusTone.orphaned} />
                  </div>
                  <div className="mt-1 truncate text-muted-foreground">{String(row.next_repair_action || "publish next phase proof")}</div>
                  <div className="mt-2 grid grid-cols-2 gap-1 text-[11px] text-muted-foreground">
                    <span>producer {String(row.next_producer_to_fix || "pending")}</span>
                    <span>next {String(row.next_required_phase || "complete")}</span>
                    <span>latest {String(row.latest_phase || "pending")}</span>
                    <span>{row.blocked_before_broker_mutation ? "blocked before broker" : "downstream proof"}</span>
                  </div>
                  {gaps.length ? (
                    <div className="mt-2 flex flex-wrap gap-1">
                      {gaps.slice(0, 5).map((gap) => (
                        <Pill key={gap} label={gap.replace(/_/g, " ")} tone={statusTone.security_blocker} />
                      ))}
                    </div>
                  ) : null}
                </div>
              );
            }) : (
              <div className="rounded-md border border-border/40 bg-muted/10 p-4 text-sm text-muted-foreground">
                No burn-down gaps are visible in the current fabric stress artifact.
              </div>
            )}
          </div>

          <div className="mt-3 grid gap-2 md:grid-cols-2 xl:grid-cols-4">
            {[
              ["recovered context", recoveredTraceRows.length],
              ["producer repairs", producerRepairRows.length || publisherGapRows.length],
              ["rate proof rows", rateBudgetCertificationRows.length],
              ["API budget gaps", apiBudgetGapRows.length],
              ["broker proof gaps", brokerGapRows.length],
            ].map(([label, value]) => (
              <div key={String(label)} className="rounded-md border border-border/40 bg-muted/10 px-3 py-2 text-xs">
                <div className="uppercase text-muted-foreground">{String(label)}</div>
                <div className="mt-1 font-mono text-warning">{formatCompact(value as number)}</div>
              </div>
            ))}
          </div>

          <div className="mt-3 grid gap-2 md:grid-cols-3">
            {producerWiringRows.length ? (
              <div className="rounded-md border border-border/40 bg-black/20 p-3 text-xs">
                <div className="mb-2 flex items-center justify-between gap-2">
                  <span className="uppercase text-muted-foreground">Producer wiring</span>
                  <Pill label={String(stressSummary.producer_burndown_state || stressSource?.producer_burndown_state || "pending").replace(/_/g, " ")} tone={stressSummary.capital_a_to_b_ready ? statusTone.wired : statusTone.orphaned} />
                </div>
                {producerWiringRows.slice(0, 5).map((row, index) => (
                  <div key={`${String(row.phase || "producer")}-${index}`} className="mt-2 border-t border-border/30 pt-2">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-medium">{String(row.phase || "phase").replace(/_/g, " ")}</span>
                      <span className={row.state === "producer_wired" || row.state === "complete_a_to_b" ? "font-mono text-success" : "font-mono text-warning"}>{String(row.state || "pending").replace(/_/g, " ")}</span>
                    </div>
                    <div className="truncate text-muted-foreground">{String(row.producer || "producer pending")}</div>
                  </div>
                ))}
              </div>
            ) : null}
            {producerRepairRows.length ? (
              <div className="rounded-md border border-border/40 bg-black/20 p-3 text-xs">
                <div className="mb-2 flex items-center justify-between gap-2">
                  <span className="uppercase text-muted-foreground">Producer repair</span>
                  <Pill label={`${formatCompact(producerRepairRows.length)} rows`} tone={statusTone.orphaned} />
                </div>
                {producerRepairRows.slice(0, 4).map((row, index) => (
                  <div key={`${String(row.missing_phase || row.missing_id || "producer")}-${index}`} className="mt-2 border-t border-border/30 pt-2">
                    <div className="font-medium">{String(row.missing_phase || row.missing_id || "missing proof").replace(/_/g, " ")}</div>
                    <div className="truncate text-muted-foreground">{String(row.next_producer_to_fix || row.missing_publisher || "producer pending")}</div>
                  </div>
                ))}
              </div>
            ) : null}
            {nextLiveTraceRequirements.length ? (
              <div className="rounded-md border border-border/40 bg-black/20 p-3 text-xs">
                <div className="mb-2 flex items-center justify-between gap-2">
                  <span className="uppercase text-muted-foreground">Next live trace requirements</span>
                  <Pill label={`${formatCompact(nextLiveTraceRequirements.length)} requirements`} tone={statusTone.orphaned} />
                </div>
                {nextLiveTraceRequirements.slice(0, 4).map((row, index) => {
                  const missing = Array.isArray(row.missing_field_set) ? row.missing_field_set.map(String).filter(Boolean) : [];
                  return (
                    <div key={`${String(row.phase || row.requirement || "requirement")}-${index}`} className="mt-2 border-t border-border/30 pt-2">
                      <div className="font-medium">{String(row.phase || row.requirement || "proof").replace(/_/g, " ")}</div>
                      <div className="truncate text-muted-foreground">{String(row.producer || "producer pending")} / {missing.slice(0, 2).join(", ") || "proof required"}</div>
                    </div>
                  );
                })}
              </div>
            ) : null}
            {Object.keys(freshCapitalTraceCandidate).length ? (
              <div className="rounded-md border border-border/40 bg-black/20 p-3 text-xs">
                <div className="mb-2 flex items-center justify-between gap-2">
                  <span className="uppercase text-muted-foreground">Fresh Capital trace</span>
                  <Pill label={String(freshCapitalTraceCandidate.state || "pending").replace(/_/g, " ")} tone={freshCapitalTraceCandidate.capital_a_to_b_ready ? statusTone.wired : statusTone.orphaned} />
                </div>
                <div className="truncate text-muted-foreground">route {String(freshCapitalTraceCandidate.route_key || "waiting")}</div>
                <div className="mt-1 truncate text-muted-foreground">next {String(freshCapitalTraceCandidate.next_required_phase || "signal_generated").replace(/_/g, " ")}</div>
              </div>
            ) : null}
            {publisherHeartbeatRows.length ? (
              <div className="rounded-md border border-border/40 bg-black/20 p-3 text-xs">
                <div className="mb-2 flex items-center justify-between gap-2">
                  <span className="uppercase text-muted-foreground">Publisher heartbeats</span>
                  <Pill label={`${formatCompact(publisherHeartbeatRows.length)} publishers`} tone={statusTone.wired} />
                </div>
                {publisherHeartbeatRows.slice(0, 4).map((row, index) => (
                  <div key={`${String(row.source_system || "source")}-${index}`} className="mt-2 border-t border-border/30 pt-2">
                    <div className="font-medium">{String(row.source_system || "publisher")}</div>
                    <div className="truncate text-muted-foreground">{String(row.latest_phase || "phase pending")} / {formatCompact(row.event_count)}</div>
                  </div>
                ))}
              </div>
            ) : null}
            {rateBudgetCertificationRows.length ? (
              <div className="rounded-md border border-border/40 bg-black/20 p-3 text-xs">
                <div className="mb-2 flex items-center justify-between gap-2">
                  <span className="uppercase text-muted-foreground">Rate-budget proof</span>
                  <Pill label={`${formatCompact(stressSummary.rate_budget_certified_count)} certified`} tone={stressSummary.rate_budget_uncertified_count ? statusTone.orphaned : statusTone.wired} />
                </div>
                {rateBudgetCertificationRows.slice(0, 4).map((row, index) => {
                  const missingTags = Array.isArray(row.missing_api_budget_tags) ? row.missing_api_budget_tags.map(String).filter(Boolean) : [];
                  return (
                    <div key={`${String(row.phase || "rate")}-${index}`} className="mt-2 border-t border-border/30 pt-2">
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-medium">{String(row.phase || "phase").replace(/_/g, " ")}</span>
                        <span className={row.rate_budget_certified ? "font-mono text-success" : "font-mono text-warning"}>{row.rate_budget_certified ? "certified" : "missing"}</span>
                      </div>
                      <div className="truncate text-muted-foreground">{missingTags.length ? missingTags.slice(0, 2).join(", ") : String(row.api_budget_source || "proof present")}</div>
                    </div>
                  );
                })}
              </div>
            ) : null}
            {recoveredBrokerTruthRows.length ? (
              <div className="rounded-md border border-border/40 bg-black/20 p-3 text-xs">
                <div className="mb-2 flex items-center justify-between gap-2">
                  <span className="uppercase text-muted-foreground">Recovered broker truth</span>
                  <Pill label={`${formatCompact(recoveredBrokerTruthRows.length)} recovered`} tone={statusTone.orphaned} />
                </div>
                {recoveredBrokerTruthRows.slice(0, 4).map((row, index) => (
                  <div key={`${String(row.trace_id || "recovered")}-${index}`} className="mt-2 border-t border-border/30 pt-2">
                    <div className="font-medium">{String(row.symbol || row.route_key || "broker proof")}</div>
                    <div className="truncate text-muted-foreground">{String(row.last_broker_proof || "broker proof pending")} / {String(row.recovered_context_status || "recovered")}</div>
                  </div>
                ))}
              </div>
            ) : null}
          </div>

          {repairRows.length ? (
            <div className="mt-3 grid gap-2 md:grid-cols-2">
              {repairRows.slice(0, 4).map((row, index) => (
                <div key={`${String(row.classification || "repair")}-${index}`} className="rounded-md border border-border/40 bg-black/20 px-3 py-2 text-xs">
                  <div className="flex items-center justify-between gap-2">
                    <span className="truncate font-medium">{String(row.next_producer_to_fix || "producer pending")}</span>
                    <span className="font-mono text-warning">{String(row.next_required_phase || "next proof")}</span>
                  </div>
                  <div className="mt-1 text-muted-foreground">{String(row.action || "Attach missing proof to the fabric event.")}</div>
                </div>
              ))}
            </div>
          ) : null}
        </div>

        <div className="grid gap-3 xl:grid-cols-[1.15fr_0.85fr]">
          <div className="space-y-2">
            <div className="flex items-center justify-between gap-2">
              <div className="text-xs uppercase text-muted-foreground">A-to-B traces</div>
              <Pill label="existing executor path" tone="border-success/30 bg-success/10 text-success" />
            </div>
            <div className="grid gap-2 md:grid-cols-2">
              {traces.length ? traces.slice(0, 8).map((trace) => {
                const missing = Array.isArray(trace.missing_phases) ? trace.missing_phases.map(String) : [];
                const phasesForTrace = Array.isArray(trace.phases) ? trace.phases.map(String) : [];
                return (
                  <div key={String(trace.trace_id || trace.lifecycle_id)} className="rounded-md border border-border/40 bg-muted/10 px-3 py-2 text-xs">
                    <div className="flex items-center justify-between gap-2">
                      <span className="truncate font-medium">{String(trace.symbol || trace.route_key || "trade trace")}</span>
                      <Pill label={String(trace.latest_phase || "waiting").replace(/_/g, " ")} tone={missing.length ? statusTone.orphaned : statusTone.wired} />
                    </div>
                    <div className="mt-1 truncate font-mono text-[11px] text-muted-foreground">{String(trace.trace_id || "")}</div>
                    <div className="mt-2 grid grid-cols-2 gap-1 text-[11px] text-muted-foreground">
                      <span>route {String(trace.route_key || "pending")}</span>
                      <span>broker {String(trace.last_broker_proof || "pending")}</span>
                      <span>latency {formatCompact(trace.duration_ms)}ms</span>
                      <span>P/L {String(trace.last_net_pnl ?? "pending")}</span>
                    </div>
                    <div className="mt-2 flex flex-wrap gap-1">
                      {(missing.length ? missing : phasesForTrace.slice(-5)).slice(0, 6).map((phase) => (
                        <Pill key={phase} label={phase.replace(/_/g, " ")} tone={missing.length ? statusTone.orphaned : "border-success/30 bg-success/10 text-success"} />
                      ))}
                    </div>
                  </div>
                );
              }) : (
                <div className="rounded-md border border-border/40 bg-muted/10 p-4 text-sm text-muted-foreground">
                  No live trade-flow trace has been published yet.
                </div>
              )}
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between gap-2">
              <div className="text-xs uppercase text-muted-foreground">Bus and mycelium proof</div>
              <Pill label="active organism visibility" tone="border-success/30 bg-success/10 text-success" />
            </div>
            <div className="grid gap-2">
              {[
                ["ThoughtBus", thoughtbus.receiving ? "receiving" : thoughtbus.latest_reason || "attention"],
                ["Thoughts", formatCompact(thoughtbus.published_count)],
                ["Mycelium", mycelium.receiving ? "receiving" : mycelium.latest_reason || "attention"],
                ["Ingested", formatCompact(mycelium.ingested_count)],
                ["Phase types", formatCompact(phases.length)],
                ["Broken chains", formatCompact(broken.length)],
                ["Rate pressure", formatCompact(ratePressure.length)],
                ["Source", "/aureon_live_trade_signal_fabric.json"],
              ].map(([label, value]) => (
                <div key={String(label)} className="rounded-md border border-border/40 bg-black/20 px-3 py-2 text-xs">
                  <div className="flex items-center justify-between gap-2">
                    <span className="uppercase text-muted-foreground">{String(label)}</span>
                    <span className="max-w-[12rem] truncate text-right font-mono text-foreground/90">{String(value ?? "0")}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {phases.length ? (
          <div className="flex flex-wrap gap-1">
            {phases.slice(0, 14).map(([phase, count]) => (
              <Pill key={phase} label={`${phase.replace(/_/g, " ")} ${formatCompact(count)}`} tone="border-border bg-muted/20 text-muted-foreground" />
            ))}
          </div>
        ) : null}

        {[...blockers, ...broken.map((item) => String(item.latest_phase || "broken_chain")), ...ratePressure.map((item) => String(item.phase || "rate_pressure"))].filter(Boolean).length ? (
          <div className="flex flex-wrap gap-1">
            {[...blockers, ...broken.map((item) => String(item.latest_phase || "broken_chain")), ...ratePressure.map((item) => String(item.phase || "rate_pressure"))]
              .filter(Boolean)
              .slice(0, 12)
              .map((blocker, index) => (
                <Pill key={`${blocker}-${index}`} label={String(blocker).replace(/_/g, " ")} tone={statusTone.security_blocker} />
              ))}
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}

function SwarmSearchMappingPanel({ audit }: { audit: SwarmSearchMappingStressAudit | null }) {
  const summary = audit?.summary || {};
  const sourceRows = asRecordArray(audit?.source_system_rows);
  const phaseRows = asRecordArray(audit?.phase_rows);
  const captureRows = asRecordArray(audit?.data_capture_rows);
  const keywordRows = asRecordArray(audit?.keyword_search_rows);
  const onlineRows = asRecordArray(audit?.online_research_rows);
  const onlineMotion = asRecord(audit?.online_research_motion_picture);
  const onlinePaper = asRecord(audit?.online_research_paper);
  const codingHandoff = asRecord(audit?.research_coding_handoff);
  const generatedFileRows = asRecordArray(audit?.research_generated_file_rows);
  const metacognition = asRecord(audit?.research_metacognition);
  const metacognitionConceptRows = asRecordArray(audit?.research_metacognition_concept_rows);
  const metacognitionRouteRows = asRecordArray(audit?.research_metacognition_route_rows);
  const metacognitionUnknownRows = asRecordArray(audit?.research_metacognition_unknown_rows);
  const metacognitionActionRows = asRecordArray(audit?.research_metacognition_test_action_rows);
  const browserRows = asRecordArray(audit?.browser_mapping_rows);
  const recentEvents = asRecordArray(audit?.recent_search_events);
  const nextActions = asRecordArray(audit?.next_actions);
  const active = audit?.status === "swarm_search_fabric_active";
  const statusLabel = String(audit?.status || "swarm search pending").replace(/_/g, " ");

  return (
    <Card className="border-primary/30 bg-primary/5">
      <CardHeader className="pb-3">
        <CardTitle className="flex flex-wrap items-center justify-between gap-2 text-base">
          <span className="flex items-center gap-2">
            <Search className="h-4 w-4 text-primary" />
            Swarm Search Fabric
          </span>
          <div className="flex flex-wrap gap-1">
            <Pill label={statusLabel} tone={active ? statusTone.wired : statusTone.orphaned} />
            <Pill label={summary.thoughtbus_receiving ? "ThoughtBus receiving" : "ThoughtBus waiting"} tone={summary.thoughtbus_receiving ? statusTone.wired : statusTone.orphaned} />
            <Pill label={summary.mycelium_receiving ? "Mycelium receiving" : "Mycelium waiting"} tone={summary.mycelium_receiving ? statusTone.wired : statusTone.orphaned} />
            <Pill label={summary.no_synthetic_capture ? "real capture only" : "capture attention"} tone={summary.no_synthetic_capture ? statusTone.wired : statusTone.security_blocker} />
            <Pill label="/aureon_swarm_search_mapping_stress_audit.json" tone="border-primary/30 bg-primary/10 text-primary" />
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-6">
          {[
            ["source systems", `${formatCompact(summary.wired_source_system_count)}/${formatCompact(summary.source_system_count)}`],
            ["browser map", `${formatCompact(summary.browser_mapping_present_count)}/${formatCompact(summary.browser_mapping_count)}`],
            ["capture artifacts", `${formatCompact(summary.data_capture_artifact_present_count)}/${formatCompact(summary.data_capture_artifact_count)}`],
            ["fabric events", summary.fabric_event_count],
            ["keyword scans", summary.keyword_search_active ? "active" : "waiting"],
            ["keyword matches", summary.keyword_match_count],
            ["keyword files", summary.keyword_match_file_count],
            ["research cinema", summary.online_research_cinema_active ? "active" : "waiting"],
            ["online sources", summary.online_research_source_count],
            ["motion frames", summary.online_research_frame_count],
            ["coding files", summary.research_generated_file_count],
            ["metacognition", summary.research_metacognition_active ? "active" : "waiting"],
            ["concepts", `${formatCompact(summary.metacognitive_understood_concept_count)}/${formatCompact(summary.metacognitive_concept_count)}`],
            ["routes", `${formatCompact(summary.metacognitive_ready_route_count)}/${formatCompact(summary.metacognitive_route_count)}`],
            ["phases", `${formatCompact(summary.phase_seen_count)}/${formatCompact(summary.phase_expected_count)}`],
            ["live capture", summary.live_search_capture_active ? "active" : "waiting"],
            ["new trading gate", summary.no_new_trading_gate ? "no" : "attention"],
            ["external mutation", summary.no_external_mutation ? "none" : "attention"],
            ["mode", audit?.mode || "pending"],
          ].map(([label, value]) => (
            <div key={String(label)} className="rounded-md border border-border/40 bg-black/20 p-3">
              <div className="text-[11px] uppercase text-muted-foreground">{String(label)}</div>
              <div className="mt-1 truncate font-mono text-sm font-semibold text-primary">
                {typeof value === "number" ? formatCompact(value) : String(value ?? "0")}
              </div>
            </div>
          ))}
        </div>

        <div className="grid gap-3 xl:grid-cols-[1.05fr_0.95fr]">
          <div className="rounded-md border border-primary/20 bg-black/20 p-3">
            <div className="mb-2 flex items-center justify-between gap-2">
              <div className="text-xs uppercase text-muted-foreground">Search producers</div>
              <Pill label={`${formatCompact(sourceRows.filter((row) => row.wired).length)} wired`} tone={summary.wired_source_system_count === summary.source_system_count ? statusTone.wired : statusTone.orphaned} />
            </div>
            <div className="grid gap-2 md:grid-cols-2">
              {sourceRows.slice(0, 8).map((row) => (
                <div key={String(row.id || row.path)} className="rounded-md border border-border/40 bg-muted/10 px-3 py-2 text-xs">
                  <div className="flex items-center justify-between gap-2">
                    <span className="truncate font-medium">{String(row.label || row.id || "producer")}</span>
                    <Pill label={row.wired ? "wired" : "attention"} tone={row.wired ? statusTone.wired : statusTone.orphaned} />
                  </div>
                  <div className="mt-1 truncate text-muted-foreground">{String(row.role || row.path || "")}</div>
                  <div className="mt-1 font-mono text-[11px] text-muted-foreground">{formatCompact(row.present_symbol_count)}/{formatCompact(row.required_symbol_count)} symbols</div>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-md border border-primary/20 bg-black/20 p-3">
            <div className="mb-2 flex items-center justify-between gap-2">
              <div className="text-xs uppercase text-muted-foreground">A-to-B search phases</div>
              <Pill label={`${formatCompact(summary.phase_seen_count)}/${formatCompact(summary.phase_expected_count)} seen`} tone={summary.phase_seen_count === summary.phase_expected_count ? statusTone.wired : statusTone.orphaned} />
            </div>
            <div className="grid gap-2 md:grid-cols-2">
              {phaseRows.map((row) => (
                <div key={String(row.phase)} className="rounded-md border border-border/40 bg-muted/10 px-3 py-2 text-xs">
                  <div className="flex items-center justify-between gap-2">
                    <span className="truncate font-medium">{String(row.phase || "phase").replace(/_/g, " ")}</span>
                    <Pill label={row.seen ? "seen" : "waiting"} tone={row.seen ? statusTone.wired : statusTone.orphaned} />
                  </div>
                  <div className="mt-1 truncate text-muted-foreground">{String(row.next_producer || "producer pending")}</div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="grid gap-3 xl:grid-cols-2">
          <div className="rounded-md border border-primary/20 bg-black/20 p-3">
            <div className="mb-2 flex items-center justify-between gap-2">
              <div className="text-xs uppercase text-muted-foreground">Online research cinema</div>
              <Pill label={summary.online_research_cinema_active ? "active" : "waiting"} tone={summary.online_research_cinema_active ? statusTone.wired : statusTone.orphaned} />
            </div>
            <div className="mb-2 grid gap-2 sm:grid-cols-2">
              <div className="rounded-md border border-primary/20 bg-primary/5 px-3 py-2 text-xs">
                <div className="truncate text-muted-foreground">topic</div>
                <div className="mt-1 truncate font-mono text-primary">{String(summary.online_research_topic || "none")}</div>
              </div>
              <div className="rounded-md border border-primary/20 bg-primary/5 px-3 py-2 text-xs">
                <div className="truncate text-muted-foreground">paper / motion</div>
                <div className="mt-1 truncate font-mono text-primary">
                  {summary.online_research_paper_created ? "paper" : "no paper"} / {summary.online_research_motion_ready ? "motion" : "no motion"}
                </div>
              </div>
              <div className="rounded-md border border-primary/20 bg-primary/5 px-3 py-2 text-xs">
                <div className="truncate text-muted-foreground">coding handoff</div>
                <div className="mt-1 truncate font-mono text-primary">
                  {summary.research_coding_artifacts_created ? "files ready" : "waiting"}
                </div>
              </div>
              <div className="rounded-md border border-primary/20 bg-primary/5 px-3 py-2 text-xs">
                <div className="truncate text-muted-foreground">test command</div>
                <div className="mt-1 truncate font-mono text-primary">{String(codingHandoff.test_command || "pending")}</div>
              </div>
            </div>
            <div className="grid gap-2 md:grid-cols-2">
              {onlineRows.length ? onlineRows.slice(0, 6).map((row, index) => (
                <div key={`${String(row.url || "online")}-${index}`} className="rounded-md border border-border/40 bg-muted/10 px-3 py-2 text-xs">
                  <div className="flex items-center justify-between gap-2">
                    <span className="truncate font-medium">{String(row.title || row.url || "source")}</span>
                    <Pill label={row.success ? "fetched" : "attention"} tone={row.success ? statusTone.wired : statusTone.orphaned} />
                  </div>
                  <div className="mt-1 truncate text-muted-foreground">{String(row.url || "")}</div>
                  <div className="mt-1 line-clamp-2 text-muted-foreground">{String(row.summary || row.excerpt || "")}</div>
                </div>
              )) : (
                <div className="rounded-md border border-border/40 bg-muted/10 p-4 text-sm text-muted-foreground">
                  No online research cinema packet has been captured yet.
                </div>
              )}
            </div>
            {generatedFileRows.length ? (
              <div className="mt-3 rounded-md border border-primary/20 bg-black/20 p-3">
                <div className="mb-2 text-xs uppercase text-muted-foreground">Generated coding files</div>
                <div className="grid gap-2 md:grid-cols-2">
                  {generatedFileRows.slice(0, 8).map((row, index) => (
                    <div key={`${String(row.path || "file")}-${index}`} className="rounded-md border border-border/40 bg-muted/10 px-3 py-2 text-xs">
                      <div className="flex items-center justify-between gap-2">
                        <span className="truncate font-medium">{String(row.path || "generated file")}</span>
                        <Pill label={row.ok ? "written" : "attention"} tone={row.ok ? statusTone.wired : statusTone.orphaned} />
                      </div>
                      <div className="mt-1 truncate text-muted-foreground">{String(row.authoring_path || "writer")}</div>
                    </div>
                  ))}
                </div>
              </div>
            ) : null}
            <div className="mt-2 flex flex-wrap gap-1">
              <Pill label={String(onlinePaper.path || "paper pending")} tone="border-primary/30 bg-primary/10 text-primary" />
              <Pill label={String(onlineMotion.public_html || "motion pending")} tone="border-primary/30 bg-primary/10 text-primary" />
            </div>
          </div>

          <div className="rounded-md border border-primary/20 bg-black/20 p-3">
            <div className="mb-2 flex items-center justify-between gap-2">
              <div className="text-xs uppercase text-muted-foreground">Metacognitive understanding</div>
              <Pill label={summary.research_metacognition_active ? "active" : "waiting"} tone={summary.research_metacognition_active ? statusTone.wired : statusTone.orphaned} />
            </div>
            <div className="mb-2 grid gap-2 sm:grid-cols-2">
              <div className="rounded-md border border-primary/20 bg-primary/5 px-3 py-2 text-xs">
                <div className="truncate text-muted-foreground">understanding</div>
                <div className="mt-1 truncate font-mono text-primary">
                  {summary.metacognitive_understanding_published ? "published" : "waiting"}
                </div>
              </div>
              <div className="rounded-md border border-primary/20 bg-primary/5 px-3 py-2 text-xs">
                <div className="truncate text-muted-foreground">unknowns / actions</div>
                <div className="mt-1 truncate font-mono text-primary">
                  {formatCompact(summary.metacognitive_unknown_count)} / {formatCompact(summary.metacognitive_test_action_count)}
                </div>
              </div>
            </div>
            <div className="mb-3 line-clamp-3 rounded-md border border-border/40 bg-muted/10 p-3 text-xs text-muted-foreground">
              {String(metacognition.understanding_summary || "No metacognitive research packet has been published yet.")}
            </div>
            <div className="grid gap-2 md:grid-cols-2">
              {metacognitionConceptRows.slice(0, 8).map((row, index) => (
                <div key={`${String(row.concept_id || "concept")}-${index}`} className="rounded-md border border-border/40 bg-muted/10 px-3 py-2 text-xs">
                  <div className="flex items-center justify-between gap-2">
                    <span className="truncate font-medium">{String(row.label || row.concept_id || "concept")}</span>
                    <Pill label={String(row.status || "waiting").replace(/_/g, " ")} tone={row.status === "understood" ? statusTone.wired : statusTone.orphaned} />
                  </div>
                  <div className="mt-1 line-clamp-2 text-muted-foreground">{String(row.meaning || row.route || "")}</div>
                </div>
              ))}
            </div>
            {metacognitionRouteRows.length ? (
              <div className="mt-3 rounded-md border border-border/40 bg-muted/10 p-3">
                <div className="mb-2 text-xs uppercase text-muted-foreground">Organism routes</div>
                <div className="grid gap-2 md:grid-cols-2">
                  {metacognitionRouteRows.slice(0, 8).map((row, index) => (
                    <div key={`${String(row.route_id || "route")}-${index}`} className="rounded-md border border-border/40 bg-black/20 px-3 py-2 text-xs">
                      <div className="flex items-center justify-between gap-2">
                        <span className="truncate font-medium">{String(row.system || row.route_id || "route")}</span>
                        <Pill label={row.ready ? "ready" : "context"} tone={row.ready ? statusTone.wired : statusTone.orphaned} />
                      </div>
                      <div className="mt-1 line-clamp-2 text-muted-foreground">{String(row.relation || row.authority || "")}</div>
                    </div>
                  ))}
                </div>
              </div>
            ) : null}
            <div className="mt-3 flex flex-wrap gap-1">
              {metacognitionUnknownRows.slice(0, 4).map((row, index) => (
                <Pill key={`${String(row.unknown_id || "unknown")}-${index}`} label={String(row.state || row.area || "unknown").replace(/_/g, " ")} tone={statusTone.orphaned} />
              ))}
              {metacognitionActionRows.slice(0, 3).map((row, index) => (
                <Pill key={`${String(row.action_id || "action")}-${index}`} label={String(row.action_id || "test action").replace(/_/g, " ")} tone="border-primary/30 bg-primary/10 text-primary" />
              ))}
            </div>
          </div>
        </div>

        <div className="grid gap-3 xl:grid-cols-4">
          <div className="rounded-md border border-border/40 bg-black/20 p-3">
            <div className="mb-2 text-xs uppercase text-muted-foreground">Data capture artifacts</div>
            <div className="space-y-2">
              {captureRows.slice(0, 8).map((row) => (
                <div key={String(row.path)} className="rounded-md border border-border/40 bg-muted/10 px-3 py-2 text-xs">
                  <div className="flex items-center justify-between gap-2">
                    <span className="truncate font-medium">{String(row.path || "artifact")}</span>
                    <Pill label={row.present ? "present" : "missing"} tone={row.present ? statusTone.wired : statusTone.orphaned} />
                  </div>
                  <div className="mt-1 truncate text-muted-foreground">{String(row.purpose || "")}</div>
                </div>
              ))}
            </div>
          </div>
          <div className="rounded-md border border-border/40 bg-black/20 p-3">
            <div className="mb-2 flex items-center justify-between gap-2">
              <div className="text-xs uppercase text-muted-foreground">Keyword read proof</div>
              <Pill label={summary.keyword_search_active ? "active" : "waiting"} tone={summary.keyword_search_active ? statusTone.wired : statusTone.orphaned} />
            </div>
            <div className="mb-2 rounded-md border border-primary/20 bg-primary/5 px-3 py-2 text-xs">
              <div className="truncate text-muted-foreground">latest query</div>
              <div className="mt-1 truncate font-mono text-primary">{String(summary.latest_keyword_query || "none")}</div>
              <div className="mt-1 text-[11px] text-muted-foreground">
                scanned {formatCompact(summary.keyword_scanned_file_count)} / matches {formatCompact(summary.keyword_match_count)}
              </div>
            </div>
            <div className="space-y-2">
              {keywordRows.length ? keywordRows.slice(0, 6).map((row, index) => (
                <div key={`${String(row.path || "keyword")}-${String(row.line || index)}`} className="rounded-md border border-border/40 bg-muted/10 px-3 py-2 text-xs">
                  <div className="flex items-center justify-between gap-2">
                    <span className="truncate font-medium">{String(row.path || "local file")}</span>
                    <span className="font-mono text-primary">L{formatCompact(row.line)}</span>
                  </div>
                  <div className="mt-1 line-clamp-2 text-muted-foreground">{String(row.snippet || "")}</div>
                </div>
              )) : (
                <div className="rounded-md border border-border/40 bg-muted/10 p-4 text-sm text-muted-foreground">
                  No local keyword scan has been captured yet.
                </div>
              )}
            </div>
          </div>
          <div className="rounded-md border border-border/40 bg-black/20 p-3">
            <div className="mb-2 text-xs uppercase text-muted-foreground">Browser mapping</div>
            <div className="space-y-2">
              {browserRows.map((row) => (
                <div key={String(row.surface)} className="rounded-md border border-border/40 bg-muted/10 px-3 py-2 text-xs">
                  <div className="flex items-center justify-between gap-2">
                    <span className="truncate font-medium">{String(row.surface || "browser surface")}</span>
                    <Pill label={row.present ? "present" : "missing"} tone={row.present ? statusTone.wired : statusTone.orphaned} />
                  </div>
                  <div className="mt-1 truncate text-muted-foreground">{String(row.evidence || "")}</div>
                </div>
              ))}
            </div>
          </div>
          <div className="rounded-md border border-border/40 bg-black/20 p-3">
            <div className="mb-2 text-xs uppercase text-muted-foreground">Recent live search events</div>
            <div className="space-y-2">
              {recentEvents.length ? recentEvents.slice(-6).reverse().map((row, index) => (
                <div key={`${String(row.event_id || row.phase)}-${index}`} className="rounded-md border border-border/40 bg-muted/10 px-3 py-2 text-xs">
                  <div className="flex items-center justify-between gap-2">
                    <span className="truncate font-medium">{String(row.phase || "event").replace(/_/g, " ")}</span>
                    <span className="font-mono text-primary">{formatCompact(row.result_count)}</span>
                  </div>
                  <div className="mt-1 truncate text-muted-foreground">{String(row.source || row.source_system || "source")}</div>
                </div>
              )) : (
                <div className="rounded-md border border-border/40 bg-muted/10 p-4 text-sm text-muted-foreground">
                  No live search event has reached the fabric yet.
                </div>
              )}
            </div>
          </div>
        </div>

        {nextActions.length ? (
          <div className="flex flex-wrap gap-1">
            {nextActions.slice(0, 10).map((row, index) => (
              <Pill key={`${String(row.area || "action")}-${index}`} label={`${String(row.area || "search").replace(/_/g, " ")}: ${String(row.state || "attention").replace(/_/g, " ")}`} tone={statusTone.orphaned} />
            ))}
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}

function CapitalRevenueLogicStressPanel({ audit }: { audit: CapitalRevenueLogicStressAudit | null }) {
  const summary = audit?.summary || {};
  const netRows = asRecordArray(audit?.net_positive_candidates);
  const rejectRows = asRecordArray(audit?.rejected_false_positives);
  const readiness = asRecord(audit?.capital_order_intent_readiness);
  const runtimeGate = asRecord(audit?.runtime_gate_proof);
  const external = asRecord(audit?.external_confirmation_proof);
  const closeFirst = asRecord(audit?.close_first_proof);
  const lifecycle = asRecord(audit?.lifecycle_proof);
  const blockers = ((audit?.blockers || []) as string[]).filter(Boolean);
  const blockerLabels = (value: unknown) => (Array.isArray(value) ? value.map((item) => String(item)).filter(Boolean) : []);
  const certified = audit?.status === "capital_revenue_logic_certified" && blockers.length === 0;
  const statusLabel = String(audit?.status || "revenue logic pending").replace(/_/g, " ");

  return (
    <Card className="border-success/30 bg-success/5">
      <CardHeader className="pb-3">
        <CardTitle className="flex flex-wrap items-center justify-between gap-2 text-base">
          <span className="flex items-center gap-2">
            <LineChart className="h-4 w-4 text-success" />
            Revenue Logic Stress
          </span>
          <div className="flex flex-wrap gap-1">
            <Pill label={statusLabel} tone={certified ? statusTone.wired : statusTone.orphaned} />
            <Pill label={`${formatCompact(summary.net_positive_candidate_count)} net-positive`} tone="border-success/30 bg-success/10 text-success" />
            <Pill label={`${formatCompact(summary.intent_eligible_candidate_count)} intent eligible`} tone={summary.intent_eligible_candidate_count ? statusTone.wired : statusTone.orphaned} />
            <Pill label="/aureon_capital_revenue_logic_stress_audit.json" tone="border-primary/30 bg-primary/10 text-primary" />
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
          {[
            ["Candidates", summary.candidate_count],
            ["Trade ready", summary.trade_ready_candidate_count],
            ["False rejects", summary.false_positive_reject_count],
            ["Candidate-ready", summary.candidate_level_intent_eligible_count],
            ["Close first", summary.close_first_opportunity_count],
            ["Duplicate blocks", summary.duplicate_route_blocked_count],
            ["Shadow confirms", summary.shadow_confirmation_count],
            ["Live gates", summary.live_gates_blocking ? "blocking" : "clear"],
            ["External hedges", summary.external_shadow_only ? "shadow only" : "attention"],
            ["No live mutation", summary.no_live_mutation ? "yes" : "attention"],
          ].map(([label, value]) => (
            <div key={String(label)} className="rounded-md border border-border/40 bg-black/20 p-3">
              <div className="text-[11px] uppercase text-muted-foreground">{String(label)}</div>
              <div className="mt-1 font-mono text-sm font-semibold text-success">
                {typeof value === "number" ? formatCompact(value) : String(value ?? "0")}
              </div>
            </div>
          ))}
        </div>

        <div className="grid gap-3 xl:grid-cols-[1.1fr_0.9fr]">
          <div className="space-y-2">
            <div className="flex items-center justify-between gap-2">
              <div className="text-xs uppercase text-muted-foreground">Top net-positive candidates</div>
              <Pill label="after spread, fees, slippage, floor, risk" tone="border-success/30 bg-success/10 text-success" />
            </div>
            <div className="grid gap-2 md:grid-cols-2">
              {netRows.length ? netRows.slice(0, 8).map((item) => (
                <div key={String(item.candidate_id || item.route_key || item.symbol)} className="rounded-md border border-border/40 bg-muted/10 px-3 py-2 text-xs">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium">{String(item.symbol || item.epic || "capital")}</span>
                    <span className="font-mono text-success">{formatCompact(item.expected_net_revenue)}</span>
                  </div>
                  <div className="mt-1 truncate text-muted-foreground">
                    {String(item.side || "WATCH")} / gross {formatCompact(item.gross_edge)} / blockers {formatCompact(blockerLabels(item.revenue_blockers).length)}
                  </div>
                </div>
              )) : (
                <div className="rounded-md border border-border/40 bg-muted/10 p-4 text-sm text-muted-foreground">
                  Net-positive Capital revenue proof is pending or gated.
                </div>
              )}
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between gap-2">
              <div className="text-xs uppercase text-muted-foreground">False-positive rejects</div>
              <Pill label={`${formatCompact(summary.false_positive_reject_count)} rejected`} tone="border-warning/30 bg-warning/10 text-warning" />
            </div>
            <div className="grid gap-2">
              {rejectRows.length ? rejectRows.slice(0, 6).map((item) => (
                <div key={String(item.candidate_id || item.route_key || item.symbol)} className="rounded-md border border-border/40 bg-black/20 px-3 py-2 text-xs">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium">{String(item.symbol || "capital")}</span>
                    <span className="font-mono text-muted-foreground">{formatCompact(item.expected_net_revenue)}</span>
                  </div>
                  <div className="mt-1 truncate text-muted-foreground">
                    {blockerLabels(item.revenue_blockers).join(", ") || "cost/risk gate"}
                  </div>
                </div>
              )) : (
                <div className="rounded-md border border-border/40 bg-muted/10 p-4 text-sm text-muted-foreground">
                  No gross-positive false rejects are visible.
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="grid gap-3 lg:grid-cols-3">
          <div className="rounded-md border border-border/40 bg-black/20 p-3 text-xs">
            <div className="mb-2 flex items-center justify-between gap-2">
              <span className="uppercase text-muted-foreground">Order-intent readiness</span>
              <Pill label={readiness.live_gates_blocking ? "gated" : "clear"} tone={readiness.live_gates_blocking ? statusTone.orphaned : statusTone.wired} />
            </div>
            <div className="truncate text-muted-foreground">candidate-ready {formatCompact(readiness.candidate_level_eligible_count)}</div>
            <div className="mt-1 truncate text-muted-foreground">runtime blockers {formatCompact(blockerLabels(readiness.runtime_gate_blockers).length)}</div>
          </div>
          <div className="rounded-md border border-border/40 bg-black/20 p-3 text-xs">
            <div className="mb-2 flex items-center justify-between gap-2">
              <span className="uppercase text-muted-foreground">Lifecycle and close-first</span>
              <Pill label={summary.duplicate_route_blocked_count ? "duplicates blocked" : "no duplicate rows"} tone={summary.duplicate_route_blocked_count ? statusTone.wired : statusTone.orphaned} />
            </div>
            <div className="truncate text-muted-foreground">active routes {formatCompact(lifecycle.active_lifecycle_route_count)}</div>
            <div className="mt-1 truncate text-muted-foreground">close-first {formatCompact(closeFirst.close_first_opportunity_count)}</div>
          </div>
          <div className="rounded-md border border-border/40 bg-black/20 p-3 text-xs">
            <div className="mb-2 flex items-center justify-between gap-2">
              <span className="uppercase text-muted-foreground">External confirmation</span>
              <Pill label={external.external_shadow_only ? "shadow only" : "attention"} tone={external.external_shadow_only ? statusTone.wired : statusTone.security_blocker} />
            </div>
            <div className="truncate text-muted-foreground">hedges {formatCompact(external.shadow_confirmation_count)}</div>
            <div className="mt-1 truncate text-muted-foreground">runtime gates {formatCompact(blockerLabels(runtimeGate.blockers).length)}</div>
          </div>
        </div>

        {blockers.length ? (
          <div className="flex flex-wrap gap-1">
            {blockers.slice(0, 10).map((blocker) => (
              <Pill key={blocker} label={blocker.replace(/_/g, " ")} tone={statusTone.security_blocker} />
            ))}
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}

function CapitalRevenueLiveGateReadinessPanel({ audit }: { audit: CapitalRevenueLiveGateReadinessAudit | null }) {
  const summary = audit?.summary || {};
  const readiness = asRecord(audit?.current_live_gate_readiness);
  const rows = asRecordArray(audit?.candidate_readiness_rows);
  const stressCases = asRecordArray(audit?.gate_clear_stress_cases);
  const runtimeProof = asRecord(audit?.runtime_gate_proof);
  const lifecycleProof = asRecord(audit?.lifecycle_gate_proof);
  const closeProof = asRecord(audit?.close_first_exit_proof);
  const externalProof = asRecord(audit?.external_confirmation_proof);
  const blockers = ((audit?.blockers || []) as string[]).filter(Boolean);
  const missingGateIds = Array.isArray(readiness.missing_gate_ids) ? readiness.missing_gate_ids.map((item) => String(item)).filter(Boolean) : [];
  const runtimeGateIds = Array.isArray(runtimeProof.runtime_gate_ids) ? runtimeProof.runtime_gate_ids.map((item) => String(item)).filter(Boolean) : [];
  const ready = audit?.status === "live_gate_ready" && blockers.length === 0;
  const statusLabel = String(audit?.status || "live gate pending").replace(/_/g, " ");
  const passedStress = stressCases.filter((item) => Boolean(item.passed)).length;

  return (
    <Card className="border-primary/30 bg-primary/5">
      <CardHeader className="pb-3">
        <CardTitle className="flex flex-wrap items-center justify-between gap-2 text-base">
          <span className="flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 text-primary" />
            Live Gate Readiness
          </span>
          <div className="flex flex-wrap gap-1">
            <Pill label={statusLabel} tone={ready ? statusTone.wired : statusTone.orphaned} />
            <Pill label={`${formatCompact(summary.ready_now_candidate_count)} ready now`} tone={summary.ready_now_candidate_count ? statusTone.wired : statusTone.orphaned} />
            <Pill label={`${formatCompact(summary.missing_gate_count)} missing gates`} tone={summary.missing_gate_count ? statusTone.security_blocker : statusTone.wired} />
            <Pill label="/aureon_capital_revenue_live_gate_readiness_audit.json" tone="border-primary/30 bg-primary/10 text-primary" />
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-5">
          {[
            ["Net-positive", summary.net_positive_candidate_count],
            ["Blocked", summary.blocked_candidate_count],
            ["Runtime gates", summary.runtime_gates_clear ? "clear" : "blocking"],
            ["Recovered exit", summary.recovered_exit_clear ? "clear" : "held"],
            ["Duplicate routes", summary.duplicate_routes_blocked ? "blocked" : "clear"],
            ["Broker proof", summary.broker_correlation_complete ? "complete" : "missing"],
            ["External", summary.external_shadow_only ? "shadow only" : "attention"],
            ["No live mutation", summary.no_live_mutation ? "yes" : "attention"],
            ["Stress cases", `${formatCompact(passedStress)}/${formatCompact(stressCases.length)}`],
            ["Readiness gates", `${formatCompact(readiness.gate_count)}`],
          ].map(([label, value]) => (
            <div key={String(label)} className="rounded-md border border-border/40 bg-black/20 p-3">
              <div className="text-[11px] uppercase text-muted-foreground">{String(label)}</div>
              <div className="mt-1 font-mono text-sm font-semibold text-primary">
                {typeof value === "number" ? formatCompact(value) : String(value ?? "0")}
              </div>
            </div>
          ))}
        </div>

        <div className="grid gap-3 xl:grid-cols-[1.15fr_0.85fr]">
          <div className="space-y-2">
            <div className="flex items-center justify-between gap-2">
              <div className="text-xs uppercase text-muted-foreground">Current candidate readiness</div>
              <Pill label="existing executor path only" tone="border-primary/30 bg-primary/10 text-primary" />
            </div>
            <div className="grid gap-2 md:grid-cols-2">
              {rows.length ? rows.slice(0, 8).map((item) => {
                const missing = Array.isArray(item.missing_live_gate_ids) ? item.missing_live_gate_ids.map((gate) => String(gate)).filter(Boolean) : [];
                return (
                  <div key={String(item.candidate_id || item.route_key || item.symbol)} className="rounded-md border border-border/40 bg-muted/10 px-3 py-2 text-xs">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-medium">{String(item.symbol || item.epic || "capital")}</span>
                      <span className="font-mono text-primary">{formatCompact(item.expected_net_revenue)}</span>
                    </div>
                    <div className="mt-1 truncate text-muted-foreground">
                      {String(item.side || "WATCH")} / {String(item.readiness_state || "blocked_by_live_gates").replace(/_/g, " ")}
                    </div>
                    <div className="mt-2 flex flex-wrap gap-1">
                      {missing.length ? missing.slice(0, 4).map((gate) => (
                        <Pill key={gate} label={gate.replace(/_/g, " ")} tone={statusTone.security_blocker} />
                      )) : (
                        <Pill label="ready for existing executor intent" tone={statusTone.wired} />
                      )}
                    </div>
                    {item.next_required_evidence ? (
                      <div className="mt-2 text-muted-foreground">{String(item.next_required_evidence)}</div>
                    ) : null}
                  </div>
                );
              }) : (
                <div className="rounded-md border border-border/40 bg-muted/10 p-4 text-sm text-muted-foreground">
                  No net-positive Capital candidates are visible in the live-gate readiness audit.
                </div>
              )}
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between gap-2">
              <div className="text-xs uppercase text-muted-foreground">Fixture gate-clear stress</div>
              <Pill label={`${formatCompact(passedStress)} passed`} tone={passedStress === stressCases.length && stressCases.length ? statusTone.wired : statusTone.orphaned} />
            </div>
            <div className="grid gap-2">
              {stressCases.length ? stressCases.slice(0, 8).map((item) => (
                <div key={String(item.id)} className="rounded-md border border-border/40 bg-black/20 px-3 py-2 text-xs">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium">{String(item.label || item.id).replace(/_/g, " ")}</span>
                    <Pill label={item.passed ? "pass" : "attention"} tone={item.passed ? statusTone.wired : statusTone.orphaned} />
                  </div>
                  <div className="mt-1 truncate text-muted-foreground">
                    {String(item.readiness_state || "fixture proof")} / {String(item.proof_mode || "fixture")}
                  </div>
                </div>
              )) : (
                <div className="rounded-md border border-border/40 bg-muted/10 p-4 text-sm text-muted-foreground">
                  Gate-clear stress cases are pending.
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="grid gap-3 lg:grid-cols-3">
          <div className="rounded-md border border-border/40 bg-black/20 p-3 text-xs">
            <div className="mb-2 flex items-center justify-between gap-2">
              <span className="uppercase text-muted-foreground">Runtime gate proof</span>
              <Pill label={summary.runtime_gates_clear ? "clear" : "blocking"} tone={summary.runtime_gates_clear ? statusTone.wired : statusTone.orphaned} />
            </div>
            <div className="truncate text-muted-foreground">runtime ids {runtimeGateIds.slice(0, 4).join(", ") || "none"}</div>
            <div className="mt-1 truncate text-muted-foreground">packet {String(runtimeProof.order_intent_packet_status || "unknown")}</div>
          </div>
          <div className="rounded-md border border-border/40 bg-black/20 p-3 text-xs">
            <div className="mb-2 flex items-center justify-between gap-2">
              <span className="uppercase text-muted-foreground">Lifecycle and exit</span>
              <Pill label={lifecycleProof.lifecycle_continuity_resolved ? "resolved" : "attention"} tone={lifecycleProof.lifecycle_continuity_resolved ? statusTone.wired : statusTone.orphaned} />
            </div>
            <div className="truncate text-muted-foreground">recovered chain {String(closeProof.recovered_close_chain_status || "unknown").replace(/_/g, " ")}</div>
            <div className="mt-1 truncate text-muted-foreground">recovered count {formatCompact(closeProof.recovered_position_count)}</div>
          </div>
          <div className="rounded-md border border-border/40 bg-black/20 p-3 text-xs">
            <div className="mb-2 flex items-center justify-between gap-2">
              <span className="uppercase text-muted-foreground">External confirmation</span>
              <Pill label={summary.external_shadow_only ? "shadow only" : "attention"} tone={summary.external_shadow_only ? statusTone.wired : statusTone.security_blocker} />
            </div>
            <div className="truncate text-muted-foreground">shadow rows {formatCompact(externalProof.shadow_confirmation_count)}</div>
            <div className="mt-1 truncate text-muted-foreground">external intents {formatCompact(externalProof.external_live_order_intent_count)}</div>
          </div>
        </div>

        {missingGateIds.length ? (
          <div className="flex flex-wrap gap-1">
            {missingGateIds.slice(0, 12).map((gate) => (
              <Pill key={gate} label={gate.replace(/_/g, " ")} tone={statusTone.security_blocker} />
            ))}
          </div>
        ) : null}
        {blockers.length ? (
          <div className="flex flex-wrap gap-1">
            {blockers.slice(0, 10).map((blocker) => (
              <Pill key={blocker} label={blocker.replace(/_/g, " ")} tone={statusTone.orphaned} />
            ))}
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}

function CapitalLiveDryStressPanel({ audit }: { audit: CapitalEcosystemLiveDryStressAudit | null }) {
  const summary = audit?.summary || {};
  const runtimeProof = asRecord(audit?.runtime_proof);
  const watchlistProof = asRecord(audit?.capital_watchlist_proof);
  const lifecycleProof = asRecord(audit?.lifecycle_route_proof);
  const recoveredProof = asRecord(audit?.recovered_position_proof);
  const recoveredExitProof = asRecord(audit?.recovered_exit_readiness_proof);
  const brokerProof = asRecord(audit?.broker_correlation_proof);
  const closeProof = asRecord(audit?.close_first_proof);
  const shadowProof = asRecord(audit?.shadow_hedge_proof);
  const shadowRows = asRecordArray(shadowProof.hedges);
  const closeRows = asRecordArray(closeProof.opportunities);
  const brokerMissing = asRecordArray(brokerProof.missing_rows);
  const missingLinks = asRecordArray(lifecycleProof.missing_link_rows);
  const recoveredRows = asRecordArray(recoveredProof.recovered_routes);
  const recoveredMissingBroker = asRecordArray(recoveredProof.missing_broker_proof_rows);
  const recoveredMissingUpstream = asRecordArray(recoveredProof.missing_upstream_context_rows);
  const recoveredCloseMissing = asRecordArray(recoveredProof.close_first_missing_rows);
  const recoveredExitRows = asRecordArray(recoveredExitProof.exit_rows);
  const recoveredWaitingAbsenceRows = asRecordArray(recoveredExitProof.waiting_absence_rows);
  const recoveredAbsenceRows = asRecordArray(recoveredExitProof.absence_verified_rows);
  const recoveredOutcomeRows = asRecordArray(recoveredExitProof.outcome_rows);
  const recoveredMissingPnlRows = asRecordArray(recoveredExitProof.missing_pnl_rows);
  const recoveredStaleRows = asRecordArray(recoveredExitProof.stale_proof_rows);
  const blockers = ((audit?.blockers || []) as string[]).filter(Boolean);
  const certified = audit?.status === "live_dry_certified" && blockers.length === 0;
  const recoveredStatus = String(summary.recovery_certification_status || recoveredProof.recovery_certification_status || "not_applicable");
  const recoveredExitStatus = String(summary.recovered_close_chain_status || recoveredExitProof.recovered_close_chain_status || "not_applicable");

  return (
    <Card className="border-primary/30 bg-primary/5">
      <CardHeader className="pb-3">
        <CardTitle className="flex flex-wrap items-center justify-between gap-2 text-base">
          <span className="flex items-center gap-2">
            <Gauge className="h-4 w-4 text-primary" />
            Capital Live Dry Stress
          </span>
          <div className="flex flex-wrap gap-1">
            <Pill label={certified ? "live dry certified" : String(audit?.status || "live dry pending").replace(/_/g, " ")} tone={certified ? statusTone.wired : statusTone.orphaned} />
            <Pill label={`${formatCompact(summary.active_watchlist_count)}/40 active`} tone="border-primary/30 bg-primary/10 text-primary" />
            <Pill label={`${formatCompact(summary.bench_watchlist_count)}/100 bench`} tone="border-border bg-muted/20 text-muted-foreground" />
            <Pill label="/aureon_capital_ecosystem_live_dry_stress_audit.json" tone="border-primary/30 bg-primary/10 text-primary" />
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
          {[
            ["Runtime fresh", summary.runtime_fresh ? "yes" : "held"],
            ["Candidates", summary.candidate_count],
            ["Active routes", summary.active_lifecycle_route_count],
            ["Duplicate blocks", summary.duplicate_route_blocked_count],
            ["Close first", summary.close_first_opportunity_count],
            ["Shadow hedges", summary.shadow_hedge_count],
            ["Broker proof", summary.broker_correlation_complete ? "complete" : "attention"],
            ["Recovered", summary.recovered_position_count],
            ["Exit chain", recoveredExitStatus.replace(/^recovered_/, "").replace(/_/g, " ")],
            ["Mutation", summary.no_live_mutation ? "none" : "attention"],
          ].map(([label, value]) => (
            <div key={String(label)} className="rounded-md border border-border/40 bg-black/20 p-3">
              <div className="text-[11px] uppercase text-muted-foreground">{String(label)}</div>
              <div className="mt-1 font-mono text-sm font-semibold text-primary">
                {typeof value === "number" ? formatCompact(value) : String(value ?? "0")}
              </div>
            </div>
          ))}
        </div>

        <div className="grid gap-3 lg:grid-cols-3">
          <div className="rounded-md border border-border/40 bg-black/20 p-3 text-xs">
            <div className="mb-2 flex items-center justify-between gap-2">
              <span className="uppercase text-muted-foreground">Runtime proof</span>
              <Pill label={runtimeProof.runtime_fresh ? "fresh" : "held"} tone={runtimeProof.runtime_fresh ? statusTone.wired : statusTone.orphaned} />
            </div>
            <div className="truncate text-muted-foreground">endpoint {String(runtimeProof.endpoint || "pending")}</div>
            <div className="mt-1 truncate text-muted-foreground">age {String(runtimeProof.age_sec ?? "n/a")}s / {String(runtimeProof.stale_reason || "no stale reason")}</div>
          </div>
          <div className="rounded-md border border-border/40 bg-black/20 p-3 text-xs">
            <div className="mb-2 flex items-center justify-between gap-2">
              <span className="uppercase text-muted-foreground">Watchlist proof</span>
              <Pill label={summary.capital_watchlist_within_limit ? "within limit" : "attention"} tone={summary.capital_watchlist_within_limit ? statusTone.wired : statusTone.orphaned} />
            </div>
            <div className="truncate text-muted-foreground">active {formatCompact(watchlistProof.active_watchlist_count)}/{formatCompact(watchlistProof.active_watchlist_limit)}</div>
            <div className="mt-1 truncate text-muted-foreground">bench {formatCompact(watchlistProof.bench_watchlist_count)}/{formatCompact(watchlistProof.bench_watchlist_limit)}</div>
          </div>
          <div className="rounded-md border border-border/40 bg-black/20 p-3 text-xs">
            <div className="mb-2 flex items-center justify-between gap-2">
              <span className="uppercase text-muted-foreground">Lifecycle proof</span>
              <Pill label={summary.lifecycle_continuity_complete ? "complete" : "missing links"} tone={summary.lifecycle_continuity_complete ? statusTone.wired : statusTone.orphaned} />
            </div>
            <div className="truncate text-muted-foreground">routes {formatCompact(lifecycleProof.active_lifecycle_route_count)}</div>
            <div className="mt-1 truncate text-muted-foreground">duplicate blocks {formatCompact(lifecycleProof.duplicate_route_blocked_count)}</div>
          </div>
        </div>

        <div className="rounded-md border border-warning/30 bg-warning/5 p-3">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <div className="text-xs uppercase text-muted-foreground">Recovered position certification</div>
            <div className="flex flex-wrap gap-1">
              <Pill
                label={recoveredStatus.replace(/_/g, " ")}
                tone={summary.recovered_positions_certified ? statusTone.wired : statusTone.orphaned}
              />
              <Pill
                label={summary.recovered_position_close_first_covered ? "close-first covered" : "close-first attention"}
                tone={summary.recovered_position_close_first_covered ? statusTone.wired : statusTone.orphaned}
              />
              <Pill
                label={summary.recovered_duplicate_route_blocking_active ? "duplicates blocked" : "duplicate attention"}
                tone={summary.recovered_duplicate_route_blocking_active ? statusTone.wired : statusTone.orphaned}
              />
            </div>
          </div>
          <div className="grid gap-2 sm:grid-cols-4">
            {[
              ["Recovered rows", summary.recovered_position_count],
              ["Upstream context", summary.recovered_upstream_context_missing_count],
              ["Broker gaps", recoveredMissingBroker.length],
              ["Close gaps", recoveredCloseMissing.length],
            ].map(([label, value]) => (
              <div key={String(label)} className="rounded-md border border-border/40 bg-black/20 p-3 text-xs">
                <div className="uppercase text-muted-foreground">{String(label)}</div>
                <div className="mt-1 font-mono text-sm font-semibold text-warning">{formatCompact(value as number)}</div>
              </div>
            ))}
          </div>
          {recoveredRows.length ? (
            <div className="mt-3 grid gap-2 md:grid-cols-2 xl:grid-cols-3">
              {recoveredRows.slice(0, 6).map((item) => (
                <div key={String(item.lifecycle_id || item.deal_id || item.route_key)} className="rounded-md border border-border/40 bg-black/20 px-3 py-2 text-xs">
                  <div className="font-medium">{String(item.symbol || "Capital")} {String(item.side || "")}</div>
                  <div className="mt-1 truncate text-muted-foreground">{String(item.deal_id || "deal pending")}</div>
                  <div className="mt-1 truncate text-muted-foreground">{String(item.route_key || "route pending")}</div>
                </div>
              ))}
            </div>
          ) : null}
        </div>

        <div className="rounded-md border border-primary/30 bg-primary/5 p-3">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <div className="text-xs uppercase text-muted-foreground">Recovered exit readiness</div>
            <div className="flex flex-wrap gap-1">
              <Pill
                label={recoveredExitStatus.replace(/_/g, " ")}
                tone={recoveredExitStatus === "recovered_outcome_recorded" ? statusTone.wired : statusTone.orphaned}
              />
              <Pill label={`${formatCompact(summary.recovered_close_acknowledged_count)} close ack`} tone="border-primary/30 bg-primary/10 text-primary" />
              <Pill label={`${formatCompact(summary.recovered_position_absence_verified_count)} absent`} tone="border-border bg-muted/20 text-muted-foreground" />
              <Pill label={`${formatCompact(summary.recovered_outcome_recorded_count)} outcomes`} tone="border-border bg-muted/20 text-muted-foreground" />
            </div>
          </div>
          <div className="grid gap-2 sm:grid-cols-5">
            {[
              ["Close requests", summary.recovered_close_request_count],
              ["Close ack", summary.recovered_close_acknowledged_count],
              ["Absence proof", summary.recovered_position_absence_verified_count],
              ["Outcomes", summary.recovered_outcome_recorded_count],
              ["Exit blockers", ((summary.recovered_exit_blockers || []) as string[]).length],
            ].map(([label, value]) => (
              <div key={String(label)} className="rounded-md border border-border/40 bg-black/20 p-3 text-xs">
                <div className="uppercase text-muted-foreground">{String(label)}</div>
                <div className="mt-1 font-mono text-sm font-semibold text-primary">{formatCompact(value as number)}</div>
              </div>
            ))}
          </div>
          {recoveredExitRows.length ? (
            <div className="mt-3 grid gap-2 md:grid-cols-2 xl:grid-cols-3">
              {recoveredExitRows.slice(0, 6).map((item) => (
                <div key={String(item.lifecycle_id || item.deal_id || item.route_key)} className="rounded-md border border-border/40 bg-black/20 px-3 py-2 text-xs">
                  <div className="font-medium">{String(item.symbol || "Capital")} {String(item.current_status || "exit").replace(/_/g, " ")}</div>
                  <div className="mt-1 truncate text-muted-foreground">{String(item.deal_id || item.route_key || "broker proof pending")}</div>
                  <div className="mt-1 truncate text-muted-foreground">
                    ack {String(item.close_acknowledged ? "yes" : "no")} / absent {String(item.position_absence_verified ? "yes" : "no")} / P/L {String(item.pnl_present ? "yes" : "held")}
                  </div>
                </div>
              ))}
            </div>
          ) : null}
          {[...recoveredWaitingAbsenceRows, ...recoveredMissingPnlRows, ...recoveredStaleRows].length ? (
            <div className="mt-3 flex flex-wrap gap-1">
              {recoveredWaitingAbsenceRows.slice(0, 4).map((item) => (
                <Pill key={`waiting-${String(item.lifecycle_id || item.deal_id)}`} label={`${String(item.symbol || "position")} waiting absence`} tone={statusTone.orphaned} />
              ))}
              {recoveredMissingPnlRows.slice(0, 4).map((item) => (
                <Pill key={`pnl-${String(item.lifecycle_id || item.deal_id)}`} label={`${String(item.symbol || "position")} missing P/L`} tone={statusTone.orphaned} />
              ))}
              {recoveredStaleRows.slice(0, 4).map((item) => (
                <Pill key={`stale-${String(item.lifecycle_id || item.deal_id)}`} label={`${String(item.symbol || "position")} stale proof`} tone={statusTone.security_blocker} />
              ))}
            </div>
          ) : null}
          {[...recoveredAbsenceRows, ...recoveredOutcomeRows].length ? (
            <div className="mt-3 flex flex-wrap gap-1">
              {recoveredAbsenceRows.slice(0, 4).map((item) => (
                <Pill key={`absent-${String(item.lifecycle_id || item.deal_id)}`} label={`${String(item.symbol || "position")} absence verified`} tone={statusTone.wired} />
              ))}
              {recoveredOutcomeRows.slice(0, 4).map((item) => (
                <Pill key={`outcome-${String(item.lifecycle_id || item.deal_id)}`} label={`${String(item.symbol || "position")} outcome recorded`} tone={statusTone.wired} />
              ))}
            </div>
          ) : null}
        </div>

        <div className="grid gap-3 lg:grid-cols-2">
          <div className="space-y-2">
            <div className="flex items-center justify-between gap-2">
              <div className="text-xs uppercase text-muted-foreground">Broker correlation proof</div>
              <Pill label={summary.broker_correlation_complete ? "complete" : "attention"} tone={summary.broker_correlation_complete ? statusTone.wired : statusTone.orphaned} />
            </div>
            <div className="grid gap-2">
              {brokerMissing.length ? brokerMissing.slice(0, 5).map((item) => (
                <div key={String(item.lifecycle_id || item.route_key)} className="rounded-md border border-border/40 bg-black/20 px-3 py-2 text-xs">
                  <div className="font-medium">{String(item.route_key || "route")}</div>
                  <div className="mt-1 truncate text-muted-foreground">missing {String((item.missing_fields as string[] | undefined)?.join(", ") || "fields")}</div>
                </div>
              )) : (
                <div className="rounded-md border border-border/40 bg-muted/10 p-4 text-sm text-muted-foreground">
                  Broker correlation fields are complete for checked live-dry rows.
                </div>
              )}
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between gap-2">
              <div className="text-xs uppercase text-muted-foreground">Close-first and shadow hedge proof</div>
              <Pill label={summary.shadow_hedges_only ? "shadow only" : "hedge attention"} tone={summary.shadow_hedges_only ? statusTone.wired : statusTone.security_blocker} />
            </div>
            <div className="grid gap-2">
              {closeRows.length ? closeRows.slice(0, 3).map((item) => (
                <div key={String(item.lifecycle_id || item.route_key)} className="rounded-md border border-border/40 bg-black/20 px-3 py-2 text-xs">
                  <div className="font-medium">{String(item.symbol || "Capital position")} close-first</div>
                  <div className="mt-1 truncate text-muted-foreground">{String(item.deal_id || item.route_key || "runtime close gate required")}</div>
                </div>
              )) : (
                <div className="rounded-md border border-border/40 bg-muted/10 p-4 text-sm text-muted-foreground">
                  No close-first opportunities are required by current evidence.
                </div>
              )}
              {shadowRows.slice(0, 3).map((item) => (
                <div key={String(item.hedge_candidate_id || item.target_symbol)} className="rounded-md border border-border/40 bg-black/20 px-3 py-2 text-xs">
                  <div className="font-medium">{String(item.source_exchange || "exchange")} -&gt; {String(item.target_symbol || "capital")}</div>
                  <div className="mt-1 truncate text-muted-foreground">{String(item.hedge_side || "WATCH")} / {String(item.authority || "shadow_only")}</div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {missingLinks.length ? (
          <div className="space-y-2">
            <div className="text-xs uppercase text-muted-foreground">Lifecycle missing links</div>
            <div className="flex flex-wrap gap-1">
              {missingLinks.slice(0, 6).map((item) => (
                <Pill key={String(item.lifecycle_id || item.route_key)} label={String(item.route_key || item.lifecycle_id || "missing link")} tone={statusTone.orphaned} />
              ))}
            </div>
          </div>
        ) : null}

        {recoveredMissingUpstream.length ? (
          <div className="space-y-2">
            <div className="text-xs uppercase text-muted-foreground">Recovered upstream context missing</div>
            <div className="flex flex-wrap gap-1">
              {recoveredMissingUpstream.slice(0, 6).map((item) => (
                <Pill key={String(item.lifecycle_id || item.deal_id || item.route_key)} label={String(item.route_key || item.deal_id || "recovered position")} tone={statusTone.orphaned} />
              ))}
            </div>
          </div>
        ) : null}

        {blockers.length ? (
          <div className="flex flex-wrap gap-1">
            {blockers.slice(0, 10).map((blocker) => (
              <Pill key={blocker} label={blocker.replace(/_/g, " ")} tone={statusTone.security_blocker} />
            ))}
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}

function AppShell() {
  const [state, setState] = useState<UnifiedFrontendState | null>(null);
  const [runtime, setRuntime] = useState<RuntimeObservation>({
    connected: false,
    clearancePending: false,
    statusLines: ["Runtime feed pending."],
    metrics: [],
    clearances: [],
    details: [],
  });
  const [tradingChecklist, setTradingChecklist] = useState<TradingIntelligenceChecklist | null>(null);
  const [exchangeChecklist, setExchangeChecklist] = useState<ExchangeMonitoringChecklist | null>(null);
  const [exchangeDataMatrix, setExchangeDataMatrix] = useState<ExchangeDataCapabilityMatrix | null>(null);
  const [globalCoverageMap, setGlobalCoverageMap] = useState<GlobalFinancialCoverageMap | null>(null);
  const [hncSecurityComparison, setHncSecurityComparison] = useState<HNCPacketSecurityComparison | null>(null);
  const [liveGoalTradeAudit, setLiveGoalTradeAudit] = useState<LiveGoalTradeAudit | null>(null);
  const [orderLifecycleStressAudit, setOrderLifecycleStressAudit] = useState<OrderLifecycleStressAudit | null>(null);
  const [capitalEcosystemIntelligence, setCapitalEcosystemIntelligence] = useState<CapitalEcosystemIntelligenceCompany | null>(null);
  const [capitalRevenueLogicStressAudit, setCapitalRevenueLogicStressAudit] = useState<CapitalRevenueLogicStressAudit | null>(null);
  const [capitalRevenueLiveGateReadinessAudit, setCapitalRevenueLiveGateReadinessAudit] = useState<CapitalRevenueLiveGateReadinessAudit | null>(null);
  const [capitalThreePLiveExecutionCertificationAudit, setCapitalThreePLiveExecutionCertificationAudit] = useState<CapitalThreePLiveExecutionCertificationAudit | null>(null);
  const [capitalThreePBlockerBurndownAudit, setCapitalThreePBlockerBurndownAudit] = useState<CapitalThreePBlockerBurndownAudit | null>(null);
  const [performanceReadinessAudit, setPerformanceReadinessAudit] = useState<PerformanceReadinessAudit | null>(null);
  const [aureonMurgeUnityBridge, setAureonMurgeUnityBridge] = useState<AureonMurgeUnityBridge | null>(null);
  const [aureonMurgeRuntimeActivation, setAureonMurgeRuntimeActivation] = useState<AureonMurgeRuntimeActivationStressAudit | null>(null);
  const [liveTradeSignalFabric, setLiveTradeSignalFabric] = useState<LiveTradeSignalFabric | null>(null);
  const [liveTradeSignalFabricStressAudit, setLiveTradeSignalFabricStressAudit] = useState<LiveTradeSignalFabricStressAudit | null>(null);
  const [swarmSearchMappingStressAudit, setSwarmSearchMappingStressAudit] = useState<SwarmSearchMappingStressAudit | null>(null);
  const [parallelStrategyUnity, setParallelStrategyUnity] = useState<ParallelStrategyUnity | null>(null);
  const [parallelStrategyUnityStressAudit, setParallelStrategyUnityStressAudit] = useState<ParallelStrategyUnityStressAudit | null>(null);
  const [capitalLiveDryStressAudit, setCapitalLiveDryStressAudit] = useState<CapitalEcosystemLiveDryStressAudit | null>(null);
  const [loading, setLoading] = useState(true);
  const [now, setNow] = useState(() => Date.now());
  const [active, setActive] = useState("overview");
  const [dashboardTab, setDashboardTabState] = useState<DashboardTabId>(() =>
    typeof window === "undefined" ? "overview" : normalizeDashboardTab(window.location.hash),
  );
  const [blockerFilter, setBlockerFilter] = useState<BlockerFilter>("all");
  const [workOrderFilter, setWorkOrderFilter] = useState<WorkOrderFilter>("all");
  const [surfaceQuery, setSurfaceQuery] = useState("");
  const [surfaceFilter, setSurfaceFilter] = useState<SurfaceFilter>("all");
  const [evidenceFilter, setEvidenceFilter] = useState<EvidenceFilter>("all");

  const setDashboardTab = (value: string) => {
    const next = normalizeDashboardTab(value);
    setDashboardTabState(next);
    if (typeof window !== "undefined") {
      const nextHash = `#${next}`;
      if (window.location.hash !== nextHash) {
        window.history.replaceState(null, "", `${window.location.pathname}${window.location.search}${nextHash}`);
      }
    }
  };

  const refresh = async () => {
    setLoading(true);
    const loaded = await loadUnifiedFrontendState();
    setState(loaded);
    setLoading(false);
  };

  useEffect(() => {
    refresh();
    const timer = window.setInterval(refresh, MANIFEST_REFRESH_MS);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), UI_CLOCK_REFRESH_MS);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return undefined;
    const syncHash = () => setDashboardTabState(normalizeDashboardTab(window.location.hash));
    syncHash();
    window.addEventListener("hashchange", syncHash);
    return () => window.removeEventListener("hashchange", syncHash);
  }, []);

  useEffect(() => {
    const refreshRuntime = async () => setRuntime(await loadRuntimeObservation());
    refreshRuntime();
    const timer = window.setInterval(refreshRuntime, RUNTIME_REFRESH_MS);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    const refreshChecklist = async () => setTradingChecklist(await loadTradingIntelligenceChecklist());
    refreshChecklist();
    const timer = window.setInterval(refreshChecklist, FAST_PANEL_REFRESH_MS);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    const refreshExchangeChecklist = async () => setExchangeChecklist(await loadExchangeMonitoringChecklist());
    refreshExchangeChecklist();
    const timer = window.setInterval(refreshExchangeChecklist, FAST_PANEL_REFRESH_MS);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    const refreshExchangeDataMatrix = async () => setExchangeDataMatrix(await loadExchangeDataCapabilityMatrix());
    refreshExchangeDataMatrix();
    const timer = window.setInterval(refreshExchangeDataMatrix, MARKET_PANEL_REFRESH_MS);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    const refreshGlobalCoverage = async () => setGlobalCoverageMap(await loadGlobalFinancialCoverageMap());
    refreshGlobalCoverage();
    const timer = window.setInterval(refreshGlobalCoverage, MARKET_PANEL_REFRESH_MS);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    const refreshLiveGoalTradeAudit = async () => setLiveGoalTradeAudit(await loadLiveGoalTradeAudit());
    refreshLiveGoalTradeAudit();
    const timer = window.setInterval(refreshLiveGoalTradeAudit, FAST_PANEL_REFRESH_MS);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    const refreshOrderLifecycleStressAudit = async () => setOrderLifecycleStressAudit(await loadOrderLifecycleStressAudit());
    refreshOrderLifecycleStressAudit();
    const timer = window.setInterval(refreshOrderLifecycleStressAudit, FAST_PANEL_REFRESH_MS);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    const refreshCapitalEcosystem = async () => setCapitalEcosystemIntelligence(await loadCapitalEcosystemIntelligence());
    refreshCapitalEcosystem();
    const timer = window.setInterval(refreshCapitalEcosystem, FAST_PANEL_REFRESH_MS);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    const refreshCapitalRevenueLogic = async () => setCapitalRevenueLogicStressAudit(await loadCapitalRevenueLogicStressAudit());
    refreshCapitalRevenueLogic();
    const timer = window.setInterval(refreshCapitalRevenueLogic, FAST_PANEL_REFRESH_MS);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    const refreshCapitalRevenueLiveGate = async () => setCapitalRevenueLiveGateReadinessAudit(await loadCapitalRevenueLiveGateReadinessAudit());
    refreshCapitalRevenueLiveGate();
    const timer = window.setInterval(refreshCapitalRevenueLiveGate, FAST_PANEL_REFRESH_MS);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    const refreshCapitalThreePExecution = async () => setCapitalThreePLiveExecutionCertificationAudit(await loadCapitalThreePLiveExecutionCertificationAudit());
    refreshCapitalThreePExecution();
    const timer = window.setInterval(refreshCapitalThreePExecution, FAST_PANEL_REFRESH_MS);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    const refreshCapitalThreePBurndown = async () => setCapitalThreePBlockerBurndownAudit(await loadCapitalThreePBlockerBurndownAudit());
    refreshCapitalThreePBurndown();
    const timer = window.setInterval(refreshCapitalThreePBurndown, FAST_PANEL_REFRESH_MS);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    const refreshPerformanceReadiness = async () => setPerformanceReadinessAudit(await loadPerformanceReadinessAudit());
    refreshPerformanceReadiness();
    const timer = window.setInterval(refreshPerformanceReadiness, FAST_PANEL_REFRESH_MS);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    const refreshMurgeUnity = async () => setAureonMurgeUnityBridge(await loadAureonMurgeUnityBridge());
    refreshMurgeUnity();
    const timer = window.setInterval(refreshMurgeUnity, MANIFEST_REFRESH_MS);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    const refreshMurgeRuntimeActivation = async () => setAureonMurgeRuntimeActivation(await loadAureonMurgeRuntimeActivationStressAudit());
    refreshMurgeRuntimeActivation();
    const timer = window.setInterval(refreshMurgeRuntimeActivation, FAST_PANEL_REFRESH_MS);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    const refreshLiveTradeSignalFabric = async () => setLiveTradeSignalFabric(await loadLiveTradeSignalFabric());
    refreshLiveTradeSignalFabric();
    const timer = window.setInterval(refreshLiveTradeSignalFabric, FAST_PANEL_REFRESH_MS);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    const refreshLiveTradeSignalFabricStress = async () => setLiveTradeSignalFabricStressAudit(await loadLiveTradeSignalFabricStressAudit());
    refreshLiveTradeSignalFabricStress();
    const timer = window.setInterval(refreshLiveTradeSignalFabricStress, FAST_PANEL_REFRESH_MS);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    const refreshSwarmSearchMapping = async () => setSwarmSearchMappingStressAudit(await loadSwarmSearchMappingStressAudit());
    refreshSwarmSearchMapping();
    const timer = window.setInterval(refreshSwarmSearchMapping, FAST_PANEL_REFRESH_MS);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    const refreshParallelStrategyUnity = async () => setParallelStrategyUnity(await loadParallelStrategyUnity());
    refreshParallelStrategyUnity();
    const timer = window.setInterval(refreshParallelStrategyUnity, FAST_PANEL_REFRESH_MS);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    const refreshParallelStrategyUnityStress = async () => setParallelStrategyUnityStressAudit(await loadParallelStrategyUnityStressAudit());
    refreshParallelStrategyUnityStress();
    const timer = window.setInterval(refreshParallelStrategyUnityStress, FAST_PANEL_REFRESH_MS);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    const refreshCapitalLiveDryStress = async () => setCapitalLiveDryStressAudit(await loadCapitalLiveDryStressAudit());
    refreshCapitalLiveDryStress();
    const timer = window.setInterval(refreshCapitalLiveDryStress, FAST_PANEL_REFRESH_MS);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    const refreshSecurity = async () => setHncSecurityComparison(await loadHNCPacketSecurityComparison());
    refreshSecurity();
    const timer = window.setInterval(refreshSecurity, MANIFEST_REFRESH_MS);
    return () => window.clearInterval(timer);
  }, []);

  const inventory = (state?.inventory || {}) as SaaSInventoryManifest;
  const plan = state?.plan || {};
  const organism = state?.organism || {};
  const evolution = state?.evolution || {};
  const switchboard = state?.switchboard || {};
  const screens = plan.canonical_screens || [];
  const summary = inventory.summary || {};
  const organismSummary = organism.summary || {};
  const evolutionSummary = evolution.summary || {};
  const switchboardSummary = switchboard.summary || {};
  const planSummary = plan.summary || {};
  const percent = readinessPercent(summary);
  const securityBlockers = asNumber(summary.security_blocker_count);
  const blindSpotCount = asNumber(organismSummary.blind_spot_count);
  const highBlindSpotCount = asNumber(organismSummary.high_blind_spot_count);
  const manualActions = Object.entries(plan.safety_contract || {}).filter(([, value]) => Boolean(value));
  const activeScreen = screens.find((screen) => screen.id === active) || screens[0];
  const tradingScreen = screens.find((screen) => screen.id === "trading") || activeScreen;
  const securityScreen = screens.find((screen) => screen.id === "saas_security") || activeScreen;
  const selectedDashboardTab = dashboardTabs.find((tab) => tab.id === dashboardTab) || dashboardTabs[0];
  const statusLines = organism.status_lines?.length ? organism.status_lines : runtime.statusLines;
  const allSecurityBlockers = Object.values(screenSecurityBlockers).flat();
  const filteredSecurityBlockers = allSecurityBlockers.filter((blocker) => matchesBlockerFilter(blocker, blockerFilter));
  const tradingSecurityBlockers = (screenSecurityBlockers.trading || []).filter((blocker) =>
    matchesBlockerFilter(blocker, blockerFilter),
  );
  const freshnessItems = useMemo(
    () =>
      buildFreshnessItems({
        state,
        runtime,
        tradingChecklist,
        exchangeChecklist,
        exchangeDataMatrix,
        globalCoverageMap,
        hncSecurityComparison,
        liveGoalTradeAudit,
        orderLifecycleStressAudit,
        capitalRevenueLogicStressAudit,
        capitalRevenueLiveGateReadinessAudit,
        capitalThreePLiveExecutionCertificationAudit,
        capitalThreePBlockerBurndownAudit,
        performanceReadinessAudit,
        aureonMurgeUnityBridge,
        aureonMurgeRuntimeActivation,
        liveTradeSignalFabric,
        liveTradeSignalFabricStressAudit,
        swarmSearchMappingStressAudit,
        parallelStrategyUnity,
        parallelStrategyUnityStressAudit,
        now,
      }),
    [state, runtime, tradingChecklist, exchangeChecklist, exchangeDataMatrix, globalCoverageMap, hncSecurityComparison, liveGoalTradeAudit, orderLifecycleStressAudit, capitalRevenueLogicStressAudit, capitalRevenueLiveGateReadinessAudit, capitalThreePLiveExecutionCertificationAudit, capitalThreePBlockerBurndownAudit, performanceReadinessAudit, aureonMurgeUnityBridge, aureonMurgeRuntimeActivation, liveTradeSignalFabric, liveTradeSignalFabricStressAudit, swarmSearchMappingStressAudit, parallelStrategyUnity, parallelStrategyUnityStressAudit, now],
  );

  const domainCounts = useMemo(() => inventory.counts?.by_domain || {}, [inventory.counts]);
  const topDomains = Object.entries(domainCounts)
    .sort((a, b) => asNumber(b[1]) - asNumber(a[1]))
    .slice(0, 8);

  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="sticky top-0 z-40 border-b border-border/50 bg-background/95 backdrop-blur">
        <div className="mx-auto flex max-w-[1500px] flex-col gap-3 px-4 py-4 lg:px-6">
          <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-center">
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="text-2xl font-semibold tracking-normal">Aureon Unified Autonomous Console</h1>
                <Badge variant={securityBlockers ? "destructive" : "success"}>
                  {securityBlockers ? `${securityBlockers} blockers` : "clear"}
                </Badge>
                <Badge variant={highBlindSpotCount ? "destructive" : blindSpotCount ? "outline" : "success"}>
                  {blindSpotCount ? `${blindSpotCount} blind spots` : "fresh pulse"}
                </Badge>
                <Badge variant="outline">{plan.status || "manifest pending"}</Badge>
                <Badge variant="secondary">{selectedDashboardTab.title}</Badge>
              </div>
              <p className="mt-1 max-w-4xl text-sm text-muted-foreground">
                Aureon works through its trading, accounting, research, vault, cognition, SaaS security, and self-audit systems while this shell exposes evidence, blockers, and manual-only boundaries.
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <Button onClick={refresh} variant="outline" size="sm" disabled={loading}>
                <RefreshCcw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />
                Refresh now
              </Button>
              <Pill
                label={runtime.connected ? (runtime.clearancePending ? "runtime feed checking" : "runtime feed live") : "runtime feed offline"}
                tone={runtime.connected ? (runtime.clearancePending ? statusTone.orphaned : statusTone.wired) : statusTone.security_blocker}
              />
              <Pill label={`view ${selectedDashboardTab.title}`} tone="border-primary/30 bg-primary/10 text-primary" />
              <Pill label={`checked ${formatFreshnessAge(timestampAgeSeconds(state?.loadedAt, now))} ago`} tone="border-border bg-muted/20 text-muted-foreground" />
            </div>
          </div>

          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
            <MetricTile label="SaaS surfaces" value={formatCompact(summary.surface_count)} icon={Database} />
            <MetricTile label="Frontend surfaces" value={formatCompact(summary.frontend_surface_count)} icon={Activity} />
            <MetricTile label="Fresh domains" value={`${formatCompact(organismSummary.fresh_domain_count)}/${formatCompact(organismSummary.domain_count)}`} icon={Server} />
            <MetricTile label="Evolution queue" value={formatCompact(evolutionSummary.queue_count)} icon={ShieldCheck} tone={asNumber(evolutionSummary.blocked_count) ? "text-warning" : "text-success"} />
            <MetricTile label="Capability modes" value={formatCompact(switchboardSummary.capability_count)} icon={Brain} tone={asNumber(switchboardSummary.blocker_count) ? "text-warning" : "text-success"} />
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-[1500px] px-4 py-5 lg:px-6">
        {state?.errors?.length ? (
          <Card className="mb-4 border-warning/30 bg-warning/10">
            <CardContent className="flex flex-col gap-2 p-4 text-sm text-warning md:flex-row md:items-center">
              <AlertTriangle className="h-4 w-4 shrink-0" />
              <div>{state.errors.join(" ")}</div>
            </CardContent>
          </Card>
        ) : null}

        <Tabs value={dashboardTab} onValueChange={setDashboardTab} className="space-y-5">
          <Card className="border-border/60 bg-card/95">
            <CardContent className="p-2">
              <ScrollArea className="w-full">
                <TabsList className="h-auto min-w-max justify-start gap-1 bg-transparent p-0">
                  {dashboardTabs.map((tab) => {
                    const Icon = tab.icon;
                    return (
                      <TabsTrigger
                        key={tab.id}
                        value={tab.id}
                        data-testid={`dashboard-tab-${tab.id}`}
                        className="min-h-12 gap-2 whitespace-nowrap px-3 py-2 text-left"
                      >
                        <Icon className="h-4 w-4" />
                        <span className="flex flex-col items-start leading-tight">
                          <span>{tab.title}</span>
                          <span className="hidden max-w-[180px] truncate text-[10px] font-normal text-muted-foreground lg:block">
                            {tab.summary}
                          </span>
                        </span>
                      </TabsTrigger>
                    );
                  })}
                </TabsList>
              </ScrollArea>
            </CardContent>
          </Card>

          <OperatorBriefingPanel
            tab={selectedDashboardTab}
            runtime={runtime}
            organism={organism}
            freshnessItems={freshnessItems}
            securityBlockers={securityBlockers}
            blindSpotCount={blindSpotCount}
            percent={percent}
            loading={loading}
            onRefresh={refresh}
          />

          <TabsContent value="overview" className="mt-0 space-y-5" data-testid="dashboard-content-overview">
            <DashboardStatusBanner
              tab={selectedDashboardTab}
              runtime={runtime}
              securityBlockers={securityBlockers}
              blindSpotCount={blindSpotCount}
              percent={percent}
            />
            <SecurityBlockerLane
              title="Visible Blockers"
              description="Filtered top blockers stay visible without flooding every tab."
              blockers={filteredSecurityBlockers}
              filter={blockerFilter}
              onFilterChange={setBlockerFilter}
              maxItems={3}
            />
            <OrganismPulsePanel organism={organism} runtimeConnected={runtime.connected} />
            <AureonMurgeUnityPanel bridge={aureonMurgeUnityBridge} />
            <AureonMurgeRuntimeActivationPanel audit={aureonMurgeRuntimeActivation} />
            <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
              <RuntimeMirrorPanel runtime={runtime} statusLines={statusLines} />
              <SafetyBoundariesPanel manualActions={manualActions} percent={percent} summary={summary} />
            </div>
            <div className="grid gap-4 lg:grid-cols-[0.85fr_1.15fr]">
              <DomainSpreadPanel topDomains={topDomains} totalSurfaceCount={summary.surface_count} />
              <CurrentScreenFocusPanel screen={activeScreen} />
            </div>
          </TabsContent>

          <TabsContent value="repo-map" className="mt-0 space-y-5" data-testid="dashboard-content-repo-map">
            <RepoNavigationPanel />
          </TabsContent>

          <TabsContent value="live-ops" className="mt-0 space-y-5" data-testid="dashboard-content-live-ops">
            <AureonGeneratedOperationalConsole />
            <RuntimeMirrorPanel runtime={runtime} statusLines={statusLines} />
          </TabsContent>

          <TabsContent value="coding" className="mt-0 space-y-5" data-testid="dashboard-content-coding">
            <AureonCodingOrganismConsole />
            <AureonCodingAgentSkillBaseConsole />
            <AureonDirectorCapabilityBridgeConsole />
          </TabsContent>

          <TabsContent value="trading" className="mt-0 space-y-5" data-testid="dashboard-content-trading">
            <SecurityBlockerLane
              title="Trading Blockers"
              description="Live order, credential, and exchange-mutation boundaries remain visible here."
              blockers={tradingSecurityBlockers}
              filter={blockerFilter}
              onFilterChange={setBlockerFilter}
            />
            <AureonGoldCapitalIntelligenceConsole
              runtimeGoldProof={runtime.goldRuntimeTradeProof}
              runtimeConnected={runtime.connected}
              runtimeClearancePending={runtime.clearancePending}
              runtimeStaleReason={runtime.staleReason}
            />
            <CapitalThreePMissionPanel
              ecosystem={capitalEcosystemIntelligence}
              revenue={capitalRevenueLogicStressAudit}
              liveGate={capitalRevenueLiveGateReadinessAudit}
              liveDry={capitalLiveDryStressAudit}
            />
            <CapitalThreePLiveExecutionCertificationPanel audit={capitalThreePLiveExecutionCertificationAudit} />
            <CapitalThreePBlockerBurndownPanel audit={capitalThreePBlockerBurndownAudit} />
            <PerformanceReadinessPanel audit={performanceReadinessAudit} />
            <AureonMurgeUnityPanel bridge={aureonMurgeUnityBridge} />
            <AureonMurgeRuntimeActivationPanel audit={aureonMurgeRuntimeActivation} />
            <ParallelTradingSystemsPanel unity={parallelStrategyUnity} stress={parallelStrategyUnityStressAudit} />
            <SwarmSearchMappingPanel audit={swarmSearchMappingStressAudit} />
            <LiveSignalFabricPanel fabric={liveTradeSignalFabric} stress={liveTradeSignalFabricStressAudit} audit={liveGoalTradeAudit} />
            <CapitalEcosystemIntelligencePanel ecosystem={capitalEcosystemIntelligence} />
            <CapitalRevenueLogicStressPanel audit={capitalRevenueLogicStressAudit} />
            <CapitalRevenueLiveGateReadinessPanel audit={capitalRevenueLiveGateReadinessAudit} />
            <CapitalLiveDryStressPanel audit={capitalLiveDryStressAudit} />
            <LiveGoalTradeAuditPanel audit={liveGoalTradeAudit} runtime={runtime} />
            <OrderLifecyclePanel audit={liveGoalTradeAudit} runtime={runtime} />
            <OrderLifecycleStressPanel stressAudit={orderLifecycleStressAudit} audit={liveGoalTradeAudit} />
            {tradingScreen ? (
              <ScreenPanel
                screen={tradingScreen}
                inventory={inventory}
                surfaceQuery={surfaceQuery}
                surfaceFilter={surfaceFilter}
              />
            ) : null}
            <GlobalFinancialCoveragePanel coverage={globalCoverageMap} />
            <ExchangeDataCapabilityMatrixPanel matrix={exchangeDataMatrix} />
            <ExchangeMonitoringChecklistPanel checklist={exchangeChecklist} />
            <TradingIntelligenceChecklistPanel checklist={tradingChecklist} />
          </TabsContent>

          <TabsContent value="security" className="mt-0 space-y-5" data-testid="dashboard-content-security">
            <SecurityBlockerLane
              title="Security And Authority Blockers"
              description="Use these filters to separate credential, runtime, stale, and critical review work."
              blockers={filteredSecurityBlockers}
              filter={blockerFilter}
              onFilterChange={setBlockerFilter}
            />
            <SaaSCredentialManagementPanel comparison={hncSecurityComparison} />
            {securityScreen ? (
              <ScreenPanel
                screen={securityScreen}
                inventory={inventory}
                surfaceQuery={surfaceQuery}
                surfaceFilter={surfaceFilter}
              />
            ) : null}
            <SafetyBoundariesPanel manualActions={manualActions} percent={percent} summary={summary} />
          </TabsContent>

          <TabsContent value="inventory" className="mt-0 space-y-5" data-testid="dashboard-content-inventory">
            <FilterHeader
              title="Work Order Filters"
              description="Keep the migration queue scannable by status or by the selected screen."
            >
              <FilterButtons options={workOrderFilterOptions} value={workOrderFilter} onChange={(value) => setWorkOrderFilter(value)} />
            </FilterHeader>
            <FrontendEvolutionPanel evolution={evolution} filter={workOrderFilter} activeScreenId={active} />
            <AureonWorkOrderExecutionConsole />
            <ScreenTabsPanel
              screens={screens}
              active={active}
              onActiveChange={setActive}
              inventory={inventory}
              surfaceQuery={surfaceQuery}
              onSurfaceQueryChange={setSurfaceQuery}
              surfaceFilter={surfaceFilter}
              onSurfaceFilterChange={setSurfaceFilter}
            />
            <div className="grid gap-4 lg:grid-cols-[0.85fr_1.15fr]">
              <DomainSpreadPanel topDomains={topDomains} totalSurfaceCount={summary.surface_count} />
              <CurrentScreenFocusPanel screen={activeScreen} />
            </div>
          </TabsContent>

          <TabsContent value="agents" className="mt-0 space-y-5" data-testid="dashboard-content-agents">
            <AureonAgentCompanyConsole />
            <CapabilitySwitchboardPanel switchboard={switchboard} />
            <AureonDirectorCapabilityBridgeConsole />
          </TabsContent>

          <TabsContent value="evidence" className="mt-0 space-y-5" data-testid="dashboard-content-evidence">
            <EvidencePanel
              state={state}
              runtime={runtime}
              filter={evidenceFilter}
              onFilterChange={setEvidenceFilter}
            />
            <AureonWorkOrderExecutionConsole />
            <AureonDirectorCapabilityBridgeConsole />
          </TabsContent>
        </Tabs>

        <div className="mt-5 text-xs text-muted-foreground">
          Sources: {state?.inventorySource || "pending"}, {state?.planSource || "pending"}, {state?.organismSource || "pending"}, {state?.evolutionSource || "pending"}, and {state?.switchboardSource || "pending"}. Generated screens: {formatCompact(planSummary.screen_count)}. Readiness signal: {percent}%.
        </div>
      </main>
    </div>
  );
}

function DashboardStatusBanner({
  tab,
  runtime,
  securityBlockers,
  blindSpotCount,
  percent,
}: {
  tab: DashboardTabConfig;
  runtime: RuntimeObservation;
  securityBlockers: number;
  blindSpotCount: number;
  percent: number;
}) {
  const Icon = tab.icon;
  return (
    <Card className="bg-card/80">
      <CardContent className="grid gap-4 p-4 lg:grid-cols-[1fr_1.2fr]">
        <div className="flex min-w-0 items-start gap-3">
          <div className="rounded-md border border-border/50 bg-muted/20 p-2">
            <Icon className="h-5 w-5 text-primary" />
          </div>
          <div className="min-w-0">
            <div className="text-lg font-semibold">{tab.title}</div>
            <p className="mt-1 text-sm text-muted-foreground">{tab.summary}</p>
          </div>
        </div>
        <div className="grid gap-2 sm:grid-cols-4">
          <div className="rounded-md border border-border/40 bg-muted/10 p-3">
            <div className="text-[11px] uppercase text-muted-foreground">runtime</div>
            <div className="mt-1 truncate text-sm font-semibold">
              {runtime.connected ? (runtime.clearancePending ? "checking" : "live") : "offline"}
            </div>
          </div>
          <div className="rounded-md border border-border/40 bg-muted/10 p-3">
            <div className="text-[11px] uppercase text-muted-foreground">blockers</div>
            <div className="mt-1 text-sm font-semibold">{formatCompact(securityBlockers)}</div>
          </div>
          <div className="rounded-md border border-border/40 bg-muted/10 p-3">
            <div className="text-[11px] uppercase text-muted-foreground">blind spots</div>
            <div className="mt-1 text-sm font-semibold">{formatCompact(blindSpotCount)}</div>
          </div>
          <div className="rounded-md border border-border/40 bg-muted/10 p-3">
            <div className="text-[11px] uppercase text-muted-foreground">readiness</div>
            <div className="mt-1 text-sm font-semibold">{percent}%</div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

type FreshnessStatus = "fresh" | "attention" | "stale" | "missing";

interface FreshnessItem {
  id: string;
  label: string;
  status: FreshnessStatus;
  ageSeconds: number | null;
  ageLabel: string;
  cadence: string;
  source: string;
  detail: string;
}

function formatCadence(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  const seconds = ms / 1000;
  return Number.isInteger(seconds) ? `${seconds}s` : `${seconds.toFixed(1)}s`;
}

function timestampAgeSeconds(timestamp?: string | number, nowMs = Date.now()): number | null {
  if (timestamp === undefined || timestamp === null || timestamp === "") return null;
  const parsed = typeof timestamp === "number" ? timestamp : Date.parse(String(timestamp));
  if (!Number.isFinite(parsed)) return null;
  const ms = typeof timestamp === "number" && timestamp < 10_000_000_000 ? timestamp * 1000 : parsed;
  return Math.max(0, Math.round((nowMs - ms) / 1000));
}

function formatFreshnessAge(seconds: number | null): string {
  if (seconds === null || seconds === undefined || seconds < 0) return "unknown";
  if (seconds < 60) return `${Math.round(seconds)}s`;
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
  if (seconds < 86400) return `${Math.round(seconds / 3600)}h`;
  return `${Math.round(seconds / 86400)}d`;
}

function statusFromAge(ageSeconds: number | null, freshSeconds: number, staleSeconds: number): FreshnessStatus {
  if (ageSeconds === null) return "missing";
  if (ageSeconds <= freshSeconds) return "fresh";
  if (ageSeconds <= staleSeconds) return "attention";
  return "stale";
}

function freshnessStatusFromText(statusText?: string, fallback: FreshnessStatus = "attention"): FreshnessStatus {
  const text = String(statusText || "").toLowerCase();
  if (!text) return fallback;
  if (text.includes("missing") || text.includes("offline") || text.includes("unavailable") || text.includes("broken")) return "missing";
  if (text.includes("stale")) return "stale";
  if (text.includes("attention") || text.includes("blocked") || text.includes("blind") || text.includes("checking")) return "attention";
  if (text.includes("fresh") || text.includes("ready") || text.includes("connected") || text.includes("complete")) return "fresh";
  return fallback;
}

function addFreshnessItem(
  items: FreshnessItem[],
  item: Omit<FreshnessItem, "ageLabel">,
) {
  items.push({
    ...item,
    ageLabel: formatFreshnessAge(item.ageSeconds),
  });
}

function buildFreshnessItems({
  state,
  runtime,
  tradingChecklist,
  exchangeChecklist,
  exchangeDataMatrix,
  globalCoverageMap,
  hncSecurityComparison,
  liveGoalTradeAudit,
  orderLifecycleStressAudit,
  capitalRevenueLogicStressAudit,
  capitalRevenueLiveGateReadinessAudit,
  capitalThreePLiveExecutionCertificationAudit,
  capitalThreePBlockerBurndownAudit,
  performanceReadinessAudit,
  aureonMurgeUnityBridge,
  aureonMurgeRuntimeActivation,
  liveTradeSignalFabric,
  liveTradeSignalFabricStressAudit,
  swarmSearchMappingStressAudit,
  parallelStrategyUnity,
  parallelStrategyUnityStressAudit,
  now,
}: {
  state: UnifiedFrontendState | null;
  runtime: RuntimeObservation;
  tradingChecklist: TradingIntelligenceChecklist | null;
  exchangeChecklist: ExchangeMonitoringChecklist | null;
  exchangeDataMatrix: ExchangeDataCapabilityMatrix | null;
  globalCoverageMap: GlobalFinancialCoverageMap | null;
  hncSecurityComparison: HNCPacketSecurityComparison | null;
  liveGoalTradeAudit: LiveGoalTradeAudit | null;
  orderLifecycleStressAudit: OrderLifecycleStressAudit | null;
  capitalRevenueLogicStressAudit: CapitalRevenueLogicStressAudit | null;
  capitalRevenueLiveGateReadinessAudit: CapitalRevenueLiveGateReadinessAudit | null;
  capitalThreePLiveExecutionCertificationAudit: CapitalThreePLiveExecutionCertificationAudit | null;
  capitalThreePBlockerBurndownAudit: CapitalThreePBlockerBurndownAudit | null;
  performanceReadinessAudit: PerformanceReadinessAudit | null;
  aureonMurgeUnityBridge: AureonMurgeUnityBridge | null;
  aureonMurgeRuntimeActivation: AureonMurgeRuntimeActivationStressAudit | null;
  liveTradeSignalFabric: LiveTradeSignalFabric | null;
  liveTradeSignalFabricStressAudit: LiveTradeSignalFabricStressAudit | null;
  swarmSearchMappingStressAudit: SwarmSearchMappingStressAudit | null;
  parallelStrategyUnity: ParallelStrategyUnity | null;
  parallelStrategyUnityStressAudit: ParallelStrategyUnityStressAudit | null;
  now: number;
}): FreshnessItem[] {
  const items: FreshnessItem[] = [];
  const runtimeAge = timestampAgeSeconds(runtime.generatedAt, now);
  const runtimeStatus: FreshnessStatus = runtime.connected
    ? runtime.clearancePending
      ? "attention"
      : statusFromAge(runtimeAge, 10, 45)
    : "missing";
  addFreshnessItem(items, {
    id: "runtime-feed",
    label: "Runtime feed",
    status: runtimeStatus,
    ageSeconds: runtimeAge,
    cadence: formatCadence(RUNTIME_REFRESH_MS),
    source: runtime.endpoint || "terminal-state endpoint",
    detail: runtime.connected ? "Live terminal-state mirror for action posture." : "Dashboard is showing manifests until the runtime feed returns.",
  });

  const addManifest = (
    id: string,
    label: string,
    generatedAt: string | undefined,
    statusText: string | undefined,
    source: string,
    cadenceMs: number,
    freshSeconds = 120,
    staleSeconds = 900,
  ) => {
    const ageSeconds = timestampAgeSeconds(generatedAt, now);
    const ageStatus = statusFromAge(ageSeconds, freshSeconds, staleSeconds);
    const textStatus = freshnessStatusFromText(statusText, ageStatus);
    const status = textStatus === "missing" ? "missing" : ageStatus === "fresh" && textStatus === "attention" ? "attention" : ageStatus;
    addFreshnessItem(items, {
      id,
      label,
      status,
      ageSeconds,
      cadence: formatCadence(cadenceMs),
      source,
      detail: statusText || "manifest loaded",
    });
  };

  addManifest("inventory", "SaaS inventory", state?.inventory.generated_at, state?.inventory.status, state?.inventorySource || "inventory manifest", MANIFEST_REFRESH_MS, 240, 1800);
  addManifest("frontend-plan", "Frontend plan", state?.plan.generated_at, state?.plan.status, state?.planSource || "frontend plan", MANIFEST_REFRESH_MS, 240, 1800);
  addManifest("organism-pulse", "Organism pulse", state?.organism.generated_at, state?.organism.status, state?.organismSource || "organism runtime", MANIFEST_REFRESH_MS, 60, 600);
  addManifest("evolution-queue", "Evolution queue", state?.evolution.generated_at, state?.evolution.status, state?.evolutionSource || "evolution queue", MANIFEST_REFRESH_MS, 240, 1800);
  addManifest("capability-switchboard", "Capability switchboard", state?.switchboard.generated_at, state?.switchboard.status, state?.switchboardSource || "switchboard", MANIFEST_REFRESH_MS, 240, 1800);
  addManifest("trading-intelligence", "Trading intelligence", tradingChecklist?.generated_at, tradingChecklist?.status, "/aureon_trading_intelligence_checklist.json", FAST_PANEL_REFRESH_MS, 20, 90);
  addManifest("exchange-monitoring", "Exchange monitoring", exchangeChecklist?.generated_at, exchangeChecklist?.status, "/aureon_exchange_monitoring_checklist.json", FAST_PANEL_REFRESH_MS, 20, 90);
  addManifest("exchange-matrix", "Exchange matrix", exchangeDataMatrix?.generated_at, exchangeDataMatrix?.status, "/aureon_exchange_data_capability_matrix.json", MARKET_PANEL_REFRESH_MS, 30, 120);
  addManifest("global-coverage", "Financial coverage", globalCoverageMap?.generated_at, globalCoverageMap?.status, "/aureon_global_financial_coverage_map.json", MARKET_PANEL_REFRESH_MS, 60, 300);
  addManifest("live-goal-trade", "Live goal trade audit", liveGoalTradeAudit?.generated_at, liveGoalTradeAudit?.status, "/aureon_live_goal_trade_audit.json", FAST_PANEL_REFRESH_MS, 20, 90);
  addManifest("order-lifecycle-stress", "Lifecycle stress certification", orderLifecycleStressAudit?.generated_at, orderLifecycleStressAudit?.status, "/aureon_order_lifecycle_stress_audit.json", FAST_PANEL_REFRESH_MS, 60, 900);
  addManifest("capital-revenue-logic", "Capital revenue logic stress", capitalRevenueLogicStressAudit?.generated_at, capitalRevenueLogicStressAudit?.status, "/aureon_capital_revenue_logic_stress_audit.json", FAST_PANEL_REFRESH_MS, 20, 120);
  addManifest("capital-revenue-live-gate", "Capital live-gate readiness", capitalRevenueLiveGateReadinessAudit?.generated_at, capitalRevenueLiveGateReadinessAudit?.status, "/aureon_capital_revenue_live_gate_readiness_audit.json", FAST_PANEL_REFRESH_MS, 20, 120);
  addManifest("capital-3p-live-execution", "Capital 3p execution certification", capitalThreePLiveExecutionCertificationAudit?.generated_at, capitalThreePLiveExecutionCertificationAudit?.status, "/aureon_capital_3p_live_execution_certification_audit.json", FAST_PANEL_REFRESH_MS, 20, 120);
  addManifest("capital-3p-blocker-burndown", "Capital 3p blocker burn-down", capitalThreePBlockerBurndownAudit?.generated_at, capitalThreePBlockerBurndownAudit?.status, "/aureon_capital_3p_blocker_burndown_audit.json", FAST_PANEL_REFRESH_MS, 20, 120);
  addManifest("performance-readiness", "Performance readiness", performanceReadinessAudit?.generated_at, performanceReadinessAudit?.status, "/aureon_performance_readiness_audit.json", FAST_PANEL_REFRESH_MS, 60, 900);
  addManifest("aureon-murge-unity", "MURGE unity bridge", aureonMurgeUnityBridge?.generated_at, aureonMurgeUnityBridge?.status, "/aureon_murge_unity_bridge.json", MANIFEST_REFRESH_MS, 120, 1800);
  addManifest("aureon-murge-runtime-activation", "MURGE runtime activation", aureonMurgeRuntimeActivation?.generated_at, aureonMurgeRuntimeActivation?.status, "/aureon_murge_runtime_activation_stress_audit.json", FAST_PANEL_REFRESH_MS, 20, 180);
  addManifest("live-signal-fabric", "Live signal fabric", liveTradeSignalFabric?.generated_at, liveTradeSignalFabric?.status, "/aureon_live_trade_signal_fabric.json", FAST_PANEL_REFRESH_MS, 10, 120);
  addManifest("live-signal-fabric-stress", "Live signal fabric stress", liveTradeSignalFabricStressAudit?.generated_at, liveTradeSignalFabricStressAudit?.status, "/aureon_live_trade_signal_fabric_stress_audit.json", FAST_PANEL_REFRESH_MS, 10, 120);
  addManifest("swarm-search-mapping", "Swarm search mapping", swarmSearchMappingStressAudit?.generated_at, swarmSearchMappingStressAudit?.status, "/aureon_swarm_search_mapping_stress_audit.json", FAST_PANEL_REFRESH_MS, 30, 300);
  addManifest("parallel-strategy-unity", "Parallel strategy unity", parallelStrategyUnity?.generated_at, parallelStrategyUnity?.status, "/aureon_parallel_strategy_unity.json", FAST_PANEL_REFRESH_MS, 10, 120);
  addManifest("parallel-strategy-unity-stress", "Parallel strategy stress", parallelStrategyUnityStressAudit?.generated_at, parallelStrategyUnityStressAudit?.status, "/aureon_parallel_strategy_unity_stress_audit.json", FAST_PANEL_REFRESH_MS, 10, 120);
  addManifest("hnc-security", "HNC security", hncSecurityComparison?.generated_at, hncSecurityComparison?.status, "/hnc_packet_security_comparison.json", MANIFEST_REFRESH_MS, 3600, 86400);

  (state?.organism.domains || []).slice(0, 16).forEach((domain) => {
    const ageSeconds = domain.age_seconds ?? timestampAgeSeconds(domain.generated_at, now);
    addFreshnessItem(items, {
      id: `domain-${domain.id}`,
      label: domain.label || domain.domain || domain.id,
      status: freshnessStatusFromText(domain.status, statusFromAge(ageSeconds, 300, 3600)),
      ageSeconds,
      cadence: "observer",
      source: domain.source_path || "organism domain",
      detail: domain.next_action || domain.display_state || domain.freshness || "domain pulse",
    });
  });

  const rank: Record<FreshnessStatus, number> = { missing: 0, stale: 1, attention: 2, fresh: 3 };
  return items.sort((a, b) => {
    const byStatus = rank[a.status] - rank[b.status];
    if (byStatus !== 0) return byStatus;
    return asNumber(b.ageSeconds) - asNumber(a.ageSeconds);
  });
}

function OperatorBriefingPanel({
  tab,
  runtime,
  organism,
  freshnessItems,
  securityBlockers,
  blindSpotCount,
  percent,
  loading,
  onRefresh,
}: {
  tab: DashboardTabConfig;
  runtime: RuntimeObservation;
  organism: UnifiedFrontendState["organism"];
  freshnessItems: FreshnessItem[];
  securityBlockers: number;
  blindSpotCount: number;
  percent: number;
  loading: boolean;
  onRefresh: () => void;
}) {
  const Icon = tab.icon;
  const freshCount = freshnessItems.filter((item) => item.status === "fresh").length;
  const attentionCount = freshnessItems.filter((item) => item.status === "attention").length;
  const staleCount = freshnessItems.filter((item) => item.status === "stale" || item.status === "missing").length;
  const visibleFreshness = freshnessItems.slice(0, 8);
  const nextAction =
    organism.next_actions?.[0] ||
    runtime.statusLines.find((line) => line.trim()) ||
    "Watch the selected tab, then use the prompt lane or evidence links for the next client job.";
  const runtimePhrase = runtime.connected
    ? runtime.clearancePending
      ? "Runtime is reachable but still checking gates."
      : "Runtime feed is live."
    : "Runtime feed is offline; manifest evidence is still visible.";
  const blockerPhrase = securityBlockers
    ? `${securityBlockers} authority blocker(s) need review before unsafe controls can appear.`
    : "No security blockers are reported in the loaded inventory.";

  return (
    <section data-testid="operator-briefing" className="grid gap-4 xl:grid-cols-[0.95fr_1.05fr]">
      <Card className="border-primary/20 bg-primary/5">
        <CardHeader className="pb-3">
          <CardTitle className="flex flex-col gap-3 text-base md:flex-row md:items-center md:justify-between">
            <span className="flex items-center gap-2">
              <Icon className="h-4 w-4 text-primary" />
              Operator Brief
            </span>
            <div className="flex flex-wrap gap-2">
              <Pill label={`view ${tab.title}`} tone="border-primary/30 bg-primary/10 text-primary" />
              <Pill label={`${percent}% ready`} tone={percent >= 80 ? statusTone.wired : statusTone.partial} />
              <Pill label={`${freshCount}/${Math.max(1, freshnessItems.length)} fresh`} tone={staleCount ? statusTone.orphaned : statusTone.wired} />
            </div>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-3 md:grid-cols-3">
            <div className="rounded-md border border-border/40 bg-black/20 p-3">
              <div className="flex items-center gap-2 text-[11px] uppercase text-muted-foreground">
                <Radio className="h-3.5 w-3.5" />
                runtime
              </div>
              <div className="mt-1 text-sm font-semibold">{runtime.connected ? (runtime.clearancePending ? "checking" : "live") : "offline"}</div>
              <div className="mt-1 text-[11px] text-muted-foreground">{runtime.generatedAt ? `${formatFreshnessAge(timestampAgeSeconds(runtime.generatedAt))} old` : "no timestamp"}</div>
            </div>
            <div className="rounded-md border border-border/40 bg-black/20 p-3">
              <div className="flex items-center gap-2 text-[11px] uppercase text-muted-foreground">
                <AlertTriangle className="h-3.5 w-3.5" />
                blockers
              </div>
              <div className="mt-1 text-sm font-semibold">{formatCompact(securityBlockers)}</div>
              <div className="mt-1 text-[11px] text-muted-foreground">{formatCompact(blindSpotCount)} blind spots visible</div>
            </div>
            <div className="rounded-md border border-border/40 bg-black/20 p-3">
              <div className="flex items-center gap-2 text-[11px] uppercase text-muted-foreground">
                <Clock className="h-3.5 w-3.5" />
                refresh cadence
              </div>
              <div className="mt-1 text-sm font-semibold">runtime {formatCadence(RUNTIME_REFRESH_MS)}</div>
              <div className="mt-1 text-[11px] text-muted-foreground">panels {formatCadence(FAST_PANEL_REFRESH_MS)} / manifests {formatCadence(MANIFEST_REFRESH_MS)}</div>
            </div>
          </div>

          <div className="rounded-md border border-border/50 bg-black/25 p-3 text-sm leading-6 text-foreground/90">
            <p>{runtimePhrase}</p>
            <p>{blockerPhrase}</p>
            <p>Next action: {nextAction}</p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <Button type="button" onClick={onRefresh} variant="outline" size="sm" disabled={loading}>
              <RefreshCcw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />
              Refresh evidence
            </Button>
            <Pill label="read-only gates preserved" tone="border-success/30 bg-success/10 text-success" />
            <Pill label="no hidden mutation controls" tone="border-warning/30 bg-warning/10 text-warning" />
          </div>
        </CardContent>
      </Card>

      <Card data-testid="data-freshness-panel" className="bg-card/85">
        <CardHeader className="pb-3">
          <CardTitle className="flex flex-col gap-3 text-base md:flex-row md:items-center md:justify-between">
            <span className="flex items-center gap-2">
              <Gauge className="h-4 w-4 text-primary" />
              Data Freshness
            </span>
            <div className="flex flex-wrap gap-2">
              <Pill label={`${freshCount} fresh`} tone={statusTone.wired} />
              <Pill label={`${attentionCount} attention`} tone="border-warning/30 bg-warning/10 text-warning" />
              <Pill label={`${staleCount} stale/offline`} tone={staleCount ? statusTone.security_blocker : "border-border bg-muted/20 text-muted-foreground"} />
            </div>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-2 md:grid-cols-2">
            {visibleFreshness.map((item) => (
              <div key={item.id} className="min-w-0 rounded-md border border-border/40 bg-muted/10 p-3">
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <div className="truncate text-sm font-semibold">{item.label}</div>
                    <div className="mt-1 truncate font-mono text-[11px] text-muted-foreground">{item.source}</div>
                  </div>
                  <Pill label={item.status} tone={freshnessTone(item.status)} />
                </div>
                <div className="mt-2 flex flex-wrap gap-2 text-[11px] text-muted-foreground">
                  <span>age {item.ageLabel}</span>
                  <span>cadence {item.cadence}</span>
                </div>
                <div className="mt-1 line-clamp-2 text-xs text-muted-foreground">{item.detail}</div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </section>
  );
}

function FilterButtons<T extends string>({
  options,
  value,
  onChange,
}: {
  options: Array<{ id: T; label: string }>;
  value: T;
  onChange: (value: T) => void;
}) {
  return (
    <div className="flex flex-wrap gap-1">
      {options.map((option) => (
        <Button
          key={option.id}
          type="button"
          variant={value === option.id ? "secondary" : "ghost"}
          size="sm"
          className="h-8 px-2 text-xs"
          onClick={() => onChange(option.id)}
        >
          {option.label}
        </Button>
      ))}
    </div>
  );
}

function FilterHeader({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children: ReactNode;
}) {
  return (
    <Card className="bg-card/80">
      <CardContent className="flex flex-col gap-3 p-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <div className="text-sm font-semibold">{title}</div>
          <div className="mt-1 text-xs text-muted-foreground">{description}</div>
        </div>
        {children}
      </CardContent>
    </Card>
  );
}

function blockerSearchText(blocker: SecurityBlockerWorkOrder): string {
  return [
    blocker.title,
    blocker.workOrder,
    blocker.sourcePath,
    blocker.target,
    blocker.priority,
    blocker.status,
    blocker.reason,
    blocker.nextStep,
    ...blocker.boundaries,
  ]
    .join(" ")
    .toLowerCase();
}

function matchesBlockerFilter(blocker: SecurityBlockerWorkOrder, filter: BlockerFilter): boolean {
  const text = blockerSearchText(blocker);
  if (filter === "critical") return blocker.priority.toUpperCase() === "P100";
  if (filter === "security") return text.includes("security") || text.includes("credential") || text.includes("kyc");
  if (filter === "runtime") return text.includes("runtime") || text.includes("trading") || text.includes("order") || text.includes("live");
  if (filter === "stale") return text.includes("stale") || text.includes("legacy") || text.includes("review");
  return true;
}

function SecurityBlockerLane({
  title,
  description,
  blockers,
  filter,
  onFilterChange,
  maxItems,
}: {
  title: string;
  description: string;
  blockers: SecurityBlockerWorkOrder[];
  filter: BlockerFilter;
  onFilterChange: (value: BlockerFilter) => void;
  maxItems?: number;
}) {
  const visible = maxItems ? blockers.slice(0, maxItems) : blockers;
  return (
    <section className="space-y-3">
      <FilterHeader title={title} description={`${description} Showing ${visible.length}/${blockers.length}.`}>
        <FilterButtons options={blockerFilterOptions} value={filter} onChange={onFilterChange} />
      </FilterHeader>
      {visible.length ? (
        <div className="space-y-3">
          {visible.map((blocker) => (
            <SecurityBlockerCard key={`${blocker.target}-${blocker.sourcePath}`} blocker={blocker} />
          ))}
        </div>
      ) : (
        <Card className="bg-card/80">
          <CardContent className="p-4 text-sm text-muted-foreground">No blockers match the current filter.</CardContent>
        </Card>
      )}
    </section>
  );
}

function RuntimeMirrorPanel({
  runtime,
  statusLines,
}: {
  runtime: RuntimeObservation;
  statusLines: string[];
}) {
  return (
    <Card className="bg-card/80">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <Radio className="h-4 w-4 text-primary" />
          Runtime Mirror
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
          {(runtime.metrics.length ? runtime.metrics : [
            { label: "portfolio", value: "offline" },
            { label: "open positions", value: "offline" },
            { label: "trades", value: "offline" },
            { label: "mode", value: "observe" },
          ]).map((metric) => (
            <div key={metric.label} className="rounded-md border border-border/40 bg-muted/10 p-3">
              <div className="text-[11px] uppercase text-muted-foreground">{metric.label}</div>
              <div className="mt-1 truncate font-mono text-sm font-semibold">{metric.value}</div>
            </div>
          ))}
        </div>
        <div className="flex flex-wrap gap-2">
          <Pill label={runtime.connected ? (runtime.clearancePending ? "connected checking" : "connected clear") : "offline"} tone={runtime.connected ? (runtime.clearancePending ? statusTone.orphaned : statusTone.wired) : statusTone.partial} />
          <Pill label={runtime.generatedAt ? `updated ${new Date(runtime.generatedAt).toLocaleTimeString()}` : "no runtime timestamp"} tone="border-border bg-muted/20 text-muted-foreground" />
          {runtime.endpoint ? <Pill label={runtime.endpoint.replace("http://127.0.0.1:", "")} tone="border-primary/30 bg-primary/10 text-primary" /> : null}
          {runtime.clearances.map((clearance) => (
            <Pill key={clearance} label={clearance} tone={statusTone.security_blocker} />
          ))}
        </div>
        {runtime.details.length ? (
          <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
            {runtime.details.map((detail) => (
              <div key={detail.label} className="rounded-md border border-border/40 bg-muted/10 p-3">
                <div className="text-[11px] uppercase text-muted-foreground">{detail.label}</div>
                <div className="mt-1 truncate font-mono text-sm font-semibold">{detail.value}</div>
              </div>
            ))}
          </div>
        ) : null}
        <div className="rounded-md border border-border/50 bg-black/35 p-3">
          {statusLines.length ? (
            <pre className="max-h-52 overflow-auto whitespace-pre-wrap font-mono text-[11px] leading-5 text-foreground">
              {statusLines.slice(-24).join("\n")}
            </pre>
          ) : (
            <div className="font-mono text-[11px] text-muted-foreground">Waiting for runtime status...</div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function SafetyBoundariesPanel({
  manualActions,
  percent,
  summary,
}: {
  manualActions: Array<[string, unknown]>;
  percent: number;
  summary: SaaSInventorySummary;
}) {
  return (
    <Card className="bg-card/80">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <Lock className="h-4 w-4 text-primary" />
          Safety And Manual Boundaries
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          {manualActions.map(([key]) => (
            <div key={key} className="flex items-center justify-between gap-3 rounded-md border border-border/40 bg-muted/10 px-3 py-2">
              <span className="text-sm">{key.replace(/_/g, " ")}</span>
              <Badge variant="outline">visible</Badge>
            </div>
          ))}
          {!manualActions.length ? <div className="text-sm text-muted-foreground">No manual boundary manifest is loaded yet.</div> : null}
        </div>
        <div>
          <div className="mb-2 flex items-center justify-between text-xs text-muted-foreground">
            <span>Inventory readiness</span>
            <span>{percent}%</span>
          </div>
          <Progress value={percent} className="h-2" />
        </div>
        <div className="grid grid-cols-2 gap-2 text-sm">
          <div className="rounded-md border border-border/40 bg-muted/10 p-3">
            <div className="text-xs text-muted-foreground">orphaned frontend</div>
            <div className="mt-1 text-lg font-semibold">{formatCompact(summary.orphaned_frontend_count)}</div>
          </div>
          <div className="rounded-md border border-border/40 bg-muted/10 p-3">
            <div className="text-xs text-muted-foreground">uncalled functions</div>
            <div className="mt-1 text-lg font-semibold">{formatCompact(summary.uncalled_supabase_function_count)}</div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function DomainSpreadPanel({
  topDomains,
  totalSurfaceCount,
}: {
  topDomains: Array<[string, unknown]>;
  totalSurfaceCount: unknown;
}) {
  return (
    <Card className="bg-card/80">
      <CardHeader className="pb-3">
        <CardTitle className="text-base">Domain Spread</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {topDomains.map(([domain, count]) => {
          const width = Math.min(100, Math.round((asNumber(count) / Math.max(1, asNumber(totalSurfaceCount))) * 100));
          return (
            <div key={domain}>
              <div className="mb-1 flex items-center justify-between text-xs">
                <span className="capitalize text-muted-foreground">{domain.replace(/_/g, " ")}</span>
                <span className="font-mono">{String(count)}</span>
              </div>
              <div className="h-2 overflow-hidden rounded bg-muted/30">
                <div className="h-full bg-primary" style={{ width: `${Math.max(4, width)}%` }} />
              </div>
            </div>
          );
        })}
        {!topDomains.length ? <div className="text-sm text-muted-foreground">Domain counts are not loaded yet.</div> : null}
      </CardContent>
    </Card>
  );
}

function CurrentScreenFocusPanel({ screen }: { screen?: FrontendScreenPlan }) {
  return (
    <Card className="bg-card/80">
      <CardHeader className="pb-3">
        <CardTitle className="text-base">Current Screen Focus</CardTitle>
      </CardHeader>
      <CardContent>
        {screen ? (
          <div className="space-y-4">
            <div>
              <div className="text-lg font-semibold">{screen.title}</div>
              <p className="mt-1 text-sm text-muted-foreground">{screen.goal}</p>
            </div>
            <div className="grid gap-3 md:grid-cols-3">
              <div className="rounded-md border border-border/40 bg-muted/10 p-3">
                <div className="text-xs text-muted-foreground">source surfaces</div>
                <div className="mt-1 text-lg font-semibold">{screen.source_surface_count}</div>
              </div>
              <div className="rounded-md border border-border/40 bg-muted/10 p-3">
                <div className="text-xs text-muted-foreground">backend functions</div>
                <div className="mt-1 text-lg font-semibold">{screen.backend_functions.length}</div>
              </div>
              <div className="rounded-md border border-border/40 bg-muted/10 p-3">
                <div className="text-xs text-muted-foreground">missing items</div>
                <div className="mt-1 text-lg font-semibold">{screen.missing_capabilities.length}</div>
              </div>
            </div>
          </div>
        ) : (
          <div className="text-sm text-muted-foreground">No screen plan available.</div>
        )}
      </CardContent>
    </Card>
  );
}

function ScreenTabsPanel({
  screens,
  active,
  onActiveChange,
  inventory,
  surfaceQuery,
  onSurfaceQueryChange,
  surfaceFilter,
  onSurfaceFilterChange,
}: {
  screens: FrontendScreenPlan[];
  active: string;
  onActiveChange: (value: string) => void;
  inventory: SaaSInventoryManifest;
  surfaceQuery: string;
  onSurfaceQueryChange: (value: string) => void;
  surfaceFilter: SurfaceFilter;
  onSurfaceFilterChange: (value: SurfaceFilter) => void;
}) {
  if (!screens.length) {
    return (
      <Card className="bg-card/80">
        <CardContent className="p-4 text-sm text-muted-foreground">No screen plan is loaded yet.</CardContent>
      </Card>
    );
  }

  return (
    <section className="space-y-4">
      <FilterHeader
        title="Source Surface Filters"
        description="Search and narrow screen surfaces by boundary or wiring state."
      >
        <div className="flex w-full flex-col gap-2 lg:w-auto lg:min-w-[560px] lg:flex-row lg:items-center lg:justify-end">
          <div className="relative w-full lg:max-w-[280px]">
            <Search className="pointer-events-none absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              value={surfaceQuery}
              onChange={(event) => onSurfaceQueryChange(event.target.value)}
              placeholder="Search paths, domains, boundaries..."
              className="h-9 pl-8"
            />
          </div>
          <FilterButtons options={surfaceFilterOptions} value={surfaceFilter} onChange={onSurfaceFilterChange} />
        </div>
      </FilterHeader>

      <Tabs value={active} onValueChange={onActiveChange}>
        <ScrollArea className="w-full">
          <TabsList className="mb-4 h-auto min-w-max justify-start gap-1 bg-card/80 p-1">
            {screens.map((screen) => {
              const Icon = screenIcons[screen.id] || Activity;
              const missing = screen.missing_capabilities?.length || 0;
              return (
                <TabsTrigger key={screen.id} value={screen.id} className="gap-2 whitespace-nowrap px-3 py-2">
                  <Icon className="h-4 w-4" />
                  <span>{screen.title}</span>
                  {missing ? <span className="rounded bg-warning/20 px-1.5 text-[10px] text-warning">{missing}</span> : null}
                </TabsTrigger>
              );
            })}
          </TabsList>
        </ScrollArea>

        {screens.map((screen) => (
          <TabsContent key={screen.id} value={screen.id} className="mt-0">
            <ScreenPanel
              screen={screen}
              inventory={inventory}
              surfaceQuery={surfaceQuery}
              surfaceFilter={surfaceFilter}
            />
          </TabsContent>
        ))}
      </Tabs>
    </section>
  );
}

interface EvidenceItem {
  id: string;
  label: string;
  type: Exclude<EvidenceFilter, "all">;
  path: string;
  status: string;
  detail: string;
}

function buildEvidenceItems(state: UnifiedFrontendState | null, runtime: RuntimeObservation): EvidenceItem[] {
  const items: EvidenceItem[] = [
    {
      id: "inventory",
      label: "SaaS and frontend inventory",
      type: "audit",
      path: state?.inventorySource || "pending",
      status: state?.inventory.status || "pending",
      detail: "Surface inventory, blockers, orphaned frontend, and Supabase function coverage.",
    },
    {
      id: "plan",
      label: "Unified frontend plan",
      type: "audit",
      path: state?.planSource || "pending",
      status: state?.plan.status || "pending",
      detail: "Canonical screens, safety contract, generated outputs, and missing capability map.",
    },
    {
      id: "organism",
      label: "Organism runtime status",
      type: "audit",
      path: state?.organismSource || "pending",
      status: state?.organism.status || "pending",
      detail: "Freshness, blind spots, runtime pulse, and next-action lines.",
    },
    {
      id: "evolution",
      label: "Frontend evolution queue",
      type: "audit",
      path: state?.evolutionSource || "pending",
      status: state?.evolution.status || "pending",
      detail: "Work orders, ready adapters, blocked migrations, and archive candidates.",
    },
    {
      id: "switchboard",
      label: "Autonomous capability switchboard",
      type: "audit",
      path: state?.switchboardSource || "pending",
      status: state?.switchboard.status || "pending",
      detail: "Autonomous modes, presentation intents, blockers, and anti-drift gates.",
    },
    {
      id: "runtime-feed",
      label: "Runtime feed",
      type: "runtime",
      path: runtime.endpoint || "offline",
      status: runtime.connected ? (runtime.clearancePending ? "checking" : "connected") : "offline",
      detail: "Live local terminal-state endpoint used by the runtime mirror.",
    },
    {
      id: "coding-organism",
      label: "Coding organism bridge",
      type: "public",
      path: "/aureon_coding_organism_bridge.json",
      status: "public artifact",
      detail: "Prompt-to-client-job evidence, proof checks, handover state, and finished artifacts.",
    },
    {
      id: "capability-forge",
      label: "Local capability forge",
      type: "public",
      path: "/aureon_capability_forge.json",
      status: "public artifact",
      detail: "Local-only build, media, coding, quality gate, and regeneration evidence.",
    },
    {
      id: "quality-report",
      label: "Artifact quality report",
      type: "public",
      path: "/aureon_artifact_quality_report.json",
      status: "public artifact",
      detail: "Render/playback proof, snags, scores, and handover gating.",
    },
    {
      id: "complex-stress",
      label: "Complex build stress certification",
      type: "public",
      path: "/aureon_complex_build_stress_audit.json",
      status: "public artifact",
      detail: "Complex case matrix, repair attempts, fake-pass detection, and handover certification.",
    },
    {
      id: "order-lifecycle-stress",
      label: "Order lifecycle stress certification",
      type: "public",
      path: "/aureon_order_lifecycle_stress_audit.json",
      status: "public artifact",
      detail: "Mock-broker lifecycle continuity proof for submit, broker acknowledgement, recovery, close verification, and failure states.",
    },
    {
      id: "coding-unblocker",
      label: "Autonomous coding capability gates",
      type: "public",
      path: "/aureon_coding_capability_unblocker.json",
      status: "public artifact",
      detail: "Coding routes, learning/research gates, safe auto-repair authority, and open-source references.",
    },
    {
      id: "self-fix-director",
      label: "Aureon self-fix SWOT director",
      type: "public",
      path: "/aureon_autonomous_self_fix_director.json",
      status: "public artifact",
      detail: "SWOT, repair backlog, guarded patch evidence, tests, snags, and Codex audit state.",
    },
    {
      id: "self-run-loop",
      label: "Aureon autonomous self-run loop",
      type: "public",
      path: "/aureon_autonomous_self_run_loop.json",
      status: "public artifact",
      detail: "Autonomous coding heartbeat, cycle tasks, self-repair queue, and hard-boundary holds.",
    },
    {
      id: "autonomous-job-executor",
      label: "Aureon autonomous job executor",
      type: "public",
      path: "/aureon_autonomous_job_executor.json",
      status: "public artifact",
      detail: "Durable autonomous job queue, active job phase, proof checklist, repair attempts, and handover state.",
    },
    {
      id: "evolution-queue-certification",
      label: "Evolution queue autonomous certification",
      type: "public",
      path: "/aureon_evolution_queue_autonomous_certification.json",
      status: "public artifact",
      detail: "All evolution queue work orders processed into safe autonomous outcomes, proof checks, and visible boundary states.",
    },
    {
      id: "frontend-runtime-patches",
      label: "Frontend runtime patch registry",
      type: "public",
      path: "/aureon_frontend_runtime_patch_registry.json",
      status: "public artifact",
      detail: "Active runtime patch records created from completed evolution work orders.",
    },
    {
      id: "bridge-report",
      label: "Coding organism audit report",
      type: "report",
      path: "docs/audits/aureon_coding_organism_bridge.md",
      status: "markdown report",
      detail: "Human-readable bridge report for the latest coding organism run.",
    },
    {
      id: "forge-report",
      label: "Capability forge audit report",
      type: "report",
      path: "docs/audits/aureon_capability_forge.md",
      status: "markdown report",
      detail: "Human-readable capability forge and quality gate report.",
    },
  ];
  return items;
}

function EvidencePanel({
  state,
  runtime,
  filter,
  onFilterChange,
}: {
  state: UnifiedFrontendState | null;
  runtime: RuntimeObservation;
  filter: EvidenceFilter;
  onFilterChange: (value: EvidenceFilter) => void;
}) {
  const items = buildEvidenceItems(state, runtime);
  const visible = filter === "all" ? items : items.filter((item) => item.type === filter);

  return (
    <Card className="bg-card/80">
      <CardHeader className="pb-3">
        <CardTitle className="flex flex-col gap-3 text-base lg:flex-row lg:items-center lg:justify-between">
          <span className="flex items-center gap-2">
            <FileText className="h-4 w-4 text-primary" />
            Evidence And Public Artifacts
          </span>
          <FilterButtons options={evidenceFilterOptions} value={filter} onChange={onFilterChange} />
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="grid gap-3 lg:grid-cols-2">
          {visible.map((item) => {
            const isLink = item.path.startsWith("/") || item.path.startsWith("http://") || item.path.startsWith("https://");
            return (
              <div key={item.id} className="rounded-md border border-border/40 bg-muted/10 p-3">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div className="min-w-0">
                    <div className="text-sm font-semibold">{item.label}</div>
                    {isLink ? (
                      <a className="mt-1 block truncate font-mono text-[11px] text-primary hover:underline" href={item.path} target="_blank" rel="noreferrer">
                        {item.path}
                      </a>
                    ) : (
                      <div className="mt-1 truncate font-mono text-[11px] text-muted-foreground">{item.path}</div>
                    )}
                  </div>
                  <div className="flex flex-wrap gap-1">
                    <Pill label={item.type} tone="border-primary/30 bg-primary/10 text-primary" />
                    <Pill label={item.status} tone="border-border bg-muted/20 text-muted-foreground" />
                  </div>
                </div>
                <div className="mt-2 text-xs text-muted-foreground">{item.detail}</div>
              </div>
            );
          })}
        </div>
        {!visible.length ? <div className="text-sm text-muted-foreground">No evidence artifacts match the current filter.</div> : null}
      </CardContent>
    </Card>
  );
}

function freshnessTone(status: string): string {
  if (status === "fresh") return statusTone.wired;
  if (status === "attention") return "border-warning/30 bg-warning/10 text-warning";
  if (status === "stale") return "border-warning/30 bg-warning/10 text-warning";
  if (status === "missing" || status === "broken") return statusTone.security_blocker;
  return statusTone.unknown;
}

function formatAge(seconds: unknown): string {
  const total = asNumber(seconds, -1);
  if (total < 0) return "unknown";
  if (total < 60) return `${Math.round(total)}s`;
  if (total < 3600) return `${Math.round(total / 60)}m`;
  return `${Math.round(total / 3600)}h`;
}

function OrganismPulsePanel({
  organism,
  runtimeConnected,
}: {
  organism: UnifiedFrontendState["organism"];
  runtimeConnected: boolean;
}) {
  const domains = organism.domains || [];
  const blindSpots = organism.blind_spots || [];
  const summary = organism.summary || {};
  const sortedDomains = [...domains].sort((a, b) => {
    const order: Record<string, number> = { missing: 0, broken: 1, stale: 2, attention: 3, fresh: 4 };
    return (order[a.status] ?? 5) - (order[b.status] ?? 5);
  });

  return (
    <div className="mb-5 grid gap-4 xl:grid-cols-[1fr_0.95fr]">
      <Card className="bg-card/80">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <Brain className="h-4 w-4 text-primary" />
            Organism Pulse
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-2">
            <Pill label={organism.status || "pulse pending"} tone={freshnessTone((organism.status || "").includes("blind") ? "attention" : "fresh")} />
            <Pill label={`mode ${organism.mode || "safe_observation"}`} tone="border-primary/30 bg-primary/10 text-primary" />
            <Pill label={runtimeConnected ? "runtime feed connected" : "runtime feed offline"} tone={runtimeConnected ? statusTone.wired : statusTone.partial} />
            <Pill label={`updated ${organism.generated_at ? new Date(organism.generated_at).toLocaleTimeString() : "pending"}`} tone="border-border bg-muted/20 text-muted-foreground" />
          </div>

          <div className="grid gap-2 md:grid-cols-4">
            <div className="rounded-md border border-border/40 bg-muted/10 p-3">
              <div className="text-[11px] uppercase text-muted-foreground">domains</div>
              <div className="mt-1 text-lg font-semibold">{formatCompact(summary.domain_count)}</div>
            </div>
            <div className="rounded-md border border-border/40 bg-muted/10 p-3">
              <div className="text-[11px] uppercase text-muted-foreground">fresh</div>
              <div className="mt-1 text-lg font-semibold text-success">{formatCompact(summary.fresh_domain_count)}</div>
            </div>
            <div className="rounded-md border border-border/40 bg-muted/10 p-3">
              <div className="text-[11px] uppercase text-muted-foreground">stale/missing</div>
              <div className="mt-1 text-lg font-semibold text-warning">
                {formatCompact(asNumber(summary.stale_domain_count) + asNumber(summary.missing_domain_count))}
              </div>
            </div>
            <div className="rounded-md border border-border/40 bg-muted/10 p-3">
              <div className="text-[11px] uppercase text-muted-foreground">blind spots</div>
              <div className="mt-1 text-lg font-semibold text-destructive">{formatCompact(summary.blind_spot_count)}</div>
            </div>
          </div>

          <ScrollArea className="h-[245px] pr-3">
            <div className="space-y-2">
              {sortedDomains.slice(0, 14).map((domain: OrganismDomainPulse) => (
                <div key={domain.id} className="rounded-md border border-border/40 bg-muted/10 p-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <div className="text-sm font-medium">{domain.label}</div>
                      <div className="mt-1 font-mono text-[11px] text-muted-foreground">{domain.source_path}</div>
                    </div>
                    <div className="flex flex-wrap gap-1">
                      <Pill label={domain.status} tone={freshnessTone(domain.status)} />
                      <Pill label={formatAge(domain.age_seconds)} tone="border-border bg-muted/20 text-muted-foreground" />
                    </div>
                  </div>
                  {domain.blind_spots?.length ? (
                    <div className="mt-2 text-xs text-warning">{domain.blind_spots.slice(0, 3).join(", ")}</div>
                  ) : null}
                </div>
              ))}
            </div>
          </ScrollArea>
        </CardContent>
      </Card>

      <Card className="bg-card/80">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <AlertTriangle className="h-4 w-4 text-primary" />
            Blind Spots And Next Actions
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <ScrollArea className="h-[276px] pr-3">
            <div className="space-y-2">
              {blindSpots.length ? (
                blindSpots.slice(0, 16).map((spot) => (
                  <div key={spot.id} className="rounded-md border border-border/40 bg-muted/10 p-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="font-mono text-[11px] text-muted-foreground">{spot.id}</div>
                      <Pill label={spot.severity} tone={spot.severity === "high" ? statusTone.security_blocker : "border-warning/30 bg-warning/10 text-warning"} />
                    </div>
                    <div className="mt-2 text-sm">{spot.issue}</div>
                    {spot.next_action ? <div className="mt-2 text-xs text-muted-foreground">{spot.next_action}</div> : null}
                  </div>
                ))
              ) : (
                <div className="rounded-md border border-success/30 bg-success/10 p-4 text-sm text-success">
                  No blind spots in the current organism pulse.
                </div>
              )}
            </div>
          </ScrollArea>
          <div className="rounded-md border border-border/50 bg-black/35 p-3">
            <pre className="max-h-32 overflow-auto whitespace-pre-wrap font-mono text-[11px] leading-5 text-foreground">
              {(organism.status_lines || ["Waiting for organism pulse..."]).slice(0, 10).join("\n")}
            </pre>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function matchesWorkOrderFilter(
  order: NonNullable<FrontendEvolutionQueueManifest["work_orders"]>[number],
  filter: WorkOrderFilter,
  activeScreenId?: string,
): boolean {
  const status = String(order.status || "").toLowerCase();
  if (filter === "blocked") return status.includes("blocked");
  if (filter === "ready") return status.includes("ready") || status.includes("adapter");
  if (filter === "archive") return status.includes("archive");
  if (filter === "screen") return Boolean(activeScreenId) && order.target_screen === activeScreenId;
  return true;
}

function FrontendEvolutionPanel({
  evolution,
  filter = "all",
  activeScreenId,
}: {
  evolution: FrontendEvolutionQueueManifest;
  filter?: WorkOrderFilter;
  activeScreenId?: string;
}) {
  const summary = evolution.summary || {};
  const orders = [...(evolution.work_orders || [])]
    .filter((order) => matchesWorkOrderFilter(order, filter, activeScreenId))
    .sort((a, b) => asNumber(b.priority) - asNumber(a.priority))
    .slice(0, filter === "all" ? 10 : 30);

  return (
    <Card className="mb-5 bg-card/80">
      <CardHeader className="pb-3">
        <CardTitle className="flex flex-wrap items-center justify-between gap-2 text-base">
          <span className="flex items-center gap-2">
            <Activity className="h-4 w-4 text-primary" />
            Frontend Evolution Queue
          </span>
          <Pill label={`showing ${formatCompact(orders.length)}`} tone="border-border bg-muted/20 text-muted-foreground" />
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-wrap gap-2">
          <Pill label={evolution.status || "queue pending"} tone={asNumber(summary.blocked_count) ? "border-warning/30 bg-warning/10 text-warning" : statusTone.wired} />
          <Pill label={`${formatCompact(summary.ready_adapter_count)} ready adapters`} tone="border-success/30 bg-success/10 text-success" />
          <Pill label={`${formatCompact(summary.blocked_count)} blocked`} tone={asNumber(summary.blocked_count) ? statusTone.security_blocker : "border-border bg-muted/20 text-muted-foreground"} />
          <Pill label={`updated ${evolution.generated_at ? new Date(evolution.generated_at).toLocaleTimeString() : "pending"}`} tone="border-border bg-muted/20 text-muted-foreground" />
        </div>

        <div className="grid gap-2 md:grid-cols-5">
          <div className="rounded-md border border-border/40 bg-muted/10 p-3">
            <div className="text-[11px] uppercase text-muted-foreground">work orders</div>
            <div className="mt-1 text-lg font-semibold">{formatCompact(summary.queue_count)}</div>
          </div>
          <div className="rounded-md border border-border/40 bg-muted/10 p-3">
            <div className="text-[11px] uppercase text-muted-foreground">targets</div>
            <div className="mt-1 text-lg font-semibold">{formatCompact(summary.target_screen_count)}</div>
          </div>
          <div className="rounded-md border border-border/40 bg-muted/10 p-3">
            <div className="text-[11px] uppercase text-muted-foreground">generated links</div>
            <div className="mt-1 text-lg font-semibold">{formatCompact(summary.generated_output_link_count)}</div>
          </div>
          <div className="rounded-md border border-border/40 bg-muted/10 p-3">
            <div className="text-[11px] uppercase text-muted-foreground">archive</div>
            <div className="mt-1 text-lg font-semibold">{formatCompact(summary.archive_candidate_count)}</div>
          </div>
          <div className="rounded-md border border-border/40 bg-muted/10 p-3">
            <div className="text-[11px] uppercase text-muted-foreground">top priority</div>
            <div className="mt-1 text-lg font-semibold">{formatCompact(summary.highest_priority)}</div>
          </div>
        </div>

        <ScrollArea className="h-[330px] pr-3">
          <div className="space-y-3">
            {orders.length ? (
              orders.map((order) => (
                <div key={order.id} className="rounded-md border border-border/40 bg-muted/10 p-3">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="text-sm font-medium">{order.title}</div>
                      <div className="mt-1 truncate font-mono text-[11px] text-muted-foreground">{order.source_path}</div>
                    </div>
                    <div className="flex flex-wrap gap-1">
                      <Pill label={`P${order.priority}`} tone="border-primary/30 bg-primary/10 text-primary" />
                      <Pill label={order.status} tone={order.status.includes("blocked") ? statusTone.security_blocker : freshnessTone("attention")} />
                      <Pill label={order.target_title} tone="border-border bg-muted/20 text-muted-foreground" />
                    </div>
                  </div>
                  <div className="mt-2 text-xs text-muted-foreground">{order.capability_summary}</div>
                  {order.frontend_action ? <div className="mt-2 text-xs text-foreground">{order.frontend_action}</div> : null}
                  {order.safety_boundary ? <div className="mt-2 text-[11px] text-warning">{order.safety_boundary}</div> : null}
                </div>
              ))
            ) : (
              <div className="rounded-md border border-border/40 bg-muted/10 p-4 text-sm text-muted-foreground">
                No evolution work orders are mounted yet.
              </div>
            )}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}

function CapabilitySwitchboardPanel({ switchboard }: { switchboard: CapabilitySwitchboardManifest }) {
  const summary = switchboard.summary || {};
  const modes = [...(switchboard.capability_modes || [])];
  const intents = [...(switchboard.presentation_intents || [])]
    .sort((a, b) => asNumber(b.priority) - asNumber(a.priority))
    .slice(0, 10);
  const blockers = switchboard.blockers || [];
  const gates = Array.isArray(switchboard.hnc_control_contract?.anti_hallucination_gates)
    ? switchboard.hnc_control_contract.anti_hallucination_gates.map((gate) => String(gate))
    : [];

  return (
    <div className="mb-5 grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
      <Card className="bg-card/80">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <Brain className="h-4 w-4 text-primary" />
            Autonomous Capability Switchboard
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-2">
            <Pill label={switchboard.status || "switchboard pending"} tone={asNumber(summary.blocker_count) ? "border-warning/30 bg-warning/10 text-warning" : statusTone.wired} />
            <Pill label={`${formatCompact(summary.autonomous_capability_count)} autonomous modes`} tone="border-success/30 bg-success/10 text-success" />
            <Pill label={`${formatCompact(summary.presentation_intent_count)} presentation intents`} tone="border-primary/30 bg-primary/10 text-primary" />
            <Pill label={`updated ${switchboard.generated_at ? new Date(switchboard.generated_at).toLocaleTimeString() : "pending"}`} tone="border-border bg-muted/20 text-muted-foreground" />
          </div>

          <div className="grid gap-2 md:grid-cols-5">
            <div className="rounded-md border border-border/40 bg-muted/10 p-3">
              <div className="text-[11px] uppercase text-muted-foreground">capabilities</div>
              <div className="mt-1 text-lg font-semibold">{formatCompact(summary.capability_count)}</div>
            </div>
            <div className="rounded-md border border-border/40 bg-muted/10 p-3">
              <div className="text-[11px] uppercase text-muted-foreground">blocked</div>
              <div className="mt-1 text-lg font-semibold text-warning">{formatCompact(summary.blocker_count)}</div>
            </div>
            <div className="rounded-md border border-border/40 bg-muted/10 p-3">
              <div className="text-[11px] uppercase text-muted-foreground">app/UI queue</div>
              <div className="mt-1 text-lg font-semibold">{formatCompact(summary.frontend_work_order_count)}</div>
            </div>
            <div className="rounded-md border border-border/40 bg-muted/10 p-3">
              <div className="text-[11px] uppercase text-muted-foreground">ready adapters</div>
              <div className="mt-1 text-lg font-semibold text-success">{formatCompact(summary.ready_adapter_count)}</div>
            </div>
            <div className="rounded-md border border-border/40 bg-muted/10 p-3">
              <div className="text-[11px] uppercase text-muted-foreground">runtime</div>
              <div className="mt-1 truncate text-sm font-semibold">{String(summary.runtime_feed_status || "unknown")}</div>
            </div>
          </div>

          <ScrollArea className="h-[356px] pr-3">
            <div className="space-y-3">
              {modes.length ? (
                modes.map((mode) => (
                  <div key={mode.id} className="rounded-md border border-border/40 bg-muted/10 p-3">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div className="min-w-0">
                        <div className="text-sm font-medium">{mode.title}</div>
                        <div className="mt-1 text-xs text-muted-foreground">{mode.authority_level.replace(/_/g, " ")}</div>
                      </div>
                      <div className="flex flex-wrap gap-1">
                        <Pill label={mode.domain} tone="border-border bg-muted/20 text-muted-foreground" />
                        <Pill label={mode.status} tone={mode.status.startsWith("blocked") ? statusTone.security_blocker : freshnessTone(mode.status.includes("ready") ? "fresh" : "attention")} />
                        <Pill label={mode.autonomous_allowed ? "autonomous" : "manual"} tone={mode.autonomous_allowed ? statusTone.wired : statusTone.partial} />
                      </div>
                    </div>
                    {mode.systems?.length ? (
                      <div className="mt-2 flex flex-wrap gap-1">
                        {mode.systems.slice(0, 5).map((system) => (
                          <Pill key={system} label={system} tone="border-primary/30 bg-primary/10 text-primary" />
                        ))}
                      </div>
                    ) : null}
                    {mode.next_action ? <div className="mt-2 text-xs text-muted-foreground">{mode.next_action}</div> : null}
                  </div>
                ))
              ) : (
                <div className="rounded-md border border-border/40 bg-muted/10 p-4 text-sm text-muted-foreground">
                  No capability modes are mounted yet.
                </div>
              )}
            </div>
          </ScrollArea>
        </CardContent>
      </Card>

      <Card className="bg-card/80">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <Eye className="h-4 w-4 text-primary" />
            What Aureon Chooses To Show Next
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="rounded-md border border-border/40 bg-muted/10 p-3">
            <div className="text-[11px] uppercase text-muted-foreground">HNC anti-drift gates</div>
            <div className="mt-2 flex flex-wrap gap-1">
              {(gates.length ? gates : ["source_evidence_required", "safe_authority_boundary_checked"]).slice(0, 7).map((gate) => (
                <Pill key={gate} label={gate.replace(/_/g, " ")} tone="border-success/30 bg-success/10 text-success" />
              ))}
            </div>
          </div>

          <ScrollArea className="h-[255px] pr-3">
            <div className="space-y-2">
              {intents.length ? (
                intents.map((intent) => (
                  <div key={intent.id} className="rounded-md border border-border/40 bg-muted/10 p-3">
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <div>
                        <div className="text-sm font-medium">{intent.title}</div>
                        <div className="mt-1 text-xs text-muted-foreground">{intent.reason}</div>
                      </div>
                      <div className="flex flex-wrap gap-1">
                        <Pill label={`P${intent.priority}`} tone="border-primary/30 bg-primary/10 text-primary" />
                        <Pill label={intent.display_mode.replace(/_/g, " ")} tone="border-border bg-muted/20 text-muted-foreground" />
                      </div>
                    </div>
                    {intent.next_action ? <div className="mt-2 text-xs text-foreground">{intent.next_action}</div> : null}
                  </div>
                ))
              ) : (
                <div className="rounded-md border border-border/40 bg-muted/10 p-4 text-sm text-muted-foreground">
                  No presentation intents are mounted yet.
                </div>
              )}
            </div>
          </ScrollArea>

          <div className="space-y-2">
            <div className="text-xs uppercase text-muted-foreground">Current blockers</div>
            {(blockers.length ? blockers.slice(0, 4) : [{ id: "none", reason: "No switchboard blockers reported." }]).map((blocker) => (
              <div key={String(blocker.id)} className="rounded-md border border-border/40 bg-muted/10 px-3 py-2 text-xs">
                <span className="font-mono text-muted-foreground">{String(blocker.id)}</span>
                <span className="ml-2 text-foreground">{String(blocker.reason || "")}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function LiveGoalTradeAuditPanel({ audit, runtime }: { audit: LiveGoalTradeAudit | null; runtime: RuntimeObservation }) {
  const goal = audit?.goal_trade_proof || {};
  const data = audit?.data_capture || {};
  const capital = audit?.capital_gold_profile || {};
  const intent = audit?.order_intent_proof || {};
  const runtimeCandidate = audit?.runtime_candidate_proof || {};
  const executor = audit?.executor_gate || {};
  const bestGold = capital.best_gold_asset || {};
  const bestIntent = intent.best_gold_intent || {};
  const runtimeProof = runtime.goldRuntimeTradeProof || {};
  const runtimeGoldSource =
    runtimeProof.fresh_gold_data_source && typeof runtimeProof.fresh_gold_data_source === "object" && !Array.isArray(runtimeProof.fresh_gold_data_source)
      ? runtimeProof.fresh_gold_data_source as Record<string, unknown>
      : {};
  const runtimeGoldDataFresh = Boolean(goal.fresh_data_ready || runtimeGoldSource.ready);
  const runtimeCandidateReady = Boolean(goal.gold_runtime_candidate_ready || runtimeProof.gold_runtime_candidate_ready);
  const runtimeCapitalRouteVisible = Boolean(goal.capital_cfd_route_visible || runtimeProof.capital_cfd_route_visible);
  const runtimeCapitalRouteReady = Boolean(goal.capital_cfd_route_ready || runtimeProof.capital_cfd_route_ready);
  const runtimeIntentReason = String(
    goal.gold_intent_publish_reason ||
      runtimeProof.gold_intent_publish_reason ||
      runtimeCandidate.gold_intent_publish_reason ||
      "candidate proof pending",
  );
  const effectiveDataAge = runtimeGoldSource.age_sec ?? data.age_sec;
  const effectiveExecutorStale = runtime.connected ? Boolean(runtime.stale) : Boolean(executor.stale);
  const effectiveExecutorState = runtime.connected && !runtime.stale
    ? String(executor.trade_path_state || executor.state || "runtime proof live")
    : String(executor.stale_reason || executor.trade_path_state || executor.state || "checking");
  const effectiveBestGold = {
    ...bestGold,
    symbol: runtimeGoldSource.capital_symbol || runtimeGoldSource.symbol || bestGold.symbol || "GOLD",
    epic: runtimeGoldSource.capital_symbol || bestGold.epic || "GOLD",
    bid: runtimeGoldSource.bid ?? bestGold.bid,
    ask: runtimeGoldSource.ask ?? bestGold.ask,
    mid_price: runtimeGoldSource.reference_price ?? bestGold.mid_price,
    spread: runtimeGoldSource.spread ?? bestGold.spread,
    snapshot_age_sec: runtimeGoldSource.age_sec ?? bestGold.snapshot_age_sec,
    instrument_name: bestGold.instrument_name || "Gold",
  };
  const obsoleteBlockers = new Set<string>();
  if (runtimeGoldDataFresh) {
    obsoleteBlockers.add("stale_active_sources:capital");
    obsoleteBlockers.add("capital_gold_live_quote_missing_or_stale");
  }
  if (runtimeCandidateReady) obsoleteBlockers.add("gold_runtime_candidate_missing");
  if (runtime.connected && runtime.stale === false) obsoleteBlockers.add("current_tick_stale");
  const blockers = (goal.blockers || []).filter((blocker) => !obsoleteBlockers.has(blocker)).slice(0, 8);
  const proofState = runtimeCandidateReady && !goal.gold_order_intent_ready
    ? "runtime_gold_candidate_ready_intent_held"
    : String(goal.proof_state || "audit_pending");
  const proofTone = goal.live_trade_produced
    ? statusTone.wired
    : goal.dry_run_executor_proof_ready
      ? statusTone.wired
    : runtimeCandidateReady
      ? statusTone.orphaned
    : goal.gold_order_intent_ready
      ? statusTone.orphaned
      : statusTone.security_blocker;
  const gateCards = [
    {
      label: "fresh GOLD data",
      state: runtimeGoldDataFresh ? "pass" : "held",
      pass: runtimeGoldDataFresh,
      detail: formatFreshnessAge(asNumber(effectiveDataAge, -1)),
    },
    {
      label: "GOLD candidate",
      state: runtimeCandidateReady ? "ready" : "missing",
      pass: runtimeCandidateReady,
      detail: runtimeIntentReason,
    },
    {
      label: "GOLD intent",
      state: goal.gold_order_intent_ready && goal.intent_packet_fresh ? "fresh" : "blocked",
      pass: Boolean(goal.gold_order_intent_ready && goal.intent_packet_fresh),
      detail: `${formatCompact(intent.gold_intent_count)}/${formatCompact(intent.intent_count)} GOLD`,
    },
    {
      label: "dry-run executor proof",
      state: goal.dry_run_executor_proof_ready ? "ready" : "held",
      pass: Boolean(goal.dry_run_executor_proof_ready),
      detail: effectiveExecutorState,
    },
  ];

  return (
    <Card className="border-warning/30 bg-warning/5">
      <CardHeader className="pb-3">
        <CardTitle className="flex flex-wrap items-center justify-between gap-2 text-base">
          <span className="flex items-center gap-2">
            <LineChart className="h-4 w-4 text-warning" />
            GOLD Live Goal Trade Audit
          </span>
          <div className="flex flex-wrap gap-1">
            <Pill label={proofState.replace(/_/g, " ")} tone={proofTone} />
            <Pill label={audit?.generated_at ? `updated ${new Date(audit.generated_at).toLocaleTimeString()}` : "not generated"} tone="border-border bg-muted/20 text-muted-foreground" />
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-2 md:grid-cols-4">
          {gateCards.map((gate, index) => (
            <div key={gate.label} className={`rounded-md border p-3 ${gate.pass ? "border-success/30 bg-success/10" : "border-warning/30 bg-warning/10"}`}>
              <div className="flex items-center justify-between gap-2">
                <div className="text-[11px] uppercase text-muted-foreground">{index + 1}. {gate.label}</div>
                <Pill label={gate.state} tone={gate.pass ? statusTone.wired : statusTone.orphaned} />
              </div>
              <div className="mt-2 line-clamp-2 text-xs text-muted-foreground">{gate.detail}</div>
            </div>
          ))}
        </div>

        <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-6">
          <div className="rounded-md border border-border/40 bg-black/20 p-3">
            <div className="text-[11px] uppercase text-muted-foreground">live data</div>
            <div className={`mt-1 font-mono text-sm font-semibold ${runtimeGoldDataFresh ? "text-success" : "text-warning"}`}>
              {runtimeGoldDataFresh ? "fresh" : "held"}
            </div>
          </div>
          <div className="rounded-md border border-border/40 bg-black/20 p-3">
            <div className="text-[11px] uppercase text-muted-foreground">stream age</div>
            <div className="mt-1 font-mono text-sm font-semibold">{formatFreshnessAge(asNumber(effectiveDataAge, -1))}</div>
          </div>
          <div className="rounded-md border border-border/40 bg-black/20 p-3">
            <div className="text-[11px] uppercase text-muted-foreground">tickers</div>
            <div className="mt-1 font-mono text-sm font-semibold">{formatCompact(data.ticker_count)}</div>
          </div>
          <div className="rounded-md border border-border/40 bg-black/20 p-3">
            <div className="text-[11px] uppercase text-muted-foreground">GOLD intents</div>
            <div className={`mt-1 font-mono text-sm font-semibold ${goal.gold_order_intent_ready ? "text-success" : "text-destructive"}`}>
              {formatCompact(intent.gold_intent_count)}/{formatCompact(intent.intent_count)}
            </div>
          </div>
          <div className="rounded-md border border-border/40 bg-black/20 p-3">
            <div className="text-[11px] uppercase text-muted-foreground">executor sent</div>
            <div className="mt-1 font-mono text-sm font-semibold">{formatCompact(executor.submitted_count)}</div>
          </div>
          <div className="rounded-md border border-border/40 bg-black/20 p-3">
            <div className="text-[11px] uppercase text-muted-foreground">handover</div>
            <div className={`mt-1 font-mono text-sm font-semibold ${goal.handover_ready ? "text-success" : "text-warning"}`}>
              {goal.handover_ready ? "ready" : "blocked"}
            </div>
          </div>
        </div>

        {intent.non_gold_intents_rejected_for_gold_proof ? (
          <div className="rounded-md border border-warning/30 bg-warning/10 px-3 py-2 text-xs text-warning">
            Non-GOLD runtime intents are visible but rejected for GOLD proof. Only fresh Capital GOLD/XAU intents count here.
          </div>
        ) : null}

        {runtimeCandidateReady ? (
          <div className="rounded-md border border-primary/30 bg-primary/10 px-3 py-2 text-xs text-primary">
            Terminal-state is publishing a fresh {String(runtimeProof.candidate_symbol || "GOLD")} candidate with side {String(runtimeProof.candidate_side || "HOLD")}. Intent remains held until interval validation permits a GOLD order-intent.
          </div>
        ) : null}

        <div className="grid gap-3 lg:grid-cols-3">
          <div className="rounded-md border border-border/40 bg-muted/10 p-3">
            <div className="text-[11px] uppercase text-muted-foreground">Capital GOLD profile</div>
            <div className="mt-1 truncate text-sm font-semibold">{String(effectiveBestGold.symbol || effectiveBestGold.epic || "GOLD")} {String(effectiveBestGold.instrument_name || "")}</div>
            <div className="mt-2 grid grid-cols-2 gap-2 text-xs">
              <div>
                <div className="text-muted-foreground">bid/ask</div>
                <div className="font-mono">{String(effectiveBestGold.bid ?? "n/a")} / {String(effectiveBestGold.ask ?? "n/a")}</div>
              </div>
              <div>
                <div className="text-muted-foreground">snapshot</div>
                <div className="font-mono">{formatFreshnessAge(asNumber(effectiveBestGold.snapshot_age_sec, -1))}</div>
              </div>
            </div>
          </div>
          <div className="rounded-md border border-border/40 bg-muted/10 p-3">
            <div className="text-[11px] uppercase text-muted-foreground">best GOLD intent</div>
            <div className="mt-1 truncate text-sm font-semibold">{String(bestIntent.symbol || "none")} {String(bestIntent.side || "")}</div>
            <div className="mt-2 grid grid-cols-2 gap-2 text-xs">
              <div>
                <div className="text-muted-foreground">confidence</div>
                <div className="font-mono">{String(bestIntent.confidence ?? "n/a")}</div>
              </div>
              <div>
                <div className="text-muted-foreground">routes</div>
                <div className="font-mono">{formatCompact(bestIntent.route_count)}</div>
              </div>
            </div>
          </div>
          <div className="rounded-md border border-border/40 bg-muted/10 p-3">
            <div className="text-[11px] uppercase text-muted-foreground">executor gate</div>
            <div className="mt-1 truncate text-sm font-semibold">{String(executor.trade_path_state || executor.state || "checking").replace(/_/g, " ")}</div>
            <div className="mt-2 flex flex-wrap gap-1">
              <Pill label={executor.executor_enabled ? "executor enabled" : "executor off"} tone={executor.executor_enabled ? statusTone.wired : statusTone.partial} />
              <Pill label={effectiveExecutorStale ? String(runtime.staleReason || executor.stale_reason || "runtime stale") : "runtime proof live"} tone={effectiveExecutorStale ? statusTone.security_blocker : statusTone.wired} />
              <Pill label={runtimeCapitalRouteVisible ? (runtimeCapitalRouteReady ? "Capital route visible" : "Capital route held") : "Capital route hidden"} tone={runtimeCapitalRouteReady ? statusTone.wired : statusTone.partial} />
            </div>
          </div>
        </div>

        {blockers.length ? (
          <div className="space-y-2">
            <div className="text-xs uppercase text-muted-foreground">Current blockers</div>
            <div className="grid gap-2 md:grid-cols-2">
              {blockers.map((blocker) => (
                <div key={blocker} className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs text-destructive">
                  {blocker}
                </div>
              ))}
            </div>
          </div>
        ) : null}

        <div className="rounded-md border border-border/40 bg-black/20 p-3 text-xs text-muted-foreground">
          {audit ? goal.next_action || "Goal-trade audit ready." : "Run python -m aureon.autonomous.aureon_live_goal_trade_audit --json to publish the first proof packet."}
        </div>
      </CardContent>
    </Card>
  );
}

function OrderLifecyclePanel({ audit, runtime }: { audit: LiveGoalTradeAudit | null; runtime: RuntimeObservation }) {
  const runtimeLifecycle = asRecord(runtime.data?.order_lifecycle);
  const auditSnapshot = asRecord(audit?.order_lifecycle_proof?.snapshot);
  const proof = audit?.order_lifecycle_proof || {};
  const state = Object.keys(runtimeLifecycle).length ? runtimeLifecycle : auditSnapshot;
  const lifecycles = asRecordArray(state.lifecycles);
  const active = asRecordArray(state.active_lifecycles ?? proof.active_lifecycles);
  const events = asRecordArray(state.events).slice(-8).reverse();
  const latest = asRecord(state.latest_event);
  const continuityBlockers = [
    ...((state.continuity_blockers as string[] | undefined) || []),
    ...((proof.blockers as string[] | undefined) || []),
  ].filter(Boolean);
  const missingLinks = [
    ...((proof.missing_links as string[] | undefined) || []),
    ...active.flatMap((row) => (Array.isArray(row.missing_links) ? row.missing_links.map(String) : [])),
  ].filter(Boolean);
  const timelineRows = active.length ? active : lifecycles.slice(0, 6);
  const lifecycleReady = Boolean(state && Object.keys(state).length && continuityBlockers.length === 0);

  return (
    <Card className="border-primary/30 bg-primary/5">
      <CardHeader className="pb-3">
        <CardTitle className="flex flex-wrap items-center justify-between gap-2 text-base">
          <span className="flex items-center gap-2">
            <Activity className="h-4 w-4 text-primary" />
            Order Lifecycle
          </span>
          <div className="flex flex-wrap gap-1">
            <Pill label={lifecycleReady ? "continuity visible" : "continuity attention"} tone={lifecycleReady ? statusTone.wired : statusTone.orphaned} />
            <Pill label={`${formatCompact(state.active_lifecycle_count ?? proof.active_lifecycle_count)} active`} tone="border-border bg-muted/20 text-muted-foreground" />
            <Pill label={`${formatCompact(state.completed_lifecycle_count ?? proof.completed_lifecycle_count)} closed`} tone="border-border bg-muted/20 text-muted-foreground" />
            <Pill label={String(latest.status || proof.latest_status || "no events").replace(/_/g, " ")} tone={continuityBlockers.length ? statusTone.security_blocker : statusTone.partial} />
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-5">
          <div className="rounded-md border border-border/40 bg-black/20 p-3">
            <div className="text-[11px] uppercase text-muted-foreground">events</div>
            <div className="mt-1 font-mono text-sm font-semibold">{formatCompact(state.event_count ?? proof.event_count)}</div>
          </div>
          <div className="rounded-md border border-border/40 bg-black/20 p-3">
            <div className="text-[11px] uppercase text-muted-foreground">lifecycles</div>
            <div className="mt-1 font-mono text-sm font-semibold">{formatCompact(state.lifecycle_count ?? proof.lifecycle_count)}</div>
          </div>
          <div className="rounded-md border border-border/40 bg-black/20 p-3">
            <div className="text-[11px] uppercase text-muted-foreground">last broker proof</div>
            <div className="mt-1 truncate font-mono text-sm font-semibold">{String(latest.deal_id || proof.latest_deal_id || latest.order_id || "pending")}</div>
          </div>
          <div className="rounded-md border border-border/40 bg-black/20 p-3">
            <div className="text-[11px] uppercase text-muted-foreground">latest chain</div>
            <div className="mt-1 truncate font-mono text-sm font-semibold">{String(latest.lifecycle_id || proof.latest_lifecycle_id || "none")}</div>
          </div>
          <div className="rounded-md border border-border/40 bg-black/20 p-3">
            <div className="text-[11px] uppercase text-muted-foreground">missing links</div>
            <div className={`mt-1 font-mono text-sm font-semibold ${missingLinks.length ? "text-warning" : "text-success"}`}>
              {missingLinks.length ? formatCompact(new Set(missingLinks).size) : "0"}
            </div>
          </div>
        </div>

        <div className="space-y-2">
          <div className="text-xs uppercase text-muted-foreground">Current chain</div>
          {timelineRows.length ? (
            <div className="grid gap-2 lg:grid-cols-2">
              {timelineRows.map((row) => {
                const missing = Array.isArray(row.missing_links) ? row.missing_links.map(String) : [];
                return (
                  <div key={String(row.lifecycle_id || row.updated_at)} className="rounded-md border border-border/40 bg-muted/10 p-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="min-w-0">
                        <div className="truncate text-sm font-semibold">
                          {String(row.symbol || "unknown")} {String(row.side || "")} {String(row.venue || "")}
                        </div>
                        <div className="truncate font-mono text-[11px] text-muted-foreground">{String(row.lifecycle_id || "")}</div>
                      </div>
                      <Pill label={String(row.current_status || "unknown").replace(/_/g, " ")} tone={missing.length ? statusTone.orphaned : statusTone.wired} />
                    </div>
                    <div className="mt-3 grid gap-2 text-xs sm:grid-cols-3">
                      <div>
                        <div className="text-muted-foreground">route</div>
                        <div className="truncate font-mono">{String(row.route_key || "pending")}</div>
                      </div>
                      <div>
                        <div className="text-muted-foreground">broker</div>
                        <div className="truncate font-mono">{String(row.deal_id || row.deal_reference || "pending")}</div>
                      </div>
                      <div>
                        <div className="text-muted-foreground">P/L</div>
                        <div className="truncate font-mono">{String(row.last_pnl ?? "pending")}</div>
                      </div>
                    </div>
                    {missing.length ? (
                      <div className="mt-2 flex flex-wrap gap-1">
                        {missing.slice(0, 5).map((link) => (
                          <Pill key={link} label={link.replace(/_/g, " ")} tone={statusTone.orphaned} />
                        ))}
                      </div>
                    ) : null}
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="rounded-md border border-border/40 bg-muted/10 p-4 text-sm text-muted-foreground">
              No lifecycle chain has been published yet.
            </div>
          )}
        </div>

        {events.length ? (
          <div className="space-y-2">
            <div className="text-xs uppercase text-muted-foreground">Recent lifecycle events</div>
            <div className="grid gap-2 md:grid-cols-2">
              {events.map((event) => (
                <div key={String(event.event_id || `${event.generated_at}-${event.status}`)} className="rounded-md border border-border/40 bg-black/20 px-3 py-2 text-xs">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-mono text-primary">{String(event.status || event.event_type || "event").replace(/_/g, " ")}</span>
                    <span className="text-muted-foreground">{event.generated_at ? new Date(String(event.generated_at)).toLocaleTimeString() : ""}</span>
                  </div>
                  <div className="mt-1 truncate text-muted-foreground">{String(event.symbol || "")} {String(event.route_key || event.lifecycle_id || "")}</div>
                </div>
              ))}
            </div>
          </div>
        ) : null}

        {continuityBlockers.length ? (
          <div className="flex flex-wrap gap-1">
            {Array.from(new Set(continuityBlockers)).slice(0, 8).map((blocker) => (
              <Pill key={blocker} label={String(blocker).replace(/_/g, " ")} tone={statusTone.security_blocker} />
            ))}
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}

function OrderLifecycleStressPanel({
  stressAudit,
  audit,
}: {
  stressAudit: OrderLifecycleStressAudit | null;
  audit: LiveGoalTradeAudit | null;
}) {
  const proofSnapshot = asRecord(audit?.order_lifecycle_stress_proof?.snapshot);
  const proof = audit?.order_lifecycle_stress_proof || {};
  const source = stressAudit || (Object.keys(proofSnapshot).length ? (proofSnapshot as OrderLifecycleStressAudit) : null);
  const summary = source?.summary || {};
  const cases = asRecordArray(source?.cases ?? proof.cases);
  const sandboxCases = asRecordArray(source?.sandbox_paper_cases ?? proof.sandbox_paper_cases);
  const requirements = asRecordArray(source?.requirements);
  const sandboxRequirements = asRecordArray(source?.sandbox_paper_requirements ?? proof.sandbox_paper_requirements);
  const missing = ((source?.missing_requirements || proof.missing_requirements || []) as string[]).filter(Boolean);
  const sandboxMissing = ((summary.sandbox_paper_missing_requirements || proof.sandbox_paper_missing_requirements || []) as string[]).filter(Boolean);
  const blockers = ((source?.blockers || proof.blockers || []) as string[]).filter(Boolean);
  const sandboxBlockers = ((summary.sandbox_paper_blockers || proof.sandbox_paper_blockers || []) as string[]).filter(Boolean);
  const certified = String(source?.status || proof.status || proof.state || "").includes("certified") && blockers.length === 0;
  const mockCertified = Boolean(summary.mock_broker_certified ?? proof.mock_broker_certified ?? certified);
  const sandboxCertified = Boolean(summary.sandbox_paper_certified ?? proof.sandbox_paper_certified);
  const brokerFields = (summary.broker_correlation_fields || []) as string[];
  const matrixByVenue = asRecord(summary.broker_requirement_matrix_by_venue);
  const matrixRows = Object.values(matrixByVenue).map(asRecord);
  const sandboxProbeMode = String(summary.sandbox_probe_mode || proof.sandbox_probe_mode || "guarded fixture");

  return (
    <Card className="border-success/30 bg-success/5">
      <CardHeader className="pb-3">
        <CardTitle className="flex flex-wrap items-center justify-between gap-2 text-base">
          <span className="flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 text-success" />
            Lifecycle Stress Certification
          </span>
          <div className="flex flex-wrap gap-1">
            <Pill label={mockCertified ? "Mock Certified" : "Mock Attention"} tone={mockCertified ? statusTone.wired : statusTone.orphaned} />
            <Pill label={sandboxCertified ? "Sandbox/Paper Certified" : "Sandbox/Paper Attention"} tone={sandboxCertified ? statusTone.wired : statusTone.orphaned} />
            <Pill label={`${formatCompact(summary.passed_count ?? proof.passed_count)}/${formatCompact(summary.case_count ?? proof.case_count)} cases`} tone="border-border bg-muted/20 text-muted-foreground" />
            <Pill label={`${formatCompact(summary.covered_requirement_count ?? proof.covered_requirement_count)}/${formatCompact(summary.requirement_count ?? proof.requirement_count)} reqs`} tone="border-border bg-muted/20 text-muted-foreground" />
            <Pill label="/aureon_order_lifecycle_stress_audit.json" tone="border-primary/30 bg-primary/10 text-primary" />
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
          {[
            ["Capital GOLD", summary.capital_gold_path_certified ?? proof.capital_gold_path_certified],
            ["Duplicate route", summary.duplicate_route_blocked ?? proof.duplicate_route_blocked],
            ["Restart recovery", summary.restart_recovery_certified ?? proof.restart_recovery_certified],
            ["Multi-venue recovery", summary.multi_venue_recovery_certified],
            ["Close verify", summary.close_verification_enforced ?? proof.close_verification_enforced],
            ["Partial fills", summary.partial_fill_certified ?? proof.partial_fill_certified],
            ["Stale proof held", summary.stale_broker_proof_blocked],
            ["Failure states", summary.failure_state_mapping_certified ?? proof.failure_state_mapping_certified],
            ["Sandbox guard", summary.sandbox_environment_guard_passed ?? proof.sandbox_environment_guard_passed],
            ["No prod endpoints", summary.sandbox_no_production_order_endpoints ?? proof.sandbox_no_production_order_endpoints],
          ].map(([label, ok]) => (
            <div key={String(label)} className="rounded-md border border-border/40 bg-muted/10 p-3">
              <div className="text-[11px] uppercase text-muted-foreground">{String(label)}</div>
              <div className={`mt-1 font-mono text-sm font-semibold ${ok ? "text-success" : "text-warning"}`}>
                {ok ? "proven" : "held"}
              </div>
            </div>
          ))}
        </div>

        <div className="grid gap-2 md:grid-cols-3">
          <div className="rounded-md border border-primary/30 bg-primary/10 p-3">
            <div className="text-[11px] uppercase text-primary/80">Mock broker tier</div>
            <div className="mt-1 font-mono text-sm text-primary">{String(summary.mock_broker_status || proof.mock_broker_status || source?.status || "pending").replace(/_/g, " ")}</div>
          </div>
          <div className="rounded-md border border-success/30 bg-success/10 p-3">
            <div className="text-[11px] uppercase text-success/80">Sandbox / paper tier</div>
            <div className="mt-1 font-mono text-sm text-success">
              {formatCompact(summary.sandbox_paper_passed_count ?? proof.sandbox_paper_passed_count)}/{formatCompact(summary.sandbox_paper_case_count ?? proof.sandbox_paper_case_count)} cases / {String(summary.sandbox_paper_status || proof.sandbox_paper_status || "pending").replace(/_/g, " ")}
            </div>
          </div>
          <div className="rounded-md border border-border/40 bg-black/20 p-3">
            <div className="text-[11px] uppercase text-muted-foreground">Last probe mode</div>
            <div className="mt-1 font-mono text-sm text-muted-foreground">{sandboxProbeMode.replace(/_/g, " ")}</div>
          </div>
        </div>

        <div className="grid gap-3 lg:grid-cols-[1.2fr_0.8fr]">
          <div className="space-y-2">
            <div className="text-xs uppercase text-muted-foreground">Stress cases</div>
            <div className="grid gap-2 md:grid-cols-2">
              {cases.length ? cases.slice(0, 8).map((item) => (
                <div key={String(item.id || item.label)} className="rounded-md border border-border/40 bg-black/20 px-3 py-2 text-xs">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium">{String(item.label || item.id || "case")}</span>
                    <Pill label={String(item.state || (item.passed ? "passed" : "held")).replace(/_/g, " ")} tone={item.passed ? statusTone.wired : statusTone.orphaned} />
                  </div>
                  <div className="mt-1 truncate text-muted-foreground">{String(item.venue || "all")} {String(item.latest_status || "")}</div>
                </div>
              )) : (
                <div className="rounded-md border border-border/40 bg-muted/10 p-4 text-sm text-muted-foreground">
                  Stress certification is pending. Run python -m aureon.autonomous.aureon_order_lifecycle_stress_audit.
                </div>
              )}
            </div>
          </div>

          <div className="space-y-2">
            <div className="text-xs uppercase text-muted-foreground">Broker correlation fields</div>
            <div className="flex flex-wrap gap-1">
              {(brokerFields.length ? brokerFields : ["client_order_id", "broker_order_id", "deal_reference", "deal_id", "venue_status", "verification_source"]).slice(0, 12).map((field) => (
                <Pill key={field} label={field.replace(/_/g, " ")} tone="border-success/30 bg-success/10 text-success" />
              ))}
            </div>
            <div className="mt-3 text-xs text-muted-foreground">
              {formatCompact(requirements.length || proof.requirement_count)} mock requirements and {formatCompact(sandboxRequirements.length || proof.sandbox_paper_requirement_count)} sandbox requirements are covered as evidence; no live broker mutation or credential surface is mounted here.
            </div>
          </div>
        </div>

        <div className="space-y-2">
          <div className="flex items-center justify-between gap-2">
            <div className="text-xs uppercase text-muted-foreground">Sandbox / paper proof</div>
            <Pill
              label={sandboxCertified ? "sandbox/paper certified" : "sandbox/paper held"}
              tone={sandboxCertified ? statusTone.wired : statusTone.orphaned}
            />
          </div>
          <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-3">
            {sandboxCases.length ? sandboxCases.slice(0, 6).map((item) => {
              const guardrails = asRecordArray(item.guardrails);
              const firstGuard = guardrails[0] || {};
              return (
                <div key={String(item.id || item.label)} className="rounded-md border border-border/40 bg-black/20 px-3 py-2 text-xs">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium">{String(item.label || item.id || "sandbox case")}</span>
                    <Pill label={String(item.state || (item.passed ? "passed" : "held")).replace(/_/g, " ")} tone={item.passed ? statusTone.wired : statusTone.orphaned} />
                  </div>
                  <div className="mt-1 line-clamp-2 text-muted-foreground">
                    {String(firstGuard.broker_environment || item.venue || "sandbox")} / {String(firstGuard.operation || "proof")} / {String(firstGuard.endpoint_url || "guarded")}
                  </div>
                </div>
              );
            }) : (
              <div className="rounded-md border border-border/40 bg-muted/10 p-4 text-sm text-muted-foreground">
                Sandbox/paper certification evidence is pending.
              </div>
            )}
          </div>
        </div>

        <div className="space-y-2">
          <div className="flex items-center justify-between gap-2">
            <div className="text-xs uppercase text-muted-foreground">Venue requirement matrix</div>
            <Pill
              label={summary.broker_requirement_matrix_complete ? "matrix complete" : "matrix attention"}
              tone={summary.broker_requirement_matrix_complete ? statusTone.wired : statusTone.orphaned}
            />
          </div>
          <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-5">
            {(matrixRows.length ? matrixRows : requirements.slice(0, 5)).map((item) => {
              const identifiers = (item.required_identifiers || []) as unknown[];
              const statusSources = (item.status_sources || []) as unknown[];
              return (
                <div key={String(item.venue || item.id || "venue")} className="rounded-md border border-border/40 bg-black/20 px-3 py-2 text-xs">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium uppercase">{String(item.venue || "all")}</span>
                    <span className="font-mono text-muted-foreground">{formatCompact(item.requirement_count || 1)} req</span>
                  </div>
                  <div className="mt-1 line-clamp-2 text-muted-foreground">
                    ids: {identifiers.slice(0, 4).map(String).join(", ") || String(item.id || "mapped")}
                  </div>
                  <div className="mt-1 line-clamp-2 text-muted-foreground">
                    proof: {statusSources.slice(0, 3).map(String).join(", ") || String(item.source || "broker")}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {missing.length ? (
          <div className="flex flex-wrap gap-1">
            {missing.slice(0, 8).map((item) => (
              <Pill key={item} label={item.replace(/_/g, " ")} tone={statusTone.orphaned} />
            ))}
          </div>
        ) : null}

        {sandboxMissing.length ? (
          <div className="flex flex-wrap gap-1">
            {sandboxMissing.slice(0, 8).map((item) => (
              <Pill key={item} label={item.replace(/_/g, " ")} tone={statusTone.orphaned} />
            ))}
          </div>
        ) : null}

        {blockers.length ? (
          <div className="flex flex-wrap gap-1">
            {blockers.slice(0, 8).map((blocker) => (
              <Pill key={blocker} label={blocker.replace(/_/g, " ")} tone={statusTone.security_blocker} />
            ))}
          </div>
        ) : null}

        {sandboxBlockers.length ? (
          <div className="flex flex-wrap gap-1">
            {sandboxBlockers.slice(0, 8).map((blocker) => (
              <Pill key={blocker} label={blocker.replace(/_/g, " ")} tone={statusTone.security_blocker} />
            ))}
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}

function GlobalFinancialCoveragePanel({ coverage }: { coverage: GlobalFinancialCoverageMap | null }) {
  const summary = coverage?.summary || {};
  const rows = coverage?.rows || [];
  const sources = coverage?.source_registry || [];
  const blockedSources = sources.filter((source) => !source.usable_for_mapping).slice(0, 8);
  const missing = (summary.top_missing || []).slice(0, 6);
  const coveragePercent = Math.round(asNumber(summary.coverage_percent));
  const accountedPercent = Math.round(asNumber(summary.accounted_percent));

  return (
    <Card className="mt-4 bg-card/80">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <LineChart className="h-4 w-4 text-primary" />
          Global Financial Coverage Map
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-wrap items-center gap-2">
          <Pill
            label={coverage?.status ? String(coverage.status).replace(/_/g, " ") : "coverage map pending"}
            tone={summary.mapping_complete ? statusTone.wired : statusTone.partial}
          />
          <Pill
            label={coverage?.generated_at ? `updated ${new Date(coverage.generated_at).toLocaleTimeString()}` : "no map timestamp"}
            tone="border-border bg-muted/20 text-muted-foreground"
          />
          <Pill label="/aureon_global_financial_coverage_map.json" tone="border-primary/30 bg-primary/10 text-primary" />
        </div>

        <div className="rounded-md border border-primary/30 bg-primary/10 p-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <div className="text-[11px] uppercase text-primary/80">configured source coverage</div>
              <div className="mt-1 text-lg font-semibold text-primary">{coveragePercent}% mapped</div>
              <div className="mt-1 text-xs text-primary/70">
                {formatCompact(summary.usable_source_count)}/{formatCompact(summary.configured_reachable_source_count)} configured/reachable sources usable; {accountedPercent}% accounted.
              </div>
            </div>
            <Pill
              label={summary.mapping_complete ? "100% mapped for configured registry" : "expanding map"}
              tone={summary.mapping_complete ? statusTone.wired : statusTone.partial}
            />
          </div>
          <Progress value={coveragePercent} className="mt-3 h-2" />
        </div>

        <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-6">
          <div className="rounded-md border border-border/40 bg-muted/10 p-3">
            <div className="text-[11px] uppercase text-muted-foreground">usable domains</div>
            <div className="mt-1 text-lg font-semibold">{formatCompact(summary.usable_domain_count)}/{formatCompact(summary.domain_count)}</div>
          </div>
          <div className="rounded-md border border-border/40 bg-muted/10 p-3">
            <div className="text-[11px] uppercase text-muted-foreground">fresh domains</div>
            <div className="mt-1 text-lg font-semibold">{formatCompact(summary.fresh_domain_count)}</div>
          </div>
          <div className="rounded-md border border-border/40 bg-muted/10 p-3">
            <div className="text-[11px] uppercase text-muted-foreground">live tickers</div>
            <div className="mt-1 text-lg font-semibold">{formatCompact(summary.live_ticker_count)}</div>
          </div>
          <div className="rounded-md border border-border/40 bg-muted/10 p-3">
            <div className="text-[11px] uppercase text-muted-foreground">live sources</div>
            <div className="mt-1 text-lg font-semibold">{formatCompact(summary.active_live_source_count)}</div>
          </div>
          <div className="rounded-md border border-border/40 bg-muted/10 p-3">
            <div className="text-[11px] uppercase text-muted-foreground">history rows</div>
            <div className="mt-1 text-lg font-semibold">{formatCompact(summary.total_history_rows)}</div>
          </div>
          <div className="rounded-md border border-border/40 bg-muted/10 p-3">
            <div className="text-[11px] uppercase text-muted-foreground">missing creds</div>
            <div className="mt-1 text-lg font-semibold text-warning">{formatCompact(summary.credential_missing_source_count)}</div>
          </div>
        </div>

        {missing.length ? (
          <div className="space-y-2">
            <div className="text-xs uppercase text-muted-foreground">Map gaps</div>
            {missing.map((item, index) => (
              <div key={`${String(item.domain)}-${index}`} className="rounded-md border border-warning/30 bg-warning/10 px-3 py-2 text-xs">
                <span className="font-semibold text-warning">{String(item.domain || "unknown")}</span>
                <span className="ml-2 text-warning/80">{String(item.missing || "")}</span>
              </div>
            ))}
          </div>
        ) : null}

        {blockedSources.length ? (
          <div className="space-y-2">
            <div className="text-xs uppercase text-muted-foreground">Source registry gaps</div>
            {blockedSources.map((source) => (
              <div key={source.source_id} className="rounded-md border border-border/40 bg-muted/10 px-3 py-2 text-xs">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-semibold">{source.title || source.source_id}</span>
                  <div className="flex flex-wrap gap-1">
                    <Pill label={source.credential_state || "unknown"} tone={source.credential_state === "missing" ? statusTone.security_blocker : statusTone.partial} />
                    <Pill label={source.governor_action || "checking"} tone={source.usable_for_mapping ? statusTone.wired : statusTone.orphaned} />
                  </div>
                </div>
                <div className="mt-1 text-muted-foreground">{source.reason || source.next_action || "No blocker detail."}</div>
                {source.decision_blocker ? <div className="mt-1 text-warning">Decision hold: {source.decision_blocker.replace(/_/g, " ")}</div> : null}
                <div className="mt-2 flex flex-wrap gap-1">
                  {(source.asset_classes || []).slice(0, 5).map((assetClass) => (
                    <Pill key={`${source.source_id}-${assetClass}`} label={assetClass.replace(/_/g, " ")} tone="border-primary/30 bg-primary/10 text-primary" />
                  ))}
                </div>
              </div>
            ))}
          </div>
        ) : null}

        <ScrollArea className="h-[235px] pr-3">
          <div className="space-y-2">
            {rows.length ? (
              rows.map((row) => (
                <div key={row.domain} className="rounded-md border border-border/40 bg-muted/10 p-3">
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div className="min-w-0">
                      <div className="text-sm font-medium">{row.domain.replace(/_/g, " ")}</div>
                      <div className="mt-1 text-xs text-muted-foreground">{row.coverage}</div>
                    </div>
                    <div className="flex flex-wrap gap-1">
                      <Pill label={row.fresh ? "fresh" : "not fresh"} tone={row.fresh ? statusTone.wired : statusTone.partial} />
                      <Pill label={row.usable ? "usable" : "gap"} tone={row.usable ? statusTone.wired : statusTone.orphaned} />
                    </div>
                  </div>
                  <div className="mt-2 grid gap-2 sm:grid-cols-2">
                    <div className="rounded-md border border-border/40 bg-background/30 px-2 py-1">
                      <div className="text-[10px] uppercase text-muted-foreground">live count</div>
                      <div className="font-mono text-xs">{formatCompact(row.live_count)}</div>
                    </div>
                    <div className="rounded-md border border-border/40 bg-background/30 px-2 py-1">
                      <div className="text-[10px] uppercase text-muted-foreground">history count</div>
                      <div className="font-mono text-xs">{formatCompact(row.history_count)}</div>
                    </div>
                  </div>
                  {row.next_action ? <div className="mt-2 text-xs text-muted-foreground">{row.next_action}</div> : null}
                </div>
              ))
            ) : (
              <div className="rounded-md border border-border/40 bg-muted/10 p-4 text-sm text-muted-foreground">
                Coverage map not generated yet. Run python -m aureon.autonomous.aureon_global_financial_coverage_map.
              </div>
            )}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}

function ExchangeMonitoringChecklistPanel({ checklist }: { checklist: ExchangeMonitoringChecklist | null }) {
  const summary = checklist?.summary || {};
  const rows = checklist?.rows || [];
  const missing = (summary.top_missing || []).slice(0, 6);

  return (
    <Card className="mt-4 bg-card/80">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <Radio className="h-4 w-4 text-primary" />
          Exchange Monitoring Checklist
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-wrap items-center gap-2">
          <Pill
            label={checklist?.status ? String(checklist.status).replace(/_/g, " ") : "exchange checklist pending"}
            tone={summary.runtime_stale ? statusTone.orphaned : statusTone.wired}
          />
          <Pill
            label={checklist?.generated_at ? `updated ${new Date(checklist.generated_at).toLocaleTimeString()}` : "no checklist timestamp"}
            tone="border-border bg-muted/20 text-muted-foreground"
          />
          <Pill label="/aureon_exchange_monitoring_checklist.json" tone="border-primary/30 bg-primary/10 text-primary" />
          {summary.stale_reason ? <Pill label={String(summary.stale_reason)} tone={statusTone.security_blocker} /> : null}
        </div>

        <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-6">
          <div className="rounded-md border border-border/40 bg-muted/10 p-3">
            <div className="text-[11px] uppercase text-muted-foreground">connected</div>
            <div className="mt-1 text-lg font-semibold">{formatCompact(summary.connected_exchange_count)}/{formatCompact(summary.exchange_count)}</div>
          </div>
          <div className="rounded-md border border-border/40 bg-muted/10 p-3">
            <div className="text-[11px] uppercase text-muted-foreground">active feeds</div>
            <div className="mt-1 text-lg font-semibold">{formatCompact(summary.active_exchange_count)}</div>
          </div>
          <div className="rounded-md border border-border/40 bg-muted/10 p-3">
            <div className="text-[11px] uppercase text-muted-foreground">fresh feeds</div>
            <div className="mt-1 text-lg font-semibold">{formatCompact(summary.fresh_exchange_count)}</div>
          </div>
          <div className="rounded-md border border-border/40 bg-muted/10 p-3">
            <div className="text-[11px] uppercase text-muted-foreground">decision fed</div>
            <div className="mt-1 text-lg font-semibold">{formatCompact(summary.decision_fed_exchange_count)}</div>
          </div>
          <div className="rounded-md border border-border/40 bg-muted/10 p-3">
            <div className="text-[11px] uppercase text-muted-foreground">waveforms</div>
            <div className="mt-1 text-lg font-semibold">{formatCompact(summary.waveform_history_exchange_count)}</div>
          </div>
          <div className="rounded-md border border-border/40 bg-muted/10 p-3">
            <div className="text-[11px] uppercase text-muted-foreground">tickers</div>
            <div className="mt-1 text-lg font-semibold">{formatCompact(summary.total_tickers_monitored)}</div>
          </div>
        </div>

        {missing.length ? (
          <div className="space-y-2">
            <div className="text-xs uppercase text-muted-foreground">Missing by exchange</div>
            {missing.map((item, index) => (
              <div key={`${String(item.exchange)}-${index}`} className="rounded-md border border-warning/30 bg-warning/10 px-3 py-2 text-xs">
                <span className="font-semibold text-warning">{String(item.exchange || "unknown")}</span>
                <span className="ml-2 text-warning/80">{String(item.missing || "")}</span>
              </div>
            ))}
          </div>
        ) : null}

        <ScrollArea className="h-[280px] pr-3">
          <div className="space-y-2">
            {rows.length ? (
              rows.map((row) => (
                <div key={row.exchange} className="rounded-md border border-border/40 bg-muted/10 p-3">
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div className="min-w-0">
                      <div className="text-sm font-medium">{row.label || row.exchange}</div>
                      <div className="mt-1 flex flex-wrap gap-1">
                        {(row.markets || []).slice(0, 4).map((market) => (
                          <Pill key={market} label={market.replace(/_/g, " ")} tone="border-primary/30 bg-primary/10 text-primary" />
                        ))}
                      </div>
                    </div>
                    <div className="flex flex-wrap gap-1">
                      <Pill label={row.connected ? "client ready" : "client missing"} tone={row.connected ? statusTone.wired : statusTone.orphaned} />
                      <Pill label={row.cache_fresh ? "fresh feed" : row.cache_active ? "feed stale" : "feed missing"} tone={row.cache_fresh ? statusTone.wired : statusTone.partial} />
                      <Pill label={row.feeds_decision_logic ? "decision fed" : "not fed"} tone={row.feeds_decision_logic ? statusTone.wired : statusTone.orphaned} />
                    </div>
                  </div>
                  <div className="mt-3 grid gap-2 sm:grid-cols-4">
                    <div className="rounded-md border border-border/40 bg-background/30 px-2 py-1">
                      <div className="text-[10px] uppercase text-muted-foreground">tickers</div>
                      <div className="font-mono text-xs">{formatCompact(row.ticker_count)}</div>
                    </div>
                    <div className="rounded-md border border-border/40 bg-background/30 px-2 py-1">
                      <div className="text-[10px] uppercase text-muted-foreground">venues</div>
                      <div className="font-mono text-xs">{formatCompact(row.action_plan_venue_count)}</div>
                    </div>
                    <div className="rounded-md border border-border/40 bg-background/30 px-2 py-1">
                      <div className="text-[10px] uppercase text-muted-foreground">waveform</div>
                      <div className="font-mono text-xs">{row.waveform_history_active ? "active" : "missing"}</div>
                    </div>
                    <div className="rounded-md border border-border/40 bg-background/30 px-2 py-1">
                      <div className="text-[10px] uppercase text-muted-foreground">fast money</div>
                      <div className="font-mono text-xs">{row.usable_for_fast_money ? "usable" : "held"}</div>
                    </div>
                  </div>
                  <div className="mt-2 flex flex-wrap gap-1">
                    {(row.monitored_now || []).slice(0, 6).map((item) => (
                      <Pill key={item} label={item.replace(/_/g, " ")} tone="border-success/30 bg-success/10 text-success" />
                    ))}
                  </div>
                  {(row.missing || []).length ? (
                    <div className="mt-2 text-xs text-warning">{(row.missing || []).slice(0, 5).join(", ")}</div>
                  ) : null}
                </div>
              ))
            ) : (
              <div className="rounded-md border border-border/40 bg-muted/10 p-4 text-sm text-muted-foreground">
                Exchange checklist not generated yet. Run python -m aureon.autonomous.aureon_exchange_monitoring_checklist.
              </div>
            )}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}

function ExchangeDataCapabilityMatrixPanel({ matrix }: { matrix: ExchangeDataCapabilityMatrix | null }) {
  const summary = matrix?.summary || {};
  const rows = matrix?.rows || [];

  return (
    <Card className="mt-4 bg-card/80">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <Database className="h-4 w-4 text-primary" />
          Exchange Data Capability Matrix
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-wrap items-center gap-2">
          <Pill
            label={matrix?.status ? String(matrix.status).replace(/_/g, " ") : "capability matrix pending"}
            tone={summary.runtime_stale ? statusTone.orphaned : summary.runtime_booting || summary.trading_ready === false || summary.data_ready === false ? statusTone.partial : statusTone.wired}
          />
          <Pill
            label={matrix?.generated_at ? `updated ${new Date(matrix.generated_at).toLocaleTimeString()}` : "no matrix timestamp"}
            tone="border-border bg-muted/20 text-muted-foreground"
          />
          <Pill label="/aureon_exchange_data_capability_matrix.json" tone="border-primary/30 bg-primary/10 text-primary" />
          {summary.stale_reason ? <Pill label={String(summary.stale_reason)} tone={statusTone.security_blocker} /> : null}
        </div>

        <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-6">
          <div className="rounded-md border border-border/40 bg-muted/10 p-3">
            <div className="text-[11px] uppercase text-muted-foreground">connected</div>
            <div className="mt-1 text-lg font-semibold">{formatCompact(summary.connected_exchange_count)}/{formatCompact(summary.exchange_count)}</div>
          </div>
          <div className="rounded-md border border-border/40 bg-muted/10 p-3">
            <div className="text-[11px] uppercase text-muted-foreground">fresh feeds</div>
            <div className="mt-1 text-lg font-semibold">{formatCompact(summary.fresh_feed_count)}</div>
          </div>
          <div className="rounded-md border border-border/40 bg-muted/10 p-3">
            <div className="text-[11px] uppercase text-muted-foreground">decision fed</div>
            <div className="mt-1 text-lg font-semibold">{formatCompact(summary.decision_fed_count)}</div>
          </div>
          <div className="rounded-md border border-border/40 bg-muted/10 p-3">
            <div className="text-[11px] uppercase text-muted-foreground">cash active</div>
            <div className="mt-1 text-lg font-semibold">{formatCompact(summary.cash_active_exchange_count)}</div>
          </div>
          <div className="rounded-md border border-border/40 bg-muted/10 p-3">
            <div className="text-[11px] uppercase text-muted-foreground">data boost</div>
            <div className="mt-1 text-lg font-semibold">{formatCompact(summary.data_boost_eligible_count)}</div>
          </div>
          <div className="rounded-md border border-border/40 bg-muted/10 p-3">
            <div className="text-[11px] uppercase text-muted-foreground">tickers</div>
            <div className="mt-1 text-lg font-semibold">{formatCompact(summary.total_ticker_count)}</div>
          </div>
        </div>

        <ScrollArea className="h-[360px] pr-3">
          <div className="space-y-3">
            {rows.length ? (
              rows.map((row) => {
                const state = row.current_state || {};
                const policy = row.optimization_policy || {};
                return (
                  <div key={row.exchange} className="rounded-md border border-border/40 bg-muted/10 p-3">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div className="min-w-0">
                        <div className="text-sm font-medium">{row.label || row.exchange}</div>
                        {row.system_role ? <div className="mt-1 text-xs text-muted-foreground">{row.system_role}</div> : null}
                      </div>
                      <div className="flex flex-wrap gap-1">
                        <Pill label={state.connected ? "client ready" : "client missing"} tone={state.connected ? statusTone.wired : statusTone.orphaned} />
                        <Pill label={state.fresh_feed ? "fresh feed" : state.active_feed ? "feed stale" : "feed missing"} tone={state.fresh_feed ? statusTone.wired : statusTone.partial} />
                        <Pill label={policy.data_boost_eligible ? "data boost" : "execution reserve"} tone={policy.data_boost_eligible ? "border-primary/30 bg-primary/10 text-primary" : "border-warning/30 bg-warning/10 text-warning"} />
                      </div>
                    </div>

                    <div className="mt-3 grid gap-2 sm:grid-cols-4">
                      <div className="rounded-md border border-border/40 bg-background/30 px-2 py-1">
                        <div className="text-[10px] uppercase text-muted-foreground">safe calls/min</div>
                        <div className="font-mono text-xs">{formatCompact(policy.safe_calls_per_min)}</div>
                      </div>
                      <div className="rounded-md border border-border/40 bg-background/30 px-2 py-1">
                        <div className="text-[10px] uppercase text-muted-foreground">market data/min</div>
                        <div className="font-mono text-xs">{formatCompact(policy.market_data_budget_per_min)}</div>
                      </div>
                      <div className="rounded-md border border-border/40 bg-background/30 px-2 py-1">
                        <div className="text-[10px] uppercase text-muted-foreground">reserve/min</div>
                        <div className="font-mono text-xs">{formatCompact(policy.execution_reserved_per_min)}</div>
                      </div>
                      <div className="rounded-md border border-border/40 bg-background/30 px-2 py-1">
                        <div className="text-[10px] uppercase text-muted-foreground">cash estimate</div>
                        <div className="font-mono text-xs">{formatCompact(policy.cash_usd_estimate)}</div>
                      </div>
                    </div>

                    <div className="mt-2 flex flex-wrap gap-1">
                      {(row.trading_modes || []).slice(0, 5).map((mode) => (
                        <Pill key={`${row.exchange}-${mode}`} label={mode.replace(/_/g, " ")} tone="border-primary/30 bg-primary/10 text-primary" />
                      ))}
                    </div>

                    <div className="mt-3 grid gap-2 lg:grid-cols-2">
                      {(row.data_channels || []).slice(0, 6).map((channel) => (
                        <div key={`${row.exchange}-${channel.name}`} className="rounded-md border border-border/40 bg-background/30 px-2 py-2">
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <div className="text-xs font-medium">{channel.name.replace(/_/g, " ")}</div>
                            <Pill label={String(channel.status || "mapped").replace(/_/g, " ")} tone={String(channel.status || "").includes("missing") ? statusTone.orphaned : statusTone.wired} />
                          </div>
                          <div className="mt-1 text-[11px] text-muted-foreground">{channel.optimization_use || channel.source}</div>
                        </div>
                      ))}
                    </div>

                    {row.next_optimization ? <div className="mt-3 text-xs text-foreground">{row.next_optimization}</div> : null}
                    {(row.gaps || []).length ? <div className="mt-2 text-xs text-warning">{(row.gaps || []).slice(0, 5).join(", ")}</div> : null}
                  </div>
                );
              })
            ) : (
              <div className="rounded-md border border-border/40 bg-muted/10 p-4 text-sm text-muted-foreground">
                Capability matrix not generated yet. Run python -m aureon.autonomous.aureon_exchange_data_capability_matrix.
              </div>
            )}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}

function TradingIntelligenceChecklistPanel({ checklist }: { checklist: TradingIntelligenceChecklist | null }) {
  const summary = checklist?.summary || {};
  const trust = checklist?.decision_trust;
  const rows = checklist?.rows || [];
  const metaContext = summary.metacognitive_data_context;
  const blockers = (summary.top_blockers || []).slice(0, 5);
  const criticalRows = rows
    .filter((row) => row.blocker || !row.usable_for_decision)
    .slice(0, 8);
  const categoryRows = [
    { label: "direct live", value: summary.direct_live_systems_passing, total: rows.filter((row) => row.category === "live_market_intelligence").length },
    { label: "HNC/Auris", value: summary.hnc_auris_passing, total: rows.filter((row) => row.category === "hnc_auris_cognition").length },
    { label: "counter intel", value: summary.counter_intelligence_passing, total: rows.filter((row) => row.category === "counter_intelligence_validation").length },
    { label: "profit timing", value: summary.profit_timing_passing, total: rows.filter((row) => row.category === "profit_timing").length },
    { label: "meta context", value: summary.metacognitive_context_passing, total: rows.filter((row) => row.category === "metacognitive_data_context").length },
  ];

  return (
    <Card className="mt-4 bg-card/80">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <ShieldCheck className="h-4 w-4 text-primary" />
          Trading Intelligence Freshness Checklist
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-wrap items-center gap-2">
          <Pill
            label={checklist?.status ? String(checklist.status).replace(/_/g, " ") : "checklist pending"}
            tone={summary.runtime_fresh ? statusTone.wired : statusTone.orphaned}
          />
          <Pill
            label={checklist?.generated_at ? `updated ${new Date(checklist.generated_at).toLocaleTimeString()}` : "no checklist timestamp"}
            tone="border-border bg-muted/20 text-muted-foreground"
          />
          <Pill label="/aureon_trading_intelligence_checklist.json" tone="border-primary/30 bg-primary/10 text-primary" />
          {summary.stale_reason ? <Pill label={String(summary.stale_reason)} tone={statusTone.security_blocker} /> : null}
        </div>

        <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-6">
          <div className="rounded-md border border-border/40 bg-muted/10 p-3">
            <div className="text-[11px] uppercase text-muted-foreground">fresh usable</div>
            <div className="mt-1 text-lg font-semibold">{formatCompact(summary.fresh_usable_count)}/{formatCompact(summary.system_count)}</div>
          </div>
          <div className="rounded-md border border-border/40 bg-muted/10 p-3">
            <div className="text-[11px] uppercase text-muted-foreground">decision fed</div>
            <div className="mt-1 text-lg font-semibold">{formatCompact(summary.decision_fed_count)}</div>
          </div>
          <div className="rounded-md border border-border/40 bg-muted/10 p-3">
            <div className="text-[11px] uppercase text-muted-foreground">present</div>
            <div className="mt-1 text-lg font-semibold">{formatCompact(summary.present_count)}</div>
          </div>
          <div className="rounded-md border border-border/40 bg-muted/10 p-3">
            <div className="text-[11px] uppercase text-muted-foreground">active</div>
            <div className="mt-1 text-lg font-semibold">{formatCompact(summary.active_count)}</div>
          </div>
          <div className="rounded-md border border-border/40 bg-muted/10 p-3">
            <div className="text-[11px] uppercase text-muted-foreground">stale/blocked</div>
            <div className="mt-1 text-lg font-semibold text-warning">{formatCompact(summary.stale_or_blocked_count)}</div>
          </div>
          <div className="rounded-md border border-border/40 bg-muted/10 p-3">
            <div className="text-[11px] uppercase text-muted-foreground">self trust</div>
            <div className="mt-1 text-lg font-semibold">{Math.round(asNumber(summary.decision_self_trust_score) * 100)}%</div>
          </div>
        </div>

        {trust ? (
          <div className="rounded-md border border-primary/30 bg-primary/10 p-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <div className="text-[11px] uppercase text-primary/80">decision posture</div>
                <div className="mt-1 font-mono text-sm font-semibold text-primary">
                  {String(trust.posture || summary.decision_posture || "checking").replace(/_/g, " ")}
                </div>
              </div>
              <div className="flex flex-wrap gap-1">
                <Pill label={trust.trust_to_decide ? "trusts decision" : "still measuring"} tone={trust.trust_to_decide ? statusTone.wired : statusTone.orphaned} />
                <Pill label={trust.trust_to_act ? "live intent ready" : trust.trust_to_shadow ? "shadow ready" : "learning"} tone={trust.trust_to_act ? statusTone.wired : statusTone.partial} />
              </div>
            </div>
            <div className="mt-2 text-xs text-primary/80">{trust.self_instruction}</div>
            <div className="mt-1 text-[11px] text-primary/60">{trust.not_fear_reason}</div>
          </div>
        ) : null}

        {metaContext?.present ? (
          <div className="rounded-md border border-success/30 bg-success/10 p-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <div className="text-[11px] uppercase text-success/80">metacognitive data ocean</div>
                <div className="mt-1 text-sm text-success">
                  {metaContext.state_phrase || "Global data context is being measured."}
                </div>
              </div>
              <div className="flex flex-wrap gap-1">
                <Pill
                  label={metaContext.usable_for_metacognition ? "usable for thought" : "filling gaps"}
                  tone={metaContext.usable_for_metacognition ? statusTone.wired : statusTone.partial}
                />
                <Pill
                  label={metaContext.usable_for_live_decision ? "live decision usable" : "runtime gated"}
                  tone={metaContext.usable_for_live_decision ? statusTone.wired : statusTone.orphaned}
                />
              </div>
            </div>
            <div className="mt-3 grid gap-2 sm:grid-cols-2 xl:grid-cols-5">
              <div className="rounded-md border border-success/20 bg-background/30 p-2">
                <div className="text-[10px] uppercase text-success/70">mapped</div>
                <div className="font-mono text-sm text-success">{Math.round(asNumber(metaContext.coverage_percent))}%</div>
              </div>
              <div className="rounded-md border border-success/20 bg-background/30 p-2">
                <div className="text-[10px] uppercase text-success/70">live sources</div>
                <div className="font-mono text-sm text-success">{formatCompact(metaContext.active_live_source_count)}</div>
              </div>
              <div className="rounded-md border border-success/20 bg-background/30 p-2">
                <div className="text-[10px] uppercase text-success/70">tickers</div>
                <div className="font-mono text-sm text-success">{formatCompact(metaContext.live_ticker_count)}</div>
              </div>
              <div className="rounded-md border border-success/20 bg-background/30 p-2">
                <div className="text-[10px] uppercase text-success/70">history rows</div>
                <div className="font-mono text-sm text-success">{formatCompact(metaContext.history_rows)}</div>
              </div>
              <div className="rounded-md border border-success/20 bg-background/30 p-2">
                <div className="text-[10px] uppercase text-success/70">cleanliness</div>
                <div className="font-mono text-sm text-success">{Math.round(asNumber(metaContext.cognitive_cleanliness_score) * 100)}%</div>
              </div>
            </div>
            {metaContext.decision_blocker ? <div className="mt-2 text-[11px] text-warning">{metaContext.decision_blocker}</div> : null}
          </div>
        ) : null}

        <div className="grid gap-2 md:grid-cols-5">
          {categoryRows.map((item) => (
            <div key={item.label} className="rounded-md border border-border/40 bg-muted/10 p-3">
              <div className="text-[11px] uppercase text-muted-foreground">{item.label}</div>
              <div className="mt-1 font-mono text-sm font-semibold">{formatCompact(item.value)}/{formatCompact(item.total)}</div>
            </div>
          ))}
        </div>

        {blockers.length ? (
          <div className="space-y-2">
            <div className="text-xs uppercase text-muted-foreground">Top blockers</div>
            {blockers.map((blocker, index) => (
              <div key={`${String(blocker.system)}-${index}`} className="rounded-md border border-warning/30 bg-warning/10 px-3 py-2 text-xs">
                <span className="font-semibold text-warning">{String(blocker.system || "unknown")}</span>
                <span className="ml-2 text-warning/80">{String(blocker.blocker || "")}</span>
              </div>
            ))}
          </div>
        ) : null}

        <ScrollArea className="h-[260px] pr-3">
          <div className="space-y-2">
            {(criticalRows.length ? criticalRows : rows.slice(0, 8)).map((row) => (
              <div key={`${row.system}-${row.downstream_stage}`} className="rounded-md border border-border/40 bg-muted/10 p-3">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div className="min-w-0">
                    <div className="text-sm font-medium">{row.system}</div>
                    <div className="mt-1 truncate font-mono text-[11px] text-muted-foreground">{row.evidence_source}</div>
                  </div>
                  <div className="flex flex-wrap gap-1">
                    <Pill label={row.downstream_stage.replace(/_/g, " ")} tone="border-primary/30 bg-primary/10 text-primary" />
                    <Pill label={row.fed_to_decision_logic ? "decision fed" : "not fed"} tone={row.fed_to_decision_logic ? statusTone.wired : statusTone.partial} />
                    <Pill label={row.usable_for_decision ? "fresh usable" : "held"} tone={row.usable_for_decision ? statusTone.wired : statusTone.orphaned} />
                  </div>
                </div>
                {row.blocker ? <div className="mt-2 text-xs text-warning">{row.blocker}</div> : null}
              </div>
            ))}
            {!rows.length ? (
              <div className="rounded-md border border-border/40 bg-muted/10 p-4 text-sm text-muted-foreground">
                Checklist not generated yet. Run python -m aureon.autonomous.aureon_trading_intelligence_checklist.
              </div>
            ) : null}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}

function surfaceSearchText(surface: ReturnType<typeof surfacesForScreen>[number]): string {
  return [
    surface.path,
    surface.purpose,
    surface.wiring_status,
    surface.safety_class,
    surface.missing_next_step,
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
}

function matchesSurfaceFilter(surface: ReturnType<typeof surfacesForScreen>[number], filter: SurfaceFilter): boolean {
  const text = surfaceSearchText(surface);
  if (filter === "observation") return surface.safety_class === "observation";
  if (filter === "security") return text.includes("security") || text.includes("boundary") || text.includes("blocker");
  if (filter === "live") return text.includes("live") || text.includes("trading") || text.includes("order");
  if (filter === "credential") return text.includes("credential") || text.includes("auth") || text.includes("key");
  if (filter === "missing") return Boolean(surface.missing_next_step) || surface.wiring_status === "orphaned" || surface.wiring_status === "partial";
  return true;
}

function ScreenPanel({
  screen,
  inventory,
  surfaceQuery = "",
  surfaceFilter = "all",
}: {
  screen: FrontendScreenPlan;
  inventory: SaaSInventoryManifest;
  surfaceQuery?: string;
  surfaceFilter?: SurfaceFilter;
}) {
  const query = surfaceQuery.trim().toLowerCase();
  const allSurfaces = surfacesForScreen(inventory, screen);
  const surfaces = allSurfaces.filter((surface) => {
    const matchesQuery = !query || surfaceSearchText(surface).includes(query);
    return matchesQuery && matchesSurfaceFilter(surface, surfaceFilter);
  });
  const Icon = screenIcons[screen.id] || Activity;

  return (
    <div className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
      <Card className="bg-card/80">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <Icon className="h-4 w-4 text-primary" />
            {screen.title}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">{screen.goal}</p>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <div className="rounded-md border border-border/40 bg-muted/10 p-3">
              <div className="text-xs text-muted-foreground">sources</div>
              <div className="mt-1 text-lg font-semibold">{screen.source_surface_count}</div>
            </div>
            <div className="rounded-md border border-border/40 bg-muted/10 p-3">
              <div className="text-xs text-muted-foreground">canonical</div>
              <div className="mt-1 text-lg font-semibold">{screen.canonical_sources.length}</div>
            </div>
            <div className="rounded-md border border-border/40 bg-muted/10 p-3">
              <div className="text-xs text-muted-foreground">legacy</div>
              <div className="mt-1 text-lg font-semibold">{screen.embedded_legacy_surfaces.length}</div>
            </div>
            <div className="rounded-md border border-border/40 bg-muted/10 p-3">
              <div className="text-xs text-muted-foreground">outputs</div>
              <div className="mt-1 text-lg font-semibold">{screen.generated_outputs.length}</div>
            </div>
          </div>

          <div className="space-y-2">
            <div className="text-xs uppercase text-muted-foreground">Safety notes</div>
            {screen.safety_notes.length ? (
              <div className="flex flex-wrap gap-2">
                {screen.safety_notes.map((note) => (
                  <Pill key={note} label={note} tone="border-warning/30 bg-warning/10 text-warning" />
                ))}
              </div>
            ) : (
              <div className="text-sm text-muted-foreground">Observation-only screen.</div>
            )}
          </div>

          {screen.missing_capabilities.length ? (
            <div className="space-y-2">
              <div className="text-xs uppercase text-muted-foreground">Missing or blocked</div>
              {screen.missing_capabilities.map((item) => (
                <div key={item} className="rounded-md border border-warning/30 bg-warning/10 px-3 py-2 text-sm text-warning">
                  {item}
                </div>
              ))}
            </div>
          ) : null}
        </CardContent>
      </Card>

      <Card className="bg-card/80">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <FileText className="h-4 w-4 text-primary" />
            Source Surfaces
            <Pill label={`${formatCompact(surfaces.length)}/${formatCompact(allSurfaces.length)}`} tone="border-border bg-muted/20 text-muted-foreground" />
          </CardTitle>
        </CardHeader>
        <CardContent>
          <ScrollArea className="h-[420px] pr-3">
            <div className="space-y-3">
              {surfaces.length ? (
                surfaces.map((surface) => (
                  <div key={surface.id} className="rounded-md border border-border/40 bg-muted/10 p-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="min-w-0">
                        <div className="truncate font-mono text-xs text-foreground">{surface.path}</div>
                        <div className="mt-1 text-xs text-muted-foreground">{surface.purpose}</div>
                      </div>
                      <div className="flex flex-wrap gap-1">
                        <Pill label={surface.wiring_status} tone={statusTone[surface.wiring_status] || statusTone.unknown} />
                        <Pill label={surface.safety_class} tone={safetyTone[surface.safety_class] || statusTone.unknown} />
                      </div>
                    </div>
                    {surface.missing_next_step ? (
                      <div className="mt-2 text-xs text-muted-foreground">{surface.missing_next_step}</div>
                    ) : null}
                  </div>
                ))
              ) : (
                <div className="rounded-md border border-border/40 bg-muted/10 p-4 text-sm text-muted-foreground">
                  No matching surfaces in the current manifest.
                </div>
              )}
            </div>
          </ScrollArea>
        </CardContent>
      </Card>
    </div>
  );
}

const App = () => (
  <ThemeProvider defaultTheme="dark">
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <Toaster />
        <Sonner />
        <AppShell />
      </TooltipProvider>
    </QueryClientProvider>
  </ThemeProvider>
);

// The inner nine-tab console, mountable inside the unified shell (which
// provides its own theme/query/tooltip/toaster providers).
export { AppShell as LegacyConsole };

export default App;
