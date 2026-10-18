"""Join the five repository layers without inventing a reading or an action.

Aureon OS is the operating layer. Skaila is evidence. Nexus is the public
field. Project Sero is the public market. The founder mirror is the decision
contract. Sample scores and simulators stay out of the join. The action gate
stays closed.
"""

from __future__ import annotations

import hashlib
import importlib.util
import os
import re
from pathlib import Path
from typing import Any, Callable, Mapping

SCHEMA = "aureon.repository-layers.v1"
_DIGEST = r"^[0-9a-f]{64}$"

_NEXUS_SOURCE = "https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json"
_MARKET_SOURCE = "https://data-api.binance.vision/api/v3/ticker/price?symbol=BTCUSDT"


def _repos_root(explicit: Path | None) -> Path:
    if explicit is not None:
        return explicit.resolve()
    env = os.environ.get("AUREON_REPOS_ROOT")
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parents[3]


def _contained(root: Path, relative: str) -> Path | None:
    path = (root / relative).resolve()
    if path != root.resolve() and root.resolve() not in path.parents:
        return None
    return path if path.is_file() else None


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _base(layer_id: str, repo: str, role: str, capability: str) -> dict[str, Any]:
    return {
        "id": layer_id,
        "repo": repo,
        "role": role,
        "capability": capability,
        "gate": "HOLD",
        "may_act": False,
        "generated_values": False,
        "truth_status": "no_data",
        "reason": "observation_unavailable",
        "capability_sha256": None,
        "observation": None,
    }


def _accept_observation(observation: Mapping[str, Any], source: str, schema: str) -> dict[str, Any]:
    if (
        observation.get("schema") != schema
        or observation.get("source") != source
        or observation.get("generated_values") is not False
        or observation.get("may_act") is not False
        or not isinstance(observation.get("payload_sha256"), str)
    ):
        raise ValueError("source_bound_observation_required")
    if re.fullmatch(_DIGEST, observation["payload_sha256"]) is None:
        raise ValueError("source_bound_observation_required")
    return dict(observation)


def _field_layer(root: Path, transport: Callable[[str], bytes] | None) -> dict[str, Any]:
    layer = _base("nexus", "NEXUS-LIVE-FEED-", "field", "public planetary K-index")
    path = _contained(root / "NEXUS-LIVE-FEED-", "organism/public_field.py")
    if path is None:
        layer["reason"] = "field_capability_missing"
        return layer
    layer["capability_sha256"] = _sha256(path)
    module = _load(path, "nexus_public_field")
    if getattr(module, "SOURCE", None) != _NEXUS_SOURCE:
        layer["reason"] = "field_source_rejected"
        return layer
    observation = module.observe_planetary_k_index(transport)
    layer["observation"] = _accept_observation(observation, _NEXUS_SOURCE, "nexus.public-field.v1")
    layer["truth_status"] = "real_observed"
    layer["reason"] = None
    return layer


def _market_layer(root: Path, transport: Callable[[str], bytes] | None) -> dict[str, Any]:
    layer = _base("sero", "Aureon-Trading--Project-Sero", "market", "public BTCUSDT price")
    path = _contained(root / "Aureon-Trading--Project-Sero", "organism/public_market.py")
    if path is None:
        layer["reason"] = "market_capability_missing"
        return layer
    layer["capability_sha256"] = _sha256(path)
    module = _load(path, "sero_public_market")
    if getattr(module, "SOURCE", None) != _MARKET_SOURCE:
        layer["reason"] = "market_source_rejected"
        return layer
    observation = module.observe_public_price(transport)
    if observation.get("order_count") != 0:
        raise ValueError("market_observation_must_not_order")
    layer["observation"] = _accept_observation(observation, _MARKET_SOURCE, "sero.public-market.v1")
    layer["truth_status"] = "real_observed"
    layer["reason"] = None
    return layer


