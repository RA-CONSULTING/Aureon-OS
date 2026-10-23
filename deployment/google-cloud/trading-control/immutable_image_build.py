"""Read committed image-build source without checkout line conversion.

The bytes come from ``git cat-file`` at the named revision. A Windows
checkout with ``core.autocrlf`` does not change the hash.
"""

from __future__ import annotations

import subprocess
from pathlib import Path


class ImageBuildError(RuntimeError):
    pass


def _git_blob(source: Path, revision: str, relative: str) -> bytes:
    """Read exact committed bytes so image inputs ignore checkout EOL policy."""

    try:
        result = subprocess.run(
            ["git", "-C", str(source), "cat-file", "blob", f"{revision}:{relative}"],
            capture_output=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ImageBuildError("committed_source_bytes_unavailable") from error
    if result.returncode != 0 or len(result.stdout) > 32 * 1024 * 1024:
        raise ImageBuildError("committed_source_bytes_unavailable")
    return result.stdout
