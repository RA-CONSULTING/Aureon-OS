import { useEffect, useMemo, useState } from "react";
import { Activity, Archive, CheckCircle2, Lock, ShieldAlert } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  AUREON_EVOLUTION_RUNTIME_PATCH_SUMMARY,
  AUREON_EVOLUTION_RUNTIME_PATCHES,
  aureonEvolutionActivePatchCount,
} from "@/components/generated/aureonEvolutionRuntimePatches";

type JsonMap = Record<string, any>;

async function fetchJson(url: string): Promise<JsonMap> {
  try {
    const response = await fetch(url, { cache: "no-store" });
    if (!response.ok) return {};
    return await response.json();
  } catch {
    return {};
  }
}

function compact(value: unknown): string {
  const number = Number(value || 0);
  return Number.isFinite(number) ? number.toLocaleString() : String(value || "0");
}

function tone(status: string): string {
  if (status.includes("blocker")) return "border-warning/40 bg-warning/10 text-warning";
  if (status.includes("archive")) return "border-slate-500/40 bg-slate-500/10 text-slate-100";
  if (status.includes("adapter") || status.includes("link")) return "border-success/40 bg-success/10 text-success";
  return "border-border bg-muted/20 text-muted-foreground";
}

function iconFor(status: string) {
  if (status.includes("blocker")) return ShieldAlert;
  if (status.includes("archive")) return Archive;
  if (status.includes("adapter") || status.includes("link")) return CheckCircle2;
  return Activity;
}

