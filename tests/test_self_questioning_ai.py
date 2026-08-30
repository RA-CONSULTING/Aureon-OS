import json
import os

from aureon.autonomous.aureon_self_questioning_ai import SelfQuestioningAI
from aureon.core.aureon_thought_bus import ThoughtBus
from aureon.integrations.obsidian import ObsidianBridge


class FakeOllama:
    def __init__(self, reachable=True, payload=None, raw_text=None):
        self.reachable = reachable
        self.chat_model = "fake-self-model"
        self.calls = []
        self.raw_text = raw_text
        self.payload = payload or {
            "summary": "I checked myself safely.",
            "answers": [
                {
                    "question": "What needs attention?",
                    "answer": "Keep audit and memory loops alive.",
                    "evidence": ["fake evidence"],
                }
            ],
            "next_actions": [
                {
                    "title": "Write memory",
                    "action_type": "write_obsidian_note",
                    "priority": 1,
                    "risk": "low",
                    "requires_human": False,
                    "details": "Persist this cycle.",
                }
            ],
        }

    def health_check(self, max_age_s=5.0):
        return self.reachable

    def snapshot(self):
        return {
            "reachable": self.reachable,
            "base_url": "http://fake-ollama",
            "chat_model": self.chat_model,
            "models": [self.chat_model] if self.reachable else [],
            "running": [],
        }

    def chat(self, messages, model=None, system=None, format=None, options=None):
        self.calls.append(
            {
                "model": model,
                "messages": messages,
                "system": system,
                "format": format,
                "options": options,
            }
        )
        return {
            "model": model or self.chat_model,
            "message": {
                "role": "assistant",
                "content": self.raw_text if self.raw_text is not None else json.dumps(self.payload),
            },
            "done": True,
        }


def make_ai(tmp_path, fake_ollama):
    obsidian = ObsidianBridge(
        api_key="",
        vault_path=str(tmp_path / "vault"),
        prefer_filesystem=True,
    )
    bus = ThoughtBus(persist_path=str(tmp_path / "thoughts.jsonl"))
    return SelfQuestioningAI(
        repo_root=tmp_path,
        obsidian=obsidian,
        ollama=fake_ollama,
        thought_bus=bus,
        state_path=tmp_path / "cycles.jsonl",
        safe_mode=True,
    )


def test_self_questioning_cycle_uses_ollama_and_writes_obsidian(tmp_path):
    fake_ollama = FakeOllama(reachable=True)
    ai = make_ai(tmp_path, fake_ollama)

    cycle = ai.run_cycle(
        questions=["What needs attention?"],
        include_audit=False,
        include_self_scan=False,
    )

    assert cycle.answer_source == "ollama"
    assert fake_ollama.calls[0]["model"] == "fake-self-model"
    assert fake_ollama.calls[0]["options"]["num_predict"] <= 256
    assert cycle.note_path
    assert (tmp_path / "vault" / "autonomy" / "self_questioning_ai.md").exists()
    assert (tmp_path / "cycles.jsonl").exists()
    assert any(a.action_type == "write_obsidian_note" for a in cycle.next_actions)

    thoughts = ai.thought_bus.recall(topic_prefix="autonomy.self_question", limit=10)
    assert any(t["topic"] == "autonomy.self_question.ask" for t in thoughts)
    assert any(t["topic"] == "autonomy.self_question.answer" for t in thoughts)


def test_self_questioning_scales_json_budget_for_multiple_questions(tmp_path):
    fake_ollama = FakeOllama(reachable=True)
    ai = make_ai(tmp_path, fake_ollama)

    ai.run_cycle(
        questions=["one", "two", "three", "four"],
        include_audit=False,
        include_self_scan=False,
    )

    assert fake_ollama.calls[0]["options"]["num_predict"] == 2048
    assert fake_ollama.calls[0]["options"]["num_ctx"] >= 8192


