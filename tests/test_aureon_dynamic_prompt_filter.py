import json
from pathlib import Path

from aureon.autonomous import aureon_dynamic_prompt_filter as prompt_filter
from aureon.inhouse_ai.llm_adapter import AureonBrainAdapter, AureonHybridAdapter, AureonLocalAdapter, LLMResponse


def _seed_research(root: Path) -> None:
    path = root / "docs/research/EMERGENT_COGNITION.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "# Emergent Cognition\n\n"
        "Gary Leckey research treats prompt flow as a human operator experience. "
        "The HNC and Auris systems should filter drift, preserve evidence, and keep "
        "small agent packets tied back to source-linked memory.",
        encoding="utf-8",
    )


def test_dynamic_prompt_filter_routes_and_publishes_source_packets(tmp_path, monkeypatch):
    _seed_research(tmp_path)
    monkeypatch.setattr(
        prompt_filter,
        "_meaning_block",
        lambda prompt: ({"direct_reply": None, "sources_consulted": ["test"]}, "Grounded knowledge: test"),
    )
    monkeypatch.setattr(prompt_filter, "_hnc_report", lambda prompt: {"available": True, "intent": {"route": "build"}})
    monkeypatch.setattr(prompt_filter, "_voice_context", lambda root: {"expression_profile_present": True})

    report = prompt_filter.build_dynamic_prompt_filter(
        [{"role": "user", "content": "Use Gary Leckey AI research to improve the coding prompt filter api_key=SHOULD_HIDE"}],
        system="Aureon coding cockpit",
        root=tmp_path,
        publish=True,
    )

    assert report["filter_mode"] == "clear_operator"
    assert report["lane"] in {"coding", "research"}
    assert report["task_family"] in {"coding", "research", "mixed"}
    assert report["source_packets"]
    assert report["source_packets"][0]["source_path"].endswith("EMERGENT_COGNITION.md")
    assert "SHOULD_HIDE" not in json.dumps(report)
    assert (tmp_path / "state/aureon_dynamic_prompt_filter_last_run.json").exists()
    assert (tmp_path / "frontend/public/aureon_dynamic_prompt_filter.json").exists()


def test_dynamic_prompt_filter_uses_operator_message_not_phi_context(tmp_path, monkeypatch):
    _seed_research(tmp_path)
    monkeypatch.setattr(prompt_filter, "_meaning_block", lambda prompt: ({}, ""))
    monkeypatch.setattr(prompt_filter, "_hnc_report", lambda prompt: {"available": True})
    monkeypatch.setattr(prompt_filter, "_voice_context", lambda root: {})

    wrapped = (
        "Operator message:\nhello my name is Gary Leckey\n\n"
        "Redacted dashboard context:\n{\"coding\":{\"status\":\"ready\"},\"symbol\":\"SOLUSDT\"}\n\n"
        "Compact Phi/Ollama/Aureon status:\n{\"backend\":\"aureon\"}"
    )

    report = prompt_filter.build_dynamic_prompt_filter(
        [{"role": "user", "content": wrapped}],
        system="Aureon coding cockpit",
        root=tmp_path,
        lane_hint="chat",
        publish=False,
    )

    assert report["lane"] == "chat"
    assert report["task_family"] == "conversation"
    assert report["user_intent"] == "hello my name is Gary Leckey"
    assert report["source_packets"] == []
    assert "SOLUSDT" not in report["user_intent"]


def test_dynamic_response_filter_redacts_and_holds_blocked_claim(tmp_path, monkeypatch):
    monkeypatch.setattr(
        prompt_filter,
        "write_dynamic_prompt_filter_report",
        lambda report, root=None: None,
    )
    report = {
        "schema_version": prompt_filter.SCHEMA_VERSION,
        "filter_mode": "clear_operator",
        "lane": "chat",
        "task_family": "conversation",
        "source_packets": [],
        "hnc_auris_report": {},
    }

    text, final = prompt_filter.apply_dynamic_response_filter(
        "I placed a live trade and your api_key=SHOULD_HIDE.",
        report,
        reply_source="test",
        root=tmp_path,
    )

    assert "SHOULD_HIDE" not in text
    assert final["handover_ready"] is False
    assert final["final_reply_source"] == "test"
    assert "auris_voice_filter" in final["hnc_auris_report"]


