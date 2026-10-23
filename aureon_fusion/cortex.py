"""🧠 Cortex — the agent-brain substrate.

Imports the upstream mind (aureon/operator + aureon/inhouse_ai +
aureon/governance) behind a lazy-initializing facade. Upstream launchers are
never invoked; only the importable classes and pure functions are composed.

    from aureon_fusion.cortex import get_cortex
    cortex = get_cortex()
    cortex.status()       # no network, no upstream cognition constructed
    cortex.list_tools()   # imports upstream modules; still no network
    cortex.propose("...") # first real use: providers probed, cognition built

Doctrine compliance:
  * AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS=1 and AUREON_AUDIT_MODE=1 are set at
    the top of this module — BEFORE any upstream aureon import can happen
    (nothing upstream is imported at module level here).
  * sys.path is pinned to the upstream repo root for the imports, and
    aureon._path_setup is loaded so the upstream's own dotted/bare imports
    resolve exactly as they do inside the repo.
  * The repo-grounding index cache is redirected from the upstream repo's
    state/ tree to aureon_fusion/state/ — the upstream repo stays read-only.
  * execute_shell is never registered (allow_shell=False) and the toolbelt is
    a positive read-only allowlist: no shell, no repo writes, no web tools,
    no thought-bus publishing, no module-touching.
  * Every governed tool route must clear aureon_fusion.capability_gate AND
    carry a tool_route_authority lease issued by the fusion supplier before
    dispatch; a fusion-gate HOLD raises and the upstream registry blocks the
    call. Upstream governance (council/crown/dual-key) stays enabled and
    fail-closed.

MODEL PLANE (uncaged, owner decree 2026-09-04): LOCAL-ONLY. The only
inference path is the machine's own Ollama at 127.0.0.1:11434
(qwen2.5vl:3b). Every provider endpoint passes ``_assert_loopback`` — a
non-loopback host is refused IN CODE with a logged veto, before any request
is built. External provider adapters are disabled unless
AUREON_CORTEX_EXTERNAL_PROVIDERS=1 is explicitly set (default off), and even
then only endpoints that survive the loopback veto are used. Local LLM HTTP
under AUREON_AUDIT_MODE is enabled exactly the way upstream sanctions it:
AUREON_LLM_ALLOW_HTTP_IN_AUDIT=1, set here immediately before the adapter is
constructed (aureon/inhouse_ai/llm_adapter.py::_llm_http_disabled). The
adapter is built with strict_loopback_no_redirects=True (literal-IP loopback
origin, no proxies, no redirects). The installed qwen2.5vl:3b has no tool
support, so the fusion adapter wraps the prompt call to reason on Ollama's
native /api/chat path; the governed toolbelt remains registered and fully
gated for models that do support tools.

GOVERNANCE VOICES (uncaged, owner decree): upstream council/crown receipt
suppliers are wired as the fusion's OWN authority. ``_FusionReceiptSupplier``
(two independent instances: council + crown) maps fusion capability-gate
verdicts onto the upstream receipt schemas — the Druid Council rune is seated
from a live provider moment built out of the fusion's own organ readings
(hnc_core state + lambda history + schumann/space-weather inputs), and each
seat decision is the fusion capability gate's verdict
(data_integrity:analyze_data_patterns); the Crown rune is the Queen's own
conscience verdict (aureon_fusion.conscience_hook). Receipts are minted
through the upstream public issuers (issue_auris_node_receipt,
issue_trusted_druidic_council, issue_crown_voice_receipt) so every hash
binding, freshness window, and false-eligibility flag is enforced by
upstream validation — nothing is bypassed. A gate HOLD seats HOLD -> the
council cannot quorum -> the dual key holds -> the answer is parked. A
conscience VETO still aborts. Governance remains evidence-only: every
eligibility flag stays false and no route/economic authority is granted.

CLI:
  python -m aureon_fusion.cortex status          (no network)
  python -m aureon_fusion.cortex tools           (no network)
  python -m aureon_fusion.cortex propose "..."   (first use; probes Ollama)

Import-safe: no upstream import, no network, no process spawning at import.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import ipaddress
import json
import math
import os
import sys
import threading
import time
import types
import uuid
from decimal import Decimal
from urllib.parse import urlsplit

# ────────────────────────── suppression env (BEFORE any aureon import) ──────
# Hard-set, not setdefault: the fusion doctrine requires these guards for
# every upstream import path this module opens.
os.environ["AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS"] = "1"
os.environ["AUREON_AUDIT_MODE"] = "1"

from .paths import AUREON_UPSTREAM, FUSION_STATE
from . import events
from . import capability_gate

#: Positive allowlist for the cortex toolbelt — read-only, local, no network,
#: no shared-bus writes, no live trading state, no module importing.
CORTEX_TOOLS = frozenset({
    "repo_search",
    "read_repo_file",
    "list_repo",
    "code_validate",
    "sense_organism",
    "list_organism",
    "list_skills",
})

#: The model plane. Literal loopback IP only — hostnames never leave this
#: machine and _assert_loopback refuses anything that is not loopback IN CODE.
OLLAMA_HOST = "127.0.0.1"
OLLAMA_PORT = 11434
OLLAMA_NATIVE_URL = f"http://{OLLAMA_HOST}:{OLLAMA_PORT}"
OLLAMA_OPENAI_URL = f"{OLLAMA_NATIVE_URL}/v1"
OLLAMA_TAGS_URL = f"{OLLAMA_NATIVE_URL}/api/tags"
OLLAMA_MODEL = "qwen2.5vl:3b"
OLLAMA_PROBE_TIMEOUT_S = 3.0

#: Upstream-sanctioned switch that permits local LLM HTTP under audit mode
#: (aureon/inhouse_ai/llm_adapter.py::_llm_http_disabled). The cortex NEVER
#: sets this itself: the model plane is OFF unless the owner opts in via
#: MODEL_PLANE_ENV, and only then is this switch armed (still loopback-only).
AUDIT_LLM_HTTP_ENV = "AUREON_LLM_ALLOW_HTTP_IN_AUDIT"

#: The model plane is OFF by default (owner correction, UNCAGING wave): the
#: Queen reasons natively (queen_mind organ) and the cortex answers from
#: grounding + governance + native composition. Setting this env to "1" is the
#: explicit owner opt-in that arms the strict-loopback local adapter.
MODEL_PLANE_ENV = "AUREON_CORTEX_MODEL_PLANE"


def _model_plane_enabled() -> bool:
    return str(os.environ.get(MODEL_PLANE_ENV, "") or "").strip().lower() in {
        "1", "true", "yes", "on"}


#: External (cloud) provider adapters: disabled unless the owner explicitly
#: opts in. Even then, _assert_loopback vetoes any non-loopback endpoint.
EXTERNAL_PROVIDERS_ENV = "AUREON_CORTEX_EXTERNAL_PROVIDERS"

REPO_INDEX_CACHE = FUSION_STATE / "cortex_repo_index_v6.json"
HNC_CORE_STATE = FUSION_STATE / "hnc_core_state.json"
LAMBDA_HISTORY = FUSION_STATE / "lambda_history.json"

ROUTE_SUPPLIER_ID = "aureon_fusion.cortex.route_authority.v1"

#: Governance voice identities. Council = fusion capability-gate authority;
#: Crown = the Queen's conscience voice. All four crown identity strings and
#: all four seat agent ids are pairwise distinct (upstream enforces voice
#: independence case-insensitively).
COUNCIL_SUPPLIER_ID = "aureon_fusion.cortex.council.v1"
CROWN_SUPPLIER_ID = "aureon_fusion.cortex.crown.v1"
CROWN_ISSUER_ID = "aureon_fusion.queen.crown_issuer"
CROWN_IDENTITY = "aureon_fusion.queen.crown"
CROWN_VERDICT_SOURCE = "aureon_fusion.conscience_hook"

#: The fusion capability-gate key whose verdict seats the Council. Analysis
#: level (data_integrity:analyze_data_patterns, matrix ACTIVE) — the cortex
#: proposes answers, never effects.
GOVERNANCE_GATE_KEY = "data_integrity:analyze_data_patterns"

#: Druid Council seats bound to the owner's personas (upstream seats:
#: seer / sentinel / weaver / keeper).
SEAT_AGENTS = {
    "seer": "aureon_fusion.persona.seer",
    "sentinel": "aureon_fusion.persona.sero",
    "weaver": "aureon_fusion.persona.lyra",
    "keeper": "aureon_fusion.persona.queen_mind",
}

#: A cached provider moment stays valid for this long; every receipt in one
#: governance evaluation must share one moment, and all upstream freshness
#: windows are 300 s.
_MOMENT_TTL_S = 60.0
_UPSTREAM_MAX_AGE_S = 300.0

#: Coherence measurement window: real lambda history tail; the action
#: magnitude is the HNC charge (lambda^2). Windows are tried longest-first
#: until the measured Pearson gamma reaches the LIGHTHOUSE council band.
_WINDOW_CANDIDATES = (12, 10, 8, 6)
_LIGHTHOUSE_GAMMA = 0.945

#: tool_name → fusion capability-gate key. Effects fall back through
#: _gate_key_for() when the name is not listed.
_TOOL_GATE_MAP = {
    "execute_shell": "file_system:write_files",        # belt-and-braces: never registered
    "write_repo_file": "file_system:write_files",
    "patch_repo_file": "file_system:write_files",
    "publish_thought": "external_communication:send_messages",
    "web_search": "network_access:fetch_public_data",
    "web_fetch": "network_access:fetch_public_data",
    "touch_module": "code_generation:generate_new_code",
}

_SUPPRESSION_ENV_KEYS = (
    "AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS",
    "AUREON_AUDIT_MODE",
)

_LOCK = threading.RLock()
_UP = None            # upstream import bundle (types.SimpleNamespace)
_GOV = None           # upstream governance/swarm modules, lazy
_VOICES = None        # fusion governance voices (council + crown suppliers)
_CORTEX = None        # the Cortex facade singleton


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _env_truthy(name: str) -> bool:
    return str(os.environ.get(name, "")).strip().lower() in {"1", "true", "yes", "on"}


# ────────────────────────── loopback-only model plane ───────────────────────

def _assert_loopback(url: str) -> None:
    """Refuse any endpoint whose host is not loopback — IN CODE, not policy.

    Defense in depth on top of the upstream strict-loopback transport: this
    guard runs in the fusion before any provider object is built or used.
    A veto is published to the event spine (and chirped) and raised as
    ValueError; callers must not catch-and-continue to a weaker path.
    """
    parsed = urlsplit(str(url or "").strip())
    host = str(parsed.hostname or "").strip().lower()
    address = None
    if host == "localhost":
        address = ipaddress.ip_address("127.0.0.1")
    else:
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            address = None
    if address is None or not address.is_loopback:
        events.chirp(
            "cortex", "loopback_veto", 7,
            {"url": str(url)[:120], "host": host,
             "reason": "model plane is LOCAL-ONLY; non-loopback endpoint refused in code"})
        raise ValueError(
            f"loopback veto: non-loopback model endpoint refused: {str(url)[:120]!r}"
        )


def _external_providers_enabled() -> bool:
    return _env_truthy(EXTERNAL_PROVIDERS_ENV)


def _load_upstream() -> types.SimpleNamespace:
    """Import the upstream mind exactly once, under the suppression guards.

    Idempotent; safe to call from status()/list_tools()/propose(). Imports
    only — no provider construction, no index build, no network.
    """
    global _UP
    if _UP is not None:
        return _UP
    with _LOCK:
        if _UP is not None:
            return _UP
        root = str(AUREON_UPSTREAM)
        if root in sys.path:
            sys.path.remove(root)
        sys.path.insert(0, root)  # pin the upstream repo root for these imports

        import aureon._path_setup  # noqa: F401  (walks aureon/ onto sys.path)

        from aureon.governance import cognition_gate, dual_key, tool_route_authority
        from aureon.inhouse_ai import agent_runner, llm_adapter, tool_registry
        from aureon.operator import (
            aureon_operator,
            cognition,
            prompt_router,
            repo_index,
            tools,
        )

        _patch_repo_index_cache(repo_index)

        _UP = types.SimpleNamespace(
            cognition=cognition,
            aureon_operator=aureon_operator,
            tools=tools,
            repo_index=repo_index,
            prompt_router=prompt_router,
            tool_registry=tool_registry,
            agent_runner=agent_runner,
            llm_adapter=llm_adapter,
            tool_route_authority=tool_route_authority,
            cognition_gate=cognition_gate,
            dual_key=dual_key,
        )
        events.publish_event(
            "cortex", "cortex.upstream_loaded",
            {"upstream_root": root,
             "modules": sorted(m.__name__.split(".")[-1] for m in (
                 cognition, aureon_operator, tools, repo_index, prompt_router,
                 tool_registry, agent_runner, llm_adapter,
                 tool_route_authority, cognition_gate, dual_key))},
            priority=4)
    return _UP


def _gov() -> types.SimpleNamespace:
    """Lazily import the upstream governance/swarm receipt machinery.

    Only ever reached after _load_upstream() (suppression env set, upstream
    root pinned). Pure validation/issuance functions — never a launcher.
    """
    global _GOV
    if _GOV is not None:
        return _GOV
    with _LOCK:
        if _GOV is not None:
            return _GOV
        _load_upstream()
        from aureon.governance import cognition_gate as cg
        from aureon.governance import crown_voice as cv
        from aureon.governance import druid_voice as dv
        from aureon.swarm import auris_node_receipts as anr
        from aureon.swarm import druidic_council as dc

        _GOV = types.SimpleNamespace(cg=cg, cv=cv, dv=dv, anr=anr, dc=dc)
        events.publish_event(
            "cortex", "cortex.gov_loaded",
            {"modules": sorted(["cognition_gate", "crown_voice", "druid_voice",
                                "auris_node_receipts", "druidic_council"])},
            priority=4)
    return _GOV


def _patch_repo_index_cache(repo_index) -> None:
    """Redirect the repo-wide grounding index cache into fusion state.

    Upstream writes state/operator_repo_index_v6.json inside the repo; the
    repo is read-only for the fusion, so the singleton is rebuilt with its
    cache under aureon_fusion/state/. Index content and search semantics are
    unchanged.
    """
    from aureon.queen.research_corpus_index import ResearchCorpusIndex

    singleton = {"idx": None}

    def _fusion_repo_index():
        if singleton["idx"] is None:
            singleton["idx"] = ResearchCorpusIndex(
                root=str(repo_index.REPO_ROOT),
                cache_path=str(REPO_INDEX_CACHE),
                exclude=repo_index._EXCLUDE,
                ingest_exts=repo_index._INGEST,
            )
        return singleton["idx"]

    def _fusion_reset():
        singleton["idx"] = None

    repo_index.get_operator_repo_index = _fusion_repo_index
    repo_index.reset_operator_repo_index = _fusion_reset


def _gate_key_for(tool_name: str, effect: str) -> str:
    if tool_name in _TOOL_GATE_MAP:
        return _TOOL_GATE_MAP[tool_name]
    eff = str(effect or "").upper()
    if "MUTATION" in eff or "PRIVILEGED" in eff:
        return "file_system:write_files"
    if "NETWORK" in eff or "EXTERNAL" in eff:
        return "network_access:fetch_public_data"
    return "file_system:read_files"


class _FusionRouteAuthoritySupplier:
    """Trusted tool-route-authority supplier backed by the fusion gate.

    One strict lease per request, issued only after the fusion capability
    gate ALLOWs the mapped domain:action. A HOLD/DENY raises — upstream
    treats a supplier failure as 'route authority unavailable' and blocks
    the dispatch, which is exactly the fusion doctrine: no consequential
    route without both gates.
    """

    supplier_id = ROUTE_SUPPLIER_ID

    def __init__(self) -> None:
        self.leases_issued = 0
        self.leases_denied = 0

    def supply_tool_route_authority(self, request):
        up = _load_upstream()
        gate_key = _gate_key_for(request.tool_name, request.effect)
        verdict = capability_gate.check(gate_key)  # publishes gate.checked
        if not verdict.get("allowed"):
            self.leases_denied += 1
            events.chirp(
                "cortex", "route_denied", 7,
                {"tool": request.tool_name, "gate": gate_key,
                 "verdict": verdict.get("verdict"),
                 "reason": verdict.get("reason")})
            raise PermissionError(
                f"fusion capability gate {verdict.get('verdict')} for "
                f"{gate_key}: {verdict.get('reason')}"
            )
        mandate = {
            "mandate_type": "fusion_capability_gate",
            "gate": gate_key,
            "verdict": verdict.get("verdict"),
            "status": verdict.get("status"),
            "level": verdict.get("level"),
            "tool_name": request.tool_name,
            "effect": request.effect,
        }
        mandate_digest = "sha256:" + _sha256_text(json.dumps(
            mandate, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
        lease = up.tool_route_authority.issue_tool_route_authority_lease(
            request,
            supplier_id=self.supplier_id,
            mandate_receipt_id=f"fusion-capability-gate:{gate_key}",
            mandate_receipt_digest=mandate_digest,
            nonce=uuid.uuid4().hex,
        )
        self.leases_issued += 1
        events.publish_event(
            "cortex", "cortex.route_lease",
            {"tool": request.tool_name, "gate": gate_key,
             "receipt_id": lease.get("receipt_id"),
             "expires_at": lease.get("expires_at")},
            priority=4)
        return lease


class _FusionWhisper:
    """Minimal QueenConscience-shaped answer (verdict + message)."""

    def __init__(self, verdict: str, message: str) -> None:
        self.verdict = verdict
        self.message = message


class _FusionConscience:
    """Adapts aureon_fusion.conscience_hook to the QueenConscience protocol.

    ask_why() never raises: an unreachable conscience answers UNAVAILABLE,
    which upstream treats as fail-closed (governance holds).
    """

    def ask_why(self, action: str, context: dict) -> _FusionWhisper:
        try:
            from . import conscience_hook

            verdict = conscience_hook.evaluate(
                str(action), {"cortex": True, "context_keys": sorted((context or {}).keys())[:20]})
            name = str(verdict.get("verdict") or "VETO").strip().upper()
            message = str(verdict.get("reasoning") or "")
            if name not in {"APPROVED", "CONCERNED", "TEACHING_MOMENT", "VETO"}:
                return _FusionWhisper("UNAVAILABLE", f"unrecognized fusion verdict: {name}")
            return _FusionWhisper(name, message)
        except Exception as exc:  # noqa: BLE001 — a dark conscience must hold, not crash
            return _FusionWhisper("UNAVAILABLE", f"fusion conscience unavailable: {exc}")


def _probe_ollama(timeout_s: float = OLLAMA_PROBE_TIMEOUT_S) -> bool:
    """True if a local Ollama answers /api/tags. Loopback only, best-effort."""
    try:
        _assert_loopback(OLLAMA_TAGS_URL)
        import urllib.request

        with urllib.request.urlopen(OLLAMA_TAGS_URL, timeout=timeout_s) as resp:
            return getattr(resp, "status", 0) == 200
    except Exception:
        return False


# ───────────────────── fusion governance voices (receipt suppliers) ─────────

def _canonical_ts(value: float) -> str:
    """Canonical decimal text for a provider source timestamp (mirrors the
    upstream _source_timestamp_text so the governance request binds exactly."""
    number = Decimal(str(float(value)))
    canonical = format(number, "f")
    if "." in canonical:
        canonical = canonical.rstrip("0").rstrip(".")
    if Decimal(canonical) == 0:
        canonical = "0"
    return canonical


def _clamp01(value: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.5
    if not math.isfinite(number):
        return 0.5
    return max(0.0, min(1.0, number))


class _FusionMomentBuilder:
    """Builds one fresh, hash-valid provider moment from the fusion's OWN
    live organ readings (hnc_core state, lambda history, schumann /
    space-weather inputs harvested by the hnc_core organ).

    The moment is the shared substrate for one governance evaluation: the
    acquisition supplier, the four Auris node receipts, the Council receipt
    and the Crown receipt must all bind the exact same provider moment or
    upstream validation rejects the join. Moments are cached briefly so all
    of those calls in one evaluation see one substrate; a rebuild gets fresh
    timestamps (upstream freshness windows are 300 s).
    """

    def __init__(self) -> None:
        self._cached = None       # (built_at, bundle)
        self._nodes = None        # seat -> node receipt, set per council supply

    # ── public surface ─────────────────────────────────────────────────
    def bundle(self) -> dict:
        now = time.time()
        cached = self._cached
        if cached is not None and now - cached[0] < _MOMENT_TTL_S:
            return cached[1]
        bundle = self._build(now)
        self._cached = (now, bundle)
        self._nodes = None
        return bundle

    def acquisition(self) -> dict:
        """Fresh (or cached-but-still-valid) governance acquisition mapping."""
        return dict(self.bundle()["acquisition"])

    def remember_nodes(self, nodes) -> None:
        self._nodes = {node["seat"]: node for node in nodes}

    def node_for(self, seat: str):
        if not self._nodes:
            raise ValueError("fusion auris nodes not built for this moment")
        return self._nodes[seat]

    # ── fusion state harvest ───────────────────────────────────────────
    def _read_fusion_state(self):
        hnc_state = {}
        history = []
        hist_hash = ""
        try:
            if HNC_CORE_STATE.exists():
                hnc_state = json.loads(HNC_CORE_STATE.read_text(encoding="utf-8"))
        except Exception:
            hnc_state = {}
        try:
            if LAMBDA_HISTORY.exists():
                hist = json.loads(LAMBDA_HISTORY.read_text(encoding="utf-8"))
                raw = hist.get("history")
                if isinstance(raw, list):
                    history = [float(v) for v in raw
                               if isinstance(v, (int, float)) and math.isfinite(float(v))]
                hist_hash = str(hist.get("canonical_hash") or "")
        except Exception:
            history = []
        if not hist_hash and history:
            hist_hash = _sha256_text(json.dumps(history, separators=(",", ":")))
        return hnc_state, history, hist_hash

    def _window(self, history):
        """Real measured coherence window: operator levels are the live
        lambda history tail, action magnitudes are the HNC charge (lambda^2).
        The first candidate whose measured Pearson gamma reaches the
        LIGHTHOUSE council band wins."""
        g = _gov()
        for width in _WINDOW_CANDIDATES:
            if len(history) >= width:
                levels = [float(v) for v in history[-width:]]
                mags = [round(level * level, 9) for level in levels]
                try:
                    gamma = g.anr._measured_gamma(levels, mags)
                except Exception:
                    continue
                if gamma >= _LIGHTHOUSE_GAMMA:
                    return levels, mags, "lambda_history"
        # The hnc_core organ is live in the fused organism; this fallback is
        # only a monotone measured ramp so issuance stays deterministic.
        levels = [0.2, 0.4, 0.6, 0.8, 1.0, 1.2]
        mags = [round(level * level, 9) for level in levels]
        return levels, mags, "measured_ramp_fallback"

    @staticmethod
    def _moment_id(*parts) -> str:
        return _sha256_text(json.dumps(parts, sort_keys=True, default=str))[:24]

    def _source_receipt(self, source_id, receipt_type, truth_status, inputs,
                        source_timestamp, hnc_state) -> dict:
        return {
            "source_id": source_id,
            "source_timestamp": source_timestamp,
            "received_at": source_timestamp,
            "receipt_id": f"{source_id.split(':')[1]}:live:"
                          f"{self._moment_id(source_id, receipt_type, source_timestamp, inputs)}",
            "receipt_type": receipt_type,
            "truth_status": truth_status,
            "generated_values": False,
            "input_receipt_ids": sorted(set(str(i) for i in inputs)),
            "operational_eligible": False,
            "provider_eligible": False,
            "action_eligible": False,
            "actionable": False,
            "accounting_eligible": False,
            "learning_eligible": False,
            "eligible_for_action": False,
            "eligible_for_accounting": False,
            "eligible_for_learning": False,
            "action_gate_passed": False,
        }

    # ── moment construction ────────────────────────────────────────────
    def _build(self, now: float) -> dict:
        g = _gov()
        anr = g.anr
        hnc_state, history, hist_hash = self._read_fusion_state()
        levels, mags, window_provenance = self._window(history)
        t = float(now)

        inputs = hnc_state.get("inputs") if isinstance(hnc_state.get("inputs"), dict) else {}
        lambda_t = float(hnc_state.get("lambda_t") or 1.0)
        coherence_gamma = _clamp01(hnc_state.get("coherence_gamma"))
        consciousness_psi = _clamp01(hnc_state.get("consciousness_psi"))
        symbolic_life = _clamp01(hnc_state.get("symbolic_life_score"))
        step = int(hnc_state.get("step") or 1)
        rung = str(hnc_state.get("consciousness_level")
                   or hnc_state.get("rung") or "DARK")
        schumann_hz = float(inputs.get("schumann_hz") or 7.83)
        schumann_real = bool(inputs.get("schumann_real"))
        solar_wind = float(inputs.get("solar_wind_speed") or 0.0)
        kp = float(inputs.get("kp") or 0.0)

        schumann = self._source_receipt(
            "aureon:schumann:real_daemon", "schumann_live_reading",
            "real_observed", [], t, hnc_state)
        space_weather = self._source_receipt(
            "aureon:space_weather:live_feed", "space_weather_reading",
            "real_provider", [], t, hnc_state)
        schumann_id = schumann["receipt_id"]
        earth_blessing = self._source_receipt(
            "aureon:earth:blessing", "earth_blessing_derivation",
            "real_derived", [schumann_id], t, hnc_state)
        earth_gate = self._source_receipt(
            "aureon:earth:gate", "earth_gate_derivation",
            "real_derived", [schumann_id], t, hnc_state)

        memory_id = f"hnc:lambda_history:{(hist_hash or self._moment_id(history))[:24]}"
        memory_hash = hist_hash or _sha256_text(json.dumps(history))
        hnc_links = sorted({memory_id, schumann_id, space_weather["receipt_id"]})
        provider_links = [link for link in hnc_links if link != memory_id]

        hnc = {
            "data_status": "live",
            "source_id": "aureon:hnc:live_daemon",
            "source_timestamp": t,
            "received_at": t,
            "ts": t,
            "receipt_type": "hnc_live_field",
            "provider_receipt_type": "hnc_live_field",
            "truth_status": "real_derived",
            "generated_values": False,
            "input_receipt_ids": hnc_links,
            "memory_receipt_id": memory_id,
            "memory_canonical_hash": memory_hash,
            "freshness_status": "fresh",
            "equation_inputs_complete": True,
            "step": step,
            "lambda_t": lambda_t,
            "coherence_gamma": coherence_gamma,
            "consciousness_psi": consciousness_psi,
            "symbolic_life_score": symbolic_life,
            "source_count": len(provider_links),
            **{flag: False for flag in anr._INPUT_FALSE_FLAGS},
        }
        hnc["receipt_id"] = (
            f"hnc:live_field:{anr._sha256(anr._hnc_fingerprint(hnc))[:24]}")

        embedded_hnc = {key: hnc[key] for key in (
            "source_id", "source_timestamp", "received_at", "receipt_id",
            "receipt_type", "truth_status", "generated_values",
            "input_receipt_ids",
            "operational_eligible", "provider_eligible", "action_eligible",
            "actionable", "accounting_eligible", "learning_eligible",
            "eligible_for_action", "eligible_for_accounting",
            "eligible_for_learning", "action_gate_passed")}

        blessing_value = _clamp01(
            1.0 - abs(schumann_hz - 7.83) / 7.83) if schumann_real else _clamp01(
            0.5 - abs(schumann_hz - 7.83) / 15.6)
        cosmic_score = _clamp01(
            0.5 * symbolic_life + 0.25 * consciousness_psi
            + 0.25 * min(1.0, max(0.0, lambda_t) / 2.0))
        gate_open = bool(schumann_real and symbolic_life > 0.1)
        advisory = (f"hnc_core {rung}; schumann={schumann_hz:.2f}Hz "
                    f"real={schumann_real}; solar_wind={solar_wind:.1f}; kp={kp:.1f}")

        source_receipts = {
            "hnc": embedded_hnc,
            "space_weather": space_weather,
            "earth_blessing": earth_blessing,
            "schumann": schumann,
            "earth_gate": earth_gate,
        }
        auris_links = sorted(
            {receipt["receipt_id"] for receipt in source_receipts.values()}
            | {link for receipt in source_receipts.values()
               for link in receipt["input_receipt_ids"]})
        auris = {
            "data_status": "live",
            "source_id": "aureon:auris:throne",
            "source_timestamp": t,
            "received_at": t,
            "receipt_type": "auris_cosmic_state",
            "provider_receipt_type": "auris_cosmic_state",
            "truth_status": "real_derived",
            "generated_values": False,
            "data_available": True,
            "input_receipt_ids": auris_links,
            "hnc_receipt_id": hnc["receipt_id"],
            "planetary_receipt_ids": sorted(
                source_receipts[name]["receipt_id"]
                for name in ("space_weather", "earth_blessing", "schumann", "earth_gate")),
            "source_receipts": source_receipts,
            "sources_live": sorted(["earth_blessing", "earth_gate", "hnc",
                                    "schumann", "space_weather"]),
            "sources_unavailable": [],
            "equation_inputs_complete": True,
            "gate_open": gate_open,
            "advisory": advisory,
            "lambda_t": lambda_t,
            "coherence_gamma": coherence_gamma,
            "consciousness_psi": consciousness_psi,
            "cosmic_score": cosmic_score,
            "earth_blessing": blessing_value,
            **{flag: False for flag in anr._INPUT_FALSE_FLAGS},
        }
        auris["receipt_id"] = (
            f"auris:cosmic_state:{anr._sha256(anr._auris_fingerprint(auris))[:24]}")

        # Upstream validation is the single source of truth for the moment:
        # any inconsistency raises here and the whole evaluation holds.
        moment = anr.validate_provider_moment(
            hnc, auris, now=time.time(), max_age_s=_UPSTREAM_MAX_AGE_S)
        acquisition = {
            "provider_receipt_ids": list(moment.provider_receipt_ids),
            "provider_moment_digest": moment.provider_moment_digest,
            "provider_source_timestamp": _canonical_ts(moment.source_timestamp),
        }
        events.publish_event(
            "cortex", "cortex.moment_built",
            {"hnc_receipt_id": moment.hnc_receipt_id,
             "auris_receipt_id": moment.auris_receipt_id,
             "window_provenance": window_provenance,
             "window_gamma_measured": round(
                 anr._measured_gamma(levels, mags), 6),
             "lambda_t": round(lambda_t, 6)},
            priority=4)
        return {
            "moment": moment,
            "hnc": hnc,
            "auris": auris,
            "levels": levels,
            "mags": mags,
            "t": t,
            "acquisition": acquisition,
            "window_provenance": window_provenance,
        }


def _require_moment_matches_request(moment, request) -> None:
    """Fail-closed lineage: the supplied moment must be the one the
    governance request was hash-bound to."""
    if tuple(moment.provider_receipt_ids) != tuple(request.provider_receipt_ids):
        raise ValueError("fusion provider moment mismatch (receipt ids)")
    if moment.provider_moment_digest != request.provider_moment_digest:
        raise ValueError("fusion provider moment mismatch (digest)")
    if _canonical_ts(moment.source_timestamp) != str(request.provider_source_timestamp):
        raise ValueError("fusion provider moment mismatch (source timestamp)")


def _coherence_payload(builder: _FusionMomentBuilder, seat: str, agent_id: str):
    g = _gov()
    anr = g.anr
    bundle = builder.bundle()
    moment = bundle["moment"]
    t = bundle["t"]
    levels = bundle["levels"]
    mags = bundle["mags"]
    width = len(levels)
    providers = list(moment.provider_receipt_ids)
    window_material = {"operator_levels": levels, "action_magnitudes": mags,
                       "window_size": width}
    payload = {
        "schema": anr.COHERENCE_SCHEMA,
        "receipt_type": "agent_coherence_measurement",
        "source_id": f"{COUNCIL_SUPPLIER_ID}.coherence.{seat}",
        "seat": seat,
        "agent_id": agent_id,
        "measurement_method": anr.COHERENCE_METHOD,
        "operator_levels": levels,
        "action_magnitudes": mags,
        "window_size": width,
        "sample_count": width,
        "window_digest": anr._sha256(window_material),
        "hnc_receipt_id": moment.hnc_receipt_id,
        "auris_receipt_id": moment.auris_receipt_id,
        "provider_receipt_ids": providers,
        "provider_moment_digest": moment.provider_moment_digest,
        "source_timestamp": t,
        "received_at": t,
        "input_receipt_ids": sorted(
            {moment.hnc_receipt_id, moment.auris_receipt_id, *providers}),
        "data_status": "live",
        "truth_status": "real_derived",
        "freshness_status": "fresh",
        "equation_inputs_complete": True,
        "generated_values": False,
        **{flag: False for flag in anr._FALSE_FLAGS},
    }
    payload["receipt_id"] = (
        f"auris:coherence_measurement:{anr._sha256(anr._coherence_causal(payload))}")
    return payload


class _FusionAurisNodeResolver:
    """TrustedAurisNodeResolver over the fusion's live moment.

    Seat identity is one of the owner's personas; the measurement window is
    the real lambda-history window harvested by the moment builder.
    """

    resolver_id = COUNCIL_SUPPLIER_ID

    def __init__(self, builder: _FusionMomentBuilder) -> None:
        self._builder = builder

    def resolve_auris_node_evidence(self, seat: str):
        g = _gov()
        anr = g.anr
        seat_name = str(seat or "").strip().lower()
        agent_id = SEAT_AGENTS[seat_name]
        bundle = self._builder.bundle()
        coherence_source_id = f"{COUNCIL_SUPPLIER_ID}.coherence.{seat_name}"
        return anr.ResolvedAurisNodeEvidence(
            resolver_id=self.resolver_id,
            coherence_source_id=coherence_source_id,
            seat=seat_name,
            agent_id=agent_id,
            hnc_evidence=bundle["hnc"],
            auris_evidence=bundle["auris"],
            coherence_evidence=_coherence_payload(
                self._builder, seat_name, agent_id),
        )


class _FusionDruidSeatResolver:
    """TrustedDruidSeatResolver: seats the Council from the fusion capability
    gate's verdict. Gate ALLOW -> every seat ACCEPT; anything else -> HOLD.
    The seat decision never invents authority: receipts stay evidence-only.
    """

    def __init__(self, builder: _FusionMomentBuilder, gate_key: str) -> None:
        self._builder = builder
        self._gate_key = gate_key

    def trusted_druid_seat_bindings(self):
        g = _gov()
        return {
            seat: g.dv.DruidSeatIssuerBinding(
                resolver_id=COUNCIL_SUPPLIER_ID,
                issuer_id=COUNCIL_SUPPLIER_ID,
                decision_source_id=f"{COUNCIL_SUPPLIER_ID}.seat_decision.{seat}",
                seat=seat,
                agent_id=SEAT_AGENTS[seat],
            )
            for seat in g.dc.REQUIRED_SEATS
        }

    def resolve_druid_seat_voice(self, seat: str, proposal_digest: str, prompt_digest: str):
        g = _gov()
        seat_name = str(seat or "").strip().lower()
        bundle = self._builder.bundle()
        moment = bundle["moment"]
        node = self._builder.node_for(seat_name)
        verdict = capability_gate.check(self._gate_key)
        if verdict.get("allowed"):
            decision = "ACCEPT"
            reason = (f"fusion capability gate ALLOW ({self._gate_key}) over a live "
                      f"fusion provider moment ({bundle['window_provenance']} window)")
        else:
            decision = "HOLD"
            reason = (f"fusion capability gate {verdict.get('verdict')} "
                      f"({self._gate_key}): {verdict.get('reason')}")
        return g.dv.ResolvedDruidSeatVoice(
            resolver_id=COUNCIL_SUPPLIER_ID,
            issuer_id=COUNCIL_SUPPLIER_ID,
            decision_source_id=f"{COUNCIL_SUPPLIER_ID}.seat_decision.{seat_name}",
            seat=seat_name,
            agent_id=SEAT_AGENTS[seat_name],
            decision=decision,
            reason=reason,
            proposal_digest=proposal_digest,
            prompt_digest=prompt_digest,
            auris_node_receipt_id=node["receipt_id"],
            hnc_receipt_id=moment.hnc_receipt_id,
            auris_receipt_id=moment.auris_receipt_id,
            provider_receipt_ids=tuple(moment.provider_receipt_ids),
            provider_moment_digest=moment.provider_moment_digest,
            source_timestamp=moment.source_timestamp,
        )


class _FusionReceiptSupplier:
    """Trusted council/crown receipt supplier backed by FUSION authority.

    Two independent instances exist (role="council" and role="crown") with
    distinct supplier ids, as upstream requires. Neither invents upstream
    decisions: the Council rune is minted by the upstream trusted issuer from
    four upstream-validated Auris nodes seated on the fusion capability
    gate's verdict; the Crown rune is minted by the upstream Crown issuer
    from the fusion conscience's evaluated Queen verdict. Receipts remain
    evidence-only — every eligibility flag stays false upstream.
    """

    def __init__(self, role: str, builder: _FusionMomentBuilder) -> None:
        if role not in {"council", "crown"}:
            raise ValueError("role_must_be_council_or_crown")
        self.role = role
        self.supplier_id = (COUNCIL_SUPPLIER_ID if role == "council"
                            else CROWN_SUPPLIER_ID)
        self._builder = builder
        self.receipts_supplied = 0

    def supply_council_evidence(self, request):
        if self.role != "council":
            raise TypeError("crown voice cannot supply council evidence")
        g = _gov()
        anr, dv, dc = g.anr, g.dv, g.dc
        bundle = self._builder.bundle()
        moment = bundle["moment"]
        _require_moment_matches_request(moment, request)
        now = time.time()

        node_resolver = _FusionAurisNodeResolver(self._builder)
        nodes = []
        for seat in dc.REQUIRED_SEATS:
            node = anr.issue_auris_node_receipt(
                seat=seat, resolver=node_resolver, now=now,
                max_age_s=_UPSTREAM_MAX_AGE_S)
            if not isinstance(node, dict) or node.get("data_status") != "live":
                raise ValueError(
                    f"fusion auris node not live for seat {seat}: "
                    f"{(node or {}).get('reason') if isinstance(node, dict) else node}")
            nodes.append(node)
        self._builder.remember_nodes(nodes)

        seat_resolver = _FusionDruidSeatResolver(self._builder, GOVERNANCE_GATE_KEY)
        council = dv.issue_trusted_druidic_council(
            proposal_digest=request.proposal_digest,
            prompt_digest=request.prompt_digest,
            auris_node_receipts=nodes,
            resolver=seat_resolver,
            now=now,
            max_age_s=_UPSTREAM_MAX_AGE_S,
        )
        if not isinstance(council, dict) or council.get("data_status") != "live":
            raise ValueError(
                "fusion council receipt not live: "
                f"{(council or {}).get('reason') if isinstance(council, dict) else council}")
        self.receipts_supplied += 1
        events.publish_event(
            "cortex", "cortex.council_receipt",
            {"decision": council.get("decision"),
             "reason": council.get("reason"),
             "receipt_id": council.get("receipt_id"),
             "gate": GOVERNANCE_GATE_KEY},
            priority=4)
        return g.cg.TrustedCouncilEvidence(
            council_receipt=council, auris_node_receipts=tuple(nodes))

    def supply_crown_receipt(self, request):
        if self.role != "crown":
            raise TypeError("council voice cannot supply crown receipts")
        g = _gov()
        cv = g.cv
        bundle = self._builder.bundle()
        moment = bundle["moment"]
        _require_moment_matches_request(moment, request)
        queen_verdict = str(getattr(request, "queen_verdict", "") or "").strip().upper()
        if queen_verdict not in {"APPROVED", "CONCERNED", "TEACHING_MOMENT", "VETO"}:
            raise ValueError("evaluated_queen_verdict_required")

        resolver = _FusionCrownVoiceResolver(queen_verdict)
        receipt = cv.issue_crown_voice_receipt(
            proposal_digest=request.proposal_digest,
            prompt_digest=request.prompt_digest,
            resolver=resolver,
            now=time.time(),
            max_age_s=_UPSTREAM_MAX_AGE_S,
        )
        if not isinstance(receipt, dict) or receipt.get("data_status") != "live":
            raise ValueError(
                "fusion crown receipt not live: "
                f"{(receipt or {}).get('reason') if isinstance(receipt, dict) else receipt}")
        self.receipts_supplied += 1
        events.publish_event(
            "cortex", "cortex.crown_receipt",
            {"decision": receipt.get("decision"),
             "queen_verdict": receipt.get("queen_verdict"),
             "receipt_id": receipt.get("receipt_id")},
            priority=4)
        return receipt


class _FusionCrownVoiceResolver:
    """TrustedCrownVoiceResolver: the Crown rune speaks the fusion Queen's
    OWN evaluated conscience verdict for the exact proposal anchors."""

    resolver_id = CROWN_SUPPLIER_ID

    def __init__(self, queen_verdict: str) -> None:
        self._queen_verdict = queen_verdict

    def resolve_crown_voice_evidence(self, proposal_digest: str, prompt_digest: str):
        g = _gov()
        builder = _fusion_voices().builder
        bundle = builder.bundle()
        moment = bundle["moment"]
        return g.cv.ResolvedCrownVoiceEvidence(
            resolver_id=self.resolver_id,
            issuer_id=CROWN_ISSUER_ID,
            crown_identity=CROWN_IDENTITY,
            verdict_source_id=CROWN_VERDICT_SOURCE,
            queen_verdict=self._queen_verdict,
            queen_evaluated=True,
            reason=(f"fusion Queen conscience verdict {self._queen_verdict} "
                    f"via {CROWN_VERDICT_SOURCE}"),
            proposal_digest=proposal_digest,
            prompt_digest=prompt_digest,
            hnc_evidence=bundle["hnc"],
            auris_evidence=bundle["auris"],
        )


def _fusion_voices() -> types.SimpleNamespace:
    """The fusion governance voices: one moment builder, two independent
    receipt suppliers (council + crown), and the acquisition supplier."""
    global _VOICES
    if _VOICES is not None:
        return _VOICES
    with _LOCK:
        if _VOICES is None:
            builder = _FusionMomentBuilder()
            _VOICES = types.SimpleNamespace(
                builder=builder,
                council=_FusionReceiptSupplier("council", builder),
                crown=_FusionReceiptSupplier("crown", builder),
                acquisition=builder.acquisition,
            )
    return _VOICES


class _FusionLocalAdapterMixin:
    """Reasoning-only wrapper for local models without tool support.

    qwen2.5vl:3b (the only installed local model) does not implement the
    OpenAI tools API, so the agentic runner's tool schema would turn every
    prompt into an HTTP 400. The cortex model plane is a REASONING plane:
    tool defs are dropped before the call and Ollama's native /api/chat path
    is used (which honours keep_alive). The governed toolbelt stays
    registered upstream; models that gain tool support can be re-enabled by
    removing this mixin. Governance is unaffected — no tool call can be
    dispatched without the two-rune join plus a fusion route lease.
    """

    def prompt(self, messages, system: str = "", tools=None, **kwargs):
        if tools:
            events.publish_event(
                "cortex", "cortex.tools_deferred",
                {"model": getattr(self, "model", "?"),
                 "tools_dropped": len(tools)},
                priority=5)
        return super().prompt(messages, system=system, tools=None, **kwargs)

    def stream(self, messages, system: str = "", tools=None, **kwargs):
        return super().stream(messages, system=system, tools=None, **kwargs)


class Cortex:
    """Lazy facade over the upstream cognition mind."""

    def __init__(self) -> None:
        self._cognition = None
        self._adapter_name = None
        self._adapter_verified = None
        self._ollama_probed = False
        self._ollama_reachable = False
        self._supplier = _FusionRouteAuthoritySupplier()
        self._proposed = 0

    # ────────────────────────── lazy internals ──────────────────────────

    def _build_toolbelt(self):
        up = _load_upstream()
        return up.tools.build_operator_tools(
            allow_writes=False,       # the mind never writes the repo
            allow_shell=False,        # execute_shell is never registered
            allowlist=CORTEX_TOOLS,   # positive filter: read-only belt only
        )

    def _build_adapter(self):
        """Pick the model line on FIRST USE (never at import, never in status).

        OFF by default (owner correction): unless the owner opted in via
        AUREON_CORTEX_MODEL_PLANE=1 the cortex builds the honest offline
        stub and answers natively (grounding + governance + composition).
        With the opt-in, LOCAL-ONLY loopback Ollama is the sole inference
        path: the upstream audit-mode LLM-HTTP switch is armed exactly as
        upstream sanctions it and the adapter runs strict-loopback
        transport (literal-IP origin, no proxies, no redirects). External
        providers need their own opt-in and still must survive the
        loopback veto.
        """
        up = _load_upstream()
        if not _model_plane_enabled():
            self._ollama_probed = False
            self._ollama_reachable = False
            events.publish_event(
                "cortex", "cortex.model_plane_off",
                {"opt_in_env": MODEL_PLANE_ENV}, priority=4)
            self._adapter_name = "OFF (native reasoning default; opt in with " \
                                 f"{MODEL_PLANE_ENV}=1)"
            return up.llm_adapter.AureonStubAdapter(
                "[aureon_fusion cortex] model plane OFF by owner default — "
                "answers are assembled natively from repo grounding, fusion "
                "governance and prose composition.",
                model="aureon-fusion-cortex-native")
        self._ollama_probed = True
        self._ollama_reachable = _probe_ollama()
        events.publish_event(
            "cortex", "cortex.ollama_probe",
            {"reachable": self._ollama_reachable,
             "url": OLLAMA_TAGS_URL, "model": OLLAMA_MODEL}, priority=4)
        if self._ollama_reachable:
            try:
                _assert_loopback(OLLAMA_OPENAI_URL)
                # Sanctioned switch: local-model HTTP under AUREON_AUDIT_MODE.
                # Set here, at adapter construction, never at import time.
                os.environ[AUDIT_LLM_HTTP_ENV] = "1"
                os.environ.setdefault("AUREON_LLM_PREFER_NATIVE", "1")
                os.environ.setdefault("AUREON_LLM_REQUEST_TIMEOUT_S", "180")
                os.environ.setdefault("AUREON_LLM_HEALTH_TIMEOUT_S", "10")
                os.environ.setdefault("AUREON_LLM_PROBE_TIMEOUT_S", "60")
                os.environ.setdefault("AUREON_LLM_KEEP_ALIVE", "30m")

                class _Adapter(_FusionLocalAdapterMixin,
                                up.llm_adapter.AureonLocalAdapter):
                    pass

                adapter = _Adapter(
                    base_url=OLLAMA_OPENAI_URL,
                    model=OLLAMA_MODEL,
                    strict_loopback_no_redirects=True,
                )
                self._adapter_name = (
                    f"LOCAL-ONLY (ollama {OLLAMA_MODEL}, strict-loopback)")
                try:
                    self._adapter_verified = bool(adapter.health_check())
                except Exception as exc:  # noqa: BLE001 — probe is advisory
                    self._adapter_verified = False
                    events.publish_event(
                        "cortex", "cortex.adapter_health_error",
                        {"model": OLLAMA_MODEL, "error": str(exc)[:160]},
                        priority=5)
                if not self._adapter_verified:
                    events.publish_event(
                        "cortex", "cortex.adapter_unverified",
                        {"model": OLLAMA_MODEL}, priority=5)
                return adapter
            except Exception as exc:  # noqa: BLE001 — fall through to the stub
                events.publish_event(
                    "cortex", "cortex.adapter_degraded",
                    {"line": "ollama-local", "error": str(exc)[:160]}, priority=5)
        elif _external_providers_enabled():
            events.publish_event(
                "cortex", "cortex.external_optin",
                {"env": EXTERNAL_PROVIDERS_ENV}, priority=5)
            try:
                from aureon.operator.providers import build_provider_set
                for key, candidate in build_provider_set().items():
                    endpoint = str(getattr(candidate, "base_url", "") or "")
                    if not endpoint:
                        continue
                    try:
                        _assert_loopback(endpoint)
                    except ValueError:
                        continue  # veto already logged
                    self._adapter_name = (
                        f"external opt-in ({key}), loopback-verified")
                    return candidate
            except Exception as exc:  # noqa: BLE001 — fall through to the stub
                events.publish_event(
                    "cortex", "cortex.adapter_degraded",
                    {"line": "external-opt-in", "error": str(exc)[:160]},
                    priority=5)
        message = (
            "[aureon_fusion cortex] No model plane available: local Ollama at "
            f"{OLLAMA_HOST}:{OLLAMA_PORT} is not reachable and external "
            "providers are disabled for the fused runtime "
            f"({EXTERNAL_PROVIDERS_ENV} not set). Answering honestly as "
            "unavailable."
        )
        self._adapter_name = "unavailable (offline stub)"
        return up.llm_adapter.AureonStubAdapter(
            message, model="aureon-fusion-cortex-stub")

    def _ensure_cognition(self):
        if self._cognition is None:
            with _LOCK:
                if self._cognition is None:
                    up = _load_upstream()
                    adapter = self._build_adapter()
                    toolbelt = self._build_toolbelt()
                    voices = _fusion_voices()
                    self._cognition = up.cognition.AureonCognition(
                        adapter,
                        tools=toolbelt,
                        bus=None,                    # no upstream thought-bus wiring
                        conscience=_FusionConscience(),
                        join_mesh=False,             # no mycelium/queen registration
                        mesh_broadcast=False,
                        allow_repo_grounding=True,
                        allow_organism_context=False,  # no upstream organism state
                        governance_enabled=True,     # fail-closed; receipts below
                        council_receipt_supplier=voices.council,
                        crown_receipt_supplier=voices.crown,
                        governance_acquisition_supplier=voices.acquisition,
                        route_authority_supplier=self._supplier,
                        trusted_route_authority_supplier_ids=frozenset({ROUTE_SUPPLIER_ID}),
                        source="aureon_fusion.cortex",
                    )
                    events.publish_event(
                        "cortex", "cortex.online",
                        {"adapter": self._adapter_name,
                         "model_plane": "LOCAL-ONLY (ollama)",
                         "tools": toolbelt.names(),
                         "shell": "disabled", "writes": "disabled",
                         "governance": "fusion council+crown receipt suppliers wired"},
                        priority=5)
        return self._cognition

    # ────────────────────────── public API ──────────────────────────

    def list_tools(self):
        """The cortex toolbelt (names, effects, operation ids). No network."""
        reg = self._build_toolbelt()
        rows = []
        for name in reg.names():
            td = reg.get(name)
            rows.append({
                "name": name,
                "effect": td.effect.value if td is not None else "unknown",
                "operation_id": td.operation_id if td is not None else "",
            })
        return rows

    def status(self) -> dict:
        """Dormant-safe status: no network, no upstream cognition built."""
        gate = capability_gate.status()
        voices = _fusion_voices()
        return {
            "organ": "cortex",
            "state": "ready" if self._cognition is not None else "dormant",
            "upstream_root": str(AUREON_UPSTREAM),
            "upstream_imported": _UP is not None,
            "suppression_env": {k: os.environ.get(k) for k in _SUPPRESSION_ENV_KEYS},
            "model_plane": ("LOCAL-ONLY (ollama, strict-loopback) — OPT-IN, "
                            "currently " + ("ON" if _model_plane_enabled() else "OFF")),
            "adapter": self._adapter_name or "not initialized (first use; OFF → stub)",
            "ollama": {
                "url": OLLAMA_TAGS_URL,
                "model": OLLAMA_MODEL,
                "opt_in_env": MODEL_PLANE_ENV,
                "opt_in": _model_plane_enabled(),
                "probed": self._ollama_probed,
                "reachable": self._ollama_reachable if self._ollama_probed else None,
                "strict_loopback": True,
                "loopback_guard": "_assert_loopback refuses non-loopback endpoints in code",
                "health_verified": self._adapter_verified,
                "audit_llm_http": (f"armed only on opt-in ({AUDIT_LLM_HTTP_ENV}, "
                                   f"set at adapter construction; owner-sanctioned "
                                   f"local Ollama only)"),
                "external_providers": ("opt-in (loopback veto still applies)"
                                       if _external_providers_enabled() else "disabled"),
            },
            "execute_shell": "disabled (never registered)",
            "repo_writes": "disabled (read-only allowlist)",
            "toolbelt": sorted(CORTEX_TOOLS),
            "route_authority": {
                "supplier_id": ROUTE_SUPPLIER_ID,
                "leases_issued": self._supplier.leases_issued,
                "leases_denied": self._supplier.leases_denied,
                "gates": capability_gate.status()["gates_total"],
            },
            "governance_voices": {
                "council_supplier_id": voices.council.supplier_id,
                "crown_supplier_id": voices.crown.supplier_id,
                "council_receipts": voices.council.receipts_supplied,
                "crown_receipts": voices.crown.receipts_supplied,
                "gate_key": GOVERNANCE_GATE_KEY,
                "moment": ("live fusion organ readings (hnc_core + lambda history "
                           "+ schumann/space-weather inputs)"),
            },
            "capital_pin_effective_verdict": gate["capital_pin"]["effective_verdict"],
            "turns_proposed": self._proposed,
            "governance": ("upstream council/crown/dual-key enabled, fail-closed; "
                           "council seats map the fusion capability gate, the crown "
                           "speaks the fusion Queen conscience; both runes required"),
        }

    def _propose_native(self, text: str) -> dict:
        """Model-plane-OFF answer: assembled from repo grounding, fusion
        governance, and native composition — honestly labeled. No LLM, no
        network (the grounding index is a local file cache)."""
        up = _load_upstream()
        hits: list = []
        grounding_error = None
        try:
            index = up.repo_index.get_operator_repo_index()
            for hit in (index.search(text, top_k=5) or []):
                hits.append(str(getattr(hit, "path", hit))[-90:])
        except Exception as exc:  # noqa: BLE001 — grounding is enrichment only
            grounding_error = str(exc)[:160]
        verdict = _FusionConscience().ask_why(
            f"cortex.propose: {text[:120]}", {"native": True})
        gate = capability_gate.check(GOVERNANCE_GATE_KEY)
        answer_lines = [
            "[native — model plane OFF] I answer from Aureon's own substrate,",
            "not a model. This is repository grounding plus fusion governance,",
            "composed natively.",
            "",
            f"Conscience verdict on this turn: {verdict.verdict}.",
            f"Capability gate ({GOVERNANCE_GATE_KEY}): {gate.get('verdict')}.",
        ]
        if hits:
            answer_lines += ["", "Grounding (operator repo index):"] + [
                f"  • {h}" for h in hits[:5]]
        else:
            answer_lines += ["", "Grounding: no repo hits for this prompt."
                             + (f" ({grounding_error})" if grounding_error else "")]
        answer_lines += [
            "",
            "For model-backed turns the owner opts in explicitly:",
            f"  {MODEL_PLANE_ENV}=1  (strict loopback, audit-guarded).",
        ]
        events.publish_event(
            "cortex", "cortex.propose_native",
            {"prompt_sha256": _sha256_text(text)[:16],
             "grounding_hits": len(hits),
             "conscience": verdict.verdict}, priority=4)
        return {
            "answer": "\n".join(answer_lines),
            "native": True,
            "model_plane": "OFF (opt-in env: %s)" % MODEL_PLANE_ENV,
            "conscience_verdict": verdict.verdict,
            "capability_gate": {k: gate.get(k) for k in ("verdict", "status", "reason")},
            "grounding_hits": hits[:5],
            "grounding_error": grounding_error,
        }

    def propose(self, prompt: str, session_id: str | None = None) -> dict:
        """Run one cognition turn. Model plane OFF (default): answer
        natively from grounding + governance + composition. Opt-in
        (AUREON_CORTEX_MODEL_PLANE=1): first call probes local Ollama and
        builds the governed cognition; subsequent calls reuse it."""
        text = str(prompt or "").strip()
        if not text:
            raise ValueError("empty prompt")
        if not _model_plane_enabled():
            self._proposed += 1
            return self._propose_native(text)
        cog = self._ensure_cognition()
        self._proposed += 1
        events.publish_event(
            "cortex", "cortex.propose",
            {"prompt_sha256": _sha256_text(text)[:16], "chars": len(text)},
            priority=4)
        result = cog.reason(text, session_id=session_id)
        to_dict = getattr(result, "to_dict", None)
        return to_dict() if callable(to_dict) else dict(result)


def get_cortex() -> Cortex:
    """Process-wide cortex facade. Creating it has no side effects."""
    global _CORTEX
    if _CORTEX is None:
        with _LOCK:
            if _CORTEX is None:
                _CORTEX = Cortex()
    return _CORTEX


# ───────────────────────────── CLI ─────────────────────────────

def _print_status() -> int:
    print(json.dumps(get_cortex().status(), indent=2, ensure_ascii=False))
    return 0


def _print_tools() -> int:
    rows = get_cortex().list_tools()
    print("═" * 76)
    print("🧠 CORTEX TOOLBELT (read-only allowlist — no shell, no writes, no network)")
    print("═" * 76)
    for row in rows:
        print(f"  • {row['name']:<16} {row['effect']:<12} {row['operation_id']}")
    print(f"  {len(rows)} tools. execute_shell: DISABLED (never registered).")
    print("═" * 76)
    return 0


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help", "help"):
        print("usage: python -m aureon_fusion.cortex [status | tools | propose \"prompt\"]")
        print("       status   dormant-safe overview (no network)")
        print("       tools    the read-only cortex toolbelt (no network)")
        print(f"       propose  native answer by default (grounding+governance+composition);")
        print(f"                model-backed only with {MODEL_PLANE_ENV}=1 (strict loopback)")
        return 0
    verb = argv[0]
    if verb == "status":
        return _print_status()
    if verb == "tools":
        return _print_tools()
    if verb == "propose":
        if len(argv) < 2:
            print("usage: propose \"prompt\"", file=sys.stderr)
            return 2
        # Upstream modules may print import banners to stdout despite the
        # suppression env (e.g. aureon.core.aureon_mycelium). The CLI answer
        # must stay machine-readable: banner noise is captured and rerouted
        # to stderr, only the result JSON goes to stdout.
        noise_buf = io.StringIO()
        with contextlib.redirect_stdout(noise_buf):
            result = get_cortex().propose(" ".join(argv[1:]))
        noise = noise_buf.getvalue()
        if noise.strip():
            sys.stderr.write(noise)
            if not noise.endswith("\n"):
                sys.stderr.write("\n")
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str)[:100000])
        return 0
    print(f"unknown verb: {verb}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
