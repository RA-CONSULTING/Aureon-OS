"""Verify and durably collect terminal receipts from the cloud authority chain."""
from __future__ import annotations

import argparse
import base64
import binascii
import json
import math
import os
import re
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Mapping
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


ROOT = Path(__file__).resolve().parent
CONTRACT_ROOT = ROOT / "trading-control"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(CONTRACT_ROOT) not in sys.path:
    sys.path.insert(0, str(CONTRACT_ROOT))

from contract import (  # noqa: E402
    ContractError,
    DISPATCH_SCHEMA,
    EXECUTOR_SCHEMA,
    RECEIPT_SCHEMA,
    REVIEW_SCHEMA,
    canonical_bytes,
    build_readiness_release_binding,
    digest,
    periodic_readiness_probe,
    unsigned_stage,
    validate_intent,
    validate_provider_probe_readback,
    validate_readiness_envelope,
    validate_stage,
)
from make_probe import build_probe  # noqa: E402
from cloud_order_intent_bridge import (  # noqa: E402
    BRIDGE_INTERVAL_SECONDS,
    BridgeError as IntentBridgeError,
    DEFAULT_STATE,
    DEFAULT_STATUS,
    OrderIntentBridge,
)
from provider_boundary import valid_instrument_readiness_blocker  # noqa: E402
from vm_workload_identity import (  # noqa: E402
    WorkloadIdentityError,
    broker_token,
)


PROJECT = "aureon-trading"
PROJECT_NUMBER = "4435775023"
SUBSCRIPTION = "aureon-trade-terminal-readback-v1"
METADATA = "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token"
PUBSUB = (
    f"https://pubsub.googleapis.com/v1/projects/{PROJECT}/subscriptions/{SUBSCRIPTION}"
)
PROBE_TOPIC = (
    f"https://pubsub.googleapis.com/v1/projects/{PROJECT}/topics/"
    "aureon-trade-intents-v1:publish"
)
KEY_PREFIX = (
    f"projects/{PROJECT}/locations/europe-west1/keyRings/aureon-trading-prod/cryptoKeys"
)
KEYS = {
    "review": f"{KEY_PREFIX}/aureon-review-signing/cryptoKeyVersions/1",
    "dispatch": f"{KEY_PREFIX}/aureon-dispatch-signing/cryptoKeyVersions/1",
    "executor": f"{KEY_PREFIX}/aureon-executor-signing/cryptoKeyVersions/1",
    "receipt": f"{KEY_PREFIX}/aureon-receipt-signing/cryptoKeyVersions/1",
}
DEFAULT_OUTPUT = Path(
    "/var/lib/aureon-control-exchange/trade-readback/latest-terminal-receipt.json"
)
DEFAULT_LIVE_OUTPUT = Path(
    "/var/lib/aureon-trade-bridge/latest-live-terminal-receipt.json"
)
_MESSAGE_ID = re.compile(r"[0-9]{1,64}")
_PROVIDER_ID = re.compile(r"[A-Za-z0-9._:/-]{1,256}")
_HEX64 = re.compile(r"[0-9a-f]{64}")
_REVISION = re.compile(r"[0-9a-f]{40,64}")
PROBE_INTERVAL_SECONDS = 120.0
REQUIRED_PROBE_HOLDS = {
    "AUREON_DEPLOYMENT_HOLD": "1",
    "AUREON_DISABLE_REAL_ORDERS": "1",
    "AUREON_DISABLE_EXCHANGE_MUTATIONS": "1",
    "AUREON_ORDER_INTENT_PUBLISH": "0",
    "AUREON_LIVE_TRADING": "0",
    "AUREON_UNIFIED_ORDER_EXECUTOR": "0",
}


class CollectorError(RuntimeError):
    """Stable receipt collector failure."""


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise CollectorError("cloud_redirect_denied")


def _http(url: str, *, method: str = "GET", headers: Mapping[str, str] | None = None,
          body: bytes | None = None, timeout: float = 30) -> bytes:
    opener = build_opener(ProxyHandler({}), NoRedirects())
    try:
        with opener.open(Request(url, data=body, headers=dict(headers or {}), method=method),
                         timeout=timeout) as response:
            if response.status < 200 or response.status >= 300:
                raise CollectorError("cloud_http_status_invalid")
            data = response.read(1_048_577)
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        raise CollectorError("cloud_http_request_failed") from exc
    if len(data) > 1_048_576:
        raise CollectorError("cloud_http_response_too_large")
    return data


