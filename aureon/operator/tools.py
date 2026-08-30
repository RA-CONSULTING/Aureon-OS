"""
Aureon Operator — tool set + guarded dispatch.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The cognition uses tools the way a flagship model does. This module assembles a
:class:`ToolRegistry` from the repo's existing built-ins (state/positions/prices,
publish_thought, execute_shell, web_search/web_fetch, skill_base_status) and adds
operator tools — repo-wide search/read, code validation, and gated file
write/patch.

Every dispatch goes through :class:`GuardedToolRegistry`, which enforces the same
hard authority boundary as the operator's veto (live-trade / payment / gate-bypass
/ credential / filing) plus tool-specific guards (no writes outside the repo, no
writes to secret/deploy files, no destructive shell, syntax-checked ``.py``
writes). Guards run BEFORE the tool executes, so a boundary-crossing call never
runs — this is what makes "full gated autonomy" safe.
"""

from __future__ import annotations

import ast
import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, Iterable

from aureon.inhouse_ai.llm_adapter import _llm_http_disabled
from aureon.inhouse_ai.tool_registry import (
    ToolAuthorizationVerifier,
    ToolDispatchAuthorization,
    ToolDispatchProposal,
    ToolEffect,
    ToolRegistry,
)
from aureon.operator.repo_index import REPO_ROOT
from aureon.operator.repo_index import repo_search as _repo_search

logger = logging.getLogger("aureon.operator.tools")

# Tools that can change the world → always guarded before execution.
CONSEQUENTIAL = {
    "execute_shell",
    "patch_repo_file",
    "publish_thought",
    "touch_module",
    "write_repo_file",
}

_SENSITIVE_PATH_RE = re.compile(
    r"(^|/)\.env|secret|credential|password|\.git/|supervisord|deploy|"
    r"id_rsa|\.pem|\.key|aws|token",
    re.IGNORECASE,
)
_DESTRUCTIVE_SHELL_RE = re.compile(
    r"\brm\s+-rf\b|\bdd\b|\bmkfs|\b:\(\)\{|\bshutdown\b|\breboot\b|>\s*/dev/|"
    r"\bcurl\b[^|]*\|\s*(sh|bash)|\bwget\b[^|]*\|\s*(sh|bash)|\bchmod\s+-R\b",
    re.IGNORECASE,
)


def _blocked(reason: str, **extra: Any) -> str:
    return json.dumps({"blocked": True, "reason": reason, **extra})


def _resolve_in_repo(path: str) -> Path | None:
    """Resolve a path and confirm it stays inside the repo. None if it escapes."""
    try:
        p = (REPO_ROOT / path).resolve() if not os.path.isabs(path) else Path(path).resolve()
        p.relative_to(REPO_ROOT)   # raises if outside
        return p
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Guarded registry
# ─────────────────────────────────────────────────────────────────────────────


