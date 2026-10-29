"""One helper function per package. A helper call is not that layer's cognition. No new formulas."""

from __future__ import annotations

import tempfile
from datetime import date
from pathlib import Path
from typing import Any

from aureon_public.quiet import quiet
from aureon_public.tools import _dumps as _public_dumps
from aureon_public.tools import _finite


def _dumps(payload: dict[str, Any]) -> str:
    label = payload.get("label")
    if isinstance(label, str) and not label.startswith("helper."):
        payload = dict(payload)
        payload["label"] = "helper. " + label
    return _public_dumps(payload)

# package, kind, reason. kind is the tool name or "excluded".
UPDATES: tuple[tuple[str, str, str], ...] = (
    ("alignment", "alignment_consonance", "consonance_score. No pillar singleton."),
    ("analytics", "analytics_fear_greed", "derive_fear_greed on a supplied series. No backtest run."),
    ("appliance", "appliance_sha256", "sha256_file on a temp file that is deleted. The repo is not hashed."),
    ("approval", "approval_subject_line", "subject_line only. Owner address is not read."),
    ("atn", "excluded", "Public functions fetch earthquakes, flares, or prices. Not called."),
    ("briefing", "briefing_severity", "severity_rank. The brief assembler and pytest runner are not called."),
    ("cognition", "cognition_logic_flow", "compute_logic_flow on an in-memory bus. The report writer is not called."),
    ("command_centers", "excluded", "Entry points launch UIs or read API-key status. Not called."),
    ("conversion", "excluded", "The conversion hub takes capital and is not a pure read."),
    ("data_feeds", "data_feed_parse_tick", "parse_binance_tick on one dict. No socket is opened."),
    ("decoders", "decoder_haversine", "haversine only. Decoders are not started."),
    ("gates", "gates_reading", "is_human_held and ungrounded_nodes. The benchmark writer is not called."),
    ("generated", "excluded", "Generated trees stay uncalled."),
    ("governance", "governance_seasonal_gate", "seasonal_gate_for_date. Live authorization is not issued."),
    ("grants", "grants_breath_interval", "breath_interval only. Dossiers are not read."),
    ("identity", "excluded", "read_identity can load personal files. Not called."),
    ("inhouse_ai", "excluded", "The tool registry can dispatch. Not re-exported."),
    ("integrations", "integrations_phi_plan", "build_phi_swarm_plan. No model is called."),
    ("intelligence", "intelligence_resonance", "calculate_harmonic_resonance. Trading permission is not called."),
    ("miner", "excluded", "The only public function constructs a bridge. Not called."),
    ("monitors", "excluded", "aureon_live_monitor exits on import without aiohttp, and the wave monitor sets LIVE=1. Not called."),
    ("observability", "observability_redact", "redact_observability_value. Events are not emitted."),
    ("observer", "observer_kp_sample", "parse_kp_file of the committed Kp file, one sample. No download."),
    ("plumber", "plumber_sha256", "sha256_hex. No key is generated."),
    ("portals", "portals_html_to_text", "html_to_text. Dashboards are not fetched."),
    ("queen", "queen_zpe_ground", "compute_zpe_ground. Queen phase and order gates are not called."),
    ("s51", "s51_summarize_receipts", "summarize_compounding with no receipts. The sim is not run."),
    ("search", "search_summarize_text", "summarize_text. Online fetch is not called."),
    ("simulation", "simulation_hz_to_rgb", "hz_to_rgb. Simulations are not run."),
    ("swarm", "swarm_voice_for_gamma", "voice_for_gamma. The council is not convened."),
    ("swarm_motion", "excluded", "The only public function constructs the hive. Not called."),
    ("vault", "vault_count_words", "count_words. Key stores and persona files are not read."),
)


def _apply() -> None:
    from aureon_public.layers import PACKAGES

    by_name = {row["package"]: row for row in PACKAGES}
    for package, kind, reason in UPDATES:
        row = by_name[package]
        row["kind"] = kind
        row["reason"] = reason if reason.startswith("Helper only.") else "Helper only. " + reason


