from __future__ import annotations

import base64
import copy
import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


GOOGLE_CLOUD = Path(__file__).parents[1]
UPSTREAM = GOOGLE_CLOUD.parents[1] / "aureon-os-upstream"
for path in (str(GOOGLE_CLOUD), str(UPSTREAM), str(GOOGLE_CLOUD / "trading-control")):
    if path not in sys.path:
        sys.path.insert(0, path)

import cloud_order_intent_bridge as bridge  # noqa: E402
from contract import (  # noqa: E402
    EXECUTOR_READINESS_SCHEMA,
    RECEIPT_READINESS_SCHEMA,
    build_periodic_readiness_statement,
    build_readiness_release_binding,
    canonical_bytes,
    digest,
    provider_readback_commitment_sha256,
    validate_intent,
)
from make_probe import build_probe  # noqa: E402


REVISION = "a" * 40


def iso(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, UTC).isoformat().replace("+00:00", "Z")


def authorization(now: float) -> dict:
    return {
        "active": True,
        "state": "active",
        "account_scope": "owner_cloud_account",
        "scope": list(bridge.TRADING_CONTROL_SCOPE),
        "authorized_at": now - 60,
        "expires_at": now + 3600,
        "ledger_event_sha256": "1" * 64,
    }


def execution_budget(now: float, *, revision=REVISION, insufficient=()) -> dict:
    sufficient = {"status": "sufficient", "allowance_usd": "5"}
    blocked = {"status": "insufficient", "allowance_usd": "0"}

    def quote(venue, asset):
        return dict(blocked if (venue, asset) in set(insufficient) else sufficient)

    observed = int((now - 20) * 1000)
    return {
        "schema": "aureon.cloud-trade-execution-budget-readiness.v1",
        "source_revision": revision,
        "observed_at_ms": observed,
        "maximum_order_usd": "5",
        "venues": {
            "alpaca": {"authenticated": True, "quotes": {"USD": quote("alpaca", "USD")}},
            "binance": {"authenticated": True, "quotes": {
                asset: quote("binance", asset) for asset in ("FDUSD", "USD", "USDC", "USDT")
            }},
            "capital": {"authenticated": True, "quotes": {"USD": quote("capital", "USD")}},
            "kraken": {"authenticated": True, "quotes": {
                asset: quote("kraken", asset) for asset in ("FDUSD", "USD", "USDC", "USDT")
            }},
        },
    }


def release(now: float, **updates) -> dict:
    value = {
        "schema": "aureon.cloud-trade-release-state.v1",
        "state": "active",
        "generation": 7,
        "request_id": "2" * 64,
        "requested_controls_sha256": bridge.digest(bridge.LIVE_CONTROLS),
        "authorization_event_sha256": "1" * 64,
        "authorization_expires_at_ms": int((now + 3600) * 1000),
        "probe_receipt_sha256": "3" * 64,
        "provider_readback_sha256": "4" * 64,
        "source_revision": REVISION,
        "signed_at_ms": int((now - 30) * 1000),
        "controller_key_version": bridge.CONTROLLER_KEY,
        "signature": "signed-controller-state",
        "update_time": "2026-09-13T12:00:00Z",
    }
    value.update(updates)
    return value


