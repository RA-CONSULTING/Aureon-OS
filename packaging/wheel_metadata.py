"""Metadata checks for the Aureon wheel. No upload and no network."""

from __future__ import annotations

import zipfile
from collections.abc import Mapping, Sequence

DISTRIBUTION_NAME = "aureon"
DISTRIBUTION_VERSION = "2.1.0"
REPOSITORY_URL = "https://github.com/RA-CONSULTING/Aureon-OS"
CONSOLE_MODULE = "protected_console_bootstrap_v05.py"
EXPECTED_SCRIPTS = {
    "aureon-operator": "protected_console_bootstrap_v05:operator_main",
    "aureon-organism": "protected_console_bootstrap_v05:organism_main",
    "aureon-hnc": "protected_console_bootstrap_v05:hnc_main",
    "aureon-local-gui": "protected_console_bootstrap_v05:local_gui_main",
    "aureon-website": "protected_console_bootstrap_v05:website_main",
}


def parse_metadata(text: str) -> dict[str, list[str]]:
    """Parse the RFC 822 headers of a wheel METADATA file."""
    headers: dict[str, list[str]] = {}
    current: str | None = None
    for line in text.splitlines():
        if line == "":
            break
        if line.startswith((" ", "\t")) and current is not None:
            headers[current][-1] = f"{headers[current][-1]} {line.strip()}"
            continue
        key, separator, value = line.partition(":")
        if not separator:
            continue
        current = key.strip()
        headers.setdefault(current, []).append(value.strip())
    return headers


def parse_console_scripts(text: str) -> dict[str, str]:
    scripts: dict[str, str] = {}
    in_section = False
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("[") and line.endswith("]"):
            in_section = line == "[console_scripts]"
            continue
        if not in_section or not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        scripts[name.strip()] = "".join(value.split())
    return scripts


def metadata_errors(headers: Mapping[str, Sequence[str]]) -> list[str]:
    errors: list[str] = []
    if list(headers.get("Name", [])) != [DISTRIBUTION_NAME]:
        errors.append("Name is not aureon")
    if list(headers.get("Version", [])) != [DISTRIBUTION_VERSION]:
        errors.append("Version is not 2.1.0")
    if list(headers.get("Requires-Python", [])) != [">=3.11"]:
        errors.append("Requires-Python is not >=3.11")
    if list(headers.get("License-Expression", [])) != ["MIT"]:
        errors.append("License-Expression is not MIT")
    summary = " ".join(headers.get("Summary", []))
    if "go-live HOLD" not in summary:
        errors.append("Summary does not keep go-live HOLD")
    for classifier in headers.get("Classifier", []):
        if "Production/Stable" in classifier:
            errors.append(f"classifier overclaims readiness: {classifier}")
    repository = [
        value
        for value in headers.get("Project-URL", [])
        if value.lower().startswith("repository,")
        and REPOSITORY_URL in value
    ]
    if not repository:
        errors.append("Repository URL is missing")
    return errors


def entry_point_errors(scripts: Mapping[str, str]) -> list[str]:
    if dict(scripts) != EXPECTED_SCRIPTS:
        return [f"console scripts are {scripts!r}"]
    return []


def wheel_member_errors(names: Sequence[str]) -> list[str]:
    errors: list[str] = []
    dist_info = f"{DISTRIBUTION_NAME}-{DISTRIBUTION_VERSION}.dist-info"
    saw_package = False
    saw_module = False
    saw_metadata = False
    for name in names:
        if name.startswith("/") or ".." in name.split("/"):
            errors.append(f"unsafe wheel member {name}")
            continue
        lowered = name.lower()
        if (
            lowered.endswith(".env")
            or "/.env" in lowered
            or lowered.endswith(".pypirc")
            or lowered.endswith("id_rsa")
            or "aureon_fusion" in lowered
        ):
            errors.append(f"forbidden wheel member {name}")
        top = name.split("/", 1)[0]
        if top == "aureon" or name.startswith("aureon/"):
            saw_package = True
        elif top == CONSOLE_MODULE:
            saw_module = True
        elif top == dist_info:
            if name.endswith("/METADATA"):
                saw_metadata = True
        elif name not in {"", dist_info}:
            errors.append(f"unexpected top-level wheel member {name}")
    if not saw_package:
        errors.append("wheel is missing the aureon package")
    if not saw_module:
        errors.append("wheel is missing the inert console module")
    if not saw_metadata:
        errors.append("wheel is missing METADATA")
    return errors


def inspect_wheel(archive: zipfile.ZipFile) -> list[str]:
    names = archive.namelist()
    errors = wheel_member_errors(names)
    metadata_name = next(
        (name for name in names if name.endswith(".dist-info/METADATA")),
        None,
    )
    entry_name = next(
        (name for name in names if name.endswith(".dist-info/entry_points.txt")),
        None,
    )
    if metadata_name is None:
        errors.append("METADATA path is missing")
    else:
        headers = parse_metadata(archive.read(metadata_name).decode("utf-8"))
        errors.extend(metadata_errors(headers))
    if entry_name is None:
        errors.append("entry_points.txt is missing")
    else:
        scripts = parse_console_scripts(archive.read(entry_name).decode("utf-8"))
        errors.extend(entry_point_errors(scripts))
    return errors
