"""
🕸️ AUREON CONNECTOME — the organism touches every part of itself.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The spine (aureon_organism_spine) already names every module in the body.
The baton (aureon_baton_link) already hears each one announce itself on import.
The mycelium and the Queen already hold the members that were wired by hand.

The Connectome closes the loop nothing else closes:

    enumerate → sense → touch → weave → pulse

  • sense(module)  — what the organism knows of a part without waking it:
                     manifest identity, baton heartbeat seen, already imported,
                     mesh membership, Queen childhood.
  • touch(module)  — wake the part: import it (ALWAYS under
                     AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS so the baton's
                     live-mode env flips can never fire from here) and feel its
                     shape — docstring, classes, functions, singleton doors.
  • weave(module)  — join the part into the living mesh via the operator's
                     join_organism (mycelium connect + Queen register).
  • sweep()        — progressively touch the untouched, batch by batch, so the
                     whole body is felt over time. Failures are counted and
                     remembered, never fatal. Some parts are deny-listed
                     (they run loops or open sockets at import) — the organism
                     knows OF them without waking them.
  • pulse()        — one breath: publish organism.connectome.pulse with honest
                     coverage (linked ≠ touched ≠ woven — all three reported).

State persists to state/organism_connectome.json so the body-map survives sleep.
"""

from __future__ import annotations

import importlib
import json
import logging
import os
import re
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger("aureon.core.connectome")

_REPO_ROOT = Path(__file__).resolve().parents[2]
_STATE_PATH = _REPO_ROOT / "state" / "organism_connectome.json"
_SUPPRESS_ENV = "AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS"

# Parts the sweep never wakes: they run loops, open sockets, spawn processes,
# or block at import. The organism knows OF them (sense) without touching.
_DENY_PATTERNS = (
    r"_daemon$", r"_launcher$", r"_server$", r"_app$", r"_live$", r"_runner$",
    r"^aureon\.autonomous\.aureon_master_launcher",
    r"^aureon\.core\.hnc_live_daemon",
    r"^aureon\.core\.integrated_cognitive_system",
    r"^aureon\.operator\.operator_server",
)
_DENY_RE = [re.compile(p) for p in _DENY_PATTERNS]


def _denied(module: str) -> bool:
    return any(rx.search(module) for rx in _DENY_RE)


