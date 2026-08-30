"""
ObsidianBridge — Local REST API client + filesystem-vault fallback
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Two transport modes:

  ObsidianMode.LOCAL_REST — talks to the `obsidian-local-rest-api`
      community plugin at https://localhost:27124 over HTTPS with a
      self-signed cert. Requires a Bearer API key supplied via
      AUREON_OBSIDIAN_API_KEY or the `api_key` constructor arg.

  ObsidianMode.FILESYSTEM — directly reads/writes `.md` files inside
      an Obsidian vault directory. This is the lowest-friction mode
      and works even when the plugin is not installed.

The bridge auto-selects LOCAL_REST if an API key is provided AND the
plugin is reachable; otherwise it falls back to FILESYSTEM. Either way,
callers use the same seven-method surface:

    health_check()
    write_note(path, content, overwrite=False)
    append_note(path, content)
    read_note(path)
    patch_section(path, heading, content, operation='append')
    search(query)
    list_notes(folder='')

Environment overrides:

    AUREON_OBSIDIAN_API_KEY    — Bearer token for the plugin
    AUREON_OBSIDIAN_BASE_URL   — default https://localhost:27124
    AUREON_OBSIDIAN_VAULT_PATH — filesystem path for the fallback
    AUREON_OBSIDIAN_VERIFY_TLS — '1' to enforce TLS verification (default off)
"""

from __future__ import annotations

import datetime as _dt
import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from aureon.obsidian_paths import (
    default_obsidian_vault_path,
    resolve_obsidian_vault_path,
)

logger = logging.getLogger("aureon.integrations.obsidian")

DEFAULT_BASE_URL = "https://localhost:27124"
DEFAULT_VAULT_PATH = str(default_obsidian_vault_path())
DEFAULT_TIMEOUT_S = 10.0


class ObsidianBridgeError(RuntimeError):
    """Raised on unrecoverable bridge failures when strict mode is on."""


class ObsidianMode(str, Enum):
    LOCAL_REST = "local_rest"
    FILESYSTEM = "filesystem"
    UNAVAILABLE = "unavailable"


@dataclass
class ObsidianNote:
    """A note returned by the bridge."""

    path: str = ""
    content: str = ""
    frontmatter: Dict[str, Any] = field(default_factory=dict)
    size_bytes: int = 0


# ─────────────────────────────────────────────────────────────────────────────
# ObsidianBridge
# ─────────────────────────────────────────────────────────────────────────────


_UNSAFE_PATH_RE = re.compile(r"[^A-Za-z0-9 _\-./]")


