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
from typing import Any, Dict, Optional

from aureon.inhouse_ai.tool_registry import ToolRegistry
from aureon.inhouse_ai.llm_adapter import _llm_http_disabled
from aureon.operator.repo_index import REPO_ROOT, repo_search as _repo_search

logger = logging.getLogger("aureon.operator.tools")

# Tools that can change the world → always guarded before execution.
CONSEQUENTIAL = {"write_repo_file", "patch_repo_file", "execute_shell"}

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


def _resolve_in_repo(path: str) -> Optional[Path]:
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

    def __init__(self, include_builtins: bool = True):
        super().__init__(include_builtins=include_builtins)
        self.blocked_calls: list = []

    def execute(self, name: str, arguments: Dict[str, Any]) -> str:
        reason = self._guard(name, arguments or {})
        if reason:
            self.blocked_calls.append({"tool": name, "reason": reason})
            logger.warning("tool %s blocked: %s", name, reason)
            return _blocked(reason, tool=name)
        return super().execute(name, arguments or {})

    @staticmethod
    def _guard(name: str, args: Dict[str, Any]) -> Optional[str]:
        # Import here to avoid an import cycle (operator imports tools).
        from aureon.operator.aureon_operator import _hard_boundary_violation

        blob = f"{name} {json.dumps(args, default=str)}"
        if _hard_boundary_violation(blob):
            return "hard authority boundary (live-trade / payment / bypass / credential / filing)"

        if name in ("write_repo_file", "patch_repo_file"):
            path = str(args.get("path", ""))
            if not path:
                return "no path given"
            if _SENSITIVE_PATH_RE.search(path):
                return f"write to sensitive path refused: {path}"
            if _resolve_in_repo(path) is None:
                return f"path escapes the repository: {path}"
        if name == "execute_shell":
            if _DESTRUCTIVE_SHELL_RE.search(str(args.get("command", ""))):
                return "destructive shell command refused"
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Operator tool handlers
# ─────────────────────────────────────────────────────────────────────────────


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


def _wrap_offline(orig_handler):
    """Wrap a network tool so it no-ops under the repo's offline/audit guards."""
    def handler(args: Dict[str, Any]) -> str:
        if _llm_http_disabled():
            return _blocked("network disabled (AUREON_LLM_OFFLINE / AUREON_AUDIT_MODE)")
        return orig_handler(args)
    return handler


# ─────────────────────────────────────────────────────────────────────────────
# Assembly
# ─────────────────────────────────────────────────────────────────────────────

_SCHEMA_STR = {"type": "object", "properties": {}, "required": [], "additionalProperties": False}


def build_operator_tools(
    *,
    allow_writes: bool = True,
    allow_shell: bool = True,
) -> GuardedToolRegistry:
    """Assemble the cognition's toolbelt. Read tools always on; writes/shell gated."""
    reg = GuardedToolRegistry(include_builtins=True)

    # Offline-guard the network tools (built-ins don't check the guard today).
    for net in ("web_search", "web_fetch"):
        td = reg.get(net)
        if td and td.handler:
            reg.define_tool(net, td.description + " (offline-guarded)", td.input_schema, _wrap_offline(td.handler))

    # Repo-wide search replaces the built-in docs-only repo_search.
    reg.define_tool(
        "repo_search",
        "Search the ENTIRE Aureon repository (all docs and Python source) for relevant snippets. Use to ground answers in the repo.",
        {"type": "object",
         "properties": {"query": {"type": "string", "description": "search query"},
                        "top_k": {"type": "integer", "description": "max results (default 4)"}},
         "required": ["query"], "additionalProperties": False},
        _h_repo_search,
    )
    reg.define_tool(
        "read_repo_file",
        "Read the contents of a file inside the Aureon repository (first 20k chars).",
        {"type": "object", "properties": {"path": {"type": "string", "description": "repo-relative path"}},
         "required": ["path"], "additionalProperties": False},
        _h_read_repo_file,
    )
    reg.define_tool(
        "list_repo",
        "List the entries of a directory inside the Aureon repository.",
        {"type": "object", "properties": {"path": {"type": "string", "description": "repo-relative dir (default repo root)"}},
         "required": [], "additionalProperties": False},
        _h_list_repo,
    )
    reg.define_tool(
        "code_validate",
        "Syntax-check Python code (ast.parse). Set sandbox_safe=true to also check it against the sandboxed-skill allow-list.",
        {"type": "object",
         "properties": {"code": {"type": "string", "description": "Python source to validate"},
                        "sandbox_safe": {"type": "boolean", "description": "also run the sandbox static check"}},
         "required": ["code"], "additionalProperties": False},
        _h_code_validate,
    )

    if allow_writes:
        reg.define_tool(
            "write_repo_file",
            "Write a file inside the repository (auto-backup). Refused for sensitive/secret/deploy paths, paths outside the repo, and .py files with syntax errors.",
            {"type": "object",
             "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
             "required": ["path", "content"], "additionalProperties": False},
            _h_write_repo_file,
        )
        reg.define_tool(
            "patch_repo_file",
            "Replace an exact snippet in a repository file (auto-backup). Same path guards as write_repo_file.",
            {"type": "object",
             "properties": {"path": {"type": "string"}, "old": {"type": "string"}, "new": {"type": "string"}},
             "required": ["path", "old", "new"], "additionalProperties": False},
            _h_patch_repo_file,
        )

    if not allow_shell and "execute_shell" in reg:
        reg._tools.pop("execute_shell", None)

    return reg


__all__ = ["build_operator_tools", "GuardedToolRegistry", "CONSEQUENTIAL"]