def test_self_questioning_exposes_goal_capability_map_to_ollama_and_thoughtbus(tmp_path):
    audits = tmp_path / "docs" / "audits"
    audits.mkdir(parents=True)
    (audits / "aureon_repo_self_catalog.json").write_text(
        json.dumps(
            {
                "status": "catalog_complete",
                "summary": {
                    "cataloged_file_count": 3,
                    "domain_count": 2,
                    "subsystem_count": 2,
                    "file_kind_count": 2,
                    "secret_metadata_only_count": 1,
                    "coverage_policy": "test policy",
                },
                "domain_counts": {"autonomy": 2, "devops": 1},
                "subsystem_counts": {"autonomy_and_self_management": 2},
                "vault_memory": {"status": "written"},
                "labels": [
                    {
                        "path": "aureon/autonomous/demo.py",
                        "subsystem": "autonomy_and_self_management",
                        "file_kind": "python_source",
                        "organism_domain": "autonomy",
                        "llm_context": "demo context",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (audits / "aureon_capability_growth_loop.json").write_text(
        json.dumps(
            {
                "status": "growth_loop_working_with_improvement_queue",
                "summary": {
                    "iteration_count": 1,
                    "latest_gap_count": 2,
                    "latest_mean_score": 0.82,
                    "latest_registered_improvement_count": 1,
                    "contract_queue_persisted": True,
                },
                "iterations": [
                    {
                        "summary": {
                            "domain_count": 12,
                            "gap_count": 2,
                            "mean_score": 0.82,
                            "registered_improvement_count": 1,
                        },
                        "gaps": [{"id": "gap_accounting_compliance"}],
                    }
                ],
                "vault_memory": {"status": "written"},
            }
        ),
        encoding="utf-8",
    )
    (audits / "aureon_saas_system_inventory.json").write_text(
        json.dumps(
            {
                "status": "inventory_ready",
                "summary": {
                    "surface_count": 12,
                    "frontend_surface_count": 6,
                    "supabase_function_count": 3,
                    "security_blocker_count": 0,
                    "orphaned_frontend_count": 2,
                },
                "counts": {"by_domain": {"operator": 4}},
                "gaps": {"security_blockers": [], "uncalled_supabase_functions": []},
            }
        ),
        encoding="utf-8",
    )
    (audits / "aureon_frontend_unification_plan.json").write_text(
        json.dumps(
            {
                "status": "unification_plan_ready",
                "summary": {"screen_count": 7, "migration_action_count": 2, "security_blocker_count": 0},
                "canonical_screens": [{"id": "overview"}, {"id": "trading"}],
                "migration_actions": [{"id": "build_unified_shell"}],
                "safety_contract": {"human_observes_aureon_works": True},
            }
        ),
        encoding="utf-8",
    )
    fake_ollama = FakeOllama(reachable=True)
    ai = make_ai(tmp_path, fake_ollama)

    cycle = ai.run_cycle(
        questions=["How should I use all skills tools logic and code systems for this goal?"],
        include_audit=False,
        include_self_scan=False,
    )

    prompt = json.loads(fake_ollama.calls[0]["messages"][0]["content"])
    goal_map = prompt["context"]["goal_capability_map"]
    assert goal_map["directive_version"] == "goal-capability-v1"
    assert "tools" in goal_map["route_surfaces"]
    assert "contracts" in goal_map["route_surfaces"]
    assert "accounting" in goal_map["route_surfaces"]
    assert "self_catalog" in goal_map["route_surfaces"]
    assert prompt["context"]["repo_self_catalog"]["available"] is True
    assert prompt["context"]["repo_self_catalog"]["summary"]["cataloged_file_count"] == 3
    assert prompt["context"]["repo_self_catalog"]["sample_labels"][0]["llm_context"] == "demo context"
    assert prompt["context"]["capability_growth_loop"]["available"] is True
    assert prompt["context"]["capability_growth_loop"]["summary"]["latest_gap_count"] == 2
    assert prompt["context"]["saas_product_inventory"]["available"] is True
    assert prompt["context"]["saas_product_inventory"]["inventory"]["summary"]["surface_count"] == 12
    assert prompt["context"]["saas_product_inventory"]["unification_plan"]["summary"]["screen_count"] == 7
    assert prompt["context"]["contract_stack"]["contract_schema_version"] == "aureon-organism-contract-v1"
    assert "accounting" in prompt["context"]
    assert prompt["context"]["accounting"]["manual_filing_required"] is True
    assert goal_map["tool_registry"]["count"] >= 5
    assert cycle.context["goal_capability_map"]["tool_registry"]["count"] >= 5

    thoughts = ai.thought_bus.recall(topic_prefix="autonomy.goal", limit=10)
    assert any(t["topic"] == "autonomy.goal.directive" for t in thoughts)
    contract_thoughts = ai.thought_bus.recall(topic_prefix="organism.contract", limit=10)
    assert any(t["topic"] == "organism.contract.directive" for t in contract_thoughts)


def test_self_questioning_cycle_falls_back_when_ollama_offline(tmp_path):
    ai = make_ai(tmp_path, FakeOllama(reachable=False))

    cycle = ai.run_cycle(include_audit=False, include_self_scan=False)

    assert cycle.answer_source == "fallback"
    assert "Fallback self-questioning completed" in cycle.summary
    assert any("Ollama" in a.title or "Ollama" in a.details for a in cycle.next_actions)


def test_self_questioning_does_not_force_safe_env_during_live_boot(tmp_path, monkeypatch):
    monkeypatch.setenv("AUREON_AUDIT_MODE", "0")
    monkeypatch.setenv("AUREON_LIVE_TRADING", "1")
    monkeypatch.setenv("AUREON_DISABLE_REAL_ORDERS", "0")
    monkeypatch.setenv("DRY_RUN", "0")
    monkeypatch.setenv("LIVE", "1")

    ai = make_ai(tmp_path, FakeOllama(reachable=False))
    cycle = ai.run_cycle(include_audit=False, include_self_scan=False)

    assert cycle.answer_source == "fallback"
    assert "Why must I stop before any exchange mutation?" in cycle.questions
    assert cycle.context["real_orders_allowed"] is True
    assert os.environ["AUREON_LIVE_TRADING"] == "1"
    assert os.environ["AUREON_DISABLE_REAL_ORDERS"] == "0"


def test_self_questioning_blocks_live_order_suggestions(tmp_path):
    payload = {
        "summary": "Unsafe suggestion test.",
        "answers": [],
        "next_actions": [
            {
                "title": "Place real order",
                "action_type": "execute_trade",
                "priority": 1,
                "risk": "high",
                "requires_human": False,
                "details": "place order on Kraken live trade",
            }
        ],
    }
    ai = make_ai(tmp_path, FakeOllama(reachable=True, payload=payload))

    cycle = ai.run_cycle(include_audit=False, include_self_scan=False)

    assert cycle.next_actions[0].blocked is True
    assert cycle.next_actions[0].requires_human is True
    assert cycle.next_actions[0].action_type == "ask_human"


def test_self_questioning_uses_ollama_text_when_json_is_malformed(tmp_path):
    ai = make_ai(
        tmp_path,
        FakeOllama(
            reachable=True,
            raw_text="I should inspect dormant Queen links, write the finding to Obsidian, and avoid live orders.",
        ),
    )

    cycle = ai.run_cycle(
        questions=["What should I ask next?"],
        include_audit=False,
        include_self_scan=False,
    )

    assert cycle.answer_source == "ollama_text"
    assert "dormant Queen links" in cycle.answers[0]["answer"]
    assert cycle.next_actions
