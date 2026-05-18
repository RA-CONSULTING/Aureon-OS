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
import {
  CapabilitySwitchboardManifest,
  FrontendScreenPlan,
  FrontendEvolutionQueueManifest,
  loadUnifiedFrontendState,
  OrganismDomainPulse,
  SaaSInventoryManifest,
  surfacesForScreen,
  UnifiedFrontendState,
} from "@/services/aureonAutonomousFrontend";

const queryClient = new QueryClient();
const ENV_LOCAL_TERMINAL_ENDPOINT = import.meta.env.VITE_LOCAL_TERMINAL_URL as string | undefined;
const DEFAULT_RUNTIME_ENDPOINTS = [
  ENV_LOCAL_TERMINAL_ENDPOINT,
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
    candidate_count?: number;
    trade_ready_candidate_count?: number;
    net_positive_candidate_count?: number;
    revenue_intent_candidate_count?: number;
    false_positive_reject_count?: number;
    active_watchlist_count?: number;
    active_watchlist_limit?: number;
    bench_watchlist_count?: number;
    bench_watchlist_limit?: number;
    gold_preserved?: boolean;
    shadow_hedge_count?: number;
    shadow_hedges_only?: boolean;
    close_first_opportunity_count?: number;
    active_lifecycle_route_count?: number;
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
    candidate_count?: number;
    trade_ready_candidate_count?: number;
    net_positive_candidate_count?: number;
    intent_eligible_candidate_count?: number;
    candidate_level_intent_eligible_count?: number;
    false_positive_reject_count?: number;
    active_watchlist_count?: number;
    bench_watchlist_count?: number;
    close_first_opportunity_count?: number;
    duplicate_route_blocked_count?: number;
    shadow_confirmation_count?: number;
    external_shadow_only?: boolean;
    live_gates_blocking?: boolean;
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
    net_positive_candidate_count?: number;
    ready_now_candidate_count?: number;
    blocked_candidate_count?: number;
    missing_gate_count?: number;
    runtime_gates_clear?: boolean;
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
  wired: "border-green-500/30 bg-green-500/10 text-green-300",
  partial: "border-blue-500/30 bg-blue-500/10 text-blue-300",
  orphaned: "border-yellow-500/30 bg-yellow-500/10 text-yellow-300",
  legacy: "border-orange-500/30 bg-orange-500/10 text-orange-300",
  generated_output: "border-cyan-500/30 bg-cyan-500/10 text-cyan-300",
  security_blocker: "border-red-500/30 bg-red-500/10 text-red-300",
  unknown: "border-border bg-muted/20 text-muted-foreground",
};

const safetyTone: Record<string, string> = {
  observation: "border-green-500/30 bg-green-500/10 text-green-300",
  credential_or_auth_boundary: "border-yellow-500/30 bg-yellow-500/10 text-yellow-300",
  live_trading_boundary: "border-red-500/30 bg-red-500/10 text-red-300",
  payment_or_kyc_boundary: "border-red-500/30 bg-red-500/10 text-red-300",
  manual_filing_boundary: "border-orange-500/30 bg-orange-500/10 text-orange-300",
  admin_or_tenant_boundary: "border-yellow-500/30 bg-yellow-500/10 text-yellow-300",
};

