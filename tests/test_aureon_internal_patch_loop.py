from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Generator

import pytest

from aureon.autonomous.aureon_agent_company_brain_fabric import (
    provision_agent_company_brain_fabric as _provision_agent_company_brain_fabric,
)
from aureon.autonomous.aureon_internal_coding_workforce import (
    ResolvedBrain,
)
from aureon.autonomous.aureon_internal_coding_workforce import (
    provision_internal_coding_workforce as _provision_internal_coding_workforce,
)
from aureon.autonomous.aureon_internal_patch_loop import (
    InternalPatchHold,
    _canonicalize_full_replacement_diff,
    _git_apply_check,
    build_patch_request,
    run_internal_patch_cycle,
)
from aureon.autonomous.aureon_safe_code_control import SafeCodeControl
from aureon.inhouse_ai.llm_adapter import LLMAdapter, LLMResponse, StreamChunk
from tests.aureon_ten_nine_one_fixtures import build_test_thought_path


def provision_agent_company_brain_fabric(*args, **kwargs):
    kwargs.setdefault("thought_path", build_test_thought_path())
    return _provision_agent_company_brain_fabric(*args, **kwargs)


def provision_internal_coding_workforce(*args, **kwargs):
    kwargs.setdefault("thought_path", build_test_thought_path())
    return _provision_internal_coding_workforce(*args, **kwargs)


GOOD_PATCH = """--- a/sample.py
+++ b/sample.py
@@ -1,2 +1,2 @@
 def answer():
-    return 1
+    return 2
"""

TRUNCATED_PATCH = """--- a/sample.py
+++ b/sample.py
@@ -1,2 +1,2 @@
 def answer():
-    return 1
"""

FULL_REPLACEMENT_WRONG_COUNTS = """--- a/sample.py
+++ b/sample.py
@@ -1,82 +1,18 @@
-def answer():
-    return 1
+def answer():
+    return 2
"""


class PatchAdapter(LLMAdapter):
    def __init__(
        self,
        lane: str,
        patch_text: str = GOOD_PATCH,
        *,
        invalid_once: bool = False,
        council_hold: bool = False,
        decision_text: str = "",
        first_patch_text: str = "",
    ) -> None:
        self.lane = lane
        self.patch_text = patch_text
        self.invalid_once = invalid_once
        self.council_hold = council_hold
        self.decision_text = decision_text
        self.first_patch_text = first_patch_text
        self.author_calls = 0
        self.calls = 0
        self.prompts: list[str] = []
        self.prompt_token_budgets: list[tuple[str, int]] = []

    def prompt(
        self,
        messages: list[dict[str, Any]],
        system: str = "",
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs,
    ) -> LLMResponse:
        del system, tools, temperature, kwargs
        self.calls += 1
        prompt = str(messages[-1]["content"]).split("Original prompt:\n", 1)[-1]
        self.prompts.append(prompt)
        self.prompt_token_budgets.append((prompt, max_tokens))
        if prompt.startswith(("AUTHOR ONE UNIFIED DIFF ONLY.", "CORRECT THE PREVIOUS FORMAT FAILURE.")):
            self.author_calls += 1
            if self.invalid_once and self.author_calls == 1:
                return LLMResponse(text="I will make the requested change.", model=f"{self.lane}-model")
            if self.first_patch_text and self.author_calls == 1:
                return LLMResponse(text=self.first_patch_text, model=f"{self.lane}-model")
            return LLMResponse(text=f"```diff\n{self.patch_text}```", model=f"{self.lane}-model")
        if "PRE-APPLY COUNCIL." in prompt and "Reply ACCEPT or HOLD" in prompt:
            verdict = "HOLD" if self.council_hold and self.lane == "architecture" else "ACCEPT"
            return LLMResponse(text=f"{verdict} bounded {self.lane} review", model=f"{self.lane}-model")
        decision = self.decision_text or f"bounded {self.lane} decision"
        return LLMResponse(text=decision, model=f"{self.lane}-model")

    def stream(
        self,
        messages: list[dict[str, Any]],
        system: str = "",
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs,
    ) -> Generator[StreamChunk, None, None]:
        del messages, system, tools, max_tokens, temperature, kwargs
        yield StreamChunk(text="done", done=True)


