"""Read gate for coverage-plan stages 3 and 4.

OPEN_PLAN_THROUGH stays 2. Two inventory rows are the ones body_call will run.
Miner is the empty insight dict. Queen is compute_zpe_ground, loaded without
executing queen/__init__.py. Exchange rows stay operator and are not imported.
Key material is not read. Live orders stay refused.

A key group in a result is a label, redacted:<venue> or absent:<venue>.
"""

from __future__ import annotations

import base64
import importlib.util
import os
import sys
from pathlib import Path
from types import ModuleType

# module, symbol, safety sentence written into the inventory for the public row.
READ_SAFETY: dict[tuple[str, str], str] = {
    ("miner/miner_inhouse_ai_bridge.py", "MinerAIInsight.to_dict"): (
        "operator-scoped read of an empty insight; the bridge is not constructed"
    ),
    ("queen/temporal_ground.py", "compute_zpe_ground"): (
        "runs from inputs or committed files; no keys and no repo write"
    ),
}

# Miner changes server to public. Queen's row is already public.
# Exchange rows stay operator. The landed exchanges surface does not import them.
READ_SERVER_PUBLIC = {
    ("miner/miner_inhouse_ai_bridge.py", "MinerAIInsight.to_dict"),
}

READ_KEYS = frozenset(READ_SAFETY)

READ_DOTTED = {
    "miner/miner_inhouse_ai_bridge.py": "aureon.miner.miner_inhouse_ai_bridge",
    "queen/temporal_ground.py": "aureon.queen.temporal_ground",
}

# Package inits that must not run. queen/__init__.py imports QueenLayer and the
# in-house adapter. The ground function's own file does not.
SKIP_PACKAGE_INIT = {
    "aureon.queen.temporal_ground": frozenset({"aureon.queen"}),
}

# Modules a read-gated call may leave in sys.modules. Anything else under
# queen, miner, or the in-house adapter is still a banned chain.
READ_MODULES: dict[tuple[str, str], frozenset[str]] = {
    ("miner/miner_inhouse_ai_bridge.py", "MinerAIInsight.to_dict"): frozenset(
        {
            "aureon.miner",
            "aureon.miner.miner_inhouse_ai_bridge",
        }
    ),
    ("queen/temporal_ground.py", "compute_zpe_ground"): frozenset(
        {
            "aureon.queen",
            "aureon.queen.temporal_ground",
        }
    ),
}

# Real arguments for the call sweep. No-argument calls are also recorded.
READ_ARGUMENTS: dict[tuple[str, str], dict[str, object]] = {
    ("miner/miner_inhouse_ai_bridge.py", "MinerAIInsight.to_dict"): {},
    ("queen/temporal_ground.py", "compute_zpe_ground"): {"lambda_t": 1.0},
}

# Env names only. Values are never copied into a result.
_KEY_GROUPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("kraken", ("KRAKEN_API_KEY", "KRAKEN_API_SECRET")),
    (
        "capital",
        ("CAPITAL_API_KEY",),
    ),
    ("alpaca", ("ALPACA_API_KEY", "ALPACA_SECRET_KEY")),
    ("binance", ("BINANCE_API_KEY", "BINANCE_API_SECRET")),
)


def is_read_key(module: str, symbol: str) -> bool:
    return (module, symbol) in READ_KEYS


def is_read_dotted(dotted: str) -> bool:
    return dotted in set(READ_DOTTED.values())


def key_group_labels() -> list[dict[str, object]]:
    """Presence labels. The env values are not copied and are not returned."""

    labels: list[dict[str, object]] = []
    for venue, names in _KEY_GROUPS:
        present = _group_present(venue, names)
        labels.append(
            {
                "key_group": f"redacted:{venue}" if present else f"absent:{venue}",
                "present": present,
            }
        )
    return labels


def _group_present(venue: str, names: tuple[str, ...]) -> bool:
    if venue == "capital":
        identifier = str(os.environ.get("CAPITAL_IDENTIFIER") or os.environ.get("CAPITAL_EMAIL") or "").strip()
        password = str(os.environ.get("CAPITAL_PASSWORD") or os.environ.get("CAPITAL_API_PASSWORD") or "").strip()
        return bool(str(os.environ.get("CAPITAL_API_KEY") or "").strip() and identifier and password)
    if venue == "alpaca":
        key = str(os.environ.get("ALPACA_API_KEY") or os.environ.get("APCA_API_KEY_ID") or "").strip()
        secret = str(os.environ.get("ALPACA_SECRET_KEY") or os.environ.get("APCA_API_SECRET_KEY") or "").strip()
        return bool(key and secret)
    return all(str(os.environ.get(name) or "").strip() for name in names)


