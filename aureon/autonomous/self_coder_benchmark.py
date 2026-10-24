"""Reproducible self-coder benchmark harness.

The system under test is Aureon's internal cognition: the Auris nodes,
the QGITA FTCP detector, and ``run_self_coding_task`` as it runs with
its lane off. No outside LLM is required and none is called unless
``AUREON_SELF_CODER_ALLOW_EXTERNAL=1``. That opt-in is labelled and is
not Aureon's brain. Published Kimi K2.5 figures are an external
reference named by the operator. They are not this process's score.
A fixture is not a result.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import sys
from pathlib import Path
from typing import Any

from aureon.autonomous.aureon_internal_self_coder import openai_compatible_model_endpoint

INTERNAL_SEED = 20261024

HARNESS_NOTE = (
    "The system under test is Aureon's internal cognition: Auris nodes, "
    "the QGITA FTCP detector, and run_self_coding_task with its default "
    "lane off. No outside LLM is called unless AUREON_SELF_CODER_ALLOW_EXTERNAL=1. "
    "That opt-in is not Aureon's brain and is labelled in the report. "
    "An API key is not required. "
    "Python the internal path actually emits is executed against each row's tests field. "
    "This is not the official SWE-bench or LiveCodeBench evaluation. "
    "This is not a kernel sandbox. The child runs only inside unshare "
    "(user, pid, and net namespace) from an environment that never held "
    "the keys. Inside that namespace, home and the workspace are covered "
    "with a tmpfs when that mount works. The opt-in path does not mount "
    "over the parent. If unshare is missing or the probe fails, model code "
    "is not run unless AUREON_BENCH_ALLOW_UNSANDBOXED=1. That opt-in is "
    "unsandboxed: a same-user child can read /proc/PID/environ and can "
    "open a raw socket. Run this only on a machine with no secrets."
)

_NAMESPACE_READY: bool | None = None
_LAST_CHILD_MODE: str | None = None


class BenchmarkChildRefused(RuntimeError):
    """Model code was not started. The sandbox was unavailable and unsandboxed mode was not opted in."""

PUBLISHED_KIMI_K2_5 = {
    "model": "Kimi K2.5",
    "swe_bench_verified_pct": 76.8,
    "livecodebench_v6_pct": 85.0,
    "source": "published score named by the operator; not a measurement from this harness",
}


def _dataset_present(root: Path, name: str) -> bool:
    return (root / "data" / "benchmarks" / name).is_dir()


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            item = json.loads(line)
            if isinstance(item, dict):
                rows.append(item)
    return rows


def _humaneval_path(root: Path) -> Path | None:
    """Public HumanEval jsonl, if this checkout already has it. No download."""

    override = (os.environ.get("AUREON_SELF_CODER_HUMANEVAL_PATH") or "").strip()
    if override:
        path = Path(override)
        return path if path.is_file() else None
    path = root / "data" / "research" / "open_benchmarks" / "humaneval.jsonl"
    return path if path.is_file() else None


def humaneval_tests(row: dict[str, Any]) -> str:
    """Turn one HumanEval row into the check the harness appends."""

    entry = str(row.get("entry_point") or "").strip()
    body = str(row.get("test") or "")
    if not entry or not body:
        return ""
    return body + f"\ncheck({entry})\n"


def humaneval_reference_program(row: dict[str, Any]) -> str:
    """The dataset's own solution. This is not a model reply."""

    return str(row.get("prompt") or "") + str(row.get("canonical_solution") or "")


def _dataset_file(root: Path, folder: str, env_name: str) -> Path | None:
    override = (os.environ.get(env_name) or "").strip()
    if override:
        path = Path(override)
        return path if path.is_file() else None
    directory = root / "data" / "benchmarks" / folder
    if not directory.is_dir():
        return None
    files = sorted(directory.glob("*.jsonl"))
    return files[0] if files else None


def _fetch_dataset(url: str, dest: Path) -> Path:
    import urllib.request

    dest.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(url, dest)
    return dest


