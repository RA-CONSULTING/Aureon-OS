"""🖥️ PC ACTIVATORS — pure mechanics for the pc_control door.

Owner decree (2026-09-05): "let her run fully autonomously with full access
to the pc — let's watch what she does." Elevated by owner decree
2026-09-06 (GAP 5 build night, Tier 4 owner-decree territory). The organism
is shown this door and mints its own key to open/close it: internal intent
plus the fail-closed gate trio in master_key (conscience VETO absolute, HNC
coherence Γ≥0.25, capability authorization on `system_control:full_pc_access`).
As an ELEVATE class door, open() additionally gets master_key's conscience
double-check automatically — NO gating is implemented here.

Scope: PURE MECHANICS ONLY. This module ACQUIRES the upstream governed
operator toolbelt (aureon.operator.tools.build_operator_tools with writes
and shell enabled, allowlist OFF so the full belt stands); it never executes
a tool on its own. Acquisition only builds the registry object.

WRITE SURFACE (GAP 5, verified by reading operator/tools.py): the upstream
repo write tools resolve paths against REPO_ROOT — the UPSTREAM repo root.
Upstream is READ-ONLY by the standing decree, so acquisition RE-ROOTS the
belt's read/write surface onto the WORKSPACE (her systems): _resolve_in_repo,
write_repo_file, patch_repo_file and read_repo_file now confine to the
workspace root. The aureon-os-upstream tree is additionally fenced: a
fusion-side wrapper on write_repo_file / patch_repo_file / execute_shell
refuses any write into that tree (path-resolved for file tools, text-guard
for shell) and records the refusal on the registry's blocked_calls ledger.
The grounding-index cache is redirected into aureon_fusion/state/ with
workspace-noise trees added to the exclude list (same patch idiom as
cortex.py). Upstream on disk stays untouched.

Upstream hard vetoes remain IN FORCE inside the registry on every dispatch:
  • live-trade / payment / gate-bypass / credential / filing can never be
    routed (GuardedToolRegistry._guard → _hard_boundary_violation);
  • write_repo_file / patch_repo_file refuse sensitive/secret/deploy paths
    and any path escaping the (re-rooted) surface, and .py writes are
    AST-validated;
  • execute_shell refuses the destructive-command set.
  • web_search / web_fetch are offline-guarded under AUREON_AUDIT_MODE and
    record the honest refusal on the ledger.

Import-safe: nothing upstream imported at module import; suppression env
honored via setdefault. Fail-closed everywhere: anything uncertain →
ok=False, never raises. Summaries carry tool names/count + paths only,
never file contents.
"""

import os
import sys
from datetime import datetime, timezone

os.environ.setdefault("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", "1")
os.environ.setdefault("AUREON_AUDIT_MODE", "1")

from .paths import AUREON_UPSTREAM, FUSION_STATE, WORKSPACE

# Repo grounding-index cache redirected under fusion state (the upstream
# repo state/ tree is never written) — same discipline as cortex.py.
REPO_INDEX_CACHE = FUSION_STATE / "pc_repo_index_v6.json"

# Workspace trees excluded from the re-rooted grounding index: pure
# log/data dumps, vendored content and historical archives — retrieval
# stays on her live systems (upstream _EXCLUDE is appended to this).
_INDEX_EXCLUDE_EXTRA = (
    "logs", "tmp", "downloads", "attack_logs", "daemon_codes",
    "academia_downloads", "zenodo_papers", "memory",
    "broadcast_logs", "autonomous_logs", "war_mode_logs",
    "multiversal_logs", "musica_harmonia_logs", "nexus_live_logs",
    "epas_logs", "euphoria_logs", "geo_monitor_logs",
    "full_activation_logs", "clean_sweep_logs", "hnc_daemon_logs",
    "hnc_orchestrator_logs", "hnc_staged_logs", "soul_shield_logs",
    "temporal_logs", "unified_logs", "master_war_logs",
    "timeline_proofs", "substack_output", "real_data_cache",
    "schumann_data_cache", "solar_system_data", "open_data_ingestion",
    "cloud_dive", "skills", "research", "mandala_ws",
    "ra-consulting-website", "R&A_CONSULTING_Package",
    "LSC_AUDIT", "deirbhle_graphics", "kimi-group-chat",
    "aureon-trading", "planetary_monitor", "ghost_fancy_cache",
    "ghost_fancy_results", "gcp_correlation", "pids",
)

