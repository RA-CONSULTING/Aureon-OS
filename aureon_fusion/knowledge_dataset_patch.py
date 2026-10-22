"""KnowledgeDataset seam patches (upstream is read-only).

Applied idempotently to the upstream ``aureon.queen.knowledge_dataset``
class from every process that writes the queen's knowledge bank:

* ``absorb`` skips exact-text duplicates and tags cycle-telemetry rows as
  ``data_type='telemetry'`` at birth, so her heartbeat never accumulates
  as world knowledge.
* ``compact_self_telemetry()`` — one-shot boot digestion: purge historical
  exact duplicates, retag telemetry rows.
* ``save`` merges on write: several live writers (the queen's per-cycle
  reload, the learning will's cached instance, the wisdom store) each hold
  their own in-memory snapshot and save the whole JSON file. Last writer
  wins silently dropped fragments written between a writer's load and its
  save (observed live: count 1482 -> 1479 across one absorb). Every save
  now first folds in on-disk fragments whose text is absent from memory,
  so no writer can clobber another's entries.

All patches are fail-closed: any internal error falls back to the
original upstream behaviour.
"""

from __future__ import annotations

import json
import types

_APPLIED = False


def ensure_applied() -> bool:
    """Idempotently patch the upstream KnowledgeDataset class. Returns True
    when the patch is (now) active."""
    global _APPLIED
    if _APPLIED:
        return True
    try:
        from aureon.queen.knowledge_dataset import KnowledgeDataset as cls
    except Exception:
        return False
    if getattr(cls, "_aureon_dedupe_patched", False):
        _APPLIED = True
        return True

    _orig_absorb = cls.absorb

    def absorb_no_dupe(self, pocket, interpretations=None):
        try:
            with self._lock:
                existing = {f.text for f in self._fragments}
                before_idx = len(self._fragments)
            entries = [e for e in (getattr(pocket, "entries", []) or [])
                       if (getattr(e, "value", "") or "") not in existing]
            if not entries:
                return 0
            pocket = types.SimpleNamespace(
                goal_id=getattr(pocket, "goal_id", ""),
                owner=getattr(pocket, "owner", ""),
                entries=entries)
        except Exception:
            before_idx = None  # fall through to the original absorb
        added = _orig_absorb(self, pocket, interpretations=interpretations)
        if added and before_idx is not None:
            # Tag cycle-telemetry rows at birth so the fact bank never
            # accumulates her own heartbeat as world knowledge.
            try:
                touched = False
                with self._lock:
                    for frag in self._fragments[before_idx:]:
                        if frag.text.startswith("Metacognitive cycle ") and \
                                frag.data_type != "telemetry":
                            frag.data_type = "telemetry"
                            frag.category = "self_telemetry"
                            touched = True
                if touched:
                    self.save()
            except Exception:
                pass
        return added

    cls.absorb = absorb_no_dupe

    def compact_self_telemetry(self):
        """Dedupe exact-text fragments (keep first), retag cycle telemetry.
        Returns a stats dict; saves only if something changed."""
        removed = 0
        updated = 0
        with self._lock:
            seen = set()
            kept = []
            for frag in self._fragments:
                if frag.text in seen:
                    removed += 1
                    continue
                seen.add(frag.text)
                if frag.text.startswith("Metacognitive cycle ") and \
                        frag.data_type != "telemetry":
                    frag.data_type = "telemetry"
                    frag.category = "self_telemetry"
                    updated += 1
                kept.append(frag)
            self._fragments = kept
            self._tag_index.clear()
            for i, frag in enumerate(self._fragments):
                for tag in frag.tags:
                    self._tag_index[tag].append(i)
            if removed or updated:
                self.save()
        return {"duplicates_removed": removed,
                "telemetry_retagged": updated,
                "total_fragments": len(self._fragments)}

    cls.compact_self_telemetry = compact_self_telemetry

    _orig_save = cls.save

    def save_merging(self):
        try:
            from aureon.queen.knowledge_dataset import KnowledgeFragment
            with self._lock:
                have = {f.text for f in self._fragments}
                extra = []
                if self._path.exists():
                    disk = json.loads(
                        self._path.read_text(encoding="utf-8"))
                    for fd in disk.get("fragments", []):
                        t = (fd.get("text") or "")
                        if t and t not in have:
                            have.add(t)
                            extra.append(fd)
                for fd in extra:
                    frag = KnowledgeFragment.from_dict(fd)
                    self._fragments.append(frag)
                    idx = len(self._fragments) - 1
                    for tag in frag.tags:
                        self._tag_index[tag].append(idx)
        except Exception:
            pass  # never block a save on a merge failure
        return _orig_save(self)

    cls.save = save_merging
    cls._aureon_dedupe_patched = True
    _APPLIED = True
    return True
