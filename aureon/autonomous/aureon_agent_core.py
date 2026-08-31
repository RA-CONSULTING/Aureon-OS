#!/usr/bin/env python3
"""
aureon_agent_core.py -- Master Brain of Aureon

The unified agent execution layer that gives the Queen the ability to do
ANYTHING a human can do on a Windows PC.  It is a tool registry + executor
called by both the sentient loop (proactive) and the conversation loop
(reactive).

Tool categories:
  1. Shell execution        6. Desktop control (wire SafeDesktopControl)
  2. App launcher           7. System info
  3. Web search / browsing  8. Knowledge query (wire global_history_db)
  4. File system            9. Trading (wire exchange clients)
  5. Code execution        10. Communication (TTS / ThoughtBus)
"""

from __future__ import annotations

import datetime
import ipaddress
import json
import logging
import platform
import re
import socket
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence
from urllib.parse import urlsplit

# ---------------------------------------------------------------------------
# Repository-local boundaries
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[2]
STATE_DIR = REPO_ROOT / "state"

logger = logging.getLogger("aureon.agent_core")

# ---------------------------------------------------------------------------
# Optional dependency imports (graceful degradation)
# ---------------------------------------------------------------------------
try:
    import psutil  # type: ignore
    HAS_PSUTIL = True
except ImportError:
    psutil = None  # type: ignore[assignment]
    HAS_PSUTIL = False

# Effect-capable or persistence-capable subsystems are imported lazily.

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
ACTION_LOG_PATH = STATE_DIR / "agent_action_log.jsonl"
COMMAND_HISTORY_PATH = STATE_DIR / "agent_command_history.jsonl"

MAX_AGENT_PARAM_BYTES = 64 * 1024
MAX_PATH_CHARS = 4096
MAX_READ_BYTES = 1024 * 1024
MAX_READ_LINES = 2000
MAX_DIRECTORY_ENTRIES = 500
MAX_GLOB_CHARS = 256
MAX_URL_CHARS = 2048
MAX_WEB_TEXT_CHARS = 10_000
MAX_SQL_CHARS = 16_384
SENSITIVE_DIRECTORY_NAMES = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        ".ssh",
        ".gnupg",
        ".aws",
        ".azure",
        ".kube",
        "credentials",
        "credential",
        "secrets",
        "secret",
        "wallet",
        "wallets",
        "keystore",
        "keystores",
    }
)
SENSITIVE_FILE_NAMES = frozenset(
    {
        ".npmrc",
        ".pypirc",
        ".netrc",
        ".git-credentials",
        "credentials.json",
        "secrets.json",
        "token.json",
        "wallet.json",
        "keystore.json",
        "client_secret.json",
        "service-account.json",
        "id_rsa",
        "id_dsa",
        "id_ecdsa",
        "id_ed25519",
    }
)
SENSITIVE_FILE_SUFFIXES = (
    ".pem",
    ".key",
    ".p12",
    ".pfx",
    ".jks",
    ".keystore",
    ".kdbx",
    ".wallet",
    ".token",
    ".secrets.json",
    ".credentials.json",
)
SENSITIVE_NAME_MARKERS = (
    "credential",
    "secret",
    "wallet",
    "keystore",
    "private_key",
    "private-key",
    "seed_phrase",
    "seed-phrase",
    "mnemonic",
    "access_token",
    "refresh_token",
    "api_key",
    "_token",
    "-token",
)
WINDOWS_DEVICE_NAMES = frozenset(
    {"con", "prn", "aux", "nul"}
    | {f"com{number}" for number in range(1, 10)}
    | {f"lpt{number}" for number in range(1, 10)}
)


def _effect_hold(effect: str, reason: str = "production_magic_star_release_required") -> dict:
    """Stable fail-closed receipt for effects without a releasable capability."""

    return {
        "success": False,
        "status": "hold",
        "effect": str(effect),
        "error": reason,
        "plumber_release_required": True,
        "magic_star_required": True,
        "production_ready": False,
    }

# ---------------------------------------------------------------------------
# Intent routing table
# ---------------------------------------------------------------------------
INTENT_MAP: Dict[str, str] = {
    # shell
    "shell": "execute_shell",
    "run_command": "execute_shell",
    "terminal": "execute_shell",
    # apps
    "open_app": "open_app",
    "launch": "open_app",
    "close_app": "close_app",
    "kill": "close_app",
    "list_apps": "list_running_apps",
    "focus_window": "focus_window",
    # web
    "web_search": "web_search",
    "search_web": "web_search",
    "google": "web_search",
    "web_fetch": "web_fetch",
    "fetch_url": "web_fetch",
    "open_url": "open_url",
    "browse": "open_url",
    # filesystem
    "list_dir": "list_dir",
    "ls": "list_dir",
    "dir": "list_dir",
    "read_file": "read_file",
    "cat": "read_file",
    "open_file": "open_file",
    "write_file": "write_file",
    "find_files": "find_files",
    "search_files": "find_files",
    "keyword_search": "keyword_search_files",
    "keyword_search_files": "keyword_search_files",
    "search_text": "keyword_search_files",
    "search_tests": "keyword_search_files",
    "online_research_cinema": "online_research_cinema",
    "research_cinema": "online_research_cinema",
    "make_research_paper": "online_research_cinema",
    "research_metacognition": "research_metacognition",
    "metacognitive_research": "research_metacognition",
    "understand_research": "research_metacognition",
    "copy_file": "copy_file",
    "move_file": "move_file",
    "delete_file": "delete_file",
    "file_info": "file_info",
    "create_dir": "create_dir",
    # code
    "execute_python": "execute_python",
    "run_code": "execute_python",
    "create_script": "create_script",
    "run_script": "run_script",
    # desktop
    "click": "click",
    "left_click": "click",
    "move_mouse": "move_mouse",
    "right_click": "right_click",
    "double_click": "double_click",
    "type_text": "type_text",
    "type": "type_text",
    "press_key": "press_key",
    "hotkey": "hotkey",
    "scroll": "scroll",
    "screenshot": "screenshot",
    "desktop_status": "desktop_status",
    "desktop_arm_live": "desktop_arm_live",
    "desktop_arm_dry_run": "desktop_arm_dry_run",
    "desktop_bind_window": "desktop_bind_window",
    "desktop_disarm": "desktop_disarm",
    "desktop_emergency_stop": "desktop_emergency_stop",
    "desktop_clear_emergency_stop": "desktop_clear_emergency_stop",
    # system
    "system_info": "system_info",
    "processes": "running_processes",
    "network_status": "network_status",
    "kill_process": "kill_process",
    # knowledge
    "query_knowledge": "query_knowledge",
    "query_db": "query_knowledge",
    "search_knowledge": "search_knowledge",
    "market_summary": "get_market_summary",
    "portfolio": "get_portfolio_summary",
    # trading
    "get_balances": "get_balances",
    "get_positions": "get_positions",
    "place_order": "place_order",
    "get_recent_trades": "get_recent_trades",
    # communication
    "speak": "speak",
    "say": "speak",
    "notify": "notify",
    "think": "think",
}