def access_token(reader=_http) -> str:
    try:
        token = broker_token()
    except WorkloadIdentityError as exc:
        raise CollectorError(str(exc)) from exc
    if token is not None:
        return token
    raw = reader(METADATA, headers={"Metadata-Flavor": "Google"}, timeout=5)
    try:
        value = json.loads(raw)
    except (ValueError, TypeError, UnicodeError) as exc:
        raise CollectorError("metadata_token_response_invalid") from exc
    token = value.get("access_token") if isinstance(value, dict) else None
    expires = value.get("expires_in") if isinstance(value, dict) else None
    if (not isinstance(token, str) or not 20 <= len(token) <= 8192
            or type(expires) is not int or expires < 30):
        raise CollectorError("metadata_token_response_invalid")
    return token


def _cloud_json(raw: bytes, code: str) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except (ValueError, TypeError, UnicodeError) as exc:
        raise CollectorError(code) from exc
    if not isinstance(value, dict):
        raise CollectorError(code)
    return value


def publish_control_probe(*, revision: str, reader=_http, current_time=time.time,
                          environ: Mapping[str, str] | None = None,
                          authorization_builder=None,
                          release: Mapping[str, Any] | None = None) -> dict[str, str] | None:
    """Publish one held, zero-mutation probe while the owner lease is active."""
    env = os.environ if environ is None else environ
    if not _REVISION.fullmatch(str(revision or "")):
        raise CollectorError("probe_revision_invalid")
    if any(env.get(key) != value for key, value in REQUIRED_PROBE_HOLDS.items()):
        raise CollectorError("probe_runtime_holds_not_enforced")
    try:
        now = float(current_time())
    except (TypeError, ValueError) as exc:
        raise CollectorError("probe_clock_invalid") from exc
    if not math.isfinite(now) or now <= 0:
        raise CollectorError("probe_clock_invalid")
    if authorization_builder is None:
        from aureon.operator.authorization_lease import build_operator_authorization_receipt

        authorization_builder = build_operator_authorization_receipt
    authorization = authorization_builder(now=now)
    if not isinstance(authorization, Mapping):
        raise CollectorError("probe_authorization_invalid")
    if authorization.get("active") is not True:
        return None
    event_sha256 = authorization.get("ledger_event_sha256")
    expires_at = authorization.get("expires_at")
    if (not _HEX64.fullmatch(str(event_sha256 or ""))
            or isinstance(expires_at, bool) or not isinstance(expires_at, (int, float))
            or not math.isfinite(float(expires_at)) or float(expires_at) <= now
            or float(expires_at) > now + 259_200):
        raise CollectorError("probe_authorization_invalid")
    readiness_release = None
    if isinstance(release, Mapping) and release.get("state") == "active":
        try:
            candidate = build_readiness_release_binding(release)
        except ContractError:
            candidate = None
        if (
            candidate is not None
            and candidate["source_revision"] == revision
            and candidate["authorization_event_sha256"] == event_sha256
            and candidate["authorization_expires_at_ms"] == int(float(expires_at) * 1000)
            and candidate["authorization_expires_at_ms"] > int(now * 1000)
        ):
            readiness_release = candidate
    probe = build_probe(
        event_sha256=str(event_sha256),
        lease_expires_at_ms=int(float(expires_at) * 1000),
        revision=revision,
        now_ms=int(now * 1000),
        readiness_release=readiness_release,
    )
    token = access_token(reader)
    response = reader(
        PROBE_TOPIC,
        method="POST",
        headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
        body=json.dumps({"messages": [{
            "data": base64.b64encode(canonical_bytes(probe)).decode("ascii"),
            "attributes": {"schema": probe["schema"]},
            "orderingKey": probe["intent_id"],
        }]}, separators=(",", ":")).encode("ascii"),
        timeout=15,
    )
    token = ""
    value = _cloud_json(response, "probe_publish_response_invalid")
    message_ids = value.get("messageIds")
    if (not isinstance(message_ids, list) or len(message_ids) != 1
            or not isinstance(message_ids[0], str)
            or not _MESSAGE_ID.fullmatch(message_ids[0])):
        raise CollectorError("probe_publish_response_invalid")
    return {
        "message_id": message_ids[0],
        "intent_id": probe["intent_id"],
        "mode": "periodic_readiness" if readiness_release is not None else "activation_probe",
    }


