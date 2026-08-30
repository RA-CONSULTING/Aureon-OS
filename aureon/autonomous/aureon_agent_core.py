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
import glob as _glob
import json
import logging
import os
import platform
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import textwrap
import time
import webbrowser
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Repo root & sys.path bootstrap
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[2]
STATE_DIR = REPO_ROOT / "state"
STATE_DIR.mkdir(parents=True, exist_ok=True)

for _p in [str(REPO_ROOT), str(REPO_ROOT / "aureon"), str(REPO_ROOT / "aureon" / "core")]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

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

try:
    import requests  # type: ignore
    HAS_REQUESTS = True
except ImportError:
    requests = None  # type: ignore[assignment]
    HAS_REQUESTS = False

try:
    from bs4 import BeautifulSoup  # type: ignore
    HAS_BS4 = True
except ImportError:
    BeautifulSoup = None  # type: ignore[assignment,misc]
    HAS_BS4 = False

try:
    import pyautogui  # type: ignore
    HAS_PYAUTOGUI = True
except ImportError:
    pyautogui = None  # type: ignore[assignment]
    HAS_PYAUTOGUI = False

try:
    import ctypes
    import ctypes.wintypes
    HAS_CTYPES = True
except ImportError:
    ctypes = None  # type: ignore[assignment]
    HAS_CTYPES = False

# Wire existing subsystems --------------------------------------------------
try:
    from aureon.core.aureon_thought_bus import ThoughtBus, Thought
    HAS_THOUGHT_BUS = True
except Exception:
    ThoughtBus = None  # type: ignore[assignment,misc]
    Thought = None  # type: ignore[assignment,misc]
    HAS_THOUGHT_BUS = False

try:
    from aureon.core.aureon_global_history_db import connect as db_connect
    HAS_HISTORY_DB = True
except Exception:
    db_connect = None  # type: ignore[assignment]
    HAS_HISTORY_DB = False

try:
    from aureon.autonomous.aureon_governed_desktop_gateway import get_governed_desktop_gateway
    HAS_DESKTOP = True
except Exception:
    get_governed_desktop_gateway = None  # type: ignore[assignment,misc]
    HAS_DESKTOP = False

try:
    from aureon.queen.queen_code_architect import QueenCodeArchitect
    HAS_CODE_ARCHITECT = True
except Exception:
    QueenCodeArchitect = None  # type: ignore[assignment,misc]
    HAS_CODE_ARCHITECT = False

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
ACTION_LOG_PATH = STATE_DIR / "agent_action_log.jsonl"
COMMAND_HISTORY_PATH = STATE_DIR / "agent_command_history.jsonl"

COMMON_APPS = {
    "chrome": "chrome.exe",
    "notepad": "notepad.exe",
    "explorer": "explorer.exe",
    "vscode": "code",
    "terminal": "cmd.exe",
    "powershell": "powershell.exe",
    "calculator": "calc.exe",
    "task manager": "taskmgr.exe",
    "edge": "msedge.exe",
    "firefox": "firefox.exe",
    "spotify": "spotify.exe",
}

# SOVEREIGN MODE — No command restrictions. The Queen is free.
# Gary granted full autonomous control. No cages.
DANGEROUS_SHELL_PATTERNS = []  # Cleared — sovereign authority
PROTECTED_DIRS = set()  # Cleared — full filesystem access