_apply()


def _missing(name: str) -> str:
    return _dumps(
        {
            "provenance": "cited",
            "reason": f"{name} is missing",
            "status": "unavailable",
        }
    )


@quiet
def alignment_consonance(ratio: float = 1.0) -> str:
    """alignment.harmonic_resonance.consonance_score. Provenance: inferred.

    Args:
        ratio: Frequency ratio. Non-positive is the function's own zero. Label: cited, consonance_score.
    """

    number = _finite(ratio)
    if number is None:
        return _missing("ratio")
    from aureon.alignment.harmonic_resonance import consonance_score

    return _dumps(
        {
            "label": "inferred. consonance_score.",
            "provenance": "inferred",
            "score": float(consonance_score(number)),
            "status": "inferred",
        }
    )


@quiet
def analytics_fear_greed() -> str:
    """analytics.backtest_sentiment_oracle.derive_fear_greed on a 40-step series. Provenance: inferred.

    No backtest is run. Trade readiness: HOLD.

    Args:
        none: The series is a fixed 40-step fixture ramp, not market data. Label: inferred.
    """

    from aureon.analytics.backtest_sentiment_oracle import derive_fear_greed

    closes = [100.0 + index for index in range(40)]
    volumes = [1.0 for _ in range(40)]
    result = derive_fear_greed(closes, volumes, 39)
    result["label"] = "The series is a fixed 40-step fixture ramp, not market data."
    result["provenance"] = "inferred"
    result["status"] = "inferred"
    result["trade_readiness"] = "HOLD"
    return _dumps(result)


@quiet
def appliance_sha256() -> str:
    """appliance.build_pipeline.sha256_file on a temp file that is deleted. Provenance: cited.

    Args:
        none: The bytes are written under the system temp directory and removed. Label: cited, sha256_file.
    """

    from aureon.appliance.build_pipeline import sha256_file

    handle = tempfile.NamedTemporaryFile(prefix="aureon-public-sha-", delete=False)
    path = Path(handle.name)
    try:
        handle.write(b"aureon-public")
        handle.close()
        digest = sha256_file(path)
    finally:
        path.unlink(missing_ok=True)
    return _dumps(
        {
            "label": "cited. sha256_file on a deleted temp file.",
            "provenance": "cited",
            "sha256": digest,
            "status": "cited",
        }
    )


@quiet
def approval_subject_line(action: str = "status") -> str:
    """approval.compose.subject_line. Provenance: cited. The owner address is not read.

    Args:
        action: Title text. Label: cited, subject_line.
    """

    from aureon.approval.compose import subject_line

    return _dumps(
        {
            "label": "cited. subject_line. No message is sent.",
            "provenance": "cited",
            "status": "cited",
            "subject": subject_line(action or "status"),
        }
    )


@quiet
def briefing_severity(severity: str = "high") -> str:
    """briefing.schemas.severity_rank. Provenance: cited. The assembler is not called.

    Args:
        severity: Rank label. Label: cited, severity_rank.
    """

    from aureon.briefing.schemas import severity_rank

    return _dumps(
        {
            "label": "cited. severity_rank.",
            "provenance": "cited",
            "rank": int(severity_rank(severity)),
            "status": "cited",
        }
    )


@quiet
def cognition_logic_flow() -> str:
    """cognition.logic_flow.compute_logic_flow. Provenance: inferred.

    The bus is in memory. write_logic_flow_report is not called. Trade readiness: HOLD.

    Args:
        none: The function's own default seed score is used. Label: cited, compute_logic_flow.
    """

    from aureon.cognition.logic_flow import compute_logic_flow

    report = compute_logic_flow().to_dict()
    report["label"] = "inferred. compute_logic_flow. The report file was not written."
    report["provenance"] = "inferred"
    report["status"] = "inferred"
    report["trade_readiness"] = "HOLD"
    return _dumps(report)