class PatchResolver:
    def __init__(
        self,
        patch_text: str = GOOD_PATCH,
        *,
        ready: bool = True,
        invalid_once: bool = False,
        council_hold: bool = False,
        decision_text: str = "",
        first_patch_text: str = "",
    ) -> None:
        self.patch_text = patch_text
        self.ready = ready
        self.invalid_once = invalid_once
        self.council_hold = council_hold
        self.decision_text = decision_text
        self.first_patch_text = first_patch_text
        self.adapters: dict[str, PatchAdapter] = {}

    def resolve(self, lane: str) -> ResolvedBrain:
        return self.resolve_for(lane, nerve_id=f"lane:{lane}")

    def resolve_for(self, lane: str, *, nerve_id: str) -> ResolvedBrain:
        adapter = self.adapters.setdefault(
            lane,
            PatchAdapter(
                lane,
                self.patch_text,
                invalid_once=self.invalid_once,
                council_hold=self.council_hold,
                decision_text=self.decision_text,
                first_patch_text=self.first_patch_text,
            ),
        )
        return ResolvedBrain(
            adapter=adapter,
            lane=lane,
            model=f"ollama-{lane}",
            source="live_probe_passed:hnc_active:test" if self.ready else "no_model_available",
            endpoint_reachable=self.ready,
            working=self.ready,
            catalog_size=5,
            catalog_refreshed_at=1_787_000_000.0,
            endpoint_authority_digest="f" * 64,
            routing_receipt_id=(
                "ollama:hnc-route:" + hashlib.sha256(nerve_id.encode()).hexdigest()
                if self.ready
                else ""
            ),
            hnc_receipt_id="hnc:live_field:test" if self.ready else "",
            hnc_gamma=0.9 if self.ready else None,
            hnc_coherence_band="active" if self.ready else "",
            provider_mode="ollama_cloud_primary" if self.ready else "",
        )

    @property
    def prompt_call_count(self) -> int:
        return sum(adapter.calls for adapter in self.adapters.values())


def _source(root: Path, text: str = "def answer():\n    return 1\n") -> Path:
    path = root / "sample.py"
    path.write_text(text, encoding="utf-8")
    return path


def _controller(root: Path, monkeypatch) -> SafeCodeControl:
    monkeypatch.setattr(SafeCodeControl, "_attach_expression_context", lambda self, proposal: None)
    return SafeCodeControl(state_path=root / "state" / "proposals.json")


def _request(root: Path, assertion: str = "assert answer() == 2"):
    return build_patch_request(
        root=root,
        goal="Make answer return two while preserving the public function.",
        target_path="sample.py",
        test_commands=[
            [
                sys.executable,
                "-c",
                f"from sample import answer; {assertion}",
            ]
        ],
    )