def _secret_forms(value: str) -> tuple[str, ...]:
    """Plain value plus its base64 spellings. Padding-stripped forms count."""

    raw = value.encode("utf-8")
    forms: list[str] = [value]
    for encoder in (base64.b64encode, base64.urlsafe_b64encode, base64.standard_b64encode):
        token = encoder(raw).decode("ascii")
        forms.append(token)
        stripped = token.rstrip("=")
        if stripped != token:
            forms.append(stripped)
    return tuple(dict.fromkeys(forms))


def contains_env_secret(text: str) -> str | None:
    """Return the env name when its value appears in text. None when it does not.

    Short values are ignored so an empty string or a single letter cannot
    match unrelated prose. The value itself is not returned. A base64
    spelling of the value counts as the same secret.
    """

    for _venue, names in _KEY_GROUPS:
        extra = {
            "CAPITAL_IDENTIFIER",
            "CAPITAL_EMAIL",
            "CAPITAL_PASSWORD",
            "CAPITAL_API_PASSWORD",
            "APCA_API_KEY_ID",
            "APCA_API_SECRET_KEY",
        }
        for name in (*names, *extra):
            value = str(os.environ.get(name) or "")
            if len(value) < 8:
                continue
            if any(form in text for form in _secret_forms(value)):
                return name
    return None


# Raw transports and the exchange client. is_http_client does not name these;
# the read gate still has to refuse them.
_BANNED_NETWORK_ROOTS = frozenset({"socket", "ssl", "smtplib", "ccxt"})


def banned_import(name: str, module: str, symbol: str, *, http_client) -> bool:
    """True when this loaded module is outside the read gate for this call."""

    allowed = READ_MODULES.get((module, symbol), frozenset())
    if name in allowed:
        return False
    if name == "aureon.inhouse_ai" or name.startswith("aureon.inhouse_ai."):
        return True
    if "ollama_config" in name:
        return True
    if name in {"aureon.queen", "aureon.miner", "aureon.swarm_motion"} or name.startswith(
        ("aureon.queen.", "aureon.miner.", "aureon.swarm_motion.")
    ):
        return True
    root = name.split(".", 1)[0]
    if root in _BANNED_NETWORK_ROOTS:
        return True
    return bool(http_client(name))


def load_read_gated(dotted: str) -> ModuleType:
    """Blob-check and exec one read-gated module. Skips the named package inits."""

    from aureon_public.guard_loader import PINNED_COMMIT
    from aureon_public.paths import repo_root
    from aureon_public.pin_blob import (
        _SameBytesLoader,
        expected_pin_blob,
        load_pinned_source,
        refuse_preseeded_aureon,
    )

    if dotted not in SKIP_PACKAGE_INIT and dotted not in set(READ_DOTTED.values()):
        raise ImportError(f"{dotted} is not a read-gated module")
    root = repo_root()
    parts = dotted.split(".")
    skip = SKIP_PACKAGE_INIT.get(dotted, frozenset())
    for index in range(1, len(parts)):
        name = ".".join(parts[:index])
        if name in sys.modules:
            continue
        directory = root.joinpath(*parts[:index])
        init = directory / "__init__.py"
        if name in skip:
            _stub_package(name, directory, init, _SameBytesLoader)
            continue
        expected, error = expected_pin_blob(init, root, PINNED_COMMIT)
        if error or not expected:
            raise ImportError(error or "expected blob is required")
        relative = init.resolve().relative_to(root.resolve()).as_posix()
        refusal = load_pinned_source(
            name,
            init,
            expected,
            f"checkout {relative} differs from pin {PINNED_COMMIT[:12]}",
        )
        if refusal:
            raise ImportError(refusal)
    path = root.joinpath(*parts).with_suffix(".py")
    expected, error = expected_pin_blob(path, root, PINNED_COMMIT)
    if error or not expected:
        raise ImportError(error or "expected blob is required")
    relative = path.resolve().relative_to(root.resolve()).as_posix()
    refusal = load_pinned_source(
        dotted,
        path,
        expected,
        f"checkout {relative} differs from pin {PINNED_COMMIT[:12]}",
    )
    if refusal:
        raise ImportError(refusal)
    refuse_preseeded_aureon()
    loaded = sys.modules.get(dotted)
    if loaded is None:
        raise ImportError(f"{dotted} could not be loaded")
    return loaded


def _stub_package(name: str, directory: Path, init: Path, loader_type: type) -> None:
    """A package object that does not execute __init__.py."""

    module = ModuleType(name)
    module.__path__ = [str(directory)]
    module.__package__ = name
    module.__file__ = str(init)
    loader = loader_type(b"", str(init))
    spec = importlib.util.spec_from_loader(name, loader, origin=str(init), is_package=True)
    if spec is None:
        raise ImportError(f"{name} stub could not be built")
    spec.submodule_search_locations = [str(directory)]
    module.__spec__ = spec
    sys.modules[name] = module