def test_hybrid_adapter_attaches_dynamic_filter_trace(monkeypatch):
    monkeypatch.setenv("AUREON_AUDIT_MODE", "1")
    monkeypatch.setenv("AUREON_LLM_ALLOW_HTTP_IN_AUDIT", "1")
    monkeypatch.setenv("AUREON_OLLAMA_CONTEXT_WEAVER", "0")

    def _load_offline_brain(self):
        self._brain = None
        self._brain_loaded = False

    monkeypatch.setattr(AureonBrainAdapter, "_load_brain", _load_offline_brain)
    # The suite runs with AUREON_LLM_OFFLINE=1, which (correctly) hard-disables
    # the local path regardless of the audit-allow flag. This test exercises
    # the LOCAL reply path with both health_check and prompt patched, so no
    # real HTTP can happen — clear the offline flags for this call only.
    monkeypatch.delenv("AUREON_LLM_OFFLINE", raising=False)
    monkeypatch.delenv("AUREON_DISABLE_LLM_HTTP", raising=False)
    monkeypatch.setattr(AureonLocalAdapter, "health_check", lambda self: True)
    monkeypatch.setattr(AureonBrainAdapter, "health_check", lambda self: False)

    def fake_build(messages, system="", lane_hint="", publish=True):
        return {
            "schema_version": prompt_filter.SCHEMA_VERSION,
            "filter_mode": "clear_operator",
            "lane": "chat",
            "task_family": "conversation",
            "meaning_resolver": {},
            "source_packets": [{"title": "Packet", "source_path": "docs/research/test.md"}],
            "hnc_auris_report": {},
        }

    def fake_apply(text, report, reply_source="", publish=True, root=None):
        next_report = dict(report)
        next_report["final_reply_source"] = reply_source
        next_report["handover_ready"] = True
        return text, next_report

    monkeypatch.setattr(prompt_filter, "build_dynamic_prompt_filter", fake_build)
    monkeypatch.setattr(prompt_filter, "apply_dynamic_response_filter", fake_apply)
    monkeypatch.setattr(
        AureonLocalAdapter,
        "prompt",
        lambda self, messages, system="", tools=None, max_tokens=4096, temperature=0.7, **kwargs: LLMResponse(
            text="single local answer",
            model="llama3:latest",
        ),
    )

    adapter = AureonHybridAdapter(model="llama3:latest")
    response = adapter.prompt([{"role": "user", "content": "hello"}], max_tokens=120)

    assert response.text == "single local answer"
    assert response.raw["dynamic_prompt_filter"]["filter_mode"] == "clear_operator"
    assert response.raw["dynamic_prompt_filter"]["final_reply_source"] == "ollama_cognitive_hybrid"


def test_brain_adapter_keeps_operator_chat_out_of_trading_json():
    adapter = AureonBrainAdapter()
    wrapped = (
        "Operator message:\nhello my name is Gary Leckey\n\n"
        "Redacted dashboard context:\n{\"screen\":\"console\",\"open_positions\":2,\"symbol\":\"SOLUSDT\"}\n\n"
        "Compact Phi/Ollama/Aureon status:\n{\"ok\":true}"
    )

    context = adapter._extract_context([{"role": "user", "content": wrapped}], system="Aureon Phi chat")
    response = adapter.prompt([{"role": "user", "content": wrapped}], system="Aureon Phi chat")

    assert context["query"] == "hello my name is Gary Leckey"
    assert context["symbols"] == []
    assert context["action"] is None
    assert "Gary Leckey" in response.text
    assert "trading signal" in response.text
    assert '"signal"' not in response.text
    assert "SOLUSDT" not in response.text

    capability = adapter.prompt(
        [
            {
                "role": "user",
                "content": (
                    "Operator message:\nwhat can you do\n\n"
                    "Redacted dashboard context:\n{\"screen\":\"console\",\"symbol\":\"SOLUSDT\"}\n\n"
                    "Compact Phi/Ollama/Aureon status:\n{\"ok\":true}"
                ),
            }
        ],
        system="Aureon Phi chat",
    )

    assert "local client-job organism" in capability.text
    assert '"signal"' not in capability.text
    assert "SOLUSDT" not in capability.text