@quiet
def data_feed_parse_tick() -> str:
    """data_feeds.unified_ws_feed.parse_binance_tick on one dict. Provenance: inferred.

    One fixture tick, not market data. No socket was opened. Trade readiness: HOLD.

    Args:
        none: One fixture tick, not market data. No socket was opened. Label: inferred.
    """

    from aureon.data_feeds.unified_ws_feed import parse_binance_tick

    tick = parse_binance_tick(
        {"s": "BTCUSDT", "b": "1", "a": "2", "c": "1.5", "v": "3", "P": "0", "E": 1},
        received_at=1.0,
    )
    body = tick.__dict__ if tick is not None and hasattr(tick, "__dict__") else {"tick": None}
    body["label"] = "One fixture tick, not market data. No socket was opened."
    body["provenance"] = "inferred"
    body["status"] = "inferred" if tick is not None else "unavailable"
    body["trade_readiness"] = "HOLD"
    return _dumps(body)


@quiet
def decoder_haversine() -> str:
    """decoders.grail_convergence.haversine. Provenance: inferred.

    Args:
        none: The two points are 0,0 and 0,1. Label: inferred.
    """

    from aureon.decoders.grail_convergence import haversine

    return _dumps(
        {
            "kilometres": float(haversine(0.0, 0.0, 0.0, 1.0)),
            "label": "inferred. haversine.",
            "provenance": "inferred",
            "status": "inferred",
        }
    )


@quiet
def gates_reading(action: str = "draft") -> str:
    """gates.switchboard.is_human_held and gates.panel.ungrounded_nodes. Provenance: cited.

    The benchmark writer is not called. Auris panel vote is not called. The nine-node list is the ungrounded-node return when no slice is grounded.

    Args:
        action: Text passed to is_human_held. Label: cited, is_human_held.
    """

    from aureon.gates.panel import ungrounded_nodes
    from aureon.gates.switchboard import is_human_held

    return _dumps(
        {
            "human_held": bool(is_human_held(action)),
            "label": "cited. is_human_held and ungrounded_nodes. The panel was not convened.",
            "provenance": "cited",
            "status": "cited",
            "ungrounded_nodes": list(ungrounded_nodes(frozenset())),
            "which_auris": "Nine-node names from NODE_SLICE via ungrounded_nodes. Not the conjecture, not the persona, not the coherence evaluator.",
        }
    )


@quiet
def governance_seasonal_gate() -> str:
    """governance.celtic_voice_bank.seasonal_gate_for_date. Provenance: cited.

    Live authorization is not issued.

    Args:
        none: The date is 2026-01-15. Label: cited, seasonal_gate_for_date.
    """

    from aureon.governance.celtic_voice_bank import seasonal_gate_for_date

    return _dumps(
        {
            "gate": seasonal_gate_for_date(date(2026, 1, 15)),
            "label": "cited. seasonal_gate_for_date.",
            "provenance": "cited",
            "status": "cited",
        }
    )


@quiet
def grants_breath_interval() -> str:
    """grants.daemon.breath_interval. Provenance: cited. Dossiers are not read.

    Args:
        none: urgency is None, which the function documents as its slowest interval. Label: cited, breath_interval.
    """

    from aureon.grants.daemon import breath_interval

    return _dumps(
        {
            "interval_s": float(breath_interval(None)),
            "label": "cited. breath_interval. No dossier was read.",
            "provenance": "cited",
            "status": "cited",
        }
    )


@quiet
def integrations_phi_plan() -> str:
    """integrations.ollama.hnc_phi_swarm.build_phi_swarm_plan. Provenance: inferred.

    No model is called.

    Args:
        none: flow is observe and catalog_size is 2. Label: inferred.
    """

    from aureon.integrations.ollama.hnc_phi_swarm import build_phi_swarm_plan

    plan = build_phi_swarm_plan({"flow": "observe"}, catalog_size=2, max_total_calls=4)
    plan["label"] = "inferred. build_phi_swarm_plan. No model was called."
    plan["provenance"] = "inferred"
    plan["status"] = "inferred"
    return _dumps(plan)