def _verify_signature(stage: Mapping[str, Any], expected_key: str, *, token: str,
                      reader=_http) -> None:
    if stage.get("key_version") != expected_key:
        raise CollectorError("terminal_key_pin_mismatch")
    raw = reader(
        "https://cloudkms.googleapis.com/v1/" + expected_key + "/publicKey",
        headers={"Authorization": "Bearer " + token, "Accept": "application/json"},
        timeout=8,
    )
    value = _cloud_json(raw, "kms_public_key_response_invalid")
    if (value.get("name") != expected_key or value.get("algorithm") != "EC_SIGN_ED25519"
            or not isinstance(value.get("pem"), str)):
        raise CollectorError("kms_public_key_response_invalid")
    try:
        public = serialization.load_pem_public_key(value["pem"].encode("ascii"))
        signature = base64.b64decode(str(stage.get("signature") or ""), validate=True)
    except (ValueError, TypeError, UnicodeError, binascii.Error) as exc:
        raise CollectorError("terminal_signature_invalid") from exc
    if not isinstance(public, Ed25519PublicKey) or len(signature) != 64:
        raise CollectorError("terminal_signature_invalid")
    try:
        public.verify(signature, canonical_bytes(unsigned_stage(stage)))
    except InvalidSignature as exc:
        raise CollectorError("terminal_signature_invalid") from exc


