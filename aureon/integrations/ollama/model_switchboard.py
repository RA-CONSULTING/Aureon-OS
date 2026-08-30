"""Dynamic Ollama model switchboard for Aureon's cognitive nerve lanes.

The configured Ollama endpoint is the live catalog authority.  The switchboard
refreshes that catalog and routes each type of thought to a suitable model
instead of pinning the whole organism to one hard-coded name.  Explicit lane
environment overrides win only when that model is present in the current
catalog; otherwise selection degrades to the best available catalog member.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import threading
import time
from dataclasses import asdict, dataclass
from typing import Any, Callable, Dict, Iterable, Mapping

from aureon.integrations.ollama.ollama_bridge import OllamaBridge

LANES = ("coding", "architecture", "self_evolution", "fast", "general")
PHI = (1.0 + math.sqrt(5.0)) / 2.0
PHI_INV = 1.0 / PHI
LIGHTHOUSE_THRESHOLD = 0.945
ACTIVE_THRESHOLD = 0.80
HNC_ROUTE_SCHEMA = "aureon-ollama-hnc-nerve-route-v1"
LANE_ENV = {
    "coding": "AUREON_OLLAMA_CODING_MODEL",
    "architecture": "AUREON_OLLAMA_ARCHITECTURE_MODEL",
    "self_evolution": "AUREON_OLLAMA_SELF_EVOLUTION_MODEL",
    "fast": "AUREON_OLLAMA_FAST_MODEL",
    "general": "AUREON_OLLAMA_GENERAL_MODEL",
}
LANE_HINTS: Dict[str, tuple[tuple[str, int], ...]] = {
    "coding": (
        ("code", 14),
        ("coder", 14),
        ("deepseek", 6),
        ("qwen", 5),
        ("kimi", 4),
        ("pro", 3),
        ("flash", -3),
    ),
    "architecture": (
        ("ultra", 12),
        ("pro", 10),
        ("675b", 9),
        ("397b", 9),
        ("120b", 7),
        ("large", 6),
        ("reason", 6),
        ("flash", -5),
        ("nano", -6),
    ),
    "self_evolution": (
        ("code", 8),
        ("pro", 7),
        ("ultra", 7),
        ("qwen", 6),
        ("kimi", 6),
        ("deepseek", 5),
        ("flash", -3),
    ),
    "fast": (
        ("flash", 14),
        ("nano", 12),
        ("20b", 7),
        ("mini", 7),
        ("preview", 2),
        ("675b", -8),
        ("397b", -7),
        ("ultra", -5),
    ),
    "general": (
        ("k3", 12),
        ("k2.7", 9),
        ("kimi", 7),
        ("mistral", 6),
        ("glm", 5),
        ("gemma", 5),
        ("qwen", 5),
        ("gpt-oss", 4),
        ("code", -20),
        ("coder", -20),
    ),
}

_SHARED_CATALOGS: Dict[str, tuple[float, bool, list[str], str]] = {}
_SHARED_CATALOG_LOCK = threading.Lock()
_SHARED_MODEL_PROBES: Dict[tuple[str, str], tuple[float, bool, str]] = {}
_SHARED_MODEL_PROBE_LOCK = threading.Lock()


@dataclass(frozen=True)
class OllamaModelSelection:
    lane: str
    model: str
    source: str
    catalog_size: int
    endpoint_reachable: bool
    catalog_refreshed_at: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class HNCModelRoutingReceipt:
    """Evidence-only binding between one nerve, the HNC field, and one cloud model."""

    schema_version: str
    decision: str
    reason: str
    nerve_id: str
    lane: str
    model: str
    provider_mode: str
    hnc_receipt_id: str
    hnc_source_timestamp: float | None
    coherence_gamma: float | None
    consciousness_psi: float | None
    lambda_t: float | None
    coherence_band: str
    catalog_digest: str
    catalog_size: int
    candidate_count: int
    selected_rank: int | None
    selection_source: str
    issued_at: float
    action_eligible: bool
    economic_eligible: bool
    receipt_id: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _canonical_json(value: Mapping[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def _sha256(value: Any) -> str:
    payload = value if isinstance(value, str) else _canonical_json(value)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _routing_causal(receipt: HNCModelRoutingReceipt) -> Dict[str, Any]:
    payload = receipt.to_dict()
    payload.pop("receipt_id", None)
    return payload


def validate_hnc_model_routing_receipt(receipt: HNCModelRoutingReceipt) -> bool:
    if not isinstance(receipt, HNCModelRoutingReceipt) or receipt.schema_version != HNC_ROUTE_SCHEMA:
        return False
    if receipt.decision not in {"ROUTE", "HOLD"}:
        return False
    if receipt.action_eligible is not False or receipt.economic_eligible is not False:
        return False
    if not receipt.nerve_id or receipt.lane not in LANES or receipt.provider_mode != "ollama_cloud_primary":
        return False
    if type(receipt.catalog_size) is not int or receipt.catalog_size < 0:
        return False
    if type(receipt.candidate_count) is not int or receipt.candidate_count < 0:
        return False
    if type(receipt.issued_at) not in {int, float} or isinstance(receipt.issued_at, bool):
        return False
    if not math.isfinite(float(receipt.issued_at)) or float(receipt.issued_at) <= 0:
        return False
    if receipt.decision == "ROUTE":
        metrics = (
            receipt.hnc_source_timestamp,
            receipt.coherence_gamma,
            receipt.consciousness_psi,
            receipt.lambda_t,
        )
        if (
            not receipt.model
            or not receipt.hnc_receipt_id.startswith("hnc:live_field:")
            or receipt.coherence_band not in {"lighthouse", "active", "organizing", "low"}
            or not receipt.catalog_digest
            or len(receipt.catalog_digest) != 64
            or type(receipt.selected_rank) is not int
            or receipt.selected_rank < 1
            or receipt.selected_rank > receipt.candidate_count
            or not receipt.selection_source.startswith("live_probe_passed:hnc_")
            or any(type(value) not in {int, float} or isinstance(value, bool) for value in metrics)
            or any(not math.isfinite(float(value)) for value in metrics)
            or not 0.0 <= float(receipt.coherence_gamma) <= 1.0
        ):
            return False
    elif (
        receipt.model
        or receipt.hnc_receipt_id
        or receipt.hnc_source_timestamp is not None
        or receipt.coherence_gamma is not None
        or receipt.consciousness_psi is not None
        or receipt.lambda_t is not None
        or receipt.coherence_band != "no_data"
        or receipt.selected_rank is not None
        or receipt.selection_source != "no_data"
    ):
        return False
    return receipt.receipt_id == f"ollama:hnc-route:{_sha256(_routing_causal(receipt))}"


class OllamaModelSwitchboard:
    """Route Aureon thought lanes across the live Ollama model catalog."""

    def __init__(
        self,
        bridge: OllamaBridge | None = None,
        *,
        catalog_ttl_s: float = 60.0,
        field_reader: Callable[[], Any] | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.bridge = bridge or OllamaBridge()
        self.catalog_ttl_s = max(1.0, float(catalog_ttl_s))
        self._field_reader = field_reader
        self._clock = clock
        self._catalog: list[str] = []
        self._reachable = False
        self._refreshed_at = 0.0
        self._last_error = ""
        self._last_nerve_routes: Dict[str, HNCModelRoutingReceipt] = {}

    @staticmethod
    def _coherence_band(gamma: float) -> str:
        if gamma >= LIGHTHOUSE_THRESHOLD:
            return "lighthouse"
        if gamma >= ACTIVE_THRESHOLD:
            return "active"
        if gamma >= PHI_INV:
            return "organizing"
        return "low"

    def _read_hnc_field(self) -> Any:
        if self._field_reader is not None:
            return self._field_reader()
        from aureon.core.hnc_field import read_canonical_field

        return read_canonical_field()

    def capture_hnc_field(self) -> Any:
        """Capture one canonical HNC moment for a complete nerve generation."""

        return self._read_hnc_field()

    @staticmethod
    def _band_adjustment(model: str, band: str) -> int:
        lower = model.lower()
        large = any(token in lower for token in ("675b", "397b", "120b", "ultra", "large"))
        fast = any(token in lower for token in ("flash", "nano", "20b", "mini"))
        stable = any(token in lower for token in ("kimi-k2.6", "mistral", "gpt-oss", "nemotron"))
        if band == "lighthouse":
            return (8 if large else 0) + (2 if stable else 0)
        if band == "active":
            return (4 if stable else 0) + (2 if large else 0)
        if band == "organizing":
            return (8 if fast else 0) + (4 if stable else 0) - (8 if large else 0)
        return (14 if fast else 0) + (2 if stable else 0) - (16 if large else 0)

    def _hnc_ranked_models(self, lane: str, gamma: float) -> list[str]:
        lane_name = lane if lane in LANES else "general"
        catalog = self.refresh()
        hints = LANE_HINTS[lane_name]
        band = self._coherence_band(gamma)

        def score(item: tuple[int, str]) -> tuple[int, int]:
            index, name = item
            lower = name.lower()
            lane_score = sum(weight for token, weight in hints if token in lower)
            return lane_score + self._band_adjustment(name, band), -index

        return [name for _, name in sorted(enumerate(catalog), key=score, reverse=True)]

    def _hold_route(self, *, nerve_id: str, lane: str, reason: str) -> HNCModelRoutingReceipt:
        receipt = HNCModelRoutingReceipt(
            schema_version=HNC_ROUTE_SCHEMA,
            decision="HOLD",
            reason=reason,
            nerve_id=nerve_id,
            lane=lane,
            model="",
            provider_mode="ollama_cloud_primary",
            hnc_receipt_id="",
            hnc_source_timestamp=None,
            coherence_gamma=None,
            consciousness_psi=None,
            lambda_t=None,
            coherence_band="no_data",
            catalog_digest="",
            catalog_size=len(self._catalog),
            candidate_count=0,
            selected_rank=None,
            selection_source="no_data",
            issued_at=self._clock(),
            action_eligible=False,
            economic_eligible=False,
            receipt_id="",
        )
        return HNCModelRoutingReceipt(
            **{
                **receipt.to_dict(),
                "receipt_id": f"ollama:hnc-route:{_sha256(_routing_causal(receipt))}",
            }
        )

    def route_nerve(
        self,
        lane: str,
        *,
        nerve_id: str,
        hnc_field: Any = None,
        max_attempts: int = 8,
        force_probe: bool = False,
    ) -> tuple[OllamaModelSelection, HNCModelRoutingReceipt]:
        """Choose one callable cloud model using the live HNC field and nerve identity."""

        lane_name = str(lane or "general").strip().lower()
        nerve = str(nerve_id or "").strip()
        if lane_name not in LANES or not nerve:
            safe_lane = lane_name if lane_name in LANES else "general"
            hold = self._hold_route(nerve_id=nerve or "invalid", lane=safe_lane, reason="valid_nerve_required")
            return self.select(safe_lane), hold
        field = hnc_field if hnc_field is not None else self._read_hnc_field()
        gamma = getattr(field, "coherence_gamma", None)
        psi = getattr(field, "consciousness_psi", None)
        lambda_t = getattr(field, "lambda_t", None)
        source_timestamp = getattr(field, "source_timestamp", None)
        hnc_receipt_id = str(getattr(field, "receipt_id", "") or "")
        metrics = (gamma, psi, lambda_t, source_timestamp)
        if (
            getattr(field, "available", False) is not True
            or not hnc_receipt_id.startswith("hnc:live_field:")
            or any(type(value) not in {int, float} or isinstance(value, bool) for value in metrics)
            or any(not math.isfinite(float(value)) for value in metrics)
            or not 0.0 <= float(gamma) <= 1.0
        ):
            hold = self._hold_route(nerve_id=nerve, lane=lane_name, reason="fresh_canonical_hnc_field_required")
            self._last_nerve_routes[nerve] = hold
            return self.select(lane_name), hold
        if not getattr(self.bridge, "base_url", "").startswith("https://ollama.com"):
            hold = self._hold_route(nerve_id=nerve, lane=lane_name, reason="ollama_cloud_primary_required")
            self._last_nerve_routes[nerve] = hold
            return self.select(lane_name), hold
        ranked_models = self._hnc_ranked_models(lane_name, float(gamma))
        band = self._coherence_band(float(gamma))
        window = {"lighthouse": 5, "active": 3, "organizing": 1, "low": 1}[band]
        candidates = ranked_models[: max(1, min(window, len(ranked_models)))]
        if candidates:
            phase = int(_sha256(f"{nerve}|{hnc_receipt_id}|{lane_name}")[:8], 16) % len(candidates)
            candidates = candidates[phase:] + candidates[:phase]
        candidates.extend(model for model in ranked_models if model not in candidates)
        selected: OllamaModelSelection | None = None
        selected_rank: int | None = None
        for index, model in enumerate(candidates[: max(1, int(max_attempts))], start=1):
            candidate = OllamaModelSelection(
                lane=lane_name,
                model=model,
                source=f"hnc_{band}:ranked_live_catalog",
                catalog_size=len(self._catalog),
                endpoint_reachable=self._reachable,
                catalog_refreshed_at=self._refreshed_at,
            )
            ok, _detail = self._probe_selection(candidate, force=force_probe)
            if ok:
                selected = OllamaModelSelection(
                    **{
                        **candidate.to_dict(),
                        "source": f"live_probe_passed:{candidate.source}",
                    }
                )
                selected_rank = index
                break
        if selected is None:
            hold = self._hold_route(nerve_id=nerve, lane=lane_name, reason="no_callable_hnc_ranked_cloud_model")
            self._last_nerve_routes[nerve] = hold
            return self.select(lane_name), hold
        receipt = HNCModelRoutingReceipt(
            schema_version=HNC_ROUTE_SCHEMA,
            decision="ROUTE",
            reason="callable_cloud_model_selected_by_hnc_nerve_profile",
            nerve_id=nerve,
            lane=lane_name,
            model=selected.model,
            provider_mode="ollama_cloud_primary",
            hnc_receipt_id=hnc_receipt_id,
            hnc_source_timestamp=float(source_timestamp),
            coherence_gamma=float(gamma),
            consciousness_psi=float(psi),
            lambda_t=float(lambda_t),
            coherence_band=band,
            catalog_digest=_sha256(self._catalog),
            catalog_size=len(self._catalog),
            candidate_count=len(candidates),
            selected_rank=selected_rank,
            selection_source=selected.source,
            issued_at=self._clock(),
            action_eligible=False,
            economic_eligible=False,
            receipt_id="",
        )
        receipt = HNCModelRoutingReceipt(
            **{
                **receipt.to_dict(),
                "receipt_id": f"ollama:hnc-route:{_sha256(_routing_causal(receipt))}",
            }
        )
        if not validate_hnc_model_routing_receipt(receipt):
            hold = self._hold_route(nerve_id=nerve, lane=lane_name, reason="hnc_routing_receipt_invalid")
            self._last_nerve_routes[nerve] = hold
            return self.select(lane_name), hold
        self._last_nerve_routes[nerve] = receipt
        return selected, receipt

    def refresh(self, *, force: bool = False) -> list[str]:
        now = time.time()
        if not force and self._refreshed_at and now - self._refreshed_at <= self.catalog_ttl_s:
            return list(self._catalog)
        shared_key = str(getattr(self.bridge, "base_url", "") or "") if type(self.bridge) is OllamaBridge else ""
        if shared_key and not force:
            with _SHARED_CATALOG_LOCK:
                shared = _SHARED_CATALOGS.get(shared_key)
            if shared and now - shared[0] <= self.catalog_ttl_s:
                self._refreshed_at, self._reachable, catalog, self._last_error = shared
                self._catalog = list(catalog)
                return list(self._catalog)
        try:
            snapshot = self.bridge.snapshot()
            self._reachable = bool(snapshot.get("reachable"))
            self._catalog = list(
                dict.fromkeys(str(item).strip() for item in snapshot.get("models", []) if str(item).strip())
            )
            self._last_error = str(snapshot.get("error") or "")[:240]
        except Exception as exc:
            self._reachable = False
            self._catalog = []
            self._last_error = type(exc).__name__
        self._refreshed_at = now
        if shared_key:
            with _SHARED_CATALOG_LOCK:
                _SHARED_CATALOGS[shared_key] = (
                    self._refreshed_at,
                    self._reachable,
                    list(self._catalog),
                    self._last_error,
                )
        return list(self._catalog)

    @staticmethod
    def _installed_name(preferred: str, catalog: list[str]) -> str:
        wanted = str(preferred or "").strip().lower()
        if not wanted:
            return ""
        for model in catalog:
            if model.lower() == wanted:
                return model
        return ""

    @staticmethod
    def _probe_error_category(error: str) -> str:
        lowered = str(error or "").lower()
        for token, category in (
            ("402", "payment_required"),
            ("payment required", "payment_required"),
            ("401", "unauthorized"),
            ("403", "forbidden"),
            ("404", "model_not_found"),
            ("429", "rate_limited"),
            ("timed out", "timeout"),
            ("timeout", "timeout"),
        ):
            if token in lowered:
                return category
        return "request_error" if lowered else "empty_probe_response"

    def rank(
        self,
        lane: str,
        *,
        limit: int | None = None,
        preferred: str = "",
        exclude: Iterable[str] = (),
        force_refresh: bool = False,
    ) -> list[OllamaModelSelection]:
        """Rank live catalog members for a nerve lane.

        Swarm callers use this to recruit different currently available
        models without inventing or pinning model names.  Explicit lane
        overrides lead the ranking only when the live endpoint reports them.
        """
        lane_name = str(lane or "general").strip().lower()
        if lane_name not in LANES:
            lane_name = "general"
        catalog = self.refresh(force=force_refresh)
        excluded = {str(item).strip().lower() for item in exclude if str(item).strip()}
        configured = (
            preferred
            or os.environ.get(LANE_ENV[lane_name], "")
            or (os.environ.get("AUREON_CODE_MODEL", "") if lane_name == "coding" else "")
        )
        installed = self._installed_name(configured, catalog)
        hints = LANE_HINTS[lane_name]

        def score(item: tuple[int, str]) -> tuple[int, int]:
            index, name = item
            lower = name.lower()
            value = sum(weight for token, weight in hints if token in lower)
            return value, -index

        ordered = [name for _, name in sorted(enumerate(catalog), key=score, reverse=True)]
        if installed:
            ordered = [installed] + [name for name in ordered if name != installed]
        ordered = [name for name in ordered if name.lower() not in excluded]
        if not ordered and not catalog:
            fallback = str(configured or getattr(self.bridge, "chat_model", "") or "").strip()
            if fallback and fallback.lower() not in excluded:
                ordered = [fallback]
        if limit is not None:
            ordered = ordered[: max(0, int(limit))]
        return [
            OllamaModelSelection(
                lane=lane_name,
                model=model,
                source=(
                    "lane_override_in_live_catalog"
                    if installed and model == installed
                    else "ranked_live_catalog"
                    if catalog
                    else "configured_fallback_catalog_unavailable"
                ),
                catalog_size=len(catalog),
                endpoint_reachable=self._reachable,
                catalog_refreshed_at=self._refreshed_at,
            )
            for model in ordered
        ]

    def select(self, lane: str, *, preferred: str = "", force_refresh: bool = False) -> OllamaModelSelection:
        ranked = self.rank(lane, limit=1, preferred=preferred, force_refresh=force_refresh)
        if ranked:
            return ranked[0]
        lane_name = str(lane or "general").strip().lower()
        if lane_name not in LANES:
            lane_name = "general"
        return OllamaModelSelection(
            lane=lane_name,
            model="",
            source="no_model_available",
            catalog_size=len(self._catalog),
            endpoint_reachable=self._reachable,
            catalog_refreshed_at=self._refreshed_at,
        )

    def _probe_selection(self, selection: OllamaModelSelection, *, force: bool = False) -> tuple[bool, str]:
        """Verify that a catalog entry is callable by the configured account."""

        if not selection.model or not selection.endpoint_reachable:
            return False, "endpoint_or_model_unavailable"
        key = (str(getattr(self.bridge, "base_url", "") or ""), selection.model.lower())
        now = time.time()
        if not force:
            with _SHARED_MODEL_PROBE_LOCK:
                cached = _SHARED_MODEL_PROBES.get(key)
            if cached and now - cached[0] <= self.catalog_ttl_s:
                return cached[1], cached[2]
        try:
            probe_bridge = OllamaBridge(
                base_url=self.bridge.base_url,
                chat_model=selection.model,
                embed_model=self.bridge.embed_model,
                keep_alive=self.bridge.keep_alive,
                timeout_s=min(30.0, self.bridge.timeout_s),
                api_key=None,
            )
            response = probe_bridge.chat(
                [{"role": "user", "content": "Reply OK only."}],
                model=selection.model,
                options={"num_predict": 4, "temperature": 0},
                think=False,
            )
            error = str(response.get("error") or "")[:240]
            content = str((response.get("message") or {}).get("content") or "").strip()
            ok = bool(content) and not error
            detail = "live_probe_passed" if ok else self._probe_error_category(error)
        except Exception as exc:
            ok = False
            detail = type(exc).__name__
        with _SHARED_MODEL_PROBE_LOCK:
            _SHARED_MODEL_PROBES[key] = (now, ok, detail)
        return ok, detail

    def working_selection(
        self,
        lane: str,
        *,
        preferred: str = "",
        max_attempts: int = 5,
        force_probe: bool = False,
    ) -> OllamaModelSelection:
        """Return the highest-ranked catalog model proven callable now."""

        ranked = self.rank(lane, preferred=preferred, limit=max(1, int(max_attempts)))
        for selection in ranked:
            ok, _detail = self._probe_selection(selection, force=force_probe)
            if ok:
                return OllamaModelSelection(
                    lane=selection.lane,
                    model=selection.model,
                    source=f"live_probe_passed:{selection.source}",
                    catalog_size=selection.catalog_size,
                    endpoint_reachable=selection.endpoint_reachable,
                    catalog_refreshed_at=selection.catalog_refreshed_at,
                )
        return ranked[0] if ranked else self.select(lane, preferred=preferred)

    def bridge_for(
        self,
        lane: str,
        *,
        preferred: str = "",
        require_working: bool = True,
    ) -> tuple[OllamaBridge, OllamaModelSelection]:
        selection = (
            self.working_selection(lane, preferred=preferred)
            if require_working
            else self.select(lane, preferred=preferred)
        )
        bridge = OllamaBridge(
            base_url=self.bridge.base_url,
            chat_model=selection.model or self.bridge.chat_model,
            embed_model=self.bridge.embed_model,
            keep_alive=self.bridge.keep_alive,
            timeout_s=self.bridge.timeout_s,
            # Re-resolve from the guarded runtime config so a cloud key is not
            # accidentally treated as an explicit key for a loopback endpoint.
            api_key=None,
        )
        return bridge, selection

    def bridge_for_nerve(
        self,
        lane: str,
        *,
        nerve_id: str,
        hnc_field: Any = None,
    ) -> tuple[OllamaBridge, OllamaModelSelection, HNCModelRoutingReceipt]:
        selection, receipt = self.route_nerve(
            lane,
            nerve_id=nerve_id,
            hnc_field=hnc_field,
        )
        bridge = OllamaBridge(
            base_url=self.bridge.base_url,
            chat_model=selection.model or self.bridge.chat_model,
            embed_model=self.bridge.embed_model,
            keep_alive=self.bridge.keep_alive,
            timeout_s=self.bridge.timeout_s,
            api_key=None,
        )
        return bridge, selection, receipt

    def compatible_adapter_for_nerve(
        self,
        lane: str,
        *,
        nerve_id: str,
        hnc_field: Any = None,
    ) -> tuple[Any, OllamaModelSelection, HNCModelRoutingReceipt]:
        from aureon.inhouse_ai.llm_adapter import AureonLocalAdapter

        selection, receipt = self.route_nerve(
            lane,
            nerve_id=nerve_id,
            hnc_field=hnc_field,
        )
        return (
            AureonLocalAdapter(
                base_url=self.bridge.base_url,
                model=selection.model or None,
            ),
            selection,
            receipt,
        )

    def adapter_for(self, lane: str, *, preferred: str = "") -> tuple[Any, OllamaModelSelection]:
        from aureon.integrations.ollama.ollama_adapter import OllamaLLMAdapter

        bridge, selection = self.bridge_for(lane, preferred=preferred)
        return OllamaLLMAdapter(bridge=bridge, model=selection.model or None), selection

    def compatible_adapter_for(self, lane: str, *, preferred: str = "") -> tuple[Any, OllamaModelSelection]:
        """Build the repo's OpenAI-compatible adapter on a live nerve lane."""

        from aureon.inhouse_ai.llm_adapter import AureonLocalAdapter

        selection = self.working_selection(lane, preferred=preferred)
        return AureonLocalAdapter(model=selection.model or None), selection

    def hybrid_adapter_for(self, lane: str, *, preferred: str = "") -> tuple[Any, OllamaModelSelection]:
        """Build an AureonBrain + Ollama hybrid on a live nerve lane."""

        from aureon.inhouse_ai.llm_adapter import AureonHybridAdapter

        selection = self.working_selection(lane, preferred=preferred)
        return AureonHybridAdapter(model=selection.model or None), selection

    def snapshot(self) -> Dict[str, Any]:
        catalog = self.refresh()
        selections = {lane: self.select(lane).to_dict() for lane in LANES}
        base_url = str(getattr(self.bridge, "base_url", "") or "")
        with _SHARED_MODEL_PROBE_LOCK:
            availability = {
                model: {
                    "last_probe_at": stamp,
                    "working": working,
                    "status": detail,
                }
                for (endpoint, model), (stamp, working, detail) in _SHARED_MODEL_PROBES.items()
                if endpoint == base_url
            }
        working_lanes: Dict[str, Dict[str, Any]] = {}
        for lane in LANES:
            for selection in self.rank(lane):
                state = availability.get(selection.model.lower())
                if state and state.get("working"):
                    working_lanes[lane] = {
                        **selection.to_dict(),
                        "source": f"cached_live_probe:{selection.source}",
                    }
                    break
        return {
            "schema_version": "aureon-ollama-model-switchboard-v2",
            "reachable": self._reachable,
            "catalog_size": len(catalog),
            "catalog": catalog,
            "catalog_refreshed_at": self._refreshed_at,
            "lanes": selections,
            "working_lanes": working_lanes,
            "availability": availability,
            "hnc_nerve_routes": {
                nerve_id: receipt.to_dict()
                for nerve_id, receipt in sorted(self._last_nerve_routes.items())
            },
            "last_error": self._last_error,
            "credential_values_exposed": False,
        }


__all__ = [
    "ACTIVE_THRESHOLD",
    "HNC_ROUTE_SCHEMA",
    "LIGHTHOUSE_THRESHOLD",
    "LANES",
    "LANE_ENV",
    "PHI",
    "PHI_INV",
    "HNCModelRoutingReceipt",
    "OllamaModelSelection",
    "OllamaModelSwitchboard",
    "validate_hnc_model_routing_receipt",
]