def _evidence_layer(root: Path, evidence: Mapping[str, Any] | None) -> dict[str, Any]:
    layer = _base("skaila", "skaila-journey-platform", "evidence", "assessment gate")
    policy = _contained(root / "skaila-journey-platform", "spec/build-pack/aureon-gate-policy.yaml")
    if policy is not None:
        layer["capability_sha256"] = _sha256(policy)
    if not evidence:
        layer["reason"] = "evidence_observation_required"
        return layer
    authority = evidence.get("authority")
    if authority != "imported":
        layer["reason"] = "sample_or_synthetic_evidence_excluded"
        return layer
    digest = evidence.get("manifest_sha256")
    gate = evidence.get("gate")
    if not isinstance(digest, str) or re.fullmatch(_DIGEST, digest) is None or gate not in {"HOLD", "RELEASE"}:
        layer["reason"] = "imported_evidence_metadata_required"
        return layer
    readiness = evidence.get("readiness")
    adoption = evidence.get("adoption")
    if (
        isinstance(readiness, bool)
        or isinstance(adoption, bool)
        or not isinstance(readiness, (int, float))
        or not isinstance(adoption, (int, float))
    ):
        layer["reason"] = "imported_evidence_metadata_required"
        return layer
    layer["observation"] = {
        "schema": "skaila.imported-evidence.v1",
        "authority": "imported",
        "gate": gate,
        "readiness": readiness,
        "adoption": adoption,
        "manifest_sha256": digest,
        "generated_values": False,
        "may_act": False,
    }
    layer["truth_status"] = "real_observed"
    layer["gate"] = gate
    layer["reason"] = None
    return layer


def _founder_layer(root: Path) -> dict[str, Any]:
    layer = _base(
        "founder-mirror",
        "aureon-founder-mirror",
        "decision",
        "draft decision contract",
    )
    path = _contained(root / "aureon-founder-mirror", "README.md")
    if path is None:
        layer["reason"] = "decision_contract_missing"
        return layer
    text = path.read_text(encoding="utf-8")[:4000]
    if "HOLD" not in text or "never sends" not in text.lower():
        layer["reason"] = "decision_contract_rejected"
        return layer
    layer["capability_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    layer["observation"] = {
        "schema": "founder.decision-contract.v1",
        "sends": False,
        "spends": False,
        "signs": False,
        "generated_values": False,
        "may_act": False,
    }
    layer["truth_status"] = "real_observed"
    layer["reason"] = None
    return layer


def _operating_layer() -> dict[str, Any]:
    layer = _base("aureon-os", "Aureon-OS", "operating", "canonical organism composition")
    root = Path(__file__).resolve().parents[2]
    path = _contained(root, "aureon/core/organism_composition.py")
    if path is None:
        layer["reason"] = "operating_capability_missing"
        return layer
    layer["capability_sha256"] = _sha256(path)
    from aureon.core.organism_composition import get_canonical_organism_composition

    seated = get_canonical_organism_composition()
    layer["observation"] = {
        "schema": "aureon.operating-layer.v1",
        "canonical_composition_seated": seated is not None,
        "generated_values": False,
        "may_act": False,
    }
    layer["truth_status"] = "real_derived"
    layer["reason"] = None if seated is not None else "canonical_composition_unseated"
    return layer


def _guard(builder: Callable[[], dict[str, Any]], layer_id: str, repo: str, role: str) -> dict[str, Any]:
    try:
        layer = builder()
    except (OSError, ValueError, TypeError, ImportError, TimeoutError) as exc:
        layer = _base(layer_id, repo, role, "unavailable")
        layer["reason"] = str(exc)[:160] or "observation_unavailable"
    if layer.get("may_act") is not False or layer.get("generated_values") is not False:
        rejected = _base(layer_id, repo, role, "rejected")
        rejected["reason"] = "layer_action_rejected"
        return rejected
    return layer


def compose_repository_layers(
    repos_root: Path | None = None,
    evidence: Mapping[str, Any] | None = None,
    field_transport: Callable[[str], bytes] | None = None,
    market_transport: Callable[[str], bytes] | None = None,
) -> dict[str, Any]:
    """Read each layer once and return the joined hold."""

    root = _repos_root(repos_root)
    layers = [
        _guard(_operating_layer, "aureon-os", "Aureon-OS", "operating"),
        _guard(lambda: _evidence_layer(root, evidence), "skaila", "skaila-journey-platform", "evidence"),
        _guard(lambda: _field_layer(root, field_transport), "nexus", "NEXUS-LIVE-FEED-", "field"),
        _guard(lambda: _market_layer(root, market_transport), "sero", "Aureon-Trading--Project-Sero", "market"),
        _guard(lambda: _founder_layer(root), "founder-mirror", "aureon-founder-mirror", "decision"),
    ]
    return {
        "schema": SCHEMA,
        "status": "hold",
        "reason": "action_authority_remains_closed",
        "generated_values": False,
        "action_eligible": False,
        "economic_mutation": False,
        "may_act": False,
        "layers": layers,
    }