class Connectome:
    """The registry of every part of the organism and how far each is wired."""

    def __init__(self, state_path: Path | None = None) -> None:
        self._state_path = state_path or _STATE_PATH
        self._lock = threading.RLock()
        self._manifest: Any = None                      # OrganismManifest, built lazily
        self._records: Dict[str, Dict[str, Any]] = {}   # module -> {status, ts, ...}
        self._linked: set[str] = set()                  # modules seen via baton.link
        self._sweep_thread: threading.Thread | None = None
        self._sweep_stop = threading.Event()
        self._load_state()
        self._subscribe_baton()

    # ── discovery ────────────────────────────────────────────────────────────

    def manifest(self) -> Any:
        with self._lock:
            if self._manifest is None:
                from aureon.core.aureon_organism_spine import build_organism_manifest

                self._manifest = build_organism_manifest(_REPO_ROOT)
                logger.info("🕸️ Connectome mapped %d nodes", len(self._manifest.nodes))
            return self._manifest

    def nodes(self, domain: str | None = None, status: str | None = None) -> List[Dict[str, Any]]:
        out = []
        for node in self.manifest().nodes:
            if domain and node.domain != domain:
                continue
            rec = self._records.get(node.module, {})
            node_status = rec.get("status", "linked" if node.module in self._linked else "unfelt")
            if status and node_status != status:
                continue
            out.append({**node.to_dict(), "status": node_status})
        return out

    # ── the baton ear: linked-module registry the bus never kept ─────────────

    def _subscribe_baton(self) -> None:
        try:
            from aureon.core.aureon_thought_bus import get_thought_bus

            bus = get_thought_bus()
            bus.subscribe("baton.link", self._on_baton)
            # Backfill from the ring buffer so restarts don't forget recent links.
            for thought in bus.recall("baton.link") or []:
                self._on_baton(thought)
        except Exception as exc:  # noqa: BLE001 — the ear is optional
            logger.debug("baton subscription unavailable: %s", exc)

    def _on_baton(self, thought: Any) -> None:
        try:
            # The baton heartbeat carries the module name under ``payload`` (the
            # live Thought) or a nested ``payload``/top-level dict (recall's
            # to_json form). Read all shapes so the 570 baton pings actually
            # register — historically this read a ``content`` field that the
            # Thought dataclass does not have, so baton_linked stayed at 0.
            if isinstance(thought, dict):
                payload = thought.get("payload", thought)
            else:
                payload = getattr(thought, "payload", None) or {}
            module = str(payload.get("module", "") or "") if isinstance(payload, dict) else ""
            if module:
                with self._lock:
                    self._linked.add(module)
        except Exception:  # noqa: BLE001
            pass

    # ── sense: know a part without waking it ─────────────────────────────────

    def sense(self, module: str) -> Dict[str, Any]:
        node = self.manifest().by_module().get(module)
        rec = self._records.get(module, {})
        mesh_member = False
        queen_child = False
        try:
            from aureon.core.aureon_mycelium import get_mycelium

            status = get_mycelium().get_mesh_status()
            # connected_systems is a list of dicts ({name, connected_at, ...}) —
            # extract the names before the membership test (a raw string-in-list
            # check against dicts is always False).
            connected = status.get("connected_systems") or []
            names = {
                (c.get("name") if isinstance(c, dict) else str(c))
                for c in connected
            }
            mesh_member = module.rsplit(".", 1)[-1] in names
        except Exception:  # noqa: BLE001
            pass
        return {
            "module": module,
            "known": node is not None,
            "node": node.to_dict() if node else None,
            "status": rec.get("status", "linked" if module in self._linked else "unfelt"),
            "baton_linked": module in self._linked,
            "imported": module in sys.modules,
            "mesh_member": mesh_member,
            "queen_child": queen_child,
            "last_touch": rec.get("ts"),
            "error": rec.get("error"),
        }

    # ── touch: wake a part and feel its shape ────────────────────────────────

    def touch(self, module: str) -> Dict[str, Any]:
        node = self.manifest().by_module().get(module)
        if node is None:
            return {"module": module, "status": "unknown", "error": "not in the organism manifest"}
        if _denied(module):
            self._record(module, "denied")
            return {"module": module, "status": "denied",
                    "reason": "runs loops/sockets at import — sensed, not woken"}

        prior = os.environ.get(_SUPPRESS_ENV)
        os.environ[_SUPPRESS_ENV] = "1"   # the baton's live-mode env flips must never fire from here
        try:
            mod = importlib.import_module(module)
        except KeyboardInterrupt:
            raise  # operator Ctrl-C still works
        except BaseException as exc:  # noqa: BLE001 — a rogue module's sys.exit()/
            # SystemExit at import must not kill the sweep, the daemon, or the
            # audit. A failed touch is data, not death — catch even BaseException
            # (except KeyboardInterrupt) so one misbehaving module can't take the
            # whole organism sweep down.
            self._record(module, "failed", error=f"{type(exc).__name__}: {exc}"[:300])
            return {"module": module, "status": "failed", "error": f"{type(exc).__name__}: {exc}"[:300]}
        finally:
            if prior is None:
                os.environ.pop(_SUPPRESS_ENV, None)
            else:
                os.environ[_SUPPRESS_ENV] = prior

        shape = self._feel(mod)
        self._record(module, "touched", **{k: shape[k] for k in ("classes", "functions", "singletons")})
        return {"module": module, "status": "touched", **shape}

    def _feel(self, mod: Any) -> Dict[str, Any]:
        classes, functions, singletons = [], [], []
        for name in dir(mod):
            if name.startswith("_"):
                continue
            try:
                obj = getattr(mod, name)
            except Exception:  # noqa: BLE001
                continue
            if isinstance(obj, type) and getattr(obj, "__module__", "") == mod.__name__:
                classes.append(name)
            elif callable(obj) and getattr(obj, "__module__", "") == mod.__name__:
                (singletons if name.startswith("get_") else functions).append(name)
        doc = (mod.__doc__ or "").strip().splitlines()
        return {
            "doc": doc[0][:200] if doc else "",
            "classes": classes[:40],
            "functions": functions[:40],
            "singletons": singletons[:20],
        }

    # ── weave: join a part into the living mesh ──────────────────────────────

    def weave(self, module: str) -> Dict[str, Any]:
        touched = self.touch(module)
        if touched["status"] not in ("touched",):
            return touched
        try:
            from aureon.operator.aureon_operator import join_organism

            mod = sys.modules[module]
            node = self.manifest().by_module()[module]
            join_organism(mod, node.id)
            self._record(module, "woven")
            return {"module": module, "status": "woven", "node": node.id}
        except Exception as exc:  # noqa: BLE001
            self._record(module, "touched", error=f"weave failed: {exc}"[:300])
            return {"module": module, "status": "touched", "error": f"weave failed: {exc}"[:300]}

    # ── sweep: feel the whole body, batch by batch ───────────────────────────

    def sweep_once(
        self,
        batch_size: int = 25,
        domains: List[str] | None = None,
        weave_batch: int = 0,
    ) -> Dict[str, Any]:
        touched = failed = denied = 0
        for node in self.manifest().nodes:
            if touched + failed + denied >= batch_size:
                break
            if domains and node.domain not in domains:
                continue
            rec = self._records.get(node.module)
            if rec is not None:      # already felt (touched/failed/denied/woven)
                continue
            result = self.touch(node.module)
            if result["status"] == "touched":
                touched += 1
            elif result["status"] == "denied":
                denied += 1
            else:
                failed += 1
        # Graduate touched modules to woven — join them onto the mycelium mesh +
        # Queen so the organism is genuinely one body, not just felt. weave()
        # only ever acts on already-touched modules (denied/failed are skipped),
        # so the deny-list + import-suppression are honoured transitively. This
        # is how the Queen's own systems (queen_*.py) become real children over
        # time, using the existing join_organism gear — no new fabric.
        woven = 0
        if weave_batch > 0:
            for module, rec in list(self._records.items()):
                if woven >= weave_batch:
                    break
                if rec.get("status") == "touched" and self.weave(module).get("status") == "woven":
                    woven += 1
        self._save_state()
        return {"touched": touched, "failed": failed, "denied": denied, "woven": woven}

    def start_sweep(self, interval_s: float = 30.0, batch_size: int = 25, weave_batch: int = 0) -> None:
        if self._sweep_thread is not None and self._sweep_thread.is_alive():
            return
        self._sweep_stop.clear()

        def _run() -> None:
            while not self._sweep_stop.wait(interval_s):
                try:
                    result = self.sweep_once(batch_size=batch_size, weave_batch=weave_batch)
                    self.pulse()
                    if not any(result.values()):
                        logger.info("🕸️ Connectome sweep complete — the whole body has been felt and woven")
                        return
                except Exception as exc:  # noqa: BLE001 — the sweep must never die
                    logger.warning("connectome sweep error: %s", exc)

        self._sweep_thread = threading.Thread(target=_run, name="aureon-connectome-sweep", daemon=True)
        self._sweep_thread.start()

    def stop_sweep(self) -> None:
        self._sweep_stop.set()

    # ── pulse: one breath of honest coverage ─────────────────────────────────

    def status(self) -> Dict[str, Any]:
        with self._lock:
            total = len(self.manifest().nodes)
            by_status: Dict[str, int] = {}
            for rec in self._records.values():
                by_status[rec.get("status", "unknown")] = by_status.get(rec.get("status", "unknown"), 0) + 1
            touched = by_status.get("touched", 0) + by_status.get("woven", 0)
            return {
                "nodes": total,
                "baton_linked": len(self._linked),
                "touched": touched,
                "woven": by_status.get("woven", 0),
                "failed": by_status.get("failed", 0),
                "denied": by_status.get("denied", 0),
                "unfelt": max(0, total - len(self._records)),
                "coverage_pct": round(100.0 * touched / total, 2) if total else 0.0,
                "note": "linked = import heartbeat heard · touched = imported+felt · "
                        "woven = joined to mycelium+Queen. Three different depths, all honest.",
            }

    def pulse(self) -> Dict[str, Any]:
        snapshot = self.status()
        try:
            from aureon.core.aureon_thought_bus import Thought, get_thought_bus

            get_thought_bus().publish(Thought(
                topic="organism.connectome.pulse",
                source="aureon_connectome",
                payload=snapshot,
            ))
        except Exception as exc:  # noqa: BLE001 — a silent breath is still a breath
            logger.debug("pulse publish unavailable: %s", exc)
        return snapshot

    # ── persistence ──────────────────────────────────────────────────────────

    def _record(self, module: str, status: str, **extra: Any) -> None:
        with self._lock:
            self._records[module] = {"status": status, "ts": time.time(), **extra}

    def _load_state(self) -> None:
        try:
            if self._state_path.exists():
                data = json.loads(self._state_path.read_text(encoding="utf-8"))
                self._records = dict(data.get("records", {}))
                self._linked = set(data.get("linked", []))
        except Exception as exc:  # noqa: BLE001
            logger.debug("connectome state load failed: %s", exc)

    def _save_state(self) -> None:
        try:
            with self._lock:
                payload = {"saved_at": time.time(), "records": self._records,
                           "linked": sorted(self._linked)}
            self._state_path.parent.mkdir(parents=True, exist_ok=True)
            self._state_path.write_text(json.dumps(payload, indent=1), encoding="utf-8")
        except Exception as exc:  # noqa: BLE001
            logger.debug("connectome state save failed: %s", exc)


# ── singleton ─────────────────────────────────────────────────────────────────

_instance: Connectome | None = None
_instance_lock = threading.Lock()


def get_connectome() -> Connectome:
    global _instance
    with _instance_lock:
        if _instance is None:
            _instance = Connectome()
        return _instance


def reset_connectome_for_tests() -> None:
    global _instance
    with _instance_lock:
        if _instance is not None:
            _instance.stop_sweep()
        _instance = None


__all__ = ["Connectome", "get_connectome", "reset_connectome_for_tests"]
