/**
 * Overview — the platform's front page.
 *
 * Live platform health from GET /api/status, domain tiles from the unified
 * frontend state (manifests), a billing/metering snapshot, and quick routes to
 * every section. Everything degrades honestly with no backend connected.
 */

import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Sparkles } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  loadUnifiedFrontendState,
  type UnifiedFrontendState,
} from "@/services/aureonAutonomousFrontend";
import { NAV_SECTIONS } from "../nav";

interface PlatformStatus {
  status?: string;
  domains_reachable?: number;
  domains_total?: number;
  product_domains?: Record<string, { status?: string; reachable?: number; total?: number }>;
  note?: string;
}

interface BillingStatus {
  configured?: boolean;
  metering?: { sink?: string; flushed?: number; pending?: number };
  charge_endpoint?: { enabled?: boolean };
}

interface OrganismStatus {
  available?: boolean;
  connectome?: {
    nodes?: number;
    baton_linked?: number;
    touched?: number;
    woven?: number;
    coverage_pct?: number;
  };
}

interface AutomationIndex {
  index_pct?: number | null;
  label?: string;
  dimensions?: Record<string, { pct?: number | null; weight?: number; detail?: string }>;
  journey?: Array<{ ts?: number; index_pct?: number }>;
  truth_status?: string;
}

interface DefenseSummary {
  counts?: { total?: number; passing?: number };
  truth_status?: string;
}

/** Dependency-free sparkline over the recorded journey; scales 0–100. */
function JourneySparkline({ points }: { points: number[] }) {
  const pts = points.filter((v) => Number.isFinite(v));
  if (pts.length < 2) return null;
  const w = 240;
  const h = 28;
  const d = pts
    .map((v, i) => `${(i / (pts.length - 1)) * w},${(h - (Math.max(0, Math.min(100, v)) / 100) * h).toFixed(2)}`)
    .join(" ");
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="h-7 w-full text-primary/70" preserveAspectRatio="none"
         role="img" aria-label="automation progress over time">
      <polyline points={d} fill="none" stroke="currentColor" strokeWidth={1.5}
                vectorEffect="non-scaling-stroke" strokeLinejoin="round" strokeLinecap="round" />
    </svg>
  );
}

const DIM_LABEL: Record<string, string> = {
  connectivity: "Connectivity",
  integration: "Integration",
  consciousness: "Consciousness",
  surfacing: "Surfacing",
};

function Bar({ pct, className }: { pct: number; className?: string }) {
  return (
    <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
      <div className={`h-full rounded-full ${className ?? "bg-primary"}`}
           style={{ width: `${Math.max(0, Math.min(100, pct))}%` }} />
    </div>
  );
}

async function fetchJson<T>(url: string): Promise<T | null> {
  try {
    const r = await fetch(url, { cache: "no-store" });
    return r.ok ? ((await r.json()) as T) : null;
  } catch {
    return null;
  }
}

const HEALTH_BADGE: Record<string, string> = {
  healthy: "bg-success/15 text-success border-success/30",
  ready: "bg-success/15 text-success border-success/30",
  degraded: "bg-primary/15 text-primary border-primary/30",
  critical: "bg-destructive/15 text-destructive border-destructive/30",
  down: "bg-destructive/15 text-destructive border-destructive/30",
};

function healthBadgeClass(status: string | undefined): string {
  return HEALTH_BADGE[String(status || "")] ?? "bg-muted text-muted-foreground";
}

