#!/usr/bin/env python3
"""
tests/integrations/test_obsidian_bridge.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ObsidianBridge + ObsidianSink tests. These tests exercise the
FILESYSTEM backend in a temporary directory (no running Obsidian app
needed) and verify the sink observers write the expected notes.

Covers:
  1. Filesystem vault mode auto-selects when no API key is provided
  2. write_note / read_note / append_note round-trip
  3. patch_section operations (append, prepend, replace)
  4. search grep over the vault files
  5. path sanitisation blocks directory traversal
  6. ObsidianSink.on_utterance creates daily + per-voice notes
  7. ObsidianSink.on_tick appends one line to the loop log
  8. ObsidianSink.on_audit writes an audit dump
  9. Canonical vault resolution honors explicit and environment overrides
 10. Legacy repo note paths route to the dedicated vault in Git checkouts
 11. Non-Git test fixtures retain isolated repo-local note paths
 12. Canonical path resolution blocks directory traversal
"""

import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from aureon.integrations.obsidian import (
    ObsidianBridge,
    ObsidianMode,
    ObsidianSink,
    ObsidianSinkConfig,
)
from aureon.integrations.obsidian.obsidian_bridge import ObsidianBridgeError
from aureon.obsidian_paths import (
    resolve_obsidian_note_path,
    resolve_obsidian_vault_path,
)
from aureon.vault.voice.utterance import Utterance, VoiceStatement


PASS = 0
FAIL = 0


def check(condition, msg):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  [OK] {msg}")
    else:
        FAIL += 1
        print(f"  [!!] {msg}")


def _make_bridge(tmp: Path) -> ObsidianBridge:
    # Force filesystem mode by providing no API key + explicit vault path
    return ObsidianBridge(
        api_key="",
        vault_path=str(tmp),
        prefer_filesystem=True,
    )


def test_canonical_vault_resolution(tmp_path, monkeypatch):
    env_vault = tmp_path / "environment-vault"
    explicit_vault = tmp_path / "explicit-vault"
    monkeypatch.setenv("AUREON_OBSIDIAN_VAULT_PATH", str(env_vault))

    assert resolve_obsidian_vault_path() == env_vault.resolve()
    assert resolve_obsidian_vault_path(explicit_vault) == explicit_vault.resolve()

    bridge = ObsidianBridge(api_key="", prefer_filesystem=True)
    assert bridge.vault_path == env_vault.resolve()