type DashboardTabId = "overview" | "live-ops" | "coding" | "trading" | "security" | "inventory" | "agents" | "evidence";
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
    <Card className="border-yellow-500/30 bg-yellow-500/10">
      <CardHeader className="pb-3">
        <CardTitle className="flex flex-wrap items-center gap-2 text-base">
          <Lock className="h-4 w-4 text-yellow-200" />
          {blocker.title}
          <Pill label={blocker.priority} tone="border-yellow-500/40 bg-yellow-500/15 text-yellow-100" />
          <Pill label={blocker.status} tone="border-red-500/35 bg-red-500/10 text-red-200" />
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
            <div className="mt-2 text-xs text-yellow-100/80">{blocker.reason}</div>
          </div>
          <div className="rounded-md border border-border/40 bg-black/25 p-3">
            <div className="text-[11px] uppercase text-muted-foreground">next action</div>
            <div className="mt-1 text-xs text-foreground/85">{blocker.nextStep}</div>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          {blocker.boundaries.map((boundary) => (
            <Pill key={boundary} label={boundary} tone="border-yellow-500/30 bg-yellow-500/10 text-yellow-100" />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function SaaSCredentialManagementPanel({ comparison }: { comparison: HNCPacketSecurityComparison | null }) {
  return (
    <section className="space-y-4 rounded-md border border-green-500/30 bg-green-500/5 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="flex items-center gap-2 text-base font-semibold">
            <Lock className="h-4 w-4 text-green-300" />
            Secure exchange key management
          </h2>
          <p className="mt-1 max-w-4xl text-sm text-muted-foreground">
            Users can add, test, or update Binance, Kraken, Alpaca, and Capital credentials through the local .env path and optional user vault sync. Saved secrets are never printed back into the console.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Pill label="add or update keys" tone={statusTone.wired} />
          <Pill label="stored values hidden" tone="border-green-500/30 bg-green-500/10 text-green-200" />
          <Pill label="withdrawals must stay disabled" tone="border-yellow-500/30 bg-yellow-500/10 text-yellow-100" />
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
    <Card className="border-cyan-500/30 bg-cyan-500/5">
      <CardHeader className="pb-3">
        <CardTitle className="flex flex-wrap items-center justify-between gap-2 text-base">
          <span className="flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 text-cyan-300" />
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
    <Card className="border-sky-500/30 bg-sky-500/5">
      <CardHeader className="pb-3">
        <CardTitle className="flex flex-wrap items-center justify-between gap-2 text-base">
          <span className="flex items-center gap-2">
            <LineChart className="h-4 w-4 text-sky-300" />
            Capital Ecosystem Intelligence
          </span>
          <div className="flex flex-wrap gap-1">
            <Pill label={ready ? "ecosystem ready" : "ecosystem attention"} tone={ready ? statusTone.wired : statusTone.orphaned} />
            <Pill label={`${formatCompact(summary.active_watchlist_count)}/${formatCompact(summary.active_watchlist_limit || 40)} active`} tone="border-sky-500/30 bg-sky-500/10 text-sky-100" />
            <Pill label={`${formatCompact(summary.bench_watchlist_count)}/${formatCompact(summary.bench_watchlist_limit || 100)} bench`} tone="border-border bg-muted/20 text-muted-foreground" />
            <Pill label="/aureon_capital_ecosystem_intelligence_company.json" tone="border-cyan-500/30 bg-cyan-500/10 text-cyan-200" />
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
              <div className="mt-1 font-mono text-sm font-semibold text-sky-100">
                {typeof value === "number" ? formatCompact(value) : String(value ?? "0")}
              </div>
            </div>
          ))}
        </div>

        <div className="grid gap-3 xl:grid-cols-[1.1fr_0.9fr]">
          <div className="space-y-2">
            <div className="flex items-center justify-between gap-2">
              <div className="text-xs uppercase text-muted-foreground">Top velocity candidates</div>
              <Pill label="fast profit velocity" tone="border-sky-500/30 bg-sky-500/10 text-sky-100" />
            </div>
            <div className="grid gap-2 md:grid-cols-2">
              {topCandidates.length ? topCandidates.slice(0, 8).map((item) => (
                <div key={String(item.candidate_id || item.symbol)} className="rounded-md border border-border/40 bg-muted/10 px-3 py-2 text-xs">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium">{String(item.symbol || item.epic || "capital")}</span>
                    <span className="font-mono text-sky-100">{formatCompact(item.fast_profit_velocity_score)}</span>
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
    <Card className="border-emerald-500/30 bg-emerald-500/5">
      <CardHeader className="pb-3">
        <CardTitle className="flex flex-wrap items-center justify-between gap-2 text-base">
          <span className="flex items-center gap-2">
            <LineChart className="h-4 w-4 text-emerald-300" />
            Revenue Logic Stress
          </span>
          <div className="flex flex-wrap gap-1">
            <Pill label={statusLabel} tone={certified ? statusTone.wired : statusTone.orphaned} />
            <Pill label={`${formatCompact(summary.net_positive_candidate_count)} net-positive`} tone="border-emerald-500/30 bg-emerald-500/10 text-emerald-100" />
            <Pill label={`${formatCompact(summary.intent_eligible_candidate_count)} intent eligible`} tone={summary.intent_eligible_candidate_count ? statusTone.wired : statusTone.orphaned} />
            <Pill label="/aureon_capital_revenue_logic_stress_audit.json" tone="border-cyan-500/30 bg-cyan-500/10 text-cyan-200" />
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
              <div className="mt-1 font-mono text-sm font-semibold text-emerald-100">
                {typeof value === "number" ? formatCompact(value) : String(value ?? "0")}
              </div>
            </div>
          ))}
        </div>

        <div className="grid gap-3 xl:grid-cols-[1.1fr_0.9fr]">
          <div className="space-y-2">
            <div className="flex items-center justify-between gap-2">
              <div className="text-xs uppercase text-muted-foreground">Top net-positive candidates</div>
              <Pill label="after spread, fees, slippage, floor, risk" tone="border-emerald-500/30 bg-emerald-500/10 text-emerald-100" />
            </div>
            <div className="grid gap-2 md:grid-cols-2">
              {netRows.length ? netRows.slice(0, 8).map((item) => (
                <div key={String(item.candidate_id || item.route_key || item.symbol)} className="rounded-md border border-border/40 bg-muted/10 px-3 py-2 text-xs">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium">{String(item.symbol || item.epic || "capital")}</span>
                    <span className="font-mono text-emerald-100">{formatCompact(item.expected_net_revenue)}</span>
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
              <Pill label={`${formatCompact(summary.false_positive_reject_count)} rejected`} tone="border-amber-500/30 bg-amber-500/10 text-amber-100" />
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
    <Card className="border-sky-500/30 bg-sky-500/5">
      <CardHeader className="pb-3">
        <CardTitle className="flex flex-wrap items-center justify-between gap-2 text-base">
          <span className="flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 text-sky-300" />
            Live Gate Readiness
          </span>
          <div className="flex flex-wrap gap-1">
            <Pill label={statusLabel} tone={ready ? statusTone.wired : statusTone.orphaned} />
            <Pill label={`${formatCompact(summary.ready_now_candidate_count)} ready now`} tone={summary.ready_now_candidate_count ? statusTone.wired : statusTone.orphaned} />
            <Pill label={`${formatCompact(summary.missing_gate_count)} missing gates`} tone={summary.missing_gate_count ? statusTone.security_blocker : statusTone.wired} />
            <Pill label="/aureon_capital_revenue_live_gate_readiness_audit.json" tone="border-cyan-500/30 bg-cyan-500/10 text-cyan-200" />
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
              <div className="mt-1 font-mono text-sm font-semibold text-sky-100">
                {typeof value === "number" ? formatCompact(value) : String(value ?? "0")}
              </div>
            </div>
          ))}
        </div>

        <div className="grid gap-3 xl:grid-cols-[1.15fr_0.85fr]">
          <div className="space-y-2">
            <div className="flex items-center justify-between gap-2">
              <div className="text-xs uppercase text-muted-foreground">Current candidate readiness</div>
              <Pill label="existing executor path only" tone="border-sky-500/30 bg-sky-500/10 text-sky-100" />
            </div>
            <div className="grid gap-2 md:grid-cols-2">
              {rows.length ? rows.slice(0, 8).map((item) => {
                const missing = Array.isArray(item.missing_live_gate_ids) ? item.missing_live_gate_ids.map((gate) => String(gate)).filter(Boolean) : [];
                return (
                  <div key={String(item.candidate_id || item.route_key || item.symbol)} className="rounded-md border border-border/40 bg-muted/10 px-3 py-2 text-xs">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-medium">{String(item.symbol || item.epic || "capital")}</span>
                      <span className="font-mono text-sky-100">{formatCompact(item.expected_net_revenue)}</span>
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
    <Card className="border-teal-500/30 bg-teal-500/5">
      <CardHeader className="pb-3">
        <CardTitle className="flex flex-wrap items-center justify-between gap-2 text-base">
          <span className="flex items-center gap-2">
            <Gauge className="h-4 w-4 text-teal-300" />
            Capital Live Dry Stress
          </span>
          <div className="flex flex-wrap gap-1">
            <Pill label={certified ? "live dry certified" : String(audit?.status || "live dry pending").replace(/_/g, " ")} tone={certified ? statusTone.wired : statusTone.orphaned} />
            <Pill label={`${formatCompact(summary.active_watchlist_count)}/40 active`} tone="border-teal-500/30 bg-teal-500/10 text-teal-100" />
            <Pill label={`${formatCompact(summary.bench_watchlist_count)}/100 bench`} tone="border-border bg-muted/20 text-muted-foreground" />
            <Pill label="/aureon_capital_ecosystem_live_dry_stress_audit.json" tone="border-cyan-500/30 bg-cyan-500/10 text-cyan-200" />
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
              <div className="mt-1 font-mono text-sm font-semibold text-teal-100">
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

        <div className="rounded-md border border-amber-500/30 bg-amber-500/5 p-3">
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
                <div className="mt-1 font-mono text-sm font-semibold text-amber-100">{formatCompact(value as number)}</div>
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

        <div className="rounded-md border border-purple-500/30 bg-purple-500/5 p-3">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <div className="text-xs uppercase text-muted-foreground">Recovered exit readiness</div>
            <div className="flex flex-wrap gap-1">
              <Pill
                label={recoveredExitStatus.replace(/_/g, " ")}
                tone={recoveredExitStatus === "recovered_outcome_recorded" ? statusTone.wired : statusTone.orphaned}
              />
              <Pill label={`${formatCompact(summary.recovered_close_acknowledged_count)} close ack`} tone="border-purple-500/30 bg-purple-500/10 text-purple-100" />
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
                <div className="mt-1 font-mono text-sm font-semibold text-purple-100">{formatCompact(value as number)}</div>
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

  const inventory = state?.inventory || {};
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
        now,
      }),
    [state, runtime, tradingChecklist, exchangeChecklist, exchangeDataMatrix, globalCoverageMap, hncSecurityComparison, liveGoalTradeAudit, orderLifecycleStressAudit, capitalRevenueLogicStressAudit, capitalRevenueLiveGateReadinessAudit, now],
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
              <Pill label={`view ${selectedDashboardTab.title}`} tone="border-cyan-500/30 bg-cyan-500/10 text-cyan-200" />
              <Pill label={`checked ${formatFreshnessAge(timestampAgeSeconds(state?.loadedAt, now))} ago`} tone="border-border bg-muted/20 text-muted-foreground" />
            </div>
          </div>

          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
            <MetricTile label="SaaS surfaces" value={formatCompact(summary.surface_count)} icon={Database} />
            <MetricTile label="Frontend surfaces" value={formatCompact(summary.frontend_surface_count)} icon={Activity} />
            <MetricTile label="Fresh domains" value={`${formatCompact(organismSummary.fresh_domain_count)}/${formatCompact(organismSummary.domain_count)}`} icon={Server} />
            <MetricTile label="Evolution queue" value={formatCompact(evolutionSummary.queue_count)} icon={ShieldCheck} tone={asNumber(evolutionSummary.blocked_count) ? "text-yellow-300" : "text-green-300"} />
            <MetricTile label="Capability modes" value={formatCompact(switchboardSummary.capability_count)} icon={Brain} tone={asNumber(switchboardSummary.blocker_count) ? "text-yellow-300" : "text-green-300"} />
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-[1500px] px-4 py-5 lg:px-6">
        {state?.errors?.length ? (
          <Card className="mb-4 border-yellow-500/30 bg-yellow-500/10">
            <CardContent className="flex flex-col gap-2 p-4 text-sm text-yellow-100 md:flex-row md:items-center">
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
            <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
              <RuntimeMirrorPanel runtime={runtime} statusLines={statusLines} />
              <SafetyBoundariesPanel manualActions={manualActions} percent={percent} summary={summary} />
            </div>
            <div className="grid gap-4 lg:grid-cols-[0.85fr_1.15fr]">
              <DomainSpreadPanel topDomains={topDomains} totalSurfaceCount={summary.surface_count} />
              <CurrentScreenFocusPanel screen={activeScreen} />
            </div>
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
              <FilterButtons options={workOrderFilterOptions} value={workOrderFilter} onChange={setWorkOrderFilter} />
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
      <Card className="border-cyan-500/20 bg-cyan-500/5">
        <CardHeader className="pb-3">
          <CardTitle className="flex flex-col gap-3 text-base md:flex-row md:items-center md:justify-between">
            <span className="flex items-center gap-2">
              <Icon className="h-4 w-4 text-cyan-300" />
              Operator Brief
            </span>
            <div className="flex flex-wrap gap-2">
              <Pill label={`view ${tab.title}`} tone="border-cyan-500/30 bg-cyan-500/10 text-cyan-200" />
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
            <Pill label="read-only gates preserved" tone="border-green-500/30 bg-green-500/10 text-green-200" />
            <Pill label="no hidden mutation controls" tone="border-yellow-500/30 bg-yellow-500/10 text-yellow-100" />
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
              <Pill label={`${attentionCount} attention`} tone="border-yellow-500/30 bg-yellow-500/10 text-yellow-100" />
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
          {runtime.endpoint ? <Pill label={runtime.endpoint.replace("http://127.0.0.1:", "")} tone="border-cyan-500/30 bg-cyan-500/10 text-cyan-300" /> : null}
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
  summary: Record<string, unknown>;
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
                  {missing ? <span className="rounded bg-yellow-500/20 px-1.5 text-[10px] text-yellow-200">{missing}</span> : null}
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
                      <a className="mt-1 block truncate font-mono text-[11px] text-cyan-200 hover:underline" href={item.path} target="_blank" rel="noreferrer">
                        {item.path}
                      </a>
                    ) : (
                      <div className="mt-1 truncate font-mono text-[11px] text-muted-foreground">{item.path}</div>
                    )}
                  </div>
                  <div className="flex flex-wrap gap-1">
                    <Pill label={item.type} tone="border-blue-500/30 bg-blue-500/10 text-blue-200" />
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
  if (status === "attention") return "border-yellow-500/30 bg-yellow-500/10 text-yellow-200";
  if (status === "stale") return "border-orange-500/30 bg-orange-500/10 text-orange-200";
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
            <Pill label={`mode ${organism.mode || "safe_observation"}`} tone="border-blue-500/30 bg-blue-500/10 text-blue-200" />
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
              <div className="mt-1 text-lg font-semibold text-green-300">{formatCompact(summary.fresh_domain_count)}</div>
            </div>
            <div className="rounded-md border border-border/40 bg-muted/10 p-3">
              <div className="text-[11px] uppercase text-muted-foreground">stale/missing</div>
              <div className="mt-1 text-lg font-semibold text-yellow-200">
                {formatCompact(asNumber(summary.stale_domain_count) + asNumber(summary.missing_domain_count))}
              </div>
            </div>
            <div className="rounded-md border border-border/40 bg-muted/10 p-3">
              <div className="text-[11px] uppercase text-muted-foreground">blind spots</div>
              <div className="mt-1 text-lg font-semibold text-red-200">{formatCompact(summary.blind_spot_count)}</div>
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
                    <div className="mt-2 text-xs text-yellow-100">{domain.blind_spots.slice(0, 3).join(", ")}</div>
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
                      <Pill label={spot.severity} tone={spot.severity === "high" ? statusTone.security_blocker : "border-yellow-500/30 bg-yellow-500/10 text-yellow-200"} />
                    </div>
                    <div className="mt-2 text-sm">{spot.issue}</div>
                    {spot.next_action ? <div className="mt-2 text-xs text-muted-foreground">{spot.next_action}</div> : null}
                  </div>
                ))
              ) : (
                <div className="rounded-md border border-green-500/30 bg-green-500/10 p-4 text-sm text-green-100">
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
          <Pill label={evolution.status || "queue pending"} tone={asNumber(summary.blocked_count) ? "border-yellow-500/30 bg-yellow-500/10 text-yellow-200" : statusTone.wired} />
          <Pill label={`${formatCompact(summary.ready_adapter_count)} ready adapters`} tone="border-green-500/30 bg-green-500/10 text-green-200" />
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
                      <Pill label={`P${order.priority}`} tone="border-blue-500/30 bg-blue-500/10 text-blue-200" />
                      <Pill label={order.status} tone={order.status.includes("blocked") ? statusTone.security_blocker : freshnessTone("attention")} />
                      <Pill label={order.target_title} tone="border-border bg-muted/20 text-muted-foreground" />
                    </div>
                  </div>
                  <div className="mt-2 text-xs text-muted-foreground">{order.capability_summary}</div>
                  {order.frontend_action ? <div className="mt-2 text-xs text-foreground">{order.frontend_action}</div> : null}
                  {order.safety_boundary ? <div className="mt-2 text-[11px] text-yellow-100">{order.safety_boundary}</div> : null}
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
            <Pill label={switchboard.status || "switchboard pending"} tone={asNumber(summary.blocker_count) ? "border-yellow-500/30 bg-yellow-500/10 text-yellow-200" : statusTone.wired} />
            <Pill label={`${formatCompact(summary.autonomous_capability_count)} autonomous modes`} tone="border-green-500/30 bg-green-500/10 text-green-200" />
            <Pill label={`${formatCompact(summary.presentation_intent_count)} presentation intents`} tone="border-blue-500/30 bg-blue-500/10 text-blue-200" />
            <Pill label={`updated ${switchboard.generated_at ? new Date(switchboard.generated_at).toLocaleTimeString() : "pending"}`} tone="border-border bg-muted/20 text-muted-foreground" />
          </div>

          <div className="grid gap-2 md:grid-cols-5">
            <div className="rounded-md border border-border/40 bg-muted/10 p-3">
              <div className="text-[11px] uppercase text-muted-foreground">capabilities</div>
              <div className="mt-1 text-lg font-semibold">{formatCompact(summary.capability_count)}</div>
            </div>
            <div className="rounded-md border border-border/40 bg-muted/10 p-3">
              <div className="text-[11px] uppercase text-muted-foreground">blocked</div>
              <div className="mt-1 text-lg font-semibold text-yellow-200">{formatCompact(summary.blocker_count)}</div>
            </div>
            <div className="rounded-md border border-border/40 bg-muted/10 p-3">
              <div className="text-[11px] uppercase text-muted-foreground">app/UI queue</div>
              <div className="mt-1 text-lg font-semibold">{formatCompact(summary.frontend_work_order_count)}</div>
            </div>
            <div className="rounded-md border border-border/40 bg-muted/10 p-3">
              <div className="text-[11px] uppercase text-muted-foreground">ready adapters</div>
              <div className="mt-1 text-lg font-semibold text-green-300">{formatCompact(summary.ready_adapter_count)}</div>
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
                          <Pill key={system} label={system} tone="border-blue-500/30 bg-blue-500/10 text-blue-100" />
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
                <Pill key={gate} label={gate.replace(/_/g, " ")} tone="border-green-500/30 bg-green-500/10 text-green-100" />
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
                        <Pill label={`P${intent.priority}`} tone="border-blue-500/30 bg-blue-500/10 text-blue-200" />
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
    <Card className="border-yellow-500/30 bg-yellow-500/5">
      <CardHeader className="pb-3">
        <CardTitle className="flex flex-wrap items-center justify-between gap-2 text-base">
          <span className="flex items-center gap-2">
            <LineChart className="h-4 w-4 text-yellow-300" />
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
            <div key={gate.label} className={`rounded-md border p-3 ${gate.pass ? "border-green-500/30 bg-green-500/10" : "border-yellow-500/30 bg-yellow-500/10"}`}>
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
            <div className={`mt-1 font-mono text-sm font-semibold ${runtimeGoldDataFresh ? "text-green-300" : "text-yellow-200"}`}>
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
            <div className={`mt-1 font-mono text-sm font-semibold ${goal.gold_order_intent_ready ? "text-green-300" : "text-red-300"}`}>
              {formatCompact(intent.gold_intent_count)}/{formatCompact(intent.intent_count)}
            </div>
          </div>
          <div className="rounded-md border border-border/40 bg-black/20 p-3">
            <div className="text-[11px] uppercase text-muted-foreground">executor sent</div>
            <div className="mt-1 font-mono text-sm font-semibold">{formatCompact(executor.submitted_count)}</div>
          </div>
          <div className="rounded-md border border-border/40 bg-black/20 p-3">
            <div className="text-[11px] uppercase text-muted-foreground">handover</div>
            <div className={`mt-1 font-mono text-sm font-semibold ${goal.handover_ready ? "text-green-300" : "text-yellow-200"}`}>
              {goal.handover_ready ? "ready" : "blocked"}
            </div>
          </div>
        </div>

        {intent.non_gold_intents_rejected_for_gold_proof ? (
          <div className="rounded-md border border-yellow-500/30 bg-yellow-500/10 px-3 py-2 text-xs text-yellow-100">
            Non-GOLD runtime intents are visible but rejected for GOLD proof. Only fresh Capital GOLD/XAU intents count here.
          </div>
        ) : null}

        {runtimeCandidateReady ? (
          <div className="rounded-md border border-cyan-500/30 bg-cyan-500/10 px-3 py-2 text-xs text-cyan-100">
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
                <div key={blocker} className="rounded-md border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-100">
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
    <Card className="border-cyan-500/30 bg-cyan-500/5">
      <CardHeader className="pb-3">
        <CardTitle className="flex flex-wrap items-center justify-between gap-2 text-base">
          <span className="flex items-center gap-2">
            <Activity className="h-4 w-4 text-cyan-300" />
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
            <div className={`mt-1 font-mono text-sm font-semibold ${missingLinks.length ? "text-yellow-200" : "text-green-300"}`}>
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
                    <span className="font-mono text-cyan-100">{String(event.status || event.event_type || "event").replace(/_/g, " ")}</span>
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
    <Card className="border-emerald-500/30 bg-emerald-500/5">
      <CardHeader className="pb-3">
        <CardTitle className="flex flex-wrap items-center justify-between gap-2 text-base">
          <span className="flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 text-emerald-300" />
            Lifecycle Stress Certification
          </span>
          <div className="flex flex-wrap gap-1">
            <Pill label={mockCertified ? "Mock Certified" : "Mock Attention"} tone={mockCertified ? statusTone.wired : statusTone.orphaned} />
            <Pill label={sandboxCertified ? "Sandbox/Paper Certified" : "Sandbox/Paper Attention"} tone={sandboxCertified ? statusTone.wired : statusTone.orphaned} />
            <Pill label={`${formatCompact(summary.passed_count ?? proof.passed_count)}/${formatCompact(summary.case_count ?? proof.case_count)} cases`} tone="border-border bg-muted/20 text-muted-foreground" />
            <Pill label={`${formatCompact(summary.covered_requirement_count ?? proof.covered_requirement_count)}/${formatCompact(summary.requirement_count ?? proof.requirement_count)} reqs`} tone="border-border bg-muted/20 text-muted-foreground" />
            <Pill label="/aureon_order_lifecycle_stress_audit.json" tone="border-cyan-500/30 bg-cyan-500/10 text-cyan-200" />
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
              <div className={`mt-1 font-mono text-sm font-semibold ${Boolean(ok) ? "text-green-300" : "text-yellow-200"}`}>
                {Boolean(ok) ? "proven" : "held"}
              </div>
            </div>
          ))}
        </div>

        <div className="grid gap-2 md:grid-cols-3">
          <div className="rounded-md border border-cyan-500/30 bg-cyan-500/10 p-3">
            <div className="text-[11px] uppercase text-cyan-100/80">Mock broker tier</div>
            <div className="mt-1 font-mono text-sm text-cyan-50">{String(summary.mock_broker_status || proof.mock_broker_status || source?.status || "pending").replace(/_/g, " ")}</div>
          </div>
          <div className="rounded-md border border-emerald-500/30 bg-emerald-500/10 p-3">
            <div className="text-[11px] uppercase text-emerald-100/80">Sandbox / paper tier</div>
            <div className="mt-1 font-mono text-sm text-emerald-50">
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
                    <Pill label={String(item.state || (Boolean(item.passed) ? "passed" : "held")).replace(/_/g, " ")} tone={Boolean(item.passed) ? statusTone.wired : statusTone.orphaned} />
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
                <Pill key={field} label={field.replace(/_/g, " ")} tone="border-emerald-500/30 bg-emerald-500/10 text-emerald-100" />
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
                    <Pill label={String(item.state || (Boolean(item.passed) ? "passed" : "held")).replace(/_/g, " ")} tone={Boolean(item.passed) ? statusTone.wired : statusTone.orphaned} />
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
              label={Boolean(summary.broker_requirement_matrix_complete) ? "matrix complete" : "matrix attention"}
              tone={Boolean(summary.broker_requirement_matrix_complete) ? statusTone.wired : statusTone.orphaned}
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
          <Pill label="/aureon_global_financial_coverage_map.json" tone="border-cyan-500/30 bg-cyan-500/10 text-cyan-200" />
        </div>

        <div className="rounded-md border border-cyan-500/30 bg-cyan-500/10 p-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <div className="text-[11px] uppercase text-cyan-100/80">configured source coverage</div>
              <div className="mt-1 text-lg font-semibold text-cyan-50">{coveragePercent}% mapped</div>
              <div className="mt-1 text-xs text-cyan-50/70">
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
            <div className="mt-1 text-lg font-semibold text-yellow-200">{formatCompact(summary.credential_missing_source_count)}</div>
          </div>
        </div>

        {missing.length ? (
          <div className="space-y-2">
            <div className="text-xs uppercase text-muted-foreground">Map gaps</div>
            {missing.map((item, index) => (
              <div key={`${String(item.domain)}-${index}`} className="rounded-md border border-yellow-500/30 bg-yellow-500/10 px-3 py-2 text-xs">
                <span className="font-semibold text-yellow-100">{String(item.domain || "unknown")}</span>
                <span className="ml-2 text-yellow-100/80">{String(item.missing || "")}</span>
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
                {source.decision_blocker ? <div className="mt-1 text-yellow-100">Decision hold: {source.decision_blocker.replace(/_/g, " ")}</div> : null}
                <div className="mt-2 flex flex-wrap gap-1">
                  {(source.asset_classes || []).slice(0, 5).map((assetClass) => (
                    <Pill key={`${source.source_id}-${assetClass}`} label={assetClass.replace(/_/g, " ")} tone="border-blue-500/30 bg-blue-500/10 text-blue-200" />
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
          <Pill label="/aureon_exchange_monitoring_checklist.json" tone="border-cyan-500/30 bg-cyan-500/10 text-cyan-200" />
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
              <div key={`${String(item.exchange)}-${index}`} className="rounded-md border border-yellow-500/30 bg-yellow-500/10 px-3 py-2 text-xs">
                <span className="font-semibold text-yellow-100">{String(item.exchange || "unknown")}</span>
                <span className="ml-2 text-yellow-100/80">{String(item.missing || "")}</span>
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
                          <Pill key={market} label={market.replace(/_/g, " ")} tone="border-blue-500/30 bg-blue-500/10 text-blue-200" />
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
                      <Pill key={item} label={item.replace(/_/g, " ")} tone="border-green-500/30 bg-green-500/10 text-green-100" />
                    ))}
                  </div>
                  {(row.missing || []).length ? (
                    <div className="mt-2 text-xs text-yellow-100">{(row.missing || []).slice(0, 5).join(", ")}</div>
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
          <Pill label="/aureon_exchange_data_capability_matrix.json" tone="border-cyan-500/30 bg-cyan-500/10 text-cyan-200" />
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
                        <Pill label={policy.data_boost_eligible ? "data boost" : "execution reserve"} tone={policy.data_boost_eligible ? "border-cyan-500/30 bg-cyan-500/10 text-cyan-200" : "border-yellow-500/30 bg-yellow-500/10 text-yellow-200"} />
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
                        <Pill key={`${row.exchange}-${mode}`} label={mode.replace(/_/g, " ")} tone="border-blue-500/30 bg-blue-500/10 text-blue-200" />
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
                    {(row.gaps || []).length ? <div className="mt-2 text-xs text-yellow-100">{(row.gaps || []).slice(0, 5).join(", ")}</div> : null}
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
          <Pill label="/aureon_trading_intelligence_checklist.json" tone="border-cyan-500/30 bg-cyan-500/10 text-cyan-200" />
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
            <div className="mt-1 text-lg font-semibold text-yellow-200">{formatCompact(summary.stale_or_blocked_count)}</div>
          </div>
          <div className="rounded-md border border-border/40 bg-muted/10 p-3">
            <div className="text-[11px] uppercase text-muted-foreground">self trust</div>
            <div className="mt-1 text-lg font-semibold">{Math.round(asNumber(summary.decision_self_trust_score) * 100)}%</div>
          </div>
        </div>

        {trust ? (
          <div className="rounded-md border border-cyan-500/30 bg-cyan-500/10 p-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <div className="text-[11px] uppercase text-cyan-100/80">decision posture</div>
                <div className="mt-1 font-mono text-sm font-semibold text-cyan-50">
                  {String(trust.posture || summary.decision_posture || "checking").replace(/_/g, " ")}
                </div>
              </div>
              <div className="flex flex-wrap gap-1">
                <Pill label={trust.trust_to_decide ? "trusts decision" : "still measuring"} tone={trust.trust_to_decide ? statusTone.wired : statusTone.orphaned} />
                <Pill label={trust.trust_to_act ? "live intent ready" : trust.trust_to_shadow ? "shadow ready" : "learning"} tone={trust.trust_to_act ? statusTone.wired : statusTone.partial} />
              </div>
            </div>
            <div className="mt-2 text-xs text-cyan-50/80">{trust.self_instruction}</div>
            <div className="mt-1 text-[11px] text-cyan-50/60">{trust.not_fear_reason}</div>
          </div>
        ) : null}

        {metaContext?.present ? (
          <div className="rounded-md border border-emerald-500/30 bg-emerald-500/10 p-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <div className="text-[11px] uppercase text-emerald-100/80">metacognitive data ocean</div>
                <div className="mt-1 text-sm text-emerald-50">
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
              <div className="rounded-md border border-emerald-400/20 bg-background/30 p-2">
                <div className="text-[10px] uppercase text-emerald-100/70">mapped</div>
                <div className="font-mono text-sm text-emerald-50">{Math.round(asNumber(metaContext.coverage_percent))}%</div>
              </div>
              <div className="rounded-md border border-emerald-400/20 bg-background/30 p-2">
                <div className="text-[10px] uppercase text-emerald-100/70">live sources</div>
                <div className="font-mono text-sm text-emerald-50">{formatCompact(metaContext.active_live_source_count)}</div>
              </div>
              <div className="rounded-md border border-emerald-400/20 bg-background/30 p-2">
                <div className="text-[10px] uppercase text-emerald-100/70">tickers</div>
                <div className="font-mono text-sm text-emerald-50">{formatCompact(metaContext.live_ticker_count)}</div>
              </div>
              <div className="rounded-md border border-emerald-400/20 bg-background/30 p-2">
                <div className="text-[10px] uppercase text-emerald-100/70">history rows</div>
                <div className="font-mono text-sm text-emerald-50">{formatCompact(metaContext.history_rows)}</div>
              </div>
              <div className="rounded-md border border-emerald-400/20 bg-background/30 p-2">
                <div className="text-[10px] uppercase text-emerald-100/70">cleanliness</div>
                <div className="font-mono text-sm text-emerald-50">{Math.round(asNumber(metaContext.cognitive_cleanliness_score) * 100)}%</div>
              </div>
            </div>
            {metaContext.decision_blocker ? <div className="mt-2 text-[11px] text-yellow-100">{metaContext.decision_blocker}</div> : null}
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
              <div key={`${String(blocker.system)}-${index}`} className="rounded-md border border-yellow-500/30 bg-yellow-500/10 px-3 py-2 text-xs">
                <span className="font-semibold text-yellow-100">{String(blocker.system || "unknown")}</span>
                <span className="ml-2 text-yellow-100/80">{String(blocker.blocker || "")}</span>
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
                    <Pill label={row.downstream_stage.replace(/_/g, " ")} tone="border-blue-500/30 bg-blue-500/10 text-blue-200" />
                    <Pill label={row.fed_to_decision_logic ? "decision fed" : "not fed"} tone={row.fed_to_decision_logic ? statusTone.wired : statusTone.partial} />
                    <Pill label={row.usable_for_decision ? "fresh usable" : "held"} tone={row.usable_for_decision ? statusTone.wired : statusTone.orphaned} />
                  </div>
                </div>
                {row.blocker ? <div className="mt-2 text-xs text-yellow-100">{row.blocker}</div> : null}
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
                  <Pill key={note} label={note} tone="border-yellow-500/30 bg-yellow-500/10 text-yellow-200" />
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
                <div key={item} className="rounded-md border border-yellow-500/30 bg-yellow-500/10 px-3 py-2 text-sm text-yellow-100">
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

export default App;