export default function OverviewPage() {
  const [status, setStatus] = useState<PlatformStatus | null | undefined>(undefined);
  const [billing, setBilling] = useState<BillingStatus | null | undefined>(undefined);
  const [organism, setOrganism] = useState<OrganismStatus | null | undefined>(undefined);
  const [automation, setAutomation] = useState<AutomationIndex | null | undefined>(undefined);
  const [defense, setDefense] = useState<DefenseSummary | null | undefined>(undefined);
  const [unified, setUnified] = useState<UnifiedFrontendState | null>(null);

  useEffect(() => {
    fetchJson<PlatformStatus>("/api/status").then(setStatus);
    fetchJson<BillingStatus>("/api/billing/status").then(setBilling);
    fetchJson<OrganismStatus>("/api/organism").then(setOrganism);
    fetchJson<AutomationIndex>("/api/automation").then(setAutomation);  // once — avoids repeated organ cold-boot
    fetchJson<DefenseSummary>("/api/defense").then(setDefense);
    loadUnifiedFrontendState().then(setUnified).catch(() => setUnified(null));
  }, []);

  const domains = status?.product_domains ?? {};
  const surfaceCount = unified?.inventory?.summary?.surface_count;

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-6">
      <div className="space-y-1">
        <div className="flex items-center gap-2">
          <Sparkles className="h-6 w-6 text-primary" />
          <h1 className="text-2xl font-semibold tracking-tight">Aureon Platform</h1>
        </div>
        <p className="text-sm text-muted-foreground">
          One interface for the whole organism — trading, planetary research, cognition,
          the coding system, operations, and the platform itself.
        </p>
      </div>

      {/* Automation progress — the headline metric toward "fully automated" */}
      <Card className="border-primary/30">
        <CardHeader className="pb-2">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <CardTitle className="text-base">Automation progress</CardTitle>
            {automation && automation.index_pct != null && (
              <Badge variant="outline" className="text-xs">{automation.label}</Badge>
            )}
          </div>
          <CardDescription>
            How much of the repo is connected into the organism and driveable by the
            soul/consciousness logic — composed from real coverage, never fabricated.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {automation === undefined ? (
            <Skeleton className="h-10 w-full" />
          ) : !automation || automation.index_pct == null ? (
            <p className="text-xs text-muted-foreground">
              Gateway offline (or organism cold) — start the operator for live progress.
            </p>
          ) : (
            <>
              <div className="flex items-end gap-3">
                <span className="font-mono text-3xl tabular-nums text-primary">
                  {automation.index_pct.toFixed(1)}%
                </span>
                <span className="pb-1 text-xs text-muted-foreground">toward fully automated</span>
              </div>
              <Bar pct={automation.index_pct} />
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                {Object.entries(automation.dimensions ?? {}).map(([name, d]) => (
                  <div key={name} className="space-y-1">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-muted-foreground">{DIM_LABEL[name] ?? name}</span>
                      <span className="font-mono tabular-nums">
                        {d.pct == null ? "—" : `${d.pct.toFixed(1)}%`}
                      </span>
                    </div>
                    <Bar pct={d.pct ?? 0} className="bg-primary/60" />
                  </div>
                ))}
              </div>
              {(automation.journey?.length ?? 0) >= 2 && (
                <div className="space-y-1">
                  <span className="text-xs text-muted-foreground">the journey — breath by breath</span>
                  <JourneySparkline points={(automation.journey ?? []).map((p) => p.index_pct ?? NaN)} />
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>

      {/* Defenses — the bio family's benchmark health (immune layer + statistical validity + lanes) */}
      <Card>
        <CardHeader className="pb-2">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <CardTitle className="text-base">Defense & Validation</CardTitle>
            <Link to="/defense" className="text-xs text-primary hover:underline inline-flex items-center gap-1">
              open <ArrowRight className="h-3 w-3" />
            </Link>
          </div>
          <CardDescription>
            The cognitive immune layer + statistical-validity dossier + sensor lanes — real
            Tier-A benchmark status, never fabricated.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {defense === undefined ? (
            <Skeleton className="h-8 w-40" />
          ) : !defense || defense.counts?.total == null ? (
            <p className="text-xs text-muted-foreground">
              Gateway offline — start the operator for live defense status.
            </p>
          ) : (
            <div className="flex items-center gap-3">
              <span className="font-mono text-2xl tabular-nums text-primary">
                {defense.counts.passing}/{defense.counts.total}
              </span>
              <span className="text-xs text-muted-foreground">bio benchmarks passing · immune layer active</span>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Platform health */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Platform status</CardDescription>
            <CardTitle className="flex items-center gap-2 text-lg">
              {status === undefined ? (
                <Skeleton className="h-6 w-24" />
              ) : status === null ? (
                <Badge variant="outline" className="text-muted-foreground">gateway offline</Badge>
              ) : (
                <Badge variant="outline" className={healthBadgeClass(status.status)}>
                  {status.status}
                </Badge>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent className="text-xs text-muted-foreground">
            {status
              ? `${status.domains_reachable ?? "?"}/${status.domains_total ?? "?"} domains reachable`
              : "Start the operator gateway (:8790) for live health."}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Catalogued surfaces</CardDescription>
            <CardTitle className="text-lg">
              {unified === null && surfaceCount === undefined ? "—" : surfaceCount ?? <Skeleton className="h-6 w-16" />}
            </CardTitle>
          </CardHeader>
          <CardContent className="text-xs text-muted-foreground">
            From the system inventory manifest — every module, categorized.
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Billing & metering</CardDescription>
            <CardTitle className="text-lg">
              {billing === undefined ? (
                <Skeleton className="h-6 w-24" />
              ) : billing === null ? (
                "—"
              ) : (
                <span className="text-sm font-medium">
                  metering: {billing.metering?.sink ?? "unknown"}
                </span>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent className="text-xs text-muted-foreground">
            {billing?.configured
              ? "Supabase billing backend connected."
              : "Record-only metering; free access, support-the-project model."}
          </CardContent>
        </Card>
      </div>

      {/* Organism connectome */}
      <Card className="border-primary/20">
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-base">
            <Sparkles className="h-4 w-4 text-primary" /> Organism connectome
          </CardTitle>
          <CardDescription>
            How much of the body the metacognitive layer has sensed and woven — honest depths.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {organism === undefined ? (
            <Skeleton className="h-10 w-full" />
          ) : !organism?.available || !organism.connectome ? (
            <p className="text-xs text-muted-foreground">
              Connectome offline — start the organism daemon (or the operator gateway) for live coverage.
            </p>
          ) : (
            <div className="flex flex-wrap gap-4 text-sm">
              <span><b>{organism.connectome.nodes ?? "?"}</b> <span className="text-muted-foreground">modules</span></span>
              <span><b>{organism.connectome.baton_linked ?? 0}</b> <span className="text-muted-foreground">linked</span></span>
              <span><b>{organism.connectome.touched ?? 0}</b> <span className="text-muted-foreground">touched</span></span>
              <span><b>{organism.connectome.woven ?? 0}</b> <span className="text-muted-foreground">woven</span></span>
              <span className="text-primary"><b>{organism.connectome.coverage_pct ?? 0}%</b> <span className="text-muted-foreground">felt</span></span>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Domain health */}
      {Object.keys(domains).length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Product domains</CardTitle>
            <CardDescription>Import-level reachability, reported honestly.</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-2">
            {Object.entries(domains).map(([name, d]) => (
              <Badge key={name} variant="outline" className={healthBadgeClass(d.status)}>
                {name} · {d.reachable}/{d.total}
              </Badge>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Section quick routes */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {NAV_SECTIONS.filter((s) => s.label !== "Platform").map((section) => (
          <Card key={section.label} className="transition-shadow hover:shadow-md">
            <CardHeader className="pb-2">
              <CardTitle className="text-base">{section.label}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-1.5">
              {section.items.map((item) => (
                <Link
                  key={item.path}
                  to={item.path}
                  className="group flex items-center gap-2 rounded-md px-2 py-1.5 text-sm text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
                >
                  <item.icon className="h-4 w-4 shrink-0" />
                  <span className="flex-1 truncate">{item.label}</span>
                  <ArrowRight className="h-3.5 w-3.5 opacity-0 transition-opacity group-hover:opacity-100" />
                </Link>
              ))}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
