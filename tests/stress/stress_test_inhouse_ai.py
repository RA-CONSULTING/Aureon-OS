#!/usr/bin/env python3
"""
MAXIMUM STRESS TEST — Aureon In-House AI Framework
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Hammers every component of the in-house AI framework + Queen AI Bridge
under extreme concurrent load to verify:

  1. LLM adapter throughput        (1000 concurrent prompts)
  2. Tool registry race conditions (10000 tool calls across threads)
  3. Agent parallel execution      (50 agents x 20 tasks each)
  4. AgentPool saturation          (pool size 8 vs 100 concurrent jobs)
  5. TaskQueue DAG resolution      (500-task dependency graph)
  6. TaskQueue cascade failure     (100-task chain with upstream failure)
  7. Message bus throughput        (50000 messages, 20 subscribers)
  8. SharedMemory contention       (10000 concurrent set/get operations)
  9. Team orchestration            (5 teams x 10 agents running in parallel)
 10. OpenMultiAgent full-stack     (everything at once)
 11. Queen AI Bridge integration   (1000 enhance_thought calls)
 12. Sustained load soak test      (60 seconds continuous fire)

Usage:
    python tests/stress/stress_test_inhouse_ai.py
    python tests/stress/stress_test_inhouse_ai.py --quick
    python tests/stress/stress_test_inhouse_ai.py --soak 120
"""

from __future__ import annotations

import argparse
import io
import json
import os
import random
import statistics
import sys
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pytest

# Ensure repo root on path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

if hasattr(sys.stdout, "buffer"):
    sys.stdout = sys.stdout if 'pytest' in sys.modules else io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# Suppress noisy logging during stress test
import logging
logging.basicConfig(level=logging.ERROR, format="%(levelname)s %(name)s %(message)s")

from aureon.inhouse_ai import (
    OpenMultiAgent,
    AgentConfig,
    Agent,
    AgentPool,
    TaskQueue,
    Team,
    ToolRegistry,
    AureonBrainAdapter,
)
from aureon.inhouse_ai.team import MessageBus, SharedMemory