def test_legacy_note_routes_to_canonical_vault_in_git_checkout(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    vault = tmp_path / "vault"
    (repo / ".git").mkdir(parents=True)
    monkeypatch.setenv("AUREON_OBSIDIAN_VAULT_PATH", str(vault))

    resolved = resolve_obsidian_note_path(
        ".obsidian/Aureon Self Understanding/status.md",
        repo_root=repo,
    )

    assert resolved == (vault / "Aureon Self Understanding" / "status.md").resolve()


def test_legacy_note_stays_isolated_for_non_git_fixture(tmp_path, monkeypatch):
    repo = tmp_path / "fixture"
    repo.mkdir()
    monkeypatch.delenv("AUREON_OBSIDIAN_VAULT_PATH", raising=False)

    resolved = resolve_obsidian_note_path(
        ".obsidian/Aureon Self Understanding/status.md",
        repo_root=repo,
    )

    assert resolved == (repo / ".obsidian" / "Aureon Self Understanding" / "status.md").resolve()


def test_canonical_note_resolution_blocks_traversal(tmp_path):
    vault = tmp_path / "vault"

    try:
        resolve_obsidian_note_path(
            ".obsidian/../../escape.md",
            vault_path=vault,
        )
    except ValueError as exc:
        assert "escapes vault" in str(exc)
    else:
        raise AssertionError("vault traversal was not rejected")


# ─────────────────────────────────────────────────────────────────────────────
# 1. Mode selection + health
# ─────────────────────────────────────────────────────────────────────────────


def test_mode_selection():
    print("\n[1] ObsidianBridge mode selection")
    with tempfile.TemporaryDirectory() as tmp:
        bridge = _make_bridge(Path(tmp))
        check(bridge.health_check(), "bridge is healthy in filesystem mode")
        check(bridge.mode == ObsidianMode.FILESYSTEM, f"mode = {bridge.mode}")
        snap = bridge.snapshot()
        check(snap["reachable"], "snapshot reports reachable")
        check(snap["mode"] == "filesystem", "snapshot.mode = filesystem")


# ─────────────────────────────────────────────────────────────────────────────
# 2. Basic note CRUD
# ─────────────────────────────────────────────────────────────────────────────


def test_note_crud():
    print("\n[2] write_note / read_note / append_note")
    with tempfile.TemporaryDirectory() as tmp:
        bridge = _make_bridge(Path(tmp))
        ok = bridge.write_note("hello.md", "# Hi\n\nFirst line.\n", overwrite=True)
        check(ok, "write_note returns True")

        note = bridge.read_note("hello.md")
        check(note is not None and "First line" in note.content, "read_note round-trip")

        ok2 = bridge.append_note("hello.md", "\n## Section two\n")
        check(ok2, "append_note returns True")
        note2 = bridge.read_note("hello.md")
        check(
            note2 is not None
            and "First line" in note2.content
            and "Section two" in note2.content,
            "appended content visible",
        )

        # Write into a nested folder
        bridge.write_note("folder1/nested/deep.md", "deep content", overwrite=True)
        deep = bridge.read_note("folder1/nested/deep.md")
        check(deep is not None and "deep content" in deep.content, "nested write")


# ─────────────────────────────────────────────────────────────────────────────
# 3. patch_section
# ─────────────────────────────────────────────────────────────────────────────


def test_patch_section():
    print("\n[3] patch_section (append / prepend / replace)")
    with tempfile.TemporaryDirectory() as tmp:
        bridge = _make_bridge(Path(tmp))
        bridge.write_note(
            "doc.md",
            "# Top\n\nsome intro\n\n# Notes\n\nold content\n",
            overwrite=True,
        )
        # append under Notes
        ok = bridge.patch_section("doc.md", "Notes", "appended line", operation="append")
        check(ok, "append returns True")
        note = bridge.read_note("doc.md")
        check("appended line" in note.content, "append under Notes visible")

        # replace under Notes
        bridge.patch_section("doc.md", "Notes", "REPLACED", operation="replace")
        note2 = bridge.read_note("doc.md")
        check("REPLACED" in note2.content, "replace visible")
        check("old content" not in note2.content, "replace removed old content")

        # patch_section on missing heading: creates the heading
        ok2 = bridge.patch_section("doc.md", "Brand New", "content x", operation="append")
        check(ok2, "missing heading creates the section")
        note3 = bridge.read_note("doc.md")
        check("# Brand New" in note3.content, "new heading added")


# ─────────────────────────────────────────────────────────────────────────────
# 4. Search + list
# ─────────────────────────────────────────────────────────────────────────────


def test_search_and_list():
    print("\n[4] search + list_notes")
    with tempfile.TemporaryDirectory() as tmp:
        bridge = _make_bridge(Path(tmp))
        bridge.write_note("a.md", "the golden ratio is phi", overwrite=True)
        bridge.write_note("sub/b.md", "queen sero watches", overwrite=True)

        results = bridge.search("golden")
        check(len(results) == 1, f"search 'golden' → {len(results)} result")
        check("a.md" in results[0]["filename"], "search hit path")

        listing = bridge.list_notes()
        check(any("a.md" in x for x in listing), "list_notes sees a.md")
        check(any("sub/b.md" in x for x in listing), "list_notes sees sub/b.md")


# ─────────────────────────────────────────────────────────────────────────────
# 5. Path safety
# ─────────────────────────────────────────────────────────────────────────────


def test_path_sanitisation():
    print("\n[5] path sanitisation")
    with tempfile.TemporaryDirectory() as tmp:
        bridge = _make_bridge(Path(tmp))
        # Traversal attempt
        ok = bridge.write_note("../escape.md", "sneaky", overwrite=True)
        check(ok, "traversal sanitised to safe path (still writes)")
        # File must be under the vault root — not in tmp's parent
        parent = Path(tmp).parent
        leaked = list(parent.glob("escape.md"))
        check(len(leaked) == 0, "nothing leaked out of the vault dir")


# ─────────────────────────────────────────────────────────────────────────────
# 6. Sink: on_utterance
# ─────────────────────────────────────────────────────────────────────────────


def _make_utterance(speaker: str, listener: str, text: str) -> Utterance:
    return Utterance(
        utterance_id="abcd1234",
        timestamp=time.time(),
        speaker=speaker,
        listener=listener,
        statement=VoiceStatement(
            voice=speaker,
            text=text,
            vault_fingerprint="fp1" * 8,
            prompt_used="prompt",
        ),
        response=VoiceStatement(
            voice=listener,
            text="thanks for that",
            vault_fingerprint="fp2" * 8,
            prompt_used="prompt",
        ),
        chosen=True,
        reasoning="test",
        urgency=0.8,
        vault_fingerprint_before="fp1" * 8,
        vault_fingerprint_after="fp2" * 8,
    )


def test_sink_on_utterance():
    print("\n[6] ObsidianSink.on_utterance writes daily + per-voice notes")
    with tempfile.TemporaryDirectory() as tmp:
        bridge = _make_bridge(Path(tmp))
        sink = ObsidianSink(bridge=bridge)

        u1 = _make_utterance("queen", "miner", "Λ(t) reads +0.870.")
        sink.on_utterance(u1)

        # Daily note exists
        daily = list(Path(tmp).glob("daily/*.md"))
        check(len(daily) == 1, f"daily journal created ({len(daily)})")
        check("queen" in daily[0].read_text(), "daily contains queen utterance")
        check("miner" in daily[0].read_text(), "daily contains listener")

        # Per-voice note exists
        voice_notes = list(Path(tmp).glob("voices/queen/*.md"))
        check(len(voice_notes) == 1, f"voices/queen/ note ({len(voice_notes)})")
        body = voice_notes[0].read_text()
        check("Λ(t)" in body, "voice note contains the statement text")
        check("aureon_voice: queen" in body, "frontmatter has voice tag")


def test_sink_on_tick_and_audit():
    print("\n[7] ObsidianSink.on_tick + on_audit")
    with tempfile.TemporaryDirectory() as tmp:
        bridge = _make_bridge(Path(tmp))
        sink = ObsidianSink(bridge=bridge)

        class FakeTick:
            def to_dict(self):
                return {
                    "cycle": 1,
                    "timestamp": time.time(),
                    "vault_size": 42,
                    "casimir_force": 0.001,
                    "auris_consensus": "BUY",
                    "auris_agreeing": 7,
                    "cells_deployed": 1,
                    "cells_success": 1,
                    "dominant_frequency_hz": 528,
                    "love_amplitude": 0.9,
                    "gratitude_score": 0.8,
                    "spoke": True,
                    "speaker": "queen",
                    "listener": "miner",
                    "utterance_preview": "Λ(t) rising",
                }

        sink.on_tick(FakeTick())
        loop_log = Path(tmp) / "loops" / "self_feedback_loop.md"
        check(loop_log.exists(), "loop log created")
        text = loop_log.read_text()
        check("cycle=1" in text, "tick line written")
        check("Λ(t) rising" in text, "utterance preview written")

        # on_audit
        audit_payload = {
            "audit_id": "audit_xxx",
            "passed": 3,
            "failed": 0,
            "results": [{"name": "x", "passed": True, "detail": "ok"}],
        }
        sink.on_audit(audit_payload)
        audit_log = Path(tmp) / "integrations" / "audit_trail.md"
        check(audit_log.exists(), "audit log created")
        check("audit_xxx" in audit_log.read_text(), "audit payload written")

        status = sink.get_status()
        check(status["ticks_written"] == 1, "ticks_written counter")
        check(status["audits_written"] == 1, "audits_written counter")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────


def main():
    test_mode_selection()
    test_note_crud()
    test_patch_section()
    test_search_and_list()
    test_path_sanitisation()
    test_sink_on_utterance()
    test_sink_on_tick_and_audit()

    print(f"\n{'═' * 60}")
    print(f"ObsidianBridge tests: {PASS} passed, {FAIL} failed")
    print(f"{'═' * 60}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