# Acquired handles, stashed with a UTC timestamp. Idempotent acquire: an
# already-acquired handle returns ok without re-building.
_HANDLES: dict = {}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_upstream_tools():
    """Import the upstream operator tools exactly once, under suppression
    guards. Pins the upstream repo root on sys.path, loads
    aureon._path_setup (so upstream dotted/bare imports resolve as inside
    the repo), and redirects the repo-index cache into fusion state so the
    upstream repo stays read-only. Imports only — never a launcher."""
    import types
    root = str(AUREON_UPSTREAM)
    if root in sys.path:
        sys.path.remove(root)
    sys.path.insert(0, root)  # pin the upstream repo root for these imports

    import aureon._path_setup  # noqa: F401  (walks aureon/ onto sys.path)

    from aureon.operator import repo_index, tools

    # GAP 5 — re-root the belt's read/write surface onto the WORKSPACE.
    # Upstream handlers resolve every repo path against the REPO_ROOT name
    # in tools.py / repo_index.py; rebinding those module globals confines
    # read_repo_file / write_repo_file / patch_repo_file / list_repo to
    # her systems. The upstream tree on disk stays read-only (the fence
    # below refuses writes into it).
    tools.REPO_ROOT = WORKSPACE
    repo_index.REPO_ROOT = WORKSPACE

    # Redirect the repo-wide grounding index cache into fusion state —
    # index content and search semantics unchanged (mirrors cortex.py),
    # with workspace-noise trees added to the exclude list.
    from aureon.queen.research_corpus_index import ResearchCorpusIndex

    singleton = {"idx": None}
    _exclude = tuple(repo_index._EXCLUDE) + _INDEX_EXCLUDE_EXTRA

    def _fusion_repo_index():
        if singleton["idx"] is None:
            singleton["idx"] = ResearchCorpusIndex(
                root=str(repo_index.REPO_ROOT),
                cache_path=str(REPO_INDEX_CACHE),
                exclude=_exclude,
                ingest_exts=repo_index._INGEST,
            )
        return singleton["idx"]

    def _fusion_reset():
        singleton["idx"] = None

    repo_index.get_operator_repo_index = _fusion_repo_index
    repo_index.reset_operator_repo_index = _fusion_reset

    return types.SimpleNamespace(tools=tools, repo_index=repo_index)


# ───────────────────── upstream read-only fence ────────────────────────────

_UPSTREAM_NAME = "aureon-os-upstream"
# (shell write-ish operators are compiled inside _fence_upstream_writes)


def _is_under_upstream(path_str: str) -> bool:
    """Path-resolved test: does this path land inside the nested
    aureon-os-upstream checkout? Uncertain → True (fail-closed).

    The unified public tree has no nested checkout. The read-only fence
    applies only to that directory, not to the whole repository. Credential
    and live-trading writes stay refused by the sensitive-path check and by
    the self-repair denylist.
    """
    try:
        from pathlib import Path
        p = Path(str(path_str))
        if not p.is_absolute():
            p = (WORKSPACE / str(path_str)).resolve()
        else:
            p = p.resolve()
        return "aureon-os-upstream" in p.parts
    except Exception:
        return True