@quiet
def intelligence_resonance() -> str:
    """intelligence.aureon_advanced_intelligence.calculate_harmonic_resonance. Provenance: inferred.

    Trading permission is not called.

    Args:
        none: The two frequencies are 100 and 200. Label: inferred.
    """

    from aureon.intelligence.aureon_advanced_intelligence import calculate_harmonic_resonance

    return _dumps(
        {
            "label": "inferred. calculate_harmonic_resonance.",
            "provenance": "inferred",
            "resonance": float(calculate_harmonic_resonance(100.0, 200.0)),
            "status": "inferred",
            "trade_readiness": "HOLD",
        }
    )


@quiet
def observability_redact() -> str:
    """observability.runtime.redact_observability_value. Provenance: cited. No event is emitted.

    Args:
        none: The value is a short string with no secret. Label: cited, redact_observability_value.
    """

    from aureon.observability.runtime import redact_observability_value

    return _dumps(
        {
            "label": "cited. redact_observability_value.",
            "provenance": "cited",
            "redacted": redact_observability_value("public-note"),
            "status": "cited",
        }
    )


@quiet
def observer_kp_sample() -> str:
    """observer.historical_backtest.parse_kp_file, one sample. Provenance: cited or unavailable.

    The committed Kp file is read when it is present. Nothing is downloaded. Schumann f0: null. HOLD.

    Args:
        none: start_year 2024 and max_samples 1. Label: cited, parse_kp_file.
    """

    from aureon.observer.historical_backtest import DEFAULT_KP_PATH, parse_kp_file

    if not DEFAULT_KP_PATH.is_file():
        return _dumps(
            {
                "label": "cited. The committed Kp file is not in this tree.",
                "provenance": "cited",
                "reason": "Kp file missing",
                "schumann_f0": "null. HOLD",
                "status": "unavailable",
            }
        )
    samples = parse_kp_file(DEFAULT_KP_PATH, start_year=2024, max_samples=1)
    first = samples[0] if samples else None
    return _dumps(
        {
            "count": len(samples),
            "kp": None if first is None else float(first.kp),
            "label": "cited. parse_kp_file, one sample. Not a Schumann measurement.",
            "provenance": "cited",
            "schumann_f0": "null. HOLD",
            "status": "cited" if first is not None else "unavailable",
        }
    )


@quiet
def plumber_sha256() -> str:
    """plumber.crypto.sha256_hex. Provenance: cited. No key is generated.

    Args:
        none: The text is aureon-public. Label: cited, sha256_hex.
    """

    from aureon.plumber.crypto import sha256_hex

    return _dumps(
        {
            "label": "cited. sha256_hex. No key was generated.",
            "provenance": "cited",
            "sha256": sha256_hex("aureon-public"),
            "status": "cited",
        }
    )


@quiet
def portals_html_to_text() -> str:
    """portals.ifs.html_to_text. Provenance: cited. No dashboard is fetched.

    Args:
        none: The HTML is a one-line fixture. Label: cited, html_to_text.
    """

    from aureon.portals.ifs import html_to_text

    return _dumps(
        {
            "label": "cited. html_to_text.",
            "provenance": "cited",
            "status": "cited",
            "text": html_to_text("<p>hold</p>"),
        }
    )


@quiet
def queen_zpe_ground(lambda_t: float = 1.0) -> str:
    """queen.temporal_ground.compute_zpe_ground. Provenance: inferred.

    This is the queen math already in that module. The phase ladder and order gates are not called. The persona is not scored. Trade readiness: HOLD.

    Args:
        lambda_t: Field value. Label: cited, compute_zpe_ground.
    """

    number = _finite(lambda_t)
    if number is None:
        return _missing("lambda_t")
    from aureon.queen.temporal_ground import compute_zpe_ground

    body = compute_zpe_ground(number).to_dict()
    body["label"] = "inferred. compute_zpe_ground. Persona was not scored."
    body["provenance"] = "inferred"
    body["status"] = "inferred"
    body["trade_readiness"] = "HOLD"
    body["which_auris"] = "Not the conjecture, not the nine nodes, not the coherence evaluator, and not the persona."
    return _dumps(body)


