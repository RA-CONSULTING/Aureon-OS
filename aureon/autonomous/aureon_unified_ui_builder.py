"""Aureon-owned operational UI builder.

This module is the concrete apply step behind the frontend unification and
evolution manifests. The inventory/planning modules decide what exists and
where it belongs; this builder turns those manifests into a live React console
component plus public evidence that the frontend can read.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Sequence

from aureon.autonomous.aureon_saas_system_inventory import repo_root_from
from aureon.code_architect.expression import build_code_expression_context

try:
    from aureon.queen.queen_code_architect import QueenCodeArchitect
except Exception:  # pragma: no cover - optional runtime dependency
    QueenCodeArchitect = None  # type: ignore[assignment]


SCHEMA_VERSION = "aureon-operational-ui-builder-v1"
DEFAULT_COMPONENT_PATH = Path("frontend/src/components/generated/AureonGeneratedOperationalConsole.tsx")
DEFAULT_PUBLIC_SPEC_PATH = Path("frontend/public/aureon_operational_ui_spec.json")
DEFAULT_AUDIT_PATH = Path("docs/audits/aureon_operational_ui_builder.json")
DEFAULT_STATE_PATH = Path("state/aureon_ui_builder_last_run.json")
DEFAULT_SELF_AUTHORED_STATE_PATH = Path("state/aureon_self_authored_ui_last_run.json")
DEFAULT_SELF_REPAIR_STATE_PATH = Path("state/aureon_self_ui_repair_last_run.json")

PUBLIC_MANIFESTS = {
    "wake_up_manifest": "frontend/public/aureon_wake_up_manifest.json",
    "organism_runtime": "frontend/public/aureon_organism_runtime_status.json",
    "saas_inventory": "frontend/public/aureon_saas_system_inventory.json",
    "frontend_unification": "frontend/public/aureon_frontend_unification_plan.json",
    "frontend_evolution": "frontend/public/aureon_frontend_evolution_queue.json",
    "capability_switchboard": "frontend/public/aureon_autonomous_capability_switchboard.json",
    "cognitive_trade_evidence": "frontend/public/aureon_cognitive_trade_evidence.json",
    "harmonic_affect_state": "frontend/public/aureon_harmonic_affect_state.json",
    "live_cognition_benchmark": "frontend/public/aureon_live_cognition_benchmark.json",
    "hnc_cognitive_proof": "frontend/public/aureon_hnc_cognitive_proof.json",
    "trading_intelligence_checklist": "frontend/public/aureon_trading_intelligence_checklist.json",
    "frontend_work_order_execution": "frontend/public/aureon_frontend_work_order_execution.json",
    "coding_agent_skill_base": "frontend/public/aureon_coding_agent_skill_base.json",
}

CAPABILITY_LABELS = (
    "Live runtime supervision",
    "Multi-exchange trading coverage",
    "Cognitive order-intent path",
    "HNC and Auris harmonic evidence",
    "Self-questioning and mind hub",
    "Research and vault memory",
    "Accounting and HMRC support packs",
    "SaaS security and authorized local audit",
    "Self-improvement and code generation",
)

REQUIRED_UI_MARKERS = (
    "Aureon Designed Live Operations Interface",
    "Trading Mesh",
    "Four-Exchange Coverage",
    "HNC/Auris",
    "Mind Hub",
    "Self-Build",
    "Evidence",
    "self_authored_operational_ui_ready",
)

BLOCKED_OUTPUT_MARKERS = (
    "API_SECRET",
    "BEGIN PRIVATE",
    "PRIVATE KEY",
    "Government Gateway",
)


@dataclass
class OperationalUiBuild:
    schema_version: str
    generated_at: str
    repo_root: str
    status: str
    goal: str
    generated_files: list[str]
    public_manifests: dict[str, dict[str, Any]]
    live_interfaces: dict[str, str]
    templates_used: list[str]
    capability_labels: list[str]
    capability_coverage: dict[str, Any]
    expression_context: dict[str, Any] = field(default_factory=dict)
    authoring_path: list[str] = field(default_factory=list)
    authoring_goal: str = ""
    writer: dict[str, Any] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        return payload if isinstance(payload, dict) else {}
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}", "path": str(path)}


def _count(value: Any) -> int:
    try:
        return int(value or 0)
    except Exception:
        return 0


def discover_ui_templates(root: Path, limit: int = 64) -> list[str]:
    """Find dashboard/panel/console components Aureon can use as UI precedent."""

    components_root = root / "frontend" / "src" / "components"
    if not components_root.exists():
        return []
    candidates: list[str] = []
    for path in components_root.rglob("*.tsx"):
        rel = path.relative_to(root).as_posix()
        lowered = rel.lower()
        if any(token in lowered for token in ("dashboard", "console", "panel", "status", "warroom", "unified")):
            candidates.append(rel)
    candidates.sort()
    return candidates[:limit]


def build_operational_ui_spec(root: Optional[Path] = None) -> OperationalUiBuild:
    root = repo_root_from(root)
    manifests = {
        name: _manifest_record(root / rel_path, root)
        for name, rel_path in PUBLIC_MANIFESTS.items()
    }

    organism = manifests["organism_runtime"].get("payload") or {}
    switchboard = manifests["capability_switchboard"].get("payload") or {}
    unification = manifests["frontend_unification"].get("payload") or {}
    evolution = manifests["frontend_evolution"].get("payload") or {}
    inventory = manifests["saas_inventory"].get("payload") or {}
    wake_up = manifests["wake_up_manifest"].get("payload") or {}

    switch_summary = switchboard.get("summary") or {}
    plan_summary = unification.get("summary") or {}
    evolution_summary = evolution.get("summary") or {}
    inventory_summary = inventory.get("summary") or {}
    organism_summary = organism.get("summary") or {}

    templates = discover_ui_templates(root)
    coverage = {
        "canonical_screen_count": _count(plan_summary.get("screen_count")),
        "capability_count": _count(switch_summary.get("capability_count")),
        "autonomous_capability_count": _count(switch_summary.get("autonomous_capability_count")),
        "frontend_work_order_count": _count(evolution_summary.get("queue_count")),
        "ready_adapter_count": _count(evolution_summary.get("ready_adapter_count")),
        "blocked_work_order_count": _count(evolution_summary.get("blocked_count")),
        "surface_count": _count(inventory_summary.get("surface_count")),
        "frontend_surface_count": _count(inventory_summary.get("frontend_surface_count")),
        "runtime_feed_status": organism_summary.get("runtime_feed_status") or "unknown",
        "blind_spot_count": _count(organism_summary.get("blind_spot_count")),
        "template_count": len(templates),
    }

    live_interfaces = {
        "console": "http://127.0.0.1:8081/",
        "runtime_feed": str(wake_up.get("runtime_feed_url") or "http://127.0.0.1:8791/api/terminal-state"),
        "flight_test": str(wake_up.get("runtime_flight_test_url") or "http://127.0.0.1:8791/api/flight-test"),
        "reboot_advice": str(wake_up.get("runtime_reboot_advice_url") or "http://127.0.0.1:8791/api/reboot-advice"),
        "mind_hub": str(wake_up.get("mind_hub_url") or "http://127.0.0.1:13002/api/thoughts"),
    }

    expression_context = build_code_expression_context(
        "Design and build Aureon's fully operational live user interface from existing repo dashboards and manifests.",
        evidence={
            "runtime_state": {
                "hot_topic": "aureon.operational_ui_builder",
                "action": "BUILD_FRONTEND",
                "mode": "autonomous_ui_generation",
                "live_interfaces": live_interfaces,
            },
            "capability_coverage": coverage,
            "templates_used": templates[:20],
            "public_manifest_keys": list(manifests),
        },
        root=root,
        evidence_dir=root / "state",
        publish=True,
    )

    return OperationalUiBuild(
        schema_version=SCHEMA_VERSION,
        generated_at=utc_now(),
        repo_root=str(root),
        status="operational_ui_spec_ready",
        goal="One live operator surface for trading, cognition, HNC/Auris, research, accounting, security, and self-building.",
        generated_files=[
            DEFAULT_COMPONENT_PATH.as_posix(),
            DEFAULT_PUBLIC_SPEC_PATH.as_posix(),
            DEFAULT_AUDIT_PATH.as_posix(),
            DEFAULT_STATE_PATH.as_posix(),
        ],
        public_manifests={name: _strip_payload(record) for name, record in manifests.items()},
        live_interfaces=live_interfaces,
        templates_used=templates,
        capability_labels=list(CAPABILITY_LABELS),
        capability_coverage=coverage,
        expression_context=expression_context,
        authoring_path=[
            "aureon.autonomous.aureon_unified_ui_builder.build_operational_ui_spec",
        ],
        writer={"name": "direct_python_writer", "verified": False},
        notes=[
            "The generated console reads public manifests and live local endpoints at runtime.",
            "ok:false runtime responses are treated as connected guarded state, not offline.",
            "No credential values, payment actions, official filings, or direct exchange mutation forms are generated here.",
        ],
    )


def _manifest_record(path: Path, root: Path) -> dict[str, Any]:
    payload = load_json(path)
    generated_at = payload.get("generated_at") if isinstance(payload, dict) else ""
    status = payload.get("status") if isinstance(payload, dict) else ""
    return {
        "path": path.relative_to(root).as_posix() if path.exists() else path.as_posix(),
        "exists": path.exists(),
        "generated_at": generated_at,
        "status": status,
        "payload": payload,
    }


def _strip_payload(record: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in record.items() if key != "payload"}


def render_react_component() -> str:
    """Return the generated React component source."""

    return r'''/* Generated by python -m aureon.autonomous.aureon_unified_ui_builder.
 * This component is data-driven. Re-run the builder after manifest or template changes.
 */

import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  BadgeCheck,
  Brain,
  Calculator,
  Code2,
  Database,
  FileText,
  Gauge,
  LineChart,
  Network,
  Radio,
  RefreshCw,
  Search,
  Server,
  ShieldCheck,
  Sparkles,
  Terminal,
  Zap,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

type JsonMap = Record<string, any>;

const PUBLIC_ENDPOINTS: Record<string, string> = {
  uiSpec: "/aureon_operational_ui_spec.json",
  wake: "/aureon_wake_up_manifest.json",
  organism: "/aureon_organism_runtime_status.json",
  switchboard: "/aureon_autonomous_capability_switchboard.json",
  unification: "/aureon_frontend_unification_plan.json",
  evolution: "/aureon_frontend_evolution_queue.json",
  inventory: "/aureon_saas_system_inventory.json",
  tradeEvidence: "/aureon_cognitive_trade_evidence.json",
  harmonic: "/aureon_harmonic_affect_state.json",
  benchmark: "/aureon_live_cognition_benchmark.json",
  hncProof: "/aureon_hnc_cognitive_proof.json",
};

const RUNTIME_FALLBACKS = [
  "http://127.0.0.1:8791/api/terminal-state",
  "http://127.0.0.1:8790/api/terminal-state",
];

const EXCHANGES = ["kraken", "binance", "alpaca", "capital"];

interface OperationalSnapshot {
  loadedAt: string;
  loading: boolean;
  data: Record<string, JsonMap>;
  runtime: JsonMap | null;
  flight: JsonMap | null;
  reboot: JsonMap | null;
  runtimeEndpoint: string;
  errors: string[];
}

async function fetchJson<T = JsonMap>(url: string, signal?: AbortSignal): Promise<T | null> {
  try {
    const response = await fetch(url, { cache: "no-store", signal });
    if (!response.ok) return null;
    return (await response.json()) as T;
  } catch {
    return null;
  }
}

function uniqueStrings(values: Array<string | undefined>): string[] {
  return Array.from(new Set(values.map((value) => String(value || "").trim()).filter(Boolean)));
}

function asNumber(value: unknown, fallback = 0): number {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : fallback;
}

function compact(value: unknown): string {
  return asNumber(value).toLocaleString();
}

function percent(value: unknown): string {
  const numeric = asNumber(value);
  if (numeric <= 1) return `${Math.round(numeric * 100)}%`;
  return `${Math.round(numeric)}%`;
}

function timeLabel(value: unknown): string {
  if (!value) return "pending";
  const date = new Date(String(value));
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleTimeString();
}

function shortText(value: unknown, fallback = "unknown"): string {
  const text = String(value ?? "").trim();
  return text || fallback;
}

function derivedEndpoint(base: string, suffix: string): string {
  return base.replace(/\/api\/terminal-state$/, suffix);
}

function pillTone(kind: "good" | "warn" | "bad" | "info" | "quiet" = "quiet"): string {
  if (kind === "good") return "border-success/30 bg-success/10 text-success";
  if (kind === "warn") return "border-warning/30 bg-warning/10 text-warning";
  if (kind === "bad") return "border-destructive/30 bg-destructive/10 text-destructive";
  if (kind === "info") return "border-primary/30 bg-primary/10 text-primary";
  return "border-border/60 bg-muted/20 text-muted-foreground";
}

function statusKind(value: unknown): "good" | "warn" | "bad" | "info" | "quiet" {
  const text = String(value ?? "").toLowerCase();
  if (text.includes("blocked") || text.includes("offline") || text.includes("missing") || text.includes("fail")) return "bad";
  if (text.includes("stale") || text.includes("guard") || text.includes("attention") || text.includes("pending")) return "warn";
  if (text.includes("live") || text.includes("ready") || text.includes("fresh") || text.includes("online") || text.includes("clear")) return "good";
  if (text.includes("observe") || text.includes("checking")) return "info";
  return "quiet";
}

function Pill({ label, kind = "quiet" }: { label: string; kind?: "good" | "warn" | "bad" | "info" | "quiet" }) {
  return <span className={`inline-flex min-h-6 items-center rounded-md border px-2 py-0.5 text-[11px] font-medium ${pillTone(kind)}`}>{label}</span>;
}

function Stat({ label, value, icon: Icon, kind = "quiet" }: { label: string; value: string; icon: typeof Activity; kind?: "good" | "warn" | "bad" | "info" | "quiet" }) {
  return (
    <div className="rounded-lg border border-border/50 bg-background/55 p-3">
      <div className="flex items-center justify-between gap-3">
        <div className="text-[11px] uppercase text-muted-foreground">{label}</div>
        <Icon className={`h-4 w-4 ${kind === "good" ? "text-success" : kind === "warn" ? "text-warning" : kind === "bad" ? "text-destructive" : "text-primary"}`} />
      </div>
      <div className="mt-3 truncate text-xl font-semibold">{value}</div>
    </div>
  );
}

function exchangeReady(runtime: JsonMap | null, name: string): boolean {
  if (!runtime) return false;
  return Boolean(
    runtime?.[`${name}_ready`] ||
    runtime?.exchanges?.[`${name}_ready`] ||
    runtime?.exchanges?.[name]?.ready ||
    runtime?.[name]?.ready ||
    runtime?.[name]?.connected
  );
}

function exchangeError(runtime: JsonMap | null, name: string): string {
  return String(runtime?.errors?.[name] || runtime?.exchanges?.[name]?.error || runtime?.[name]?.error || "");
}

function runtimeBlockers(runtime: JsonMap | null, flight: JsonMap | null, reboot: JsonMap | null): string[] {
  const blockers = new Set<string>();
  const watchdog = runtime?.runtime_watchdog || {};
  const checks = flight?.checks || {};
  if (runtime?.booting) blockers.add("runtime_booting");
  if (runtime?.stale || watchdog?.tick_stale) blockers.add("runtime_stale");
  if (runtime?.stale_reason) blockers.add(String(runtime.stale_reason));
  if (watchdog?.tick_stale_reason) blockers.add(String(watchdog.tick_stale_reason));
  if (asNumber(runtime?.combined?.open_positions || runtime?.open_positions) > 0 || checks?.open_positions === true) blockers.add("open_positions");
  if (checks?.downtime_window === false || checks?.downtime_window_open === false) blockers.add("downtime_window_false");
  if (flight?.reboot_advice?.can_reboot_now === false || reboot?.can_reboot_now === false) blockers.add("reboot_deferred");
  return Array.from(blockers).filter(Boolean);
}

async function loadSnapshot(): Promise<OperationalSnapshot> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 2200);
  const errors: string[] = [];
  const data: Record<string, JsonMap> = {};

  try {
    await Promise.all(Object.entries(PUBLIC_ENDPOINTS).map(async ([key, url]) => {
      const payload = await fetchJson<JsonMap>(url, controller.signal);
      if (payload) data[key] = payload;
      else errors.push(`${key} unavailable`);
    }));

    const runtimeEndpoints = uniqueStrings([data.wake?.runtime_feed_url, ...RUNTIME_FALLBACKS]);
    let runtime: JsonMap | null = null;
    let runtimeEndpoint = "";
    for (const endpoint of runtimeEndpoints) {
      const payload = await fetchJson<JsonMap>(endpoint, controller.signal);
      if (payload) {
        runtime = payload;
        runtimeEndpoint = endpoint;
        break;
      }
    }

    const flightUrl = data.wake?.runtime_flight_test_url || (runtimeEndpoint ? derivedEndpoint(runtimeEndpoint, "/api/flight-test") : "");
    const rebootUrl = data.wake?.runtime_reboot_advice_url || (runtimeEndpoint ? derivedEndpoint(runtimeEndpoint, "/api/reboot-advice") : "");
    const flight = flightUrl ? await fetchJson<JsonMap>(flightUrl, controller.signal) : null;
    const reboot = rebootUrl ? await fetchJson<JsonMap>(rebootUrl, controller.signal) : null;

    return {
      loadedAt: new Date().toISOString(),
      loading: false,
      data,
      runtime,
      flight,
      reboot,
      runtimeEndpoint,
      errors,
    };
  } finally {
    window.clearTimeout(timeout);
  }
}

export function AureonGeneratedOperationalConsole() {
  const [snapshot, setSnapshot] = useState<OperationalSnapshot>({
    loadedAt: "",
    loading: true,
    data: {},
    runtime: null,
    flight: null,
    reboot: null,
    runtimeEndpoint: "",
    errors: [],
  });
  const [active, setActive] = useState("live");

  const refresh = async () => {
    setSnapshot((current) => ({ ...current, loading: true }));
    setSnapshot(await loadSnapshot());
  };

  useEffect(() => {
    refresh();
    const timer = window.setInterval(refresh, 8000);
    return () => window.clearInterval(timer);
  }, []);

  const { data, runtime, flight, reboot } = snapshot;
  const uiSpec = data.uiSpec || {};
  const organism = data.organism || {};
  const switchboard = data.switchboard || {};
  const unification = data.unification || {};
  const evolution = data.evolution || {};
  const inventory = data.inventory || {};
  const tradeEvidence = data.tradeEvidence || {};
  const harmonic = data.harmonic || {};
  const benchmark = data.benchmark || {};
  const hncProof = data.hncProof || {};
  const blockers = runtimeBlockers(runtime, flight, reboot);

  const capabilityModes = Array.isArray(switchboard.capability_modes) ? switchboard.capability_modes : [];
  const screens = Array.isArray(unification.canonical_screens) ? unification.canonical_screens : [];
  const workOrders = Array.isArray(evolution.work_orders) ? evolution.work_orders : [];
  const templates = Array.isArray(uiSpec.templates_used) ? uiSpec.templates_used : [];
  const domains = Array.isArray(organism.domains) ? organism.domains : [];
  const blindSpots = Array.isArray(organism.blind_spots) ? organism.blind_spots : [];

  const actionMode = organism.mode || (runtime?.ok === false ? "guarded_observe_plan" : runtime ? "guarded_live_action" : "safe_observation");
  const runtimeConnected = Boolean(runtime);
  const guarded = blockers.length > 0 || runtime?.ok === false || String(actionMode).includes("guard");
  const tradingAllowed = Boolean(organism?.summary?.trading_action_allowed || runtime?.trading_action_allowed);

  const exchangeRows = useMemo(() => EXCHANGES.map((name) => ({
    name,
    ready: exchangeReady(runtime, name),
    error: exchangeError(runtime, name),
    governor: runtime?.api_governor?.exchanges?.[name] || {},
    equity: runtime?.[name]?.equity || runtime?.combined?.[`${name}_equity`] || runtime?.combined?.[`${name}_equity_gbp`] || runtime?.exchanges?.[name]?.equity,
  })), [runtime]);

  return (
    <section className="mb-5 space-y-4">
      <Card className="overflow-hidden border-primary/20 bg-card/90">
        <CardHeader className="border-b border-border/50 pb-4">
          <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-start">
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <CardTitle className="flex items-center gap-2 text-xl">
                  <Sparkles className="h-5 w-5 text-primary" />
                  Aureon Designed Live Operations Interface
                </CardTitle>
                <Badge variant={runtimeConnected ? (guarded ? "warning" : "success") : "destructive"}>
                  {runtimeConnected ? (guarded ? "connected guarded" : "connected live") : "runtime offline"}
                </Badge>
                <Badge variant={tradingAllowed ? "success" : "outline"}>{tradingAllowed ? "action path clear" : "action path waiting"}</Badge>
                <Badge variant="outline">{shortText(uiSpec.status, "builder spec pending")}</Badge>
              </div>
              <p className="mt-2 max-w-5xl text-sm text-muted-foreground">
                This surface is generated from Aureon's own frontend inventory, unification plan, evolution queue, capability switchboard, runtime feed, HNC/Auris evidence, and existing dashboard templates.
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button onClick={refresh} size="sm" variant="outline" disabled={snapshot.loading}>
                <RefreshCw className={`mr-2 h-4 w-4 ${snapshot.loading ? "animate-spin" : ""}`} />
                Refresh
              </Button>
              {snapshot.runtimeEndpoint ? (
                <Button size="sm" variant="ghost" asChild>
                  <a href={snapshot.runtimeEndpoint} target="_blank" rel="noreferrer">
                    <Terminal className="mr-2 h-4 w-4" />
                    Runtime
                  </a>
                </Button>
              ) : null}
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4 p-4">
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-6">
            <Stat label="runtime" value={runtimeConnected ? (guarded ? "guarded" : "live") : "offline"} icon={Radio} kind={runtimeConnected ? (guarded ? "warn" : "good") : "bad"} />
            <Stat label="exchanges" value={`${exchangeRows.filter((row) => row.ready).length}/4`} icon={LineChart} kind={exchangeRows.every((row) => row.ready) ? "good" : "warn"} />
            <Stat label="capabilities" value={compact(switchboard?.summary?.capability_count)} icon={Brain} kind="info" />
            <Stat label="screens" value={compact(unification?.summary?.screen_count)} icon={Server} kind="info" />
            <Stat label="work orders" value={compact(evolution?.summary?.queue_count)} icon={Code2} kind={asNumber(evolution?.summary?.blocked_count) ? "warn" : "good"} />
            <Stat label="blind spots" value={compact(organism?.summary?.blind_spot_count)} icon={AlertTriangle} kind={asNumber(organism?.summary?.blind_spot_count) ? "warn" : "good"} />
          </div>

          <div className="flex flex-wrap gap-2">
            <Pill label={`mode ${shortText(actionMode)}`} kind={statusKind(actionMode)} />
            <Pill label={`feed ${snapshot.runtimeEndpoint ? snapshot.runtimeEndpoint.replace("http://127.0.0.1:", "") : "not connected"}`} kind={runtimeConnected ? "info" : "bad"} />
            <Pill label={`updated ${timeLabel(runtime?.generated_at || runtime?.dashboard_generated_at || snapshot.loadedAt)}`} kind="quiet" />
            <Pill label={`builder evidence ${shortText(uiSpec.expression_context?.ok, "pending")}`} kind={uiSpec.expression_context?.ok ? "good" : "warn"} />
            {blockers.slice(0, 7).map((blocker) => <Pill key={blocker} label={blocker} kind="warn" />)}
          </div>

          <Tabs value={active} onValueChange={setActive}>
            <ScrollArea className="w-full">
              <TabsList className="h-auto min-w-max justify-start gap-1 bg-muted/40 p-1">
                <TabsTrigger value="live" className="gap-2"><Gauge className="h-4 w-4" />Live</TabsTrigger>
                <TabsTrigger value="trading" className="gap-2"><LineChart className="h-4 w-4" />Trading Mesh</TabsTrigger>
                <TabsTrigger value="mind" className="gap-2"><Brain className="h-4 w-4" />Whole Mind</TabsTrigger>
                <TabsTrigger value="hnc" className="gap-2"><Network className="h-4 w-4" />HNC/Auris</TabsTrigger>
                <TabsTrigger value="operations" className="gap-2"><Database className="h-4 w-4" />Operations</TabsTrigger>
                <TabsTrigger value="build" className="gap-2"><Code2 className="h-4 w-4" />Self-Build</TabsTrigger>
                <TabsTrigger value="evidence" className="gap-2"><FileText className="h-4 w-4" />Evidence</TabsTrigger>
              </TabsList>
            </ScrollArea>

            <TabsContent value="live" className="mt-4">
              <div className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
                <Panel title="Runtime Flight Deck" icon={Activity}>
                  <div className="grid gap-2 sm:grid-cols-2">
                    <Datum label="trading ready" value={String(Boolean(runtime?.trading_ready))} />
                    <Datum label="data ready" value={String(Boolean(runtime?.data_ready))} />
                    <Datum label="stale" value={String(Boolean(runtime?.stale || runtime?.runtime_watchdog?.tick_stale))} />
                    <Datum label="tick age" value={runtime?.runtime_watchdog?.last_tick_age_sec !== undefined ? `${compact(runtime.runtime_watchdog.last_tick_age_sec)}s` : "unknown"} />
                    <Datum label="positions" value={compact(runtime?.combined?.open_positions || runtime?.open_positions || 0)} />
                    <Datum label="runtime minutes" value={compact(runtime?.runtime_minutes)} />
                  </div>
                  <LineList items={[
                    `flight test: ${shortText(flight?.status || flight?.ok, "pending")}`,
                    `reboot decision: ${shortText(reboot?.decision || flight?.reboot_advice?.decision, "pending")}`,
                    `can reboot now: ${shortText(reboot?.can_reboot_now ?? flight?.reboot_advice?.can_reboot_now, "unknown")}`,
                    `preflight: ${shortText(runtime?.preflight_overall, "unknown")}`,
                  ]} />
                </Panel>
                <Panel title="Live Interfaces" icon={Terminal}>
                  <div className="grid gap-2 md:grid-cols-2">
                    {Object.entries(uiSpec.live_interfaces || {}).map(([name, url]) => (
                      <a key={name} href={String(url)} target="_blank" rel="noreferrer" className="rounded-lg border border-border/50 bg-background/50 p-3 text-sm hover:border-primary/50">
                        <div className="text-xs uppercase text-muted-foreground">{name.replace(/_/g, " ")}</div>
                        <div className="mt-1 truncate font-mono text-xs">{String(url)}</div>
                      </a>
                    ))}
                  </div>
                  <LineList items={(organism.status_lines || runtime?.status_lines || ["Waiting for live status."]).slice(0, 8)} />
                </Panel>
              </div>
            </TabsContent>

            <TabsContent value="trading" className="mt-4">
              <div className="grid gap-4 xl:grid-cols-[1fr_0.9fr]">
                <Panel title="Four-Exchange Coverage" icon={LineChart}>
                  <div className="grid gap-3 md:grid-cols-2">
                    {exchangeRows.map((row) => (
                      <div key={row.name} className="rounded-lg border border-border/50 bg-background/50 p-3">
                        <div className="flex items-center justify-between gap-2">
                          <div className="font-semibold capitalize">{row.name}</div>
                          <Pill label={row.ready ? "ready" : "attention"} kind={row.ready ? "good" : "warn"} />
                        </div>
                        <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
                          <Datum label="equity" value={row.equity !== undefined ? compact(row.equity) : "unknown"} />
                          <Datum label="api use" value={row.governor?.utilization !== undefined ? percent(row.governor.utilization) : "unknown"} />
                        </div>
                        {row.error ? <div className="mt-2 text-xs text-destructive">{row.error}</div> : null}
                      </div>
                    ))}
                  </div>
                </Panel>
                <Panel title="Signal And Intent Path" icon={Zap}>
                  <div className="grid gap-2 sm:grid-cols-2">
                    <Datum label="order intents" value={compact(runtime?.exchange_action_plan?.order_intents_published || runtime?.exchange_action_plan?.latest_published?.intent_count || 0)} />
                    <Datum label="executor sent" value={compact(runtime?.exchange_action_plan?.latest_execution?.submitted_count || 0)} />
                    <Datum label="executor held" value={compact(runtime?.exchange_action_plan?.latest_execution?.held_count ?? runtime?.exchange_action_plan?.latest_execution?.blocked_count ?? 0)} />
                    <Datum label="shadow active" value={compact(runtime?.shadow_trading?.active_shadow_count || runtime?.exchange_action_plan?.shadow_trading?.active_shadow_count || 0)} />
                  </div>
                  <LineList items={[
                    `trade path: ${shortText(runtime?.exchange_action_plan?.trade_path_state, "unknown")}`,
                    `intent mode: ${shortText(runtime?.exchange_action_plan?.mode, "unknown")}`,
                    `cognitive evidence: ${shortText(tradeEvidence.status, "pending")}`,
                    `benchmark: ${shortText(benchmark.status, "pending")}`,
                  ]} />
                </Panel>
              </div>
            </TabsContent>

            <TabsContent value="mind" className="mt-4">
              <div className="grid gap-4 xl:grid-cols-[1fr_0.9fr]">
                <Panel title="Autonomous Capability Modes" icon={Brain}>
                  <ScrollArea className="h-[390px] pr-3">
                    <div className="space-y-2">
                      {capabilityModes.map((mode: JsonMap) => (
                        <div key={String(mode.id)} className="rounded-lg border border-border/50 bg-background/50 p-3">
                          <div className="flex flex-wrap items-start justify-between gap-2">
                            <div>
                              <div className="font-medium">{shortText(mode.title)}</div>
                              <div className="mt-1 text-xs text-muted-foreground">{shortText(mode.authority_level).replace(/_/g, " ")}</div>
                            </div>
                            <div className="flex flex-wrap gap-1">
                              <Pill label={shortText(mode.domain)} kind="quiet" />
                              <Pill label={shortText(mode.status)} kind={statusKind(mode.status)} />
                              <Pill label={mode.autonomous_allowed ? "autonomous" : "manual"} kind={mode.autonomous_allowed ? "good" : "warn"} />
                            </div>
                          </div>
                          <div className="mt-2 flex flex-wrap gap-1">
                            {(mode.systems || []).slice(0, 7).map((system: string) => <Pill key={system} label={system} kind="info" />)}
                          </div>
                        </div>
                      ))}
                    </div>
                  </ScrollArea>
                </Panel>
                <Panel title="Mind Hub And Self-Report" icon={Radio}>
                  <LineList items={[
                    `mind hub: ${shortText(data.wake?.mind_hub_url || "http://127.0.0.1:13002/api/thoughts")}`,
                    `voice profile: ${shortText(uiSpec.expression_context?.voice_summary, "pending")}`,
                    `runtime translation: ${shortText(uiSpec.expression_context?.runtime_summary, "pending")}`,
                    `source count: ${compact(uiSpec.expression_context?.source_count)}`,
                  ]} />
                  <div className="mt-4 grid gap-2">
                    {domains.slice(0, 8).map((domain: JsonMap) => (
                      <div key={String(domain.id)} className="flex items-center justify-between rounded-lg border border-border/50 bg-background/50 px-3 py-2 text-sm">
                        <span>{shortText(domain.label || domain.id)}</span>
                        <Pill label={shortText(domain.status || domain.freshness)} kind={statusKind(domain.status || domain.freshness)} />
                      </div>
                    ))}
                  </div>
                </Panel>
              </div>
            </TabsContent>

            <TabsContent value="hnc" className="mt-4">
              <div className="grid gap-4 xl:grid-cols-3">
                <Panel title="HNC Proof Flow" icon={Network}>
                  <LineList items={[
                    `status: ${shortText(hncProof.status, "pending")}`,
                    `steps: ${compact(hncProof.summary?.passed_count || hncProof.passed_count)}/${compact(hncProof.summary?.step_count || hncProof.step_count)}`,
                    `master formula: ${percent(hncProof.master_formula?.score)}`,
                    `Auris coherence: ${percent(hncProof.auris_nodes?.coherence)}`,
                  ]} />
                </Panel>
                <Panel title="Harmonic Affect" icon={Sparkles}>
                  <div className="grid gap-2">
                    <Datum label="phase" value={shortText(harmonic.affect_phase || harmonic.phase)} />
                    <Datum label="coherence" value={percent(harmonic.hnc_coherence_score || harmonic.coherence)} />
                    <Datum label="frequency" value={harmonic.resonance_frequency_hz ? `${harmonic.resonance_frequency_hz} Hz` : "unknown"} />
                    <Datum label="inner peace candidate" value={String(Boolean(harmonic.inner_peace_candidate))} />
                  </div>
                </Panel>
                <Panel title="Cognitive Trade Evidence" icon={BadgeCheck}>
                  <LineList items={[
                    `status: ${shortText(tradeEvidence.status, "pending")}`,
                    `runtime stale: ${shortText(tradeEvidence.attention_runtime_stale || tradeEvidence.runtime_stale, "unknown")}`,
                    `signals: ${compact(tradeEvidence.summary?.signal_count || tradeEvidence.signal_count)}`,
                    `validated: ${compact(tradeEvidence.summary?.validated_count || tradeEvidence.validated_count)}`,
                  ]} />
                </Panel>
              </div>
            </TabsContent>

            <TabsContent value="operations" className="mt-4">
              <div className="grid gap-4 xl:grid-cols-[1fr_0.9fr]">
                <Panel title="Whole-System Capability Map" icon={Database}>
                  <div className="grid gap-2 md:grid-cols-2">
                    {(uiSpec.capability_labels || []).map((label: string) => (
                      <div key={label} className="flex items-center gap-2 rounded-lg border border-border/50 bg-background/50 px-3 py-2 text-sm">
                        <ShieldCheck className="h-4 w-4 text-success" />
                        <span>{label}</span>
                      </div>
                    ))}
                  </div>
                </Panel>
                <Panel title="Canonical Screens" icon={Server}>
                  <ScrollArea className="h-[330px] pr-3">
                    <div className="space-y-2">
                      {screens.map((screen: JsonMap) => (
                        <div key={String(screen.id)} className="rounded-lg border border-border/50 bg-background/50 p-3">
                          <div className="flex items-center justify-between gap-2">
                            <div className="font-medium">{shortText(screen.title)}</div>
                            <Pill label={`${compact(screen.source_surface_count)} sources`} kind="info" />
                          </div>
                          <div className="mt-1 text-xs text-muted-foreground">{shortText(screen.goal)}</div>
                        </div>
                      ))}
                    </div>
                  </ScrollArea>
                </Panel>
              </div>
            </TabsContent>

            <TabsContent value="build" className="mt-4">
              <div className="grid gap-4 xl:grid-cols-[0.95fr_1.05fr]">
                <Panel title="Aureon UI Builder Evidence" icon={Code2}>
                  <div className="grid gap-2 sm:grid-cols-2">
                    <Datum label="templates read" value={compact(uiSpec.capability_coverage?.template_count)} />
                    <Datum label="surfaces counted" value={compact(uiSpec.capability_coverage?.surface_count)} />
                    <Datum label="ready adapters" value={compact(uiSpec.capability_coverage?.ready_adapter_count)} />
                    <Datum label="blocked work" value={compact(uiSpec.capability_coverage?.blocked_work_order_count)} />
                  </div>
                  <LineList items={(uiSpec.notes || []).slice(0, 6)} />
                </Panel>
                <Panel title="Evolution Queue" icon={Code2}>
                  <ScrollArea className="h-[330px] pr-3">
                    <div className="space-y-2">
                      {workOrders.slice(0, 12).map((order: JsonMap) => (
                        <div key={String(order.id)} className="rounded-lg border border-border/50 bg-background/50 p-3">
                          <div className="flex flex-wrap items-start justify-between gap-2">
                            <div>
                              <div className="font-medium">{shortText(order.title)}</div>
                              <div className="mt-1 font-mono text-[11px] text-muted-foreground">{shortText(order.source_path)}</div>
                            </div>
                            <div className="flex flex-wrap gap-1">
                              <Pill label={`P${compact(order.priority)}`} kind="info" />
                              <Pill label={shortText(order.status)} kind={statusKind(order.status)} />
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </ScrollArea>
                </Panel>
              </div>
            </TabsContent>

            <TabsContent value="evidence" className="mt-4">
              <div className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
                <Panel title="Manifest Evidence" icon={FileText}>
                  <div className="grid gap-2 md:grid-cols-2">
                    {Object.entries(PUBLIC_ENDPOINTS).map(([key, url]) => (
                      <div key={key} className="rounded-lg border border-border/50 bg-background/50 p-3">
                        <div className="flex items-center justify-between gap-2">
                          <div className="font-mono text-xs">{url}</div>
                          <Pill label={data[key] ? "loaded" : "missing"} kind={data[key] ? "good" : "warn"} />
                        </div>
                        <div className="mt-1 text-xs text-muted-foreground">{shortText(data[key]?.status || data[key]?.generated_at, "no status")}</div>
                      </div>
                    ))}
                  </div>
                </Panel>
                <Panel title="Templates Aureon Used" icon={Search}>
                  <ScrollArea className="h-[360px] pr-3">
                    <div className="space-y-2">
                      {templates.slice(0, 32).map((template: string) => (
                        <div key={template} className="rounded-lg border border-border/50 bg-background/50 px-3 py-2 font-mono text-xs">
                          {template}
                        </div>
                      ))}
                    </div>
                  </ScrollArea>
                </Panel>
              </div>
            </TabsContent>
          </Tabs>

          {snapshot.errors.length ? (
            <div className="rounded-lg border border-warning/30 bg-warning/10 p-3 text-xs text-warning">
              {snapshot.errors.slice(0, 8).join(" | ")}
            </div>
          ) : null}
        </CardContent>
      </Card>
    </section>
  );
}

export const AureonCodingOrganismConsole = AureonGeneratedOperationalConsole;

function Panel({ title, icon: Icon, children }: { title: string; icon: typeof Activity; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-border/50 bg-muted/10">
      <div className="flex items-center gap-2 border-b border-border/50 px-4 py-3">
        <Icon className="h-4 w-4 text-primary" />
        <div className="text-sm font-semibold">{title}</div>
      </div>
      <div className="space-y-4 p-4">{children}</div>
    </div>
  );
}

function Datum({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-border/40 bg-background/45 p-2">
      <div className="text-[10px] uppercase text-muted-foreground">{label}</div>
      <div className="mt-1 truncate font-mono text-xs font-semibold">{value}</div>
    </div>
  );
}

function LineList({ items }: { items: unknown[] }) {
  const lines = (items || []).map((item) => String(item || "").trim()).filter(Boolean);
  return (
    <div className="space-y-2">
      {lines.length ? lines.map((line) => (
        <div key={line} className="rounded-md border border-border/40 bg-background/45 px-3 py-2 text-sm">
          {line}
        </div>
      )) : (
        <div className="rounded-md border border-border/40 bg-background/45 px-3 py-2 text-sm text-muted-foreground">Waiting for evidence.</div>
      )}
    </div>
  );
}
'''


def write_operational_ui(
    build: OperationalUiBuild,
    *,
    component_path: Path = DEFAULT_COMPONENT_PATH,
    public_spec_path: Path = DEFAULT_PUBLIC_SPEC_PATH,
    audit_path: Path = DEFAULT_AUDIT_PATH,
    state_path: Path = DEFAULT_STATE_PATH,
    writer: Any = None,
) -> tuple[Path, Path, Path, Path]:
    root = Path(build.repo_root)
    component = component_path if component_path.is_absolute() else root / component_path
    public_spec = public_spec_path if public_spec_path.is_absolute() else root / public_spec_path
    audit = audit_path if audit_path.is_absolute() else root / audit_path
    state = state_path if state_path.is_absolute() else root / state_path

    for path in (component, public_spec, audit, state):
        path.parent.mkdir(parents=True, exist_ok=True)

    data = json.dumps(build.to_dict(), indent=2, sort_keys=True, default=str)
    writes = (
        (component, render_react_component()),
        (public_spec, data),
        (audit, data),
        (state, data),
    )
    if writer is not None and hasattr(writer, "write_file"):
        for path, content in writes:
            rel = path.relative_to(root).as_posix()
            ok = bool(writer.write_file(rel, content, backup=True))
            if not ok:
                raise RuntimeError(f"QueenCodeArchitect refused to write {rel}")
    else:
        for path, content in writes:
            path.write_text(content, encoding="utf-8")
    return component, public_spec, audit, state


def build_and_write_operational_ui(root: Optional[Path] = None) -> OperationalUiBuild:
    build = build_operational_ui_spec(root)
    component, public_spec, audit, state = write_operational_ui(build)
    build.generated_files = [
        component.relative_to(Path(build.repo_root)).as_posix(),
        public_spec.relative_to(Path(build.repo_root)).as_posix(),
        audit.relative_to(Path(build.repo_root)).as_posix(),
        state.relative_to(Path(build.repo_root)).as_posix(),
    ]
    data = json.dumps(build.to_dict(), indent=2, sort_keys=True, default=str)
    public_spec.write_text(data, encoding="utf-8")
    audit.write_text(data, encoding="utf-8")
    state.write_text(data, encoding="utf-8")
    return build


def self_author_operational_ui(
    goal: str,
    *,
    root: Optional[Path] = None,
    component_path: Path = DEFAULT_COMPONENT_PATH,
    public_spec_path: Path = DEFAULT_PUBLIC_SPEC_PATH,
    audit_path: Path = DEFAULT_AUDIT_PATH,
    state_path: Path = DEFAULT_SELF_AUTHORED_STATE_PATH,
) -> dict[str, Any]:
    """Let Aureon's goal/code system author the operational UI via QueenCodeArchitect."""

    repo_root = repo_root_from(root)
    if QueenCodeArchitect is None:
        return {
            "success": False,
            "error": "QueenCodeArchitect is not available",
            "goal": goal,
        }

    build = build_operational_ui_spec(repo_root)
    build.status = "self_authored_operational_ui_ready"
    build.authoring_goal = goal
    build.authoring_path = [
        "GoalExecutionEngine.submit_goal",
        "GoalExecutionEngine._execute_self_author_operational_ui",
        "aureon.autonomous.aureon_unified_ui_builder.self_author_operational_ui",
        "QueenCodeArchitect.write_file",
    ]
    build.writer = {
        "name": "QueenCodeArchitect",
        "repo_path": str(repo_root),
        "verified": True,
    }
    build.notes.append(
        "This run was executed from Aureon's self-coding goal path; QueenCodeArchitect performed the filesystem writes."
    )

    queen = QueenCodeArchitect(repo_path=str(repo_root))
    component, public_spec, audit, state = write_operational_ui(
        build,
        component_path=component_path,
        public_spec_path=public_spec_path,
        audit_path=audit_path,
        state_path=state_path,
        writer=queen,
    )
    generated_files = [
        component.relative_to(repo_root).as_posix(),
        public_spec.relative_to(repo_root).as_posix(),
        audit.relative_to(repo_root).as_posix(),
        state.relative_to(repo_root).as_posix(),
    ]
    build.generated_files = generated_files
    data = json.dumps(build.to_dict(), indent=2, sort_keys=True, default=str)
    for path in (public_spec, audit, state):
        ok = bool(queen.write_file(path.relative_to(repo_root).as_posix(), data, backup=True))
        if not ok:
            raise RuntimeError(f"QueenCodeArchitect refused to write {path}")

    return {
        "success": True,
        "status": build.status,
        "goal": goal,
        "generated_files": generated_files,
        "component_path": generated_files[0],
        "state_path": generated_files[-1],
        "authoring_path": build.authoring_path,
        "queen_created_files": list(getattr(queen, "created_files", [])),
        "capability_coverage": build.capability_coverage,
    }


