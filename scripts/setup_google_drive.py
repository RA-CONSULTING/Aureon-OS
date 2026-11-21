"""Authorize Aureon's read-only Google Drive connector on this Windows user.

Requires an OAuth *Desktop app* client JSON downloaded from Google Cloud Console.
The sign-in happens in the operator's browser. No Google password is collected.
The refresh token is DPAPI-encrypted under the current Windows user profile.
"""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import sys
from ctypes import wintypes
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aureon.connectors.base import oauth_token_path
from aureon.connectors.google_drive import SCOPES, DriveConnector


class _Blob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]


def _protect(raw: bytes) -> bytes:
    if os.name != "nt":
        raise RuntimeError("this credential store requires Windows DPAPI")
    source_buffer = ctypes.create_string_buffer(raw)
    source = _Blob(len(raw), ctypes.cast(source_buffer, ctypes.POINTER(ctypes.c_byte)))
    target = _Blob()
    if not ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(source), "Aureon read-only Drive", None, None, None, 0, ctypes.byref(target)
    ):
        raise OSError("Windows could not protect the Drive token")
    try:
        return ctypes.string_at(target.pbData, target.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(target.pbData)


def _validate_client_file(path: Path) -> Path:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        installed = payload.get("installed")
        assert isinstance(installed, dict)
        assert isinstance(installed.get("client_id"), str) and installed["client_id"]
        assert isinstance(installed.get("client_secret"), str) and installed["client_secret"]
        assert isinstance(installed.get("redirect_uris"), list)
    except (OSError, ValueError, TypeError, AssertionError):
        raise SystemExit(
            "Expected a valid OAuth Desktop app client JSON from Google Cloud Console."
        ) from None
    return path.resolve()


def authorize(client_file: Path, token_path: Path) -> dict[str, object]:
    from google_auth_oauthlib.flow import InstalledAppFlow

    client_file = _validate_client_file(client_file)
    flow = InstalledAppFlow.from_client_secrets_file(str(client_file), list(SCOPES))
    credentials = flow.run_local_server(
        host="127.0.0.1",
        port=0,
        open_browser=True,
        authorization_prompt_message="Open this URL in your browser to authorize read-only Drive: {url}",
        success_message="Aureon Drive authorization is complete. You may close this window.",
    )
    payload = {
        "version": 1,
        "client_file": str(client_file),
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "scopes": list(SCOPES),
    }
    token_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = token_path.with_suffix(".tmp")
    temporary.write_bytes(_protect(json.dumps(payload).encode("utf-8")))
    temporary.replace(token_path)
    connector = DriveConnector(env={"AUREON_GOOGLE_OAUTH_TOKEN": str(token_path)})
    status = connector.status()
    return {"available": status.available, "source": status.source, "blocker": status.blocker}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("client_file", type=Path, nargs="?", help="local OAuth Desktop app client JSON")
    parser.add_argument("--token", type=Path, default=oauth_token_path())
    parser.add_argument("--status", action="store_true", help="check existing read-only access")
    args = parser.parse_args()
    if args.status:
        status = DriveConnector(env={"AUREON_GOOGLE_OAUTH_TOKEN": str(args.token)}).status()
        print(json.dumps({"available": status.available, "source": status.source, "blocker": status.blocker}))
        return 0 if status.available else 1
    print(json.dumps(authorize(args.client_file, args.token), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