def verify_terminal_receipt(receipt: Mapping[str, Any], *, token: str,
                            now_ms: int | None = None, reader=_http) -> dict[str, Any]:
    current = int(time.time() * 1000) if now_ms is None else int(now_ms)
    terminal = validate_stage(receipt, schema=RECEIPT_SCHEMA, payload_key="executor")
    _verify_signature(terminal, KEYS["receipt"], token=token, reader=reader)
    executor = validate_stage(terminal["executor"], schema=EXECUTOR_SCHEMA, payload_key="result")
    _verify_signature(executor, KEYS["executor"], token=token, reader=reader)
    result = executor["result"]
    if not isinstance(result, Mapping) or not isinstance(result.get("dispatch"), Mapping):
        raise CollectorError("terminal_executor_result_invalid")
    dispatch = validate_stage(result["dispatch"], schema=DISPATCH_SCHEMA, payload_key="review")
    _verify_signature(dispatch, KEYS["dispatch"], token=token, reader=reader)
    review = validate_stage(dispatch["review"], schema=REVIEW_SCHEMA, payload_key="intent")
    _verify_signature(review, KEYS["review"], token=token, reader=reader)
    untrusted_intent = review["intent"]
    created_at = untrusted_intent.get("created_at_ms") if isinstance(untrusted_intent, Mapping) else None
    if type(created_at) is not int or created_at > current + 5_000:
        raise CollectorError("terminal_intent_time_invalid")
    # A receipt remains verifiable after its short command lease expires.  Use
    # the signed creation time for shape/lifetime validation, then constrain all
    # signed stage times to that same lease below.
    intent = validate_intent(
        untrusted_intent, now_ms=created_at, max_order_usd=5,
        live_release=bool(isinstance(untrusted_intent, Mapping) and untrusted_intent.get("kind") == "order"),
    )
    outcome = result.get("outcome")
    if not isinstance(outcome, Mapping):
        raise CollectorError("terminal_outcome_invalid")
    is_probe = intent["kind"] == "control_plane_probe"
    if is_probe:
        if (intent["dry_run"] is not True
                or outcome.get("schema") != "aureon.cloud-trade-probe-result.v1"
                or outcome.get("status") != "probe_passed"
                or outcome.get("provider_mutation_attempted") is not False
                or outcome.get("orders_attempted") != 0
                or outcome.get("orders_submitted") != 0):
            raise CollectorError("terminal_probe_outcome_invalid")
        capabilities = outcome.get("executor_capabilities")
        if (not isinstance(capabilities, Mapping)
                or set(capabilities) != {
                    "live_execution_release", "durable_budget_ledger",
                    "order_adapter_ready", "live_result_binding_ready",
                    "instrument_preflight_enforced",
                }
                or any(type(value) is not bool for value in capabilities.values())):
            raise CollectorError("terminal_executor_capabilities_invalid")
        readiness_attestation = outcome.get("readiness_attestation")
        if periodic_readiness_probe(intent):
            try:
                readiness_attestation = validate_readiness_envelope(
                    readiness_attestation, role="executor", now_ms=current,
                )
            except ContractError as exc:
                raise CollectorError("terminal_periodic_readiness_invalid") from exc
            if readiness_attestation["key_version"] != KEYS["executor"]:
                raise CollectorError("terminal_periodic_readiness_key_invalid")
            _verify_signature(
                readiness_attestation, KEYS["executor"], token=token, reader=reader,
            )
        elif readiness_attestation is not None:
            raise CollectorError("terminal_activation_probe_readiness_forbidden")
    else:
        status = outcome.get("status")
        blocker = outcome.get("instrument_readiness_blocker")
        reason_code = outcome.get("reason_code")
        valid_blocker = blocker is None or (
            status == "rejected"
            and valid_instrument_readiness_blocker(
                blocker, venue=outcome.get("venue"), reason_code=reason_code,
            )
        )
        provider_rule_rejection = (
            status == "rejected"
            and isinstance(reason_code, str)
            and any(reason_code.startswith(venue + "_") for venue in (
                "alpaca", "binance", "capital", "kraken",
            ))
        )
        valid_live = (
            intent["dry_run"] is False
            and outcome.get("schema") == "aureon.cloud-trade-live-result.v1"
            and outcome.get("intent_id") == intent["intent_id"]
            and outcome.get("dispatch_sha256") == digest(dispatch)
            and status in {"provider_observed", "rejected", "uncertain"}
            and valid_blocker
            and (not provider_rule_rejection or blocker is not None)
            and ((status == "provider_observed"
                  and outcome.get("provider_mutation_attempted") is True
                  and outcome.get("orders_attempted") == 1
                  and outcome.get("orders_submitted") == 1
                  and isinstance(outcome.get("provider_order_id"), str)
                  and isinstance(outcome.get("provider_client_order_id"), str)
                  and _PROVIDER_ID.fullmatch(outcome["provider_order_id"]) is not None
                  and _PROVIDER_ID.fullmatch(outcome["provider_client_order_id"]) is not None
                  and isinstance(outcome.get("provider_readback_sha256"), str)
                  and re.fullmatch(r"[0-9a-f]{64}", outcome["provider_readback_sha256"]) is not None
                  and isinstance(outcome.get("instrument_preflight_sha256"), str)
                  and re.fullmatch(r"[0-9a-f]{64}", outcome["instrument_preflight_sha256"]) is not None)
                 or (status == "rejected"
                     and outcome.get("provider_mutation_attempted") is False
                     and outcome.get("orders_attempted") == 0
                     and outcome.get("orders_submitted") == 0
                     and (outcome.get("instrument_preflight_sha256") is None
                          or (isinstance(outcome.get("instrument_preflight_sha256"), str)
                              and re.fullmatch(r"[0-9a-f]{64}", outcome["instrument_preflight_sha256"]) is not None)))
                 or (status == "uncertain"
                     and outcome.get("provider_mutation_attempted") is True
                     and outcome.get("orders_attempted") == 1
                     and outcome.get("orders_submitted") is None
                     and isinstance(outcome.get("instrument_preflight_sha256"), str)
                     and re.fullmatch(r"[0-9a-f]{64}", outcome["instrument_preflight_sha256"]) is not None))
        )
        if not valid_live:
            raise CollectorError("terminal_live_outcome_invalid")
        capabilities = None
    provider_readback = outcome.get("provider_readback") if is_probe else None
    provider_summary = None
    if provider_readback is not None:
        try:
            provider_readback = validate_provider_probe_readback(
                provider_readback,
                source_revision=intent["source_revision"],
                now_ms=current,
            )
        except (ContractError, KeyError, TypeError):
            raise CollectorError("terminal_provider_readback_invalid")
        providers = provider_readback["providers"]
        provider_summary = {
            "provider_count": 4, "all_authenticated": True,
            "instrument_preflight_enforced": True,
            "provider_accounts_sha256": provider_readback["provider_accounts_sha256"],
            "execution_budget_readiness_sha256": provider_readback[
                "execution_budget_readiness_sha256"
            ],
            "readback_sha256": provider_readback["readback_sha256"],
            "providers": {
                venue: {"authenticated": True, "account_binding_sha256": row["account_binding_sha256"]}
                for venue, row in providers.items()
            },
        }
    if not (
        review["intent_id"] == dispatch["intent_id"] == executor["intent_id"]
        == terminal["intent_id"] == intent["intent_id"]
        and review["prior_sha256"] == digest(intent)
        and dispatch["prior_sha256"] == digest(review)
        and executor["prior_sha256"] == digest(dispatch)
        and terminal["prior_sha256"] == digest(executor)
        and outcome.get("dispatch_sha256") == digest(dispatch)
        and intent["created_at_ms"] <= review["signed_at_ms"] <= intent["expires_at_ms"]
        and intent["created_at_ms"] <= dispatch["signed_at_ms"] <= intent["expires_at_ms"]
        and intent["created_at_ms"] <= executor["signed_at_ms"] <= intent["expires_at_ms"]
        and intent["created_at_ms"] <= terminal["signed_at_ms"] <= intent["expires_at_ms"]
    ):
        raise CollectorError("terminal_chain_join_invalid")
    readiness_summary = None
    if is_probe and periodic_readiness_probe(intent):
        statement = outcome["readiness_attestation"]["statement"]
        readiness_summary = {
            key: statement[key]
            for key in (
                "source_revision", "release_generation", "release_request_id",
                "release_state_sha256", "authorization_event_sha256",
                "authorization_expires_at_ms", "provider_accounts_sha256",
                "provider_readback_sha256", "execution_budget_readiness_sha256",
                "maximum_order_usd", "provider_count", "all_authenticated",
                "provider_mutation_attempted", "orders_attempted", "orders_submitted",
                "observed_at_ms", "expires_at_ms",
            )
        }
        readiness_summary["executor_attestation_sha256"] = digest(
            outcome["readiness_attestation"],
        )
    return {
        "intent_id": intent["intent_id"],
        "intent_created_at_ms": intent["created_at_ms"],
        "source_revision": intent["source_revision"],
        "runtime_measurement_sha256": intent["runtime_measurement_sha256"],
        "receipt_sha256": digest(terminal),
        "stage_ids": {
            "review": review["stage_id"], "dispatch": dispatch["stage_id"],
            "executor": executor["stage_id"], "receipt": terminal["stage_id"],
        },
        "authority_ids": {
            "review": review["authority_id"], "dispatch": dispatch["authority_id"],
            "executor": executor["authority_id"], "receipt": terminal["authority_id"],
        },
        "key_versions": dict(KEYS),
        "provider_mutation_attempted": outcome["provider_mutation_attempted"],
        "orders_attempted": outcome["orders_attempted"],
        "orders_submitted": outcome["orders_submitted"],
        "dry_run": bool(intent["dry_run"]),
        "chain_verified": True,
        "outcome_status": outcome["status"],
        "venue": intent["order"]["venue"] if intent["order"] else None,
        "provider_order_id": outcome.get("provider_order_id"),
        "provider_client_order_id": outcome.get("provider_client_order_id"),
        "provider_status": outcome.get("provider_status"),
        "provider_readback_sha256": outcome.get("provider_readback_sha256"),
        "instrument_preflight_sha256": outcome.get("instrument_preflight_sha256"),
        "instrument_readiness_blocker": (
            dict(outcome["instrument_readiness_blocker"])
            if isinstance(outcome.get("instrument_readiness_blocker"), Mapping) else None
        ),
        "executor_capabilities": dict(capabilities) if isinstance(capabilities, Mapping) else None,
        "provider_readback": provider_summary,
        "periodic_readiness": readiness_summary,
    }