def _chat(endpoint: dict[str, Any], prompt: str) -> dict[str, Any]:
    """One OpenAI-compatible chat call. Ollama's /v1/chat/completions uses this shape."""

    import urllib.error
    import urllib.request

    url = endpoint["base_url"].rstrip("/") + "/chat/completions"
    body = json.dumps(
        {
            "model": endpoint["model"],
            "temperature": 0,
            "messages": [{"role": "user", "content": prompt}],
        }
    ).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    key = (os.environ.get("AUREON_SELF_CODER_API_KEY") or "").strip()
    if key:
        headers["Authorization"] = f"Bearer {key}"
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        return {"ok": False, "error": str(exc.reason if hasattr(exc, "reason") else exc), "text": ""}
    except Exception as exc:
        return {"ok": False, "error": f"{exc.__class__.__name__}: {exc}", "text": ""}
    text = ""
    try:
        text = str(payload["choices"][0]["message"]["content"])
    except (KeyError, IndexError, TypeError):
        return {"ok": False, "error": "model response had no message content", "text": ""}
    return {"ok": True, "error": "", "text": text}


def _scrubbed_child_env(home: Path) -> dict[str, str]:
    """Environment for model-written code. No parent secrets and no AUREON_*."""

    path = os.environ.get("PATH") or "/usr/bin:/bin"
    return {
        "PATH": path,
        "HOME": str(home),
        "USERPROFILE": str(home),
        "TMPDIR": str(home),
        "TEMP": str(home),
        "TMP": str(home),
        "LANG": "C",
        "LC_ALL": "C",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTHONSAFEPATH": "1",
        "PYTHONUNBUFFERED": "1",
    }


def _unsandboxed_allowed() -> bool:
    return os.environ.get("AUREON_BENCH_ALLOW_UNSANDBOXED", "").strip() == "1"