class GuardedToolRegistry(ToolRegistry):
    """A ToolRegistry that vets consequential calls against the authority boundary."""

    def __init__(
        self,
        include_builtins: bool = True,
        *,
        governance_required: bool = False,
        authorization_verifier: ToolAuthorizationVerifier | None = None,
        hnc_coherence_required: bool = True,
    ):
        super().__init__(
            include_builtins=include_builtins,
            governance_required=governance_required,
            authorization_verifier=authorization_verifier,
            hnc_coherence_required=hnc_coherence_required,
        )
        self.blocked_calls: list = []
        # The coherence membrane (set per turn by cognition): ``None`` means
        # unrestricted; a set means ONLY those tools are within the current
        # aperture. The hive field decides this, never the individual unit.
        self.aperture_allowed: set | None = None
        self.aperture_note: str = ""

    def execute(
        self,
        name: str,
        arguments: Dict[str, Any],
        *,
        proposal: ToolDispatchProposal | None = None,
        authorization: ToolDispatchAuthorization | None = None,
        governance_required: bool | None = None,
    ) -> str:
        governed = (
            self.governance_required
            or bool(governance_required)
            or self.hnc_coherence_required
        )
        args = arguments or {}
        # Rebind at this outer dispatch boundary before any handler can run.
        # ToolRegistry repeats this check before consuming the authorization.
        if governed:
            binding_error = self._dispatch_binding_error(name, args, proposal)
            if binding_error:
                self.blocked_calls.append({"tool": name, "reason": binding_error})
                logger.warning("tool %s blocked: %s", name, binding_error)
                return self._blocked_governed_dispatch(
                    name=name,
                    proposal=proposal,
                    authorization=(
                        authorization
                        if isinstance(authorization, ToolDispatchAuthorization)
                        else None
                    ),
                    reason=binding_error,
                )
        # Outer wall first: the hard authority boundary is absolute.
        reason = self._guard(name, args)
        if reason:
            self.blocked_calls.append({"tool": name, "reason": reason})
            logger.warning("tool %s blocked: %s", name, reason)
            if governed:
                return self._blocked_governed_dispatch(
                    name=name,
                    proposal=proposal,
                    authorization=(
                        authorization
                        if isinstance(authorization, ToolDispatchAuthorization)
                        else None
                    ),
                    reason=reason,
                )
            return _blocked(reason, tool=name)
        # Inner membrane second: the live-field coherence aperture.
        if self.aperture_allowed is not None and name not in self.aperture_allowed:
            reason = (f"coherence gate: {self.aperture_note or 'aperture restricted'}"
                      f" — '{name}' is outside the field's current reach")
            self.blocked_calls.append({"tool": name, "reason": reason})
            logger.info("tool %s held by the coherence gate: %s", name, reason)
            if governed:
                return self._blocked_governed_dispatch(
                    name=name,
                    proposal=proposal,
                    authorization=(
                        authorization
                        if isinstance(authorization, ToolDispatchAuthorization)
                        else None
                    ),
                    reason=reason,
                )
            return _blocked(reason, tool=name)
        if governed:
            return super().execute(
                name,
                args,
                proposal=proposal,
                authorization=authorization,
                governance_required=True,
            )
        return super().execute(name, args)

    @staticmethod
    def _guard(name: str, args: Dict[str, Any]) -> str | None:
        # Import here to avoid an import cycle (operator imports tools).
        from aureon.operator.aureon_operator import _hard_boundary_violation

        blob = f"{name} {json.dumps(args, default=str)}"
        # Read-only cognition may inspect and discuss consequential domains.
        # The content boundary applies to generic mutation primitives that
        # could otherwise become a shell/write/publish bypass. Typed economic
        # and statutory routes keep their own exact execution boundaries.
        if name in CONSEQUENTIAL and _hard_boundary_violation(blob):
            return (
                "generic mutation bypass boundary "
                "(live-trade / payment / bypass / credential / filing)"
            )

        if name in ("write_repo_file", "patch_repo_file"):
            path = str(args.get("path", ""))
            if not path:
                return "no path given"
            if _SENSITIVE_PATH_RE.search(path):
                return f"write to sensitive path refused: {path}"
            if _resolve_in_repo(path) is None:
                return f"path escapes the repository: {path}"
        if name == "execute_shell" and _DESTRUCTIVE_SHELL_RE.search(str(args.get("command", ""))):
            return "destructive shell command refused"
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Operator tool handlers
# ─────────────────────────────────────────────────────────────────────────────


def _h_sense_organism(args: Dict[str, Any]) -> str:
    from aureon.core.aureon_connectome import get_connectome

    status = get_connectome().status()
    mesh: Dict[str, Any] = {}
    try:
        from aureon.core.aureon_mycelium import get_mycelium

        raw = get_mycelium().get_mesh_status()
        mesh = {"connected_systems": raw.get("connected_systems", []),
                "hives": raw.get("hive_count", raw.get("hives"))}
    except Exception as exc:  # noqa: BLE001 — mesh is optional
        mesh = {"unavailable": str(exc)[:120]}
    return json.dumps({"connectome": status, "mycelium": mesh}, default=str)