def _durable_write(path: Path, value: Mapping[str, Any], *, shared: bool = False) -> None:
    if not path.is_absolute() or path.exists() and path.is_symlink():
        raise CollectorError("receipt_output_path_invalid")
    path.parent.mkdir(parents=True, exist_ok=True)
    parent = path.parent.resolve(strict=True)
    if path.resolve().parent != parent:
        raise CollectorError("receipt_output_path_invalid")
    data = json.dumps(value, sort_keys=True, indent=2, allow_nan=False).encode() + b"\n"
    handle, temporary = tempfile.mkstemp(prefix=".receipt-", dir=parent)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, 0o640 if shared else 0o600)
        os.replace(temporary, path)
        if os.name == "posix":
            directory = os.open(parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def pull_once(*, output: Path = DEFAULT_OUTPUT, reader=_http,
              current_time=time.time) -> bool:
    token = access_token(reader)
    headers = {"Authorization": "Bearer " + token, "Content-Type": "application/json"}
    pulled = _cloud_json(reader(
        PUBSUB + ":pull", method="POST", headers=headers,
        body=b'{"maxMessages":1}', timeout=30,
    ), "pubsub_pull_response_invalid")
    rows = pulled.get("receivedMessages", [])
    if rows == []:
        return False
    if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], Mapping):
        raise CollectorError("pubsub_pull_response_invalid")
    row = rows[0]
    message = row.get("message")
    ack_id = row.get("ackId")
    if not isinstance(message, Mapping) or not isinstance(ack_id, str) or not ack_id:
        raise CollectorError("pubsub_pull_response_invalid")
    message_id = message.get("messageId")
    encoded = message.get("data")
    if not isinstance(message_id, str) or not _MESSAGE_ID.fullmatch(message_id):
        raise CollectorError("pubsub_message_id_invalid")
    if not isinstance(encoded, str) or not 0 < len(encoded) <= 1_000_000:
        raise CollectorError("pubsub_message_data_invalid")
    try:
        wire = base64.b64decode(encoded, validate=True)
        receipt = json.loads(wire)
    except (ValueError, TypeError, UnicodeError, binascii.Error) as exc:
        raise CollectorError("pubsub_message_data_invalid") from exc
    if not isinstance(receipt, dict) or canonical_bytes(receipt) != wire:
        raise CollectorError("pubsub_terminal_receipt_not_canonical")
    summary = verify_terminal_receipt(
        receipt, token=token, now_ms=int(float(current_time()) * 1000), reader=reader,
    )
    stored = {
        "schema": "aureon.cloud-trade-terminal-readback.v1",
        "received_at": float(current_time()),
        "pubsub_message_id": message_id,
        "receipt": summary,
        "production_ready": False,
        "release_authority": False,
        "mutation_authority": False,
    }
    live_output = Path(
        os.environ.get("AUREON_CLOUD_TRADE_LIVE_READBACK_PATH")
        or str(DEFAULT_LIVE_OUTPUT)
    )
    target = live_output if output == DEFAULT_OUTPUT and summary["dry_run"] is False else output
    _durable_write(target, stored, shared=target == DEFAULT_OUTPUT)
    reader(
        PUBSUB + ":acknowledge", method="POST", headers=headers,
        body=json.dumps({"ackIds": [ack_id]}, separators=(",", ":")).encode(), timeout=8,
    )
    return True


