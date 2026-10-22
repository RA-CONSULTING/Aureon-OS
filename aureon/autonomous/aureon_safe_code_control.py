#!/usr/bin/env python3
"""
Safe local code proposal controller.

This module does not directly modify the repo or execute generated code.
It provides a reviewable queue for:
- code tasks
- proposed file edits
- patch text proposals

By default proposals are pending review. Set AUREON_CODE_AUTO_APPROVE=1 only
for an explicitly trusted local workflow that wants proposals marked approved
immediately; this still does not apply patches by itself. Auto-approve does
not cover protected paths: live-trading flags, evidence gates, position
sizing, and credential files stay pending human review.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from aureon.autonomous.self_repair_guard import block_reason_for_proposal
from aureon.code_architect.expression import build_code_expression_context


DEFAULT_STATE_PATH = Path("state/safe_code_control_state.json")


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class CodeProposal:
    kind: str
    title: str
    summary: str = ""
    target_files: List[str] = field(default_factory=list)
    patch_text: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    source: str = "local"
    created_at: float = field(default_factory=time.time)


class SafeCodeControl:
    def __init__(self, state_path: Optional[Path] = None) -> None:
        self.state_path = Path(state_path or DEFAULT_STATE_PATH)
        self.state_path.parent.mkdir(parents=True, exist_ok=True)

        self.enabled = True
        self.auto_approve = _env_bool("AUREON_CODE_AUTO_APPROVE", False)
        self.pending_proposals: List[Dict[str, Any]] = []
        self.recent_reviews: List[Dict[str, Any]] = []
        self.last_error = ""
        self.max_pending = 50
        self.max_recent = 25
        self._load_existing()
        self._persist()

    def propose(self, proposal: CodeProposal) -> Dict[str, Any]:
        self._attach_expression_context(proposal)
        item = asdict(proposal)
        protected = block_reason_for_proposal(
            proposal.target_files,
            proposal.patch_text,
            proposal.title,
            proposal.summary,
        )
        if protected:
            item["status"] = "pending_human_review"
            item["human_review"] = True
            item["reason"] = protected
            item["reviewer"] = ""
            self.pending_proposals.append(item)
            self.pending_proposals = self.pending_proposals[-self.max_pending :]
            self._persist()
            return item
        if self.auto_approve:
            item["status"] = "approved"
            item["reviewed_at"] = time.time()
            item["reviewer"] = "env:AUREON_CODE_AUTO_APPROVE"
            self.recent_reviews.append(item)
            self.recent_reviews = self.recent_reviews[-self.max_recent :]
        else:
            item["status"] = "pending_review"
            self.pending_proposals.append(item)
            self.pending_proposals = self.pending_proposals[-self.max_pending :]
        self._persist()
        return item

    def _attach_expression_context(self, proposal: CodeProposal) -> None:
        if proposal.metadata.get("expression_context"):
            return
        context = build_code_expression_context(
            proposal.title or proposal.kind,
            evidence={
                "runtime_state": {
                    "hot_topic": proposal.title or proposal.kind,
                    "action": "PROPOSE_CODE",
                    "mode": "safe_code_control",
                },
                "proposal": {
                    "kind": proposal.kind,
                    "title": proposal.title,
                    "summary": proposal.summary,
                    "target_files": proposal.target_files,
                    "source": proposal.source,
                    "has_patch_text": bool(proposal.patch_text.strip()),
                },
            },
            evidence_dir=self.state_path.parent,
            publish=True,
        )
        proposal.metadata["expression_context"] = context
        if not proposal.summary and context.get("voice_summary"):
            proposal.summary = str(context["voice_summary"])[:500]

    def approve_next(self, reviewer: str = "operator") -> Dict[str, Any]:
        if not self.pending_proposals:
            result = {"ok": False, "reason": "no_pending_proposals"}
            self.last_error = result["reason"]
            self._persist()
            return result
        item = self.pending_proposals.pop(0)
        item["status"] = "approved"
        item["reviewed_at"] = time.time()
        item["reviewer"] = reviewer
        self.recent_reviews.append(item)
        self.recent_reviews = self.recent_reviews[-self.max_recent :]
        self._persist()
        return {"ok": True, "proposal": item}

    def reject_next(self, reviewer: str = "operator", reason: str = "rejected") -> Dict[str, Any]:
        if not self.pending_proposals:
            result = {"ok": False, "reason": "no_pending_proposals"}
            self.last_error = result["reason"]
            self._persist()
            return result
        item = self.pending_proposals.pop(0)
        item["status"] = "rejected"
        item["reviewed_at"] = time.time()
        item["reviewer"] = reviewer
        item["reject_reason"] = reason
        self.recent_reviews.append(item)
        self.recent_reviews = self.recent_reviews[-self.max_recent :]
        self._persist()
        return {"ok": True, "proposal": item}

    def mark_reviewed_applied(self, proposal: Dict[str, Any]) -> Dict[str, Any]:
        """Mark a reviewed proposal as applied so it is not reloaded."""
        created_at = proposal.get("created_at")
        title = proposal.get("title")
        matched = False
        for item in self.recent_reviews:
            if item.get("title") != title:
                continue
            if created_at is not None and item.get("created_at") != created_at:
                continue
            item["status"] = "applied"
            item["applied_at"] = time.time()
            matched = True
            break
        if matched:
            self._persist()
        return {"ok": matched, "matched": matched}

    def clear_pending(self) -> None:
        self.pending_proposals = []
        self._persist()

    def status(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "auto_approve": self.auto_approve,
            "last_error": self.last_error,
            "pending_count": len(self.pending_proposals),
            "pending_proposals": self.pending_proposals[-10:],
            "recent_reviews": self.recent_reviews[-10:],
        }

    def _persist(self) -> None:
        self.state_path.write_text(json.dumps(self.status(), indent=2), encoding="utf-8")

    def _load_existing(self) -> None:
        if not self.state_path.exists():
            return
        try:
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
        except Exception:
            return
        if isinstance(data.get("pending_proposals"), list):
            self.pending_proposals = data["pending_proposals"][-self.max_pending :]
        if isinstance(data.get("recent_reviews"), list):
            self.recent_reviews = data["recent_reviews"][-self.max_recent :]
        self.enabled = bool(data.get("enabled", self.enabled))
        self.last_error = str(data.get("last_error") or "")


def build_default_code_controller() -> SafeCodeControl:
    return SafeCodeControl()


if __name__ == "__main__":
    ctl = build_default_code_controller()
    print(json.dumps(ctl.status(), indent=2))
