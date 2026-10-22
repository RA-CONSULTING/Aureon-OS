"""Root-only token rotation broker for isolated Aureon VM workloads.

The broker is the sole Aureon process allowed to reach Compute Engine metadata.
Its attached identity has no data-plane roles.  It may mint short-lived tokens
for four fixed service accounts, then writes each token to one fixed root-owned
runtime path.  It accepts no requests and never prints token material.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import re
import signal
import stat
import tempfile
import time
from typing import Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

from vm_workload_identity import TOKEN_SCHEMA

if os.name == "posix":
    import grp
    import pwd
else:  # pragma: no cover - deployment is Linux; keeps offline Windows import safe.
    grp = None
    pwd = None


PROJECT = "aureon-trading"
BROKER_SERVICE_ACCOUNT = (
    "aureon-vm-token-broker@aureon-trading.iam.gserviceaccount.com"
)
METADATA_ROOT = "http://metadata.google.internal/computeMetadata/v1/"
METADATA_EMAIL = METADATA_ROOT + "instance/service-accounts/default/email"
METADATA_TOKEN = METADATA_ROOT + "instance/service-accounts/default/token"
IAM_ROOT = "https://iamcredentials.googleapis.com/v1/projects/-/serviceAccounts/"
TOKEN_LIFETIME_SECONDS = 1_800
ROTATION_SECONDS = 300
_TOKEN = re.compile(r"[A-Za-z0-9._~-]{20,8192}")


@dataclass(frozen=True)
class Workload:
    name: str
    service_account: str
    user: str
    group: str
    path: str


WORKLOADS = (
    Workload(
        "ui",
        "aureon-vm-ui@aureon-trading.iam.gserviceaccount.com",
        "aureon-ui",
        "aureon-ui",
        "/run/aureon-cloud-identity/ui/token.json",
    ),
    Workload(
        "operator",
        "aureon-vm-operator@aureon-trading.iam.gserviceaccount.com",
        "aureon-operator",
        "aureon-operator",
        "/run/aureon-cloud-identity/operator/token.json",
    ),
    Workload(
        "trade-bridge",
        "aureon-vm-trade-bridge@aureon-trading.iam.gserviceaccount.com",
        "aureon-trade-bridge",
        "aureon-trade-bridge",
        "/run/aureon-cloud-identity/trade-bridge/token.json",
    ),
    Workload(
        "provider",
        "aureon-vm-provider@aureon-trading.iam.gserviceaccount.com",
        "aureon-provider",
        "aureon-provider",
        "/run/aureon-cloud-identity/provider/token.json",
    ),
)


class BrokerError(RuntimeError):
    """A stable, credential-free broker failure."""


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise BrokerError("broker_redirect_denied")


def _http(
    url: str,
    *,
    method: str = "GET",
    headers: Mapping[str, str] | None = None,
    body: bytes | None = None,
    timeout: float = 8.0,
) -> bytes:
    if not (
        url in {METADATA_EMAIL, METADATA_TOKEN}
        or any(url == IAM_ROOT + row.service_account + ":generateAccessToken" for row in WORKLOADS)
    ):
        raise BrokerError("broker_endpoint_denied")
    opener = build_opener(ProxyHandler({}), NoRedirects())
    try:
        with opener.open(
            Request(url, data=body, headers=dict(headers or {}), method=method),
            timeout=timeout,
        ) as response:
            if response.status < 200 or response.status >= 300:
                raise BrokerError("broker_http_failed")
            raw = response.read(16_385)
    except BrokerError:
        raise
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        raise BrokerError("broker_http_failed") from exc
    if len(raw) > 16_384:
        raise BrokerError("broker_response_too_large")
    return raw


def _attached_token(reader: Callable[..., bytes] = _http) -> str:
    metadata_headers = {"Metadata-Flavor": "Google"}
    try:
        email = reader(METADATA_EMAIL, headers=metadata_headers, timeout=5).decode("ascii")
        token_value = json.loads(
            reader(METADATA_TOKEN, headers=metadata_headers, timeout=5)
        )
    except (ValueError, TypeError, UnicodeError) as exc:
        raise BrokerError("broker_metadata_identity_invalid") from exc
    token = token_value.get("access_token") if isinstance(token_value, dict) else None
    expires = token_value.get("expires_in") if isinstance(token_value, dict) else None
    if (
        email.strip() != BROKER_SERVICE_ACCOUNT
        or not isinstance(token, str)
        or _TOKEN.fullmatch(token) is None
        or type(expires) is not int
        or expires < 300
    ):
        raise BrokerError("broker_metadata_identity_invalid")
    return token


def _parse_expiry(value: object, *, now: float) -> float:
    if not isinstance(value, str) or len(value) > 64:
        raise BrokerError("broker_impersonation_response_invalid")
    try:
        expiry = datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC).timestamp()
    except (ValueError, TypeError, OverflowError) as exc:
        raise BrokerError("broker_impersonation_response_invalid") from exc
    if not now + 300 < expiry <= now + TOKEN_LIFETIME_SECONDS + 60:
        raise BrokerError("broker_impersonation_response_invalid")
    return expiry


def mint(
    workload: Workload,
    broker_token: str,
    *,
    reader: Callable[..., bytes] = _http,
    now: float | None = None,
) -> dict[str, object]:
    if workload not in WORKLOADS or _TOKEN.fullmatch(str(broker_token or "")) is None:
        raise BrokerError("broker_workload_invalid")
    current = time.time() if now is None else float(now)
    body = json.dumps(
        {
            "scope": ["https://www.googleapis.com/auth/cloud-platform"],
            "lifetime": f"{TOKEN_LIFETIME_SECONDS}s",
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")
    raw = reader(
        IAM_ROOT + workload.service_account + ":generateAccessToken",
        method="POST",
        headers={
            "Authorization": "Bearer " + broker_token,
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        body=body,
        timeout=8,
    )
    try:
        value = json.loads(raw)
    except (ValueError, TypeError, UnicodeError) as exc:
        raise BrokerError("broker_impersonation_response_invalid") from exc
    token = value.get("accessToken") if isinstance(value, dict) else None
    if not isinstance(token, str) or _TOKEN.fullmatch(token) is None:
        raise BrokerError("broker_impersonation_response_invalid")
    expiry = _parse_expiry(value.get("expireTime"), now=current)
    return {
        "schema": TOKEN_SCHEMA,
        "service_account": workload.service_account,
        "access_token": token,
        "token_type": "Bearer",
        "expires_at_epoch": expiry,
    }


def install_token(workload: Workload, value: Mapping[str, object]) -> None:
    if workload not in WORKLOADS:
        raise BrokerError("broker_workload_invalid")
    if os.name != "posix" or grp is None or pwd is None:
        raise BrokerError("broker_posix_required")
    path = Path(workload.path)
    try:
        pwd.getpwnam(workload.user)
        group = grp.getgrnam(workload.group)
        path.parent.mkdir(mode=0o750, parents=True, exist_ok=True)
        parent = path.parent.stat(follow_symlinks=False)
        if not stat.S_ISDIR(parent.st_mode) or parent.st_uid != 0 or parent.st_mode & 0o022:
            raise BrokerError("broker_runtime_directory_invalid")
        os.chown(path.parent, 0, group.gr_gid)
        os.chmod(path.parent, 0o750)
        payload = (
            json.dumps(dict(value), sort_keys=True, separators=(",", ":")) + "\n"
        ).encode("ascii")
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=path.parent, prefix=".token.", delete=False
        ) as handle:
            temporary = Path(handle.name)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.chown(temporary, 0, group.gr_gid)
        os.chmod(temporary, 0o640)
        os.replace(temporary, path)
    except BrokerError:
        raise
    except (OSError, KeyError, UnicodeError) as exc:
        raise BrokerError("broker_token_install_failed") from exc


def rotate_once(
    *,
    reader: Callable[..., bytes] = _http,
    installer: Callable[[Workload, Mapping[str, object]], None] = install_token,
    now: float | None = None,
) -> None:
    current = time.time() if now is None else float(now)
    source_token = _attached_token(reader)
    # Mint every token before replacing any file, so an IAM failure preserves
    # the previous coherent token set until its normal expiry.
    values = [(row, mint(row, source_token, reader=reader, now=current)) for row in WORKLOADS]
    for workload, value in values:
        installer(workload, value)


def run_forever(*, interval: float = ROTATION_SECONDS) -> None:
    if os.name != "posix" or os.geteuid() != 0:
        raise BrokerError("broker_root_required")
    if interval < 60 or interval > 600:
        raise BrokerError("broker_interval_invalid")
    stopped = False

    def stop(_signum, _frame):
        nonlocal stopped
        stopped = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    while not stopped:
        rotate_once()
        deadline = time.monotonic() + interval
        while not stopped and time.monotonic() < deadline:
            time.sleep(min(1.0, max(0.0, deadline - time.monotonic())))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.once:
            if os.name != "posix" or os.geteuid() != 0:
                raise BrokerError("broker_root_required")
            rotate_once()
        else:
            run_forever()
        return 0
    except BrokerError as exc:
        print(str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