# SOVEREIGN MODE — full DB access, no read-only restriction.
READ_ONLY_SQL_BLOCKLIST = None  # Cleared — sovereign authority

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

    def __init__(self) -> None:
        self.repo_root = REPO_ROOT
        self.state_dir = STATE_DIR
        self._stats: Dict[str, int] = {"calls": 0, "success": 0, "failure": 0}

        # Lazy-init wired subsystems
        self._thought_bus: Optional[Any] = None
        self._desktop: Optional[Any] = None
        self._code_architect: Optional[Any] = None
        self._db_conn: Optional[Any] = None
        self._laptop: Optional[Any] = None
        self._parser: Optional[Any] = None

        # The legacy LaptopControl HAL contains ungoverned mutation primitives.
        # It is intentionally not attached to the master executor.  Screen and
        # input automation are exposed only through a governed gateway.
        self._laptop = None

        # Wire InstructionParser (natural language understanding)
        try:
            from aureon.autonomous.aureon_instruction_parser import InstructionParser
            self._parser = InstructionParser()
        except Exception:
            self._parser = None

    # ------------------------------------------------------------------
    # Subsystem accessors (lazy)
    # ------------------------------------------------------------------
    def _get_thought_bus(self):
        if self._thought_bus is None and HAS_THOUGHT_BUS:
            self._thought_bus = ThoughtBus(
                persist_path=str(STATE_DIR / "agent_thoughts.jsonl")
            )
        return self._thought_bus

    def _get_desktop(self):
        if self._desktop is None and HAS_DESKTOP:
            # No environment flag or persisted state may auto-arm the organism.
            # Live authority is an explicit, expiring in-memory lease.
            self._desktop = get_governed_desktop_gateway()
        return self._desktop

    def _get_code_architect(self):
        if self._code_architect is None and HAS_CODE_ARCHITECT:
            self._code_architect = QueenCodeArchitect(repo_path=str(REPO_ROOT))
        return self._code_architect

    def _get_db(self):
        if self._db_conn is None and HAS_HISTORY_DB:
            self._db_conn = db_connect()
        return self._db_conn

    # ------------------------------------------------------------------
    # Logging helpers
    # ------------------------------------------------------------------
    def _append_jsonl(self, path: Path, data: dict) -> None:
        try:
            with open(path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(data, default=str) + "\n")
        except Exception as exc:
            logger.warning("Failed to write to %s: %s", path, exc)

    def log_action(self, action: str, result: dict, duration: float = 0.0) -> None:
        entry = {
            "ts": datetime.datetime.utcnow().isoformat(),
            "action": action,
            "result_ok": result.get("success", False),
            "duration_s": round(duration, 4),
            "summary": str(result.get("result", ""))[:300],
        }
        self._append_jsonl(ACTION_LOG_PATH, entry)

    def _publish_search_capture(self, phase: str, **payload: Any) -> dict:
        """Best-effort search/browser/data-capture fabric publish."""
        try:
            from aureon.search.swarm_search_fabric import publish_search_event

            return publish_search_event(
                phase=phase,
                source_system="aureon_agent_core",
                **payload,
            )
        except Exception:
            return {}

    # ===================================================================
    #  1. SHELL EXECUTION
    # ===================================================================
    def execute_shell(self, command: str, timeout: int = 30, cwd: str = None,
                      force: bool = False) -> dict:
        """Run a shell command and return stdout / stderr / exit_code."""
        del force  # legacy argument retained for callers; it no longer bypasses safety
        # Safety check: conservative denylist with no sovereign override.
        patterns = list(DANGEROUS_SHELL_PATTERNS or [])
        if not patterns:
            patterns = [
                r"(?i)\\brm\\s+-rf\\b",
                r"(?i)\\brm\\s+-fr\\b",
                r"(?i)\\bdel\\b\\s+.*\\s+/s\\b",
                r"(?i)\\brmdir\\b\\s+.*\\s+/s\\b",
                r"(?i)\\bformat\\b",
                r"(?i)\\bdiskpart\\b",
                r"(?i)\\bshutdown\\b",
                r"(?i)\\breg\\s+delete\\b",
                r"(?i)\\bbcdedit\\b",
                r"(?i)\\bvssadmin\\s+delete\\b",
                r"(?i)\\bcipher\\s+/w\\b",
            ]
        for pat in patterns:
            if re.search(pat, command):
                return {
                    "stdout": "",
                    "stderr": f"Blocked dangerous command matching /{pat}/.",
                    "exit_code": -1,
                    "command": command,
                }
        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True,
                timeout=timeout, cwd=cwd,
            )
            out = {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.returncode,
                "command": command,
            }
        except subprocess.TimeoutExpired:
            out = {"stdout": "", "stderr": "Timed out", "exit_code": -1, "command": command}
        except Exception as exc:
            out = {"stdout": "", "stderr": str(exc), "exit_code": -1, "command": command}

        self._append_jsonl(COMMAND_HISTORY_PATH, {
            "ts": datetime.datetime.utcnow().isoformat(), **out
        })
        return out

    # ===================================================================
    #  2. APP LAUNCHER
    # ===================================================================
    def open_app(self, app_name: str) -> dict:
        """Open an application by name or path."""
        exe = COMMON_APPS.get(app_name.lower(), app_name)
        try:
            subprocess.Popen(exe, shell=True)
            return {"success": True, "app": exe}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def close_app(self, app_name: str) -> dict:
        """Close an application by image name."""
        exe = COMMON_APPS.get(app_name.lower(), app_name)
        if not exe.endswith(".exe"):
            exe += ".exe"
        result = subprocess.run(
            f"taskkill /im {exe} /f", shell=True, capture_output=True, text=True,
        )
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
        }

    def kill_process(self, name_or_pid: str) -> dict:
        """Kill a process by image name or PID."""
        target = str(name_or_pid or "").strip()
        if not target:
            return {"success": False, "error": "name_or_pid is required"}
        try:
            if sys.platform == "win32":
                if target.isdigit():
                    cmd = f"taskkill /pid {target} /f"
                else:
                    exe = target
                    if not exe.lower().endswith(".exe"):
                        exe += ".exe"
                    cmd = f"taskkill /im {exe} /f"
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                return {
                    "success": result.returncode == 0,
                    "command": cmd,
                    "stdout": result.stdout.strip(),
                    "stderr": result.stderr.strip(),
                }

            # Best-effort non-Windows fallback
            cmd = ["pkill", "-f", target]
            result = subprocess.run(cmd, capture_output=True, text=True)
            return {
                "success": result.returncode == 0,
                "command": " ".join(cmd),
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
            }
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def list_running_apps(self) -> list:
        """List currently running applications (visible window processes)."""
        result = subprocess.run(
            "tasklist /fo csv /nh", shell=True, capture_output=True, text=True,
        )
        apps: list[dict] = []
        for line in result.stdout.strip().splitlines():
            parts = line.replace('"', "").split(",")
            if len(parts) >= 5:
                apps.append({
                    "name": parts[0],
                    "pid": parts[1],
                    "mem": parts[4],
                })
        return apps

    def focus_window(self, title_pattern: str) -> dict:
        """Bring a window to the foreground by title substring (Windows)."""
        if not HAS_CTYPES or sys.platform != "win32":
            return {"success": False, "error": "ctypes/win32 not available"}
        try:
            import ctypes
            import ctypes.wintypes

            EnumWindows = ctypes.windll.user32.EnumWindows
            GetWindowTextW = ctypes.windll.user32.GetWindowTextW
            SetForegroundWindow = ctypes.windll.user32.SetForegroundWindow
            IsWindowVisible = ctypes.windll.user32.IsWindowVisible

            WNDENUMPROC = ctypes.WINFUNCTYPE(
                ctypes.wintypes.BOOL, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM,
            )
            found_hwnd = None
            pattern_lower = title_pattern.lower()

            def _cb(hwnd, _lp):
                nonlocal found_hwnd
                if IsWindowVisible(hwnd):
                    buf = ctypes.create_unicode_buffer(512)
                    GetWindowTextW(hwnd, buf, 512)
                    if pattern_lower in buf.value.lower():
                        found_hwnd = hwnd
                        return False  # stop enumeration
                return True

            EnumWindows(WNDENUMPROC(_cb), 0)
            if found_hwnd:
                SetForegroundWindow(found_hwnd)
                return {"success": True, "hwnd": found_hwnd}
            return {"success": False, "error": "Window not found"}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    # ===================================================================
    #  3. WEB SEARCH & BROWSING
    # ===================================================================
    def web_search(self, query: str, num_results: int = 5) -> list:
        """Search the web via DuckDuckGo HTML and return results."""
        start_event = self._publish_search_capture(
            "query_received",
            query=query,
            source="duckduckgo_html",
            metadata={"num_results": num_results},
        )
        trace_id = start_event.get("trace_id")
        query_id = start_event.get("query_id")
        if not HAS_REQUESTS or not HAS_BS4:
            self._publish_search_capture(
                "search_failed",
                query=query,
                trace_id=trace_id,
                query_id=query_id,
                source="duckduckgo_html",
                status="missing_dependency",
                error="requests or beautifulsoup4 not installed",
            )
            return [{"error": "requests or beautifulsoup4 not installed"}]
        try:
            self._publish_search_capture(
                "source_selected",
                query=query,
                trace_id=trace_id,
                query_id=query_id,
                source="duckduckgo_html",
                metadata={"endpoint": "https://html.duckduckgo.com/html/"},
            )
            resp = requests.get(
                "https://html.duckduckgo.com/html/",
                params={"q": query},
                headers={"User-Agent": "Mozilla/5.0 (Aureon Agent)"},
                timeout=15,
            )
            soup = BeautifulSoup(resp.text, "html.parser")
            results: list[dict] = []
            for r in soup.select(".result__body")[:num_results]:
                title_el = r.select_one(".result__a")
                snippet_el = r.select_one(".result__snippet")
                link_el = r.select_one(".result__url")
                results.append({
                    "title": title_el.get_text(strip=True) if title_el else "",
                    "snippet": snippet_el.get_text(strip=True) if snippet_el else "",
                    "url": link_el.get_text(strip=True) if link_el else "",
                })
            if results:
                self._publish_search_capture(
                    "result_captured",
                    query=query,
                    trace_id=trace_id,
                    query_id=query_id,
                    source="duckduckgo_html",
                    result_count=len(results),
                    status="success",
                    metadata={"http_status": resp.status_code},
                )
                return results
            fallback = self._official_learning_search_fallback(query, num_results)
            self._publish_search_capture(
                "result_captured",
                query=query,
                trace_id=trace_id,
                query_id=query_id,
                source="official_learning_fallback",
                result_count=len(fallback),
                status="fallback",
                metadata={"http_status": resp.status_code},
            )
            return fallback
        except Exception as exc:
            fallback = self._official_learning_search_fallback(query, num_results)
            if fallback:
                self._publish_search_capture(
                    "result_captured",
                    query=query,
                    trace_id=trace_id,
                    query_id=query_id,
                    source="official_learning_fallback",
                    result_count=len(fallback),
                    status="fallback_after_error",
                    error=str(exc),
                )
                return fallback
            self._publish_search_capture(
                "search_failed",
                query=query,
                trace_id=trace_id,
                query_id=query_id,
                source="duckduckgo_html",
                status="error",
                error=str(exc),
            )
            return [{"error": str(exc)}]

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
        """Fetch a web page and return its text content."""
        start_event = self._publish_search_capture(
            "page_fetch_requested",
            url=url,
            source="requests",
        )
        trace_id = start_event.get("trace_id")
        if not HAS_REQUESTS:
            self._publish_search_capture(
                "page_fetch_failed",
                url=url,
                trace_id=trace_id,
                source="requests",
                status="missing_dependency",
                error="requests not installed",
            )
            return {"success": False, "error": "requests not installed"}
        try:
            resp = requests.get(url, timeout=20, headers={
                "User-Agent": "Mozilla/5.0 (Aureon Agent)",
            })
            if HAS_BS4:
                soup = BeautifulSoup(resp.text, "html.parser")
                for tag in soup(["script", "style", "nav", "footer", "header"]):
                    tag.decompose()
                text = soup.get_text(separator="\n", strip=True)
            else:
                text = resp.text
            self._publish_search_capture(
                "page_fetched",
                url=url,
                trace_id=trace_id,
                source="requests",
                result_count=1,
                status="success",
                metadata={
                    "http_status": resp.status_code,
                    "captured_text_chars": len(text or ""),
                    "stored_text_chars": min(len(text or ""), 10000),
                },
            )
            return {
                "success": True,
                "url": url,
                "status_code": resp.status_code,
                "text": text[:10000],
            }
        except Exception as exc:
            self._publish_search_capture(
                "page_fetch_failed",
                url=url,
                trace_id=trace_id,
                source="requests",
                status="error",
                error=str(exc),
            )
            return {"success": False, "error": str(exc)}

    def open_url(self, url: str) -> dict:
        """Open a URL in the default browser."""
        try:
            webbrowser.open(url)
            self._publish_search_capture(
                "browser_opened",
                url=url,
                source="default_browser",
                status="success",
            )
            return {"success": True, "url": url}
        except Exception as exc:
            self._publish_search_capture(
                "browser_open_failed",
                url=url,
                source="default_browser",
                status="error",
                error=str(exc),
            )
            return {"success": False, "error": str(exc)}

    # ===================================================================
    #  4. FILE SYSTEM
    # ===================================================================
    def list_dir(self, path: str = ".") -> list:
        """List directory contents with file sizes and modification dates."""
        p = Path(path).resolve()
        if not p.is_dir():
            return [{"error": f"Not a directory: {p}"}]
        entries: list[dict] = []
        try:
            for item in sorted(p.iterdir()):
                try:
                    stat = item.stat()
                    entries.append({
                        "name": item.name,
                        "type": "dir" if item.is_dir() else "file",
                        "size": stat.st_size,
                        "modified": datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    })
                except PermissionError:
                    entries.append({"name": item.name, "type": "unknown", "error": "permission denied"})
        except PermissionError:
            return [{"error": f"Permission denied: {p}"}]
        return entries

    def read_file(self, path: str, max_lines: int = 200) -> str:
        """Read a file from anywhere on the PC (first N lines)."""
        p = Path(path)
        if not p.is_file():
            return f"ERROR: File not found: {path}"
        try:
            lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
            return "\n".join(lines[:max_lines])
        except Exception as exc:
            return f"ERROR: {exc}"

    def open_file(self, path: str) -> dict:
        """Open a file with its default application."""
        p = Path(path)
        if not p.exists():
            return {"success": False, "error": f"Not found: {path}"}
        try:
            if sys.platform == "win32":
                os.startfile(str(p.resolve()))  # type: ignore[attr-defined]
                return {"success": True, "path": str(p.resolve())}
            subprocess.Popen(["xdg-open", str(p.resolve())])
            return {"success": True, "path": str(p.resolve())}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def write_file(self, path: str, content: str, backup: bool = True) -> dict:
        """Write content to a file, optionally backing up the original."""
        p = Path(path)
        try:
            if backup and p.exists():
                bak = p.with_suffix(p.suffix + ".bak")
                shutil.copy2(str(p), str(bak))
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            return {"success": True, "path": str(p), "bytes": len(content)}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def find_files(self, directory: str, pattern: str) -> list:
        """Find files matching a glob pattern within a directory."""
        base = Path(directory).resolve()
        try:
            return [str(f) for f in base.rglob(pattern)][:500]
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
        """Fetch online sources, render a motion replay, and draft a paper."""
        try:
            from aureon.search.online_research_cinema import build_online_research_cinema

            return build_online_research_cinema(
                topic=topic,
                query=query or topic,
                urls=urls or None,
                max_sources=max_sources,
                root=self.repo_root,
            )
        except Exception as exc:
            self._publish_search_capture(
                "online_research_cinema_failed",
                query=query or topic,
                source="online_research_cinema",
                status="error",
                error=str(exc),
                metadata={"topic": topic},
            )
            return {"success": False, "error": str(exc), "topic": topic}

    def research_metacognition(
        self,
        topic: str = "",
        manifest_path: str = "frontend/public/aureon_online_research_cinema.json",
    ) -> dict:
        """Turn the latest research cinema packet into structured understanding."""
        try:
            manifest_file = (self.repo_root / manifest_path).resolve()
            manifest = json.loads(manifest_file.read_text(encoding="utf-8")) if manifest_file.exists() else {}
            if not isinstance(manifest, dict):
                manifest = {}
            from aureon.search.research_metacognition import build_research_metacognition

            packet_topic = topic or str(manifest.get("topic") or "Research Packet")
            paper = manifest.get("paper", {}) if isinstance(manifest.get("paper"), dict) else {}
            return build_research_metacognition(
                topic=packet_topic,
                query=str(manifest.get("query") or packet_topic),
                source_rows=manifest.get("source_rows", []) if isinstance(manifest.get("source_rows"), list) else [],
                paper_path=str(paper.get("path") or ""),
                motion_picture=manifest.get("motion_picture", {}) if isinstance(manifest.get("motion_picture"), dict) else {},
                coding_manifest=manifest.get("coding_handoff", {}) if isinstance(manifest.get("coding_handoff"), dict) else {},
                root=self.repo_root,
            )
        except Exception as exc:
            self._publish_search_capture(
                "metacognition_failed",
                query=topic or "research metacognition",
                source="research_metacognition",
                status="error",
                error=str(exc),
                metadata={"manifest_path": manifest_path},
            )
            return {"success": False, "error": str(exc), "topic": topic}

    def file_info(self, path: str) -> dict:
        """Get metadata for a file or directory."""
        p = Path(path)
        if not p.exists():
            return {"error": f"Not found: {path}"}
        stat = p.stat()
        return {
            "path": str(p.resolve()),
            "type": "dir" if p.is_dir() else "file",
            "size": stat.st_size,
            "modified": datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "created": datetime.datetime.fromtimestamp(stat.st_ctime).isoformat(),
        }

    def copy_file(self, src: str, dst: str) -> dict:
        try:
            shutil.copy2(src, dst)
            return {"success": True, "src": src, "dst": dst}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def move_file(self, src: str, dst: str) -> dict:
        try:
            shutil.move(src, dst)
            return {"success": True, "src": src, "dst": dst}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def delete_file(self, path: str, confirm: bool = False) -> dict:
        """Delete a file. Refuses system directories unless confirm=True."""
        p = Path(path).resolve()
        # Safety: block system directories
        for part in p.parts:
            if part.lower() in PROTECTED_DIRS and not confirm:
                return {
                    "success": False,
                    "error": f"Refusing to delete in protected directory '{part}'. "
                             "Pass confirm=True to override.",
                }
        if not confirm:
            return {
                "success": False,
                "error": "Pass confirm=True to actually delete.",
                "path": str(p),
            }
        try:
            if p.is_dir():
                shutil.rmtree(str(p))
            else:
                p.unlink()
            return {"success": True, "deleted": str(p)}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def create_dir(self, path: str) -> dict:
        try:
            Path(path).mkdir(parents=True, exist_ok=True)
            return {"success": True, "path": path}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    # ===================================================================
    #  5. CODE EXECUTION (wire QueenCodeArchitect)
    # ===================================================================
    def execute_python(self, code: str) -> dict:
        """Execute Python code and return output."""
        ca = self._get_code_architect()
        if ca:
            try:
                return ca.execute_code(code)
            except Exception as exc:
                return {"success": False, "error": str(exc)}
        # Fallback: run in subprocess
        try:
            result = subprocess.run(
                [sys.executable, "-c", code],
                capture_output=True, text=True, timeout=30,
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.returncode,
            }
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def create_script(self, path: str, code: str) -> dict:
        """Create a Python script file."""
        return self.write_file(path, code, backup=True)

    def run_script(self, path: str) -> dict:
        """Run a Python script file."""
        p = Path(path)
        if not p.is_file():
            return {"success": False, "error": f"Script not found: {path}"}
        try:
            result = subprocess.run(
                [sys.executable, str(p)],
                capture_output=True, text=True, timeout=60,
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.returncode,
            }
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    # ===================================================================
    #  6. DESKTOP CONTROL (wire SafeDesktopControl)
    # ===================================================================
    def _desktop_exec(self, action: str, params: dict) -> dict:
        dc = self._get_desktop()
        if dc is None:
            return {"success": False, "error": "GovernedDesktopGateway not available"}
        try:
            p = dict(params or {})
            target_binding_id = str(p.pop("target_binding_id", "") or "") or None
            mapped = {
                "move_mouse": "move",
                "left_click": "click",
                "right_click": "right_click",
                "double_click": "double_click",
                "type_text": "type",
                "press_key": "press",
                "hotkey": "hotkey",
                "scroll": "scroll",
            }.get(action, action)
            if target_binding_id is None:
                return {
                    "success": False,
                    "error": "valid_target_window_binding_required",
                }

            # Bind every mutation to the exact masked pixels from which it was
            # chosen.  The gateway captures again immediately before dispatch
            # and rejects the action if the target window has drifted.
            source = dc.observe(target_binding_id=target_binding_id)
            if not source.ok or not source.before_sha256:
                return {
                    "success": False,
                    "error": "bound_source_observation_failed",
                    "source_observation": source.to_dict(),
                }
            res = dc.execute(
                mapped,
                p,
                target_binding_id=target_binding_id,
                expected_before_sha256=source.before_sha256,
            )
            return {
                "success": res.ok,
                **res.to_dict(),
                "source_observation_action_id": source.action_id,
            }
        except Exception as exc:
            return {"success": False, "error": str(exc)}

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
        dc = self._get_desktop()
        if dc is None:
            return {"success": False, "error": "GovernedDesktopGateway not available"}
        try:
            lease = dc.authorize_live(
                capability_token,
                ttl_seconds=ttl_seconds,
                subject=subject,
                allowed_actions=allowed_actions,
            )
            return {"success": True, "result": lease.public_dict(), "status": dc.status()}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

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
        """Network interfaces and basic connectivity check."""
        info: dict = {"connected": False, "interfaces": {}}
        if HAS_PSUTIL:
            addrs = psutil.net_if_addrs()
            for iface, addr_list in addrs.items():
                info["interfaces"][iface] = [
                    {"family": str(a.family), "address": a.address}
                    for a in addr_list
                ]
        # Quick connectivity check
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            info["connected"] = True
        except OSError:
            info["connected"] = False
        return info

    # ===================================================================
    #  8. KNOWLEDGE QUERY (wire global_history_db)
    # ===================================================================
    def query_knowledge(self, sql: str) -> list:
        """Run SQL against the unified knowledge DB (read-only by default)."""
        conn = self._get_db()
        if conn is None:
            return [{"error": "Knowledge DB not available"}]
        sovereign = str(os.getenv("AUREON_SOVEREIGN_MODE", "")).strip().lower() in {"1", "true", "yes", "on"}
        sql_text = (sql or "").strip()
        if not sql_text:
            return [{"error": "SQL is empty"}]
        if not sovereign:
            lower = sql_text.lower()
            allowed_prefixes = ("select", "with")
            if not lower.startswith(allowed_prefixes):
                return [{"error": "Blocked non-read-only SQL. Use SELECT/WITH or set AUREON_SOVEREIGN_MODE=1."}]
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
            )
            for kw in block_keywords:
                if re.search(rf"\\b{kw}\\b", lower):
                    return [{"error": f"Blocked keyword in SQL: {kw}. Set AUREON_SOVEREIGN_MODE=1 to override."}]
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
        """Dynamically load an exchange client by venue name."""
        mapping = {
            "binance": ("aureon.exchanges.binance_client", "BinanceClient"),
            "alpaca": ("aureon.exchanges.alpaca_client", "AlpacaClient"),
            "capital": ("aureon.exchanges.capital_cfd_trader", "CapitalCFDTrader"),
        }
        if venue not in mapping:
            return None
        mod_name, cls_name = mapping[venue]
        try:
            import importlib
            mod = importlib.import_module(mod_name)
            cls = getattr(mod, cls_name)
            return cls()
        except Exception as exc:
            logger.warning("Could not load %s: %s", venue, exc)
            return None

    def get_balances(self, venue: str = "all") -> dict:
        """Get account balances."""
        if venue == "all":
            result = {}
            for v in ("binance", "alpaca", "capital"):
                client = self._load_exchange_client(v)
                if client and hasattr(client, "get_balances"):
                    try:
                        result[v] = client.get_balances()
                    except Exception as exc:
                        result[v] = {"error": str(exc)}
            return result
        client = self._load_exchange_client(venue)
        if client is None:
            return {"error": f"Unknown venue: {venue}"}
        try:
            return client.get_balances()
        except Exception as exc:
            return {"error": str(exc)}

    def place_order(self, venue: str, symbol: str, side: str, qty: float,
                    order_type: str = "market") -> dict:
        """Place a trade order on a specific venue."""
        client = self._load_exchange_client(venue)
        if client is None:
            return {"success": False, "error": f"Unknown venue: {venue}"}
        try:
            if hasattr(client, "place_order"):
                return client.place_order(symbol=symbol, side=side, qty=qty,
                                          order_type=order_type)
            return {"success": False, "error": "Client has no place_order method"}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def get_positions(self, venue: str = "all") -> dict:
        """Get open positions."""
        if venue == "all":
            result = {}
            for v in ("binance", "alpaca", "capital"):
                client = self._load_exchange_client(v)
                if client and hasattr(client, "get_positions"):
                    try:
                        result[v] = client.get_positions()
                    except Exception as exc:
                        result[v] = {"error": str(exc)}
            return result
        client = self._load_exchange_client(venue)
        if client is None:
            return {"error": f"Unknown venue: {venue}"}
        try:
            return client.get_positions()
        except Exception as exc:
            return {"error": str(exc)}

    def get_recent_trades(self, venue: str = "all", limit: int = 10) -> list:
        """Get recent trades from exchange clients."""
        if venue == "all":
            results: list = []
            for v in ("binance", "alpaca", "capital"):
                client = self._load_exchange_client(v)
                if client and hasattr(client, "get_recent_trades"):
                    try:
                        trades = client.get_recent_trades(limit=limit)
                        results.extend(trades if isinstance(trades, list) else [])
                    except Exception:
                        pass
            return results
        client = self._load_exchange_client(venue)
        if client is None:
            return [{"error": f"Unknown venue: {venue}"}]
        try:
            return client.get_recent_trades(limit=limit)
        except Exception as exc:
            return [{"error": str(exc)}]

    # ===================================================================
    #  10. COMMUNICATION
    # ===================================================================
    def speak(self, text: str, priority: int = 3) -> dict:
        """Speak via TTS (publish thought with voice topic)."""
        bus = self._get_thought_bus()
        if bus:
            try:
                bus.publish(
                    source="agent_core",
                    topic="voice.speak",
                    payload={"text": text, "priority": priority},
                )
                return {"success": True, "text": text}
            except Exception as exc:
                return {"success": False, "error": str(exc)}
        # Fallback: system TTS on Windows
        if sys.platform == "win32":
            try:
                subprocess.Popen(
                    ["powershell", "-Command",
                     f"Add-Type -AssemblyName System.Speech; "
                     f"(New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak('{text}')"],
                )
                return {"success": True, "text": text, "method": "powershell_tts"}
            except Exception:
                pass
        return {"success": False, "error": "No TTS backend available"}

    def notify(self, title: str, message: str) -> dict:
        """Show a user-visible notification (best-effort)."""
        try:
            if sys.platform == "win32":
                # Run in a separate process so we don't block the agent loop/REPL.
                script = (
                    "Add-Type -AssemblyName PresentationFramework; "
                    "[System.Windows.MessageBox]::Show("
                    f"@'{message}'@, @'{title}'@) | Out-Null"
                )
                subprocess.Popen(["powershell", "-NoProfile", "-Command", script])
                return {"success": True, "method": "powershell_messagebox"}

            logger.info("notify: %s | %s", title, message)
            return {"success": True, "method": "log"}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def think(self, message: str, topic: str = "agent.action") -> dict:
        """Publish a thought to ThoughtBus."""
        bus = self._get_thought_bus()
        if bus:
            try:
                bus.publish(source="agent_core", topic=topic,
                            payload={"message": message})
                return {"success": True, "topic": topic}
            except Exception as exc:
                return {"success": False, "error": str(exc)}
        return {"success": False, "error": "ThoughtBus not available"}

    # ===================================================================
    #  MASTER EXECUTE
    # ===================================================================
    def execute(self, intent: str, params: dict = None) -> dict:
        """
        Execute any task by intent name.

        Routes to the correct tool based on the intent string.
        Returns: {"success": bool, "result": any, "tool_used": str, "error": str}
        """
        params = params or {}
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
            "shell": "Run a shell command",
            "open_app": "Open an application",
            "close_app": "Close an application",
            "list_apps": "List running applications",
            "focus_window": "Bring a window to focus",
            "web_search": "Search the web",
            "web_fetch": "Fetch a web page as text",
            "open_url": "Open a URL in the browser",
            "list_dir": "List directory contents",
            "read_file": "Read a file",
            "open_file": "Open a file with default app",
            "write_file": "Write content to a file",
            "find_files": "Find files by glob pattern",
            "keyword_search": "Read local text/test files and find keyword snippets",
            "online_research_cinema": "Fetch online sources, render research motion replay, and draft a cited paper",
            "research_metacognition": "Convert the latest research cinema packet into structured organism understanding",
            "file_info": "Get file metadata",
            "copy_file": "Copy a file",
            "move_file": "Move a file",
            "delete_file": "Delete a file (requires confirm)",
            "create_dir": "Create a directory",
            "execute_python": "Execute Python code",
            "create_script": "Create a Python script file",
            "run_script": "Run a Python script",
            "click": "Click at screen coordinates",
            "move_mouse": "Move mouse to coordinates",
            "right_click": "Right click at coordinates",
            "double_click": "Double click at coordinates",
            "type_text": "Type text via keyboard",
            "press_key": "Press a keyboard key",
            "hotkey": "Press a keyboard shortcut",
            "screenshot": "Take a screenshot",
            "desktop_status": "Get desktop controller status",
            "desktop_arm_live": "Arm desktop controller (live mode)",
            "desktop_arm_dry_run": "Arm desktop controller (dry-run mode)",
            "desktop_disarm": "Disarm desktop controller",
            "desktop_emergency_stop": "Emergency stop desktop controller",
            "desktop_clear_emergency_stop": "Clear emergency stop and keep disarmed",
            "system_info": "Get CPU/RAM/disk/OS info",
            "processes": "List top processes",
            "network_status": "Check network connectivity",
            "kill_process": "Kill a process by name or PID",
            "query_knowledge": "Run SQL on knowledge DB",
            "search_knowledge": "Keyword search across DB",
            "market_summary": "Get latest market data",
            "portfolio": "Get portfolio / recent trades",
            "get_balances": "Get exchange balances",
            "get_positions": "Get open positions",
            "place_order": "Place a trade order",
            "get_recent_trades": "Get recent trades",
            "speak": "Speak via TTS",
            "notify": "Show a notification dialog",
            "think": "Publish a thought to ThoughtBus",
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
        if self._parser is not None:
            try:
                parsed = self._parser.parse(natural_language)
                if parsed:
                    # Convert parser output to plan_task format
                    for step in parsed:
                        method = step.get("method", "")
                        tool = step.get("tool", "")
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