def test_aureon_authors_applies_and_tests_a_real_unified_diff(tmp_path: Path, monkeypatch) -> None:
    source = _source(tmp_path)
    resolver = PatchResolver()
    workforce = provision_agent_company_brain_fabric(resolver)
    controller = _controller(tmp_path, monkeypatch)
    controller.pending_proposals.append({"status": "pending_review", "title": "older proposal"})
    controller._persist()

    cycle = run_internal_patch_cycle(
        root=tmp_path,
        request=_request(tmp_path),
        workforce=workforce,
        controller=controller,
    )

    assert source.read_text(encoding="utf-8") == "def answer():\n    return 2\n"
    assert cycle["status"] == "internal_patch_applied_pending_senior_review"
    assert cycle["applied"] is True
    assert cycle["pending_senior_review"] is True
    assert cycle["proposal"]["source"] == "aureon_internal_coding_workforce"
    assert cycle["proposal"]["status"] == "approved"
    assert cycle["proposal"]["reviewer"] == "aureon:pre_apply_council"
    assert cycle["proposal"]["metadata"]["codex_implementation"] is False
    assert cycle["authoring_correction_attempted"] is False
    assert len(cycle["author_work_receipt_ids"]) == 1
    assert cycle["patch_validation"]["target_paths"] == ["sample.py"]
    assert cycle["apply_evidence"]["status"] == "applied"
    assert cycle["apply_evidence"]["test_results"][0]["ok"] is True
    assert cycle["pre_apply_council"]["accepted"] is True
    assert cycle["pre_apply_council"]["decision_count"] == 16
    assert cycle["pre_apply_council"]["hold_count"] == 0
    assert cycle["workforce_report"]["internal_work_units"] == 99
    assert cycle["workforce_report"]["ten_nine_one_work_units"] == 99
    assert cycle["workforce_report"]["ten_nine_one_complete"] is True
    assert cycle["workforce_report"]["senior_oversight_units"] == 0
    assert cycle["workforce_report"]["ready"] is False
    assert len(cycle["evidence_digest"]) == 64
    assert resolver.prompt_call_count == 99
    assert len(workforce.thought_path_receipts) == 99
    pre_apply_prompts = [
        prompt
        for adapter in resolver.adapters.values()
        for prompt in adapter.prompts
        if "FULL VALIDATED UNIFIED DIFF (no bytes omitted):" in prompt
    ]
    assert len(pre_apply_prompts) == 16
    assert all(GOOD_PATCH in prompt for prompt in pre_apply_prompts)
    assert all("those distinct hashes are not expected to be equal" in prompt for prompt in pre_apply_prompts)
    author_budgets = [
        budget
        for adapter in resolver.adapters.values()
        for prompt, budget in adapter.prompt_token_budgets
        if prompt.startswith("AUTHOR ONE UNIFIED DIFF ONLY.")
    ]
    council_budgets = [
        budget
        for adapter in resolver.adapters.values()
        for prompt, budget in adapter.prompt_token_budgets
        if "FULL VALIDATED UNIFIED DIFF (no bytes omitted):" in prompt
    ]
    assert author_budgets == [4_096]
    assert council_budgets == [512] * 16
    persisted = json.loads(controller.state_path.read_text(encoding="utf-8"))
    assert persisted["pending_count"] == 1
    assert persisted["pending_proposals"][0]["title"] == "older proposal"
    assert persisted["recent_reviews"][-1]["status"] == "approved"
    assert persisted["recent_reviews"][-1]["reviewer"] == "aureon:pre_apply_council"


def test_git_invalid_truncated_hunk_gets_one_receipted_correction(
    tmp_path: Path, monkeypatch
) -> None:
    source = _source(tmp_path)
    resolver = PatchResolver(first_patch_text=TRUNCATED_PATCH)
    workforce = provision_agent_company_brain_fabric(resolver)

    cycle = run_internal_patch_cycle(
        root=tmp_path,
        request=_request(tmp_path),
        workforce=workforce,
        controller=_controller(tmp_path, monkeypatch),
    )

    assert source.read_text(encoding="utf-8") == "def answer():\n    return 2\n"
    assert cycle["authoring_correction_attempted"] is True
    assert cycle["authoring_failure_reason"] == "authored_diff_git_apply_check_failed"
    assert cycle["git_apply_check"]["ok"] is True
    assert len(cycle["author_work_receipt_ids"]) == 2
    assert sum(adapter.author_calls for adapter in resolver.adapters.values()) == 2
    correction_prompts = [
        prompt
        for adapter in resolver.adapters.values()
        for prompt in adapter.prompts
        if prompt.startswith("CORRECT THE PREVIOUS FORMAT FAILURE.")
    ]
    assert len(correction_prompts) == 1
    assert "use no diff --git, index metadata, or context lines" in correction_prompts[0]


def test_wrong_full_replacement_counts_are_canonicalized_after_one_correction(
    tmp_path: Path, monkeypatch
) -> None:
    source = _source(tmp_path)
    resolver = PatchResolver(patch_text=FULL_REPLACEMENT_WRONG_COUNTS)
    workforce = provision_agent_company_brain_fabric(resolver)

    cycle = run_internal_patch_cycle(
        root=tmp_path,
        request=_request(tmp_path),
        workforce=workforce,
        controller=_controller(tmp_path, monkeypatch),
    )

    receipt = cycle["structural_canonicalization"]
    expected = chr(10).join(("def answer():", "    return 2", ""))
    assert source.read_text(encoding="utf-8") == expected
    assert cycle["applied"] is True
    assert cycle["authoring_correction_attempted"] is True
    assert receipt["used"] is True
    assert receipt["removed_line_count"] == 2
    assert receipt["added_line_count"] == 2
    assert receipt["source_lines_consumed"] == 2
    assert receipt["source_coverage_complete"] is True
    assert receipt["original_patch_sha256"] != receipt["canonical_patch_sha256"]
    assert receipt["model_additions_preserved"] is True
    council_prompts = [
        prompt
        for adapter in resolver.adapters.values()
        for prompt in adapter.prompts
        if "FULL VALIDATED UNIFIED DIFF (no bytes omitted):" in prompt
    ]
    assert len(council_prompts) == 16
    assert all("@@ -1,2 +1,2 @@" in prompt for prompt in council_prompts)