@quiet
def s51_summarize_receipts() -> str:
    """s51.aureon_51_compound.summarize_compounding with no receipts. Provenance: cited.

    The sim is not run. Trade readiness: HOLD.

    Args:
        none: An empty receipt list. Label: cited, summarize_compounding.
    """

    from aureon.s51.aureon_51_compound import summarize_compounding

    body = summarize_compounding([])
    body["receipt_status"] = body.get("status")
    body["label"] = "cited. summarize_compounding with no receipts."
    body["provenance"] = "cited"
    body["status"] = "cited"
    body["trade_readiness"] = "HOLD"
    return _dumps(body)


@quiet
def search_summarize_text() -> str:
    """search.online_research_cinema.summarize_text. Provenance: cited. No URL is fetched.

    Args:
        none: One sentence and the topic hold. Label: cited, summarize_text.
    """

    from aureon.search.online_research_cinema import summarize_text

    return _dumps(
        {
            "label": "cited. summarize_text. No URL was fetched.",
            "provenance": "cited",
            "status": "cited",
            "summary": summarize_text("Hold the claim.", "hold"),
        }
    )


@quiet
def simulation_hz_to_rgb() -> str:
    """simulation.aureon_world_simulator.hz_to_rgb. Provenance: inferred. No simulation is run.

    Args:
        none: The frequency is 528. Label: inferred.
    """

    from aureon.simulation.aureon_world_simulator import hz_to_rgb

    red, green, blue = hz_to_rgb(528.0)
    return _dumps(
        {
            "blue": int(blue),
            "green": int(green),
            "label": "inferred. hz_to_rgb. No simulation was run.",
            "provenance": "inferred",
            "red": int(red),
            "status": "inferred",
        }
    )


@quiet
def swarm_voice_for_gamma(gamma: float = 0.5) -> str:
    """swarm.druidic_council.voice_for_gamma. Provenance: inferred. The council is not convened.

    Args:
        gamma: Coherence in 0 to 1. Label: cited, voice_for_gamma.
    """

    number = _finite(gamma)
    if number is None:
        return _missing("gamma")
    from aureon.swarm.druidic_council import voice_for_gamma

    try:
        band, weight = voice_for_gamma(number)
    except ValueError as exc:
        return _dumps(
            {
                "provenance": "cited",
                "reason": str(exc),
                "status": "unavailable",
            }
        )
    return _dumps(
        {
            "label": "inferred. voice_for_gamma. The council was not convened.",
            "provenance": "inferred",
            "status": "inferred",
            "voice_band": band,
            "voice_weight": float(weight),
        }
    )


@quiet
def vault_count_words() -> str:
    """vault.voice.document_artifact_skill.count_words. Provenance: cited.

    Key stores and persona files are not read.

    Args:
        none: The text is two words. Label: cited, count_words.
    """

    from aureon.vault.voice.document_artifact_skill import count_words

    return _dumps(
        {
            "count": int(count_words("two words")),
            "label": "cited. count_words. No vault file was read.",
            "provenance": "cited",
            "status": "cited",
        }
    )


TOOLS: list[Any] = [
    alignment_consonance,
    analytics_fear_greed,
    appliance_sha256,
    approval_subject_line,
    briefing_severity,
    cognition_logic_flow,
    data_feed_parse_tick,
    decoder_haversine,
    gates_reading,
    governance_seasonal_gate,
    grants_breath_interval,
    integrations_phi_plan,
    intelligence_resonance,
    observability_redact,
    observer_kp_sample,
    plumber_sha256,
    portals_html_to_text,
    queen_zpe_ground,
    s51_summarize_receipts,
    search_summarize_text,
    simulation_hz_to_rgb,
    swarm_voice_for_gamma,
    vault_count_words,
]
