"""
Aureon ↔ Obsidian Integration
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Thin client for the community `obsidian-local-rest-api` plugin plus a
filesystem fallback so the vault can mirror its thoughts into a real
Obsidian vault (notes, daily journal, tagged folders) even when the
plugin is not installed.

Two collaborators:

  ObsidianBridge  — talks to the Local REST API on https://localhost:27124
                    (HTTPS, self-signed cert, Bearer auth) and falls back
                    to a local filesystem vault if the API is unreachable.

  ObsidianSink    — subscribes to vault utterances / ticks / audit events
                    and writes them as markdown notes: daily journal,
                    per-voice folders, and a rolling "cognitive loop log".
"""

from aureon.integrations.obsidian.obsidian_bridge import (
    ObsidianBridge,
    ObsidianBridgeError,
    ObsidianMode,
    ObsidianNote,
)
from aureon.integrations.obsidian.obsidian_sink import (
    ObsidianSink,
    ObsidianSinkConfig,
)
from aureon.obsidian_paths import (
    default_obsidian_vault_path,
    resolve_obsidian_note_path,
    resolve_obsidian_vault_path,
)

__all__ = [
    "ObsidianBridge",
    "ObsidianBridgeError",
    "ObsidianMode",
    "ObsidianNote",
    "ObsidianSink",
    "ObsidianSinkConfig",
    "default_obsidian_vault_path",
    "resolve_obsidian_note_path",
    "resolve_obsidian_vault_path",
]