def _namespace_command(runner: Path) -> list[str] | None:
    """Launch command whose own environment never held the parent keys.

    A successful probe is remembered. A missing ``unshare``, a failed probe,
    or a timeout is not remembered, so the next call tries again. ``unshare``
    is pid 1 inside a new user, pid, and net namespace.
    """

    import shutil
    import subprocess

    global _NAMESPACE_READY
    if _NAMESPACE_READY is True:
        command = _unshare_argv(runner)
        if command is None:
            _NAMESPACE_READY = None
        return command
    _NAMESPACE_READY = None
    unshare = shutil.which("unshare")
    if not unshare:
        return None
    command = _unshare_argv(runner)
    if command is None:
        return None
    try:
        probe = subprocess.run(
            command[:-1] + ["-c", "import socket; raise SystemExit(0)"],
            cwd=runner.parent,
            env=_scrubbed_child_env(runner.parent),
            capture_output=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if probe.returncode != 0:
        return None
    _NAMESPACE_READY = True
    return command


def _unshare_argv(runner: Path) -> list[str] | None:
    import shutil

    unshare = shutil.which("unshare")
    if not unshare:
        return None
    return [
        unshare,
        "--user",
        "--map-root-user",
        "--mount",
        "--propagation",
        "private",
        "--net",
        "--pid",
        "--fork",
        "--mount-proc",
        sys.executable,
        "-I",
        str(runner),
    ]


def _run_python(code: str, tests: str, timeout: int = 20) -> bool:
    """Run model Python only from a sandboxed spawn, unless the operator opts in.

    The spawn uses a fresh environment, not a filtered copy of the parent.
    Without a working ``unshare`` probe the child is not started, so a
    same-user read of ``/proc/PID/environ`` and a raw socket connect do not
    happen. ``AUREON_BENCH_ALLOW_UNSANDBOXED=1`` is the explicit opt-in for
    that unsandboxed path. This is not a kernel sandbox. Run it only on a
    machine with no secrets.
    """

    import subprocess
    import tempfile

    global _LAST_CHILD_MODE, _NAMESPACE_READY
    runner = (
        "import os, subprocess, sys\n"
        "def _hide_host_dirs():\n"
        "    if os.environ.get('BENCH_CHILD_MOUNT_NS') != '1':\n"
        "        return\n"
        "    if os.geteuid() != 0:\n"
        "        return\n"
        "    try:\n"
        "        subprocess.check_call(['mount', '--make-rprivate', '/'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)\n"
        "    except Exception:\n"
        "        return\n"
        "    roots = []\n"
        "    for item in (sys.base_prefix, sys.prefix):\n"
        "        try:\n"
        "            roots.append(os.path.realpath(item))\n"
        "        except Exception:\n"
        "            continue\n"
        "    def relation(path):\n"
        "        try:\n"
        "            path = os.path.realpath(path)\n"
        "        except Exception:\n"
        "            return 'cover'\n"
        "        for root in roots:\n"
        "            if path == root or path.startswith(root + os.sep):\n"
        "                return 'keep'\n"
        "            if root.startswith(path + os.sep):\n"
        "                return 'descend'\n"
        "        return 'cover'\n"
        "    def cover(path):\n"
        "        try:\n"
        "            if os.path.isdir(path) and not os.path.islink(path):\n"
        "                subprocess.check_call(['mount', '-t', 'tmpfs', '-o', 'nosuid,nodev,noexec', 'tmpfs', path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)\n"
        "            elif os.path.isfile(path):\n"
        "                subprocess.check_call(['mount', '--bind', '/dev/null', path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)\n"
        "        except Exception:\n"
        "            return\n"
        "    def walk(path):\n"
        "        if not os.path.exists(path):\n"
        "            return\n"
        "        kind = relation(path)\n"
        "        if kind == 'keep':\n"
        "            return\n"
        "        if kind == 'cover':\n"
        "            cover(path)\n"
        "            return\n"
        "        if os.path.isdir(path) and not os.path.islink(path):\n"
        "            try:\n"
        "                names = os.listdir(path)\n"
        "            except OSError:\n"
        "                return\n"
        "            for name in names:\n"
        "                walk(os.path.join(path, name))\n"
        "    for path in ('/home', '/root', '/workspace'):\n"
        "        walk(path)\n"
        "_hide_host_dirs()\n"
        "import socket\n"
        "def _blocked(*_args, **_kwargs):\n"
        "    raise OSError('network is disabled for the benchmark child')\n"
        "socket.socket = _blocked\n"
        "socket.create_connection = _blocked\n"
        "import runpy\n"
        "runpy.run_path('solution.py', run_name='__main__')\n"
    )
    try:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "solution.py").write_text(code + "\n\n" + tests + "\n", encoding="utf-8")
            script = root / "runner.py"
            script.write_text(runner, encoding="utf-8")
            command = _namespace_command(script)
            if command is None:
                if not _unsandboxed_allowed():
                    _LAST_CHILD_MODE = "refused"
                    raise BenchmarkChildRefused(
                        "model code was not run: sandbox is unavailable and "
                        "AUREON_BENCH_ALLOW_UNSANDBOXED=1 is not set"
                    )
                _LAST_CHILD_MODE = "unsandboxed-opt-in"
                command = [sys.executable, "-I", str(script)]
            else:
                _LAST_CHILD_MODE = "namespace"
            child_env = _scrubbed_child_env(root)
            if _LAST_CHILD_MODE == "namespace":
                child_env["BENCH_CHILD_MOUNT_NS"] = "1"
            completed = subprocess.run(
                command,
                cwd=directory,
                env=child_env,
                capture_output=True,
                timeout=timeout,
                check=False,
            )
            return completed.returncode == 0
    except BenchmarkChildRefused:
        raise
    except subprocess.TimeoutExpired:
        return False
    except OSError:
        if _LAST_CHILD_MODE == "namespace":
            _LAST_CHILD_MODE = "refused"
            _NAMESPACE_READY = None
        return False


def _score_livecode(rows: list[dict[str, Any]], endpoint: dict[str, Any]) -> dict[str, Any]:
    passed = 0
    failures: list[str] = []
    for row in rows:
        prompt = str(row.get("prompt") or row.get("question") or "")
        tests = str(row.get("tests") or "")
        if not prompt or not tests:
            failures.append(str(row.get("question_id") or "missing-fields"))
            continue
        reply = _chat(endpoint, prompt + "\nReply with Python only.")
        if not reply["ok"]:
            return {
                "suite": "LiveCodeBench",
                "executed": False,
                "passed": passed,
                "total": len(rows),
                "reason": reply["error"],
            }
        try:
            ok = _run_python(reply["text"], tests)
        except BenchmarkChildRefused as exc:
            return {
                "suite": "LiveCodeBench",
                "executed": False,
                "passed": passed,
                "total": len(rows),
                "reason": str(exc),
            }
        if ok:
            passed += 1
        else:
            failures.append(str(row.get("question_id") or "failed"))
    total = len(rows)
    return {
        "suite": "LiveCodeBench",
        "executed": total > 0,
        "passed": passed,
        "total": total,
        "failures": failures,
        "measured_pct": round(100.0 * passed / total, 2) if total else None,
    }