def _h_list_organism(args: Dict[str, Any]) -> str:
    from aureon.core.aureon_connectome import get_connectome

    limit = max(1, min(200, int(args.get("limit", 40) or 40)))
    nodes = get_connectome().nodes(
        domain=str(args["domain"]) if args.get("domain") else None,
        status=str(args["status"]) if args.get("status") else None,
    )
    return json.dumps({
        "count": len(nodes),
        "nodes": [{"module": n["module"], "domain": n["domain"],
                   "status": n["status"], "topic": n["organism_topic"]} for n in nodes[:limit]],
        "truncated": len(nodes) > limit,
    }, default=str)


def _h_touch_module(args: Dict[str, Any]) -> str:
    from aureon.core.aureon_connectome import get_connectome

    module = str(args.get("module", "")).strip()
    if not module:
        return json.dumps({"error": "module required"})
    return json.dumps(get_connectome().touch(module), default=str)


def _h_repo_search(args: Dict[str, Any]) -> str:
    query = str(args.get("query", "")).strip()
    top_k = int(args.get("top_k", 4) or 4)
    if not query:
        return json.dumps({"error": "query required"})
    hits = _repo_search(query, top_k=top_k)
    return json.dumps(
        {"results": [{"doc_id": s.doc_id, "score": round(s.score, 3), "text": s.text[:600]} for s in hits]},
        default=str,
    )


def _h_read_repo_file(args: Dict[str, Any]) -> str:
    path = str(args.get("path", ""))
    p = _resolve_in_repo(path)
    if p is None or not p.is_file():
        return json.dumps({"error": f"not a readable repo file: {path}"})
    if _SENSITIVE_PATH_RE.search(path):
        return _blocked("sensitive path", tool="read_repo_file")
    try:
        text = p.read_text(encoding="utf-8", errors="replace")[:20000]
        return json.dumps({"path": path, "text": text})
    except Exception as e:  # noqa: BLE001
        return json.dumps({"error": str(e)})


def _h_list_repo(args: Dict[str, Any]) -> str:
    path = str(args.get("path", "") or ".")
    p = _resolve_in_repo(path)
    if p is None or not p.is_dir():
        return json.dumps({"error": f"not a repo directory: {path}"})
    try:
        entries = sorted(e.name + ("/" if e.is_dir() else "") for e in p.iterdir())
        return json.dumps({"path": path, "entries": entries[:400]})
    except Exception as e:  # noqa: BLE001
        return json.dumps({"error": str(e)})


def _h_code_validate(args: Dict[str, Any]) -> str:
    """Syntax-check code (always) + optional sandbox-safety check (SkillValidator)."""
    code = str(args.get("code", ""))
    if not code.strip():
        return json.dumps({"error": "code required"})
    result: Dict[str, Any] = {"syntax_ok": True, "syntax_error": "", "sandbox_safe": None, "sandbox_errors": []}
    try:
        ast.parse(code)
    except SyntaxError as e:
        result["syntax_ok"] = False
        result["syntax_error"] = f"line {e.lineno}: {e.msg}"
    if args.get("sandbox_safe"):
        try:
            from aureon.code_architect.validator import SkillValidator

            ok, errs = SkillValidator().static_check(code)
            result["sandbox_safe"] = bool(ok)
            result["sandbox_errors"] = list(errs)[:8]
        except Exception as e:  # noqa: BLE001
            result["sandbox_errors"] = [f"validator unavailable: {e}"]
    return json.dumps(result)


