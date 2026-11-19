#!/usr/bin/env python3
"""
CognitiveDashboard -- Rich-based Terminal UI for the Integrated Cognitive System

Subscribes to ThoughtBus topics and renders a 6-panel live dashboard showing
all cognitive layers: BODY (Agent), MIND (Cortex), SOURCE (Lambda),
SOUL (Being), HNC COMBUSTION, plus an internal monologue stream and
goal progress tracker.

Pure consumer: never calls subsystem methods directly, only reads ThoughtBus
events. Falls back to ANSI escape codes if Rich is unavailable.
"""

from __future__ import annotations

import logging
import threading
import time
from collections import deque
from typing import Any, Deque, Dict, List, Optional

from aureon.core.lambda_reading import lambda_reading

logger = logging.getLogger("aureon.core.dashboard")


def source_lambda_text(src: Any) -> str:
    """Dashboard Lambda(t). A missing key is ``no reading``, not 0.0000."""
    if not isinstance(src, dict) or "lambda_t" not in src:
        return "no reading"
    number = lambda_reading(src["lambda_t"])
    if number is None:
        return "no reading"
    sign = "+" if number >= 0 else ""
    return f"{sign}{number:.4f}"

# ---------------------------------------------------------------------------
# Rich imports (graceful degradation)
# ---------------------------------------------------------------------------
try:
    from rich.live import Live
    from rich.layout import Layout
    from rich.panel import Panel
    from rich.table import Table
    from rich.console import Console
    from rich.text import Text
    from rich.box import ROUNDED, HEAVY
    from rich.align import Align
    from rich.style import Style
    _HAS_RICH = True
except ImportError:
    _HAS_RICH = False

# ---------------------------------------------------------------------------
# ThoughtBus import
# ---------------------------------------------------------------------------
try:
    from aureon.core.aureon_thought_bus import get_thought_bus
    _HAS_THOUGHT_BUS = True
except Exception:
    get_thought_bus = None  # type: ignore[assignment]
    _HAS_THOUGHT_BUS = False


# ═══════════════════════════════════════════════════════════════════════════════
# ANSI FALLBACK (when Rich is not available)
# ═══════════════════════════════════════════════════════════════════════════════

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
MAGENTA = "\033[35m"
BLUE = "\033[34m"
WHITE = "\033[97m"


def _ansi_bar(val: float, width: int = 5) -> str:
    n = max(0, min(width, int(val * width)))
    return "|" * n + " " * (width - n)


# ═══════════════════════════════════════════════════════════════════════════════
# STATE CONTAINERS (updated by ThoughtBus subscribers)
# ═══════════════════════════════════════════════════════════════════════════════

class _DashboardState:
    """Thread-safe mutable state container for the dashboard."""

    def __init__(self) -> None:
        self._lock = threading.Lock()

        # BODY (Agent)
        self.body: Dict[str, Any] = {
            "tools": 0, "vm_sessions": 0, "actions": 0, "last_action": "",
        }

        # MIND (Cortex)
        self.mind: Dict[str, Any] = {
            "delta": 0.0, "theta": 0.0, "alpha": 0.0, "beta": 0.0, "gamma": 0.0,
        }

        # SOURCE (Lambda)
        self.source: Dict[str, Any] = {
            "lambda_t": None, "coherence_gamma": 0.0, "consciousness_psi": 0.0,
            "consciousness_level": "DORMANT", "symbolic_life_score": 0.0,
        }

        # SOUL (Being)
        self.soul: Dict[str, Any] = {
            "consciousness_level": "", "consciousness_psi": 0.0,
            "purpose": "", "objective": "", "symbolic_life_score": 0.0,
        }

        # HNC COMBUSTION
        self.hnc: Dict[str, Any] = {
            "auris_consensus": "NEUTRAL", "auris_confidence": 0.0,
            "auris_agreeing": 0, "auris_total": 9,
            "lighthouse_cleared": False,
            "cells_deployed": 0, "cells_success": 0,
            "plasticity_avg": 0.0,
            "composite_coherence": 0.0,
        }

        # Monologue stream (most recent lines)
        self.monologue: Deque[Dict[str, str]] = deque(maxlen=8)

        # Goal progress
        self.goal: Dict[str, Any] = {
            "text": "", "status": "", "total_steps": 0,
            "steps": [],  # list of {title, status, coherence}
        }

        # Meta
        self.boot_time: float = time.time()
        self.cycle: int = 0
        self.bus_rate: float = 0.0  # messages/sec estimate
        self._msg_count: int = 0
        self._rate_window_start: float = time.time()

    def update(self, section: str, data: Dict[str, Any]) -> None:
        with self._lock:
            target = getattr(self, section, None)
            if isinstance(target, dict):
                target.update(data)

    def add_monologue(self, source: str, text: str) -> None:
        with self._lock:
            self.monologue.append({"source": source, "text": text})

    def update_goal(self, data: Dict[str, Any]) -> None:
        with self._lock:
            self.goal.update(data)

    def tick_message(self) -> None:
        with self._lock:
            self._msg_count += 1
            elapsed = time.time() - self._rate_window_start
            if elapsed >= 5.0:
                self.bus_rate = self._msg_count / elapsed
                self._msg_count = 0
                self._rate_window_start = time.time()

    def increment_cycle(self) -> None:
        with self._lock:
            self.cycle += 1

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "body": dict(self.body),
                "mind": dict(self.mind),
                "source": dict(self.source),
                "soul": dict(self.soul),
                "hnc": dict(self.hnc),
                "monologue": list(self.monologue),
                "goal": dict(self.goal),
                "uptime": time.time() - self.boot_time,
                "cycle": self.cycle,
                "bus_rate": self.bus_rate,
            }