def test_full_replacement_canonicalizer_rejects_ambiguous_inputs() -> None:
    source = chr(10).join(("def answer():", "    return 1", ""))
    cases = (
        (
            """--- a/sample.py
+++ b/sample.py
@@ -1,2 +1,1 @@
-def answer():
+def answer():
""",
            "full_replacement_canonicalization_source_mismatch",
        ),
        (
            """--- a/sample.py
+++ b/sample.py
@@ -1,2 +1,2 @@
 wrong_answer():
-    return 1
+    return 2
""",
            "full_replacement_canonicalization_source_mismatch",
        ),
        (
            """--- a/sample.py
+++ b/sample.py
@@ -1,2 +1,2 @@
-def answer():
-    return 1
+API_SECRET = 'secret-value'
+def answer():
""",
            "full_replacement_canonicalization_secret_scan_failed",
        ),
        (
            """diff --git a/sample.py b/sample.py
--- a/sample.py
+++ b/sample.py
@@ -1,2 +1,2 @@
-def answer():
-    return 1
+def answer():
+    return 2
""",
            "full_replacement_canonicalization_headers_invalid",
        ),
    )
    for patch_text, reason in cases:
        with pytest.raises(InternalPatchHold, match=reason):
            _canonicalize_full_replacement_diff(
                source=source,
                patch_text=patch_text,
                target_path="sample.py",
            )


def test_full_source_context_replay_is_unicode_safe_and_git_applicable(tmp_path: Path) -> None:
    newline = chr(10)
    source = newline.join(("# target 🎯", "value = 'old'", ""))
    (tmp_path / "sample.py").write_text(source, encoding="utf-8")
    patch_text = newline.join(
        (
            "--- a/sample.py",
            "+++ b/sample.py",
            "@@ -1,99 +1,1 @@",
            " # target 🎯",
            "-value = 'old'",
            "+value = 'new'",
            "",
        )
    )

    canonical, receipt = _canonicalize_full_replacement_diff(
        source=source,
        patch_text=patch_text,
        target_path="sample.py",
    )

    assert receipt["source_line_count"] == 2
    assert receipt["source_lines_consumed"] == 2
    assert receipt["context_line_count"] == 1
    assert receipt["removed_line_count"] == 1
    assert receipt["model_addition_line_count"] == 1
    assert receipt["source_coverage_complete"] is True
    assert "@@ -1,2 +1,2 @@" in canonical
    assert _git_apply_check(tmp_path, canonical)["ok"] is True


def test_full_patch_prompt_over_budget_holds_before_council_or_mutation(
    tmp_path: Path, monkeypatch
) -> None:
    source_text = "value = 'a'\n"
    source = _source(tmp_path, text=source_text)
    replacement = "x" * 48_000
    large_patch = (
        "--- a/sample.py\n"
        "+++ b/sample.py\n"
        "@@ -1 +1 @@\n"
        "-value = 'a'\n"
        f"+value = '{replacement}'\n"
    )
    resolver = PatchResolver(patch_text=large_patch)
    workforce = provision_agent_company_brain_fabric(resolver)

    with pytest.raises(InternalPatchHold, match="pre_apply_full_patch_prompt_exceeds_limit"):
        run_internal_patch_cycle(
            root=tmp_path,
            request=_request(tmp_path),
            workforce=workforce,
            controller=_controller(tmp_path, monkeypatch),
        )

    assert source.read_text(encoding="utf-8") == source_text
    assert not any(
        "FULL VALIDATED UNIFIED DIFF (no bytes omitted):" in prompt
        for adapter in resolver.adapters.values()
        for prompt in adapter.prompts
    )