def _score_swe(rows: list[dict[str, Any]], endpoint: dict[str, Any]) -> dict[str, Any]:
    passed = 0
    failures: list[str] = []
    for row in rows:
        prompt = str(row.get("problem_statement") or row.get("prompt") or "")
        tests = str(row.get("tests") or "")
        if not prompt or not tests:
            failures.append(str(row.get("instance_id") or "missing-fields"))
            continue
        reply = _chat(endpoint, prompt + "\nReply with Python only. Do not place an order.")
        if not reply["ok"]:
            return {
                "suite": "SWE-bench Lite or Verified",
                "executed": False,
                "passed": passed,
                "total": len(rows),
                "reason": reply["error"],
            }
        try:
            ok = _run_python(reply["text"], tests)
        except BenchmarkChildRefused as exc:
            return {
                "suite": "SWE-bench Lite or Verified",
                "executed": False,
                "passed": passed,
                "total": len(rows),
                "reason": str(exc),
            }
        if ok:
            passed += 1
        else:
            failures.append(str(row.get("instance_id") or "failed"))
    total = len(rows)
    return {
        "suite": "SWE-bench Lite or Verified",
        "executed": total > 0,
        "passed": passed,
        "total": total,
        "failures": failures,
        "measured_pct": round(100.0 * passed / total, 2) if total else None,
    }


def _external_allowed() -> bool:
    return os.environ.get("AUREON_SELF_CODER_ALLOW_EXTERNAL", "").strip() == "1"


def _prompt_draw(task_id: str, prompt: str) -> tuple[dict[str, float], list[float]]:
    """Fixed draw from the public row. The seed is the task, not the clock."""

    digest = hashlib.sha256(f"{INTERNAL_SEED}\n{task_id}\n{prompt}".encode("utf-8")).digest()
    rng = random.Random(int.from_bytes(digest[:8], "big"))
    momentum = rng.uniform(-1.0, 1.0)
    features = {
        "volatility": rng.random(),
        "momentum": momentum,
        "volume": rng.random(),
        "spread": rng.random(),
    }
    series = [rng.uniform(-1.0, 1.0) for _ in range(16)]
    return features, series


def _auris_on_features(features: dict[str, float]) -> dict[str, Any]:
    from aureon.utils.aureon_queen_hive_mind import QueenHiveMind

    queen = QueenHiveMind.__new__(QueenHiveMind)
    reading = queen.read_auris_nodes(features)
    coherence, status = queen.get_auris_coherence(features)
    nodes = {name: float(item["value"]) for name, item in reading.items()}
    return {
        "nodes": nodes,
        "coherence": float(coherence),
        "coherence_status": status,
    }


def _qgita_on_series(series: list[float]) -> dict[str, Any]:
    import numpy as np

    from aureon.wisdom.aureon_qgita_framework import FTCPDetector

    detector = FTCPDetector()
    times = np.arange(len(series), dtype=float)
    found = detector.detect_ftcps(times, np.array(series, dtype=float))
    valid = [item for item in found if item.is_valid]
    return {
        "points": len(found),
        "valid_points": len(valid),
        "max_g_eff": max((float(item.g_eff) for item in valid), default=None),
    }