def probe_attestation(
    now: float, *, revision=REVISION, insufficient=(), release_value=None,
) -> dict:
    current_release = release_value or release(now, source_revision=revision)
    readiness = execution_budget(now, revision=revision, insufficient=insufficient)
    providers = {
        venue: {
            "venue": venue,
            "authenticated": True,
            "account_binding_sha256": str(index) * 64,
        }
        for index, venue in enumerate(("alpaca", "binance", "capital", "kraken"), 1)
    }
    accounts_sha = digest(providers)
    readiness_sha = digest(readiness)
    provider = {
        "schema": "aureon.cloud-trade-provider-readback.v1",
        "providers": providers,
        "provider_count": 4,
        "all_authenticated": True,
        "provider_mutation_attempted": False,
        "instrument_preflight_enforced": True,
        "provider_accounts_sha256": accounts_sha,
        "execution_budget_readiness": readiness,
        "execution_budget_readiness_sha256": readiness_sha,
        "readback_sha256": provider_readback_commitment_sha256(accounts_sha, readiness_sha),
    }
    now_ms = int(now * 1000)
    probe = build_probe(
        event_sha256="1" * 64,
        lease_expires_at_ms=int((now + 3600) * 1000),
        revision=revision,
        now_ms=int((now - 21) * 1000),
        readiness_release=build_readiness_release_binding(current_release),
    )
    statement = build_periodic_readiness_statement(
        probe,
        provider,
        {
            "live_execution_release": True,
            "durable_budget_ledger": True,
            "order_adapter_ready": True,
            "live_result_binding_ready": True,
            "instrument_preflight_enforced": True,
        },
        now_ms=now_ms,
    )
    executor = {
        "schema": EXECUTOR_READINESS_SCHEMA,
        "statement": statement,
        "statement_sha256": digest(statement),
        "authority_id": "gcp:aureon-trade-executor",
        "key_version": bridge.EXECUTOR_KEY,
        "signed_at_ms": now_ms,
        "signature": "x" * 64,
    }
    receipt = {
        "schema": RECEIPT_READINESS_SCHEMA,
        "executor_attestation_sha256": digest(executor),
        "statement_sha256": digest(statement),
        "source_revision": statement["source_revision"],
        "release_generation": statement["release_generation"],
        "release_state_sha256": statement["release_state_sha256"],
        "authorization_event_sha256": statement["authorization_event_sha256"],
        "authorization_expires_at_ms": statement["authorization_expires_at_ms"],
        "observed_at_ms": statement["observed_at_ms"],
        "expires_at_ms": statement["expires_at_ms"],
        "authority_id": "gcp:aureon-trade-receipt",
        "key_version": bridge.RECEIPT_KEY,
        "signed_at_ms": now_ms,
        "signature": "y" * 64,
    }
    return {
        "schema": "aureon.cloud-trade-periodic-readiness-document.v1",
        "stored_at_ms": now_ms,
        "source_revision": statement["source_revision"],
        "release_generation": statement["release_generation"],
        "release_request_id": statement["release_request_id"],
        "release_state_sha256": statement["release_state_sha256"],
        "authorization_event_sha256": statement["authorization_event_sha256"],
        "authorization_expires_at_ms": statement["authorization_expires_at_ms"],
        "observed_at_ms": statement["observed_at_ms"],
        "expires_at_ms": statement["expires_at_ms"],
        "provider_accounts_sha256": statement["provider_accounts_sha256"],
        "provider_readback_sha256": statement["provider_readback_sha256"],
        "execution_budget_readiness_sha256": statement["execution_budget_readiness_sha256"],
        "maximum_order_usd": statement["maximum_order_usd"],
        "provider_count": 4,
        "all_authenticated": True,
        "provider_mutation_attempted": False,
        "orders_attempted": 0,
        "orders_submitted": 0,
        "executor_attestation_sha256": digest(executor),
        "executor_attestation_json": canonical_bytes(executor).decode("ascii"),
        "receipt_endorsement_sha256": digest(receipt),
        "receipt_endorsement_json": canonical_bytes(receipt).decode("ascii"),
        "update_time": "2026-09-13T12:00:00Z",
    }


def route(venue="alpaca", market_type="spot", symbol="AAPL") -> dict:
    return {
        "venue": venue,
        "market_type": market_type,
        "symbol": symbol,
        "route_key": f"{venue}:{market_type}:{symbol}:BUY",
        "ready": True,
        "trade_clearance_state": "available",
        "guard_state": "available",
        "runtime_clearances": [],
        "guards": [],
        "clearance_required": [],
        "end_user_trade_available": True,
        "blockers": [],
        "model_count": 2,
        "model_coverage_ready": True,
        "cash_capability_state": "quote_budgeted_at_execution",
    }


