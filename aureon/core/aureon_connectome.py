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

# Parts the sweep never wakes: they run loops, open sockets, spawn processes, or
# block at import. Denial is a fast-path for KNOWN loopers/hangers — the real
# protection is the timeout-guarded touch (behaviour decides, not a name). The broad
# name suffixes (_live/_runner/_app) were dropped: probing showed ~26 of them import
# fine and were denied purely for their name — costing honest reachable coverage.
_DENY_PATTERNS = (
    r"_daemon$", r"_launcher$", r"_server$",
    r"^aureon\.autonomous\.aureon_master_launcher",
    r"^aureon\.core\.hnc_live_daemon",
    r"^aureon\.core\.integrated_cognitive_system",
    r"^aureon\.operator\.operator_server",
)
_DENY_RE = [re.compile(p) for p in _DENY_PATTERNS]

# Known modules that do a blocking/network import at MODULE TOP LEVEL (not under a
# __main__ guard), so they hang the import itself. Fast-path-denied so the sweep
# doesn't pay the touch timeout for them; the timeout guard backstops any missed.
_DENY_EXPLICIT = frozenset({
    "aureon.trading.aureon_unified_live",
    "aureon.simulation.aureon_multiverse_live",
})


def _denied(module: str) -> bool:
    return module in _DENY_EXPLICIT or any(rx.search(module) for rx in _DENY_RE)


_PATHS_READY = False


def _ensure_import_paths() -> None:
    """Activate the repo's own ``sys.path`` shim ONCE so intra-repo bare-name imports
    (``import binance_client``) resolve during touch — exactly as they do when an app
    entry point runs. Only mutates ``sys.path``; imports nothing heavy. Guarded — a
    missing shim is never fatal. Without it, ~half the touch failures are spurious
    ``ModuleNotFoundError``s for modules that live in the repo."""
    global _PATHS_READY
    if _PATHS_READY:
        return
    _PATHS_READY = True
    try:
        import aureon._path_setup  # noqa: F401 — side effect: sys.path population
    except Exception as exc:  # noqa: BLE001
        logger.debug("import-path shim unavailable: %s", exc)


def _max_retry() -> int:
    """How many times a failed module is re-attempted before it settles (so a
    genuinely-broken module never churns every cycle). Env ``AUREON_CONNECTOME_MAX_RETRY``."""
    try:
        return max(0, int(os.environ.get("AUREON_CONNECTOME_MAX_RETRY", "") or 3))
    except (TypeError, ValueError):
        return 3


def _retry_batch() -> int:
    """How many failed modules the sweep re-attempts per cycle (bounded self-heal).
    Env ``AUREON_CONNECTOME_RETRY_BATCH``; 0 = off (sweep byte-identical to before)."""
    try:
        return max(0, int(os.environ.get("AUREON_CONNECTOME_RETRY_BATCH", "") or 5))
    except (TypeError, ValueError):
        return 5