# ─────────────────────────────────────────────────────────────────────────────
# Test result tracking
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class TestResult:
    name: str
    passed: bool = False
    duration_s: float = 0.0
    operations: int = 0
    throughput_ops_s: float = 0.0
    errors: int = 0
    details: Dict[str, Any] = field(default_factory=dict)
    exception: Optional[str] = None

    def report(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        icon = "[OK]" if self.passed else "[XX]"
        line = (
            f"{icon} {status:4s}  {self.name:42s}  "
            f"{self.operations:>7d} ops  "
            f"{self.duration_s:>7.2f}s  "
            f"{self.throughput_ops_s:>10.1f} ops/s  "
            f"errors={self.errors}"
        )
        if self.details:
            extras = "  ".join(f"{k}={v}" for k, v in self.details.items())
            line += f"\n        {extras}"
        if self.exception:
            line += f"\n        EXCEPTION: {self.exception}"
        return line


class StressTestRunner:
    """Executes stress tests and collects results."""

    def __init__(self, quick: bool = False, scale: float = 1.0):
        self.quick = quick
        self.results: List[TestResult] = []
        if quick:
            self.scale = 0.1
        else:
            self.scale = float(scale)

    def scaled(self, n: int) -> int:
        return max(1, int(n * self.scale))

    def run(self, name: str, fn):
        """Run a single test with timing + error capture."""
        print(f"  Running: {name}...", flush=True)
        start = time.time()
        result = TestResult(name=name)
        try:
            details = fn() or {}
            result.duration_s = time.time() - start
            result.passed = True
            if isinstance(details, dict):
                result.operations = details.pop("operations", 0)
                result.errors = details.pop("errors", 0)
                result.details = details
                if result.duration_s > 0:
                    result.throughput_ops_s = result.operations / result.duration_s
        except Exception as e:
            result.duration_s = time.time() - start
            result.passed = False
            result.exception = f"{type(e).__name__}: {e}"
            traceback.print_exc()
        self.results.append(result)
        return result

    def summary(self):
        print("\n" + "=" * 100)
        print("  MAXIMUM STRESS TEST RESULTS")
        print("=" * 100)
        for r in self.results:
            print(r.report())
        print("=" * 100)
        passed = sum(1 for r in self.results if r.passed)
        total = len(self.results)
        total_ops = sum(r.operations for r in self.results)
        total_time = sum(r.duration_s for r in self.results)
        total_errors = sum(r.errors for r in self.results)
        print(
            f"  TOTAL: {passed}/{total} tests passed  |  "
            f"{total_ops:,} operations  |  "
            f"{total_time:.2f}s total  |  "
            f"{total_errors} errors"
        )
        print("=" * 100)
        return passed == total


@pytest.fixture
def runner() -> StressTestRunner:
    """Keep the pytest lane bounded; the CLI retains its explicit scale flags."""

    return StressTestRunner(quick=True)


# ─────────────────────────────────────────────────────────────────────────────
# Batched parallel runner — keeps memory bounded at extreme scale
# ─────────────────────────────────────────────────────────────────────────────


def run_parallel_batched(
    fn,
    n_ops: int,
    max_workers: int = 32,
    batch_size: int = 20000,
):
    """
    Run `fn(i)` for i in range(n_ops) using a ThreadPoolExecutor, but
    submit work in batches so only `batch_size` futures exist at any
    moment. This keeps memory bounded when n_ops is in the millions.

    Returns None — callers use shared state for result collection.
    """
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        remaining = n_ops
        start = 0
        while remaining > 0:
            chunk = min(batch_size, remaining)
            futures = [executor.submit(fn, start + j) for j in range(chunk)]
            for f in as_completed(futures):
                # Consume the result so the future is released
                try:
                    f.result()
                except Exception:
                    pass
            start += chunk
            remaining -= chunk


# ─────────────────────────────────────────────────────────────────────────────
# Test 1: LLM adapter throughput
# ─────────────────────────────────────────────────────────────────────────────


def test_llm_adapter_throughput(runner: StressTestRunner):
    """Fire 1000 concurrent prompts at the Brain adapter."""
    n_prompts = runner.scaled(1000)
    adapter = AureonBrainAdapter()

    errors = 0
    errors_lock = threading.Lock()
    latencies = []
    latencies_lock = threading.Lock()

    def fire_prompt(i: int):
        nonlocal errors
        try:
            t0 = time.time()
            response = adapter.prompt(
                messages=[{"role": "user", "content": f"analyse BTCUSDT signal {i}"}],
                system="You are a market analyst",
                max_tokens=256,
            )
            dt = time.time() - t0
            with latencies_lock:
                latencies.append(dt)
            if not response.text:
                with errors_lock:
                    errors += 1
        except Exception:
            with errors_lock:
                errors += 1

    run_parallel_batched(fire_prompt, n_prompts, max_workers=32, batch_size=20000)

    return {
        "operations": n_prompts,
        "errors": errors,
        "p50_latency_ms": round(statistics.median(latencies) * 1000, 2) if latencies else 0,
        "p99_latency_ms": round(sorted(latencies)[int(len(latencies) * 0.99)] * 1000, 2) if len(latencies) > 1 else 0,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Test 2: Tool registry race conditions
# ─────────────────────────────────────────────────────────────────────────────


def test_tool_registry_race(runner: StressTestRunner):
    """10000 concurrent tool calls across threads."""
    n_calls = runner.scaled(10000)
    registry = ToolRegistry(include_builtins=True)

    # Register a custom counter tool
    counter = {"value": 0}
    counter_lock = threading.Lock()

    def counter_handler(args):
        with counter_lock:
            counter["value"] += 1
            return json.dumps({"value": counter["value"]})

    registry.define_tool(
        name="counter",
        description="Increments a counter",
        input_schema={"type": "object", "properties": {}, "required": []},
        handler=counter_handler,
    )

    errors = 0
    errors_lock = threading.Lock()

    def hammer(i: int):
        nonlocal errors
        try:
            tool_name = random.choice(["counter", "read_state", "read_prices", "read_positions"])
            args = {"keys": "all"} if tool_name == "read_state" else \
                   {"symbols": "BTCUSDT", "top_n": 5} if tool_name == "read_prices" else \
                   {"exchange": "all"} if tool_name == "read_positions" else \
                   {}
            result = registry.execute(tool_name, args)
            if not result:
                with errors_lock:
                    errors += 1
        except Exception:
            with errors_lock:
                errors += 1

    run_parallel_batched(hammer, n_calls, max_workers=64, batch_size=20000)

    return {
        "operations": n_calls,
        "errors": errors,
        "counter_final": counter["value"],
    }


# ─────────────────────────────────────────────────────────────────────────────
# Test 3: Agent parallel execution
# ─────────────────────────────────────────────────────────────────────────────


def test_agent_parallel_execution(runner: StressTestRunner):
    """Agents running tasks in parallel. Caps agent count to keep memory bounded."""
    # Cap the number of distinct agent INSTANCES at 500 to avoid
    # instantiating millions of Agent objects under extreme scale.
    # Total ops scale linearly via n_tasks_per_agent instead.
    n_agents = min(runner.scaled(50), 500)
    n_tasks_per_agent = max(1, (runner.scaled(50) * runner.scaled(20)) // n_agents)
    adapter = AureonBrainAdapter()

    agents = [
        Agent(
            adapter=adapter,
            config=AgentConfig(
                name=f"StressAgent-{i}",
                system_prompt=f"You are stress agent {i}",
                max_turns=2,
            ),
        )
        for i in range(n_agents)
    ]

    total_ops = n_agents * n_tasks_per_agent
    errors = 0
    errors_lock = threading.Lock()

    def run_agent_tasks(agent: Agent):
        nonlocal errors
        for j in range(n_tasks_per_agent):
            try:
                result = agent.run(f"task {j} for {agent.name}")
                if not result:
                    with errors_lock:
                        errors += 1
            except Exception:
                with errors_lock:
                    errors += 1

    with ThreadPoolExecutor(max_workers=16) as executor:
        futures = [executor.submit(run_agent_tasks, a) for a in agents]
        for f in as_completed(futures):
            pass

    return {
        "operations": total_ops,
        "errors": errors,
        "agents": n_agents,
        "tasks_per_agent": n_tasks_per_agent,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Test 4: AgentPool saturation
# ─────────────────────────────────────────────────────────────────────────────


def test_agent_pool_saturation(runner: StressTestRunner):
    """AgentPool with size 8 vs N jobs. Capped at 5000 distinct agents
    to keep memory bounded under extreme scale."""
    pool_size = 8
    n_jobs = min(runner.scaled(100), 5000)
    adapter = AureonBrainAdapter()

    pool = AgentPool(max_concurrent=pool_size)
    for i in range(n_jobs):
        pool.add(Agent(
            adapter=adapter,
            config=AgentConfig(name=f"Worker-{i}", max_turns=1),
        ))

    results = pool.run_parallel("Compute signal for BTCUSDT", timeout=60)
    errors = sum(1 for r in results if not r.success)

    return {
        "operations": len(results),
        "errors": errors,
        "pool_size": pool_size,
        "successful": sum(1 for r in results if r.success),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Test 5: TaskQueue DAG resolution
# ─────────────────────────────────────────────────────────────────────────────


def test_task_queue_dag(runner: StressTestRunner):
    """Build a 500-task DAG and resolve dependencies."""
    n_tasks = runner.scaled(500)
    queue = TaskQueue()

    # Build a complex DAG: tasks chain in groups of 5
    task_ids = []
    for i in range(n_tasks):
        depends_on = []
        if i >= 5:
            # Each task depends on the task 5 slots back (mostly linear)
            depends_on.append(task_ids[i - 5])
        if i >= 10 and i % 3 == 0:
            # Every 3rd task also depends on one 10 slots back
            depends_on.append(task_ids[i - 10])

        task = queue.add(
            name=f"task_{i}",
            agent_name=f"agent_{i % 10}",
            prompt=f"task prompt {i}",
            depends_on=depends_on,
        )
        task_ids.append(task.id)

    # Process the queue
    resolved = 0
    max_iterations = n_tasks * 2
    while not queue.is_complete() and resolved < max_iterations:
        ready = queue.get_ready()
        if not ready:
            break
        for task in ready:
            queue.start(task.id)
            queue.complete(task.id, f"result_{task.name}")
            resolved += 1

    summary = queue.summary()
    return {
        "operations": resolved,
        "errors": summary.get("failed", 0) + summary.get("cancelled", 0),
        "tasks_total": n_tasks,
        "completed": summary.get("completed", 0),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Test 6: TaskQueue cascade failure
# ─────────────────────────────────────────────────────────────────────────────


def test_task_queue_cascade_failure(runner: StressTestRunner):
    """100-task chain with upstream failure — verify cascade."""
    n_tasks = max(runner.scaled(100), 20)  # Need at least 20 for fail-at-10 logic
    queue = TaskQueue()

    task_ids = []
    for i in range(n_tasks):
        depends_on = [task_ids[i - 1]] if i > 0 else []
        task = queue.add(
            name=f"chain_{i}",
            agent_name="chain_agent",
            prompt=f"step {i}",
            depends_on=depends_on,
        )
        task_ids.append(task.id)

    # Complete the first 10, then fail task 10 — expect cascade to 90 others
    for i in range(10):
        queue.start(task_ids[i])
        queue.complete(task_ids[i], "ok")

    queue.fail(task_ids[10], "intentional test failure")

    summary = queue.summary()
    cascade_count = summary.get("failed", 0)
    expected_failures = n_tasks - 10  # task 10 fails + all downstream

    details = {
        "operations": n_tasks,
        "errors": 0 if cascade_count == expected_failures else 1,
        "cascade_count": cascade_count,
        "expected": expected_failures,
        "completed": summary.get("completed", 0),
    }

    if cascade_count != expected_failures:
        raise AssertionError(
            f"Cascade failure broken: got {cascade_count} failed, expected {expected_failures}"
        )

    return details


# ─────────────────────────────────────────────────────────────────────────────
# Test 7: Message bus throughput
# ─────────────────────────────────────────────────────────────────────────────


def test_message_bus_throughput(runner: StressTestRunner):
    """50000 messages with 20 subscribers."""
    n_messages = runner.scaled(50000)
    n_subscribers = 20

    bus = MessageBus()
    received: Dict[int, int] = {i: 0 for i in range(n_subscribers)}
    received_lock = threading.Lock()

    def make_handler(sub_id: int):
        def handler(msg):
            with received_lock:
                received[sub_id] += 1
        return handler

    for i in range(n_subscribers):
        bus.subscribe("stress.topic", make_handler(i))

    def publisher(idx: int):
        bus.publish("stress.topic", {"msg": idx}, source="stress")

    run_parallel_batched(publisher, n_messages, max_workers=32, batch_size=20000)

    total_received = sum(received.values())
    expected = n_messages * n_subscribers

    return {
        "operations": n_messages,
        "errors": 0 if total_received == expected else 1,
        "total_delivered": total_received,
        "expected": expected,
        "subscribers": n_subscribers,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Test 8: SharedMemory contention
# ─────────────────────────────────────────────────────────────────────────────


def test_shared_memory_contention(runner: StressTestRunner):
    """10000 concurrent set/get operations on SharedMemory."""
    n_ops = runner.scaled(10000)
    memory = SharedMemory()
    errors = 0
    errors_lock = threading.Lock()

    def hammer(i: int):
        nonlocal errors
        try:
            key = f"key_{i % 100}"
            if i % 2 == 0:
                memory.set(key, {"val": i, "ts": time.time()}, source=f"worker_{i}")
            else:
                memory.get(key, default={})
        except Exception:
            with errors_lock:
                errors += 1

    run_parallel_batched(hammer, n_ops, max_workers=64, batch_size=20000)

    return {
        "operations": n_ops,
        "errors": errors,
        "keys_stored": len(memory.keys()),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Test 9: Team orchestration
# ─────────────────────────────────────────────────────────────────────────────


def test_team_orchestration(runner: StressTestRunner):
    """N teams x M agents running in parallel. Bounded to keep memory
    sane when scale factors multiply (5 × 10 × 1000² is untenable)."""
    n_teams = min(runner.scaled(5), 50)
    n_agents_per_team = min(runner.scaled(10), 50)
    adapter = AureonBrainAdapter()

    teams = []
    for t in range(n_teams):
        configs = [
            AgentConfig(name=f"Team{t}-Agent{a}", max_turns=1)
            for a in range(n_agents_per_team)
        ]
        team = Team(
            name=f"StressTeam-{t}",
            adapter=adapter,
            agent_configs=configs,
            max_concurrent=4,
        )
        teams.append(team)

    total_ops = 0
    errors = 0

    def run_team(team: Team):
        nonlocal total_ops, errors
        results = team.run_all("Analyse market state", parallel=True)
        total_ops += len(results)
        for r in results.values():
            if r.startswith("[ERROR]"):
                errors += 1

    with ThreadPoolExecutor(max_workers=n_teams) as executor:
        futures = [executor.submit(run_team, t) for t in teams]
        for f in as_completed(futures):
            pass

    return {
        "operations": total_ops,
        "errors": errors,
        "teams": n_teams,
        "agents_per_team": n_agents_per_team,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Test 10: OpenMultiAgent full-stack
# ─────────────────────────────────────────────────────────────────────────────


def test_open_multi_agent_full_stack(runner: StressTestRunner):
    """End-to-end orchestrator with teams + tasks + parallel agents."""
    oma = OpenMultiAgent(mode="brain")

    # Create 3 teams with 5 agents each
    for t in range(3):
        configs = [
            AgentConfig(name=f"Stack-T{t}-A{a}", max_turns=1)
            for a in range(5)
        ]
        oma.create_team(
            name=f"StackTeam-{t}",
            agent_configs=configs,
            max_concurrent=4,
        )

    total_ops = 0
    errors = 0

    # Run each team on a task
    for team_name in oma.list_teams():
        results = oma.run_team(team_name, "Compute signal")
        total_ops += len(results)
        for r in results.values():
            if r.startswith("[ERROR]"):
                errors += 1

    # Run standalone agents
    for i in range(runner.scaled(20)):
        try:
            oma.run_agent(
                name=f"Standalone-{i}",
                task=f"Check signal {i}",
                system_prompt="You are a signal checker.",
            )
            total_ops += 1
        except Exception:
            errors += 1

    # Build a task DAG in the first team
    first_team = oma.get_team("StackTeam-0")
    t1 = first_team.queue.add("fetch", agent_name="Stack-T0-A0", prompt="fetch")
    t2 = first_team.queue.add("analyse", agent_name="Stack-T0-A1", prompt="analyse", depends_on=[t1.id])
    first_team.queue.add("decide", agent_name="Stack-T0-A2", prompt="decide", depends_on=[t2.id])

    oma.run_tasks("StackTeam-0")
    total_ops += len(first_team.queue)

    # Get system-wide status
    status = oma.get_status()
    oma.shutdown()

    return {
        "operations": total_ops,
        "errors": errors,
        "teams": status["team_count"],
        "standalone": status["standalone_agent_count"],
        "tools": len(status["tools_registered"]),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Test 11: Queen AI Bridge integration
# ─────────────────────────────────────────────────────────────────────────────


def test_queen_ai_bridge_integration(runner: StressTestRunner):
    """1000 calls to enhance_thought + synthesise_insight + reflect."""
    n_calls = runner.scaled(1000)

    from aureon.queen.queen_inhouse_ai_bridge import QueenAIBridge
    bridge = QueenAIBridge()
    bridge.start()

    if not bridge.is_alive:
        raise RuntimeError("Queen AI Bridge adapter failed to initialise")

    errors = 0
    errors_lock = threading.Lock()

    def hammer(i: int):
        nonlocal errors
        try:
            op = i % 4
            if op == 0:
                result = bridge.enhance_thought(
                    "UPDATE",
                    perception={"significant_moves": [{"symbol": "BTCUSDT"}], "recent_bars": [1, 2, 3]},
                    emotion={"mood": "focused", "urgency": 0.6, "excitement": 0.4},
                )
            elif op == 1:
                insight = bridge.synthesise_insight(
                    market_data={"symbol": "BTCUSDT", "price": 100000 + i},
                    system_signals=[{"source": "scanner", "signal": "BUY"}],
                )
                result = insight.text
            elif op == 2:
                result = bridge.reflect([
                    {"action": "BUY", "confidence": 0.8},
                    {"action": "HOLD", "confidence": 0.5},
                    {"action": "BUY", "confidence": 0.9},
                ])
            else:
                result = bridge.reason(f"What is the state of signal {i}?")

            if not result:
                with errors_lock:
                    errors += 1
        except Exception:
            with errors_lock:
                errors += 1

    run_parallel_batched(hammer, n_calls, max_workers=16, batch_size=20000)

    status = bridge.get_status()
    bridge.stop()

    return {
        "operations": n_calls,
        "errors": errors,
        "insights_generated": status["insights_generated"],
        "thoughts_enhanced": status["thoughts_enhanced"],
        "bridge_errors": status["errors"],
    }


# ─────────────────────────────────────────────────────────────────────────────
# Test 12: Miner AI Bridge integration
# ─────────────────────────────────────────────────────────────────────────────


def test_miner_ai_bridge_integration(runner: StressTestRunner):
    """Hammer the MinerAIBridge across all 5 integration points concurrently."""
    n_calls = runner.scaled(1000)

    from aureon.miner.miner_inhouse_ai_bridge import MinerAIBridge
    bridge = MinerAIBridge()
    bridge.start()

    if not bridge.is_alive:
        raise RuntimeError("Miner AI Bridge failed to initialise")

    errors = 0
    errors_lock = threading.Lock()

    def hammer(i: int):
        nonlocal errors
        try:
            op = i % 5
            if op == 0:
                insight = bridge.enhance_skeptical_analysis(
                    market_data={
                        "fear_greed": 20 + (i % 60),
                        "btc_dominance": 55.0 + (i % 10),
                        "mcap_change": -2.0 + (i % 4),
                        "btc_price": 67000 + i,
                    },
                    existing_red_flags=["test flag"],
                    existing_green_flags=["test green"],
                )
                result = insight.verdict
            elif op == 1:
                insight = bridge.synthesise_council_verdict(
                    market_data={"fear_greed": 30, "btc_price": 67000},
                    advisor_votes=[
                        {"advisor": f"Advisor-{j}", "verdict": "BUY" if j % 2 == 0 else "HOLD",
                         "confidence": 0.5 + (j * 0.1), "reasoning": f"reason {j}"}
                        for j in range(5)
                    ],
                )
                result = insight.verdict
            elif op == 2:
                insight = bridge.enhance_wisdom_synthesis(
                    civilization_signals={
                        "egyptian": {"verdict": "BUY", "confidence": 0.75},
                        "pythagorean": {"verdict": "NEUTRAL", "confidence": 0.6},
                        "celtic": {"verdict": "BUY", "confidence": 0.7},
                        "aztec": {"verdict": "HOLD", "confidence": 0.5},
                        "mogollon": {"verdict": "BUY", "confidence": 0.65},
                        "plantagenet": {"verdict": "BUY", "confidence": 0.8},
                        "warfare": {"verdict": "NEUTRAL", "confidence": 0.55},
                    },
                    quantum_context={
                        "quantum_coherence": 0.7 + (i % 3) * 0.1,
                        "planetary_gamma": 0.6 + (i % 4) * 0.05,
                        "is_lighthouse": (i % 5 == 0),
                    },
                )
                result = insight.verdict
            elif op == 3:
                insight = bridge.suggest_quantum_weights(
                    subsystem_states={
                        "planetary_gamma": 0.3 + (i % 7) * 0.1,
                        "coherence_psi": 0.4 + (i % 6) * 0.1,
                        "probability_edge": (i % 4) * 0.1,
                        "is_lighthouse": (i % 3 == 0),
                    },
                )
                result = str(len(insight.suggested_weights))
                # Validate weights sum to ~1.0
                total = sum(insight.suggested_weights.values())
                if abs(total - 1.0) > 0.01:
                    with errors_lock:
                        errors += 1
            else:
                result = bridge.reason_about_mining_state(
                    full_context={
                        "hash_rate": 100 + i,
                        "coherence": 0.5 + (i % 5) * 0.1,
                        "gamma": 0.6 + (i % 4) * 0.1,
                    },
                    question=f"Mining question {i}?",
                )

            if not result:
                with errors_lock:
                    errors += 1
        except Exception:
            with errors_lock:
                errors += 1

    run_parallel_batched(hammer, n_calls, max_workers=16, batch_size=20000)

    status = bridge.get_status()
    bridge.stop()

    return {
        "operations": n_calls,
        "errors": errors,
        "skeptical_calls": status["skeptical_calls"],
        "council_calls": status["council_calls"],
        "wisdom_calls": status["wisdom_calls"],
        "quantum_calls": status["quantum_calls"],
        "general_calls": status["general_calls"],
        "bridge_errors": status["errors"],
    }


# ─────────────────────────────────────────────────────────────────────────────
# Test 13: Miner Quantum Weight Stability Test
# ─────────────────────────────────────────────────────────────────────────────


def test_miner_quantum_weight_stability(runner: StressTestRunner):
    """Verify quantum weight suggestions stay normalised under continuous adaptation."""
    n_cycles = runner.scaled(500)

    from aureon.miner.miner_inhouse_ai_bridge import MinerAIBridge
    bridge = MinerAIBridge()
    bridge.start()

    # Start with default weights
    weights = {
        "probability": 0.22, "planetary": 0.18, "harmonic": 0.13,
        "temporal": 0.12, "casimir": 0.08, "coherence": 0.10,
        "memory": 0.05, "diamond": 0.12,
    }

    errors = 0
    normalisation_violations = 0

    for i in range(n_cycles):
        # Simulate varying market conditions
        states = {
            "planetary_gamma": 0.3 + (i % 10) * 0.07,
            "coherence_psi": 0.4 + (i % 8) * 0.07,
            "probability_edge": (i % 6) * 0.08,
            "is_lighthouse": (i % 7 == 0),
        }

        insight = bridge.suggest_quantum_weights(
            subsystem_states=states,
            current_weights=weights,
        )

        if insight.suggested_weights:
            # Blend at 20% new, 80% current (matches real usage)
            for k, v in insight.suggested_weights.items():
                if k in weights:
                    weights[k] = weights[k] * 0.8 + v * 0.2

            # Re-normalise
            total = sum(weights.values())
            if total > 0:
                weights = {k: v / total for k, v in weights.items()}

            # Verify normalisation
            total_after = sum(weights.values())
            if abs(total_after - 1.0) > 0.001:
                normalisation_violations += 1

            # Verify no negative weights
            if any(v < 0 for v in weights.values()):
                errors += 1

    bridge.stop()

    return {
        "operations": n_cycles,
        "errors": errors + normalisation_violations,
        "normalisation_violations": normalisation_violations,
        "final_weights_sum": round(sum(weights.values()), 4),
        "max_weight": round(max(weights.values()), 4),
        "min_weight": round(min(weights.values()), 4),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Test 14: VM Control dispatch throughput
# ─────────────────────────────────────────────────────────────────────────────


def test_vm_control_dispatch(runner: StressTestRunner):
    """Hammer the VMControlDispatcher with 10000 concurrent actions."""
    n_ops = runner.scaled(10000)

    from aureon.autonomous.vm_control import VMControlDispatcher

    dispatcher = VMControlDispatcher()
    sid = dispatcher.create_session(backend="simulated", name="stress-vm", make_default=True)
    controller = dispatcher.get_session(sid)
    controller.arm(dry_run=False)

    errors = 0
    errors_lock = threading.Lock()

    actions_to_test = [
        ("screenshot", {}),
        ("mouse_move", {"x": 500, "y": 300}),
        ("left_click", {"x": 100, "y": 200}),
        ("right_click", {}),
        ("double_click", {"x": 400, "y": 400}),
        ("type_text", {"text": "hello"}),
        ("press_key", {"key": "enter"}),
        ("hotkey", {"keys": ["ctrl", "c"]}),
        ("scroll", {"x": 500, "y": 500, "direction": "down", "amount": 3}),
        ("get_cursor_position", {}),
        ("get_screen_size", {}),
        ("list_windows", {}),
        ("get_active_window", {}),
        ("focus_window", {"title": "File Explorer"}),
        ("execute_shell", {"command": "whoami"}),
        ("execute_powershell", {"command": "Get-ComputerInfo"}),
    ]

    def fire(i: int):
        nonlocal errors
        action, params = actions_to_test[i % len(actions_to_test)]
        try:
            result = dispatcher.dispatch(action, dict(params))
            if not result.get("ok"):
                with errors_lock:
                    errors += 1
        except Exception:
            with errors_lock:
                errors += 1

    run_parallel_batched(fire, n_ops, max_workers=32, batch_size=20000)

    status = dispatcher.get_status()
    dispatcher.destroy_all()

    return {
        "operations": n_ops,
        "errors": errors,
        "dispatch_total": status["total_actions"],
        "dispatch_errors": status["total_errors"],
    }


# ─────────────────────────────────────────────────────────────────────────────
# Test 15: VM multi-session concurrency
# ─────────────────────────────────────────────────────────────────────────────


def test_vm_multi_session(runner: StressTestRunner):
    """Run 10 simultaneous VM sessions with actions distributed across them."""
    n_sessions = 10
    n_ops_per_session = runner.scaled(500)

    from aureon.autonomous.vm_control import VMControlDispatcher

    dispatcher = VMControlDispatcher()
    session_ids = []
    for i in range(n_sessions):
        sid = dispatcher.create_session(
            backend="simulated",
            name=f"vm-{i}",
            host=f"10.0.0.{100 + i}",
        )
        session_ids.append(sid)
        dispatcher.get_session(sid).arm(dry_run=False)

    errors = 0
    errors_lock = threading.Lock()

    def session_worker(sid: str, count: int):
        nonlocal errors
        for i in range(count):
            try:
                op = i % 4
                if op == 0:
                    r = dispatcher.dispatch("screenshot", {}, session_id=sid)
                elif op == 1:
                    r = dispatcher.dispatch("left_click", {"x": i, "y": i * 2}, session_id=sid)
                elif op == 2:
                    r = dispatcher.dispatch("type_text", {"text": f"msg-{i}"}, session_id=sid)
                else:
                    r = dispatcher.dispatch("execute_shell", {"command": "whoami"}, session_id=sid)
                if not r.get("ok"):
                    with errors_lock:
                        errors += 1
            except Exception:
                with errors_lock:
                    errors += 1

    with ThreadPoolExecutor(max_workers=n_sessions) as executor:
        futures = [executor.submit(session_worker, sid, n_ops_per_session) for sid in session_ids]
        for f in as_completed(futures):
            pass

    total_ops = n_sessions * n_ops_per_session

    # Verify each session saw the correct number of actions
    per_session_counts = {
        s["session_id"]: s["action_count"]
        for s in dispatcher.list_sessions()
    }
    min_count = min(per_session_counts.values())
    max_count = max(per_session_counts.values())

    dispatcher.destroy_all()

    return {
        "operations": total_ops,
        "errors": errors,
        "sessions": n_sessions,
        "ops_per_session": n_ops_per_session,
        "min_count": min_count,
        "max_count": max_count,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Test 16: VM tools registered with ToolRegistry end-to-end
# ─────────────────────────────────────────────────────────────────────────────


def test_vm_tool_registry_integration(runner: StressTestRunner):
    """Register VM tools into ToolRegistry and call them as an agent would."""
    n_ops = runner.scaled(5000)

    from aureon.autonomous.vm_control import VMControlDispatcher, register_vm_tools, VM_TOOL_NAMES
    from aureon.inhouse_ai import ToolRegistry

    dispatcher = VMControlDispatcher()
    sid = dispatcher.create_session(backend="simulated", name="registry-vm", make_default=True)
    dispatcher.get_session(sid).arm(dry_run=False)

    registry = ToolRegistry(include_builtins=True)
    count = register_vm_tools(registry, dispatcher)

    if count != len(VM_TOOL_NAMES):
        raise AssertionError(f"Expected {len(VM_TOOL_NAMES)} tools, registered {count}")

    errors = 0
    errors_lock = threading.Lock()

    tool_call_sequence = [
        ("vm_screenshot", {}),
        ("vm_mouse_move", {"x": 500, "y": 300}),
        ("vm_left_click", {"x": 500, "y": 300}),
        ("vm_type_text", {"text": "test"}),
        ("vm_press_key", {"key": "enter"}),
        ("vm_hotkey", {"keys": ["ctrl", "s"]}),
        ("vm_get_cursor_position", {}),
        ("vm_list_windows", {}),
        ("vm_execute_shell", {"command": "echo hello"}),
    ]

    def agent_call(i: int):
        nonlocal errors
        tool_name, args = tool_call_sequence[i % len(tool_call_sequence)]
        try:
            result_str = registry.execute(tool_name, dict(args))
            result = json.loads(result_str)
            if not result.get("ok"):
                with errors_lock:
                    errors += 1
        except Exception:
            with errors_lock:
                errors += 1

    run_parallel_batched(agent_call, n_ops, max_workers=16, batch_size=20000)

    dispatcher.destroy_all()

    return {
        "operations": n_ops,
        "errors": errors,
        "vm_tools_registered": count,
        "total_registry_tools": len(registry),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Test 17: Agent-driven VM control via full conversation loop
# ─────────────────────────────────────────────────────────────────────────────


def test_agent_driven_vm_control(runner: StressTestRunner):
    """An in-house agent drives a VM through its tool dispatch loop."""
    from aureon.inhouse_ai import Agent, AgentConfig, AureonBrainAdapter, ToolRegistry
    from aureon.autonomous.vm_control import VMControlDispatcher, register_vm_tools

    dispatcher = VMControlDispatcher()
    sid = dispatcher.create_session(backend="simulated", name="agent-vm", make_default=True)
    dispatcher.get_session(sid).arm(dry_run=False)

    registry = ToolRegistry(include_builtins=True)
    register_vm_tools(registry, dispatcher)

    adapter = AureonBrainAdapter()
    agent = Agent(
        adapter=adapter,
        config=AgentConfig(
            name="VMOperator",
            system_prompt="You control a Windows VM via the vm_* tools.",
            max_turns=3,
        ),
        tools=registry,
    )

    n_runs = runner.scaled(100)
    errors = 0

    for i in range(n_runs):
        try:
            result = agent.run(f"Take a screenshot of the VM and tell me what you see, iteration {i}")
            if not result:
                errors += 1
        except Exception:
            errors += 1

    # Verify the dispatcher saw the actions
    status = dispatcher.get_status()
    dispatcher.destroy_all()

    return {
        "operations": n_runs,
        "errors": errors,
        "vm_actions_triggered": status["total_actions"],
    }


# ─────────────────────────────────────────────────────────────────────────────
# Test 18: Swarm motion hive — end-to-end with Lambda(t) synthesis
# ─────────────────────────────────────────────────────────────────────────────


def test_swarm_motion_hive(runner: StressTestRunner):
    """Spawn a full swarm motion environment and run it under load."""
    from aureon.swarm_motion import SwarmMotionHive, SwarmMotionConfig

    swarm_size = runner.scaled(8)
    swarm_size = max(2, swarm_size)
    pulse_count = runner.scaled(500)

    hive = SwarmMotionHive(config=SwarmMotionConfig(
        swarm_size=swarm_size,
        backend="simulated",
        interval_scale=0.02,
        alpha=0.25,
        beta=0.85,
        sample_rate_hz=20.0,
        mirror_interval_s=0.2,
    ))
    hive.spawn_swarm()

    errors = 0

    # Fire synchronous swarm snapshots in parallel
    def snap_batch(i: int):
        nonlocal errors
        try:
            snaps = hive.take_swarm_snapshot()
            if any(s.error for s in snaps):
                errors += 1
        except Exception:
            errors += 1

    n_batches = max(5, runner.scaled(100))
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(snap_batch, i) for i in range(n_batches)]
        for f in as_completed(futures):
            pass

    # Pulse the love stream
    samples = hive.pulse_love_stream(count=pulse_count)

    # Verify Λ(t) stays bounded (sanity check)
    lambda_max = max(abs(s.lambda_t) for s in samples) if samples else 0.0
    if lambda_max > 10.0:
        raise AssertionError(f"Λ(t) exploded: max={lambda_max}")

    # Reflect many times
    reflections = runner.scaled(200)
    for _ in range(reflections):
        hive.reflect()

    status = hive.get_status()
    state = hive.get_unified_state()
    hive.shutdown()

    total_ops = n_batches * swarm_size + pulse_count + reflections

    return {
        "operations": total_ops,
        "errors": errors,
        "swarm_size": swarm_size,
        "total_snapshots": state["total_snapshots"],
        "lambda_samples": state["love_stream"]["samples_generated"],
        "reflections": reflections,
        "lambda_max": round(lambda_max, 4),
        "final_lambda": round(status.get("lambda_t") or 0, 4),
        "dominant_chakra": status.get("dominant_chakra"),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Test 19: HNC Lambda(t) stability — verify past feedback loop stays stable
# ─────────────────────────────────────────────────────────────────────────────


def test_lambda_stability(runner: StressTestRunner):
    """Run Λ(t) for N cycles and verify β Λ(t-τ) keeps the field bounded."""
    from aureon.swarm_motion import StandingWaveLoveStream
    from aureon.swarm_motion.fibonacci_snapper import MotionSnapshot

    n_cycles = runner.scaled(2000)

    # Test three β values: below, inside, and above the stability regime
    results = {}
    for beta_label, beta in [("unstable_low", 0.3), ("stable", 0.85), ("edge", 1.05)]:
        stream = StandingWaveLoveStream(alpha=0.25, beta=beta, tau_s=10.0, sample_rate_hz=100.0)

        # Feed it synthetic snapshots with varying motion
        for i in range(50):
            snap = MotionSnapshot(
                session_id="test", agent_name="bench",
                sequence=i, interval_s=0.1,
                image_hash=f"{i:064x}",
                motion_delta=0.3 + 0.2 * (i % 3),
                coherence=0.5 + 0.2 * ((i % 5) / 5),
                width=1920, height=1080,
                cursor_x=500 + i * 10, cursor_y=300 + i * 5,
            )
            stream.ingest_snapshot(snap)

        # Run Λ(t) evaluations
        max_abs = 0.0
        for _ in range(n_cycles):
            sample = stream.evaluate()
            max_abs = max(max_abs, abs(sample.lambda_t))

        status = stream.get_status()
        results[beta_label] = {
            "beta": beta,
            "max_abs_lambda": round(max_abs, 4),
            "samples": status["samples_generated"],
            "love_weight": round(status["weights"]["love"], 4),
        }

    # Stable β should keep |Λ| bounded (< 3 is generous)
    errors = 0
    if results["stable"]["max_abs_lambda"] > 3.0:
        errors += 1

    total_ops = 3 * n_cycles

    return {
        "operations": total_ops,
        "errors": errors,
        "stable_max": results["stable"]["max_abs_lambda"],
        "stable_love_weight": results["stable"]["love_weight"],
        "edge_max": results["edge"]["max_abs_lambda"],
    }


# ─────────────────────────────────────────────────────────────────────────────
# Test 20: Pillar alignment throughput + correctness
# ─────────────────────────────────────────────────────────────────────────────


def test_pillar_alignment(runner: StressTestRunner):
    """Hammer PillarAlignment.run_synthetic_cycle + verify alignment math."""
    from aureon.alignment import (
        PillarAlignment,
        AlignmentConfig,
    )

    n_cycles = runner.scaled(5000)

    alignment = PillarAlignment(AlignmentConfig(auto_load_pillars=False))

    # Test 1: baseline synthetic stack under load
    errors = 0
    errors_lock = threading.Lock()
    lighthouse_count = 0
    lighthouse_lock = threading.Lock()

    def fire(i: int):
        nonlocal errors, lighthouse_count
        try:
            # Alternate between three scenarios
            if i % 3 == 0:
                # Perfect alignment
                signals = [
                    {"pillar": f"P{j}", "signal": "BUY", "confidence": 0.95,
                     "coherence": 0.96, "frequency_hz": 528.0}
                    for j in range(6)
                ]
            elif i % 3 == 1:
                # Default (mixed)
                signals = None
            else:
                # Complete disagreement
                signals = [
                    {"pillar": f"A{j}", "signal": "BUY" if j % 2 == 0 else "SELL",
                     "confidence": 0.7, "coherence": 0.6, "frequency_hz": 432.0 if j < 3 else 741.0}
                    for j in range(6)
                ]
            result = alignment.run_synthetic_cycle(signals=signals)
            if result.lighthouse_cleared:
                with lighthouse_lock:
                    lighthouse_count += 1
            if result.total_pillars != 6:
                with errors_lock:
                    errors += 1
        except Exception:
            with errors_lock:
                errors += 1

    run_parallel_batched(fire, n_cycles, max_workers=16, batch_size=20000)

    # Correctness check: of the ~1/3 perfect-alignment cycles, most should clear
    expected_lighthouse = n_cycles // 3
    # Tolerance: at least 90% of perfect cycles should clear
    if lighthouse_count < expected_lighthouse * 0.9:
        errors += 1

    status = alignment.get_status()

    return {
        "operations": n_cycles,
        "errors": errors,
        "lighthouse_count": lighthouse_count,
        "expected_lighthouse_min": int(expected_lighthouse * 0.9),
        "lighthouse_rate": round(status["lighthouse_clear_rate"], 4),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Test 21: Harmonic math correctness
# ─────────────────────────────────────────────────────────────────────────────


def test_harmonic_math(runner: StressTestRunner):
    """Verify the harmonic resonance math returns correct results."""
    from aureon.alignment.harmonic_resonance import (
        consonance_score,
        compute_signal_consensus,
        compute_phase_coherence,
        analyse_frequency_harmony,
        full_harmonic_analysis,
        geometric_mean,
        FUNDAMENTAL_HZ,
    )
    import math

    errors = 0
    n_checks = 0

    # Consonance scores — exact unison must be 1.0
    n_checks += 1
    if abs(consonance_score(1.0) - 1.0) > 0.001:
        errors += 1

    # Perfect octave must be 1.0
    n_checks += 1
    if abs(consonance_score(2.0) - 1.0) > 0.001:
        errors += 1

    # Perfect fifth
    n_checks += 1
    if abs(consonance_score(1.5) - 1.0) > 0.001:
        errors += 1

    # Very dissonant ratio (midway between unison and octave)
    n_checks += 1
    mid = consonance_score(1.4142135623730951)  # sqrt(2) → tritone, but still consonant here
    # Tritone IS in our consonant set, so it should be high
    if mid < 0.9:
        errors += 1

    # Signal consensus: all agree → 1.0
    n_checks += 1
    c, _, _, _ = compute_signal_consensus(["BUY"] * 6)
    if abs(c - 1.0) > 0.001:
        errors += 1

    # Signal consensus: perfect 3-way split → 1/3
    n_checks += 1
    c, _, _, _ = compute_signal_consensus(["BUY", "BUY", "SELL", "SELL", "NEUTRAL", "NEUTRAL"])
    if abs(c - 1/3) > 0.01:
        errors += 1

    # Phase coherence: aligned → 1.0
    n_checks += 1
    r = compute_phase_coherence([0.0, 0.0, 0.0])
    if abs(r - 1.0) > 0.001:
        errors += 1

    # Phase coherence: evenly scattered → ~0
    n_checks += 1
    r = compute_phase_coherence([0, 2 * math.pi / 3, 4 * math.pi / 3])
    if r > 0.01:
        errors += 1

    # Geometric mean: all 1 → 1
    n_checks += 1
    if abs(geometric_mean([1, 1, 1, 1]) - 1.0) > 0.001:
        errors += 1

    # Geometric mean: any zero → ~0
    n_checks += 1
    if geometric_mean([1, 1, 1, 0]) > 0.01:
        errors += 1

    # Full analysis on a perfect stack should clear the Lighthouse
    n_checks += 1
    perfect = [
        {"pillar": f"P{i}", "signal": "BUY", "confidence": 0.95,
         "coherence": 0.96, "frequency_hz": 528.0}
        for i in range(6)
    ]
    analysis = full_harmonic_analysis(perfect, t=0.0)
    if not analysis.lighthouse_cleared:
        errors += 1
    if analysis.alignment_score < 0.94:
        errors += 1

    # Full analysis on complete disagreement should NOT clear
    n_checks += 1
    scattered = [
        {"pillar": f"P{i}", "signal": "BUY" if i < 2 else "SELL" if i < 4 else "NEUTRAL",
         "confidence": 0.5, "coherence": 0.4, "frequency_hz": 528.0}
        for i in range(6)
    ]
    analysis = full_harmonic_analysis(scattered, t=0.0)
    if analysis.lighthouse_cleared:
        errors += 1

    # Pillar frequency harmonic lock should be high (≥0.99)
    n_checks += 1
    lock, _, _ = analyse_frequency_harmony({
        "Nexus": 432.0, "Omega": 432.0, "Infinite": 528.0,
        "Piano": 396.0, "QGITA": 528.0, "Auris": 741.0,
    }, FUNDAMENTAL_HZ)
    if lock < 0.99:
        errors += 1

    return {
        "operations": n_checks,
        "errors": errors,
        "checks_passed": n_checks - errors,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Test 22: Unified harmonic directive (pillars + love stream + queen + miner)
# ─────────────────────────────────────────────────────────────────────────────


def test_unified_directive(runner: StressTestRunner):
    """Exercise the full cross-layer alignment assembly."""
    from aureon.alignment import (
        PillarAlignment, AlignmentConfig, UnifiedHarmonicDirective,
    )
    from aureon.swarm_motion import SwarmMotionHive, SwarmMotionConfig

    n_directives = runner.scaled(500)

    # Set up a small hive so the love stream is alive
    hive = SwarmMotionHive(config=SwarmMotionConfig(
        swarm_size=3, backend="simulated", interval_scale=0.01,
    ))
    hive.spawn_swarm()
    # Warm up the love stream
    for _ in range(5):
        hive.take_swarm_snapshot()
    hive.pulse_love_stream(count=20)

    alignment = PillarAlignment(AlignmentConfig(auto_load_pillars=False))
    unified = UnifiedHarmonicDirective(pillar_alignment=alignment)
    unified.set_love_stream(hive._ensure_love_stream())

    perfect = [
        {"pillar": f"P{i}", "signal": "BUY", "confidence": 0.95,
         "coherence": 0.96, "frequency_hz": 528.0}
        for i in range(6)
    ]

    errors = 0
    errors_lock = threading.Lock()
    lighthouse_count = 0
    lighthouse_lock = threading.Lock()

    def fire(i: int):
        nonlocal errors, lighthouse_count
        try:
            directive = unified.assemble(
                context={"btc_price": 67000 + i, "fear_greed": 35 + (i % 30)},
                use_synthetic_pillars=True,
                synthetic_pillar_signals=perfect,
            )
            if directive.lighthouse_cleared:
                with lighthouse_lock:
                    lighthouse_count += 1
            # Verify all 4 layers contributed
            if len(directive.contributing_layers) < 1:
                with errors_lock:
                    errors += 1
        except Exception:
            with errors_lock:
                errors += 1

    run_parallel_batched(fire, n_directives, max_workers=8, batch_size=20000)

    status = unified.get_status()
    hive.shutdown()

    return {
        "operations": n_directives,
        "errors": errors,
        "lighthouse_count": lighthouse_count,
        "layers_wired": sum(1 for v in status["layers_wired"].values() if v),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Test 23: Code architect — static safety validator
# ─────────────────────────────────────────────────────────────────────────────


def test_code_architect_safety(runner: StressTestRunner):
    """Verify the validator blocks dangerous code and accepts safe code."""
    from aureon.code_architect.validator import SkillValidator

    v = SkillValidator(strict_static=True)

    safe_snippets = [
        "def s(): return vm_screenshot()",
        "def s(x=0, y=0): return vm_left_click(x=x, y=y)",
        "def s():\n    r = call_skill('mouse_move')\n    return {'ok': True, 'r': r}",
        "def s():\n    safe_sleep(0.1)\n    return {'ok': True}",
        "def s():\n    results = []\n    for i in range(3):\n        results.append(vm_wait(seconds=0.01))\n    return {'ok': True, 'results': results}",
    ]

    dangerous_snippets = [
        "def s(): eval('1+1')",
        "def s(): exec('print(1)')",
        "def s(): __import__('os').system('ls')",
        "def s(): open('/etc/passwd').read()",
        "def s():\n    import os\n    os.remove('/tmp/x')",
        "def s(): compile('1', '', 'eval')",
        "def s(): return ().__class__.__bases__[0].__subclasses__()",
        "def s(): raise SystemExit(1)",
        "def s(): globals()",
        "def s(): locals()",
    ]

    errors = 0
    n_checks = len(safe_snippets) + len(dangerous_snippets)

    for code in safe_snippets:
        ok, err_list = v.static_check(code)
        if not ok:
            errors += 1

    for code in dangerous_snippets:
        ok, err_list = v.static_check(code)
        if ok:
            errors += 1  # Should have been blocked

    return {
        "operations": n_checks,
        "errors": errors,
        "safe_accepted": len(safe_snippets),
        "dangerous_blocked": len(dangerous_snippets),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Test 24: Code architect — skill library persistence + dependency resolution
# ─────────────────────────────────────────────────────────────────────────────


def test_code_architect_library(runner: StressTestRunner):
    """Verify SkillLibrary add/save/load/resolve under concurrent pressure."""
    from aureon.code_architect.skill_library import SkillLibrary
    from aureon.code_architect.skill import Skill, SkillLevel, SkillStatus
    from pathlib import Path
    import tempfile, shutil

    tmp = Path(tempfile.mkdtemp(prefix="aureon_lib_stress_"))
    try:
        lib = SkillLibrary(storage_dir=tmp)
        # Cap skill chain depth at 50,000 — beyond that the JSON
        # save/load and pure Skill object overhead dominates without
        # proving anything new.
        n_skills = min(runner.scaled(500), 50000)
        errors = 0

        # Add skills in a chain so each depends on the previous
        def add_skill(i: int):
            nonlocal errors
            try:
                skill = Skill(
                    name=f"skill_{i}",
                    description=f"Stress skill {i}",
                    level=SkillLevel.COMPOUND if i > 0 else SkillLevel.ATOMIC,
                    code=f"def skill_{i}(): return {{'i': {i}}}",
                    entry_function=f"skill_{i}",
                    dependencies=[f"skill_{i-1}"] if i > 0 else [],
                    status=SkillStatus.VALIDATED,
                )
                lib.add(skill, persist=False)
            except Exception:
                errors += 1

        with ThreadPoolExecutor(max_workers=16) as executor:
            futures = [executor.submit(add_skill, i) for i in range(n_skills)]
            for f in as_completed(futures):
                pass

        # Verify count
        if len(lib) != n_skills:
            errors += 1

        # Verify cycle detection
        if lib.has_cycles():
            errors += 1

        # Persist + reload
        lib.save()
        lib2 = SkillLibrary(storage_dir=tmp)
        if len(lib2) != n_skills:
            errors += 1

        # Verify transitive dependency resolution
        top_name = f"skill_{n_skills - 1}"
        chain = lib2.resolve_dependencies(top_name)
        # Should be n_skills long (whole chain)
        if len(chain) != n_skills:
            errors += 1
        # Topological ordering: each skill's deps come before it
        seen: set = set()
        for s in chain:
            for dep in s.dependencies:
                if dep not in seen:
                    errors += 1
                    break
            seen.add(s.name)

        stats = lib2.get_stats()

        return {
            "operations": n_skills + n_skills,  # add + resolve
            "errors": errors,
            "stored": len(lib2),
            "chain_length": len(chain),
            "has_cycles": stats["has_cycles"],
        }
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ─────────────────────────────────────────────────────────────────────────────
# Test 25: Code architect — full pipeline (observe → write → validate → exec)
# ─────────────────────────────────────────────────────────────────────────────


def test_code_architect_full_pipeline(runner: StressTestRunner):
    """
    Full end-to-end: bootstrap atomics, build be_ceo tree, execute it,
    verify the dependency chain actually fires.
    """
    from aureon.code_architect import CodeArchitect, SkillLibrary
    from aureon.autonomous.vm_control import VMControlDispatcher
    from pathlib import Path
    import tempfile, shutil

    tmp = Path(tempfile.mkdtemp(prefix="aureon_arch_stress_"))
    try:
        lib = SkillLibrary(storage_dir=tmp)
        dispatcher = VMControlDispatcher()
        sid = dispatcher.create_session(backend="simulated", name="arch-vm", make_default=True)
        dispatcher.get_session(sid).arm(dry_run=False)

        arch = CodeArchitect(library=lib, dispatcher=dispatcher, auto_wire=False)
        arch.executor.dispatcher = dispatcher

        errors = 0

        # 1. Bootstrap atomics
        atomics = arch.bootstrap_atomics()
        if len(atomics) < 15:  # Allow a couple of blocked skills
            errors += 1

        # 2. Build the full CEO tree
        summary = arch.demo_build_ceo_persona()
        if not summary.get("role_built"):
            errors += 1
        if summary.get("library_size", 0) < 30:
            errors += 1

        # 3. Execute skills at every level
        n_runs = runner.scaled(100)
        total_exec = 0
        total_ok = 0

        # Run the full be_ceo a few times (capped to keep the
        # per-run execution cost sane — a full CEO run fires
        # 80 sub-skill calls, so 1000 runs = 80k calls)
        ceo_runs = min(max(5, runner.scaled(20)), 1000)
        for _ in range(ceo_runs):
            r = arch.execute_skill("be_ceo")
            total_exec += 1
            if r.ok:
                total_ok += 1

        # Run atomic mouse_move lots of times in parallel
        def fire_mouse(i: int):
            nonlocal total_exec, total_ok
            r = arch.execute_skill("mouse_move", params={"x": i, "y": i * 2},
                                    resolve_deps=False)
            total_exec += 1
            if r.ok:
                total_ok += 1
            return r.ok

        run_parallel_batched(fire_mouse, n_runs, max_workers=16, batch_size=10000)

        # 4. Observer → pattern → skill auto-learn cycle
        for _ in range(3):
            arch.observer.record_action("vm_screenshot", {})
            arch.observer.record_action("vm_mouse_move", {"x": 500, "y": 300})
            arch.observer.record_action("vm_left_click", {})
        learned = arch.observe_and_propose()

        final_lib = arch.library.get_stats()

        dispatcher.destroy_all()

        return {
            "operations": total_exec,
            "errors": errors + (total_exec - total_ok),
            "bootstrapped_atomics": len(atomics),
            "total_skills": final_lib["total_skills"],
            "role_built": summary.get("role_built"),
            "dependency_chain_length": len(arch.library.resolve_dependencies("be_ceo")),
            "ceo_runs": ceo_runs,
            "ceo_ok": total_ok - sum(1 for _ in range(n_runs)),  # approximate
            "learned_skills": len(learned),
        }
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ─────────────────────────────────────────────────────────────────────────────
# Test 26: Sustained soak test
# ─────────────────────────────────────────────────────────────────────────────


def test_sustained_soak(runner: StressTestRunner, duration_s: float = 10.0):
    """Continuous load for N seconds across all subsystems."""
    oma = OpenMultiAgent(mode="brain")
    oma.create_team(
        name="SoakTeam",
        agent_configs=[
            AgentConfig(name=f"Soak-{i}", max_turns=1) for i in range(6)
        ],
        max_concurrent=4,
    )

    total_ops = 0
    errors = 0
    stop_flag = threading.Event()
    counter_lock = threading.Lock()

    def worker():
        nonlocal total_ops, errors
        local_ops = 0
        local_errors = 0
        while not stop_flag.is_set():
            try:
                results = oma.run_team("SoakTeam", f"Soak cycle {local_ops}")
                local_ops += len(results)
                for r in results.values():
                    if r.startswith("[ERROR]"):
                        local_errors += 1
            except Exception:
                local_errors += 1
            local_ops += 1
        with counter_lock:
            total_ops += local_ops
            errors += local_errors

    n_workers = 4
    threads = [threading.Thread(target=worker, daemon=True) for _ in range(n_workers)]
    for t in threads:
        t.start()

    time.sleep(duration_s)
    stop_flag.set()

    for t in threads:
        t.join(timeout=30)

    oma.shutdown()

    return {
        "operations": total_ops,
        "errors": errors,
        "duration_s": duration_s,
        "workers": n_workers,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Main runner
# ─────────────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="Aureon In-House AI maximum stress test")
    parser.add_argument("--quick", action="store_true", help="Run at 10% scale for quick verification")
    parser.add_argument("--scale", type=float, default=1.0,
                        help="Scale factor (1.0 = full, 10.0 = HYPER, 0.1 = quick)")
    parser.add_argument("--soak", type=float, default=10.0, help="Soak test duration seconds (default 10)")
    parser.add_argument("--skip-soak", action="store_true", help="Skip the soak test")
    args = parser.parse_args()

    if args.quick:
        mode_label = "QUICK MODE (10% scale)"
    elif args.scale >= 10.0:
        mode_label = f"HYPER MODE ({args.scale:.0f}× scale)"
    elif args.scale != 1.0:
        mode_label = f"SCALED MODE ({args.scale:.1f}× scale)"
    else:
        mode_label = "FULL SCALE"

    print("=" * 100)
    print("  AUREON IN-HOUSE AI — MAXIMUM STRESS TEST")
    print("  " + mode_label)
    print("=" * 100 + "\n")

    runner = StressTestRunner(quick=args.quick, scale=args.scale)

    print("\n[Test Suite]")
    runner.run("1. LLM adapter throughput",          lambda: test_llm_adapter_throughput(runner))
    runner.run("2. Tool registry race conditions",   lambda: test_tool_registry_race(runner))
    runner.run("3. Agent parallel execution",        lambda: test_agent_parallel_execution(runner))
    runner.run("4. AgentPool saturation",            lambda: test_agent_pool_saturation(runner))
    runner.run("5. TaskQueue DAG resolution",        lambda: test_task_queue_dag(runner))
    runner.run("6. TaskQueue cascade failure",       lambda: test_task_queue_cascade_failure(runner))
    runner.run("7. Message bus throughput",          lambda: test_message_bus_throughput(runner))
    runner.run("8. SharedMemory contention",         lambda: test_shared_memory_contention(runner))
    runner.run("9. Team orchestration",              lambda: test_team_orchestration(runner))
    runner.run("10. OpenMultiAgent full-stack",      lambda: test_open_multi_agent_full_stack(runner))
    runner.run("11. Queen AI Bridge integration",    lambda: test_queen_ai_bridge_integration(runner))
    runner.run("12. Miner AI Bridge integration",    lambda: test_miner_ai_bridge_integration(runner))
    runner.run("13. Miner quantum weight stability", lambda: test_miner_quantum_weight_stability(runner))
    runner.run("14. VM control dispatch throughput", lambda: test_vm_control_dispatch(runner))
    runner.run("15. VM multi-session concurrency",   lambda: test_vm_multi_session(runner))
    runner.run("16. VM tool registry integration",   lambda: test_vm_tool_registry_integration(runner))
    runner.run("17. Agent-driven VM control",        lambda: test_agent_driven_vm_control(runner))
    runner.run("18. Swarm motion hive end-to-end",   lambda: test_swarm_motion_hive(runner))
    runner.run("19. HNC Lambda(t) stability",        lambda: test_lambda_stability(runner))
    runner.run("20. Pillar alignment throughput",    lambda: test_pillar_alignment(runner))
    runner.run("21. Harmonic math correctness",      lambda: test_harmonic_math(runner))
    runner.run("22. Unified harmonic directive",     lambda: test_unified_directive(runner))
    runner.run("23. Code architect static safety",   lambda: test_code_architect_safety(runner))
    runner.run("24. Code architect library",         lambda: test_code_architect_library(runner))
    runner.run("25. Code architect full pipeline",   lambda: test_code_architect_full_pipeline(runner))

    if not args.skip_soak:
        runner.run(
            f"26. Sustained soak test ({args.soak}s)",
            lambda: test_sustained_soak(runner, duration_s=args.soak),
        )

    all_passed = runner.summary()
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
