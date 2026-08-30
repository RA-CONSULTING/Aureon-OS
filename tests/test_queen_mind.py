"""Focused proof for the single process-owned QueenMind."""

from __future__ import annotations

import ast
import hashlib
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import aureon.autonomous.aureon_internal_coding_workforce as workforce_module
import aureon.queen.queen_mind as mind_module
from aureon.autonomous.aureon_internal_coding_workforce import WorkReceipt
from aureon.queen.queen_mind import (
    QueenMind,
    bind_queen_mind,
    discover_queen_faculty_manifest,
    validate_faculty_signal_receipt,
    validate_queen_thought_envelope,
)

NOW = 1_786_579_200.0


def _write(path: Path, source: str = "def observe():\n    return None\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


def _manifest_root(tmp_path: Path) -> Path:
    _write(tmp_path / "aureon" / "miner" / "miner_brain.py")
    _write(tmp_path / "aureon" / "queen" / "queen_quantum.py")
    _write(tmp_path / "aureon" / "queen" / "knowledge_interpreter.py")
    _write(tmp_path / "aureon" / "queen" / "queen_metacognition.py")
    _write(
        tmp_path / "aureon" / "queen" / "queen_legacy_trader.py",
        "def act(client):\n    return client.place_market_order('XBTUSD')\n",
    )
    _write(
        tmp_path / "imports" / "snapshot" / "queen_ignored.py",
        "raise RuntimeError('must not import')\n",
    )
    return tmp_path


class _Acquisition:
    def load_governance_acquisition(self) -> dict[str, Any]:
        return {
            "provider_receipt_ids": ["provider:one"],
            "provider_moment_digest": "a" * 64,
            "provider_source_timestamp": str(NOW),
        }


class _Composition:
    def __init__(self, *, ready: bool = True) -> None:
        self.ready = ready
        self.governance = SimpleNamespace(
            council_receipt_supplier=object(),
            crown_receipt_supplier=object(),
            acquisition_supplier=_Acquisition(),
        )

    def status(self) -> dict[str, Any]:
        return {"status": "ready" if self.ready else "hold"}


class _Workforce:
    def __init__(self) -> None:
        self.calls = 0

    def process_id_for_role(self, role: str) -> str:
        assert role == "CEO Goal Steward"
        return "agent-company:ceo-goal-steward"

    def decide(self, **kwargs: Any):
        self.calls += 1
        assert kwargs["stage"] == "queen_mind_thought"
        assert kwargs["work_kind"] == "queen_sentient_thought"
        answer = "One coherent, source-aware answer."
        receipt = WorkReceipt(
            schema_version=workforce_module.WORK_SCHEMA_VERSION,
            sequence=1,
            actor_class=workforce_module.INTERNAL_ACTOR,
            actor_id="aureon:agent:CEO Goal Steward",
            process_id=kwargs["process_id"],
            stage=kwargs["stage"],
            work_kind=kwargs["work_kind"],
            input_digest=hashlib.sha256(kwargs["prompt"].encode("utf-8")).hexdigest(),
            output_digest=hashlib.sha256(answer.encode("utf-8")).hexdigest(),
            brain_passport_id="brain:test-queen-mind",
            completed_at=NOW,
            action_eligible=False,
            economic_eligible=False,
            receipt_id="",
            thought_path_receipt_id=(
                workforce_module.TRUTH_GATED_THOUGHT_RECEIPT_PREFIX + "test"
            ),
        )
        receipt = replace(
            receipt,
            receipt_id=(
                "work:"
                + workforce_module._digest(  # noqa: SLF001 - exact receipt fixture
                    workforce_module._work_causal_payload(receipt)  # noqa: SLF001
                )
            ),
        )
        return answer, receipt


class _Conscience:
    def __init__(self) -> None:
        self.calls = 0

    def ask_why(self, action: str, context=None):
        self.calls += 1
        assert "QueenMind" in action
        assert context["observer_context_digest"]
        return SimpleNamespace(verdict=SimpleNamespace(name="APPROVED"))


class _Bus:
    def __init__(self) -> None:
        self.subscriptions: list[tuple[str, Any]] = []

    def subscribe(self, topic: str, handler: Any) -> None:
        self.subscriptions.append((topic, handler))

    def unsubscribe(self, topic: str, handler: Any) -> bool:
        self.subscriptions.remove((topic, handler))
        return True

    def publish(self, _thought: Any) -> None:
        return None


def _mind(tmp_path: Path, *, ready: bool = True):
    workforce = _Workforce()
    conscience = _Conscience()
    mind = bind_queen_mind(
        composition=_Composition(ready=ready),
        workforce=workforce,
        conscience=conscience,
        root=_manifest_root(tmp_path),
        clock=lambda: NOW,
    )
    return mind, workforce, conscience


def _seat_required_roles(mind: QueenMind) -> dict[str, str]:
    modules = {
        item.role: item.module_name
        for item in mind.manifest.faculties
        if item.role in {"knowledge", "metacognition", "miner", "quantum"}
    }
    for role, module in sorted(modules.items()):
        receipt = mind.submit_faculty_signal(
            module_name=module,
            signal={"role": role, "observation": f"{role} evidence"},
            source_receipt_ids=[f"source:{role}"],
        )
        validate_faculty_signal_receipt(receipt)
    return modules


def test_manifest_seats_required_brains_without_importing(tmp_path: Path) -> None:
    root = _manifest_root(tmp_path)

    first = discover_queen_faculty_manifest(root)
    second = discover_queen_faculty_manifest(root)
    report = first.report()

    assert first.to_dict() == second.to_dict()
    assert set(report["required_roles"]) == {
        "knowledge",
        "metacognition",
        "miner",
        "quantum",
    }
    assert all(report["roles"][role] >= 1 for role in report["required_roles"])
    assert report["effects"]["legacy_authority_capable"] == 1
    assert all(not item.source_file.startswith("imports/") for item in first.faculties)
    assert report["action_eligible"] is False
    assert report["economic_mutation"] is False


def test_constructor_is_factory_only(tmp_path: Path) -> None:
    manifest = discover_queen_faculty_manifest(_manifest_root(tmp_path))

    with pytest.raises(TypeError, match="use_bind_queen_mind"):
        QueenMind(
            _factory_token=object(),
            composition=_Composition(),
            workforce=_Workforce(),
            conscience=_Conscience(),
            manifest=manifest,
            clock=lambda: NOW,
        )


def test_missing_required_brain_holds_before_cloud_or_council(tmp_path: Path) -> None:
    mind, workforce, conscience = _mind(tmp_path)
    miner = next(
        item for item in mind.manifest.faculties if item.role == "miner"
    )
    mind.submit_faculty_signal(
        module_name=miner.module_name,
        signal={"observation": "miner only"},
    )

    result = mind.think_once("incomplete inputs")

    assert result.envelope["decision"] == "HOLD"
    assert result.envelope["reason"] == "complete_cognitive_role_inputs_required"
    assert result.envelope["action_proposal"] is None
    assert workforce.calls == conscience.calls == 0


def test_complete_roles_use_one_cloud_thought_and_dual_key_accept(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mind, workforce, conscience = _mind(tmp_path)
    modules = _seat_required_roles(mind)
    proposal = mind.submit_action_proposal(
        module_name=modules["quantum"],
        proposal={"intent": "observe_market", "symbol": "XBTGBP"},
        source_receipt_ids=["provider:market"],
    )
    gate_calls = []

    def accept(**kwargs: Any) -> dict[str, Any]:
        gate_calls.append(kwargs)
        return {
            "decision": "ACCEPT",
            "reason": None,
            "receipt_id": "dual-key:queen-mind",
        }

    monkeypatch.setattr(mind_module, "evaluate_cognition_governance", accept)

    result = mind.think_once("phi-squared cycle")
    envelope = validate_queen_thought_envelope(result.envelope)

    assert proposal["action_eligible"] is False
    assert workforce.calls == conscience.calls == len(gate_calls) == 1
    assert envelope["stage"] == "APPROVED"
    assert envelope["decision"] == "ACCEPT"
    assert envelope["thought_path_receipt_id"].startswith(
        workforce_module.TRUTH_GATED_THOUGHT_RECEIPT_PREFIX
    )
    assert envelope["action_proposal"]["intent"] == "observe_market"
    assert envelope["action_dispatch_status"] == "awaiting_guarded_route"
    assert envelope["action_eligible"] is False
    assert envelope["economic_mutation"] is False


def test_unvalidated_cloud_work_receipt_holds_before_conscience(
    tmp_path: Path,
) -> None:
    mind, workforce, conscience = _mind(tmp_path)
    _seat_required_roles(mind)
    workforce.decide = lambda **_kwargs: (  # type: ignore[method-assign]
        "Unbound answer.",
        SimpleNamespace(
            to_dict=lambda: {
                "receipt_id": "work:self-attested",
                "thought_path_receipt_id": "thought:10-9-1:truth-gated:fake",
            }
        ),
    )

    envelope = mind.think_once("forged work receipt").envelope

    assert envelope["decision"] == "HOLD"
    assert envelope["reason"] == "truth_gated_cloud_brain_unavailable"
    assert conscience.calls == 0


def test_dual_key_hold_never_releases_action_proposal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mind, _, _ = _mind(tmp_path)
    modules = _seat_required_roles(mind)
    mind.submit_action_proposal(
        module_name=modules["metacognition"],
        proposal={"intent": "submit_goal", "goal": "inspect evidence"},
    )
    monkeypatch.setattr(
        mind_module,
        "evaluate_cognition_governance",
        lambda **_kwargs: {
            "decision": "HOLD",
            "reason": "council_quorum_required",
            "receipt_id": "dual-key:hold",
        },
    )

    envelope = mind.think_once("hold cycle").envelope

    assert envelope["stage"] == "HELD"
    assert envelope["action_proposal"] is None
    assert envelope["action_dispatch_status"] == "not_requested"
    assert envelope["action_eligible"] is False


def test_composition_hold_prevents_cloud_and_conscience(tmp_path: Path) -> None:
    mind, workforce, conscience = _mind(tmp_path, ready=False)
    _seat_required_roles(mind)

    result = mind.think_once("composition hold")

    assert result.envelope["reason"] == "canonical_organism_composition_not_ready"
    assert workforce.calls == conscience.calls == 0


def test_start_and_stop_release_wildcard_bus_subscription(tmp_path: Path) -> None:
    bus = _Bus()
    mind = bind_queen_mind(
        composition=_Composition(),
        workforce=_Workforce(),
        conscience=_Conscience(),
        root=_manifest_root(tmp_path),
        bus=bus,
        clock=lambda: NOW,
        interval_s=0.01,
    )

    assert mind.start()["running"] is True
    assert len(bus.subscriptions) == 1
    assert bus.subscriptions[0][0] == "*"

    mind.stop()

    assert mind.status()["running"] is False
    assert bus.subscriptions == []


def test_legacy_queen_action_paths_are_proposal_only() -> None:
    targets = {
        Path("aureon/queen/queen_sentient_loop.py"): "_act",
        Path("aureon/queen/queen_quantum_cognition.py"): "autonomous_decision_cycle",
        Path("aureon/queen/queen_cognitive_action_planner.py"): "_synthesise_and_submit",
    }
    forbidden = {"autonomous_execute", "execute", "submit_goal"}
    found: list[tuple[str, str]] = []
    for path, method_name in targets.items():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        method = next(
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == method_name
        )
        for node in ast.walk(method):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in forbidden
            ):
                found.append((path.as_posix(), node.func.attr))

    assert found == []