def payload(now: float, *, venues=None, side="BUY") -> dict:
    routes = venues or [route()]
    route_symbols = {str(item["venue"]): str(item["symbol"]) for item in routes}
    candidate = {
        "symbol": "AAPL",
        "alpaca_symbol": route_symbols.get("alpaca"),
        "binance_symbol": route_symbols.get("binance"),
        "capital_symbol": route_symbols.get("capital"),
        "kraken_spot_symbol": route_symbols.get("kraken"),
        "side": side,
        "confidence": 0.91,
        "support_count": 2,
        "candidate_id": "candidate-strong-0001",
        "lifecycle_id": "lifecycle-strong-0001",
        "selection_rank": 1,
        "data_status": "live",
        "actionable": True,
        "intent_publish_blockers": [],
        "reference_price": 100.0,
        "source_prices": {"alpaca": 100.0, "market_cache": 100.0},
        "market_observations": [
            {
                "source": "alpaca",
                "feed": "alpaca",
                "symbol": "AAPL",
                "provider_symbol": "AAPL",
                "price": 100.0,
                "source_timestamp": now - 1.0,
                "max_age_sec": 5.0,
            },
            {
                "source": "alpaca_rest",
                "feed": "market_cache",
                "symbol": "AAPL",
                "provider_symbol": "AAPL",
                "price": 100.0,
                "source_timestamp": now - 2.0,
                "max_age_sec": 30.0,
            },
        ],
        "scanner_fusion": {
            "scanner_fusion_score": 0.82,
            "cross_reference_count": 4,
            "usable_for_decision": True,
            "fed_to_decision_logic": True,
            "active_scanners": [
                "LiveMomentumHunter", "SelfValidatingPredictor",
                "TruthPredictionEngine", "WhaleSonar",
            ],
        },
        "execution_routes": routes,
    }
    exchanges = {
        venue: {
            "connected": True,
            "balance_known": True,
            "role": "execution_priority",
            "deployable_cash_usd": 100.0,
        }
        for venue in {str(item["venue"]) for item in routes}
    }
    return {
        "ok": True,
        "source": "unified-market-trader",
        "generated_at": iso(now),
        "trading_gate_evidence": {"analysis_ready": True},
        "hnc_cognitive_proof": {
            "status": "passing",
            "real_data": {"passed": True},
            "passed_count": 6,
            "step_count": 6,
        },
        "exchange_action_plan": {
            **bridge.LOCAL_PLAN_HOLDS,
            "global_blockers": [
                "live_trading_not_enabled", "real_orders_disabled",
                "exchange_mutations_disabled", "order_intent_publish_disabled",
            ],
        },
        "shared_order_flow": {
            "generated_at": iso(now),
            "active_order_flow": [candidate],
            "dynamic_intelligence_budget": {"exchanges": exchanges},
        },
    }


def write_runtime(path: Path, value: dict, now: float) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")
    os.utime(path, (now, now))


class CapturePublisher:
    def __init__(self, *, fail=False):
        self.values = []
        self.fail = fail

    def __call__(self, value, **_kwargs):
        self.values.append(copy.deepcopy(value))
        if self.fail:
            raise bridge.BridgeError("intent_publish_response_invalid")
        return "123456789"


def instance(
    tmp_path: Path, now: float, value: dict, *, publisher=None,
    release_value=None, attestation_value=None, env=None,
):
    tmp_path.mkdir(parents=True, exist_ok=True)
    runtime = tmp_path / "runtime.json"
    write_runtime(runtime, value, now)
    capture = publisher or CapturePublisher()
    current_release = release_value or release(now)
    if attestation_value is not None:
        current_attestation = attestation_value
    else:
        try:
            current_attestation = probe_attestation(now, release_value=current_release)
        except Exception:
            current_attestation = probe_attestation(now)
    return bridge.OrderIntentBridge(
        revision=REVISION,
        runtime_path=runtime,
        state_path=tmp_path / "bridge-state.json",
        status_path=tmp_path / "bridge-status.json",
        environ=dict(bridge.LOCAL_EXECUTOR_HOLDS if env is None else env),
        current_time=lambda: now,
        authorization_builder=lambda **_kwargs: authorization(now),
        controller_reader=lambda **_kwargs: (copy.deepcopy(current_release), None),
        attestation_reader=lambda **_kwargs: (copy.deepcopy(current_attestation), None),
        publisher=capture,
        http_reader=lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("unexpected real HTTP")),
    ), capture


def test_cycle_publishes_one_exact_canonical_five_dollar_max_intent(tmp_path):
    now = time.time()
    worker, capture = instance(tmp_path, now, payload(now))
    result = worker.cycle()
    assert result["state"] == "published"
    assert result["operational"] is result["candidate_ready"] is True
    assert len(capture.values) == 1
    intent = capture.values[0]
    assert canonical_bytes(intent) == json.dumps(
        intent, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False,
    ).encode("ascii")
    validated = validate_intent(intent, now_ms=int(now * 1000), max_order_usd=5, live_release=True)
    assert validated == intent
    assert intent["requested_controls"] == bridge.LIVE_CONTROLS
    assert intent["dry_run"] is False and intent["kind"] == "order"
    assert intent["order"]["quote_value_usd"] <= 5
    assert intent["order"]["quantity"] > 0
    assert bridge._HEX64.fullmatch(intent["intent_id"])
    assert bridge._HEX64.fullmatch(intent["order"]["client_order_id"])
    stored = json.loads((tmp_path / "bridge-state.json").read_text())
    assert len(stored["entries"]) == 1
    assert stored["entries"][0]["status"] == "published"
    assert stored["entries"][0]["pubsub_message_id"] == "123456789"
    assert result["last_publish"]["topic"] == bridge.TOPIC_RESOURCE
    assert "access_token" not in json.dumps(result)