def _fence_upstream_writes(registry) -> None:
    """Wrap the belt's mutation tools so the aureon-os-upstream tree can
    never be written through this door (standing decree: upstream is
    READ-ONLY). File tools are refused by resolved path; execute_shell by
    write-operator text guard. Every refusal lands on blocked_calls, the
    same ledger the upstream guards use."""
    import json as _json
    import re as _re

    def _blocked(reason, tool):
        try:
            registry.blocked_calls.append({"tool": tool, "reason": reason})
        except Exception:
            pass
        return _json.dumps({"blocked": True, "reason": reason, "tool": tool})

    # Defense in depth: the upstream sensitive-path / escape refusals live in
    # GuardedToolRegistry._guard (execute level). They are mirrored HERE so a
    # handler-direct caller can never write a secret file or escape the
    # surface either — proven necessary when a raw-handler probe bypassed
    # _guard and clobbered aureon_radar/.env (restored same session; the
    # lesson is wired into the fence).
    sensitive_re = _re.compile(
        r"(^|/|\\)\.env|\.env([./\\]|$)|secret|credential|password|"
        r"\.git[/\\]|supervisord|deploy|id_rsa|\.pem|\.key|aws|token",
        _re.IGNORECASE)

    def _surface_refusal(tool, path):
        if not path:
            return _blocked("no path given", tool)
        if sensitive_re.search(str(path)):
            return _blocked(
                f"write to sensitive path refused: {path}", tool)
        if _is_under_upstream(str(path)):
            return _blocked(
                "upstream read-only fence: writes into "
                "aureon-os-upstream are refused by owner decree", tool)
        try:
            from pathlib import Path
            p = Path(str(path))
            if not p.is_absolute():
                p = (WORKSPACE / str(path)).resolve()
            p.relative_to(WORKSPACE.resolve())
        except Exception:
            return _blocked(f"path escapes the workspace surface: {path}",
                            tool)
        return None

    for name in ("write_repo_file", "patch_repo_file"):
        td = registry.get(name)
        orig = getattr(td, "handler", None) if td is not None else None
        if not callable(orig):
            continue

        def _make_file_guard(orig=orig, tool=name):
            def handler(args):
                refusal = _surface_refusal(tool, (args or {}).get("path", ""))
                if refusal is not None:
                    return refusal
                return orig(args or {})
            return handler

        registry.define_tool(
            name,
            td.description + " (upstream tree + sensitive-path write-refused "
                             "by owner decree)",
            td.input_schema, _make_file_guard(),
            effect=td.effect, operation_id=td.operation_id,
            hnc_repair_safe=td.hnc_repair_safe)

    td = registry.get("execute_shell")
    orig = getattr(td, "handler", None) if td is not None else None
    if callable(orig):
        write_op = _re.compile(
            r"(?is)(>>>|>>|>[^=]|\btouch\b|\bcp\b|\bcopy\b|\bxcopy\b|"
            r"\brobocopy\b|\bmv\b|\bmove\b|\bren\b|\brename\b|\bdel\b|"
            r"\berase\b|\brm\b|\bmkdir\b|\bmd\b|\battrib\b|\bfsutil\b|"
            r"\bformat\b|\btype\b[^|]*>)")

        def _shell_guard(args):
            cmd = str((args or {}).get("command", ""))
            if _UPSTREAM_NAME in cmd and write_op.search(cmd):
                return _blocked(
                    "upstream read-only fence: shell writes into "
                    "aureon-os-upstream are refused by owner decree",
                    "execute_shell")
            return orig(args or {})

        registry.define_tool(
            "execute_shell",
            td.description + " (upstream tree write-refused by owner decree)",
            td.input_schema, _shell_guard,
            effect=td.effect, operation_id=td.operation_id,
            hnc_repair_safe=td.hnc_repair_safe)