export function AureonWorkOrderExecutionConsole() {
  const [report, setReport] = useState<JsonMap>({});
  const [registry, setRegistry] = useState<JsonMap>({});

  useEffect(() => {
    let cancelled = false;
    const refresh = () => {
      fetchJson("/aureon_frontend_work_order_execution.json").then((payload) => {
        if (!cancelled) setReport(payload);
      });
      fetchJson("/aureon_frontend_runtime_patch_registry.json").then((payload) => {
        if (!cancelled) setRegistry(payload);
      });
    };
    refresh();
    const timer = window.setInterval(refresh, 2500);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, []);

  const executions = Array.isArray(report.executions) ? report.executions : [];
  const summary = report.summary || {};
  const movement = report.queue_movement || {};
  const validation = report.validation_summary || {};
  const patchSummary = registry.summary || report.runtime_patch_registry?.summary || {};
  const activePatches = Array.isArray(registry.patches) ? registry.patches : report.runtime_patch_registry?.patches || [];
  const materializedPatchCount = AUREON_EVOLUTION_RUNTIME_PATCHES.length;
  const materializedActivePatchCount = aureonEvolutionActivePatchCount();
  const top = useMemo(() => executions.slice(0, 80), [executions]);

  return (
    <Card className="mb-5 bg-card/80">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <Activity className="h-4 w-4 text-primary" />
          Aureon Work Order Execution
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-wrap gap-2">
          <Badge variant="outline" className="border-success/40 bg-success/10 text-success">{report.status || "pending"}</Badge>
          <Badge variant="outline" className="border-border bg-muted/20 text-muted-foreground">updated {report.generated_at ? new Date(report.generated_at).toLocaleTimeString() : "pending"}</Badge>
          <Badge variant="outline" className="border-primary/40 bg-primary/10 text-primary">code materialized {materializedPatchCount}</Badge>
        </div>
        <div className="grid gap-2 md:grid-cols-5">
          <Stat label="orders executed" value={summary.executed_count} />
          <Stat label="moved from queue" value={summary.moved_from_queue_count || movement.moved_from_queue_count} />
          <Stat label="remaining queue" value={summary.remaining_queue_count ?? movement.remaining_queue_count} />
          <Stat label="validated" value={summary.validated_count || validation.validated_count} />
          <Stat label="runtime patches active" value={summary.runtime_patch_count || patchSummary.active_patch_count} />
        </div>
        <div className="grid gap-2 md:grid-cols-5">
          <Stat label="adapters" value={summary.adapter_record_count} />
          <Stat label="blocker cards" value={summary.blocker_card_count} />
          <Stat label="archive decisions" value={summary.archive_decision_count} />
          <Stat label="validation failures" value={summary.failed_validation_count || validation.failed_validation_count || 0} />
          <Stat label="queue drained" value={movement.queue_drained ? "yes" : "no"} />
        </div>
        <div className="rounded-md border border-primary/25 bg-primary/10 p-3">
          <div className="mb-2 text-sm font-medium text-primary">Materialized Repo Code</div>
          <div className="grid gap-2 md:grid-cols-4">
            <Stat label="generated TS patches" value={materializedPatchCount} />
            <Stat label="active in code" value={materializedActivePatchCount} />
            <Stat label="module status" value={AUREON_EVOLUTION_RUNTIME_PATCH_SUMMARY.status} />
            <Stat label="source queue" value={AUREON_EVOLUTION_RUNTIME_PATCH_SUMMARY.sourceQueueCount} />
          </div>
          <div className="mt-2 font-mono text-[11px] text-primary/75">
            frontend/src/components/generated/aureonEvolutionRuntimePatches.ts is imported by this runtime console.
          </div>
        </div>
        <div className="rounded-md border border-success/25 bg-success/10 p-3">
          <div className="mb-2 text-sm font-medium text-success">Runtime Patch Activation</div>
          <div className="grid gap-2 md:grid-cols-3">
            {activePatches.slice(0, 6).map((patch: JsonMap) => (
              <div key={patch.patch_id} className="rounded border border-success/20 bg-background/20 px-2 py-1 text-[11px] text-success/80">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-medium">{String(patch.patch_type || "patch").replace(/_/g, " ")}</span>
                  <Badge variant="outline" className="border-success/40 bg-success/10 text-success">{patch.status}</Badge>
                </div>
                <div className="mt-1 truncate font-mono text-success/70">{patch.source_path}</div>
              </div>
            ))}
            {!activePatches.length ? <div className="text-xs text-success/70">No runtime patch registry loaded yet.</div> : null}
          </div>
        </div>
        <ScrollArea className="h-[420px] pr-3">
          <div className="space-y-2">
            {top.length ? top.map((item: JsonMap) => {
              const Icon = iconFor(String(item.execution_status || ""));
              return (
                <div key={item.id} className="rounded-md border border-border/40 bg-muted/10 p-3">
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 text-sm font-medium">
                        <Icon className="h-4 w-4 text-primary" />
                        {item.title}
                      </div>
                      <div className="mt-1 truncate font-mono text-[11px] text-muted-foreground">{item.source_path}</div>
                    </div>
                    <div className="flex flex-wrap gap-1">
                      <Badge variant="outline" className={tone(String(item.execution_status || ""))}>{item.execution_status}</Badge>
                      <Badge variant="outline" className={item.queue_state === "completed_validated" ? "border-success/40 bg-success/10 text-success" : "border-warning/40 bg-warning/10 text-warning"}>{item.queue_state}</Badge>
                      <Badge variant="outline" className="border-border bg-muted/20 text-muted-foreground">{item.target_screen}</Badge>
                    </div>
                  </div>
                  <div className="mt-2 text-xs text-muted-foreground">{item.next_action}</div>
                  <div className="mt-2 text-[11px] text-success">
                    moved from queue: {item.queue_transition?.moved_from_queue ? "yes" : "no"} | validation: {item.validation?.status || "waiting"} | patch: {item.runtime_patch?.status || "waiting"}
                  </div>
                  <div className="mt-2 text-[11px] text-warning">{item.safety_boundary}</div>
                </div>
              );
            }) : (
              <div className="rounded-md border border-border/40 bg-muted/10 p-4 text-sm text-muted-foreground">No work-order execution manifest loaded.</div>
            )}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}

function Stat({ label, value }: { label: string; value: unknown }) {
  return (
    <div className="rounded-md border border-border/40 bg-muted/10 p-3">
      <div className="text-[11px] uppercase text-muted-foreground">{label}</div>
      <div className="mt-1 text-lg font-semibold">{compact(value)}</div>
    </div>
  );
}