def test_long_unicode_council_is_digest_bound_within_author_prompt_limit(
    tmp_path: Path, monkeypatch
) -> None:
    _source(tmp_path)
    resolver = PatchResolver(decision_text=("late warning Ω漢字 " * 500))
    workforce = provision_agent_company_brain_fabric(resolver)

    cycle = run_internal_patch_cycle(
        root=tmp_path,
        request=_request(tmp_path),
        workforce=workforce,
        controller=_controller(tmp_path, monkeypatch),
    )

    context = cycle["author_prompt_context"]
    author_prompts = [
        prompt
        for adapter in resolver.adapters.values()
        for prompt in adapter.prompts
        if prompt.startswith("AUTHOR ONE UNIFIED DIFF ONLY.")
    ]
    assert len(author_prompts) == 1
    assert len(author_prompts[0]) <= context["prompt_char_count"]
    assert context["prompt_char_count"] <= context["prompt_char_limit"] == 65_536
    assert context["decision_count"] == 41
    assert context["excerpt_char_limit"] < 1_500
    assert author_prompts[0].count('"process_decision_sha256"') == 41
    assert f"Full Aureon deliberation SHA-256: {cycle['deliberation_digest']}" in author_prompts[0]


def test_full_source_and_minimum_council_context_fail_closed_when_prompt_cannot_fit(
    tmp_path: Path, monkeypatch
) -> None:
    source = _source(tmp_path, text="value = '" + ("x" * 60_000) + "'\n")
    resolver = PatchResolver(decision_text=("Ω漢字" * 2_000))
    workforce = provision_agent_company_brain_fabric(resolver)

    with pytest.raises(InternalPatchHold, match="author_prompt_minimum_context_exceeds_limit"):
        run_internal_patch_cycle(
            root=tmp_path,
            request=_request(tmp_path),
            workforce=workforce,
            controller=_controller(tmp_path, monkeypatch),
        )

    assert source.read_text(encoding="utf-8") == "value = '" + ("x" * 60_000) + "'\n"
    assert sum(adapter.author_calls for adapter in resolver.adapters.values()) == 0


def test_format_failure_gets_one_receipted_correction_then_applies(tmp_path: Path, monkeypatch) -> None:
    source = _source(tmp_path)
    resolver = PatchResolver(invalid_once=True)
    workforce = provision_agent_company_brain_fabric(resolver)

    cycle = run_internal_patch_cycle(
        root=tmp_path,
        request=_request(tmp_path),
        workforce=workforce,
        controller=_controller(tmp_path, monkeypatch),
    )

    assert source.read_text(encoding="utf-8") == "def answer():\n    return 2\n"
    assert cycle["applied"] is True
    assert cycle["authoring_correction_attempted"] is True
    assert len(cycle["author_work_receipt_ids"]) == 2
    assert cycle["proposal"]["metadata"]["authoring_correction_attempted"] is True
    assert cycle["workforce_report"]["internal_work_units"] == 100
    assert resolver.prompt_call_count == 100


def test_failed_tests_roll_back_the_aureon_authored_patch(tmp_path: Path, monkeypatch) -> None:
    source = _source(tmp_path)
    workforce = provision_agent_company_brain_fabric(PatchResolver())

    cycle = run_internal_patch_cycle(
        root=tmp_path,
        request=_request(tmp_path, assertion="assert answer() == 3"),
        workforce=workforce,
        controller=_controller(tmp_path, monkeypatch),
    )

    assert source.read_text(encoding="utf-8") == "def answer():\n    return 1\n"
    assert cycle["applied"] is False
    assert cycle["status"] == "internal_patch_held_or_rolled_back"
    assert cycle["apply_evidence"]["status"] == "rolled_back_tests_failed"
    assert cycle["apply_evidence"]["rollback"]["ok"] is True


def test_pre_apply_council_hold_prevents_code_mutation(tmp_path: Path, monkeypatch) -> None:
    source = _source(tmp_path)
    resolver = PatchResolver(council_hold=True)
    workforce = provision_agent_company_brain_fabric(resolver)
    controller = _controller(tmp_path, monkeypatch)

    with pytest.raises(InternalPatchHold, match="pre_apply_council_held"):
        run_internal_patch_cycle(
            root=tmp_path,
            request=_request(tmp_path),
            workforce=workforce,
            controller=controller,
        )

    assert source.read_text(encoding="utf-8") == "def answer():\n    return 1\n"
    assert resolver.prompt_call_count == 99
    assert controller.status()["pending_count"] == 0
    assert controller.status()["recent_reviews"] == []