def test_deterministic_ids_and_at_most_one_route(tmp_path):
    now = time.time()
    routes = [route("alpaca", "spot", "AAPL"), route("binance", "spot", "AAPLUSDT")]
    value = payload(now, venues=routes)
    first, capture = instance(tmp_path, now, value)
    result = first.cycle()
    assert result["state"] == "published"
    assert len(capture.values) == 1
    intent = capture.values[0]
    evidence = bridge.select_candidate(
        value, runtime_generated_at_ms=int(now * 1000), now_ms=int(now * 1000),
        execution_budget_readiness=execution_budget(now),
    )
    auth = bridge._validate_authorization(authorization(now), now_ms=int(now * 1000))
    expected, _ = bridge.build_intent(
        evidence, authorization=auth, release=release(now), revision=REVISION,
        runtime_sha256=result["source"]["runtime_status_sha256"], now_ms=int(now * 1000),
    )
    assert expected["intent_id"] == intent["intent_id"]
    assert expected["order"]["client_order_id"] == intent["order"]["client_order_id"]


@pytest.mark.parametrize("venue,market_type,route_symbol", [
    ("alpaca", "spot", "AAPL"),
    ("binance", "spot", "AAPLUSDT"),
    ("capital", "cfd", "AAPL"),
    ("kraken", "spot", "AAPL/USD"),
])
def test_each_venue_uses_its_exact_candidate_bound_route_symbol(
    venue, market_type, route_symbol,
):
    now = time.time()
    value = payload(now, venues=[route(venue, market_type, route_symbol)])
    candidate = value["shared_order_flow"]["active_order_flow"][0]
    candidate["source_prices"] = {venue: 100.0, "market_cache": 100.0}
    candidate["market_observations"][0].update(
        source=venue, feed=venue, provider_symbol=route_symbol,
    )
    evidence = bridge.select_candidate(
        value, runtime_generated_at_ms=int(now * 1000), now_ms=int(now * 1000),
        execution_budget_readiness=execution_budget(now),
    )
    auth = bridge._validate_authorization(authorization(now), now_ms=int(now * 1000))
    intent, evidence_sha256 = bridge.build_intent(
        evidence, authorization=auth, release=release(now), revision=REVISION,
        runtime_sha256="f" * 64, now_ms=int(now * 1000),
    )
    assert evidence["symbol"] == "AAPL"
    assert evidence["route"]["symbol"] == route_symbol
    assert evidence["route"]["candidate_symbol_binding_field"] == (
        bridge.ROUTE_SYMBOL_FIELDS[venue]
    )
    assert intent["order"]["venue"] == venue
    assert intent["order"]["symbol"] == route_symbol
    assert intent["market_evidence_sha256"] == evidence_sha256


def test_replay_is_blocked_without_second_publish(tmp_path):
    now = time.time()
    worker, capture = instance(tmp_path, now, payload(now))
    worker.cycle()
    second = worker.cycle()
    assert len(capture.values) == 1
    assert second["state"] == "idle"
    assert second["operational"] is True
    assert second["blockers"] == ["intent_replay_blocked"]


def test_route_cooldown_blocks_new_candidate_on_same_route(tmp_path):
    now = time.time()
    worker, capture = instance(tmp_path, now, payload(now))
    worker.cycle()
    changed = payload(now + 10)
    changed["shared_order_flow"]["active_order_flow"][0]["candidate_id"] = "candidate-strong-0002"
    changed["shared_order_flow"]["active_order_flow"][0]["lifecycle_id"] = "lifecycle-strong-0002"
    write_runtime(worker.runtime_path, changed, now + 10)
    worker.current_time = lambda: now + 10
    second = worker.cycle()
    assert len(capture.values) == 1
    assert second["blockers"] == ["route_cooldown_active"]


def test_pending_reservation_prevents_retry_after_unknown_publish_outcome(tmp_path):
    now = time.time()
    capture = CapturePublisher(fail=True)
    worker, _ = instance(tmp_path, now, payload(now), publisher=capture)
    first = worker.cycle()
    assert first["state"] == "publish_outcome_unknown"
    state = json.loads(worker.state_path.read_text())
    assert state["entries"][0]["status"] == "pending"
    second = worker.cycle()
    assert len(capture.values) == 1
    assert second["blockers"] == ["intent_replay_blocked"]


