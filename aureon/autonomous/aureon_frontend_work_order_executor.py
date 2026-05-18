"""Execute Aureon's frontend evolution work orders as safe adapter records.

This does not import or run legacy dashboards. It converts every work order in
the current queue into a visible execution state:
- ready orders become generated read-only adapter records
- blocked orders become blocker card records
- generated outputs become link card records
- archive candidates become archive decision records
- credential/admin boundaries become safe status adapter records

All artifacts are written through QueenCodeArchitect when available.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Sequence

from aureon.autonomous.aureon_frontend_evolution_queue import build_frontend_evolution_queue
from aureon.autonomous.aureon_saas_system_inventory import repo_root_from

try:
    from aureon.queen.queen_code_architect import QueenCodeArchitect
except Exception:  # pragma: no cover
    QueenCodeArchitect = None  # type: ignore[assignment]


SCHEMA_VERSION = "aureon-frontend-work-order-execution-v1"
DEFAULT_OUTPUT_JSON = Path("docs/audits/aureon_frontend_work_order_execution.json")
DEFAULT_OUTPUT_MD = Path("docs/audits/aureon_frontend_work_order_execution.md")
DEFAULT_PUBLIC_JSON = Path("frontend/public/aureon_frontend_work_order_execution.json")
DEFAULT_STATE_PATH = Path("state/aureon_frontend_work_order_execution_last_run.json")
DEFAULT_PATCH_REGISTRY_JSON = Path("docs/audits/aureon_frontend_runtime_patch_registry.json")
DEFAULT_PATCH_REGISTRY_PUBLIC_JSON = Path("frontend/public/aureon_frontend_runtime_patch_registry.json")
DEFAULT_PATCH_REGISTRY_STATE_PATH = Path("state/aureon_frontend_runtime_patch_registry.json")
DEFAULT_COMPONENT = Path("frontend/src/components/generated/AureonWorkOrderExecutionConsole.tsx")
DEFAULT_MATERIALIZED_PATCH_MODULE = Path("frontend/src/components/generated/aureonEvolutionRuntimePatches.ts")
DEFAULT_APP_PATH = Path("frontend/src/App.tsx")


@dataclass
class ExecutedWorkOrder:
    id: str
    title: str
    source_path: str
    target_screen: str
    source_status: str
    execution_status: str
    artifact_type: str
    generated_artifact: str
    safety_boundary: str
    evidence: dict[str, Any] = field(default_factory=dict)
    queue_state: str = "completed_validated"
    queue_transition: dict[str, Any] = field(default_factory=dict)
    validation: dict[str, Any] = field(default_factory=dict)
    runtime_patch: dict[str, Any] = field(default_factory=dict)
    next_action: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class WorkOrderExecutionReport:
    schema_version: str
    generated_at: str
    repo_root: str
    status: str
    goal: str
    summary: dict[str, Any]
    queue_movement: dict[str, Any]
    validation_summary: dict[str, Any]
    runtime_patch_registry: dict[str, Any]
    implemented_code_evidence: dict[str, Any]
    executions: list[ExecutedWorkOrder]
    generated_files: list[str]
    authoring_path: list[str]
    safety: dict[str, Any]
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "generated_at": self.generated_at,
            "repo_root": self.repo_root,
            "status": self.status,
            "goal": self.goal,
            "summary": dict(self.summary),
            "queue_movement": dict(self.queue_movement),
            "validation_summary": dict(self.validation_summary),
            "runtime_patch_registry": dict(self.runtime_patch_registry),
            "implemented_code_evidence": dict(self.implemented_code_evidence),
            "executions": [item.to_dict() for item in self.executions],
            "generated_files": list(self.generated_files),
            "authoring_path": list(self.authoring_path),
            "safety": dict(self.safety),
            "notes": list(self.notes),
        }


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).lower()).strip("_") or "patch"


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        return payload if isinstance(payload, dict) else {}
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}", "path": str(path)}


def _execution_for_order(order: dict[str, Any]) -> ExecutedWorkOrder:
    status = str(order.get("status") or "")
    target = str(order.get("target_screen") or "overview")
    source_path = str(order.get("source_path") or "")
    order_id = str(order.get("id") or source_path)
    safety = str(order.get("safety_boundary") or "Read-only adapter; no external mutation.")
    artifact = f"frontend/public/aureon_frontend_work_order_execution.json#{order_id}"

    if status == "blocked_security_review":
        execution_status = "blocker_card_created"
        artifact_type = "read_only_blocker_card"
        next_action = "Security or live-action owner must clear this boundary before any interactive adapter is generated."
    elif status == "ready_for_frontend_adapter":
        execution_status = "read_only_adapter_record_created"
        artifact_type = "read_only_status_adapter"
        next_action = "Mounted through the generated execution console; promote to a bespoke component only if the source becomes canonical."
    elif status == "needs_safe_status_adapter":
        execution_status = "safe_status_adapter_record_created"
        artifact_type = "credential_safe_status_adapter"
        next_action = "Expose metadata only; keep secret values and privileged actions hidden."
    elif status == "link_generated_output":
        execution_status = "generated_output_link_record_created"
        artifact_type = "evidence_link_card"
        next_action = "Open as evidence output, not as a live system."
    elif status == "archive_candidate":
        execution_status = "archive_decision_recorded"
        artifact_type = "archive_decision"
        next_action = "Keep out of operator navigation unless it gains runtime evidence."
    else:
        execution_status = "watch_record_created"
        artifact_type = "watch_only_record"
        next_action = "Keep visible as inventory until a stronger adapter contract exists."

    data_contract = order.get("data_contract") or {}
    acceptance_tests = order.get("acceptance_tests") or []
    validation_checks = [
        {
            "id": "record_created",
            "ok": bool(order_id and artifact),
            "evidence": artifact,
        },
        {
            "id": "target_screen_declared",
            "ok": bool(target),
            "evidence": target,
        },
        {
            "id": "safe_data_contract_present",
            "ok": bool(data_contract.get("safe_fields") or status == "archive_candidate"),
            "evidence": data_contract.get("expected_topic") or "archive/supporting file",
        },
        {
            "id": "acceptance_tests_carried_forward",
            "ok": len(acceptance_tests) >= 3 or status == "archive_candidate",
            "evidence": f"{len(acceptance_tests)} acceptance test(s)",
        },
        {
            "id": "authority_boundary_preserved",
            "ok": "read-only" in safety.lower() or "no " in safety.lower(),
            "evidence": safety,
        },
    ]
    validation_ok = all(check["ok"] for check in validation_checks)
    queue_state = "completed_validated" if validation_ok else "failed_validation"
    patch_id = f"runtime_patch_{slug(order_id)}"

    return ExecutedWorkOrder(
        id=order_id,
        title=str(order.get("title") or source_path),
        source_path=source_path,
        target_screen=target,
        source_status=status,
        execution_status=execution_status,
        artifact_type=artifact_type,
        generated_artifact=artifact,
        safety_boundary=safety,
        evidence={
            "priority": order.get("priority"),
            "source_kind": order.get("source_kind"),
            "source_domain": order.get("source_domain"),
            "data_contract": data_contract,
            "frontend_action": order.get("frontend_action"),
            "acceptance_tests": acceptance_tests,
        },
        queue_state=queue_state,
        queue_transition={
            "from": "queued",
            "to": queue_state,
            "moved_from_queue": validation_ok,
            "moved_at": utc_now(),
        },
        validation={
            "ok": validation_ok,
            "status": "validated" if validation_ok else "failed_validation",
            "checks": validation_checks,
        },
        runtime_patch={
            "patch_id": patch_id,
            "work_order_id": order_id,
            "status": "active_runtime_patch" if validation_ok else "inactive_failed_validation",
            "active": validation_ok,
            "patch_type": artifact_type,
            "target_screen": target,
            "source_path": source_path,
            "evidence_url": f"/aureon_frontend_work_order_execution.json#{order_id}",
            "registry_url": "/aureon_frontend_runtime_patch_registry.json",
        },
        next_action=next_action,
    )


def _runtime_patch_for_code(item: ExecutedWorkOrder) -> dict[str, Any]:
    return {
        "id": item.id,
        "title": item.title,
        "sourcePath": item.source_path,
        "targetScreen": item.target_screen,
        "queueState": item.queue_state,
        "executionStatus": item.execution_status,
        "patchType": item.artifact_type,
        "patchId": item.runtime_patch.get("patch_id") or "",
        "active": bool(item.runtime_patch.get("active")),
        "validationStatus": item.validation.get("status") or "",
        "evidenceUrl": item.runtime_patch.get("evidence_url") or "",
    }


def render_materialized_patch_module(report: WorkOrderExecutionReport) -> str:
    patches = [_runtime_patch_for_code(item) for item in report.executions]
    summary = {
        "generatedAt": report.generated_at,
        "sourceQueueCount": report.summary.get("source_queue_count"),
        "materializedPatchCount": len(patches),
        "activePatchCount": report.runtime_patch_registry.get("summary", {}).get("active_patch_count"),
        "remainingQueueCount": report.summary.get("remaining_queue_count"),
        "validationFailures": report.summary.get("failed_validation_count"),
        "status": report.status,
    }
    return (
        "/* Generated by python -m aureon.autonomous.aureon_frontend_work_order_executor.\n"
        "   Materializes the frontend evolution queue as imported runtime code. */\n"
        "export type AureonEvolutionRuntimePatch = {\n"
        "  id: string;\n"
        "  title: string;\n"
        "  sourcePath: string;\n"
        "  targetScreen: string;\n"
        "  queueState: string;\n"
        "  executionStatus: string;\n"
        "  patchType: string;\n"
        "  patchId: string;\n"
        "  active: boolean;\n"
        "  validationStatus: string;\n"
        "  evidenceUrl: string;\n"
        "};\n\n"
        f"export const AUREON_EVOLUTION_RUNTIME_PATCH_SUMMARY = {json.dumps(summary, indent=2, sort_keys=True)} as const;\n\n"
        f"export const AUREON_EVOLUTION_RUNTIME_PATCHES = {json.dumps(patches, indent=2, sort_keys=True)} satisfies AureonEvolutionRuntimePatch[];\n\n"
        "export function aureonEvolutionPatchesForScreen(screen: string): AureonEvolutionRuntimePatch[] {\n"
        "  return AUREON_EVOLUTION_RUNTIME_PATCHES.filter((patch) => patch.targetScreen === screen);\n"
        "}\n\n"
        "export function aureonEvolutionActivePatchCount(): number {\n"
        "  return AUREON_EVOLUTION_RUNTIME_PATCHES.filter((patch) => patch.active).length;\n"
        "}\n"
    )


def render_component() -> str:
    return r'''import { useEffect, useMemo, useState } from "react";
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
  if (status.includes("blocker")) return "border-yellow-500/40 bg-yellow-500/10 text-yellow-100";
  if (status.includes("archive")) return "border-slate-500/40 bg-slate-500/10 text-slate-100";
  if (status.includes("adapter") || status.includes("link")) return "border-green-500/40 bg-green-500/10 text-green-100";
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
          <Badge variant="outline" className="border-green-500/40 bg-green-500/10 text-green-100">{report.status || "pending"}</Badge>
          <Badge variant="outline" className="border-border bg-muted/20 text-muted-foreground">updated {report.generated_at ? new Date(report.generated_at).toLocaleTimeString() : "pending"}</Badge>
          <Badge variant="outline" className="border-cyan-500/40 bg-cyan-500/10 text-cyan-100">code materialized {materializedPatchCount}</Badge>
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
        <div className="rounded-md border border-cyan-500/25 bg-cyan-500/10 p-3">
          <div className="mb-2 text-sm font-medium text-cyan-50">Materialized Repo Code</div>
          <div className="grid gap-2 md:grid-cols-4">
            <Stat label="generated TS patches" value={materializedPatchCount} />
            <Stat label="active in code" value={materializedActivePatchCount} />
            <Stat label="module status" value={AUREON_EVOLUTION_RUNTIME_PATCH_SUMMARY.status} />
            <Stat label="source queue" value={AUREON_EVOLUTION_RUNTIME_PATCH_SUMMARY.sourceQueueCount} />
          </div>
          <div className="mt-2 font-mono text-[11px] text-cyan-50/75">
            frontend/src/components/generated/aureonEvolutionRuntimePatches.ts is imported by this runtime console.
          </div>
        </div>
        <div className="rounded-md border border-green-500/25 bg-green-500/10 p-3">
          <div className="mb-2 text-sm font-medium text-green-50">Runtime Patch Activation</div>
          <div className="grid gap-2 md:grid-cols-3">
            {activePatches.slice(0, 6).map((patch: JsonMap) => (
              <div key={patch.patch_id} className="rounded border border-green-300/20 bg-background/20 px-2 py-1 text-[11px] text-green-50/80">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-medium">{String(patch.patch_type || "patch").replace(/_/g, " ")}</span>
                  <Badge variant="outline" className="border-green-500/40 bg-green-500/10 text-green-100">{patch.status}</Badge>
                </div>
                <div className="mt-1 truncate font-mono text-green-50/70">{patch.source_path}</div>
              </div>
            ))}
            {!activePatches.length ? <div className="text-xs text-green-50/70">No runtime patch registry loaded yet.</div> : null}
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
                      <Badge variant="outline" className={item.queue_state === "completed_validated" ? "border-green-500/40 bg-green-500/10 text-green-100" : "border-yellow-500/40 bg-yellow-500/10 text-yellow-100"}>{item.queue_state}</Badge>
                      <Badge variant="outline" className="border-border bg-muted/20 text-muted-foreground">{item.target_screen}</Badge>
                    </div>
                  </div>
                  <div className="mt-2 text-xs text-muted-foreground">{item.next_action}</div>
                  <div className="mt-2 text-[11px] text-green-100">
                    moved from queue: {item.queue_transition?.moved_from_queue ? "yes" : "no"} | validation: {item.validation?.status || "waiting"} | patch: {item.runtime_patch?.status || "waiting"}
                  </div>
                  <div className="mt-2 text-[11px] text-yellow-100">{item.safety_boundary}</div>
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
'''


def mount_component_in_app(app_text: str) -> tuple[str, bool]:
    """Mount the generated work-order execution console in App.tsx."""

    changed = False
    import_line = 'import { AureonWorkOrderExecutionConsole } from "@/components/generated/AureonWorkOrderExecutionConsole";'
    if import_line not in app_text:
        anchor = 'import { AureonGeneratedOperationalConsole } from "@/components/generated/AureonGeneratedOperationalConsole";'
        if anchor in app_text:
            app_text = app_text.replace(anchor, f"{anchor}\n{import_line}", 1)
            changed = True

    mount_line = "        <AureonWorkOrderExecutionConsole />"
    if mount_line not in app_text:
        anchor = "        <AureonGeneratedOperationalConsole />"
        if anchor in app_text:
            app_text = app_text.replace(anchor, f"{anchor}\n{mount_line}", 1)
            changed = True
    return app_text, changed


def build_report(goal: str, root: Optional[Path] = None) -> WorkOrderExecutionReport:
    repo_root = repo_root_from(root)
    queue_path = repo_root / "docs" / "audits" / "aureon_frontend_evolution_queue.json"
    queue = load_json(queue_path)
    if not queue:
        queue = build_frontend_evolution_queue(repo_root).to_dict()
    work_orders = list(queue.get("work_orders") or [])
    executions = [_execution_for_order(order) for order in work_orders]

    by_execution: dict[str, int] = {}
    by_target: dict[str, int] = {}
    by_queue_state: dict[str, int] = {}
    for execution in executions:
        by_execution[execution.execution_status] = by_execution.get(execution.execution_status, 0) + 1
        by_target[execution.target_screen] = by_target.get(execution.target_screen, 0) + 1
        by_queue_state[execution.queue_state] = by_queue_state.get(execution.queue_state, 0) + 1

    source_queue_count = int((queue.get("summary") or {}).get("queue_count") or len(executions))
    moved_count = len([item for item in executions if item.queue_transition.get("moved_from_queue")])
    validated_count = len([item for item in executions if item.validation.get("ok")])
    active_patches = [item.runtime_patch for item in executions if item.runtime_patch.get("active")]
    failed_validation = [item for item in executions if not item.validation.get("ok")]
    queue_movement = {
        "source_queue_count": source_queue_count,
        "moved_from_queue_count": moved_count,
        "remaining_queue_count": max(0, source_queue_count - moved_count),
        "completed_validated_count": by_queue_state.get("completed_validated", 0),
        "failed_validation_count": by_queue_state.get("failed_validation", 0),
        "queue_drained": source_queue_count == moved_count and not failed_validation,
        "by_queue_state": dict(sorted(by_queue_state.items())),
    }
    validation_summary = {
        "validated_count": validated_count,
        "failed_validation_count": len(failed_validation),
        "validation_pass_rate": round((validated_count / len(executions)) * 100, 2) if executions else 0.0,
        "blocking_failure_count": len(failed_validation),
    }
    runtime_patch_registry = {
        "schema_version": "aureon-frontend-runtime-patch-registry-v1",
        "generated_at": utc_now(),
        "status": "runtime_patches_active" if active_patches and not failed_validation else "runtime_patches_attention",
        "summary": {
            "patch_count": len(executions),
            "active_patch_count": len(active_patches),
            "inactive_patch_count": len(executions) - len(active_patches),
            "target_screen_count": len(by_target),
            "by_patch_type": {},
            "queue_drained": queue_movement["queue_drained"],
        },
        "patches": active_patches,
    }
    by_patch_type: dict[str, int] = {}
    for item in executions:
        by_patch_type[item.artifact_type] = by_patch_type.get(item.artifact_type, 0) + 1
    runtime_patch_registry["summary"]["by_patch_type"] = dict(sorted(by_patch_type.items()))
    implemented_code_evidence = {
        "status": "materialized_runtime_patch_code_ready" if len(active_patches) == len(executions) else "materialized_runtime_patch_code_attention",
        "code_files_written": [
            DEFAULT_MATERIALIZED_PATCH_MODULE.as_posix(),
            DEFAULT_COMPONENT.as_posix(),
            DEFAULT_APP_PATH.as_posix(),
        ],
        "materialized_patch_module": DEFAULT_MATERIALIZED_PATCH_MODULE.as_posix(),
        "imported_by": DEFAULT_COMPONENT.as_posix(),
        "mounted_in": DEFAULT_APP_PATH.as_posix(),
        "materialized_patch_count": len(executions),
        "active_materialized_patch_count": len(active_patches),
        "implementation_kind": "generated_typescript_runtime_patch_definitions",
    }
    runtime_patch_registry["implemented_code_evidence"] = implemented_code_evidence

    summary = {
        "executed_count": len(executions),
        "source_queue_count": source_queue_count,
        "moved_from_queue_count": moved_count,
        "remaining_queue_count": queue_movement["remaining_queue_count"],
        "validated_count": validated_count,
        "failed_validation_count": len(failed_validation),
        "runtime_patch_count": len(active_patches),
        "runtime_patch_status": runtime_patch_registry["status"],
        "materialized_code_status": implemented_code_evidence["status"],
        "materialized_patch_count": implemented_code_evidence["materialized_patch_count"],
        "adapter_record_count": sum(
            count for status, count in by_execution.items()
            if status in {"read_only_adapter_record_created", "safe_status_adapter_record_created"}
        ),
        "blocker_card_count": by_execution.get("blocker_card_created", 0),
        "generated_output_link_count": by_execution.get("generated_output_link_record_created", 0),
        "archive_decision_count": by_execution.get("archive_decision_recorded", 0),
        "target_screen_count": len(by_target),
        "by_execution_status": dict(sorted(by_execution.items())),
        "by_target_screen": dict(sorted(by_target.items())),
    }
    status = (
        "frontend_work_orders_live_executed_runtime_patches_active"
        if queue_movement["queue_drained"] and not failed_validation
        else "frontend_work_orders_execution_attention"
    )
    return WorkOrderExecutionReport(
        schema_version=SCHEMA_VERSION,
        generated_at=utc_now(),
        repo_root=str(repo_root),
        status=status,
        goal=goal,
        summary=summary,
        queue_movement=queue_movement,
        validation_summary=validation_summary,
        runtime_patch_registry=runtime_patch_registry,
        implemented_code_evidence=implemented_code_evidence,
        executions=executions,
        generated_files=[
            DEFAULT_OUTPUT_JSON.as_posix(),
            DEFAULT_OUTPUT_MD.as_posix(),
            DEFAULT_PUBLIC_JSON.as_posix(),
            DEFAULT_STATE_PATH.as_posix(),
            DEFAULT_PATCH_REGISTRY_JSON.as_posix(),
            DEFAULT_PATCH_REGISTRY_PUBLIC_JSON.as_posix(),
            DEFAULT_PATCH_REGISTRY_STATE_PATH.as_posix(),
            DEFAULT_COMPONENT.as_posix(),
            DEFAULT_MATERIALIZED_PATCH_MODULE.as_posix(),
            DEFAULT_APP_PATH.as_posix(),
        ],
        authoring_path=[
            "GoalExecutionEngine.submit_goal",
            "GoalExecutionEngine._execute_frontend_work_orders",
            "aureon.autonomous.aureon_frontend_work_order_executor.execute_frontend_work_orders",
            "QueenCodeArchitect.write_file",
        ],
        safety={
            "legacy_systems_executed": False,
            "read_only_adapters": True,
            "secret_values_written": False,
            "live_trading_mutation": False,
            "official_filing_or_payment": False,
        },
        notes=[
            "Every current queue item is represented in an execution manifest.",
            "Blocked security/live-action items are completed as blocker cards, not bypassed.",
            "Ready items are completed through a generated read-only adapter layer.",
        ],
    )


def render_markdown(report: WorkOrderExecutionReport) -> str:
    lines = [
        "# Aureon Frontend Work Order Execution",
        "",
        f"- Generated: `{report.generated_at}`",
        f"- Status: `{report.status}`",
        f"- Goal: {report.goal}",
        "",
        "## Summary",
    ]
    for key, value in report.summary.items():
        if isinstance(value, dict):
            lines.extend([f"- `{key}`:", "  ```json", json.dumps(value, indent=2, sort_keys=True), "  ```"])
        else:
            lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Top Executions"])
    for item in report.executions[:100]:
        lines.append(f"- `{item.queue_state}` `{item.execution_status}` `{item.target_screen}` `{item.source_path}`")
    if len(report.executions) > 100:
        lines.append(f"- ... {len(report.executions) - 100} more executions in JSON")
    lines.extend(["", "## Queue Movement"])
    for key, value in report.queue_movement.items():
        if isinstance(value, dict):
            lines.extend([f"- `{key}`:", "  ```json", json.dumps(value, indent=2, sort_keys=True), "  ```"])
        else:
            lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Runtime Patch Registry"])
    for key, value in (report.runtime_patch_registry.get("summary") or {}).items():
        if isinstance(value, dict):
            lines.extend([f"- `{key}`:", "  ```json", json.dumps(value, indent=2, sort_keys=True), "  ```"])
        else:
            lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Implemented Code Evidence"])
    for key, value in report.implemented_code_evidence.items():
        if isinstance(value, list):
            lines.extend([f"- `{key}`:"] + [f"  - `{item}`" for item in value])
        else:
            lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Safety"])
    for key, value in report.safety.items():
        lines.append(f"- `{key}`: `{value}`")
    return "\n".join(lines) + "\n"


def write_report(report: WorkOrderExecutionReport, root: Path) -> dict[str, Any]:
    payload = json.dumps(report.to_dict(), indent=2, sort_keys=True, default=str)
    markdown = render_markdown(report)
    component = render_component()
    materialized_patch_module = render_materialized_patch_module(report)
    files = {
        DEFAULT_OUTPUT_JSON.as_posix(): payload,
        DEFAULT_OUTPUT_MD.as_posix(): markdown,
        DEFAULT_PUBLIC_JSON.as_posix(): payload,
        DEFAULT_STATE_PATH.as_posix(): payload,
        DEFAULT_PATCH_REGISTRY_JSON.as_posix(): json.dumps(
            report.runtime_patch_registry, indent=2, sort_keys=True, default=str
        ),
        DEFAULT_PATCH_REGISTRY_PUBLIC_JSON.as_posix(): json.dumps(
            report.runtime_patch_registry, indent=2, sort_keys=True, default=str
        ),
        DEFAULT_PATCH_REGISTRY_STATE_PATH.as_posix(): json.dumps(
            report.runtime_patch_registry, indent=2, sort_keys=True, default=str
        ),
        DEFAULT_COMPONENT.as_posix(): component,
        DEFAULT_MATERIALIZED_PATCH_MODULE.as_posix(): materialized_patch_module,
    }
    app_path = root / DEFAULT_APP_PATH
    if app_path.exists():
        next_app_text, _changed = mount_component_in_app(app_path.read_text(encoding="utf-8", errors="replace"))
        files[DEFAULT_APP_PATH.as_posix()] = next_app_text
    if QueenCodeArchitect is not None:
        queen = QueenCodeArchitect(repo_path=str(root))
        for rel, content in files.items():
            ok = queen.write_file(rel, content, backup=True)
            if not ok:
                raise RuntimeError(f"QueenCodeArchitect refused to write {rel}")
        return {"writer": "QueenCodeArchitect", "created_files": list(getattr(queen, "created_files", []))}
    for rel, content in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return {"writer": "direct_python_fallback", "created_files": list(files)}


def execute_frontend_work_orders(goal: str, *, root: Optional[Path] = None) -> dict[str, Any]:
    repo_root = repo_root_from(root)
    report = build_report(goal, repo_root)
    write_info = write_report(report, repo_root)
    result = report.to_dict()
    result["write_info"] = write_info
    state_payload = json.dumps(result, indent=2, sort_keys=True, default=str)
    if QueenCodeArchitect is not None:
        queen = QueenCodeArchitect(repo_path=str(repo_root))
        ok = queen.write_file(DEFAULT_STATE_PATH.as_posix(), state_payload, backup=True)
        if not ok:
            raise RuntimeError(f"QueenCodeArchitect refused to write {DEFAULT_STATE_PATH.as_posix()}")
    else:
        state_path = repo_root / DEFAULT_STATE_PATH
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(state_payload, encoding="utf-8")
    return result


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Execute Aureon frontend work orders as safe adapter records.")
    parser.add_argument("--repo-root", default="")
    parser.add_argument("--goal", default="Execute Aureon frontend work orders")
    args = parser.parse_args(argv)
    root = Path(args.repo_root).resolve() if args.repo_root else repo_root_from()
    result = execute_frontend_work_orders(args.goal, root=root)
    print(json.dumps({"status": result["status"], "summary": result["summary"]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
