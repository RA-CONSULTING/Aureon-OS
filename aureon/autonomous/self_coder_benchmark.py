"""Reproducible self-coder benchmark harness.

The model is called, and its Python is run against each row's ``tests``
field. That is not the official SWE-bench or LiveCodeBench evaluation.
Published Kimi K2.5 figures are a reference named by the operator. They
are not this process's score. A fixture is not a result.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from aureon.autonomous.aureon_internal_self_coder import openai_compatible_model_endpoint

HARNESS_NOTE = (
    "model-written Python is executed against each row's tests field. "
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


def run_harness(root: Path | None = None) -> dict[str, Any]:
    """Call the configured model and score the datasets. A fixture is not a result."""

    root = Path(root or Path.cwd())
    endpoint = openai_compatible_model_endpoint()
    endpoint["ollama_openai_compatible"] = True
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
    swe_rows = _load_jsonl(swe_path) if swe_path else []
    live_rows = _load_jsonl(live_path) if live_path else []
    if not probe["ok"]:
        swe = {"suite": "SWE-bench Lite or Verified", "executed": False, "reason": probe["error"], "dataset": str(swe_path or "")}
        live = {"suite": "LiveCodeBench", "executed": False, "reason": probe["error"], "dataset": str(live_path or "")}
        swe_pct = None
        live_pct = None
    else:
        swe = _score_swe(swe_rows, endpoint) if swe_rows else {
            "suite": "SWE-bench Lite or Verified",
            "executed": False,
            "reason": "dataset path was not provided and no fetch URL was set",
        }
        live = _score_livecode(live_rows, endpoint) if live_rows else {
            "suite": "LiveCodeBench",
            "executed": False,
            "reason": "dataset path was not provided and no fetch URL was set",
        }
        swe_pct = swe.get("measured_pct")
        live_pct = live.get("measured_pct")
    return {
        "schema": "aureon.self-coder-benchmark.v1",
        "endpoint": endpoint,
        "offline_fixture": {
            "suite": "offline-fixture",
            "executed": False,
            "counts_as_result": False,
            "reason": "a fixture is not a benchmark result",
        },
        "model_call": {"attempted": True, "ok": probe["ok"], "error": probe["error"]},
        "swe_bench": swe,
        "livecodebench": live,
        "published_reference": PUBLISHED_KIMI_K2_5,
        "harness": HARNESS_NOTE,
        "child_isolation": {
            "namespace": "unshare user, pid, and net namespace; home and workspace on tmpfs when the mount works",
            "unsandboxed-opt-in": "AUREON_BENCH_ALLOW_UNSANDBOXED=1; not a kernel sandbox",
            "refused": "refused; sandbox unavailable and AUREON_BENCH_ALLOW_UNSANDBOXED is not 1",
        }.get(_LAST_CHILD_MODE or "", "child was not launched"),
        "model_python_task_pass_pct": {
            "swe_rows": swe_pct,
            "livecode_rows": live_pct,
        },
        "live_trading": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Call the configured model and score SWE-bench and LiveCodeBench")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--fetch", action="store_true")
    args = parser.parse_args(argv)
    if args.fetch:
        os.environ["AUREON_SELF_CODER_BENCH_FETCH"] = "1"
    report = run_harness(args.root)
    print(json.dumps(report, indent=2, sort_keys=True))
    scores = report["model_python_task_pass_pct"]
    measured = scores.get("swe_rows") is not None or scores.get("livecode_rows") is not None
    return 0 if measured or report["model_call"]["attempted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