def _score_internal_humaneval(root: Path, rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Run the internal path on HumanEval. A hold receipt is not a program."""

    from aureon.autonomous.aureon_self_run_coding_task import run_self_coding_task

    passed = 0
    attempted = 0
    results: list[dict[str, Any]] = []
    pipeline_error = ""
    for row in rows:
        task_id = str(row.get("task_id") or "missing-fields")
        prompt = str(row.get("prompt") or "")
        tests = humaneval_tests(row)
        features, series = _prompt_draw(task_id, prompt)
        auris: dict[str, Any] | None = None
        qgita: dict[str, Any] | None = None
        try:
            auris = _auris_on_features(features)
            qgita = _qgita_on_series(series)
        except Exception as exc:
            pipeline_error = f"{exc.__class__.__name__}: {exc}"
        coder = run_self_coding_task(root, prompt, enabled=False)
        summary = coder.get("summary") if isinstance(coder.get("summary"), dict) else {}
        raw_program = coder.get("program")
        program = raw_program if isinstance(raw_program, str) else ""
        sandbox = "not run"
        ok = False
        reason = str(summary.get("reason_code") or coder.get("status") or "no Python program emitted")
        if program.strip() and tests:
            attempted += 1
            try:
                ok = _run_python(program, tests)
                sandbox = "passed" if ok else "failed"
            except BenchmarkChildRefused as exc:
                return {
                    "suite": "HumanEval",
                    "system_under_test": "internal",
                    "seed": INTERNAL_SEED,
                    "executed": False,
                    "passed": passed,
                    "attempted": attempted,
                    "not_attempted": len(rows) - attempted,
                    "total": len(rows),
                    "rows": len(rows),
                    "status": "HOLD",
                    "counts_as_aureon_score": False,
                    "counts_as_model_score": False,
                    "external_provider_called": False,
                    "measured_pct": None,
                    "reason": str(exc),
                    "results": results,
                }
        if ok:
            passed += 1
        results.append(
            {
                "task_id": task_id,
                "auris": auris,
                "qgita": qgita,
                "self_coder_status": coder.get("status"),
                "self_coder_reason": summary.get("reason_code"),
                "program_emitted": bool(program.strip()),
                "sandbox": sandbox,
                "passed": ok,
                "external_provider_called": False,
                "reason": reason,
            }
        )
    total = len(rows)
    not_attempted = total - attempted
    if total == 0:
        status = "not_attempted"
        measured = None
        reason = "no HumanEval rows were loaded"
    else:
        status = "measured"
        measured = round(100.0 * passed / total, 2)
        reason = (
            "the internal path emitted no Python program, so the sandbox was not given a candidate"
            if attempted == 0
            else ""
        )
    if pipeline_error and attempted == 0:
        reason = f"{reason}; pipeline error: {pipeline_error}"
    return {
        "suite": "HumanEval",
        "system_under_test": (
            "Auris read_auris_nodes, QGITA FTCPDetector, "
            "aureon.autonomous.aureon_self_run_coding_task.run_self_coding_task"
        ),
        "seed": INTERNAL_SEED,
        "executed": total > 0,
        "passed": passed,
        "attempted": attempted,
        "not_attempted": not_attempted,
        "total": total,
        "rows": total,
        "status": status,
        "counts_as_aureon_score": total > 0,
        "counts_as_model_score": False,
        "external_provider_called": False,
        "measured_pct": measured,
        "self_coder_lane": "disabled; run_self_coding_task defaults to enabled=False and does not call a model",
        "authoring_note": (
            "InternalCodingWorkforce.decide calls an adapter prompt. "
            "That step is not reached while the self-coder lane is disabled "
            "and AUREON_SELF_CODER_ALLOW_EXTERNAL is off."
        ),
        "reason": reason,
        "results": results,
    }


def _score_humaneval(rows: list[dict[str, Any]], endpoint: dict[str, Any]) -> dict[str, Any]:
    """Score model replies on HumanEval. The dataset solution is not the reply."""

    passed = 0
    failures: list[str] = []
    for row in rows:
        prompt = str(row.get("prompt") or "")
        tests = humaneval_tests(row)
        task_id = str(row.get("task_id") or "missing-fields")
        if not prompt or not tests:
            failures.append(task_id)
            continue
        reply = _chat(endpoint, prompt + "\nReply with Python only. Include the function.")
        if not reply["ok"]:
            return {
                "suite": "HumanEval",
                "executed": False,
                "passed": passed,
                "total": len(rows),
                "status": "HOLD",
                "counts_as_model_score": False,
                "reason": reply["error"],
            }
        try:
            ok = _run_python(reply["text"], tests)
        except BenchmarkChildRefused as exc:
            return {
                "suite": "HumanEval",
                "executed": False,
                "passed": passed,
                "total": len(rows),
                "status": "HOLD",
                "counts_as_model_score": False,
                "reason": str(exc),
            }
        if ok:
            passed += 1
        else:
            failures.append(task_id)
    total = len(rows)
    return {
        "suite": "HumanEval",
        "executed": total > 0,
        "passed": passed,
        "total": total,
        "failures": failures,
        "status": "measured" if total else "HOLD",
        "counts_as_model_score": total > 0,
        "measured_pct": round(100.0 * passed / total, 2) if total else None,
        "reason": "",
    }


def _hold_humaneval(path: Path | None, reason: str) -> dict[str, Any]:
    rows = 0
    if path is not None and path.is_file():
        rows = sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
    return {
        "suite": "HumanEval",
        "dataset": str(path or ""),
        "executed": False,
        "passed": None,
        "total": rows,
        "rows": rows,
        "status": "HOLD",
        "counts_as_model_score": False,
        "measured_pct": None,
        "reason": reason,
    }


def _internal_suite_absent(name: str) -> dict[str, Any]:
    return {
        "suite": name,
        "executed": False,
        "measured_pct": None,
        "external_provider_called": False,
        "counts_as_aureon_score": False,
        "reason": "outside provider is off by default; this suite has no internal runner",
    }


def run_harness(root: Path | None = None) -> dict[str, Any]:
    """Score HumanEval with the internal path. An outside model is opt-in."""

    root = Path(root or Path.cwd())
    endpoint = openai_compatible_model_endpoint()
    endpoint["ollama_openai_compatible"] = True
    allowed = _external_allowed()
    humaneval_file = _humaneval_path(root)
    if humaneval_file is None:
        humaneval = _hold_humaneval(None, "HumanEval jsonl is not in this checkout")
        humaneval["status"] = "not_attempted"
        humaneval["attempted"] = 0
        humaneval["not_attempted"] = 0
        humaneval["external_provider_called"] = False
        humaneval["counts_as_aureon_score"] = False
    else:
        humaneval = _score_internal_humaneval(root, _load_jsonl(humaneval_file))
        humaneval["dataset"] = str(humaneval_file)
    aureon_pct = humaneval.get("measured_pct") if humaneval.get("counts_as_aureon_score") else None
    external: dict[str, Any] = {
        "enabled": allowed,
        "called": False,
        "default": "off",
        "opt_in": "AUREON_SELF_CODER_ALLOW_EXTERNAL=1",
        "api_key_required": False,
        "api_key_configured": bool(endpoint.get("api_key_configured")),
        "api_key_returned": False,
        "base_url": endpoint.get("base_url"),
        "model": endpoint.get("model"),
        "counts_as_aureon_brain": False,
        "humaneval_pct": None,
        "swe_bench_pct": None,
        "livecodebench_pct": None,
        "note": (
            "An outside provider is not Aureon's brain. "
            "The call stays off unless AUREON_SELF_CODER_ALLOW_EXTERNAL=1."
        ),
    }
    probe = {"ok": False, "error": ""}
    if allowed:
        fetch = os.environ.get("AUREON_SELF_CODER_BENCH_FETCH", "").strip() in {"1", "true", "yes"}
        swe_path = _dataset_file(root, "swebench", "AUREON_SELF_CODER_SWE_PATH")
        live_path = _dataset_file(root, "livecodebench", "AUREON_SELF_CODER_LIVECODE_PATH")
        if swe_path is None and fetch and (os.environ.get("AUREON_SELF_CODER_SWE_URL") or "").strip():
            swe_path = _fetch_dataset(
                os.environ["AUREON_SELF_CODER_SWE_URL"].strip(),
                root / "data" / "benchmarks" / "swebench" / "instances.jsonl",
            )
        if live_path is None and fetch and (os.environ.get("AUREON_SELF_CODER_LIVECODE_URL") or "").strip():
            live_path = _fetch_dataset(
                os.environ["AUREON_SELF_CODER_LIVECODE_URL"].strip(),
                root / "data" / "benchmarks" / "livecodebench" / "problems.jsonl",
            )
        probe = _chat(endpoint, "Reply with the single word ready.")
        external["called"] = True
        if probe["ok"]:
            swe_rows = _load_jsonl(swe_path) if swe_path else []
            live_rows = _load_jsonl(live_path) if live_path else []
            swe_ext = _score_swe(swe_rows, endpoint) if swe_rows else {
                "executed": False,
                "measured_pct": None,
                "reason": "dataset path was not provided and no fetch URL was set",
            }
            live_ext = _score_livecode(live_rows, endpoint) if live_rows else {
                "executed": False,
                "measured_pct": None,
                "reason": "dataset path was not provided and no fetch URL was set",
            }
            external["swe_bench_pct"] = swe_ext.get("measured_pct")
            external["livecodebench_pct"] = live_ext.get("measured_pct")
            external["swe_bench"] = swe_ext
            external["livecodebench"] = live_ext
            if humaneval_file is not None:
                external_he = _score_humaneval(_load_jsonl(humaneval_file), endpoint)
                external["humaneval_pct"] = (
                    external_he.get("measured_pct") if external_he.get("counts_as_model_score") else None
                )
                external["humaneval"] = {
                    "passed": external_he.get("passed"),
                    "total": external_he.get("total"),
                    "measured_pct": external["humaneval_pct"],
                    "status": external_he.get("status"),
                    "counts_as_aureon_brain": False,
                    "reason": external_he.get("reason"),
                }
        else:
            external["error"] = probe["error"]
    swe = _internal_suite_absent("SWE-bench Lite or Verified")
    live = _internal_suite_absent("LiveCodeBench")
    comparison_reason = (
        "this run's HumanEval figure is the internal path; published figures are an external reference"
        if aureon_pct is not None
        else "this run has no internal HumanEval score to set beside a published figure"
    )
    return {
        "schema": "aureon.self-coder-benchmark.v2",
        "system_under_test": "internal",
        "endpoint": endpoint,
        "external_provider": external,
        "offline_fixture": {
            "suite": "offline-fixture",
            "executed": False,
            "counts_as_result": False,
            "reason": "a fixture is not a benchmark result",
        },
        "model_call": {
            "attempted": external["called"],
            "ok": bool(probe["ok"]) if external["called"] else False,
            "error": probe["error"] if external["called"] else "",
            "external_provider": external["called"],
        },
        "swe_bench": swe,
        "livecodebench": live,
        "humaneval": humaneval,
        "published_reference": PUBLISHED_KIMI_K2_5,
        "flagship_comparison": {
            "status": "measured" if aureon_pct is not None else "HOLD",
            "this_run_swe_bench_pct": None,
            "this_run_livecodebench_pct": None,
            "this_run_humaneval_pct": aureon_pct,
            "published_references_are_not_this_run": True,
            "published_references": [PUBLISHED_KIMI_K2_5],
            "reason": comparison_reason,
        },
        "harness": HARNESS_NOTE,
        "child_isolation": {
            "namespace": "unshare user, pid, and net namespace; home and workspace on tmpfs when the mount works",
            "unsandboxed-opt-in": "AUREON_BENCH_ALLOW_UNSANDBOXED=1; not a kernel sandbox",
            "refused": "refused; sandbox unavailable and AUREON_BENCH_ALLOW_UNSANDBOXED is not 1",
        }.get(_LAST_CHILD_MODE or "", "child was not launched"),
        "model_python_task_pass_pct": {
            "swe_rows": None,
            "livecode_rows": None,
            "humaneval_rows": aureon_pct,
        },
        "live_trading": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Score the internal cognition path on HumanEval")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--fetch", action="store_true")
    args = parser.parse_args(argv)
    if args.fetch:
        os.environ["AUREON_SELF_CODER_BENCH_FETCH"] = "1"
    report = run_harness(args.root)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["humaneval"].get("executed") or report["humaneval"].get("status") == "not_attempted" else 1


if __name__ == "__main__":
    raise SystemExit(main())