@pytest.mark.parametrize(
    ("release_updates", "expected"),
    [
        ({"state": "held"}, "controller_release_not_current_for_owner_runtime"),
        ({"source_revision": "b" * 40}, "controller_release_not_current_for_owner_runtime"),
        ({"authorization_event_sha256": "9" * 64}, "controller_release_not_current_for_owner_runtime"),
        ({"requested_controls_sha256": "8" * 64}, "controller_release_not_current_for_owner_runtime"),
    ],
)
def test_release_must_match_live_controls_owner_lease_and_revision(tmp_path, release_updates, expected):
    now = time.time()
    worker, capture = instance(tmp_path, now, payload(now), release_value=release(now, **release_updates))
    result = worker.cycle()
    assert result["state"] == "blocked"
    assert result["blockers"] == [expected]
    assert capture.values == []


def test_inactive_authorization_and_weak_local_holds_never_publish(tmp_path):
    now = time.time()
    worker, capture = instance(tmp_path, now, payload(now), env={**bridge.LOCAL_EXECUTOR_HOLDS, "AUREON_LIVE_TRADING": "1"})
    assert worker.cycle()["blockers"] == ["bridge_service_local_holds_not_enforced"]
    assert capture.values == []
    worker, capture = instance(tmp_path / "second", now, payload(now))
    worker.runtime_path.parent.mkdir(exist_ok=True)
    write_runtime(worker.runtime_path, payload(now), now)
    inactive = authorization(now)
    inactive.update(active=False, state="expired")
    worker.authorization_builder = lambda **_kwargs: inactive
    assert worker.cycle()["blockers"] == ["operator_authorization_invalid"]
    assert capture.values == []


@pytest.mark.parametrize(
    ("mutate", "reason"),
    [
        (lambda value, now: value.update(generated_at=iso(now - 31)), "unified_runtime_status_not_fresh_complete"),
        (lambda value, now: value["trading_gate_evidence"].update(analysis_ready=False), "trading_gate_analysis_not_ready"),
        (lambda value, now: value["hnc_cognitive_proof"].update(status="attention"), "hnc_cognitive_proof_not_passing"),
        (lambda value, now: value["shared_order_flow"]["active_order_flow"][0].update(confidence=0.69), "candidate_signal_evidence_not_strong"),
        (lambda value, now: value["shared_order_flow"]["active_order_flow"][0]["market_observations"][0].update(source_timestamp=now - 31), "provider_timestamp_not_fresh"),
        (lambda value, now: value["shared_order_flow"]["active_order_flow"][0]["execution_routes"][0].update(blockers=["held"]), "candidate_route_evidence_not_ready"),
    ],
)
def test_stale_or_weak_candidate_evidence_never_publishes(tmp_path, mutate, reason):
    now = time.time()
    value = payload(now)
    mutate(value, now)
    worker, capture = instance(tmp_path, now, value)
    result = worker.cycle()
    assert result["blockers"] == [reason]
    assert capture.values == []


def test_vm_runtime_balance_claims_cannot_grant_or_remove_executor_budget(tmp_path):
    now = time.time()
    value = payload(now)
    value["shared_order_flow"]["dynamic_intelligence_budget"] = {
        "exchanges": {
            "alpaca": {
                "connected": False,
                "balance_known": False,
                "role": "sensor_priority",
                "deployable_cash_usd": 999_999_999,
            },
        },
    }
    worker, capture = instance(tmp_path, now, value)
    assert worker.cycle()["state"] == "published"
    assert len(capture.values) == 1
    assert capture.values[0]["order"]["quote_value_usd"] == 5


def test_insufficient_executor_budget_attestation_blocks_publish(tmp_path):
    now = time.time()
    live_release = release(now)
    attestation = probe_attestation(
        now,
        insufficient={("alpaca", "USD")},
        release_value=live_release,
    )
    worker, capture = instance(
        tmp_path, now, payload(now),
        release_value=live_release,
        attestation_value=attestation,
    )
    result = worker.cycle()
    assert result["blockers"] == ["candidate_route_execution_budget_not_ready"]
    assert capture.values == []