def _h_write_repo_file(args: Dict[str, Any]) -> str:
    path = str(args.get("path", ""))
    content = str(args.get("content", ""))
    p = _resolve_in_repo(path)
    if p is None:
        return _blocked("path escapes repo", tool="write_repo_file")
    if path.endswith(".py"):
        try:
            ast.parse(content)
        except SyntaxError as e:
            return json.dumps({"error": f"refusing to write .py with syntax error: line {e.lineno}: {e.msg}"})
    try:
        from aureon.queen.queen_code_architect import QueenCodeArchitect

        ok = QueenCodeArchitect(repo_path=str(REPO_ROOT)).write_file(str(p), content, backup=True)
        return json.dumps({"written": bool(ok), "path": path, "bytes": len(content)})
    except Exception as e:  # noqa: BLE001
        return json.dumps({"error": str(e)})


def _h_patch_repo_file(args: Dict[str, Any]) -> str:
    path = str(args.get("path", ""))
    old, new = str(args.get("old", "")), str(args.get("new", ""))
    p = _resolve_in_repo(path)
    if p is None or not p.is_file():
        return json.dumps({"error": f"not a repo file: {path}"})
    try:
        from aureon.queen.queen_code_architect import QueenCodeArchitect

        arch = QueenCodeArchitect(repo_path=str(REPO_ROOT))
        ok = arch.apply_edit(str(p), old, new, backup=True)
        return json.dumps({"patched": bool(ok), "path": path})
    except Exception as e:  # noqa: BLE001
        return json.dumps({"error": str(e)})


def _h_list_skills(args: Dict[str, Any]) -> str:
    """Read-only view of the SkillLibrary — the organism's assimilated,
    validated procedures. Listing only; skill EXECUTION stays behind its own
    gates (validators + Queen approval), never through this tool."""
    try:
        from aureon.code_architect.skill_library import get_skill_library

        lib = get_skill_library()
        query = str(args.get("query") or "").strip()
        skills = lib.search(query) if query else lib.all()
        rows = [{
            "name": s.name,
            "category": str(getattr(s, "category", "")),
            "level": getattr(getattr(s, "level", None), "name", str(getattr(s, "level", ""))),
            "status": getattr(getattr(s, "status", None), "value", str(getattr(s, "status", ""))),
            "description": str(getattr(s, "description", ""))[:160],
        } for s in skills[:20]]
        return json.dumps({
            "skills": rows, "total_in_library": len(lib),
            "note": ("read-only: validated procedures the organism already "
                     "knows; execution stays gated behind validators + Queen "
                     "approval, never through this tool"),
        })
    except Exception as exc:  # noqa: BLE001 — an empty library is honest, not a crash
        return json.dumps({"skills": [], "total_in_library": 0,
                           "error": str(exc)[:200]})


def _wrap_offline(orig_handler, registry: GuardedToolRegistry | None = None,
                  tool_name: str = ""):
    """Wrap a network tool so it no-ops under the repo's offline/audit guards.

    The refusal is RECORDED on the registry's ``blocked_calls`` (when given),
    exactly like a guard block — so the tool ledger, the actualization record,
    and the acquisition outcome all see the honest truth that the network was
    unreachable, never a silent no-op."""
    def handler(args: Dict[str, Any]) -> str:
        if _llm_http_disabled():
            reason = "network disabled (AUREON_LLM_OFFLINE / AUREON_AUDIT_MODE)"
            if registry is not None:
                registry.blocked_calls.append({"tool": tool_name, "reason": reason})
            return _blocked(reason)
        return orig_handler(args)
    return handler


# ─────────────────────────────────────────────────────────────────────────────
# Assembly
# ─────────────────────────────────────────────────────────────────────────────

_SCHEMA_STR = {"type": "object", "properties": {}, "required": [], "additionalProperties": False}

