"""Fallback answers must not claim facts they did not read.

When Ollama is down the self-questioning engine answers from local context
("fallback" mode). Those answers must not say the Ollama endpoint is
reachable when it was not, and must not print a missing count as 0.
"""
from aureon.autonomous.aureon_self_questioning_ai import SelfQuestioningAI


def _ai():
    return SelfQuestioningAI.__new__(SelfQuestioningAI)


def test_unreachable_ollama_is_not_reported_reachable():
    ans = _ai()._deterministic_answer("Which model should I use?", {}, "ollama_unavailable")
    assert "reachable but" not in ans
    assert "not reachable" in ans


def test_model_unavailable_still_reports_reachable_without_model():
    ans = _ai()._deterministic_answer("Which model should I use?", {}, "ollama_model_unavailable")
    assert "reachable but reports no chat model" in ans


def test_missing_mind_wiring_counts_are_unknown_not_zero():
    ctx = {"mind_wiring": {"counts": {"wired": 5}}}
    ans = _ai()._deterministic_answer("What is unwired?", ctx, "ollama_unavailable")
    assert "5 wired" in ans
    assert "unknown partial" in ans and "unknown broken" in ans
    assert "0 partial" not in ans


def test_missing_tool_count_is_not_zero():
    ans = _ai()._deterministic_answer("Which tool fits the goal?", {}, "ollama_unavailable")
    assert "; 0 registered" not in ans
    assert "an unknown number of registered" in ans


def test_missing_saas_inventory_counts_are_unknown():
    ctx = {"saas_product_inventory": {"status": "ok", "inventory": {"summary": {}}}}
    ans = _ai()._deterministic_answer("What does the saas frontend need?", ctx, "ollama_unavailable")
    assert "surfaces=unknown" in ans and "security_blockers=unknown" in ans
    assert "=0" not in ans
