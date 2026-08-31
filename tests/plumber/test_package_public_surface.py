from __future__ import annotations

import importlib
import json
import os
import pkgutil
import subprocess
import sys
import textwrap
from pathlib import Path


def test_package_reexports_every_submodule_declared_public_name() -> None:
    package = importlib.import_module("aureon.plumber")
    advertised: set[str] = set()
    for module_info in pkgutil.iter_modules(package.__path__):
        module = importlib.import_module(f"{package.__name__}.{module_info.name}")
        declared = getattr(module, "__all__", ())
        assert isinstance(declared, list)
        assert len(declared) == len(set(declared))
        advertised.update(declared)

    assert package.__all__ == sorted(advertised)
    assert all(hasattr(package, name) for name in advertised)
    assert (
        package.LocalDevelopmentMagicStarReleaseBoundaryV02
        is package.LocalDevelopmentReleaseBoundaryV02
    )


def test_public_package_exposes_no_raw_share_parser_or_exporter() -> None:
    package = importlib.import_module("aureon.plumber")
    custody_module = importlib.import_module("aureon.plumber.star_custody_v02")
    forbidden_entry_points = {
        "_CustodyRecord",
        "_join_five",
        "_split_five",
        "export_raw_share",
        "join_five",
        "parse_raw_share",
        "split_five",
    }

    assert forbidden_entry_points.isdisjoint(package.__all__)
    assert forbidden_entry_points.isdisjoint(custody_module.__all__)
    assert all("share" not in name.lower() for name in package.__all__)


def test_clean_subprocess_import_has_no_external_or_mutating_actions() -> None:
    repository_root = Path(__file__).resolve().parents[2]
    audit_script = textwrap.dedent(
        """
        import json
        import os
        import sys

        forbidden_events = {
            "os.chmod",
            "os.chown",
            "os.link",
            "os.mkdir",
            "os.putenv",
            "os.remove",
            "os.rename",
            "os.rmdir",
            "os.symlink",
            "os.system",
            "os.truncate",
            "os.unsetenv",
            "os.utime",
            "subprocess.Popen",
        }
        write_flags = (
            os.O_WRONLY
            | os.O_RDWR
            | os.O_CREAT
            | os.O_TRUNC
            | os.O_APPEND
        )
        observed = []

        def audit(event, args):
            forbidden = event in forbidden_events or event.startswith("socket.")
            if event == "open":
                mode = args[1] if len(args) > 1 else None
                flags = args[2] if len(args) > 2 else 0
                forbidden = (
                    isinstance(mode, str)
                    and any(marker in mode for marker in "wax+")
                ) or (isinstance(flags, int) and bool(flags & write_flags))
            if forbidden:
                observed.append(event)
                raise RuntimeError(f"forbidden import action: {event}")

        sys.addaudithook(audit)
        import aureon.plumber as plumber

        print(json.dumps({"events": observed, "exports": len(plumber.__all__)}))
        """
    )
    environment = os.environ.copy()
    environment.update(
        {
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONHASHSEED": "0",
            "PYTHONNOUSERSITE": "1",
        }
    )
    completed = subprocess.run(
        [sys.executable, "-B", "-c", audit_script],
        cwd=repository_root,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    report = json.loads(completed.stdout)
    assert report == {"events": [], "exports": 227}