def run(*, revision: str, output: Path = DEFAULT_OUTPUT,
        probe_interval: float = PROBE_INTERVAL_SECONDS) -> None:
    if not _REVISION.fullmatch(str(revision or "")):
        raise CollectorError("probe_revision_invalid")
    if not math.isfinite(probe_interval) or not 30 <= probe_interval <= 240:
        raise CollectorError("probe_interval_invalid")
    next_probe = 0.0
    next_intent_bridge = 0.0
    state_path = Path(
        os.environ.get("AUREON_ORDER_INTENT_STATE_PATH") or str(DEFAULT_STATE)
    )
    status_path = Path(
        os.environ.get("AUREON_ORDER_INTENT_STATUS_PATH") or str(DEFAULT_STATUS)
    )
    intent_bridge = OrderIntentBridge(
        revision=revision, state_path=state_path, status_path=status_path,
    )
    while True:
        current = time.time()
        if current >= next_intent_bridge:
            try:
                intent_bridge.cycle()
            except IntentBridgeError as exc:
                print(str(exc), file=sys.stderr, flush=True)
            next_intent_bridge = current + BRIDGE_INTERVAL_SECONDS
        if current >= next_probe:
            try:
                release, _release_error = intent_bridge.controller_reader(
                    reader=intent_bridge.http_reader,
                )
                published = publish_control_probe(revision=revision, release=release)
                next_probe = current + (probe_interval if published is not None else 60.0)
            except CollectorError as exc:
                print(str(exc), file=sys.stderr, flush=True)
                next_probe = current + 30.0
        try:
            if not pull_once(output=output):
                time.sleep(1)
        except CollectorError as exc:
            print(str(exc), file=sys.stderr, flush=True)
            time.sleep(5)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(os.environ.get("AUREON_CLOUD_TRADE_READBACK_PATH") or DEFAULT_OUTPUT),
    )
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--revision")
    args = parser.parse_args()
    if args.once:
        print(json.dumps({"collected": pull_once(output=args.output)}))
    else:
        if not args.revision:
            parser.error("--revision is required for continuous collection")
        run(revision=args.revision, output=args.output)


if __name__ == "__main__":
    main()
