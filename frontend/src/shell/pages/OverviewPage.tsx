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
  const [unified, setUnified] = useState<UnifiedFrontendState | null>(null);

  useEffect(() => {
    fetchJson<PlatformStatus>("/api/status").then(setStatus);
    fetchJson<BillingStatus>("/api/billing/status").then(setBilling);
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