def test_stale_execution_budget_attestation_blocks_publish(tmp_path):
    now = time.time()
    attestation = probe_attestation(now)
    executor = json.loads(attestation["executor_attestation_json"])
    statement = executor["statement"]
    readiness = statement["execution_budget_readiness"]
    readiness["observed_at_ms"] = int((now - 301) * 1000)
    readiness_sha = digest(readiness)
    statement["execution_budget_readiness_sha256"] = readiness_sha
    statement["provider_readback_sha256"] = provider_readback_commitment_sha256(
        statement["provider_accounts_sha256"], readiness_sha,
    )
    statement["observed_at_ms"] = readiness["observed_at_ms"]
    statement["expires_at_ms"] = readiness["observed_at_ms"] + 300_000
    executor["statement_sha256"] = digest(statement)
    attestation["observed_at_ms"] = statement["observed_at_ms"]
    attestation["expires_at_ms"] = statement["expires_at_ms"]
    attestation["execution_budget_readiness_sha256"] = readiness_sha
    attestation["provider_readback_sha256"] = statement["provider_readback_sha256"]
    attestation["executor_attestation_json"] = canonical_bytes(executor).decode("ascii")
    attestation["executor_attestation_sha256"] = digest(executor)
    receipt = json.loads(attestation["receipt_endorsement_json"])
    receipt.update({
        "executor_attestation_sha256": digest(executor),
        "statement_sha256": digest(statement),
        "observed_at_ms": statement["observed_at_ms"],
        "expires_at_ms": statement["expires_at_ms"],
    })
    attestation["receipt_endorsement_json"] = canonical_bytes(receipt).decode("ascii")
    attestation["receipt_endorsement_sha256"] = digest(receipt)
    live_release = release(now)
    worker, capture = instance(
        tmp_path, now, payload(now), release_value=live_release,
        attestation_value=attestation,
    )
    assert worker.cycle()["blockers"] == ["periodic_readiness_document_invalid"]
    assert capture.values == []


def test_revision_mismatched_budget_attestation_blocks_publish(tmp_path):
    now = time.time()
    attestation = probe_attestation(now, revision="b" * 40)
    live_release = release(
        now,
        provider_readback_sha256=attestation["provider_readback_sha256"],
    )
    worker, capture = instance(
        tmp_path, now, payload(now), release_value=live_release,
        attestation_value=attestation,
    )
    assert worker.cycle()["blockers"] == [
        "execution_budget_attestation_release_join_invalid",
    ]
    assert capture.values == []


def test_tampered_budget_attestation_blocks_and_private_payload_is_not_exposed(tmp_path):
    now = time.time()
    attestation = probe_attestation(now)
    executor = json.loads(attestation["executor_attestation_json"])
    readiness = executor["statement"]["execution_budget_readiness"]
    readiness["venues"]["alpaca"]["quotes"]["USD"] = {
        "status": "insufficient", "allowance_usd": "0",
    }
    attestation["executor_attestation_json"] = canonical_bytes(executor).decode("ascii")
    worker, capture = instance(tmp_path, now, payload(now), attestation_value=attestation)
    assert worker.cycle()["blockers"] == ["periodic_readiness_document_invalid"]
    assert capture.values == []

    clean_worker, clean_capture = instance(tmp_path / "clean", now, payload(now))
    status = clean_worker.cycle()
    exposed = json.dumps({"status": status, "intent": clean_capture.values[0]}).lower()
    assert "execution_budget_readiness_json" not in exposed
    assert "provider_accounts_sha256" not in exposed
    assert "account_binding_sha256" not in exposed


@pytest.mark.parametrize(
    ("mutate", "reason"),
    [
        (
            lambda value: value["shared_order_flow"]["active_order_flow"][0].update(
                alpaca_symbol="MSFT",
            ),
            "candidate_route_symbol_binding_mismatch",
        ),
        (
            lambda value: value["shared_order_flow"]["active_order_flow"][0][
                "execution_routes"
            ][0].update(symbol="MSFT", route_key="alpaca:spot:MSFT:BUY"),
            "candidate_route_symbol_binding_mismatch",
        ),
        (
            lambda value: value["shared_order_flow"]["active_order_flow"][0][
                "execution_routes"
            ][0].update(route_key="alpaca:spot:AAPL:SELL"),
            "candidate_route_key_binding_mismatch",
        ),
        (
            lambda value: value["shared_order_flow"]["active_order_flow"][0][
                "market_observations"
            ][0].update(symbol="MSFT"),
            "provider_price_symbol_join_invalid",
        ),
        (
            lambda value: value["shared_order_flow"]["active_order_flow"][0][
                "market_observations"
            ][0].update(price=10_000.0),
            "provider_price_observation_join_invalid",
        ),
        (
            lambda value: value["shared_order_flow"]["active_order_flow"][0][
                "market_observations"
            ][0].update(provider_symbol="MSFT"),
            "route_provider_price_symbol_join_invalid",
        ),
        (
            lambda value: (
                value["shared_order_flow"]["active_order_flow"][0]["source_prices"].update(
                    notalpacaevil=value["shared_order_flow"]["active_order_flow"][0][
                        "source_prices"
                    ].pop("alpaca")
                ),
                value["shared_order_flow"]["active_order_flow"][0][
                    "market_observations"
                ][0].update(source="notalpacaevil", feed="notalpacaevil"),
            ),
            "route_provider_price_observation_missing",
        ),
    ],
)
def test_candidate_route_and_price_observation_are_exactly_joined_before_publish(
    tmp_path, mutate, reason,
):
    now = time.time()
    value = payload(now)
    mutate(value)
    worker, capture = instance(tmp_path, now, value)
    assert worker.cycle()["blockers"] == [reason]
    assert capture.values == []