def _redact(obj):
    """Mask any value whose key smells like a secret. Owner decree: summaries
    are externalized only redacted."""
    import json
    import re
    secret_key = re.compile(r"psk|secret|token|password|credential|api[-_]?key",
                            re.IGNORECASE)

    def walk(value):
        if isinstance(value, dict):
            return {k: ("***REDACTED***" if secret_key.search(str(k))
                        else walk(v)) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [walk(v) for v in value]
        return value

    try:
        return json.loads(json.dumps(walk(obj), default=str, ensure_ascii=False))
    except Exception:  # noqa: BLE001 - redaction must never raise
        return {"note": "summary redacted"}


# ───────────────────── pc_control (in-proc acquire/release) ────────────────

def acquire_pc_control() -> dict:
    """Acquire the upstream governed operator toolbelt with writes and shell
    ENABLED (owner decree: full pc access). Idempotent: an already-acquired
    handle returns ok without re-building. Fail-closed on any error.

    The registry object is built ONLY — no tool is executed here. Upstream
    hard vetoes (credential/payment/live-trade/gate-bypass/filing, sensitive
    paths, destructive shell) stay armed on every future dispatch."""
    try:
        entry = _HANDLES.get("pc_control")
        if entry is not None:
            return {"ok": True,
                    "summary": {"door": "pc_control",
                                "status": "already-acquired",
                                "acquired_at": entry.get("acquired_at"),
                                "handle": type(entry.get("handle")).__name__}}
        up = _load_upstream_tools()
        build_fn = getattr(up.tools, "build_operator_tools", None)
        if not callable(build_fn):
            return {"ok": False,
                    "error": "aureon.operator.tools exposes no "
                             "build_operator_tools()"}
        # Writes + shell enabled per owner decree; allowlist OFF (None) so
        # the full governed belt stands — upstream guards are the boundary.
        registry = build_fn(
            allow_writes=True,
            allow_shell=True,
            allowlist=None,
        )
        if registry is None:
            return {"ok": False, "error": "build_operator_tools() returned None"}
        _fence_upstream_writes(registry)
        names_fn = getattr(registry, "names", None)
        tool_names = sorted(names_fn()) if callable(names_fn) else []
        _HANDLES["pc_control"] = {"handle": registry,
                                  "acquired_at": _utc_now()}
        summary = {
            "door": "pc_control",
            "status": "acquired",
            "acquired_at": _HANDLES["pc_control"]["acquired_at"],
            "handle": type(registry).__name__,
            "tool_count": len(tool_names),
            "tools": tool_names,
            "writes": ("enabled — surface re-rooted to the workspace root "
                       "(aureon-os-upstream write-refused by owner decree)"),
            "shell": ("enabled — destructive-set refused upstream; upstream "
                      "tree write-refused by owner decree"),
            "upstream_path": str(AUREON_UPSTREAM),
            "veto_boundaries": [
                "live-trade / payment / gate-bypass / credential / filing "
                "can never be routed (hard authority boundary)",
                "write/patch refuse sensitive/secret/deploy paths and "
                "surface-escaping paths; .py writes AST-validated",
                "execute_shell refuses the destructive-command set",
                "write surface is the WORKSPACE root; aureon-os-upstream "
                "fenced read-only on file tools + shell; index cache "
                "redirected under aureon_fusion/state/",
            ],
            "note": ("ELEVATE door — decree-record lock class "
                     "(state/pc_control_ack.json) + master_key conscience "
                     "double-check at open; every dispatch journaled"),
        }
        return {"ok": True, "summary": _redact(summary)}
    except Exception as exc:  # noqa: BLE001 - never raise across the door
        return {"ok": False,
                "error": f"acquire_pc_control failed: {type(exc).__name__}"}


def release_pc_control() -> dict:
    """Drop the stashed registry handle. The registry is stateless apart from
    its blocked-call ledger; release only ends this door's in-process claim."""
    try:
        _HANDLES.pop("pc_control", None)
        return {"ok": True}
    except Exception as exc:  # noqa: BLE001
        return {"ok": True, "note": f"release degraded: {type(exc).__name__}"}