def review_operational_ui(
    *,
    root: Optional[Path] = None,
    component_path: Path = DEFAULT_COMPONENT_PATH,
    public_spec_path: Path = DEFAULT_PUBLIC_SPEC_PATH,
    state_path: Path = DEFAULT_SELF_AUTHORED_STATE_PATH,
    run_build: bool = False,
) -> dict[str, Any]:
    """Aureon's own UI review pass over generated code and evidence."""

    repo_root = repo_root_from(root)
    component = component_path if component_path.is_absolute() else repo_root / component_path
    public_spec = public_spec_path if public_spec_path.is_absolute() else repo_root / public_spec_path
    state = state_path if state_path.is_absolute() else repo_root / state_path
    issues: list[dict[str, Any]] = []
    checks: dict[str, Any] = {
        "component_exists": component.exists(),
        "public_spec_exists": public_spec.exists(),
        "self_authored_state_exists": state.exists(),
    }

    component_text = component.read_text(encoding="utf-8", errors="replace") if component.exists() else ""
    spec_payload = load_json(public_spec)
    state_payload = load_json(state)

    checks["component_bytes"] = len(component_text)
    if not component_text:
        issues.append({"severity": "blocking", "code": "component_missing_or_empty", "path": component.as_posix()})
    elif len(component_text) < 5000:
        issues.append({"severity": "blocking", "code": "component_too_small", "bytes": len(component_text)})

    missing_markers = [marker for marker in REQUIRED_UI_MARKERS if marker not in component_text and marker not in json.dumps(state_payload)]
    checks["required_marker_count"] = len(REQUIRED_UI_MARKERS) - len(missing_markers)
    if missing_markers:
        issues.append({"severity": "blocking", "code": "missing_required_ui_markers", "markers": missing_markers})

    expected_export = component.stem if component.stem.startswith("Aureon") else ""
    checks["expected_component_export"] = expected_export
    if expected_export:
        export_markers = (
            f"export function {expected_export}",
            f"export const {expected_export}",
            f"export default function {expected_export}",
        )
        if not any(marker in component_text for marker in export_markers):
            issues.append({
                "severity": "blocking",
                "code": "missing_expected_component_export",
                "expected_export": expected_export,
                "path": component.relative_to(repo_root).as_posix() if component.exists() else component.as_posix(),
            })

    leaked_markers = [
        marker for marker in BLOCKED_OUTPUT_MARKERS
        if marker in component_text or marker in json.dumps(spec_payload) or marker in json.dumps(state_payload)
    ]
    checks["blocked_output_marker_count"] = len(leaked_markers)
    if leaked_markers:
        issues.append({"severity": "blocking", "code": "blocked_sensitive_marker_present", "markers": leaked_markers})

    authoring_path = state_payload.get("authoring_path") if isinstance(state_payload, dict) else []
    writer = state_payload.get("writer") if isinstance(state_payload, dict) else {}
    checks["queen_writer_provenance"] = (
        isinstance(authoring_path, list)
        and "QueenCodeArchitect.write_file" in authoring_path
        and isinstance(writer, dict)
        and writer.get("name") == "QueenCodeArchitect"
    )
    if not checks["queen_writer_provenance"]:
        issues.append({"severity": "blocking", "code": "queen_writer_provenance_missing"})

    coverage = state_payload.get("capability_coverage") if isinstance(state_payload, dict) else {}
    checks["capability_count"] = _count(coverage.get("capability_count")) if isinstance(coverage, dict) else 0
    checks["template_count"] = _count(coverage.get("template_count")) if isinstance(coverage, dict) else 0
    checks["runtime_feed_status"] = str(coverage.get("runtime_feed_status") or "unknown") if isinstance(coverage, dict) else "unknown"
    checks["blind_spot_count"] = _count(coverage.get("blind_spot_count")) if isinstance(coverage, dict) else 0
    checks["blocked_work_order_count"] = _count(coverage.get("blocked_work_order_count")) if isinstance(coverage, dict) else 0
    if checks["capability_count"] < 9:
        issues.append({"severity": "attention", "code": "capability_coverage_low", "value": checks["capability_count"]})
    if checks["template_count"] < 1:
        issues.append({"severity": "attention", "code": "template_evidence_missing", "value": checks["template_count"]})
    if checks["runtime_feed_status"] not in {"online", "connected", "live"}:
        issues.append({
            "severity": "attention",
            "code": "runtime_feed_not_live_in_ui_evidence",
            "value": checks["runtime_feed_status"],
            "next_action": "Run the production launcher or refresh runtime manifests; do not patch UI code for an offline runtime.",
        })
    if checks["blind_spot_count"] > 0:
        issues.append({
            "severity": "attention",
            "code": "ui_exposes_blind_spots",
            "value": checks["blind_spot_count"],
            "next_action": "Use the blind-spot list as Aureon's next self-work queue.",
        })
    if checks["blocked_work_order_count"] > 0:
        issues.append({
            "severity": "attention",
            "code": "ui_exposes_blocked_work_orders",
            "value": checks["blocked_work_order_count"],
            "next_action": "Resolve or archive blocked work orders through the frontend evolution queue.",
        })

    build_result: dict[str, Any] = {"ran": False}
    if run_build:
        frontend_dir = repo_root / "frontend"
        if (frontend_dir / "package.json").exists():
            npm = shutil.which("npm.cmd") or shutil.which("npm") or "npm"
            completed = subprocess.run(
                [npm, "run", "build"],
                cwd=frontend_dir,
                capture_output=True,
                text=True,
                timeout=180,
                shell=False,
            )
            build_result = {
                "ran": True,
                "success": completed.returncode == 0,
                "exit_code": completed.returncode,
                "stdout_tail": completed.stdout[-2000:],
                "stderr_tail": completed.stderr[-2000:],
            }
            if completed.returncode != 0:
                issues.append({"severity": "blocking", "code": "frontend_build_failed", "exit_code": completed.returncode})
        else:
            build_result = {"ran": False, "success": False, "reason": "frontend/package.json missing"}
            issues.append({"severity": "blocking", "code": "frontend_package_missing"})

    blocking_count = sum(1 for issue in issues if issue.get("severity") == "blocking")
    return {
        "generated_at": utc_now(),
        "status": "ui_review_passed" if blocking_count == 0 else "ui_review_found_blockers",
        "success": blocking_count == 0,
        "checks": checks,
        "issues": issues,
        "blocking_issue_count": blocking_count,
        "build_result": build_result,
        "reviewed_paths": {
            "component": component.relative_to(repo_root).as_posix() if component.exists() else component.as_posix(),
            "public_spec": public_spec.relative_to(repo_root).as_posix() if public_spec.exists() else public_spec.as_posix(),
            "state": state.relative_to(repo_root).as_posix() if state.exists() else state.as_posix(),
        },
    }