def _touch_timeout() -> float:
    """Seconds a single import may take before touch treats it as a hanger and moves
    on — so no misbehaving module can freeze the sweep, and behaviour (not a name)
    decides what is un-touchable. Env ``AUREON_CONNECTOME_TOUCH_TIMEOUT``; 0 = off
    (synchronous import, old behaviour)."""
    try:
        return max(0.0, float(os.environ.get("AUREON_CONNECTOME_TOUCH_TIMEOUT", "") or 10.0))
    except (TypeError, ValueError):
        return 10.0


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
        _ensure_import_paths()   # heal the import context so intra-repo imports resolve
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
            mod, err = self._import_guarded(module, _touch_timeout())
        finally:
            if prior is None:
                os.environ.pop(_SUPPRESS_ENV, None)
            else:
                os.environ[_SUPPRESS_ENV] = prior

        if err is not None:
            # A failed touch is data, not death — a rogue module's sys.exit(), a
            # missing dep, or a hang (timed out) is recorded and the sweep moves on.
            self._record(module, "failed", error=err)
            return {"module": module, "status": "failed", "error": err}

        shape = self._feel(mod)
        self._record(module, "touched", **{k: shape[k] for k in ("classes", "functions", "singletons")})
        return {"module": module, "status": "touched", **shape}

    def _import_guarded(self, module: str, timeout: float) -> tuple[Any, str | None]:
        """Import ``module`` behaviourally hang-safe: if the import takes longer than
        ``timeout`` seconds it is treated as a hanger (recorded ``failed``, the sweep
        moves on — never blocked). Returns ``(mod_or_None, error_or_None)``. A rogue
        ``sys.exit()`` / missing dep is captured as an error (never raised). ``timeout
        <= 0`` → synchronous import (old behaviour). Operator Ctrl-C still interrupts."""
        if timeout <= 0:
            try:
                return importlib.import_module(module), None
            except KeyboardInterrupt:
                raise
            except BaseException as exc:  # noqa: BLE001
                return None, f"{type(exc).__name__}: {exc}"[:300]
        box: Dict[str, Any] = {}

        def _work() -> None:
            try:
                box["mod"] = importlib.import_module(module)
            except BaseException as exc:  # noqa: BLE001 — capture, never crash the worker
                box["err"] = f"{type(exc).__name__}: {exc}"[:300]

        t = threading.Thread(target=_work, name=f"connectome-touch-{module}"[:60], daemon=True)
        t.start()
        t.join(timeout)   # Ctrl-C on the main thread interrupts the join and propagates
        if t.is_alive():
            return None, f"import exceeded {timeout:g}s — treated as a hanger"
        if "mod" in box:
            return box["mod"], None
        return None, box.get("err", "import failed")

    def _feel(self, mod: Any) -> Dict[str, Any]:
        classes: List[str] = []
        functions: List[str] = []
        singletons: List[str] = []
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

    def weave_touched(self, limit: int | None = None) -> Dict[str, Any]:
        """Drain the currently-touched backlog onto the mycelium mesh + Queen in one
        bounded pass, so ``woven`` keeps pace with what the organism has already felt.
        Registration only (via ``join_organism`` — no module code runs), **idempotent**
        (a woven module is skipped, so a second pass is a no-op), bounded by ``limit``
        (``None`` = all), guarded — one bad module never stops the drain. Returns
        ``{"woven": n, "remaining": m}`` (m = touched still awaiting a weave)."""
        woven = 0
        pending = [m for m, rec in self._records.items() if rec.get("status") == "touched"]
        for module in pending:
            if limit is not None and woven >= limit:
                break
            try:
                if self.weave(module).get("status") == "woven":
                    woven += 1
            except Exception as exc:  # noqa: BLE001 — never let one module stop the drain
                logger.debug("weave_touched skipped %s: %s", module, exc)
        remaining = sum(1 for rec in self._records.values() if rec.get("status") == "touched")
        if woven:
            self._save_state()
        return {"woven": woven, "remaining": remaining}

    def retry_failed(self, limit: int | None = None) -> Dict[str, Any]:
        """A failure is not forever. Re-attempt latched ``failed`` modules — the import
        context is healed first (``touch`` activates the shim), so intra-repo imports
        that were spurious ``ModuleNotFoundError``s now resolve. A recovered module
        becomes ``touched`` (and weaves onward next drain); a still-broken one keeps an
        ``attempts`` counter and **settles** after ``AUREON_CONNECTOME_MAX_RETRY`` so it
        never churns every cycle. Bounded by ``limit`` (``None`` = all eligible),
        guarded, saves once. Returns ``{retried, recovered, still_failed}``."""
        cap = _max_retry()
        eligible = [m for m, rec in list(self._records.items())
                    if rec.get("status") == "failed" and int(rec.get("attempts", 0) or 0) < cap]
        retried = recovered = 0
        for module in eligible:
            if limit is not None and retried >= limit:
                break
            prev = int(self._records.get(module, {}).get("attempts", 0) or 0)
            try:
                res = self.touch(module)          # re-imports; overwrites the record
            except Exception as exc:  # noqa: BLE001 — one module never stops the retry
                logger.debug("retry_failed skipped %s: %s", module, exc)
                continue
            retried += 1
            if res.get("status") == "touched":
                recovered += 1
            else:
                rec = self._records.get(module)   # re-failed → preserve the attempt count
                if rec is not None:
                    rec["attempts"] = prev + 1
        if retried:
            self._save_state()
        still = sum(1 for rec in self._records.values() if rec.get("status") == "failed")
        return {"retried": retried, "recovered": recovered, "still_failed": still}

    def reconcile_denied(self, limit: int | None = None) -> Dict[str, Any]:
        """A denial is not forever either. When the deny-list narrows (or a module is
        renamed), a module recorded ``denied`` under the OLD gate stays frozen — the
        sweep skips any recorded module, so it never re-touches even though it is now
        allowed. This clears the record for every ``denied`` module that the CURRENT
        ``_denied()`` no longer matches, so the sweep re-touches it (behaviour, via the
        timeout-guarded touch, then decides — weave / fail / re-deny). Bounded by
        ``limit``, guarded, saves once. Returns ``{re_evaluated, freed, still_denied}``."""
        stale = [m for m, rec in list(self._records.items())
                 if rec.get("status") == "denied" and not _denied(m)]
        freed = 0
        for module in stale:
            if limit is not None and freed >= limit:
                break
            with self._lock:
                self._records.pop(module, None)   # → unfelt; the sweep/touch re-attempts it
            freed += 1
        if freed:
            self._save_state()
        still = sum(1 for rec in self._records.values() if rec.get("status") == "denied")
        return {"re_evaluated": len(stale), "freed": freed, "still_denied": still}

    # ── sweep: feel the whole body, batch by batch ───────────────────────────

    def sweep_once(
        self,
        batch_size: int = 25,
        domains: List[str] | None = None,
        weave_batch: int = 0,
        retry_batch: int | None = None,
    ) -> Dict[str, Any]:
        # Re-evaluate stale denials first: if the deny-list has narrowed, free the
        # now-allowed modules back to unfelt so this cycle's touch loop re-attempts them.
        freed = self.reconcile_denied().get("freed", 0)
        # A bounded, attempt-capped self-heal: re-attempt a few latched failures each
        # cycle so recoverable ones (e.g. a dep that has since arrived) rejoin the body.
        # retry_batch None → env default; 0 → off (sweep byte-identical to before).
        rb = _retry_batch() if retry_batch is None else max(0, retry_batch)
        recovered = self.retry_failed(limit=rb).get("recovered", 0) if rb else 0
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
        # weave_batch > 0 caps at N per cycle; < 0 drains ALL touched (keep-pace);
        # 0 weaves none. Keep-pace mode lets woven track touched cycle for cycle.
        woven = 0
        if weave_batch != 0:
            for module, rec in list(self._records.items()):
                if weave_batch > 0 and woven >= weave_batch:
                    break
                if rec.get("status") == "touched" and self.weave(module).get("status") == "woven":
                    woven += 1
        self._save_state()
        return {"touched": touched, "failed": failed, "denied": denied,
                "woven": woven, "recovered": recovered, "freed": freed}

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
            cap = _max_retry()
            by_status: Dict[str, int] = {}
            retryable = 0
            for rec in self._records.values():
                st = rec.get("status", "unknown")
                by_status[st] = by_status.get(st, 0) + 1
                if st == "failed" and int(rec.get("attempts", 0) or 0) < cap:
                    retryable += 1
            touched = by_status.get("touched", 0) + by_status.get("woven", 0)
            return {
                "nodes": total,
                "baton_linked": len(self._linked),
                "touched": touched,
                "woven": by_status.get("woven", 0),
                "failed": by_status.get("failed", 0),
                "retryable": retryable,      # failed but not yet settled — still self-healing
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
