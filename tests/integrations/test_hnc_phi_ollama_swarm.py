from __future__ import annotations

from types import SimpleNamespace

from aureon.integrations.ollama.hnc_phi_swarm import (
    HNCPhiOllamaSwarm,
    _parse_json_object,
    build_phi_swarm_plan,
)


class _Bridge:
    def __init__(self, model):
        self.model = model

    def chat(self, messages, model=None, format=None, options=None):
        if format:
            content = '{"consensus":"repair the bus","validation":["focused"],"rollback":"reverse patch"}'
        else:
            content = f"Evidence-backed response from {model}."
        return {"message": {"content": content}, "eval_count": 10, "prompt_eval_count": 20}


class _Switchboard:
    models = ["general", "architect", "coder", "challenger", "flash"]

    def snapshot(self):
        return {"reachable": True, "catalog_size": len(self.models), "catalog": self.models}

    def rank(self, lane, limit=None, preferred="", exclude=(), force_refresh=False):
        excluded = {item.lower() for item in exclude}
        order = {
            "general": ["general", "flash", "architect"],
            "architecture": ["architect", "general"],
            "coding": ["coder", "architect"],
            "self_evolution": ["challenger", "coder"],
            "fast": ["flash", "general"],
        }[lane]
        if preferred in self.models:
            order = [preferred] + [item for item in order if item != preferred]
        selected = [item for item in order if item.lower() not in excluded]
        if limit is not None:
            selected = selected[:limit]
        return [
            SimpleNamespace(model=item, source="ranked_live_catalog", lane=lane)
            for item in selected
        ]

    def bridge_for(self, lane, preferred=""):
        selection = self.rank(lane, limit=1, preferred=preferred)[0]
        return _Bridge(selection.model), selection


def _flow(name="expand"):
    return {
        "flow": name,
        "gamma": 0.8,
        "minimum_review_cycles": 1,
        "required_test_layers": ["focused", "integration", "regression"],
    }


def test_phi_plan_uses_bounded_fibonacci_sized_fanout():
    assert build_phi_swarm_plan(_flow("expand"), catalog_size=10)["worker_count"] == 5
    assert build_phi_swarm_plan(_flow("steady"), catalog_size=10)["worker_count"] == 3
    assert build_phi_swarm_plan(_flow("observe"), catalog_size=10)["worker_count"] == 2
    repair = build_phi_swarm_plan(_flow("repair"), catalog_size=10)
    assert repair["worker_count"] == 3
    assert repair["internal_blocking"] is False


def test_swarm_normalizes_fenced_json():
    assert _parse_json_object('preface\n```json\n{"ok": true}\n```') == {"ok": True}


def test_swarm_uses_research_distinct_models_and_synthesis(tmp_path):
    swarm = HNCPhiOllamaSwarm(
        repo_root=tmp_path,
        switchboard=_Switchboard(),
        research_provider=lambda query, top_k: [
            {"doc_id": "docs/HNC.md", "paragraph_idx": 1, "text": "HNC evidence"}
        ],
    )

    report = swarm.run("connect the organism", _flow("expand"))

    assert report["ok"] is True
    assert report["summary"]["successful_worker_count"] == 5
    assert report["summary"]["distinct_worker_models"] == 5
    assert report["summary"]["api_call_count"] == 6
    assert report["summary"]["credential_values_exposed"] is False
    assert report["synthesis"]["answer"]["consensus"] == "repair the bus"