def test_spot_sell_and_margin_routes_fail_closed(tmp_path):
    now = time.time()
    sell = payload(now, side="SELL")
    worker, capture = instance(tmp_path, now, sell)
    assert worker.cycle()["blockers"] == ["spot_sell_asset_balance_evidence_missing"]
    assert capture.values == []
    margin = payload(now, venues=[route("binance", "margin", "AAPLUSDT")])
    worker, capture = instance(tmp_path / "margin", now, margin)
    worker.runtime_path.parent.mkdir(exist_ok=True)
    write_runtime(worker.runtime_path, margin, now)
    assert worker.cycle()["blockers"] == ["candidate_route_not_supported_by_cloud_adapter"]
    assert capture.values == []


def test_corrupt_replay_state_fails_closed_before_publish(tmp_path):
    now = time.time()
    worker, capture = instance(tmp_path, now, payload(now))
    worker.state_path.write_text('{"schema":"wrong"}', encoding="utf-8")
    result = worker.cycle()
    assert result["state"] == "blocked"
    assert result["blockers"] == ["bridge_state_invalid"]
    assert capture.values == []


def test_default_readiness_reader_verifies_executor_and_receipt_detached_signatures():
    now = time.time()
    document = probe_attestation(now)
    private = {
        bridge.EXECUTOR_KEY: Ed25519PrivateKey.generate(),
        bridge.RECEIPT_KEY: Ed25519PrivateKey.generate(),
    }
    executor = json.loads(document["executor_attestation_json"])
    executor["signature"] = base64.b64encode(private[bridge.EXECUTOR_KEY].sign(
        canonical_bytes({key: value for key, value in executor.items() if key != "signature"}),
    )).decode("ascii")
    document["executor_attestation_json"] = canonical_bytes(executor).decode("ascii")
    document["executor_attestation_sha256"] = digest(executor)
    receipt = json.loads(document["receipt_endorsement_json"])
    receipt["executor_attestation_sha256"] = digest(executor)
    receipt["signature"] = base64.b64encode(private[bridge.RECEIPT_KEY].sign(
        canonical_bytes({key: value for key, value in receipt.items() if key != "signature"}),
    )).decode("ascii")
    document["receipt_endorsement_json"] = canonical_bytes(receipt).decode("ascii")
    document["receipt_endorsement_sha256"] = digest(receipt)

    def firestore_value(value):
        if type(value) is bool:
            return {"booleanValue": value}
        if type(value) is int:
            return {"integerValue": str(value)}
        return {"stringValue": value}

    wire = {
        "fields": {
            key: firestore_value(value)
            for key, value in document.items()
            if key != "update_time"
        },
        "updateTime": document["update_time"],
    }

    def reader(url, **_kwargs):
        if url == bridge.METADATA_URL:
            value = {"access_token": "x" * 40, "expires_in": 3600}
        elif url == bridge.FIRESTORE_READINESS_URL:
            value = wire
        else:
            key = (
                bridge.EXECUTOR_KEY
                if url == bridge.EXECUTOR_PUBLIC_KEY_URL
                else bridge.RECEIPT_KEY
            )
            value = {
                "name": key,
                "algorithm": "EC_SIGN_ED25519",
                "pem": private[key].public_key().public_bytes(
                    serialization.Encoding.PEM,
                    serialization.PublicFormat.SubjectPublicKeyInfo,
                ).decode("ascii"),
            }
        return bridge._Response(200, json.dumps(value).encode("ascii"))

    verified, error = bridge._probe_state(reader=reader, now_ms=int(now * 1000))
    assert error is None
    assert verified["release_generation"] == 7
    assert "executor_attestation" not in verified

    receipt["signature"] = base64.b64encode(b"x" * 64).decode("ascii")
    wire["fields"]["receipt_endorsement_json"] = firestore_value(
        canonical_bytes(receipt).decode("ascii"),
    )
    wire["fields"]["receipt_endorsement_sha256"] = firestore_value(digest(receipt))
    verified, error = bridge._probe_state(reader=reader, now_ms=int(now * 1000))
    assert verified is None and error == "periodic_readiness_signature_invalid"


