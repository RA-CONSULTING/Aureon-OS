from __future__ import annotations

import os
from pathlib import Path

import pytest

from aureon.operator import secure_immutable_artifact as secure


def test_writes_exact_bytes_with_same_handle_readback(tmp_path: Path) -> None:
    output = tmp_path / "receipt.json"

    secure.write_new_file(
        output,
        b'{"safe":true}\n',
    )

    assert output.read_bytes() == b'{"safe":true}\n'


def test_existing_output_is_never_overwritten(tmp_path: Path) -> None:
    output = tmp_path / "receipt.json"
    output.write_text("owner\n", encoding="utf-8")

    with pytest.raises(secure.SecureImmutableArtifactError, match="already exists"):
        secure.write_new_file(output, b"replacement\n")

    assert output.read_text(encoding="utf-8") == "owner\n"


def test_precreation_failure_leaves_no_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "receipt.json"
    real_write = secure._windows_write_file if os.name == "nt" else secure._posix_write  # noqa: SLF001

    def reject(path: Path, payload: bytes) -> None:
        del path, payload
        raise secure.SecureImmutableArtifactError("rejected")

    monkeypatch.setattr(
        secure,
        "_windows_write_file" if os.name == "nt" else "_posix_write",
        reject,
    )
    with pytest.raises(secure.SecureImmutableArtifactError, match="rejected"):
        secure.write_new_file(output, b"new\n")
    monkeypatch.setattr(
        secure,
        "_windows_write_file" if os.name == "nt" else "_posix_write",
        real_write,
    )

    assert not output.exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows sharing semantics")
def test_open_file_cannot_be_replaced_during_write(tmp_path: Path) -> None:
    output = tmp_path / "receipt.json"
    substitute = tmp_path / "substitute.json"
    substitute.write_text("unrelated\n", encoding="utf-8")
    real_write = secure._windows_write_file  # noqa: SLF001

    def attempt_replace(path: Path, payload: bytes) -> None:
        kernel, handle = secure._windows_create_file(path)  # noqa: SLF001
        with pytest.raises(PermissionError):
            os.replace(substitute, output)
        secure._windows_delete_bound(kernel, handle)  # noqa: SLF001
        kernel.CloseHandle(handle)
        real_write(path, payload)

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(secure, "_windows_write_file", attempt_replace)
    try:
        secure.write_new_file(output, b"bound\n")
    finally:
        monkeypatch.undo()
    assert output.read_bytes() == b"bound\n"
    assert substitute.read_text(encoding="utf-8") == "unrelated\n"


@pytest.mark.skipif(os.name != "nt", reason="Windows final-path attack replay")
def test_parent_swap_before_kernel_create_is_detected_and_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parent = tmp_path / "approved"
    parent.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    parked = tmp_path / "parked"
    output = parent / "receipt.json"
    real_create = secure._windows_create_file  # noqa: SLF001

    def swapped_create(path: Path):
        parent.rename(parked)
        try:
            parent.symlink_to(outside, target_is_directory=True)
        except OSError:
            parked.rename(parent)
            pytest.skip("Directory symlink creation is unavailable on this host.")
        return real_create(path)

    monkeypatch.setattr(secure, "_windows_create_file", swapped_create)

    with pytest.raises(
        secure.SecureImmutableArtifactError,
        match="escaped|final path",
    ):
        secure.write_new_file(output, b"escaped\n")

    assert not (outside / "receipt.json").exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows parent identity replay")
def test_ordinary_parent_replacement_before_kernel_create_is_detected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parent = tmp_path / "approved"
    parent.mkdir()
    parked = tmp_path / "parked"
    output = parent / "receipt.json"
    real_create = secure._windows_create_file  # noqa: SLF001

    def swapped_create(path: Path):
        parent.rename(parked)
        parent.mkdir()
        return real_create(path)

    monkeypatch.setattr(secure, "_windows_create_file", swapped_create)

    with pytest.raises(
        secure.SecureImmutableArtifactError,
        match="ancestry",
    ):
        secure.write_new_file(output, b"bound\n")

    assert not output.exists()
    assert parked.is_dir()


@pytest.mark.skipif(os.name != "nt", reason="NTFS alternate data streams are Windows-specific")
def test_ntfs_alternate_data_stream_output_is_rejected(tmp_path: Path) -> None:
    base = tmp_path / "receipt.json"
    base.write_text("owner\n", encoding="utf-8")
    stream = Path(f"{base}:worker")

    with pytest.raises(
        secure.SecureImmutableArtifactError,
        match="alternate data stream",
    ):
        secure.write_new_file(stream, b"hidden\n")

    assert base.read_text(encoding="utf-8") == "owner\n"


@pytest.mark.skipif(os.name != "nt", reason="Windows hard-link race replay")
def test_post_close_hard_link_race_fails_closed_without_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "receipt.json"
    alias = tmp_path / "alias.json"
    real_open_existing = secure._windows_open_existing  # noqa: SLF001

    def add_alias_then_open(path: Path):
        os.link(path, alias)
        return real_open_existing(path)

    monkeypatch.setattr(secure, "_windows_open_existing", add_alias_then_open)

    with pytest.raises(
        secure.SecureImmutableArtifactError,
        match="post-close identity|single-link",
    ):
        secure.write_new_file(output, b"bound\n")

    assert output.read_bytes() == b"bound\n"
    assert alias.read_bytes() == b"bound\n"


@pytest.mark.skipif(os.name != "nt", reason="Windows post-handle replacement replay")
def test_same_size_replacement_after_post_handle_close_is_detected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "receipt.json"
    substitute = tmp_path / "substitute.json"
    substitute.write_bytes(b"other\n")
    real_open_existing = secure._windows_open_existing  # noqa: SLF001

    class _ReplacingKernel:
        def __init__(self, kernel: object) -> None:
            self._kernel = kernel

        def __getattr__(self, name: str) -> object:
            return getattr(self._kernel, name)

        def CloseHandle(self, handle: object) -> int:  # noqa: N802 - Windows API spelling
            result = int(self._kernel.CloseHandle(handle))
            os.replace(substitute, output)
            return result

    def replace_after_open(path: Path):
        kernel, handle = real_open_existing(path)
        return _ReplacingKernel(kernel), handle

    monkeypatch.setattr(secure, "_windows_open_existing", replace_after_open)

    with pytest.raises(
        secure.SecureImmutableArtifactError,
        match="final post-handle ancestry, identity",
    ):
        secure.write_new_file(output, b"bound\n")

    assert output.read_bytes() == b"other\n"
