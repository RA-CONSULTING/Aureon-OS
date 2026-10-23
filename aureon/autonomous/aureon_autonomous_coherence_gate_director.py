"""Aureon Autonomous Coherence Gate Director.

This director turns the proposal-only self-fix path into a real local
autonomous patch-apply path with a caterpillar-to-cocoon-to-butterfly cycle.

Authority is bounded strictly inside the repository and local test layer:
- live trading, payments, filings, secrets, and destructive actions stay blocked
  by the shared safety scans imported from the proposal-only director;
- every patch is backed up, checked with ``git apply --check``, applied, tested,
  and rolled back on failure;
- a durable receipt records full telemetry, test outputs, file hashes, and the
  next action.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

from aureon.autonomous.self_repair_guard import append_review, block_reason_for_patch
from aureon.autonomous.aureon_autonomous_self_fix_director import (
    BLOCKED_PATH_NEEDLES,
    DEFAULT_PATCH_ALLOWLIST,
    MANUAL_AUTHORITY_NEEDLES,  # noqa: F401
    SECRET_CONTENT_PATTERNS,  # noqa: F401
    ProposalPreflight,  # noqa: F401
    _contains_manual_authority,
    _extract_patch_target_files,
    _normalize_rel_path,
    _path_blocked,
    _scan_patch_for_secrets,
)
from aureon.autonomous.aureon_capability_forge import REPO_ROOT
from aureon.autonomous.aureon_internal_self_coder import (
    DEFAULT_EVIDENCE_PATH as SELF_CODER_EVIDENCE_PATH,
    DEFAULT_PROPOSAL_PATH as SELF_CODER_PROPOSAL_PATH,
)
from aureon.autonomous.aureon_safe_code_control import (
    CodeProposal,
    SafeCodeControl,
)
from aureon.autonomous.aureon_unified_self_evolution_loop import read_evolution_field_inputs
from aureon.core.hnc_field import read_canonical_field
from aureon.operator.coherence_gate import (
    GAMMA_FULL,  # noqa: F401
    GAMMA_REDUCED,  # noqa: F401
    compute_evolution_flow,
)

SCHEMA_VERSION = "aureon-autonomous-coherence-gate-director-v1"

DEFAULT_STATE_PATH = Path("state/aureon_autonomous_coherence_gate_director_last_run.json")
DEFAULT_AUDIT_JSON = Path("docs/audits/aureon_autonomous_coherence_gate_director.json")
DEFAULT_AUDIT_MD = Path("docs/audits/aureon_autonomous_coherence_gate_director.md")
DEFAULT_PUBLIC_JSON = Path("frontend/public/aureon_autonomous_coherence_gate_director.json")
DEFAULT_LOCK_PATH = Path("state/aureon_autonomous_coherence_gate_director.lock")
DEFAULT_BACKUP_DIR = Path("state/coherence_gate_backups")

TERMINAL_STATE_URL = "http://127.0.0.1:5173/api/terminal-state"
PULSE_URL = "http://127.0.0.1:8080/api/pulse"

COHERENCE_GATE_ALLOWLIST = list(
    dict.fromkeys(
        list(DEFAULT_PATCH_ALLOWLIST)
        + [
            "aureon/autonomous/aureon_coding_capability_unblocker.py",
            "aureon/autonomous/aureon_autonomous_self_run_loop.py",
            "aureon/autonomous/aureon_autonomous_job_executor.py",
            "aureon/autonomous/aureon_autonomous_coherence_gate_director.py",
            "aureon/autonomous/aureon_self_run_coding_task.py",
            "aureon/autonomous/aureon_internal_self_coder.py",
            "aureon/autonomous/workers/local_coding_tool_worker.py",
            "tests/test_aureon_autonomous_coherence_gate_director.py",
            "aureon/accounting/__init__.py",
            "cli/__init__.py",
            "aureon/simulation/simple_check.py",
            "aureon/core/no_external_calls.py",
        ]
    )
)


@dataclass
class TelemetrySnapshot:
    """A snapshot of all four telemetry sources used for self-approval."""

    canonical_field: Dict[str, Any] = field(default_factory=dict)
    evolution_inputs: Dict[str, Any] = field(default_factory=dict)
    evolution_flow: Dict[str, Any] = field(default_factory=dict)
    terminal_state: Dict[str, Any] = field(default_factory=dict)
    pulse: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "canonical_field": self.canonical_field,
            "evolution_inputs": self.evolution_inputs,
            "evolution_flow": self.evolution_flow,
            "terminal_state": self.terminal_state,
            "pulse": self.pulse,
            "errors": self.errors,
        }


class CoherenceGateDirector:
    """Local autonomous patch director with bounded cocoon/butterfly cycle."""

    def __init__(
        self,
        root: Path | None = None,
        allowlist: Sequence[str] | None = None,
        state_path: Path = DEFAULT_STATE_PATH,
        audit_json: Path = DEFAULT_AUDIT_JSON,
        audit_md: Path = DEFAULT_AUDIT_MD,
        public_json: Path = DEFAULT_PUBLIC_JSON,
        lock_path: Path = DEFAULT_LOCK_PATH,
        backup_dir: Path = DEFAULT_BACKUP_DIR,
        operator_prompt: str = "",
        dry_run: bool = False,
    ) -> None:
        self.root = Path(root or _default_root()).resolve()
        self.allowlist = list(allowlist) if allowlist is not None else list(COHERENCE_GATE_ALLOWLIST)
        self.state_path = state_path
        self.audit_json = audit_json
        self.audit_md = audit_md
        self.public_json = public_json
        self.lock_path = lock_path
        self.backup_dir = backup_dir
        self.operator_prompt = operator_prompt
        self.dry_run = dry_run
        self._telemetry_before: TelemetrySnapshot | None = None
        self._telemetry_after: TelemetrySnapshot | None = None

    def run_cycle(self) -> Dict[str, Any]:
        """Run one full caterpillar → cocoon → butterfly cycle."""
        lock_info = self._acquire_lock()
        if not lock_info["acquired"]:
            return self._build_report(
                status="blocked",
                ok=False,
                blocked_reason=lock_info.get("reason", "lock_held"),
                next_action="Wait for the existing coherence-gate run to finish or clear the stale lock file.",
            )
        try:
            return self._run_cycle_locked()
        finally:
            self._release_lock()

    def _run_cycle_locked(self) -> Dict[str, Any]:
        # Caterpillar: read live telemetry and find approved proposals.
        telemetry = self._read_telemetry()
        self._telemetry_before = telemetry
        proposals = self._load_approved_proposals()

        if not proposals:
            return self._build_report(
                status="held",
                ok=True,
                blocked_reason="no_approved_proposals",
                next_action="No approved proposals in SafeCodeControl; nothing to apply.",
                proposals=[],
            )

        if self.dry_run:
            validated = [self._validate_for_self_approval(prop, index=i) for i, prop in enumerate(proposals)]
            return self._build_report(
                status="held",
                ok=True,
                blocked_reason="dry_run",
                next_action="Dry-run completed; remove --dry-run to apply validated proposals.",
                proposals=validated,
            )

        # Self-approve at most one proposal per cycle (safest first step).
        for index, proposal in enumerate(proposals):
            approval = self._validate_for_self_approval(proposal, index=index)
            if approval["approved"]:
                return self._cocoon_and_butterfly(proposal, approval, telemetry)

        # No proposal passed self-approval; report the first failure.
        first = self._validate_for_self_approval(proposals[0], index=0)
        return self._build_report(
            status="held",
            ok=False,
            blocked_reason=first.get("blocked_reason", "self_approval_failed"),
            next_action="Review the failing self-approval checks and re-propose when conditions pass.",
            proposals=[first],
        )

    def _read_telemetry(self) -> TelemetrySnapshot:
        snapshot = TelemetrySnapshot()

        try:
            field = read_canonical_field()
            snapshot.canonical_field = field.to_dict()
        except Exception as exc:
            snapshot.errors.append(f"canonical_field_read_failed:{type(exc).__name__}:{exc}")
            snapshot.canonical_field = {"available": False, "error": type(exc).__name__}

        try:
            inputs = read_evolution_field_inputs()
            snapshot.evolution_inputs = inputs
            snapshot.evolution_flow = compute_evolution_flow(
                inputs.get("gamma"),
                inputs.get("advisory_open"),
                inputs.get("lighthouse_severity"),
                auris_confidence=inputs.get("auris_confidence"),
                beta=inputs.get("beta"),
            )
        except Exception as exc:
            snapshot.errors.append(f"evolution_flow_failed:{type(exc).__name__}:{exc}")
            snapshot.evolution_inputs = {"available": False, "error": type(exc).__name__}
            snapshot.evolution_flow = {"flow": "repair", "field_status": "canonical_dark"}

        snapshot.terminal_state = self._http_get_json(TERMINAL_STATE_URL)
        snapshot.pulse = self._http_get_json(PULSE_URL)
        return snapshot

    def _http_get_json(self, url: str) -> Dict[str, Any]:
        try:
            return _requests_get_json(url)
        except Exception as exc:
            return {"ok": False, "error": f"{type(exc).__name__}:{exc}"}

    def _load_approved_proposals(self) -> List[Dict[str, Any]]:
        # Read from the self-coder's proposal state, which is where approved
        # internal patches are written when AUREON_CODE_AUTO_APPROVE=1.
        path = self._rooted(SELF_CODER_PROPOSAL_PATH)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            payload = {}
        proposals: List[Dict[str, Any]] = []
        if isinstance(payload, dict):
            for key in ("pending_proposals", "recent_reviews"):
                for item in payload.get(key, []) if isinstance(payload.get(key), list) else []:
                    if isinstance(item, dict) and str(item.get("status") or "").casefold() == "approved":
                        proposals.append({**item, "_proposal_state_bucket": key})
        return proposals

    def _validate_for_self_approval(self, proposal: Dict[str, Any], *, index: int = 0) -> Dict[str, Any]:
        patch_text = str(proposal.get("patch_text") or "")
        target_files = self._resolve_target_files(proposal, patch_text)
        proposal_id = self._proposal_id(proposal, index)
        checks: List[Dict[str, Any]] = []

        def add_check(check_id: str, ok: bool, detail: str) -> None:
            checks.append({"id": check_id, "ok": ok, "detail": detail})

        # 1. Canonical field live.
        cf = self._telemetry_before.canonical_field if self._telemetry_before else {}
        canonical_ok = bool(
            cf.get("available") is True
            and cf.get("data_status") == "live"
            and cf.get("truth_status") == "real_derived"
            and cf.get("freshness_status") == "fresh"
        )
        add_check(
            "canonical_field_live",
            canonical_ok,
            f"available={cf.get('available')} data_status={cf.get('data_status')} "
            f"truth_status={cf.get('truth_status')} freshness_status={cf.get('freshness_status')}",
        )

        # 2. Evolution flow expand/steady and live.
        flow = (self._telemetry_before.evolution_flow if self._telemetry_before else {}).get("flow")
        field_status = (self._telemetry_before.evolution_flow if self._telemetry_before else {}).get(
            "field_status"
        )
        flow_ok = flow in ("expand", "steady") and field_status == "live"
        add_check(
            "evolution_flow_allows_apply",
            flow_ok,
            f"flow={flow} field_status={field_status}",
        )

        # 3. Terminal state ok and not stale.
        ts = self._telemetry_before.terminal_state if self._telemetry_before else {}
        terminal_ok = bool(ts.get("ok") is True and ts.get("stale") is False)
        add_check(
            "terminal_state_ok",
            terminal_ok,
            f"ok={ts.get('ok')} stale={ts.get('stale')}",
        )

        # 4. Pulse operational core healthy and available.
        pulse = self._telemetry_before.pulse if self._telemetry_before else {}
        op_core = (pulse.get("status") or {}).get("operational_core") or {}
        pulse_ok = bool(op_core.get("status") == "healthy" and op_core.get("available") is True)
        add_check(
            "pulse_operational_core_healthy",
            pulse_ok,
            f"status={op_core.get('status')} available={op_core.get('available')}",
        )

        # 5. Unified diff shape.
        unified_ok = "--- " in patch_text and "+++ " in patch_text and "@@" in patch_text
        add_check(
            "unified_diff_shape",
            unified_ok,
            "requires ---/+++/@@ unified diff markers",
        )

        # 6. Allowlist and path safety.
        allow = {_normalize_rel_path(item) for item in self.allowlist}
        allowlist_ok = bool(target_files) and all(path in allow for path in target_files)
        blocked_paths = [path for path in target_files if _path_blocked(path)]
        add_check(
            "target_files_allowlisted",
            allowlist_ok and not blocked_paths,
            ", ".join(blocked_paths) or "all target files allowlisted",
        )

        # 7. Secret scan clean.
        secret_findings = _scan_patch_for_secrets(patch_text)
        add_check(
            "secret_scan_clean",
            not secret_findings,
            ", ".join(secret_findings) or "no secret-like additions",
        )

        # 8. Operator prompt authority scan.
        authority_ok = not _contains_manual_authority(self.operator_prompt)
        add_check(
            "operator_prompt_authority_clean",
            authority_ok,
            "manual-authority needles: " + ("found" if not authority_ok else "none"),
        )

        # 9. Extra blocked-path needles in target files.
        extra_blocked = [path for path in target_files if _extra_blocked_path(path)]
        add_check(
            "target_paths_authority_blocked",
            not extra_blocked,
            ", ".join(extra_blocked) or "no authority-blocked target paths",
        )

        approved = all(check["ok"] for check in checks)
        blocked_reason = None
        if not approved:
            blocked_reason = next((check["id"] for check in checks if not check["ok"]), "self_approval_failed")

        return {
            "proposal_id": proposal_id,
            "index": index,
            "approved": approved,
            "blocked_reason": blocked_reason,
            "target_files": target_files,
            "checks": checks,
            "proposal": proposal,
        }

    def _resolve_target_files(self, proposal: Dict[str, Any], patch_text: str) -> List[str]:
        targets = [
            _normalize_rel_path(item)
            for item in list(proposal.get("target_files") or []) + _extract_patch_target_files(patch_text)
            if str(item or "").strip()
        ]
        return list(dict.fromkeys(targets))

    def _proposal_id(self, proposal: Dict[str, Any], index: int) -> str:
        base = str(proposal.get("id") or proposal.get("title") or proposal.get("kind") or f"proposal_{index}")
        return re.sub(r"[^a-zA-Z0-9_\-.]", "_", base)[:120]

    def _cocoon_and_butterfly(
        self, proposal: Dict[str, Any], approval: Dict[str, Any], before_telemetry: TelemetrySnapshot
    ) -> Dict[str, Any]:
        proposal_id = approval["proposal_id"]
        target_files = approval["target_files"]
        patch_text = str(proposal.get("patch_text") or "")
        protected = block_reason_for_patch(self.root, patch_text, target_files)
        if protected:
            append_review(
                self.root,
                "human_review_required",
                reason=protected,
                path=",".join(target_files),
                human_review=True,
                auto_approve_ignored=True,
            )
            return self._build_report(
                status="human_review",
                ok=False,
                blocked_reason=protected,
                next_action="Human review required. The patch was not applied.",
                proposal=approval,
                cocoon={"proposal_id": proposal_id, "human_review": True, "protected_reason": protected, "backups": []},
            )
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        backup_root = self.backup_dir / proposal_id / timestamp

        cocoon: Dict[str, Any] = {
            "proposal_id": proposal_id,
            "timestamp": timestamp,
            "backups": [],
            "git_apply_check": {},
            "git_apply": {},
            "test_layers": [],
            "rollback": {},
        }

        # Resolve and validate target paths.
        resolved: List[Tuple[str, Path]] = []
        for rel in target_files:
            try:
                path = _bounded_target_path(self.root, Path(rel))
                resolved.append((rel, path))
            except ValueError:
                return self._build_report(
                    status="blocked",
                    ok=False,
                    blocked_reason=f"target_path_escapes_repository:{rel}",
                    next_action="Reject proposal with escaping or absolute target paths.",
                    proposal=approval,
                    cocoon=cocoon,
                )

        # Backup existing files and remove targets that a new-file patch would
        # recreate, so git apply can create them from /dev/null.
        for rel, path in resolved:
            if path.exists():
                backup_path = backup_root / rel
                backup_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, backup_path)
                cocoon["backups"].append({"rel": rel, "path": str(path), "backup": str(backup_path)})
                if _patch_creates_new_file(patch_text, rel):
                    path.unlink()
                    cocoon["backups"][-1]["removed_before_apply"] = True
            else:
                cocoon["backups"].append({"rel": rel, "path": str(path), "backup": None, "note": "new_file"})

        # Write patch to temp file and run git apply --check.
        # Use newline="\n" so the patch stays LF-only on Windows; git apply rejects CRLF diffs.
        with tempfile.NamedTemporaryFile(mode="w", suffix=".patch", delete=False, encoding="utf-8", newline="\n") as fh:
            fh.write(patch_text)
            patch_path = Path(fh.name)
        try:
            check = _run_git_apply(self.root, patch_path, check=True)
            cocoon["git_apply_check"] = check
            if not check.get("ok"):
                if _patch_already_applied(self.root, patch_path):
                    cocoon["git_apply_check"]["already_applied"] = True
                    cocoon["git_apply"] = {
                        "ok": True,
                        "already_applied": True,
                        "note": "Patch was already applied by the bounded autonomous self-coder path.",
                    }
                    return self._build_report(
                        status="applied",
                        ok=True,
                        blocked_reason=None,
                        next_action="Patch already applied; no further action needed.",
                        proposal=approval,
                        cocoon=cocoon,
                    )
                self._rollback(resolved, backup_root, cocoon)
                return self._build_report(
                    status="blocked",
                    ok=False,
                    blocked_reason="git_apply_check_failed",
                    next_action="Fix the patch so it applies cleanly, then re-propose.",
                    proposal=approval,
                    cocoon=cocoon,
                )

            # Apply patch.
            apply = _run_git_apply(self.root, patch_path, check=False)
            cocoon["git_apply"] = apply
            if not apply.get("ok"):
                self._rollback(resolved, backup_root, cocoon)
                return self._build_report(
                    status="rolled_back",
                    ok=False,
                    blocked_reason="git_apply_failed",
                    next_action="Patch applied check passed but apply failed; rolled back. Inspect git output.",
                    proposal=approval,
                    cocoon=cocoon,
                )

            # Run bounded test layers.
            test_layers = self._run_test_layers(target_files)
            cocoon["test_layers"] = test_layers
            all_pass = all(layer.get("ok") for layer in test_layers)
            if not all_pass:
                self._rollback(resolved, backup_root, cocoon)
                return self._build_report(
                    status="rolled_back",
                    ok=False,
                    blocked_reason="test_layer_failed",
                    next_action="Repair the patch so all bounded test layers pass, then re-propose.",
                    proposal=approval,
                    cocoon=cocoon,
                )

        finally:
            try:
                patch_path.unlink()
            except Exception:
                pass

        # Butterfly: re-read telemetry and hash files.
        self._telemetry_after = self._read_telemetry()
        file_hashes = self._hash_targets(resolved)

        report = self._build_report(
            status="emerged",
            ok=True,
            blocked_reason=None,
            next_action="Patch emerged from cocoon. Receipt written. Monitor next cycle.",
            proposal=approval,
            cocoon=cocoon,
            file_hashes=file_hashes,
        )
        cocoon["proposal_marked_applied"] = self._mark_proposal_applied(proposal)
        self._write_receipts(report)
        self._archive_self_coder_evidence()
        return report

    def _archive_self_coder_evidence(self) -> Dict[str, Any]:
        """Move the self-coder hand-off evidence into the backup dir after apply."""

        evidence_file = self.root / SELF_CODER_EVIDENCE_PATH
        if not evidence_file.exists():
            return {"archived": False, "reason": "no_evidence_file"}
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        archive_dir = self.backup_dir / "self_coder_evidence" / timestamp
        archive_dir.mkdir(parents=True, exist_ok=True)
        archive_path = archive_dir / evidence_file.name
        try:
            shutil.move(str(evidence_file), str(archive_path))
            return {"archived": True, "source": str(evidence_file), "destination": str(archive_path)}
        except Exception as exc:
            return {"archived": False, "reason": f"move_failed:{type(exc).__name__}:{exc}"}

    def _mark_proposal_applied(self, proposal: Dict[str, Any]) -> Dict[str, Any]:
        try:
            control = SafeCodeControl(state_path=self._rooted(SELF_CODER_PROPOSAL_PATH))
            return control.mark_reviewed_applied(proposal)
        except Exception as exc:
            return {"ok": False, "matched": False, "error": f"{type(exc).__name__}:{exc}"}

    def _run_test_layers(self, target_files: Sequence[str]) -> List[Dict[str, Any]]:
        layers: List[Dict[str, Any]] = []
        python_files = [
            rel for rel in target_files if rel.endswith(".py") and not rel.startswith("frontend/")
        ]
        compile_files = [
            rel for rel in python_files if not rel.startswith("tests/")
        ]
        if compile_files:
            result = _py_compile_files(self.root, compile_files)
            layers.append(result)

        frontend_files = [rel for rel in target_files if rel.startswith("frontend/")]
        if frontend_files:
            layers.append(_npm_run(self.root, "typecheck"))
            layers.append(_npm_run(self.root, "lint:shell"))

        test_files = [rel for rel in target_files if rel.startswith("tests/") and rel.startswith("test_", 6)]
        for test_file in test_files:
            layers.append(_pytest_file(self.root, test_file))

        # Companion tests for aureon modules.
        companion_tests: List[str] = []
        for rel in python_files:
            if rel.startswith("aureon/"):
                name = Path(rel).stem
                companion = f"tests/test_{name}.py"
                if (self.root / companion).exists() and companion not in test_files:
                    companion_tests.append(companion)
        for companion in companion_tests:
            layers.append(_pytest_file(self.root, companion))

        return layers

    def _rollback(
        self, resolved: Sequence[Tuple[str, Path]], backup_root: Path, cocoon: Dict[str, Any]
    ) -> None:
        rollback_log: List[Dict[str, Any]] = []
        for rel, path in resolved:
            backup_path = backup_root / rel
            if backup_path.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(backup_path, path)
                rollback_log.append({"rel": rel, "restored_from": str(backup_path)})
            else:
                # Newly created file: remove it.
                if path.exists():
                    try:
                        path.unlink()
                        rollback_log.append({"rel": rel, "deleted": True})
                    except Exception as exc:
                        rollback_log.append({"rel": rel, "delete_failed": str(exc)})
        cocoon["rollback"] = {"performed": True, "log": rollback_log}

    def _hash_targets(self, resolved: Sequence[Tuple[str, Path]]) -> Dict[str, str]:
        hashes: Dict[str, str] = {}
        for rel, path in resolved:
            if path.exists():
                hashes[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
            else:
                hashes[rel] = ""
        return hashes

    def _build_report(
        self,
        *,
        status: str,
        ok: bool,
        blocked_reason: str | None,
        next_action: str,
        proposal: Dict[str, Any] | None = None,
        proposals: List[Dict[str, Any]] | None = None,
        cocoon: Dict[str, Any] | None = None,
        file_hashes: Dict[str, str] | None = None,
    ) -> Dict[str, Any]:
        generated_at = datetime.now(UTC).isoformat()
        report: Dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "status": status,
            "ok": ok,
            "generated_at": generated_at,
            "operator_prompt": self.operator_prompt,
            "dry_run": self.dry_run,
            "root": str(self.root),
            "telemetry_before": (self._telemetry_before or TelemetrySnapshot()).to_dict(),
            "telemetry_after": (self._telemetry_after or TelemetrySnapshot()).to_dict(),
            "self_approval_policy": {
                "required_canonical_field": "available=True, data_status=live, truth_status=real_derived, freshness_status=fresh",
                "required_evolution_flow": "expand or steady with field_status=live",
                "required_terminal_state": "ok=True, stale=False",
                "required_pulse": "status.operational_core.status=healthy and available=True",
                "required_patch_shape": "unified diff with ---/+++/@@",
                "required_target_files": "all allowlisted and none blocked",
                "required_secret_scan": "clean",
                "required_operator_prompt": "no manual-authority needles",
                "required_path_authority": "no .env/credential/secret/private_key/live_order/order_router/payment/filing/hmrc/companies_house",
            },
            "proposal": proposal,
            "proposals": proposals,
            "cocoon": cocoon,
            "file_hashes": file_hashes,
            "human_review": status == "human_review",
            "blocked_reason": blocked_reason,
            "next_action": next_action,
            "allowlist": self.allowlist,
        }
        return report

    def _write_receipts(self, report: Dict[str, Any]) -> None:
        paths = [
            self._rooted(self.state_path),
            self._rooted(self.audit_json),
            self._rooted(self.public_json),
        ]
        for path in paths:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(report, indent=2, sort_keys=True, default=str), encoding="utf-8")
        md_path = self._rooted(self.audit_md)
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(_make_markdown(report), encoding="utf-8")

    def _acquire_lock(self) -> Dict[str, Any]:
        lock_file = self._rooted(self.lock_path)
        lock_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            # Try to create exclusively (O_EXCL). If it exists, check staleness.
            fd = os.open(str(lock_file), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            try:
                content = lock_file.read_text(encoding="utf-8")
                data = json.loads(content)
                created = float(data.get("created", 0))
                pid = int(data.get("pid", 0))
                if time.time() - created > 600:
                    # Stale lock.
                    lock_file.unlink()
                    fd = os.open(str(lock_file), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                elif pid and _process_alive(pid):
                    return {"acquired": False, "reason": "another_run_in_progress"}
                else:
                    lock_file.unlink()
                    fd = os.open(str(lock_file), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except Exception:
                return {"acquired": False, "reason": "lock_state_unreadable"}
        except Exception as exc:
            return {"acquired": False, "reason": f"lock_create_failed:{exc}"}

        payload = json.dumps({"pid": os.getpid(), "created": time.time()})
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(payload)
        return {"acquired": True, "lock_file": str(lock_file)}

    def _release_lock(self) -> None:
        lock_file = self._rooted(self.lock_path)
        try:
            if lock_file.exists():
                lock_file.unlink()
        except Exception:
            pass

    def _rooted(self, rel_path: Path) -> Path:
        return rel_path if rel_path.is_absolute() else self.root / rel_path


def _default_root() -> Path:
    return Path.cwd().resolve() if (Path.cwd() / "aureon").exists() else REPO_ROOT


def _bounded_target_path(root: Path, rel_path: Path) -> Path:
    """Resolve a target file path, refusing absolute or repo-escaping paths."""
    if rel_path.is_absolute():
        raise ValueError("target_path_must_be_repo_relative")
    normalized = _normalize_rel_path(rel_path.as_posix())
    candidate = root / normalized
    try:
        candidate.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError("target_path_escaped_repository") from exc
    return candidate


def _extra_blocked_path(path: str) -> bool:
    lower = _normalize_rel_path(path).lower()
    return any(needle in lower for needle in BLOCKED_PATH_NEEDLES)


def _patch_creates_new_file(patch_text: str, rel_path: str) -> bool:
    """Return True when the patch hunk for rel_path starts from /dev/null."""
    rel = _normalize_rel_path(rel_path)
    in_hunk = False
    for line in str(patch_text or "").splitlines():
        if line.startswith("diff --git"):
            in_hunk = False
        if line.startswith("--- "):
            raw = line[4:].strip().split("\t", 1)[0]
            in_hunk = _normalize_rel_path(raw) == rel or raw == "/dev/null"
        if in_hunk and line.startswith("--- /dev/null"):
            return True
    return False


def _requests_get_json(url: str) -> Dict[str, Any]:
    try:
        import requests

        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception:
        return _urllib_get_json(url)


def _urllib_get_json(url: str) -> Dict[str, Any]:
    import urllib.request

    with urllib.request.urlopen(url, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def _run_git_apply(root: Path, patch_path: Path, *, check: bool, reverse: bool = False) -> Dict[str, Any]:
    command = ["git", "apply", "--whitespace=nowarn"]
    if check:
        command.append("--check")
    if reverse:
        command.append("--reverse")
    command.append(str(patch_path))
    result = subprocess.run(command, cwd=root, capture_output=True, text=True)
    return {
        "ok": result.returncode == 0,
        "command": command,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def _patch_already_applied(root: Path, patch_path: Path) -> bool:
    """True if the patch has already been applied to the working tree."""
    reverse_check = _run_git_apply(root, patch_path, check=True, reverse=True)
    return bool(reverse_check.get("ok"))


def _py_compile_files(root: Path, rel_paths: Sequence[str]) -> Dict[str, Any]:
    files = [str(root / rel) for rel in rel_paths]
    result = subprocess.run(
        [sys.executable, "-m", "py_compile", *files],
        cwd=root,
        capture_output=True,
        text=True,
    )
    return {
        "layer": "py_compile",
        "ok": result.returncode == 0,
        "files": files,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode,
    }


def _npm_run(root: Path, script: str) -> Dict[str, Any]:
    frontend = root / "frontend"
    if not (frontend / "package.json").exists():
        return {"layer": f"npm:{script}", "ok": True, "note": "no_frontend_package_json"}
    result = subprocess.run(
        ["npm", "run", script],
        cwd=frontend,
        capture_output=True,
        text=True,
    )
    return {
        "layer": f"npm:{script}",
        "ok": result.returncode == 0,
        "stdout": result.stdout[-4000:],
        "stderr": result.stderr[-4000:],
        "returncode": result.returncode,
    }


def _pytest_file(root: Path, rel_path: str) -> Dict[str, Any]:
    test_path = root / rel_path
    if not test_path.exists():
        return {"layer": "pytest", "ok": True, "note": "test_file_missing", "file": str(test_path)}
    result = subprocess.run(
        [sys.executable, "-m", "pytest", str(test_path), "-q"],
        cwd=root,
        capture_output=True,
        text=True,
    )
    return {
        "layer": "pytest",
        "ok": result.returncode == 0,
        "file": str(test_path),
        "stdout": result.stdout[-6000:],
        "stderr": result.stderr[-6000:],
        "returncode": result.returncode,
    }


def _process_alive(pid: int) -> bool:
    try:
        import psutil

        return psutil.pid_exists(pid)
    except Exception:
        # Best-effort fallback; on Windows signal 0 is not supported, so treat
        # an unreadable lock as stale after the timeout rather than crash.
        try:
            os.kill(pid, 0)
            return True
        except Exception:
            return False


def _make_markdown(report: Dict[str, Any]) -> str:
    lines = [
        "# Aureon Autonomous Coherence Gate Director",
        "",
        f"- status: {report.get('status')}",
        f"- ok: {report.get('ok')}",
        f"- dry_run: {report.get('dry_run')}",
        f"- generated_at: {report.get('generated_at')}",
        f"- blocked_reason: {report.get('blocked_reason')}",
        f"- next_action: {report.get('next_action')}",
        "",
        "## Telemetry (before)",
    ]
    before = report.get("telemetry_before") or {}
    flow = (before.get("evolution_flow") or {})
    lines.extend(
        [
            f"- canonical_field_available: {(before.get('canonical_field') or {}).get('available')}",
            f"- evolution_flow: {flow.get('flow')}",
            f"- evolution_field_status: {flow.get('field_status')}",
            f"- terminal_state_ok: {(before.get('terminal_state') or {}).get('ok')}",
            f"- terminal_state_stale: {(before.get('terminal_state') or {}).get('stale')}",
            f"- pulse_operational_core_status: {((before.get('pulse') or {}).get('status') or {}).get('operational_core', {}).get('status')}",
        ]
    )
    lines.extend(["", "## Proposal / Self-Approval"])
    proposal = report.get("proposal")
    if proposal:
        lines.append(f"- proposal_id: {proposal.get('proposal_id')}")
        lines.append(f"- approved: {proposal.get('approved')}")
        lines.append(f"- blocked_reason: {proposal.get('blocked_reason')}")
        lines.append("- checks:")
        for check in proposal.get("checks", []):
            lines.append(f"  - {check.get('id')}: ok={check.get('ok')} ({check.get('detail')})")
    cocoon = report.get("cocoon")
    if cocoon:
        lines.extend(["", "## Cocoon"])
        lines.append(f"- git_apply_check_ok: {(cocoon.get('git_apply_check') or {}).get('ok')}")
        lines.append(f"- git_apply_ok: {(cocoon.get('git_apply') or {}).get('ok')}")
        lines.append("- test_layers:")
        for layer in cocoon.get("test_layers", []):
            lines.append(f"  - {layer.get('layer')}: ok={layer.get('ok')}")
        rollback = cocoon.get("rollback") or {}
        if rollback.get("performed"):
            lines.append(f"- rollback_performed: True ({len(rollback.get('log', []))} files)")
    hashes = report.get("file_hashes")
    if hashes:
        lines.extend(["", "## File Hashes"])
        for rel, digest in hashes.items():
            lines.append(f"- `{rel}`: `{digest}`")
    return "\n".join(lines) + "\n"


def build_and_write_coherence_gate_director(
    *,
    root: Path | None = None,
    operator_prompt: str = "",
    dry_run: bool = False,
    allowlist: Sequence[str] | None = None,
    lock_path: Path = DEFAULT_LOCK_PATH,
) -> Dict[str, Any]:
    director = CoherenceGateDirector(
        root=root,
        operator_prompt=operator_prompt,
        dry_run=dry_run,
        allowlist=allowlist,
        lock_path=lock_path,
    )
    report = director.run_cycle()
    # Receipts are part of the butterfly phase; dry-run only validates.
    if not dry_run:
        director._write_receipts(report)
    return report


def _build_test_proposal_patch(root: Path) -> str:
    """Build a unified diff that creates the director's pytest file.

    Reads the current test file so the embedded proposal always matches the
    checked-in tests. Falls back to a minimal static patch when the file is
    missing.
    """
    test_path = root / "tests" / "test_aureon_autonomous_coherence_gate_director.py"
    if test_path.exists():
        content = test_path.read_text(encoding="utf-8")
        lines = content.splitlines(keepends=True)
        header = [
            "diff --git a/tests/test_aureon_autonomous_coherence_gate_director.py "
            "b/tests/test_aureon_autonomous_coherence_gate_director.py",
            "new file mode 100644",
            "--- /dev/null",
            "+++ b/tests/test_aureon_autonomous_coherence_gate_director.py",
            f"@@ -0,0 +1,{len(lines)} @@",
        ]
        body = ["+" + line.rstrip("\n") for line in lines]
        if not content.endswith("\n"):
            body.append("+")
        return "\n".join(header + body) + "\n"

    # Minimal static fallback for bootstrapping when the test file is absent.
    return (
        "diff --git a/tests/test_aureon_autonomous_coherence_gate_director.py "
        "b/tests/test_aureon_autonomous_coherence_gate_director.py\n"
        "new file mode 100644\n"
        "--- /dev/null\n"
        "+++ b/tests/test_aureon_autonomous_coherence_gate_director.py\n"
        "@@ -0,0 +1,20 @@\n"
        "+from __future__ import annotations\n"
        "+\n"
        "+from aureon.autonomous.aureon_autonomous_coherence_gate_director import (\n"
        "+    CoherenceGateDirector,\n"
        "+    build_and_write_coherence_gate_director,\n"
        "+)\n"
        "+\n"
        "+\n"
        "+def test_director_can_read_live_telemetry() -> None:\n"
        "+    director = CoherenceGateDirector(dry_run=True)\n"
        "+    telemetry = director._read_telemetry()\n"
        "+    assert isinstance(telemetry.canonical_field, dict)\n"
        "+    assert telemetry.evolution_flow.get(\"flow\") in (\n"
        "+        \"expand\", \"steady\", \"repair\", \"observe\"\n"
        "+    )\n"
        "+\n"
        "+\n"
        "+def test_report_contains_schema_version() -> None:\n"
        "+    report = build_and_write_coherence_gate_director(dry_run=True)\n"
        "+    assert report[\"schema_version\"] == \"aureon-autonomous-coherence-gate-director-v1\"\n"
        "+    assert \"telemetry_before\" in report\n"
    )


def _create_test_proposal(root: Path) -> Dict[str, Any]:
    """Insert one safe test proposal into SafeCodeControl and return it."""
    control = SafeCodeControl(state_path=root / SAFE_CODE_DEFAULT_STATE_PATH)
    # Remove stale coherence-gate test proposals so the latest patch is applied.
    control.pending_proposals = [
        p for p in control.pending_proposals if p.get("title") != "coherence_gate_test_self_fix"
    ]
    control.recent_reviews = [
        r for r in control.recent_reviews if r.get("title") != "coherence_gate_test_self_fix"
    ]
    patch_text = _build_test_proposal_patch(root)
    proposal = CodeProposal(
        kind="patch_proposal",
        title="coherence_gate_test_self_fix",
        summary="Safe test proposal for the coherence gate director.",
        target_files=["tests/test_aureon_autonomous_coherence_gate_director.py"],
        patch_text=patch_text,
        source="coherence_gate_director_cli",
    )
    # Force approval so the director can attempt the cocoon.
    item = control.propose(proposal)
    item["status"] = "approved"
    item["reviewed_at"] = time.time()
    item["reviewer"] = "coherence_gate_director_cli"
    control.recent_reviews.append(item)
    control.pending_proposals = [p for p in control.pending_proposals if p.get("title") != proposal.title]
    control._persist()
    return item


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run Aureon's autonomous coherence gate director (caterpillar-to-cocoon-to-butterfly)."
    )
    parser.add_argument("--root", default="", help="Repository root. Defaults to the Aureon repo.")
    parser.add_argument("--json", action="store_true", help="Print full JSON report.")
    parser.add_argument("--dry-run", action="store_true", help="Validate but do not apply patches.")
    parser.add_argument(
        "--create-test-proposal",
        action="store_true",
        help="Insert a safe test proposal and attempt the cocoon/butterfly.",
    )
    parser.add_argument("--operator-prompt", default="", help="Optional operator prompt for authority scan.")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve() if args.root else None

    if args.create_test_proposal:
        resolved_root = Path(root or _default_root()).resolve()
        _create_test_proposal(resolved_root)

    report = build_and_write_coherence_gate_director(
        root=root,
        operator_prompt=args.operator_prompt,
        dry_run=args.dry_run,
    )

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True, default=str))
    else:
        status = report.get("status")
        ok = report.get("ok")
        reason = report.get("blocked_reason") or report.get("next_action")
        print(f"{status}: ok={ok} reason={reason}")
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