def test_publish_uses_metadata_token_fixed_topic_and_canonical_intent():
    now = time.time()
    evidence = bridge.select_candidate(
        payload(now), runtime_generated_at_ms=int(now * 1000), now_ms=int(now * 1000),
        execution_budget_readiness=execution_budget(now),
    )
    auth = bridge._validate_authorization(authorization(now), now_ms=int(now * 1000))
    intent, _fingerprint = bridge.build_intent(
        evidence, authorization=auth, release=release(now), revision=REVISION,
        runtime_sha256="f" * 64, now_ms=int(now * 1000),
    )
    calls = []

    def reader(url, **kwargs):
        calls.append((url, kwargs))
        if url == bridge.METADATA_URL:
            assert kwargs["headers"] == {"Metadata-Flavor": "Google"}
            return bridge._Response(200, json.dumps({"access_token": "t" * 20, "expires_in": 300}).encode())
        assert url == bridge.PUBLISH_URL
        envelope = json.loads(kwargs["body"])
        assert base64.b64decode(envelope["messages"][0]["data"]) == canonical_bytes(intent)
        assert envelope["messages"][0]["orderingKey"] == intent["intent_id"]
        assert envelope["messages"][0]["attributes"] == {
            "schema": bridge.INTENT_SCHEMA, "kind": "order", "intent_id": intent["intent_id"],
        }
        return bridge._Response(200, b'{"messageIds":["42"]}')

    assert bridge.publish_intent(intent, reader=reader, current_time=lambda: now) == "42"
    assert [url for url, _ in calls] == [bridge.METADATA_URL, bridge.PUBLISH_URL]


def test_fixed_http_rejects_every_non_allowlisted_endpoint_without_network():
    with pytest.raises(bridge.BridgeError, match="cloud_endpoint_not_allowlisted"):
        bridge._fixed_http("https://example.com/steal", method="GET")
    with pytest.raises(bridge.BridgeError, match="cloud_endpoint_not_allowlisted"):
        bridge._fixed_http(bridge.METADATA_URL, method="POST")


def _signed_controller_reader(now: float, *, tamper=False):
    private = Ed25519PrivateKey.generate()
    value = release(now)
    unsigned = {
        key: item for key, item in value.items() if key not in {"signature", "update_time"}
    }
    signature = private.sign(json.dumps(
        unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False,
    ).encode("utf-8"))
    value["signature"] = base64.b64encode(signature).decode("ascii")
    if tamper:
        value["request_id"] = "f" * 64
    fields = {}
    for key, item in value.items():
        if key == "update_time":
            continue
        fields[key] = (
            {"integerValue": str(item)} if type(item) is int
            else {"booleanValue": item} if type(item) is bool
            else {"stringValue": item}
        )
    firestore = {"fields": fields, "updateTime": value["update_time"]}
    pem = private.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("ascii")
    calls = []

    def reader(url, **kwargs):
        calls.append((url, kwargs.get("method", "GET")))
        if url == bridge.METADATA_URL:
            return bridge._Response(200, json.dumps({
                "access_token": "m" * 20, "expires_in": 300,
            }).encode())
        if url == bridge.FIRESTORE_RELEASE_URL:
            return bridge._Response(200, json.dumps(firestore).encode())
        if url == bridge.KMS_PUBLIC_KEY_URL:
            return bridge._Response(200, json.dumps({
                "name": bridge.CONTROLLER_KEY,
                "algorithm": "EC_SIGN_ED25519",
                "pem": pem,
            }).encode())
        raise AssertionError(url)

    return reader, calls


def test_controller_state_uses_fixed_google_endpoints_and_verifies_signature():
    reader, calls = _signed_controller_reader(time.time())
    value, error = bridge._controller_state(reader=reader)
    assert error is None
    assert value["state"] == "active"
    assert [url for url, _method in calls] == [
        bridge.METADATA_URL,
        bridge.FIRESTORE_RELEASE_URL,
        bridge.KMS_PUBLIC_KEY_URL,
    ]


def test_controller_state_rejects_tampered_signed_fields():
    reader, _calls = _signed_controller_reader(time.time(), tamper=True)
    value, error = bridge._controller_state(reader=reader)
    assert value is None
    assert error == "cloud_release_signature_invalid"


def test_all_supported_venues_produce_positive_bounded_quantity():
    for venue in sorted(bridge.SUPPORTED_ROUTE_TYPES):
        quantity, quote = bridge._quantity(67_000.123456, venue)
        assert quantity > 0
        assert 0 < quote <= 5