# ═══════════════════════════════════════════════════════════════════════════════
# COGNITIVE DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════

class CognitiveDashboard:
    """
    Rich-based live terminal dashboard for the Integrated Cognitive System.

    Subscribes to ThoughtBus topics and renders at ~2Hz. Pure consumer --
    never calls subsystem methods directly.
    """

    def __init__(self, thought_bus: Any = None) -> None:
        self._state = _DashboardState()
        self._thought_bus = thought_bus
        self._running = False
        self._thread: Optional[threading.Thread] = None

        if self._thought_bus is None and _HAS_THOUGHT_BUS:
            try:
                self._thought_bus = get_thought_bus()
            except Exception:
                pass

        self._subscribe()

    # ------------------------------------------------------------------
    # ThoughtBus subscriptions
    # ------------------------------------------------------------------
    def _subscribe(self) -> None:
        if self._thought_bus is None:
            return

        bus = self._thought_bus
        bus.subscribe("ics.body.state", self._on_body)
        bus.subscribe("ics.mind.state", self._on_mind)
        bus.subscribe("ics.source.state", self._on_source)
        bus.subscribe("ics.soul.state", self._on_soul)
        bus.subscribe("ics.hnc.state", self._on_hnc)
        bus.subscribe("ics.monologue", self._on_monologue)
        bus.subscribe("ics.boot.progress", self._on_boot)
        bus.subscribe("goal.*", self._on_goal)

    def _on_body(self, thought: Any) -> None:
        self._state.tick_message()
        p = thought.payload if hasattr(thought, "payload") else {}
        self._state.update("body", p)

    def _on_mind(self, thought: Any) -> None:
        self._state.tick_message()
        p = thought.payload if hasattr(thought, "payload") else {}
        self._state.update("mind", p)

    def _on_source(self, thought: Any) -> None:
        self._state.tick_message()
        p = thought.payload if hasattr(thought, "payload") else {}
        self._state.update("source", p)

    def _on_soul(self, thought: Any) -> None:
        self._state.tick_message()
        p = thought.payload if hasattr(thought, "payload") else {}
        self._state.update("soul", p)

    def _on_hnc(self, thought: Any) -> None:
        self._state.tick_message()
        p = thought.payload if hasattr(thought, "payload") else {}
        self._state.update("hnc", p)

    def _on_monologue(self, thought: Any) -> None:
        self._state.tick_message()
        p = thought.payload if hasattr(thought, "payload") else {}
        source = p.get("source", "system")
        text = p.get("text", "")
        if text:
            self._state.add_monologue(source, text)

    def _on_boot(self, thought: Any) -> None:
        self._state.tick_message()
        p = thought.payload if hasattr(thought, "payload") else {}
        name = p.get("subsystem", "unknown")
        status = p.get("status", "unknown")
        self._state.add_monologue("boot", f"{name}: {status}")

    def _on_goal(self, thought: Any) -> None:
        self._state.tick_message()
        p = thought.payload if hasattr(thought, "payload") else {}
        topic = thought.topic if hasattr(thought, "topic") else ""

        if topic == "goal.submitted":
            self._state.update_goal({
                "text": p.get("text", ""),
                "status": "submitted",
            })
        elif topic == "goal.decomposed":
            steps = p.get("steps", [])
            self._state.update_goal({
                "total_steps": len(steps),
                "steps": [{"title": s.get("title", ""), "status": "pending", "coherence": 0.0} for s in steps],
                "status": "active",
            })
        elif topic == "goal.step.starting":
            idx = p.get("step_index", 0)
            steps = self._state.goal.get("steps", [])
            if 0 <= idx < len(steps):
                steps[idx]["status"] = "active"
            self._state.update_goal({"steps": steps})
        elif topic == "goal.step.completed":
            step_id = p.get("step_id", "")
            coherence = p.get("coherence", 0.0)
            steps = self._state.goal.get("steps", [])
            for s in steps:
                if s.get("status") == "active":
                    s["status"] = "completed"
                    s["coherence"] = coherence
                    break
            self._state.update_goal({"steps": steps})
        elif topic == "goal.step.failed":
            steps = self._state.goal.get("steps", [])
            for s in steps:
                if s.get("status") == "active":
                    s["status"] = "failed"
                    break
            self._state.update_goal({"steps": steps})
        elif topic == "goal.completed":
            self._state.update_goal({"status": "completed"})
        elif topic == "goal.failed":
            self._state.update_goal({"status": "failed"})

    # ------------------------------------------------------------------
    # Rich rendering
    # ------------------------------------------------------------------
    def _make_layout(self) -> Layout:
        layout = Layout(name="root")
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="upper", size=8),
            Layout(name="lower", size=7),
            Layout(name="monologue", size=6),
            Layout(name="goal", size=7),
        )
        layout["upper"].split_row(
            Layout(name="body"),
            Layout(name="mind"),
            Layout(name="source"),
        )
        layout["lower"].split_row(
            Layout(name="soul"),
            Layout(name="hnc"),
        )
        return layout

    def _render(self, snap: Dict[str, Any]) -> Layout:
        layout = self._make_layout()

        uptime_s = snap["uptime"]
        h, rem = divmod(int(uptime_s), 3600)
        m, s = divmod(rem, 60)
        uptime_str = f"{h:02d}:{m:02d}:{s:02d}"

        # Header
        header_text = Text()
        header_text.append("  AUREON INTEGRATED COGNITIVE SYSTEM", style="bold cyan")
        header_text.append(f"    Uptime: {uptime_str}", style="dim")
        header_text.append(f"  Cycle: {snap['cycle']}", style="dim")
        header_text.append(f"  Bus: {snap['bus_rate']:.0f}/s", style="dim")
        layout["header"].update(Panel(header_text, style="cyan"))

        # BODY panel
        b = snap["body"]
        body_table = Table.grid(padding=(0, 1))
        body_table.add_row("Tools:", str(b.get("tools", 0)))
        body_table.add_row("Actions:", str(b.get("actions", 0)))
        body_table.add_row("VMs:", str(b.get("vm_sessions", 0)))
        last = b.get("last_action", "") or ""
        body_table.add_row("Last:", last[:18])
        layout["body"].update(Panel(body_table, title="BODY (Agent)", border_style="green"))

        # MIND panel
        mi = snap["mind"]
        mind_table = Table.grid(padding=(0, 1))
        for band in ("delta", "theta", "alpha", "beta", "gamma"):
            val = mi.get(band, 0.0)
            if isinstance(val, dict):
                val = val.get("amplitude", 0.0) if isinstance(val, dict) else 0.0
            bar_str = _ansi_bar(float(val), 5)
            mind_table.add_row(
                Text(f"{band.capitalize():>7}:", style="bold"),
                Text(bar_str, style="yellow"),
                Text(f"{float(val):.2f}", style="dim"),
            )
        layout["mind"].update(Panel(mind_table, title="MIND (Cortex)", border_style="magenta"))

        # SOURCE panel
        src = snap["source"]
        source_table = Table.grid(padding=(0, 1))
        source_table.add_row("Lambda(t):", source_lambda_text(src))
        source_table.add_row("Gamma:", f"{src.get('coherence_gamma', 0.0):.3f}")
        source_table.add_row("Psi:", f"{src.get('consciousness_psi', 0.0):.3f}")
        source_table.add_row("Level:", str(src.get("consciousness_level", "DORMANT")))
        source_table.add_row("SymLife:", f"{src.get('symbolic_life_score', 0.0):.3f}")
        layout["source"].update(Panel(source_table, title="SOURCE (Lambda)", border_style="yellow"))

        # SOUL panel
        so = snap["soul"]
        soul_table = Table.grid(padding=(0, 1))
        soul_level = so.get("consciousness_level", "") or src.get("consciousness_level", "")
        soul_psi = so.get("consciousness_psi", 0.0)
        soul_table.add_row("Level:", f"{soul_level} psi={soul_psi:.2f}")
        purpose = so.get("purpose", "") or so.get("sacred_purpose", "")
        soul_table.add_row("Purpose:", (purpose[:30] + "...") if len(purpose) > 30 else purpose)
        objective = so.get("objective", "") or so.get("active_objective", "")
        soul_table.add_row("Objective:", (objective[:30] + "...") if len(objective) > 30 else objective)
        soul_table.add_row("SymLife:", f"{so.get('symbolic_life_score', 0.0):.3f}")
        layout["soul"].update(Panel(soul_table, title="SOUL (Being)", border_style="blue"))

        # HNC COMBUSTION panel
        hc = snap["hnc"]
        hnc_table = Table.grid(padding=(0, 1))
        consensus = hc.get("auris_consensus", "NEUTRAL")
        agreeing = hc.get("auris_agreeing", 0)
        total = hc.get("auris_total", 9)
        conf = hc.get("auris_confidence", 0.0)
        hnc_table.add_row("Auris:", f"{consensus} ({agreeing}/{total}) conf={conf:.2f}")
        lh = hc.get("lighthouse_cleared", False)
        hnc_table.add_row("Lighthouse:", "CLEAR" if lh else "off")
        cd = hc.get("cells_deployed", 0)
        cs = hc.get("cells_success", 0)
        hnc_table.add_row("Cells:", f"{cd} deployed, {cs} success")
        hnc_table.add_row("Coherence:", f"{hc.get('composite_coherence', 0.0):.3f}")
        layout["hnc"].update(Panel(hnc_table, title="HNC COMBUSTION", border_style="red"))

        # MONOLOGUE panel
        mono_lines = snap.get("monologue", [])
        mono_text = Text()
        for entry in mono_lines[-5:]:
            src_name = entry.get("source", "system")
            txt = entry.get("text", "")
            mono_text.append(f"  [{src_name:>12}] ", style="bold dim")
            mono_text.append(f'"{txt[:60]}"\n', style="italic")
        if not mono_lines:
            mono_text.append("  (awaiting internal dialogue...)", style="dim")
        layout["monologue"].update(Panel(mono_text, title="INTERNAL MONOLOGUE", border_style="cyan"))

        # GOAL panel
        g = snap.get("goal", {})
        goal_text = Text()
        goal_label = g.get("text", "")
        goal_status = g.get("status", "")
        steps = g.get("steps", [])

        if goal_label:
            completed_count = sum(1 for s in steps if s.get("status") == "completed")
            active_idx = next((i for i, s in enumerate(steps) if s.get("status") == "active"), -1)
            label_short = goal_label[:50] + ("..." if len(goal_label) > 50 else "")
            step_info = f"Step {active_idx + 1}/{len(steps)}" if active_idx >= 0 else f"{completed_count}/{len(steps)} done"
            goal_text.append(f"  GOAL: {label_short} [{step_info}]\n", style="bold")

            for s in steps[:6]:
                title = s.get("title", "")[:40]
                st = s.get("status", "pending")
                coh = s.get("coherence", 0.0)
                if st == "completed":
                    goal_text.append(f"  [x] {title}", style="green")
                    goal_text.append(f"  [{coh:.2f}]\n", style="dim")
                elif st == "active":
                    goal_text.append(f"  [>] {title}", style="yellow bold")
                    goal_text.append("  [active...]\n", style="yellow")
                elif st == "failed":
                    goal_text.append(f"  [!] {title}", style="red")
                    goal_text.append("  [FAILED]\n", style="red")
                else:
                    goal_text.append(f"  [ ] {title}\n", style="dim")
        else:
            goal_text.append("  No active goal. Type a goal to begin.", style="dim")

        layout["goal"].update(Panel(goal_text, title="GOAL PROGRESS", border_style="green"))

        return layout

    # ------------------------------------------------------------------
    # ANSI fallback rendering
    # ------------------------------------------------------------------
    def _render_ansi(self, snap: Dict[str, Any]) -> str:
        lines: List[str] = []
        uptime_s = snap["uptime"]
        h, rem = divmod(int(uptime_s), 3600)
        m, s = divmod(rem, 60)

        lines.append(f"{BOLD}{CYAN}+{'=' * 64}+{RESET}")
        lines.append(f"{BOLD}{CYAN}|  AUREON ICS  Uptime: {h:02d}:{m:02d}:{s:02d}  "
                      f"Cycle: {snap['cycle']}  Bus: {snap['bus_rate']:.0f}/s{RESET}")
        lines.append(f"{BOLD}{CYAN}+{'=' * 64}+{RESET}")

        # Source
        src = snap["source"]
        lines.append(f"  {BOLD}Lambda(t):{RESET} {YELLOW}{source_lambda_text(src)}{RESET}  "
                      f"{BOLD}Gamma:{RESET} {GREEN}{src.get('coherence_gamma', 0.0):.3f}{RESET}  "
                      f"{BOLD}Psi:{RESET} {CYAN}{src.get('consciousness_psi', 0.0):.3f}{RESET}  "
                      f"{BOLD}Level:{RESET} {src.get('consciousness_level', 'DORMANT')}")

        # HNC
        hc = snap["hnc"]
        lines.append(f"  {BOLD}Auris:{RESET} {hc.get('auris_consensus', 'NEUTRAL')} "
                      f"({hc.get('auris_agreeing', 0)}/{hc.get('auris_total', 9)}) "
                      f"conf={hc.get('auris_confidence', 0.0):.2f}  "
                      f"{BOLD}Lighthouse:{RESET} {'CLEAR' if hc.get('lighthouse_cleared') else 'off'}")

        # Goal
        g = snap.get("goal", {})
        if g.get("text"):
            steps = g.get("steps", [])
            done = sum(1 for s in steps if s.get("status") == "completed")
            lines.append(f"  {BOLD}Goal:{RESET} {g['text'][:50]} [{done}/{len(steps)} done]")

        # Monologue
        mono = snap.get("monologue", [])
        for entry in mono[-3:]:
            lines.append(f"  {DIM}[{entry.get('source', '')}]{RESET} "
                          f"{entry.get('text', '')[:60]}")

        lines.append(f"{BOLD}{CYAN}+{'-' * 64}+{RESET}")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def start(self) -> None:
        """Start the dashboard render loop in a background daemon thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, name="ics-dashboard", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=3)
            self._thread = None

    def _run_loop(self) -> None:
        """Main render loop. Uses Rich Live if available, else ANSI."""
        if _HAS_RICH:
            self._run_rich_loop()
        else:
            self._run_ansi_loop()

    def _run_rich_loop(self) -> None:
        console = Console()
        try:
            with Live(self._render(self._state.snapshot()), console=console,
                       refresh_per_second=2, screen=False) as live:
                while self._running:
                    self._state.increment_cycle()
                    snap = self._state.snapshot()
                    try:
                        layout = self._render(snap)
                        live.update(layout)
                    except Exception as exc:
                        logger.debug("Dashboard render error: %s", exc)
                    time.sleep(0.5)
        except Exception as exc:
            logger.warning("Rich dashboard failed, falling back to ANSI: %s", exc)
            self._run_ansi_loop()

    def _run_ansi_loop(self) -> None:
        while self._running:
            self._state.increment_cycle()
            snap = self._state.snapshot()
            output = self._render_ansi(snap)
            # Clear screen and redraw
            print("\033[2J\033[H" + output, flush=True)
            time.sleep(1.0)

    def get_state(self) -> _DashboardState:
        """Return the internal state object (for testing / inspection)."""
        return self._state
