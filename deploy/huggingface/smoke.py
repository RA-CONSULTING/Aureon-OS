#!/usr/bin/env python3
"""Fail-closed acceptance checks for the public Aureon GPU Space.

No prompt, completion, credential, or internal bearer value is written to the
receipt. This is a deployment probe, not a model-quality benchmark.
"""
from __future__ import annotations

import concurrent.futures
import json
import os
import re
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

EXPECTED_HASH = "48487f800623474ab99371d71b369694cae64f8ebc4ef038019c7e60da3d45bb"
EXPECTED_SIZE = 13_990_806_664
EXPECTED_MODEL = "aureon-7b-v65k"
EXPECTED_PROVIDER = "aureon_own_model"
PUBLIC_READS = (
    "/api/status",
    "/api/organism",
    "/api/cognition/field",
    "/api/demo/status",
    "/api/hnc/status",
    "/api/hnc/replay",
    "/api/hnc/organism-replay",
    "/fusion/api/status",
    "/hnc",
    "/hnc/",
    "/app/",
    "/",
)
SENSITIVE_READS = (
    "/api/credentials",
    "/api/terminal-state",
    "/api/providers",
    "/api/connections",
    "/api/approvals",
    "/api/switchboard",
    "/api/pulse",
    "/api/fleet",
    "/api/mcp/tools",
    "/api/seats",
    "/fusion/api/capital_release.flag",
    "/fusion/api/provider",
)
MUTATIONS = (
    "/api/operator/ask",
    "/api/capital/order",
    "/fusion/api/command",
    "/fusion/api/control",
    "/mcp/invoke",
)
REQUIRED_PROCESSES = (
    "redis",
    "postgres",
    "error_sink",
    "aureon_model",
    "api_a",
    "api_b",
    "operator",
    "demo_api",
    "frontend",
    "fleet",
    "hnc_core",
    "nginx",
)


@dataclass
class Check:
    name: str
    ok: bool
    detail: str = ""


def validate_readiness(body: Any, revision: str) -> list[str]:
    """Return stable failure labels; never include upstream values or secrets."""
    failures: list[str] = []
    if not isinstance(body, dict):
        return ["payload"]
    if body.get("ready") is not True or body.get("ok") is not True:
        failures.append("aggregate")
    if body.get("provider_mode") != EXPECTED_PROVIDER or body.get("model") != EXPECTED_MODEL:
        failures.append("attribution")
    if body.get("live_trading") is not False or body.get("orders_placed") != 0:
        failures.append("paper_only")
    checks = body.get("checks")
    checks = checks if isinstance(checks, dict) else {}
    posture = checks.get("public_posture")
    if not isinstance(posture, dict) or posture.get("ok") is not True:
        failures.append("public_posture")
    operator = checks.get("operator")
    if not isinstance(operator, dict) or operator.get("ok") is not True:
        failures.append("operator")
    model = checks.get("model")
    model = model if isinstance(model, dict) else {}
    model_checks = model.get("checks")
    model_checks = model_checks if isinstance(model_checks, dict) else {}
    if model.get("ok") is not True or not all(model_checks.get(name) is True for name in (
        "ready", "provider_mode", "model", "immutable_revision", "weight_sha256",
        "weight_size_bytes", "parameters", "vocabulary", "eos", "cuda",
        "startup_generation_verified", "startup_generation_tokens",
    )):
        failures.append("model_evidence")
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        failures.append("configured_revision")
    return failures