class ObsidianBridge:
    """
    One client, two transports. Prefers the Local REST API when keyed and
    reachable, otherwise falls back to a filesystem vault.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        vault_path: Optional[str] = None,
        verify_tls: Optional[bool] = None,
        timeout_s: Optional[float] = None,
        prefer_filesystem: bool = False,
    ):
        self.api_key = api_key or os.environ.get("AUREON_OBSIDIAN_API_KEY", "")
        self.base_url = (
            base_url or os.environ.get("AUREON_OBSIDIAN_BASE_URL", DEFAULT_BASE_URL)
        ).rstrip("/")
        self.vault_path = resolve_obsidian_vault_path(vault_path)
        env_verify = os.environ.get("AUREON_OBSIDIAN_VERIFY_TLS", "").strip()
        if verify_tls is None:
            self.verify_tls = env_verify == "1"
        else:
            self.verify_tls = bool(verify_tls)
        self.timeout_s = float(timeout_s or DEFAULT_TIMEOUT_S)
        self.prefer_filesystem = bool(prefer_filesystem)

        self._session: Any = None
        self._requests_available = False
        try:
            import requests  # type: ignore

            self._session = requests.Session()
            self._requests_available = True
        except Exception:
            logger.debug("requests not installed — ObsidianBridge REST mode disabled")

        self._last_health: Optional[bool] = None
        self._last_health_at: float = 0.0
        self.mode: ObsidianMode = self._pick_mode()

    # ─────────────────────────────────────────────────────────────────────
    # Mode selection / health
    # ─────────────────────────────────────────────────────────────────────

    def _pick_mode(self) -> ObsidianMode:
        if not self.prefer_filesystem and self._rest_available():
            return ObsidianMode.LOCAL_REST
        if self._fs_available():
            return ObsidianMode.FILESYSTEM
        return ObsidianMode.UNAVAILABLE

    def _rest_available(self) -> bool:
        if not (self._requests_available and self.api_key):
            return False
        try:
            resp = self._session.get(
                f"{self.base_url}/",
                headers=self._headers(),
                verify=self.verify_tls,
                timeout=self.timeout_s,
            )
            return resp.status_code == 200
        except Exception as e:
            logger.debug("obsidian REST probe failed: %s", e)
            return False

    def _fs_available(self) -> bool:
        try:
            self.vault_path.mkdir(parents=True, exist_ok=True)
            return self.vault_path.is_dir() and os.access(self.vault_path, os.W_OK)
        except Exception as e:
            logger.debug("obsidian filesystem probe failed: %s", e)
            return False

    def health_check(self, max_age_s: float = 5.0) -> bool:
        """Return True if *some* transport is working."""
        now = time.time()
        if (
            self._last_health is not None
            and (now - self._last_health_at) < max_age_s
        ):
            return self._last_health
        self.mode = self._pick_mode()
        ok = self.mode in (ObsidianMode.LOCAL_REST, ObsidianMode.FILESYSTEM)
        self._last_health = ok
        self._last_health_at = now
        return ok

    def _headers(self) -> Dict[str, str]:
        h = {"Content-Type": "text/markdown; charset=utf-8"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    # ─────────────────────────────────────────────────────────────────────
    # Core note ops (dispatches by mode)
    # ─────────────────────────────────────────────────────────────────────

    def write_note(
        self,
        path: str,
        content: str,
        overwrite: bool = False,
    ) -> bool:
        """Create or (if overwrite) replace a note at `path`. Returns success."""
        path = self._safe_path(path)
        if self.mode == ObsidianMode.LOCAL_REST:
            return self._rest_write(path, content, overwrite)
        if self.mode == ObsidianMode.FILESYSTEM:
            return self._fs_write(path, content, overwrite)
        return False

    def append_note(self, path: str, content: str) -> bool:
        """Append to a note (creating it if missing). Returns success."""
        path = self._safe_path(path)
        if self.mode == ObsidianMode.LOCAL_REST:
            return self._rest_append(path, content)
        if self.mode == ObsidianMode.FILESYSTEM:
            return self._fs_append(path, content)
        return False

    def read_note(self, path: str) -> Optional[ObsidianNote]:
        """Read a note. Returns None if missing."""
        path = self._safe_path(path)
        if self.mode == ObsidianMode.LOCAL_REST:
            return self._rest_read(path)
        if self.mode == ObsidianMode.FILESYSTEM:
            return self._fs_read(path)
        return None

    def patch_section(
        self,
        path: str,
        heading: str,
        content: str,
        operation: str = "append",
    ) -> bool:
        """
        Append/prepend/replace content under a specific heading.
        Uses the Local REST plugin's PATCH semantics when available,
        falls back to a filesystem edit otherwise.
        """
        path = self._safe_path(path)
        if self.mode == ObsidianMode.LOCAL_REST:
            return self._rest_patch_section(path, heading, content, operation)
        if self.mode == ObsidianMode.FILESYSTEM:
            return self._fs_patch_section(path, heading, content, operation)
        return False

    def search(self, query: str) -> List[Dict[str, Any]]:
        """
        Search the vault. Uses /search/simple/ over REST, or a naive
        in-memory grep over the filesystem vault.
        """
        q = query.strip()
        if not q:
            return []
        if self.mode == ObsidianMode.LOCAL_REST:
            return self._rest_search(q)
        if self.mode == ObsidianMode.FILESYSTEM:
            return self._fs_search(q)
        return []

    def list_notes(self, folder: str = "") -> List[str]:
        """List .md files under `folder` (relative to vault root)."""
        folder = self._safe_path(folder) if folder else ""
        if self.mode == ObsidianMode.LOCAL_REST:
            return self._rest_list(folder)
        if self.mode == ObsidianMode.FILESYSTEM:
            return self._fs_list(folder)
        return []

    # ─────────────────────────────────────────────────────────────────────
    # LOCAL_REST backend
    # ─────────────────────────────────────────────────────────────────────

    def _rest_url(self, path: str) -> str:
        safe = "/".join(self._safe_path(path).split("/"))
        return f"{self.base_url}/vault/{safe}"

    def _rest_write(self, path: str, content: str, overwrite: bool) -> bool:
        try:
            method = "PUT" if overwrite else "POST"
            resp = self._session.request(
                method,
                self._rest_url(path),
                data=content.encode("utf-8"),
                headers=self._headers(),
                verify=self.verify_tls,
                timeout=self.timeout_s,
            )
            return 200 <= resp.status_code < 300
        except Exception as e:
            logger.debug("obsidian REST write failed: %s", e)
            return False

    def _rest_append(self, path: str, content: str) -> bool:
        try:
            headers = dict(self._headers())
            headers["Operation"] = "append"
            resp = self._session.patch(
                self._rest_url(path),
                data=("\n" + content).encode("utf-8"),
                headers=headers,
                verify=self.verify_tls,
                timeout=self.timeout_s,
            )
            if 200 <= resp.status_code < 300:
                return True
            # If the note doesn't exist, create it
            return self._rest_write(path, content, overwrite=False)
        except Exception as e:
            logger.debug("obsidian REST append failed: %s", e)
            return False

    def _rest_read(self, path: str) -> Optional[ObsidianNote]:
        try:
            resp = self._session.get(
                self._rest_url(path),
                headers={"Authorization": f"Bearer {self.api_key}", "Accept": "text/markdown"},
                verify=self.verify_tls,
                timeout=self.timeout_s,
            )
            if resp.status_code == 200:
                body = resp.text or ""
                return ObsidianNote(path=path, content=body, size_bytes=len(body))
            return None
        except Exception as e:
            logger.debug("obsidian REST read failed: %s", e)
            return None

    def _rest_patch_section(
        self, path: str, heading: str, content: str, operation: str
    ) -> bool:
        try:
            headers = dict(self._headers())
            headers["Operation"] = operation
            headers["Target-Type"] = "heading"
            headers["Target"] = heading
            resp = self._session.patch(
                self._rest_url(path),
                data=content.encode("utf-8"),
                headers=headers,
                verify=self.verify_tls,
                timeout=self.timeout_s,
            )
            return 200 <= resp.status_code < 300
        except Exception as e:
            logger.debug("obsidian REST patch_section failed: %s", e)
            return False

    def _rest_search(self, query: str) -> List[Dict[str, Any]]:
        try:
            resp = self._session.post(
                f"{self.base_url}/search/simple/",
                params={"query": query},
                headers={"Authorization": f"Bearer {self.api_key}"},
                verify=self.verify_tls,
                timeout=self.timeout_s,
            )
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list):
                    return data
                return data.get("results", []) or []
            return []
        except Exception as e:
            logger.debug("obsidian REST search failed: %s", e)
            return []

    def _rest_list(self, folder: str) -> List[str]:
        """The REST API exposes vault listing only for folders; we GET /vault/{folder}/."""
        try:
            url = f"{self.base_url}/vault/{folder}/" if folder else f"{self.base_url}/vault/"
            resp = self._session.get(
                url,
                headers={"Authorization": f"Bearer {self.api_key}"},
                verify=self.verify_tls,
                timeout=self.timeout_s,
            )
            if resp.status_code != 200:
                return []
            try:
                data = resp.json()
            except Exception:
                return []
            files = data.get("files") if isinstance(data, dict) else data
            if not isinstance(files, list):
                return []
            return [str(x) for x in files if str(x).endswith(".md")]
        except Exception as e:
            logger.debug("obsidian REST list failed: %s", e)
            return []

    # ─────────────────────────────────────────────────────────────────────
    # FILESYSTEM backend
    # ─────────────────────────────────────────────────────────────────────

    def _fs_path(self, path: str) -> Path:
        rel = self._safe_path(path)
        if not rel.endswith(".md"):
            rel = rel + ".md"
        full = (self.vault_path / rel).resolve()
        # Enforce the resolved path still lives under the vault root
        try:
            full.relative_to(self.vault_path.resolve())
        except ValueError:
            raise ObsidianBridgeError(f"path escape attempt: {path}")
        return full

    def _fs_write(self, path: str, content: str, overwrite: bool) -> bool:
        try:
            full = self._fs_path(path)
            full.parent.mkdir(parents=True, exist_ok=True)
            if full.exists() and not overwrite:
                # Disambiguate with a timestamp suffix
                stem = full.stem
                ts = _dt.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                full = full.with_name(f"{stem}_{ts}.md")
            full.write_text(content, encoding="utf-8")
            return True
        except Exception as e:
            logger.debug("obsidian FS write failed: %s", e)
            return False

    def _fs_append(self, path: str, content: str) -> bool:
        try:
            full = self._fs_path(path)
            full.parent.mkdir(parents=True, exist_ok=True)
            sep = "" if not full.exists() else "\n"
            with full.open("a", encoding="utf-8") as fh:
                fh.write(sep + content)
            return True
        except Exception as e:
            logger.debug("obsidian FS append failed: %s", e)
            return False

    def _fs_read(self, path: str) -> Optional[ObsidianNote]:
        try:
            full = self._fs_path(path)
            if not full.exists():
                return None
            body = full.read_text(encoding="utf-8")
            return ObsidianNote(path=path, content=body, size_bytes=len(body))
        except Exception as e:
            logger.debug("obsidian FS read failed: %s", e)
            return None

    def _fs_patch_section(
        self, path: str, heading: str, content: str, operation: str
    ) -> bool:
        try:
            full = self._fs_path(path)
            if not full.exists():
                # Create the note with the heading seeded
                seed = f"# {heading}\n\n{content}\n"
                return self._fs_write(path, seed, overwrite=True)
            text = full.read_text(encoding="utf-8")
            lines = text.split("\n")
            target_idx = None
            heading_match = re.compile(r"^#{1,6}\s+" + re.escape(heading) + r"\s*$")
            for i, line in enumerate(lines):
                if heading_match.match(line):
                    target_idx = i
                    break
            if target_idx is None:
                # Append the heading + content
                lines.append("")
                lines.append(f"# {heading}")
                lines.append(content)
            else:
                # Find the end of the section (next heading at same-or-higher level
                # or end of file).
                end_idx = len(lines)
                for j in range(target_idx + 1, len(lines)):
                    if re.match(r"^#{1,6}\s+", lines[j]):
                        end_idx = j
                        break
                if operation == "prepend":
                    lines[target_idx + 1 : target_idx + 1] = [content, ""]
                elif operation == "replace":
                    lines[target_idx + 1 : end_idx] = [content, ""]
                else:  # append (default)
                    lines[end_idx:end_idx] = ["", content]
            full.write_text("\n".join(lines), encoding="utf-8")
            return True
        except Exception as e:
            logger.debug("obsidian FS patch_section failed: %s", e)
            return False

    def _fs_search(self, query: str) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        q_lower = query.lower()
        try:
            for p in self.vault_path.rglob("*.md"):
                try:
                    body = p.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    continue
                if q_lower in body.lower():
                    rel = str(p.relative_to(self.vault_path))
                    # Grab a little context snippet
                    idx = body.lower().find(q_lower)
                    snippet = body[max(0, idx - 40) : idx + 80]
                    out.append({"filename": rel, "score": 1.0, "context": snippet})
                    if len(out) >= 50:
                        break
        except Exception as e:
            logger.debug("obsidian FS search failed: %s", e)
        return out

    def _fs_list(self, folder: str) -> List[str]:
        out: List[str] = []
        try:
            root = self.vault_path / folder if folder else self.vault_path
            if not root.is_dir():
                return []
            for p in root.rglob("*.md"):
                out.append(str(p.relative_to(self.vault_path)))
        except Exception as e:
            logger.debug("obsidian FS list failed: %s", e)
        return out

    # ─────────────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────────────

    @staticmethod
    def _safe_path(path: str) -> str:
        """Sanitise a caller-supplied path — strip '..', leading slashes, etc."""
        cleaned = str(path or "").replace("\\", "/").strip()
        cleaned = cleaned.lstrip("/")
        # Disallow parent-dir traversal
        parts = [p for p in cleaned.split("/") if p not in ("", ".", "..")]
        sanitised = "/".join(_UNSAFE_PATH_RE.sub("_", p) for p in parts)
        return sanitised

    # ─────────────────────────────────────────────────────────────────────
    # Snapshot (for the audit trail)
    # ─────────────────────────────────────────────────────────────────────

    def snapshot(self) -> Dict[str, Any]:
        reachable = self.health_check()
        snap: Dict[str, Any] = {
            "reachable": reachable,
            "mode": self.mode.value,
            "base_url": self.base_url,
            "vault_path": str(self.vault_path),
            "api_key_set": bool(self.api_key),
            "verify_tls": self.verify_tls,
            "requests_installed": self._requests_available,
            "note_count": 0,
        }
        if reachable:
            try:
                snap["note_count"] = len(self.list_notes())
            except Exception:
                pass
        return snap