# ═══════════════════════════════════════════════════════════════════════════
#  AureonAgentCore
# ═══════════════════════════════════════════════════════════════════════════
class AureonAgentCore:
    """Unified tool registry + executor for the Aureon agent."""

    def __init__(
        self,
        *,
        workspace_roots: Optional[Sequence[str | Path]] = None,
        web_reader: Optional[Callable[[str], Mapping[str, Any]]] = None,
        allowed_web_hosts: Optional[Sequence[str]] = None,
        account_reader: Optional[
            Callable[[str, str, Mapping[str, Any]], Any]
        ] = None,
        knowledge_connection: Optional[Any] = None,
        trade_authorization_provider: Optional[Callable[[Any], Any]] = None,
        final_trade_dispatcher: Optional[Callable[[Any], Mapping[str, Any]]] = None,
    ) -> None:
        self.repo_root = REPO_ROOT
        self.state_dir = STATE_DIR
        self._stats: Dict[str, int] = {"calls": 0, "success": 0, "failure": 0}
        raw_roots = list(workspace_roots or (REPO_ROOT,))
        if not raw_roots or len(raw_roots) > 8:
            raise ValueError("workspace_roots_invalid")
        self._workspace_roots = tuple(Path(root).resolve() for root in raw_roots)
        self._web_reader = web_reader
        self._allowed_web_hosts = frozenset(
            str(host or "").strip().lower().rstrip(".")
            for host in (allowed_web_hosts or ())
            if str(host or "").strip()
        )
        self._account_reader = account_reader
        self._trade_authorization_provider = trade_authorization_provider
        self._final_trade_dispatcher = final_trade_dispatcher

        # Lazy-init wired subsystems
        self._thought_bus: Optional[Any] = None
        self._desktop: Optional[Any] = None
        self._db_conn: Optional[Any] = knowledge_connection
        self._laptop: Optional[Any] = None
        self._parser: Optional[Any] = None

        # The legacy LaptopControl HAL contains ungoverned mutation primitives.
        # It is intentionally not attached to the master executor.  Screen and
        # input automation are exposed only through a governed gateway.
        self._laptop = None

    # ------------------------------------------------------------------
    # Subsystem accessors (lazy)
    # ------------------------------------------------------------------
    def _get_thought_bus(self):
        # Deliberately no lazy constructor: the historical implementation
        # created persistence as a side effect of an otherwise generic call.
        return self._thought_bus

    def _get_desktop(self):
        if self._desktop is None:
            try:
                from aureon.autonomous.aureon_governed_desktop_gateway import (
                    get_governed_desktop_gateway,
                )

                # No environment flag or persisted state may auto-arm the organism.
                self._desktop = get_governed_desktop_gateway()
            except Exception:
                self._desktop = None
        return self._desktop

    def _get_db(self):
        # A caller may inject an already-open read-only connection. The core
        # never constructs a database or creates schema on its default path.
        return self._db_conn

    def _get_parser(self):
        if self._parser is None:
            try:
                from aureon.autonomous.aureon_instruction_parser import InstructionParser

                self._parser = InstructionParser()
            except Exception:
                self._parser = None
        return self._parser

    def _resolve_workspace_path(
        self,
        raw_path: str | Path,
        *,
        must_exist: bool = False,
    ) -> Path:
        text = str(raw_path or "")
        if not text or len(text) > MAX_PATH_CHARS or "\x00" in text:
            raise ValueError("workspace_path_invalid")
        candidate = Path(text)
        if not candidate.is_absolute():
            candidate = self._workspace_roots[0] / candidate
        resolved = candidate.resolve(strict=False)
        matching_root = next(
            (
                root
                for root in self._workspace_roots
                if resolved == root or resolved.is_relative_to(root)
            ),
            None,
        )
        if matching_root is None:
            raise ValueError("workspace_path_outside_allowlist")
        relative = resolved.relative_to(matching_root)
        self._assert_path_not_sensitive(relative)
        if must_exist and not resolved.exists():
            raise ValueError("workspace_path_not_found")
        return resolved

    @staticmethod
    def _assert_path_not_sensitive(relative_path: Path) -> None:
        """Deny VCS internals and credential-like material within a safe root."""

        parts = tuple(
            part.lower().split(":", 1)[0].rstrip(" .")
            for part in relative_path.parts
            if part not in {"", "."}
        )
        if not parts:
            return
        if any(part.split(".", 1)[0] in WINDOWS_DEVICE_NAMES for part in parts):
            raise ValueError("workspace_special_device_path_denied")
        if any(part in SENSITIVE_DIRECTORY_NAMES for part in parts[:-1]):
            raise ValueError("workspace_sensitive_path_denied")
        name = parts[-1]
        if (
            name in SENSITIVE_DIRECTORY_NAMES
            or name in SENSITIVE_FILE_NAMES
            # Repositories in this workspace use variants such as ``.env1``
            # as well as the conventional ``.env.local`` form.  Treat the
            # complete prefix family as credential material.
            or name.startswith(".env")
            or name.endswith(SENSITIVE_FILE_SUFFIXES)
            or any(marker in name for marker in SENSITIVE_NAME_MARKERS)
        ):
            raise ValueError("workspace_sensitive_path_denied")

    @staticmethod
    def _bounded_params(params: object) -> bool:
        if not isinstance(params, dict):
            return False
        try:
            encoded = json.dumps(params, ensure_ascii=False, default=str).encode("utf-8")
        except Exception:
            return False
        return len(encoded) <= MAX_AGENT_PARAM_BYTES

    def _validated_public_url(self, raw_url: str) -> str:
        value = str(raw_url or "").strip()
        if not value or len(value) > MAX_URL_CHARS or any(ord(ch) < 32 for ch in value):
            raise ValueError("web_url_invalid")
        parsed = urlsplit(value)
        host = str(parsed.hostname or "").lower().rstrip(".")
        if (
            parsed.scheme.lower() != "https"
            or not host
            or parsed.username is not None
            or parsed.password is not None
            or parsed.port not in {None, 443}
            or parsed.fragment
            or host not in self._allowed_web_hosts
        ):
            raise ValueError("web_url_not_allowlisted_https")
        if host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
            raise ValueError("web_url_private_host_denied")
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            address = None
        if address is not None and (
            address.is_private
            or address.is_loopback
            or address.is_link_local
            or address.is_multicast
            or address.is_reserved
            or address.is_unspecified
        ):
            raise ValueError("web_url_private_host_denied")
        return value

    # ------------------------------------------------------------------
    # Logging helpers
    # ------------------------------------------------------------------
    def _append_jsonl(self, path: Path, data: dict) -> None:
        try:
            target = Path(path).resolve(strict=False)
            state_root = STATE_DIR.resolve(strict=False)
            if not (target == state_root or target.is_relative_to(state_root)):
                raise ValueError("audit_path_outside_fixed_state_root")
            encoded = json.dumps(data, default=str, ensure_ascii=False)
            if len(encoded.encode("utf-8")) > 4096:
                encoded = json.dumps(
                    {"ts": data.get("ts"), "error": "audit_entry_too_large"}
                )
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("a", encoding="utf-8") as fh:
                fh.write(encoded + "\n")
        except Exception as exc:
            logger.warning("Failed to write to %s: %s", path, exc)

    def log_action(self, action: str, result: dict, duration: float = 0.0) -> None:
        """Persist outcome metadata only; never copy tool-returned plaintext."""

        entry = {
            "ts": datetime.datetime.utcnow().isoformat(),
            "action": action,
            "result_ok": result.get("success", False),
            "duration_s": round(duration, 4),
            "status": str(result.get("status", "unknown"))[:48],
            "effect": str(result.get("effect", "none"))[:96],
        }
        self._append_jsonl(ACTION_LOG_PATH, entry)

    def _publish_search_capture(self, phase: str, **payload: Any) -> dict:
        """Keep implicit search-fabric persistence disabled by default."""

        del phase, payload
        return {}

    # ===================================================================
    #  1. SHELL EXECUTION
    # ===================================================================
    def execute_shell(self, command: str, timeout: int = 30, cwd: str = None,
                      force: bool = False) -> dict:
        """Remain on HOLD until an argv-bound Plumber capability exists."""

        del command, timeout, cwd, force
        return _effect_hold("process.execute", "argv_magic_star_capability_unavailable")

    # ===================================================================
    #  2. APP LAUNCHER
    # ===================================================================
    def open_app(self, app_name: str) -> dict:
        """Application launch requires an exact argv-bound capability."""

        del app_name
        return _effect_hold("process.launch", "argv_magic_star_capability_unavailable")

    def close_app(self, app_name: str) -> dict:
        del app_name
        return _effect_hold("process.terminate", "process_termination_capability_unavailable")

    def kill_process(self, name_or_pid: str) -> dict:
        del name_or_pid
        return _effect_hold("process.terminate", "process_termination_capability_unavailable")

    def list_running_apps(self) -> list:
        """Return a bounded read-only process snapshot through psutil."""

        return self.running_processes(top_n=50)

    def focus_window(self, title_pattern: str) -> dict:
        del title_pattern
        return _effect_hold("window.focus", "governed_window_capability_required")

    # ===================================================================
    #  3. WEB SEARCH & BROWSING
    # ===================================================================
    def web_search(self, query: str, num_results: int = 5) -> list:
        """Return bounded curated sources without performing a network request."""

        bounded_query = str(query or "").strip()[:1024]
        bounded_count = max(1, min(int(num_results or 5), 10))
        return self._official_learning_search_fallback(bounded_query, bounded_count)

    def _official_learning_search_fallback(self, query: str, num_results: int = 5) -> list:
        """Return curated official learning sources when public search blocks bots."""

        catalog = [
            ("python", "Python documentation", "https://docs.python.org/3/", "Official Python language and standard library documentation."),
            ("ast", "Python ast documentation", "https://docs.python.org/3/library/ast.html", "Official AST module reference for safe code analysis."),
            ("pytest", "pytest documentation", "https://docs.pytest.org/", "Official pytest guide for fixtures, assertions, and test structure."),
            ("typescript", "TypeScript documentation", "https://www.typescriptlang.org/docs/", "Official TypeScript handbook and language reference."),
            ("react", "React documentation", "https://react.dev/learn", "Official React learning docs for components and state."),
            ("vite", "Vite documentation", "https://vite.dev/guide/", "Official Vite guide for frontend builds."),
            ("owasp", "OWASP ASVS", "https://owasp.org/www-project-application-security-verification-standard/", "Official OWASP application security verification standard."),
            ("binance", "Binance API documentation", "https://developers.binance.com/docs", "Official Binance developer documentation."),
            ("kraken", "Kraken API documentation", "https://docs.kraken.com/api/", "Official Kraken API documentation."),
            ("alpaca", "Alpaca API documentation", "https://docs.alpaca.markets/", "Official Alpaca API documentation."),
            ("github", "GitHub REST API documentation", "https://docs.github.com/en/rest", "Official GitHub REST API documentation."),
            ("pypi", "PyPI JSON API", "https://warehouse.pypa.io/api-reference/json.html", "Official Warehouse/PyPI JSON API reference."),
        ]
        words = {word for word in re.findall(r"[a-z0-9]+", (query or "").lower()) if len(word) >= 3}
        ranked: list[tuple[int, dict]] = []
        for key, title, url, snippet in catalog:
            haystack = f"{key} {title} {snippet}".lower()
            score = sum(1 for word in words if word in haystack)
            if score:
                ranked.append((score, {"title": title, "snippet": snippet, "url": url, "source": "official_fallback"}))
        if not ranked:
            ranked = [
                (1, {"title": title, "snippet": snippet, "url": url, "source": "official_fallback"})
                for key, title, url, snippet in catalog
            ]
        ranked.sort(key=lambda item: (-item[0], item[1]["title"]))
        return [item for _score, item in ranked[: max(1, min(int(num_results or 5), 10))]]

    def web_fetch(self, url: str) -> dict:
        """Use an injected reader that pins DNS and reports its public peer IP."""

        url_errors = {
            "web_url_invalid",
            "web_url_not_allowlisted_https",
            "web_url_private_host_denied",
        }
        response_errors = {
            "web_reader_response_invalid",
            "web_redirect_denied",
            "web_reader_peer_ip_required",
            "web_reader_peer_ip_invalid",
            "web_reader_private_peer_denied",
            "web_response_text_invalid",
            "web_response_status_invalid",
        }
        reader = self._web_reader
        if not callable(reader):
            return {
                "success": False,
                "status": "hold",
                "error": "injected_allowlisted_web_reader_required",
            }
        try:
            validated = self._validated_public_url(url)
        except Exception as exc:
            code = str(exc)
            return {
                "success": False,
                "error": code if code in url_errors else "web_url_invalid",
            }
        try:
            observed = reader(validated)
        except Exception:
            return {"success": False, "error": "web_reader_failed"}
        try:
            if not isinstance(observed, Mapping):
                raise ValueError("web_reader_response_invalid")
            final_url = str(observed.get("final_url") or validated)
            if final_url != validated or observed.get("redirected") is True:
                raise ValueError("web_redirect_denied")
            peer_ip_text = observed.get("peer_ip")
            if not isinstance(peer_ip_text, str):
                raise ValueError("web_reader_peer_ip_required")
            try:
                peer_ip = ipaddress.ip_address(peer_ip_text)
            except ValueError as exc:
                raise ValueError("web_reader_peer_ip_invalid") from exc
            if not peer_ip.is_global:
                raise ValueError("web_reader_private_peer_denied")
            text = observed.get("text")
            status_code = observed.get("status_code")
            if not isinstance(text, str) or len(text.encode("utf-8")) > MAX_READ_BYTES:
                raise ValueError("web_response_text_invalid")
            if not isinstance(status_code, int) or not 100 <= status_code <= 599:
                raise ValueError("web_response_status_invalid")
            return {
                "success": True,
                "url": validated,
                "status_code": status_code,
                "text": text[:MAX_WEB_TEXT_CHARS],
            }
        except Exception as exc:
            code = str(exc)
            return {
                "success": False,
                "error": code if code in response_errors else "web_reader_response_invalid",
            }

    def open_url(self, url: str) -> dict:
        del url
        return _effect_hold("browser.open", "governed_browser_capability_unavailable")

    # ===================================================================
    #  4. FILE SYSTEM
    # ===================================================================
    def list_dir(self, path: str = ".") -> list:
        """List a bounded directory inside an allowlisted workspace root."""

        entries: list[dict] = []
        try:
            p = self._resolve_workspace_path(path, must_exist=True)
            if not p.is_dir():
                return [{"error": "workspace_path_not_directory"}]
            for item in sorted(p.iterdir(), key=lambda entry: entry.name):
                if len(entries) >= MAX_DIRECTORY_ENTRIES:
                    break
                try:
                    safe_item = self._resolve_workspace_path(item, must_exist=True)
                    stat = safe_item.stat()
                    entries.append({
                        "name": item.name,
                        "type": "dir" if safe_item.is_dir() else "file",
                        "size": stat.st_size,
                        "modified": datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    })
                except ValueError:
                    continue
                except PermissionError:
                    entries.append({"name": item.name, "type": "unknown", "error": "permission denied"})
        except (OSError, ValueError) as exc:
            return [{"error": str(exc)}]
        return entries

    def read_file(self, path: str, max_lines: int = 200) -> str:
        """Read bounded UTF-8 text from an allowlisted workspace root."""

        try:
            p = self._resolve_workspace_path(path, must_exist=True)
            if not p.is_file():
                return "ERROR: workspace_path_not_file"
            if p.stat().st_size > MAX_READ_BYTES:
                return "ERROR: workspace_file_too_large"
            limit = max(1, min(int(max_lines), MAX_READ_LINES))
            lines = p.read_bytes().decode("utf-8", errors="replace").splitlines()
            return "\n".join(lines[:limit])
        except Exception as exc:
            return f"ERROR: {exc}"

    def open_file(self, path: str) -> dict:
        del path
        return _effect_hold("file.open", "governed_file_open_capability_unavailable")

    def write_file(self, path: str, content: str, backup: bool = True) -> dict:
        del path, content, backup
        return _effect_hold("file.write")

    def find_files(self, directory: str, pattern: str) -> list:
        """Find a bounded number of files inside an allowlisted root."""

        try:
            base = self._resolve_workspace_path(directory, must_exist=True)
            candidate_pattern = str(pattern or "")
            if (
                not candidate_pattern
                or len(candidate_pattern) > MAX_GLOB_CHARS
                or ".." in candidate_pattern.replace("\\", "/").split("/")
                or Path(candidate_pattern).is_absolute()
            ):
                raise ValueError("workspace_glob_invalid")
            matches = []
            for item in base.rglob(candidate_pattern):
                try:
                    resolved = self._resolve_workspace_path(item, must_exist=True)
                except (OSError, ValueError):
                    continue
                matches.append(str(resolved))
                if len(matches) >= MAX_DIRECTORY_ENTRIES:
                    break
            return matches
        except Exception as exc:
            return [f"ERROR: {exc}"]

    def keyword_search_files(
        self,
        keyword: str,
        scope: str = "tests",
        max_results: int = 40,
        require_all_terms: bool = False,
    ) -> dict:
        """Read local text/test files and return keyword match snippets."""
        if (
            not isinstance(keyword, str)
            or not keyword.strip()
            or len(keyword.encode("utf-8")) > 4096
            or scope not in {"tests", "aureon", "scripts", "frontend", "all"}
        ):
            return {"success": False, "error": "bounded_keyword_scope_required"}
        max_results = max(1, min(int(max_results), 100))
        start_event = self._publish_search_capture(
            "keyword_scan_requested",
            query=keyword,
            source="local_keyword_search",
            metadata={
                "scope": scope,
                "max_results": max_results,
                "require_all_terms": require_all_terms,
            },
        )
        trace_id = start_event.get("trace_id")
        query_id = start_event.get("query_id")
        try:
            from aureon.search.local_keyword_search import run_keyword_search

            result = run_keyword_search(
                keyword=keyword,
                scope=scope,
                max_results=max_results,
                require_all_terms=require_all_terms,
                repo_root=self.repo_root,
                # AgentCore exposes this as an observation tool.  The search
                # helper defaults to writing state/public artifacts, so the
                # no-write mode must be explicit here.
                write_artifact=False,
            )
            summary = result.get("summary", {}) if isinstance(result, dict) else {}
            scanned = int(summary.get("scanned_file_count") or 0)
            matches = int(summary.get("match_count") or 0)
            matched_files = int(summary.get("matched_file_count") or 0)
            self._publish_search_capture(
                "keyword_file_read",
                query=keyword,
                trace_id=trace_id,
                query_id=query_id,
                source="local_keyword_search",
                result_count=scanned,
                status="success",
                metadata={"scope": scope, "scanned_file_count": scanned},
            )
            self._publish_search_capture(
                "keyword_match_captured",
                query=keyword,
                trace_id=trace_id,
                query_id=query_id,
                source="local_keyword_search",
                result_count=matches,
                status="success" if matches else "no_matches",
                metadata={
                    "scope": scope,
                    "matched_file_count": matched_files,
                    "sample_paths": result.get("matched_paths", [])[:12] if isinstance(result, dict) else [],
                },
            )
            self._publish_search_capture(
                "keyword_scan_completed",
                query=keyword,
                trace_id=trace_id,
                query_id=query_id,
                source="local_keyword_search",
                result_count=matches,
                status=str(result.get("status") or "success") if isinstance(result, dict) else "success",
                metadata={"scope": scope, "matched_file_count": matched_files},
            )
            return result
        except Exception as exc:
            self._publish_search_capture(
                "keyword_scan_failed",
                query=keyword,
                trace_id=trace_id,
                query_id=query_id,
                source="local_keyword_search",
                status="error",
                error=str(exc),
                metadata={"scope": scope},
            )
            return {"success": False, "error": str(exc), "keyword": keyword, "scope": scope}

    def online_research_cinema(
        self,
        topic: str,
        query: str = "",
        urls: Optional[List[str]] = None,
        max_sources: int = 5,
    ) -> dict:
        """Hold network-plus-file generation until a released workflow exists."""

        del topic, query, urls, max_sources
        return _effect_hold("research.generate", "research_release_capability_unavailable")

    def research_metacognition(
        self,
        topic: str = "",
        manifest_path: str = "frontend/public/aureon_online_research_cinema.json",
    ) -> dict:
        del topic, manifest_path
        return _effect_hold("research.metacognition", "research_release_capability_unavailable")

    def file_info(self, path: str) -> dict:
        """Get metadata for a file or directory."""
        try:
            p = self._resolve_workspace_path(path, must_exist=True)
            stat = p.stat()
            return {
                "path": str(p),
                "type": "dir" if p.is_dir() else "file",
                "size": stat.st_size,
                "modified": datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "created": datetime.datetime.fromtimestamp(stat.st_ctime).isoformat(),
            }
        except Exception as exc:
            return {"error": str(exc)}

    def copy_file(self, src: str, dst: str) -> dict:
        del src, dst
        return _effect_hold("file.copy")

    def move_file(self, src: str, dst: str) -> dict:
        del src, dst
        return _effect_hold("file.move")

    def delete_file(self, path: str, confirm: bool = False) -> dict:
        del path, confirm
        return _effect_hold("file.delete")

    def create_dir(self, path: str) -> dict:
        del path
        return _effect_hold("directory.create")

    # ===================================================================
    #  5. CODE EXECUTION (fail-closed until a governed sandbox is released)
    # ===================================================================
    def execute_python(self, code: str) -> dict:
        del code
        return _effect_hold("code.execute", "dynamic_code_execution_disabled")

    def create_script(self, path: str, code: str) -> dict:
        del path, code
        return _effect_hold("code.create", "dynamic_code_creation_disabled")

    def run_script(self, path: str) -> dict:
        del path
        return _effect_hold("code.execute", "dynamic_code_execution_disabled")

    # ===================================================================
    #  6. DESKTOP CONTROL (wire SafeDesktopControl)
    # ===================================================================
    def _desktop_exec(self, action: str, params: dict) -> dict:
        del action, params
        return _effect_hold(
            "desktop.input",
            "production_magic_star_desktop_release_unavailable",
        )

    def click(self, x: int, y: int, target_binding_id: str | None = None) -> dict:
        p: Dict[str, Any] = {"x": int(x), "y": int(y)}
        if target_binding_id:
            p["target_binding_id"] = target_binding_id
        return self._desktop_exec("left_click", p)

    def move_mouse(self, x: int, y: int, duration: float = 0.0, target_binding_id: str | None = None) -> dict:
        p: Dict[str, Any] = {"x": int(x), "y": int(y), "duration": duration}
        if target_binding_id:
            p["target_binding_id"] = target_binding_id
        return self._desktop_exec("move_mouse", p)

    def right_click(self, x: int, y: int, target_binding_id: str | None = None) -> dict:
        p: Dict[str, Any] = {"x": int(x), "y": int(y)}
        if target_binding_id:
            p["target_binding_id"] = target_binding_id
        return self._desktop_exec("right_click", p)

    def double_click(self, x: int, y: int, target_binding_id: str | None = None) -> dict:
        p: Dict[str, Any] = {"x": int(x), "y": int(y)}
        if target_binding_id:
            p["target_binding_id"] = target_binding_id
        return self._desktop_exec("double_click", p)

    def type_text(self, text: str, interval: float = 0.02, target_binding_id: str | None = None) -> dict:
        p: Dict[str, Any] = {"text": text, "interval": interval}
        if target_binding_id:
            p["target_binding_id"] = target_binding_id
        return self._desktop_exec("type_text", p)

    def press_key(self, key: str, target_binding_id: str | None = None) -> dict:
        p: Dict[str, Any] = {"key": key}
        if target_binding_id:
            p["target_binding_id"] = target_binding_id
        return self._desktop_exec("press_key", p)

    def hotkey(
        self,
        keys: List[str] | str | None = None,
        *more_keys: str,
        target_binding_id: str | None = None,
    ) -> dict:
        # Support both styles:
        # - hotkey(keys=["ctrl", "c"])
        # - hotkey("ctrl", "c")
        all_keys: List[str] = []
        if isinstance(keys, list):
            all_keys.extend([str(k) for k in keys if k])
        elif keys:
            all_keys.append(str(keys))
        all_keys.extend([str(k) for k in more_keys if k])
        p: Dict[str, Any] = {"keys": all_keys}
        if target_binding_id:
            p["target_binding_id"] = target_binding_id
        return self._desktop_exec("hotkey", p)

    def scroll(self, x: int, y: int, amount: int, target_binding_id: str | None = None) -> dict:
        p: Dict[str, Any] = {"x": int(x), "y": int(y), "amount": int(amount)}
        if target_binding_id:
            p["target_binding_id"] = target_binding_id
        return self._desktop_exec("scroll", p)

    def screenshot(self) -> dict:
        """Observe the screen through the same evidence-producing gateway."""
        dc = self._get_desktop()
        if dc is None:
            return {"success": False, "error": "GovernedDesktopGateway not available"}
        try:
            res = dc.observe()
            self._publish_search_capture(
                "screen_observed" if res.ok else "screen_capture_failed",
                source="governed_desktop_gateway",
                status="success" if res.ok else "error",
                result_count=1 if res.ok else 0,
                metadata={
                    "before_sha256": res.before_sha256,
                    "action_id": res.action_id,
                    "data_capture_mode": "in_memory_evidence_hash",
                },
            )
            return {"success": res.ok, **res.to_dict()}
        except Exception as exc:
            self._publish_search_capture(
                "screen_capture_failed",
                source="governed_desktop_gateway",
                status="error",
                error=str(exc),
            )
            return {"success": False, "error": str(exc)}

    def desktop_status(self) -> dict:
        dc = self._get_desktop()
        if dc is None:
            return {"success": False, "error": "GovernedDesktopGateway not available"}
        try:
            return {"success": True, "result": dc.status()}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def desktop_arm_live(
        self,
        capability_token: str,
        ttl_seconds: float,
        subject: str,
        allowed_actions: List[str] | None = None,
    ) -> dict:
        del capability_token, ttl_seconds, subject, allowed_actions
        return _effect_hold(
            "desktop.arm_live",
            "production_magic_star_desktop_release_unavailable",
        )

    def desktop_arm_dry_run(self) -> dict:
        dc = self._get_desktop()
        if dc is None:
            return {"success": False, "error": "GovernedDesktopGateway not available"}
        try:
            dc.disarm(reason="agent_core_dry_run")
            return {"success": True, "result": dc.status()}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def desktop_bind_window(self, expected_title: str, expected_process_id: int | None = None) -> dict:
        dc = self._get_desktop()
        if dc is None:
            return {"success": False, "error": "GovernedDesktopGateway not available"}
        try:
            binding = dc.bind_target_window(
                expected_title,
                expected_process_id=expected_process_id,
            )
            return {"success": True, "result": binding.audit_dict(), "binding_id": binding.binding_id}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def desktop_disarm(self) -> dict:
        dc = self._get_desktop()
        if dc is None:
            return {"success": False, "error": "GovernedDesktopGateway not available"}
        try:
            dc.disarm(reason="agent_core_disarm")
            return {"success": True, "result": dc.status()}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def desktop_emergency_stop(self) -> dict:
        dc = self._get_desktop()
        if dc is None:
            return {"success": False, "error": "GovernedDesktopGateway not available"}
        try:
            dc.emergency_stop(reason="agent_core_emergency_stop")
            return {"success": True, "result": dc.status()}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def desktop_clear_emergency_stop(self) -> dict:
        dc = self._get_desktop()
        if dc is None:
            return {"success": False, "error": "GovernedDesktopGateway not available"}
        try:
            dc.clear_emergency_stop(reason="agent_core_clear_emergency_stop")
            return {"success": True, "result": dc.status()}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    # ===================================================================
    #  7. SYSTEM INFO
    # ===================================================================
    def system_info(self) -> dict:
        """Get CPU, RAM, disk usage, OS info."""
        info: dict = {
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python": sys.version,
            "hostname": socket.gethostname(),
        }
        if HAS_PSUTIL:
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage("/") if sys.platform != "win32" else psutil.disk_usage("C:\\")
            info.update({
                "cpu_count": psutil.cpu_count(),
                "cpu_percent": psutil.cpu_percent(interval=0.5),
                "ram_total_gb": round(mem.total / (1024 ** 3), 2),
                "ram_used_gb": round(mem.used / (1024 ** 3), 2),
                "ram_percent": mem.percent,
                "disk_total_gb": round(disk.total / (1024 ** 3), 2),
                "disk_used_gb": round(disk.used / (1024 ** 3), 2),
                "disk_percent": disk.percent,
            })
        return info

    def running_processes(self, top_n: int = 20) -> list:
        """Top processes by memory usage."""
        if not HAS_PSUTIL:
            return [{"error": "psutil not installed"}]
        procs: list[dict] = []
        for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
            try:
                procs.append(p.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        procs.sort(key=lambda x: x.get("memory_percent") or 0, reverse=True)
        return procs[:top_n]

    def network_status(self) -> dict:
        """Return local interface metadata without an outbound connectivity probe."""

        info: dict = {
            "connected": None,
            "connectivity_probe": "disabled_offline",
            "interfaces": {},
        }
        if HAS_PSUTIL:
            addrs = psutil.net_if_addrs()
            for iface, addr_list in addrs.items():
                info["interfaces"][iface] = [
                    {"family": str(a.family), "address": a.address}
                    for a in addr_list
                ]
        return info

    # ===================================================================
    #  8. KNOWLEDGE QUERY (wire global_history_db)
    # ===================================================================
    def query_knowledge(self, sql: str) -> list:
        """Run SQL against the unified knowledge DB (read-only by default)."""
        conn = self._get_db()
        if conn is None:
            return [{"error": "Knowledge DB not available"}]
        sql_text = (sql or "").strip()
        if not sql_text or len(sql_text.encode("utf-8")) > MAX_SQL_CHARS:
            return [{"error": "SQL is empty"}]
        lower = sql_text.lower()
        if not lower.startswith(("select", "with")):
            return [{"error": "Blocked non-read-only SQL. Only SELECT/WITH is allowed."}]
        block_keywords = (
            "insert",
            "update",
            "delete",
            "drop",
            "alter",
            "create",
            "replace",
            "vacuum",
            "attach",
            "detach",
            "reindex",
            "pragma",
            "load_extension",
        )
        for kw in block_keywords:
            if re.search(rf"(?<![a-z0-9_]){kw}(?![a-z0-9_])", lower):
                return [{"error": f"Blocked keyword in SQL: {kw}."}]
        try:
            cursor = conn.execute(sql_text)
            cols = [d[0] for d in cursor.description] if cursor.description else []
            return [dict(zip(cols, row)) for row in cursor.fetchall()]
        except Exception as exc:
            return [{"error": str(exc)}]

    def search_knowledge(self, keyword: str) -> dict:
        """Search across all knowledge tables for a keyword."""
        start_event = self._publish_search_capture(
            "knowledge_search_requested",
            query=keyword,
            source="global_history_db",
        )
        trace_id = start_event.get("trace_id")
        query_id = start_event.get("query_id")
        conn = self._get_db()
        if conn is None:
            self._publish_search_capture(
                "knowledge_search_failed",
                query=keyword,
                trace_id=trace_id,
                query_id=query_id,
                source="global_history_db",
                status="db_unavailable",
                error="Knowledge DB not available",
            )
            return {"error": "Knowledge DB not available"}
        results: dict = {}
        try:
            tables = [r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()]
            for table in tables:
                cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
                text_cols = [c for c in cols if c.lower() not in ("id", "ts", "timestamp")]
                for col in text_cols[:3]:
                    try:
                        rows = conn.execute(
                            f"SELECT * FROM {table} WHERE CAST({col} AS TEXT) LIKE ? LIMIT 5",
                            (f"%{keyword}%",),
                        ).fetchall()
                        if rows:
                            col_names = [d[0] for d in conn.execute(
                                f"SELECT * FROM {table} LIMIT 0"
                            ).description]
                            results[f"{table}.{col}"] = [
                                dict(zip(col_names, r)) for r in rows
                            ]
                    except Exception:
                        pass
        except Exception as exc:
            self._publish_search_capture(
                "knowledge_search_failed",
                query=keyword,
                trace_id=trace_id,
                query_id=query_id,
                source="global_history_db",
                status="error",
                error=str(exc),
            )
            return {"error": str(exc)}
        self._publish_search_capture(
            "knowledge_search_completed",
            query=keyword,
            trace_id=trace_id,
            query_id=query_id,
            source="global_history_db",
            result_count=sum(len(v) for v in results.values() if isinstance(v, list)),
            status="success",
            metadata={"matched_tables": len(results)},
        )
        return results

    def get_market_summary(self) -> dict:
        """Current market state from the DB."""
        conn = self._get_db()
        if conn is None:
            return {"error": "Knowledge DB not available"}
        summary: dict = {}
        try:
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM market_bars"
            ).fetchone()
            summary["total_bars"] = row[0] if row else 0
        except Exception:
            summary["total_bars"] = "table not found"
        try:
            rows = conn.execute(
                "SELECT provider, symbol, close, volume, time_start_ms "
                "FROM market_bars ORDER BY time_start_ms DESC LIMIT 10"
            ).fetchall()
            summary["latest_bars"] = [
                {"provider": r[0], "symbol": r[1], "close": r[2], "volume": r[3], "time_start_ms": r[4]}
                for r in rows
            ]
        except Exception:
            summary["latest_bars"] = []
        return summary

    def get_portfolio_summary(self) -> dict:
        """Current portfolio state from account_trades."""
        conn = self._get_db()
        if conn is None:
            return {"error": "Knowledge DB not available"}
        summary: dict = {}
        try:
            rows = conn.execute(
                "SELECT venue, symbol, side, qty, price, ts_ms "
                "FROM account_trades ORDER BY ts_ms DESC LIMIT 20"
            ).fetchall()
            summary["recent_trades"] = [
                {"venue": r[0], "symbol": r[1], "side": r[2],
                 "qty": r[3], "price": r[4], "ts_ms": r[5]}
                for r in rows
            ]
        except Exception:
            summary["recent_trades"] = []
        return summary

    # ===================================================================
    #  9. TRADING (wire exchange clients)
    # ===================================================================
    def _load_exchange_client(self, venue: str):
        """Compatibility shim: raw provider clients are never constructed."""

        del venue
        return None

    def _read_account_observation(
        self,
        observation: str,
        venue: str,
        params: Optional[Mapping[str, Any]] = None,
    ) -> Any:
        reader = self._account_reader
        normalized_venue = str(venue or "").strip().lower()
        if normalized_venue not in {"binance", "alpaca", "capital", "kraken"}:
            return {"error": "account_observation_venue_invalid"}
        if not callable(reader):
            return {
                "data_status": "no_data",
                "error": "injected_account_reader_required",
                "venue": normalized_venue,
            }
        try:
            return reader(observation, normalized_venue, dict(params or {}))
        except Exception as exc:
            return {
                "data_status": "no_data",
                "error": f"account_reader_failed:{type(exc).__name__}",
                "venue": normalized_venue,
            }

    def get_balances(self, venue: str = "all") -> dict:
        """Get account balances."""
        if venue == "all":
            return {
                item: self._read_account_observation("balances", item)
                for item in ("binance", "alpaca", "capital", "kraken")
            }
        return self._read_account_observation("balances", venue)

    def place_order(self, venue: str, symbol: str, side: str, qty: float,
                    order_type: str = "market") -> dict:
        """Claim one exact-plan Magic-Star authority at the injected dispatcher."""

        authorization_provider = self._trade_authorization_provider
        dispatcher = self._final_trade_dispatcher
        if not callable(authorization_provider) or not callable(dispatcher):
            return _effect_hold("trade.order")
        try:
            from aureon.queen.queen_force_trade_governance import (
                ForceTradePlan,
                claim_queen_force_trade_authority,
            )

            if str(order_type or "").strip().lower() != "market":
                return _effect_hold("trade.order", "market_order_only")
            plan = ForceTradePlan(
                provider=venue,
                symbol=symbol,
                side=side,
                quantity=str(qty),
                quantity_kind="base_units",
                order_type="market",
            )
            authorization = authorization_provider(plan)
            decision = claim_queen_force_trade_authority(
                plan=plan,
                authorization=authorization,
            )
            if not decision.allowed:
                reason = (
                    decision.missing_requirements[0]
                    if decision.missing_requirements
                    else "trade_authorization_denied"
                )
                return _effect_hold("trade.order", reason)
        except Exception as exc:
            return _effect_hold(
                "trade.order",
                f"trade_authorization_invalid:{type(exc).__name__}",
            )

        # The atomic claim above is the final pre-dispatch step. Once invoked,
        # a handler may already have produced provider-side effects; failures
        # are indeterminate and the one-use authority remains consumed.
        try:
            receipt = dispatcher(plan)
            if not isinstance(receipt, Mapping):
                return {
                    "success": False,
                    "status": "pending_reconciliation",
                    "submitted": None,
                    "error": "ambiguous_authorized_trade_receipt",
                }
            # A dispatch callback cannot independently attest its own provider
            # effect.  Keep the outcome unresolved until a separate provider
            # read-back reconciles the exact plan.
            return {
                "success": False,
                "status": "pending_reconciliation",
                "submitted": None,
                "error": "independent_provider_readback_required",
                "plan_sha256": plan.commitment,
                "authorization_consumed": True,
                "dispatcher_acknowledgement_untrusted": True,
                "eligible_for_accounting": False,
                "eligible_for_learning": False,
            }
        except Exception as exc:
            return {
                "success": False,
                "status": "pending_reconciliation",
                "submitted": None,
                "error": f"ambiguous_authorized_trade_dispatch:{type(exc).__name__}",
            }

    def get_positions(self, venue: str = "all") -> dict:
        """Get open positions."""
        if venue == "all":
            return {
                item: self._read_account_observation("positions", item)
                for item in ("binance", "alpaca", "capital", "kraken")
            }
        return self._read_account_observation("positions", venue)

    def get_recent_trades(self, venue: str = "all", limit: int = 10) -> list:
        """Get recent trades from exchange clients."""
        bounded_limit = max(1, min(int(limit), 100))
        if venue == "all":
            return [
                {
                    "venue": item,
                    "observation": self._read_account_observation(
                        "recent_trades",
                        item,
                        {"limit": bounded_limit},
                    ),
                }
                for item in ("binance", "alpaca", "capital", "kraken")
            ]
        observed = self._read_account_observation(
            "recent_trades",
            venue,
            {"limit": bounded_limit},
        )
        return observed if isinstance(observed, list) else [observed]

    # ===================================================================
    #  10. COMMUNICATION
    # ===================================================================
    def speak(self, text: str, priority: int = 3) -> dict:
        del text, priority
        return _effect_hold("audio.speak", "governed_tts_capability_unavailable")

    def notify(self, title: str, message: str) -> dict:
        del title, message
        return _effect_hold("user.notify", "governed_notification_capability_unavailable")

    def think(self, message: str, topic: str = "agent.action") -> dict:
        """Hold publication until a released persistence capability exists."""

        del message, topic
        return _effect_hold("thought.publish", "thought_bus_release_capability_unavailable")

    # ===================================================================
    #  MASTER EXECUTE
    # ===================================================================
    def execute(self, intent: str, params: dict = None) -> dict:
        """
        Execute any task by intent name.

        Routes to the correct tool based on the intent string.
        Returns: {"success": bool, "result": any, "tool_used": str, "error": str}
        """
        if not isinstance(intent, str) or not intent or len(intent) > 128:
            return {
                "success": False,
                "result": None,
                "tool_used": None,
                "error": "intent_invalid",
            }
        params = params or {}
        if not self._bounded_params(params):
            return {
                "success": False,
                "result": None,
                "tool_used": None,
                "error": "bounded_object_params_required",
            }
        # The gate is a mandatory invariant, not an opt-in feature.  A missing or
        # broken gate fails closed instead of silently restoring sovereign access.
        try:
            from aureon.operator.grounded_action import get_action_gate

            _verdict = get_action_gate().ground(intent, params if isinstance(params, dict) else {})
            if not _verdict.approved:
                return {"success": False, "result": None, "tool_used": None,
                        "error": f"grounded-action gate {_verdict.verdict}: {_verdict.reason}"}
        except Exception as exc:  # noqa: BLE001
            return {"success": False, "result": None, "tool_used": None,
                    "error": f"grounded-action gate unavailable: {exc}"}
        method_name = INTENT_MAP.get(intent)

        if method_name is None:
            return {
                "success": False,
                "result": None,
                "tool_used": None,
                "error": f"Unknown intent: '{intent}'. Use get_capabilities() to list options.",
            }
        method = getattr(self, method_name, None)
        if method is None:
            return {
                "success": False,
                "result": None,
                "tool_used": method_name,
                "error": f"Method '{method_name}' not implemented.",
            }

        self._stats["calls"] += 1
        t0 = time.time()
        try:
            result = method(**params)
            duration = time.time() - t0
            success = True
            if isinstance(result, dict):
                success = result.get("success", True)
                if "error" in result and result["error"]:
                    success = False
            self._stats["success" if success else "failure"] += 1
            out = {
                "success": success,
                "result": result,
                "tool_used": method_name,
                "error": None,
            }
        except Exception as exc:
            duration = time.time() - t0
            self._stats["failure"] += 1
            out = {
                "success": False,
                "result": None,
                "tool_used": method_name,
                "error": str(exc),
            }

        self.log_action(intent, out, duration)
        return out

    # ===================================================================
    #  CAPABILITIES
    # ===================================================================
    def get_capabilities(self) -> list:
        """Return list of all available intents with descriptions."""
        descs = {
            "shell": "HOLD: exact argv Magic-Star capability unavailable",
            "open_app": "HOLD: governed process launch unavailable",
            "close_app": "HOLD: governed process termination unavailable",
            "list_apps": "List running applications",
            "focus_window": "HOLD: governed window-focus capability unavailable",
            "web_search": "Search curated offline documentation links",
            "web_fetch": "Fetch through an injected exact-host HTTPS reader",
            "open_url": "HOLD: governed browser capability unavailable",
            "list_dir": "List bounded allowlisted workspace contents",
            "read_file": "Read a bounded allowlisted workspace file",
            "open_file": "HOLD: governed file-open capability unavailable",
            "write_file": "HOLD: Plumber file-write release unavailable",
            "find_files": "Find files by glob pattern",
            "keyword_search": "Read local text/test files and find keyword snippets",
            "online_research_cinema": "HOLD: network-plus-file research release unavailable",
            "research_metacognition": "HOLD: research persistence release unavailable",
            "file_info": "Get file metadata",
            "copy_file": "HOLD: Plumber file-copy release unavailable",
            "move_file": "HOLD: Plumber file-move release unavailable",
            "delete_file": "HOLD: Plumber file-delete release unavailable",
            "create_dir": "HOLD: Plumber directory release unavailable",
            "execute_python": "HOLD: dynamic code execution disabled",
            "create_script": "HOLD: dynamic code creation disabled",
            "run_script": "HOLD: dynamic code execution disabled",
            "click": "HOLD: production Magic-Star desktop release unavailable",
            "move_mouse": "HOLD: production Magic-Star desktop release unavailable",
            "right_click": "HOLD: production Magic-Star desktop release unavailable",
            "double_click": "HOLD: production Magic-Star desktop release unavailable",
            "type_text": "HOLD: production Magic-Star desktop release unavailable",
            "press_key": "HOLD: production Magic-Star desktop release unavailable",
            "hotkey": "HOLD: production Magic-Star desktop release unavailable",
            "screenshot": "Take a screenshot",
            "desktop_status": "Get desktop controller status",
            "desktop_arm_live": "HOLD: production Magic-Star desktop release unavailable",
            "desktop_arm_dry_run": "Arm desktop controller (dry-run mode)",
            "desktop_disarm": "Disarm desktop controller",
            "desktop_emergency_stop": "Emergency stop desktop controller",
            "desktop_clear_emergency_stop": "Clear emergency stop and keep disarmed",
            "system_info": "Get CPU/RAM/disk/OS info",
            "processes": "List top processes",
            "network_status": "Check network connectivity",
            "kill_process": "HOLD: governed process termination unavailable",
            "query_knowledge": "Run SQL on knowledge DB",
            "search_knowledge": "Keyword search across DB",
            "market_summary": "Get latest market data",
            "portfolio": "Get portfolio / recent trades",
            "get_balances": "Get exchange balances",
            "get_positions": "Get open positions",
            "place_order": "Exact-plan one-use Magic-Star trade dispatcher",
            "get_recent_trades": "Get recent trades",
            "speak": "HOLD: governed TTS capability unavailable",
            "notify": "HOLD: governed notification capability unavailable",
            "think": "HOLD: thought persistence release unavailable",
        }
        caps = []
        for intent, desc in descs.items():
            method_name = INTENT_MAP.get(intent, "?")
            caps.append({
                "intent": intent,
                "aliases": [k for k, v in INTENT_MAP.items() if v == method_name and k != intent],
                "method": method_name,
                "description": desc,
            })
        return caps

    # ===================================================================
    #  NATURAL LANGUAGE TASK PLANNER
    # ===================================================================
    def plan_task(self, natural_language: str) -> list:
        """
        Break a natural language request into executable steps.

        Uses rule-based keyword matching and regex patterns -- no LLM call,
        so it's fast and deterministic.

        Returns list of {"intent": str, "params": dict, "description": str}
        """
        text = natural_language.strip().lower()
        steps: list[dict] = []

        # --- App launch patterns ---
        m = re.search(r"open\s+(chrome|notepad|explorer|vscode|edge|firefox|spotify|calculator|terminal|powershell|task\s*manager)", text)
        if m:
            app = m.group(1).strip()
            steps.append({"intent": "open_app", "params": {"app_name": app},
                          "description": f"Open {app}"})

        # --- Close app ---
        m = re.search(r"close\s+(chrome|notepad|explorer|vscode|edge|firefox|spotify|calculator|terminal|powershell)", text)
        if m:
            app = m.group(1).strip()
            steps.append({"intent": "close_app", "params": {"app_name": app},
                          "description": f"Close {app}"})

        local_keyword_pattern = re.search(
            r"(?:keyword\s+search|search\s+(?:tests?|text|files?)\s+for|scan\s+(?:tests?|text|files?)\s+for)\s+[\"']?(.+?)[\"']?\s*$",
            text,
        )

        # --- Web search ---
        m = re.search(r"(?:search\s+(?:for|the\s+web\s+for)?|google)\s+[\"']?(.+?)[\"']?\s*$", text)
        if m and not steps and not local_keyword_pattern:
            query = m.group(1).strip().rstrip(".")
            steps.append({"intent": "web_search", "params": {"query": query},
                          "description": f"Web search: {query}"})
        elif re.search(r"search.*for\s+(.+)", text) and not local_keyword_pattern:
            m2 = re.search(r"search.*for\s+(.+)", text)
            if m2:
                query = m2.group(1).strip().rstrip(".")
                # If we already have an open_app step, add search after
                steps.append({"intent": "web_search", "params": {"query": query},
                              "description": f"Web search: {query}"})

        # --- Open URL ---
        m = re.search(r"(?:open|go\s+to|browse|visit)\s+(https?://\S+)", text)
        if m:
            url = m.group(1)
            steps.append({"intent": "open_url", "params": {"url": url},
                          "description": f"Open URL: {url}"})

        # --- Fetch URL ---
        m = re.search(r"(?:fetch|download|get)\s+(?:the\s+)?(?:page|content|url)\s+(https?://\S+)", text)
        if m:
            steps.append({"intent": "web_fetch", "params": {"url": m.group(1)},
                          "description": f"Fetch URL: {m.group(1)}"})

        # --- Local keyword scan ---
        if local_keyword_pattern:
            keyword = local_keyword_pattern.group(1).strip().rstrip(".")
            scope = "tests" if re.search(r"tests?", text) else "."
            steps.append({"intent": "keyword_search", "params": {"keyword": keyword, "scope": scope},
                          "description": f"Local keyword search in {scope}: {keyword}"})

        # --- Online research cinema / paper ---
        m = re.search(r"(?:research\s+cinema|motion\s+paper|online\s+research\s+paper|full\s+paper)\s+(?:on|about|for)?\s*[\"']?(.+?)[\"']?\s*$", text)
        if m:
            topic = m.group(1).strip().rstrip(".")
            steps.append({"intent": "online_research_cinema", "params": {"topic": topic, "max_sources": 5},
                          "description": f"Build online research cinema and paper: {topic}"})

        # --- Research metacognition ---
        m = re.search(r"(?:understand\s+research|research\s+metacognition|metacognitive\s+research)\s+(?:on|about|for)?\s*[\"']?(.+?)[\"']?\s*$", text)
        if m:
            topic = m.group(1).strip().rstrip(".")
            steps.append({"intent": "research_metacognition", "params": {"topic": topic},
                          "description": f"Build metacognitive understanding packet: {topic}"})

        # --- Portfolio / balances ---
        if re.search(r"portfolio|holdings|my\s+positions?|what.*(?:own|hold)", text):
            steps.append({"intent": "portfolio", "params": {},
                          "description": "Get portfolio summary"})
        if re.search(r"balance|how\s+much\s+(?:money|cash|funds)", text):
            steps.append({"intent": "get_balances", "params": {},
                          "description": "Get account balances"})

        # --- Market ---
        if re.search(r"market\s+(?:summary|status|data|overview)", text):
            steps.append({"intent": "market_summary", "params": {},
                          "description": "Get market summary"})

        # --- System info ---
        if re.search(r"(?:system\s+info|cpu|ram|memory|disk\s+space|how\s+much\s+(?:disk|storage|space))", text):
            steps.append({"intent": "system_info", "params": {},
                          "description": "Get system info"})

        # --- Processes ---
        if re.search(r"(?:processes|what.*running|task\s+list|top\s+processes)", text):
            steps.append({"intent": "processes", "params": {},
                          "description": "List top processes"})

        # --- Shell command ---
        m = re.search(r"(?:run|execute|shell)\s+(?:command\s+)?[\"'`](.+?)[\"'`]", text)
        if m:
            steps.append({"intent": "shell", "params": {"command": m.group(1)},
                          "description": f"Run shell command: {m.group(1)}"})

        # --- List directory ---
        m = re.search(r"(?:list|ls|dir|show)\s+(?:files?\s+in\s+|directory\s+|folder\s+)?[\"']?([A-Za-z]:\\[^\s\"']+|/[^\s\"']+|\.)[\"']?", text)
        if m and not any(s["intent"] in ("web_search",) for s in steps):
            steps.append({"intent": "list_dir", "params": {"path": m.group(1)},
                          "description": f"List directory: {m.group(1)}"})

        # --- Read file ---
        m = re.search(r"(?:read|show|cat|view)\s+(?:file\s+)?[\"']?([A-Za-z]:\\[^\s\"']+|/[^\s\"']+)[\"']?", text)
        if m:
            steps.append({"intent": "read_file", "params": {"path": m.group(1)},
                          "description": f"Read file: {m.group(1)}"})

        # --- Screenshot ---
        if re.search(r"screenshot|screen\s*cap|capture\s+screen", text):
            steps.append({"intent": "screenshot", "params": {},
                          "description": "Take a screenshot"})

        # --- Create script ---
        if re.search(r"create\s+(?:a\s+)?(?:python\s+)?script", text):
            steps.append({"intent": "execute_python", "params": {"code": "# TODO: generate script"},
                          "description": "Create a Python script"})

        # --- Speak ---
        m = re.search(r"(?:say|speak|tell\s+me)\s+[\"'](.+?)[\"']", text)
        if m:
            steps.append({"intent": "speak", "params": {"text": m.group(1)},
                          "description": f"Speak: {m.group(1)}"})

        # --- Query knowledge ---
        m = re.search(r"(?:query|sql)\s+[\"'](.+?)[\"']", text)
        if m:
            steps.append({"intent": "query_knowledge", "params": {"sql": m.group(1)},
                          "description": f"Query DB: {m.group(1)}"})

        # --- Network ---
        if re.search(r"network|internet|connected|connectivity|wifi", text):
            steps.append({"intent": "network_status", "params": {},
                          "description": "Check network status"})

        # Deduplicate by intent
        seen: set = set()
        unique: list[dict] = []
        for s in steps:
            key = (s["intent"], json.dumps(s["params"], sort_keys=True))
            if key not in seen:
                seen.add(key)
                unique.append(s)

        if unique:
            return unique

        # Fallback: use the smart InstructionParser (200+ patterns, typo tolerance)
        parser = self._get_parser()
        if parser is not None:
            try:
                parsed = parser.parse(natural_language)
                if parsed:
                    # Convert parser output to plan_task format
                    for step in parsed:
                        method = step.get("method", "")
                        # Map laptop methods to direct intent (agent core routes via laptop)
                        intent_name = method if method else "unknown"
                        steps.append({
                            "intent": intent_name,
                            "params": step.get("params", {}),
                            "description": step.get("description", method),
                        })
                    return steps
            except Exception:
                pass

        return [{"intent": "unknown", "params": {"raw": natural_language},
                 "description": "Could not parse intent from request"}]

    # ===================================================================
    #  STATS
    # ===================================================================
    def get_stats(self) -> dict:
        return dict(self._stats)