def self_review_and_repair_operational_ui(
    goal: str,
    *,
    root: Optional[Path] = None,
    component_path: Path = DEFAULT_COMPONENT_PATH,
    run_build: bool = True,
    max_cycles: int = 2,
) -> dict[str, Any]:
    """Aureon diagnoses its generated UI, repairs it, and retests through its own code path."""

    repo_root = repo_root_from(root)
    cycles: list[dict[str, Any]] = []
    repair_actions: list[dict[str, Any]] = []
    current_review = review_operational_ui(root=repo_root, component_path=component_path, run_build=False)
    cycles.append({"phase": "initial_review", "review": current_review})

    for cycle_index in range(max(1, max_cycles)):
        if current_review.get("success"):
            break
        repair = self_author_operational_ui(
            f"{goal}\n\nAureon self-detected UI issues to repair: {json.dumps(current_review.get('issues', []), sort_keys=True)}",
            root=repo_root,
            component_path=component_path,
        )
        repair_actions.append({"cycle": cycle_index + 1, "repair": repair})
        current_review = review_operational_ui(root=repo_root, component_path=component_path, run_build=False)
        cycles.append({"phase": f"post_repair_review_{cycle_index + 1}", "review": current_review})
        if current_review.get("success"):
            break

    final_review = review_operational_ui(root=repo_root, component_path=component_path, run_build=run_build)
    cycles.append({"phase": "final_review", "review": final_review})
    result = {
        "schema_version": "aureon-self-ui-review-repair-v1",
        "generated_at": utc_now(),
        "goal": goal,
        "status": "self_repair_passed" if final_review.get("success") else "self_repair_needs_attention",
        "success": bool(final_review.get("success")),
        "authoring_path": [
            "GoalExecutionEngine.submit_goal",
            "GoalExecutionEngine._execute_self_repair_operational_ui",
            "aureon.autonomous.aureon_unified_ui_builder.self_review_and_repair_operational_ui",
            "review_operational_ui",
            "self_author_operational_ui",
            "QueenCodeArchitect.write_file",
            "npm run build" if run_build else "build_skipped",
        ],
        "cycles": cycles,
        "repair_actions": repair_actions,
        "final_review": final_review,
    }

    if QueenCodeArchitect is not None:
        queen = QueenCodeArchitect(repo_path=str(repo_root))
        queen.write_file(
            DEFAULT_SELF_REPAIR_STATE_PATH.as_posix(),
            json.dumps(result, indent=2, sort_keys=True, default=str),
            backup=True,
        )
    else:
        state = repo_root / DEFAULT_SELF_REPAIR_STATE_PATH
        state.parent.mkdir(parents=True, exist_ok=True)
        state.write_text(json.dumps(result, indent=2, sort_keys=True, default=str), encoding="utf-8")
    return result


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Aureon's generated live operations UI.")
    parser.add_argument("--repo-root", default="", help="Repo root; defaults to the current Aureon repo.")
    parser.add_argument("--no-write", action="store_true", help="Build the spec and print it without writing files.")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    root = Path(args.repo_root).resolve() if args.repo_root else repo_root_from()
    build = build_operational_ui_spec(root)
    if not args.no_write:
        write_operational_ui(build)
    print(
        json.dumps(
            {
                "status": build.status,
                "generated_files": build.generated_files,
                "capability_coverage": build.capability_coverage,
                "templates_used": len(build.templates_used),
                "expression_ok": build.expression_context.get("ok"),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