def test_malformed_accepted_council_cannot_approve_or_mutate(tmp_path: Path, monkeypatch) -> None:
    source = _source(tmp_path)
    resolver = PatchResolver()
    workforce = provision_agent_company_brain_fabric(resolver)
    controller = _controller(tmp_path, monkeypatch)
    deliberate = workforce.deliberate_coding_goal

    def malformed_council(prompt: str, **kwargs: Any) -> dict[str, Any]:
        result = deliberate(prompt, **kwargs)
        if kwargs.get("require_accept"):
            result["decisions"][0]["role"] = "Unapproved Role"
        return result

    monkeypatch.setattr(workforce, "deliberate_coding_goal", malformed_council)

    with pytest.raises(InternalPatchHold, match="pre_apply_council_held"):
        run_internal_patch_cycle(
            root=tmp_path,
            request=_request(tmp_path),
            workforce=workforce,
            controller=controller,
        )

    assert source.read_text(encoding="utf-8") == "def answer():\n    return 1\n"
    assert controller.status()["pending_count"] == 0
    assert controller.status()["recent_reviews"] == []


@pytest.mark.parametrize(
    "patch_text,reason",
    [
        ("This is not a diff", "model_response_did_not_contain_unified_diff"),
        (
            "--- a/other.py\n+++ b/other.py\n@@ -1 +1 @@\n-old\n+new\n",
            "patch_target_mismatch",
        ),
    ],
)
def test_malformed_or_cross_target_model_output_is_held(
    tmp_path: Path,
    monkeypatch,
    patch_text: str,
    reason: str,
) -> None:
    source = _source(tmp_path)
    workforce = provision_agent_company_brain_fabric(PatchResolver(patch_text))

    with pytest.raises(InternalPatchHold, match=reason):
        run_internal_patch_cycle(
            root=tmp_path,
            request=_request(tmp_path),
            workforce=workforce,
            controller=_controller(tmp_path, monkeypatch),
        )

    assert source.read_text(encoding="utf-8") == "def answer():\n    return 1\n"


def test_source_hash_drift_holds_before_any_model_call(tmp_path: Path, monkeypatch) -> None:
    source = _source(tmp_path)
    request = _request(tmp_path)
    source.write_text("def answer():\n    return 9\n", encoding="utf-8")
    resolver = PatchResolver()
    workforce = provision_internal_coding_workforce(resolver)

    with pytest.raises(InternalPatchHold, match="source_changed_since_request"):
        run_internal_patch_cycle(
            root=tmp_path,
            request=request,
            workforce=workforce,
            controller=_controller(tmp_path, monkeypatch),
        )

    assert resolver.prompt_call_count == 0
    assert source.read_text(encoding="utf-8") == "def answer():\n    return 9\n"


def test_secret_bearing_source_is_never_sent_to_model(tmp_path: Path, monkeypatch) -> None:
    source = _source(tmp_path, 'API_SECRET = "never-send-this-value"\n')
    resolver = PatchResolver()
    workforce = provision_internal_coding_workforce(resolver)

    with pytest.raises(InternalPatchHold, match="source_secret_scan_failed_before_model"):
        run_internal_patch_cycle(
            root=tmp_path,
            request=_request(tmp_path),
            workforce=workforce,
            controller=_controller(tmp_path, monkeypatch),
        )

    assert resolver.prompt_call_count == 0
    assert source.read_text(encoding="utf-8") == 'API_SECRET = "never-send-this-value"\n'


def test_unready_brain_fabric_holds_without_model_or_patch(tmp_path: Path, monkeypatch) -> None:
    source = _source(tmp_path)
    resolver = PatchResolver(ready=False)
    workforce = provision_agent_company_brain_fabric(resolver)

    with pytest.raises(InternalPatchHold, match="full_agent_company_brain_fabric_required"):
        run_internal_patch_cycle(
            root=tmp_path,
            request=_request(tmp_path),
            workforce=workforce,
            controller=_controller(tmp_path, monkeypatch),
        )

    assert resolver.prompt_call_count == 0
    assert source.read_text(encoding="utf-8") == "def answer():\n    return 1\n"


@pytest.mark.parametrize(
    "target",
    ["../outside.py", "/absolute.py", ".env", "config/credentials.py"],
)
def test_authoring_request_rejects_escape_and_authority_paths(tmp_path: Path, target: str) -> None:
    _source(tmp_path)
    with pytest.raises(InternalPatchHold):
        build_patch_request(
            root=tmp_path,
            goal="unsafe target",
            target_path=target,
            test_commands=[[sys.executable, "-c", "pass"]],
        )
