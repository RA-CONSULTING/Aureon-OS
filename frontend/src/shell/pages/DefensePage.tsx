/**
 * Defense & Validation — the bio family surfaced as verified SaaS.
 *
 * Reads GET /api/defense and renders the whole bio family in three groups —
 * the cognitive immune layer (integrity guard · swarm defense · MCP membrane),
 * the statistical-validity dossier (size · power · calibration · FWER · FDR),
 * and the sensor lanes — each module carrying its real pass/metrics/evidence
 * from the committed Tier-A benchmark report (with a live bus-trace overlay
 * where it has run) and an honest data-provenance badge. Nothing is fabricated;
 * a module that has neither been benchmarked nor run shows as no_data.
 */

import { useEffect, useState } from "react";
import { ShieldCheck, ShieldAlert, FlaskConical, Radar } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { LiveDataNotice } from "@/shell/Page";
import { type TruthStatus, TRUTH_STATUS_STYLE } from "../truthStatus";


interface DefenseModule {
  key: string;
  name: string;
  module: string;
  group: string;
  passed: boolean;
  metrics: Record<string, number | string | null>;
  invariants_passed: number;
  invariants_total: number;
  evidence: string;
  boundary?: string | null;
  truth_status: TruthStatus;
}

interface DefenseGroup {
  label: string;
  purpose: string;
  module_count: number;
  passing: number;
  modules: DefenseModule[];
}

interface DefensePayload {
  generated_at?: string | null;
  group_order: string[];
  groups: Record<string, DefenseGroup>;
  counts: { total?: number; passing?: number; groups?: number };
  note?: string;
  truth_status: TruthStatus;
}

const GROUP_ICON: Record<string, typeof ShieldCheck> = {
  cognitive_immune_layer: ShieldCheck,
  statistical_validity: FlaskConical,
  sensor_lane: Radar,
};

const STATUS_STYLE: Record<TruthStatus, { cls: string; label: string }> = {
  live: { cls: TRUTH_STATUS_STYLE.live, label: "live" },
  real_derived: { cls: TRUTH_STATUS_STYLE.real_derived, label: "real · derived" },
  cached_real: { cls: TRUTH_STATUS_STYLE.cached_real, label: "cached real" },
  no_data: { cls: TRUTH_STATUS_STYLE.no_data, label: "no data" },
  test_fixture: { cls: TRUTH_STATUS_STYLE.test_fixture, label: "test fixture" },
};

function StatusBadge({ status }: { status: TruthStatus }) {
  const s = STATUS_STYLE[status] ?? STATUS_STYLE.no_data;
  return <Badge variant="outline" className={`text-[10px] ${s.cls}`}>{s.label}</Badge>;
}

/** The two or three most telling metrics for a module, formatted without leaking internals. */
function topMetrics(metrics: Record<string, number | string | null>): { label: string; value: string }[] {
  const fmt = (v: number | string | null) =>
    typeof v === "number" ? (Number.isInteger(v) ? String(v) : v.toFixed(4)) : v == null ? "—" : String(v);
  return Object.entries(metrics)
    .slice(0, 4)
    .map(([label, value]) => ({ label: label.replace(/_/g, " "), value: fmt(value) }));
}

function ModuleCard({ mod }: { mod: DefenseModule }) {
  return (
    <Card className="flex flex-col">
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-2">
          <CardTitle className="text-sm leading-snug">{mod.name}</CardTitle>
          <div className="flex shrink-0 items-center gap-1">
            <Badge variant={mod.passed ? "success" : "destructive"} className="text-[10px]">
              {mod.passed ? "pass" : "fail"}
            </Badge>
            <StatusBadge status={mod.truth_status} />
          </div>
        </div>
      </CardHeader>
      <CardContent className="flex flex-1 flex-col gap-2">
        <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
          {topMetrics(mod.metrics).map((row) => (
            <div key={row.label} className="flex justify-between gap-2">
              <dt className="truncate text-muted-foreground">{row.label}</dt>
              <dd className="font-mono">{row.value}</dd>
            </div>
          ))}
        </dl>
        {mod.invariants_total > 0 && (
          <p className="text-[11px] text-muted-foreground">
            invariants {mod.invariants_passed}/{mod.invariants_total} · <span className="font-mono">{mod.module}</span>
          </p>
        )}
        {mod.evidence && <p className="mt-auto text-[11px] italic text-muted-foreground">{mod.evidence}</p>}
        {mod.boundary && <p className="text-[10px] text-muted-foreground/80">{mod.boundary}</p>}
      </CardContent>
    </Card>
  );
}

export default function DefensePage() {
  const [data, setData] = useState<DefensePayload | null | undefined>(undefined);

  useEffect(() => {
    fetch("/api/defense")
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then(setData)
      .catch(() => setData(null));
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <ShieldCheck className="h-6 w-6 text-primary" />
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Defense & Validation</h1>
          <p className="text-sm text-muted-foreground">
            The bio family — sensor lanes, the statistical-validity dossier, and the cognitive immune
            layer — surfaced from the committed Tier-A benchmark report with honest data provenance.
          </p>
        </div>
      </div>

      <LiveDataNotice />

      {data === undefined && (
        <div className="space-y-3">{Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-40 w-full" />)}</div>
      )}
      {data === null && (
        <Card><CardHeader><CardTitle>Gateway offline</CardTitle></CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            Start the operator for the live Defense & Validation surface.
          </CardContent></Card>
      )}

      {data && (
        <>
          <Card>
            <CardHeader className="pb-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <CardTitle className="text-base">
                  {data.counts.passing} of {data.counts.total} bio benchmarks passing
                </CardTitle>
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Badge variant={data.counts.passing === data.counts.total ? "success" : "secondary"}>
                    {data.counts.passing}/{data.counts.total}
                  </Badge>
                  {data.generated_at && (
                    <Badge variant="outline" className="text-[10px]">report {data.generated_at}</Badge>
                  )}
                </div>
              </div>
            </CardHeader>
            <CardContent className="text-xs text-muted-foreground">{data.note}</CardContent>
          </Card>

          {data.group_order.map((gkey) => {
            const group = data.groups[gkey];
            if (!group || group.modules.length === 0) return null;
            const Icon = GROUP_ICON[gkey] ?? ShieldAlert;
            return (
              <section key={gkey} className="space-y-3">
                <div className="flex items-center gap-2">
                  <Icon className="h-4 w-4 text-primary" />
                  <h2 className="text-lg font-semibold tracking-tight">{group.label}</h2>
                  <Badge variant="outline" className="text-[10px]">{group.passing}/{group.module_count}</Badge>
                </div>
                <p className="text-sm text-muted-foreground">{group.purpose}</p>
                <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
                  {group.modules.map((mod) => <ModuleCard key={mod.key} mod={mod} />)}
                </div>
              </section>
            );
          })}
        </>
      )}
    </div>
  );
}