# The ONLY tools a tenant-plane engine may hold.
#
# This is an ALLOWLIST, not a denylist, and that distinction is the whole security property. A tenant
# supplies their own ``base_url``, so the model answering their turn is a server THEY control and every
# ``tool_call`` it emits is dispatched on the operator host — the conscience veto runs *after* the tool
# loop, so it cannot undo a side effect. An adversarial audit proved a denylist ("drop shell + writes")
# left 14 of 17 tools reachable: ``web_fetch`` (arbitrary outbound HTTP from the operator's IP — SSRF to
# co-located instance services and cloud metadata), ``touch_module`` (import any dotted module),
# ``publish_thought`` (writes the process-global ThoughtBus, bypassing the per-tenant isolated bus),
# ``read_state`` / ``read_positions`` / ``read_prices`` (the instance's live trading state), and
# ``repo_search`` / ``read_repo_file`` / ``list_repo`` (repository contents).
#
# So the tenant belt is pinned positively to pure-compute tools only: ``code_validate`` is ``ast.parse``
# plus an optional static check — no I/O, no network, no shared state. Applied as a *final filter*, so a
# new built-in added upstream can never silently widen the tenant surface.
TENANT_ALLOWED_TOOLS = frozenset({"code_validate"})


def build_operator_tools(
    *,
    allow_writes: bool = True,
    allow_shell: bool = True,
    allowlist: Iterable[str] | None = None,
    governance_required: bool = False,
    authorization_verifier: ToolAuthorizationVerifier | None = None,
    hnc_coherence_required: bool = True,
) -> GuardedToolRegistry:
    """Assemble the cognition's toolbelt. Read tools always on; writes/shell gated.

    ``allowlist`` — when given, the finished registry is pruned to exactly these names. Use
    :data:`TENANT_ALLOWED_TOOLS` for any engine driven by a model the caller controls.
    """
    reg = GuardedToolRegistry(
        include_builtins=True,
        governance_required=governance_required,
        authorization_verifier=authorization_verifier,
        hnc_coherence_required=hnc_coherence_required,
    )

    # Offline-guard the network tools (built-ins don't check the guard today).
    for net in ("web_search", "web_fetch"):
        td = reg.get(net)
        if td and td.handler:
            reg.define_tool(net, td.description + " (offline-guarded)", td.input_schema,
                            _wrap_offline(td.handler, reg, net),
                            effect=td.effect, operation_id=td.operation_id,
                            hnc_repair_safe=td.hnc_repair_safe)

    # Repo-wide search replaces the built-in docs-only repo_search.
    reg.define_tool(
        "repo_search",
        "Search the ENTIRE Aureon repository (all docs and Python source) for relevant snippets. Use to ground answers in the repo.",
        {"type": "object",
         "properties": {"query": {"type": "string", "description": "search query"},
                        "top_k": {"type": "integer", "description": "max results (default 4)"}},
         "required": ["query"], "additionalProperties": False},
        _h_repo_search,
        effect=ToolEffect.READ_ONLY,
        operation_id="aureon.operator.repo_search.v1",
    )
    reg.define_tool(
        "read_repo_file",
        "Read the contents of a file inside the Aureon repository (first 20k chars).",
        {"type": "object", "properties": {"path": {"type": "string", "description": "repo-relative path"}},
         "required": ["path"], "additionalProperties": False},
        _h_read_repo_file,
        effect=ToolEffect.READ_ONLY,
        operation_id="aureon.operator.read_repo_file.v1",
    )
    reg.define_tool(
        "list_repo",
        "List the entries of a directory inside the Aureon repository.",
        {"type": "object", "properties": {"path": {"type": "string", "description": "repo-relative dir (default repo root)"}},
         "required": [], "additionalProperties": False},
        _h_list_repo,
        effect=ToolEffect.READ_ONLY,
        operation_id="aureon.operator.list_repo.v1",
    )
    reg.define_tool(
        "sense_organism",
        "Sense the whole Aureon organism: connectome coverage (nodes/linked/touched/woven), "
        "mycelium mesh membership, and honest wiring depth across all ~1,200 modules.",
        {"type": "object", "properties": {}, "required": [], "additionalProperties": False},
        _h_sense_organism,
        effect=ToolEffect.READ_ONLY,
        operation_id="aureon.operator.sense_organism.v1",
    )
    reg.define_tool(
        "list_organism",
        "List the organism's modules from the connectome manifest, optionally filtered by "
        "domain (e.g. queen, trading_decision, cognition) and/or wiring status "
        "(unfelt|linked|touched|woven|failed|denied).",
        {"type": "object",
         "properties": {"domain": {"type": "string", "description": "filter by organism domain"},
                        "status": {"type": "string", "description": "filter by wiring status"},
                        "limit": {"type": "integer", "description": "max nodes returned (default 40)"}},
         "required": [], "additionalProperties": False},
        _h_list_organism,
        effect=ToolEffect.READ_ONLY,
        operation_id="aureon.operator.list_organism.v1",
    )
    reg.define_tool(
        "touch_module",
        "Touch a module of the organism: import it safely (side-effect suppression enforced, "
        "loop-at-import modules denied) and feel its shape — docstring, classes, functions, "
        "get_* singleton doors. This is how the cognition reaches legacy code as a live part of itself.",
        {"type": "object",
         "properties": {"module": {"type": "string", "description": "dotted module, e.g. aureon.harmonic.aureon_harmonic_seed"}},
         "required": ["module"], "additionalProperties": False},
        _h_touch_module,
        effect=ToolEffect.PRIVILEGED,
        operation_id="aureon.operator.touch_module.v1",
    )
    reg.define_tool(
        "list_skills",
        "List the organism's assimilated skills (validated procedures) from the SkillLibrary, "
        "optionally filtered by a search query. READ-ONLY — execution stays gated elsewhere.",
        {"type": "object",
         "properties": {"query": {"type": "string", "description": "substring filter (optional)"}},
         "required": [], "additionalProperties": False},
        _h_list_skills,
        effect=ToolEffect.READ_ONLY,
        operation_id="aureon.operator.list_skills.v1",
    )
    reg.define_tool(
        "code_validate",
        "Syntax-check Python code (ast.parse). Set sandbox_safe=true to also check it against the sandboxed-skill allow-list.",
        {"type": "object",
         "properties": {"code": {"type": "string", "description": "Python source to validate"},
                        "sandbox_safe": {"type": "boolean", "description": "also run the sandbox static check"}},
         "required": ["code"], "additionalProperties": False},
        _h_code_validate,
        effect=ToolEffect.READ_ONLY,
        operation_id="aureon.operator.code_validate.v1",
        hnc_repair_safe=True,
    )

    if allow_writes:
        reg.define_tool(
            "write_repo_file",
            "Write a file inside the repository (auto-backup). Refused for sensitive/secret/deploy paths, paths outside the repo, and .py files with syntax errors.",
            {"type": "object",
             "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
             "required": ["path", "content"], "additionalProperties": False},
            _h_write_repo_file,
            effect=ToolEffect.LOCAL_MUTATION,
            operation_id="aureon.operator.write_repo_file.v1",
        )
        reg.define_tool(
            "patch_repo_file",
            "Replace an exact snippet in a repository file (auto-backup). Same path guards as write_repo_file.",
            {"type": "object",
             "properties": {"path": {"type": "string"}, "old": {"type": "string"}, "new": {"type": "string"}},
             "required": ["path", "old", "new"], "additionalProperties": False},
            _h_patch_repo_file,
            effect=ToolEffect.LOCAL_MUTATION,
            operation_id="aureon.operator.patch_repo_file.v1",
        )

    if not allow_shell and "execute_shell" in reg:
        reg._tools.pop("execute_shell", None)

    # Final positive filter — everything not explicitly allowed is removed, whatever registered it.
    if allowlist is not None:
        keep = set(allowlist)
        for name in [n for n in reg.names() if n not in keep]:
            reg._tools.pop(name, None)

    return reg


__all__ = ["build_operator_tools", "GuardedToolRegistry", "CONSEQUENTIAL", "TENANT_ALLOWED_TOOLS"]