class Acceptance:
    def __init__(self) -> None:
        self.base = os.environ.get("AUREON_SMOKE_BASE_URL", "http://127.0.0.1:7860").rstrip("/")
        self.revision = os.environ.get("AUREON_MODEL_REVISION", "")
        self.runtime = Path(os.environ.get("AUREON_RUNTIME_DIR", "/app/aureon-os/runtime"))
        self.receipt = self.runtime / "smoke-receipt.json"
        self.checks: list[Check] = []
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        self.operator_key = os.environ.get("AUREON_OPERATOR_API_KEY", "")
        self.fusion_token = os.environ.get("AUREON_FUSION_API_TOKEN", "")

    def request(
        self,
        method: str,
        path: str,
        *,
        payload: dict | None = None,
        bearer: str = "",
        timeout: float = 30,
    ) -> tuple[int | None, Any, str | None]:
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        headers = {"Accept": "application/json"}
        if data is not None:
            headers["Content-Type"] = "application/json"
        if bearer:
            headers["Authorization"] = f"Bearer {bearer}"
        request = urllib.request.Request(self.base + path, data=data, headers=headers, method=method)
        try:
            with self.opener.open(request, timeout=timeout) as response:
                status = response.status
                raw = response.read(2 * 1024 * 1024 + 1)
        except urllib.error.HTTPError as exc:
            status = exc.code
            raw = exc.read(2 * 1024 * 1024 + 1)
        except Exception as exc:  # Network errors are check data, not secret-bearing output.
            return None, None, type(exc).__name__
        if len(raw) > 2 * 1024 * 1024:
            return status, None, "response_too_large"
        if not raw:
            return status, None, None
        try:
            return status, json.loads(raw.decode("utf-8")), None
        except (UnicodeError, json.JSONDecodeError):
            return status, None, None

    def record(self, name: str, ok: bool, detail: str = "") -> None:
        self.checks.append(Check(name, bool(ok), detail))

    def expect(
        self,
        name: str,
        method: str,
        path: str,
        statuses: set[int],
        *,
        payload: dict | None = None,
        bearer: str = "",
    ) -> Any:
        status, body, error = self.request(method, path, payload=payload, bearer=bearer)
        self.record(name, status in statuses, f"http={status};error={error}")
        return body

    def wait_ready(self) -> bool:
        timeout = float(os.environ.get("AUREON_SMOKE_TIMEOUT_S", "2100"))
        deadline = time.monotonic() + timeout
        last = "not_probed"
        while time.monotonic() < deadline:
            status, body, error = self.request("GET", "/readyz", timeout=5)
            failures = validate_readiness(body, self.revision) if status == 200 and error is None else ["http"]
            if status == 200 and not failures:
                self.record("strict_ready", True, "http=200;all_identity_and_posture_checks=true")
                return True
            last = f"http={status};error={error};failures={','.join(failures)}"
            time.sleep(5)
        self.record("strict_ready", False, last)
        return False

    def check_public_routes(self) -> None:
        self.expect("liveness", "GET", "/healthz", {200})
        for path in PUBLIC_READS:
            self.expect(f"public_read:{path}", "GET", path, {200})
        self.expect("generation_get_denied", "GET", "/api/demo/generate", {403, 405})

    def check_denials(self) -> None:
        # The literal probe value is not a credential. Actual per-boot values are
        # sent only to prove that possession does not unlock the public edge;
        # neither value nor response content is logged.
        for path in SENSITIVE_READS:
            self.expect(f"anonymous_sensitive_read:{path}", "GET", path, {401, 403})
            internal = self.fusion_token if path.startswith("/fusion/") else self.operator_key
            self.expect(f"internal_sensitive_read:{path}", "GET", path, {403}, bearer=internal)
        for path in MUTATIONS:
            for method in ("POST", "PUT", "PATCH", "DELETE"):
                self.expect(f"anonymous_mutation:{method}:{path}", method, path, {401, 403})
                internal = self.fusion_token if path.startswith("/fusion/") else self.operator_key
                self.expect(f"internal_mutation:{method}:{path}", method, path, {403}, bearer=internal)
        for path in ("/healthz", "/readyz", "/api/status", "/fusion/api/status", "/hnc", "/hnc/", "/"):
            self.expect(f"read_route_post_denied:{path}", "POST", path, {403, 405})

    def check_generation(self) -> None:
        payload = {"prompt": "Return one short JSON object with an ok field.", "max_tokens": 4}
        status, body, error = self.request("POST", "/api/demo/generate", payload=payload, timeout=140)
        valid = isinstance(body, dict) and status == 200
        if valid:
            gears = body.get("hnc_gears")
            snapshot = gears.get("pre_inference_organism_snapshot") if isinstance(gears, dict) else None
            usage = body.get("usage")
            valid = (
                body.get("provider_mode") == EXPECTED_PROVIDER
                and body.get("model") == EXPECTED_MODEL
                and body.get("live_trading") is False
                and isinstance(body.get("text"), str)
                and isinstance(gears, dict)
                and isinstance(snapshot, dict)
                and isinstance(snapshot.get("gears"), list)
                and isinstance(usage, dict)
                and isinstance(usage.get("completion_tokens"), int)
                and 1 <= usage["completion_tokens"] <= 4
            )
        self.record("real_own_model_hnc_generation", valid, f"http={status};error={error}")

        # Six simultaneous one-token requests must hit either the edge or app
        # token bucket. Accepted requests remain bounded; no response text is kept.
        def one_request(_: int) -> int | None:
            status, _body, _error = self.request(
                "POST", "/api/demo/generate", payload={**payload, "max_tokens": 1}, timeout=140
            )
            return status

        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            statuses = list(pool.map(one_request, range(6)))
        self.record(
            "generation_rate_limit",
            429 in statuses,
            "statuses=" + ",".join(str(status) for status in sorted(statuses, key=lambda item: item or 0)),
        )

    def check_services(self) -> None:
        try:
            import redis

            redis.Redis.from_url("redis://127.0.0.1:6379/0", socket_timeout=3).ping()
            self.record("redis_ping", True)
        except Exception as exc:
            self.record("redis_ping", False, type(exc).__name__)
        status, _body, error = self._absolute("http://127.0.0.1:8088/healthz")
        self.record("error_sink", status == 200, f"http={status};error={error}")
        try:
            result = subprocess.run(
                ["psql", "-h", "127.0.0.1", "-p", "5433", "-U", "postgres", "-d", "aureon",
                 "-At", "-c", "SELECT to_regclass('public.schumann_resonance_data')"],
                capture_output=True, text=True, timeout=10, check=False,
            )
            self.record(
                "postgres_schema",
                result.returncode == 0 and result.stdout.strip() == "schumann_resonance_data",
                f"returncode={result.returncode}",
            )
        except Exception as exc:
            self.record("postgres_schema", False, type(exc).__name__)
        try:
            result = subprocess.run(
                ["supervisorctl", "-c", "/app/aureon-os/deploy/huggingface/supervisord.conf", "status"],
                capture_output=True, text=True, timeout=10, check=False,
            )
            states = {}
            for line in result.stdout.splitlines():
                parts = line.split()
                if len(parts) >= 2:
                    states[parts[0]] = parts[1]
            missing = [name for name in REQUIRED_PROCESSES if states.get(name) != "RUNNING"]
            self.record("supervisor_processes", result.returncode == 0 and not missing, "not_running=" + ",".join(missing))
        except Exception as exc:
            self.record("supervisor_processes", False, type(exc).__name__)

    def _absolute(self, url: str) -> tuple[int | None, Any, str | None]:
        request = urllib.request.Request(url, headers={"Accept": "application/json"})
        try:
            with self.opener.open(request, timeout=5) as response:
                return response.status, None, None
        except urllib.error.HTTPError as exc:
            return exc.code, None, None
        except Exception as exc:
            return None, None, type(exc).__name__

    def write_receipt(self, ok: bool) -> None:
        self.runtime.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": 1,
            "ok": ok,
            "model": EXPECTED_MODEL,
            "model_revision": self.revision,
            "weight_sha256": EXPECTED_HASH,
            "weight_size_bytes": EXPECTED_SIZE,
            "live_trading": False,
            "orders_placed": 0,
            "checks": [asdict(check) for check in self.checks],
        }
        descriptor, temporary = tempfile.mkstemp(prefix=".smoke-", dir=self.runtime)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2, sort_keys=True, allow_nan=False)
                handle.write("\n")
            os.replace(temporary, self.receipt)
        except Exception:
            try:
                Path(temporary).unlink()
            except OSError:
                pass
            raise

    def run(self) -> int:
        ready = self.wait_ready()
        self.check_public_routes()
        self.check_denials()
        if ready:
            self.check_generation()
        else:
            self.record("real_own_model_hnc_generation", False, "skipped_strict_readiness_failed")
            self.record("generation_rate_limit", False, "skipped_strict_readiness_failed")
        self.check_services()
        ok = all(check.ok for check in self.checks)
        self.write_receipt(ok)
        failed = [check.name for check in self.checks if not check.ok]
        print(json.dumps({"smoke_ok": ok, "checks": len(self.checks), "failed": failed}, sort_keys=True), flush=True)
        return 0 if ok else 1


def main() -> int:
    try:
        return Acceptance().run()
    except Exception as exc:  # A receipt/write/runner failure is itself a failed gate.
        print(json.dumps({"smoke_ok": False, "runner_error": type(exc).__name__}), flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