# ═══════════════════════════════════════════════════════════════════════════
#  Interactive REPL for testing
# ═══════════════════════════════════════════════════════════════════════════
def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    agent = AureonAgentCore()
    print("=" * 60)
    print("  Aureon Agent Core -- Interactive REPL")
    print("  Type '<intent> [json_params]' or 'plan <natural language>'")
    print("  Examples:")
    print("    shell dir")
    print("    open_app chrome")
    print("    web_search \"Bitcoin price today\"")
    print("    query_knowledge \"SELECT COUNT(*) FROM market_bars\"")
    print("    plan open Chrome and search for Bitcoin price")
    print("    caps")
    print("    stats")
    print("    quit")
    print("=" * 60)

    while True:
        try:
            raw = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            break
        if not raw:
            continue
        if raw.lower() in ("quit", "exit", "q"):
            print("Bye.")
            break
        if raw.lower() == "caps":
            for cap in agent.get_capabilities():
                aliases = ", ".join(cap["aliases"]) if cap["aliases"] else ""
                print(f"  {cap['intent']:20s} {cap['description']}" +
                      (f"  (aliases: {aliases})" if aliases else ""))
            continue
        if raw.lower() == "stats":
            print(json.dumps(agent.get_stats(), indent=2))
            continue
        if raw.lower().startswith("plan "):
            steps = agent.plan_task(raw[5:])
            for i, step in enumerate(steps, 1):
                print(f"  Step {i}: [{step['intent']}] {step['description']}")
                if step["params"]:
                    print(f"          params={json.dumps(step['params'])}")
            continue

        # Parse intent and params
        parts = raw.split(None, 1)
        intent = parts[0]
        param_str = parts[1] if len(parts) > 1 else ""

        # Try to parse params as JSON
        params: dict = {}
        if param_str:
            try:
                params = json.loads(param_str)
                if not isinstance(params, dict):
                    params = {}
                    raise ValueError
            except (json.JSONDecodeError, ValueError):
                # Heuristic: map single string arg to the most likely param
                method_name = INTENT_MAP.get(intent, "")
                if method_name in ("execute_shell",):
                    params = {"command": param_str}
                elif method_name in ("open_app", "close_app"):
                    params = {"app_name": param_str}
                elif method_name in ("web_search",):
                    params = {"query": param_str.strip("\"'")}
                elif method_name in ("web_fetch",):
                    params = {"url": param_str}
                elif method_name in ("open_url",):
                    params = {"url": param_str}
                elif method_name in ("read_file",):
                    params = {"path": param_str}
                elif method_name in ("list_dir",):
                    params = {"path": param_str}
                elif method_name in ("find_files",):
                    p = param_str.split(None, 1)
                    params = {"directory": p[0], "pattern": p[1] if len(p) > 1 else "*"}
                elif method_name in ("keyword_search_files",):
                    params = {"keyword": param_str, "scope": "tests"}
                elif method_name in ("online_research_cinema",):
                    params = {"topic": param_str, "max_sources": 5}
                elif method_name in ("research_metacognition",):
                    params = {"topic": param_str}
                elif method_name in ("query_knowledge",):
                    params = {"sql": param_str.strip("\"'")}
                elif method_name in ("search_knowledge",):
                    params = {"keyword": param_str}
                elif method_name in ("speak",):
                    params = {"text": param_str}
                elif method_name in ("think",):
                    params = {"message": param_str}
                elif method_name in ("focus_window",):
                    params = {"title_pattern": param_str}
                elif method_name in ("execute_python",):
                    params = {"code": param_str}
                else:
                    params = {"command": param_str}

        result = agent.execute(intent, params)
        print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
