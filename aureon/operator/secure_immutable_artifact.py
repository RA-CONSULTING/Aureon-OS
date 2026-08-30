"""Handle-bound exclusive creation for immutable local operator artifacts.

Path preflight followed by a normal ``open(path)`` is vulnerable to concurrent
parent-directory replacement.  This control keeps the created file handle
open, denies sharing on Windows, verifies the kernel-resolved final path and
file identity, reads exact bytes back through that same handle, and performs
identity-bound best-effort cleanup while that handle is still open.

On POSIX it creates relative to an opened no-follow parent directory and
checks parent/file device and inode identities around caller validation.

This is a fail-closed local integrity control, not an isolation boundary.
An equally privileged same-user process can race hard-link creation or mutate
the file after this function returns.  Pre-close and post-close identity,
single-link and byte checks narrow that window but cannot remove it without an
OS-enforced isolated principal, ACL or filesystem boundary.
"""

from __future__ import annotations

import ctypes
import ntpath
import os
import re
import stat
from pathlib import Path
from typing import Any


class SecureImmutableArtifactError(OSError):
    """Handle-bound immutable creation could not be proven safe."""


_WINDOWS_DRIVE = re.compile(r"(?:\\\\\?\\)?[A-Za-z]:\Z")


def validate_no_alternate_stream_path(path: Path, *, label: str = "Artifact path") -> None:
    """Reject NTFS alternate-data-stream syntax at every public path boundary.

    The check is intentionally portable and rejects ``:`` outside one ordinary
    Windows drive designator even when tests run on a non-Windows host.
    """

    raw = os.fspath(path)
    if not raw or "\x00" in raw:
        raise SecureImmutableArtifactError(f"{label} is invalid.")
    drive, tail = ntpath.splitdrive(raw)
    if ":" in tail or (":" in drive and _WINDOWS_DRIVE.fullmatch(drive) is None):
        raise SecureImmutableArtifactError(f"{label} may not address an NTFS alternate data stream.")


def _is_link_or_reparse(path: Path) -> bool:
    try:
        details = path.lstat()
    except OSError as exc:
        raise SecureImmutableArtifactError(f"Artifact path cannot be inspected: {path}") from exc
    if stat.S_ISLNK(details.st_mode):
        return True
    attributes = int(getattr(details, "st_file_attributes", 0))
    reparse = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
    return bool(attributes & reparse)


def _ordinary_directory(path: Path, *, label: str) -> os.stat_result:
    absolute = Path(os.path.abspath(path))
    for component in (absolute, *absolute.parents):
        if (component.exists() or component.is_symlink()) and _is_link_or_reparse(component):
            raise SecureImmutableArtifactError(f"{label} crosses a symbolic link or reparse point.")
    try:
        details = absolute.lstat()
    except OSError as exc:
        raise SecureImmutableArtifactError(f"{label} must exist.") from exc
    if not stat.S_ISDIR(details.st_mode):
        raise SecureImmutableArtifactError(f"{label} must be an ordinary directory.")
    return details


def _same_identity(left: os.stat_result, right: os.stat_result) -> bool:
    return (
        stat.S_IFMT(left.st_mode) == stat.S_IFMT(right.st_mode)
        and int(getattr(left, "st_dev", 0)) == int(getattr(right, "st_dev", 0))
        and int(getattr(left, "st_ino", 0)) == int(getattr(right, "st_ino", 0))
    )


def _normalise_windows_final_path(value: str) -> str:
    if value.startswith("\\\\?\\UNC\\"):
        value = "\\\\" + value[8:]
    elif value.startswith("\\\\?\\"):
        value = value[4:]
    return os.path.normcase(os.path.abspath(value))


class _ByHandleFileInformation(ctypes.Structure):
    _fields_ = [
        ("dwFileAttributes", ctypes.c_ulong),
        ("ftCreationTimeLow", ctypes.c_ulong),
        ("ftCreationTimeHigh", ctypes.c_ulong),
        ("ftLastAccessTimeLow", ctypes.c_ulong),
        ("ftLastAccessTimeHigh", ctypes.c_ulong),
        ("ftLastWriteTimeLow", ctypes.c_ulong),
        ("ftLastWriteTimeHigh", ctypes.c_ulong),
        ("dwVolumeSerialNumber", ctypes.c_ulong),
        ("nFileSizeHigh", ctypes.c_ulong),
        ("nFileSizeLow", ctypes.c_ulong),
        ("nNumberOfLinks", ctypes.c_ulong),
        ("nFileIndexHigh", ctypes.c_ulong),
        ("nFileIndexLow", ctypes.c_ulong),
    ]


class _FileDispositionInfo(ctypes.Structure):
    _fields_ = [("DeleteFile", ctypes.c_ubyte)]


def _windows_kernel() -> Any:
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateFileW.argtypes = [
        ctypes.c_wchar_p,
        ctypes.c_ulong,
        ctypes.c_ulong,
        ctypes.c_void_p,
        ctypes.c_ulong,
        ctypes.c_ulong,
        ctypes.c_void_p,
    ]
    kernel.CreateFileW.restype = ctypes.c_void_p
    kernel.GetFinalPathNameByHandleW.argtypes = [
        ctypes.c_void_p,
        ctypes.c_wchar_p,
        ctypes.c_ulong,
        ctypes.c_ulong,
    ]
    kernel.GetFinalPathNameByHandleW.restype = ctypes.c_ulong
    kernel.GetFileInformationByHandle.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(_ByHandleFileInformation),
    ]
    kernel.GetFileInformationByHandle.restype = ctypes.c_int
    kernel.WriteFile.argtypes = [
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_ulong,
        ctypes.POINTER(ctypes.c_ulong),
        ctypes.c_void_p,
    ]
    kernel.WriteFile.restype = ctypes.c_int
    kernel.ReadFile.argtypes = [
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_ulong,
        ctypes.POINTER(ctypes.c_ulong),
        ctypes.c_void_p,
    ]
    kernel.ReadFile.restype = ctypes.c_int
    kernel.SetFilePointerEx.argtypes = [
        ctypes.c_void_p,
        ctypes.c_longlong,
        ctypes.POINTER(ctypes.c_longlong),
        ctypes.c_ulong,
    ]
    kernel.SetFilePointerEx.restype = ctypes.c_int
    kernel.FlushFileBuffers.argtypes = [ctypes.c_void_p]
    kernel.FlushFileBuffers.restype = ctypes.c_int
    kernel.SetFileInformationByHandle.argtypes = [
        ctypes.c_void_p,
        ctypes.c_int,
        ctypes.c_void_p,
        ctypes.c_ulong,
    ]
    kernel.SetFileInformationByHandle.restype = ctypes.c_int
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    kernel.CloseHandle.restype = ctypes.c_int
    return kernel


def _windows_create_file(path: Path) -> tuple[Any, Any]:
    kernel = _windows_kernel()
    generic_read = 0x80000000
    generic_write = 0x40000000
    delete_access = 0x00010000
    create_new = 1
    file_attribute_normal = 0x00000080
    file_flag_open_reparse_point = 0x00200000
    file_flag_write_through = 0x80000000
    handle = kernel.CreateFileW(
        str(path),
        generic_read | generic_write | delete_access,
        0,
        None,
        create_new,
        file_attribute_normal | file_flag_open_reparse_point | file_flag_write_through,
        None,
    )
    invalid = ctypes.c_void_p(-1).value
    if handle in (None, invalid):
        error = ctypes.get_last_error()
        raise SecureImmutableArtifactError(
            error,
            f"Exclusive artifact creation failed with Windows error {error}.",
            str(path),
        )
    return kernel, handle


def _windows_open_existing(path: Path) -> tuple[Any, Any]:
    kernel = _windows_kernel()
    generic_read = 0x80000000
    open_existing = 3
    file_attribute_normal = 0x00000080
    file_flag_open_reparse_point = 0x00200000
    handle = kernel.CreateFileW(
        str(path),
        generic_read,
        0,
        None,
        open_existing,
        file_attribute_normal | file_flag_open_reparse_point,
        None,
    )
    invalid = ctypes.c_void_p(-1).value
    if handle in (None, invalid):
        error = ctypes.get_last_error()
        raise SecureImmutableArtifactError(
            error,
            f"Post-close artifact validation failed to reopen the path (Windows error {error}).",
            str(path),
        )
    return kernel, handle


def _windows_information(kernel: Any, handle: Any) -> tuple[int, int, int, int]:
    information = _ByHandleFileInformation()
    if not kernel.GetFileInformationByHandle(handle, ctypes.byref(information)):
        error = ctypes.get_last_error()
        raise SecureImmutableArtifactError(
            error,
            f"Created artifact identity could not be read (Windows error {error}).",
        )
    file_index = (int(information.nFileIndexHigh) << 32) | int(information.nFileIndexLow)
    size = (int(information.nFileSizeHigh) << 32) | int(information.nFileSizeLow)
    return (
        int(information.dwVolumeSerialNumber),
        file_index,
        int(information.nNumberOfLinks),
        size,
    )


def _windows_final_path(kernel: Any, handle: Any) -> str:
    needed = int(kernel.GetFinalPathNameByHandleW(handle, None, 0, 0))
    if needed <= 0 or needed > 32768:
        error = ctypes.get_last_error()
        raise SecureImmutableArtifactError(
            error,
            f"Created artifact final path could not be sized (Windows error {error}).",
        )
    buffer = ctypes.create_unicode_buffer(needed + 1)
    written = int(kernel.GetFinalPathNameByHandleW(handle, buffer, len(buffer), 0))
    if written <= 0 or written >= len(buffer):
        error = ctypes.get_last_error()
        raise SecureImmutableArtifactError(
            error,
            f"Created artifact final path could not be read (Windows error {error}).",
        )
    return _normalise_windows_final_path(buffer.value)


def _windows_delete_bound(kernel: Any, handle: Any) -> None:
    disposition = _FileDispositionInfo(1)
    kernel.SetFileInformationByHandle(
        handle,
        4,
        ctypes.byref(disposition),
        ctypes.sizeof(disposition),
    )


def _windows_write_handle(kernel: Any, handle: Any, payload: bytes) -> None:
    offset = 0
    while offset < len(payload):
        block = payload[offset : offset + 1024 * 1024]
        buffer = ctypes.create_string_buffer(block)
        written = ctypes.c_ulong()
        if not kernel.WriteFile(
            handle,
            buffer,
            len(block),
            ctypes.byref(written),
            None,
        ):
            error = ctypes.get_last_error()
            raise SecureImmutableArtifactError(
                error,
                f"Artifact write failed with Windows error {error}.",
            )
        if int(written.value) != len(block):
            raise SecureImmutableArtifactError("Artifact write was unexpectedly short.")
        offset += len(block)
    if not kernel.FlushFileBuffers(handle):
        error = ctypes.get_last_error()
        raise SecureImmutableArtifactError(
            error,
            f"Artifact flush failed with Windows error {error}.",
        )


def _windows_read(kernel: Any, handle: Any, expected_bytes: int) -> bytes:
    new_position = ctypes.c_longlong()
    if not kernel.SetFilePointerEx(handle, 0, ctypes.byref(new_position), 0):
        error = ctypes.get_last_error()
        raise SecureImmutableArtifactError(
            error,
            f"Artifact read-back seek failed with Windows error {error}.",
        )
    result = bytearray()
    remaining = expected_bytes + 1
    while remaining:
        size = min(remaining, 1024 * 1024)
        buffer = ctypes.create_string_buffer(size)
        read = ctypes.c_ulong()
        if not kernel.ReadFile(handle, buffer, size, ctypes.byref(read), None):
            error = ctypes.get_last_error()
            raise SecureImmutableArtifactError(
                error,
                f"Artifact read-back failed with Windows error {error}.",
            )
        count = int(read.value)
        if count == 0:
            break
        result.extend(buffer.raw[:count])
        remaining -= count
    return bytes(result)


def _windows_write_file(output: Path, payload: bytes) -> None:
    expected_path = _normalise_windows_final_path(str(output))
    parent_identity = _ordinary_directory(output.parent, label="Artifact output parent")
    kernel, handle = _windows_create_file(output)
    succeeded = False
    final_identity: tuple[int, int, int, int] | None = None
    preclose_path_identity: os.stat_result | None = None
    try:
        initial_path = _windows_final_path(kernel, handle)
        initial_identity = _windows_information(kernel, handle)
        if initial_path != expected_path or initial_identity[2] != 1 or initial_identity[3] != 0:
            raise SecureImmutableArtifactError("Created artifact escaped, is linked, or was not newly empty.")
        _windows_write_handle(kernel, handle, payload)
        written_identity = _windows_information(kernel, handle)
        if (
            written_identity[:3] != initial_identity[:3]
            or written_identity[2] != 1
            or written_identity[3] != len(payload)
            or _windows_final_path(kernel, handle) != expected_path
        ):
            raise SecureImmutableArtifactError(
                "Created artifact identity or final path changed during write."
            )
        if _windows_read(kernel, handle, len(payload)) != payload:
            raise SecureImmutableArtifactError("Created artifact failed exact same-handle byte read-back.")
        final_identity = _windows_information(kernel, handle)
        if final_identity != written_identity or _windows_final_path(kernel, handle) != expected_path:
            raise SecureImmutableArtifactError(
                "Created artifact identity or final path changed during read-back."
            )
        try:
            current_parent = output.parent.lstat()
            current_output = output.lstat()
        except OSError as exc:
            raise SecureImmutableArtifactError(
                "Created artifact ancestry disappeared before handle close."
            ) from exc
        if (
            not _same_identity(parent_identity, current_parent)
            or not stat.S_ISREG(current_output.st_mode)
            or int(current_output.st_nlink) != 1
            or int(current_output.st_size) != len(payload)
        ):
            raise SecureImmutableArtifactError(
                "Created artifact ancestry or path identity changed before handle close."
            )
        preclose_path_identity = current_output
        succeeded = True
    finally:
        if not succeeded:
            _windows_delete_bound(kernel, handle)
        if not kernel.CloseHandle(handle) and succeeded:
            error = ctypes.get_last_error()
            raise SecureImmutableArtifactError(
                error,
                f"Created artifact handle could not be closed (Windows error {error}).",
            )
    if final_identity is None or preclose_path_identity is None:
        raise SecureImmutableArtifactError("Created artifact identity was not completely captured.")
    post_kernel, post_handle = _windows_open_existing(output)
    post_path_identity: os.stat_result | None = None
    try:
        post_identity = _windows_information(post_kernel, post_handle)
        if (
            post_identity != final_identity
            or post_identity[2] != 1
            or post_identity[3] != len(payload)
            or _windows_final_path(post_kernel, post_handle) != expected_path
            or _windows_read(post_kernel, post_handle, len(payload)) != payload
        ):
            raise SecureImmutableArtifactError(
                "Created artifact failed post-close identity, link-count, path, size, or byte validation."
            )
        try:
            current_parent = output.parent.lstat()
            current_output = output.lstat()
        except OSError as exc:
            raise SecureImmutableArtifactError(
                "Created artifact ancestry disappeared during post-close validation."
            ) from exc
        if (
            not _same_identity(parent_identity, current_parent)
            or not _same_identity(preclose_path_identity, current_output)
            or not stat.S_ISREG(current_output.st_mode)
            or int(current_output.st_nlink) != 1
            or int(current_output.st_size) != len(payload)
        ):
            raise SecureImmutableArtifactError(
                "Created artifact failed post-close ancestry and path-identity validation."
            )
        post_path_identity = current_output
    finally:
        post_kernel.CloseHandle(post_handle)
    try:
        final_parent = output.parent.lstat()
        post_path = output.lstat()
    except OSError as exc:
        raise SecureImmutableArtifactError(
            "Created artifact ancestry disappeared after post-close validation."
        ) from exc
    if (
        post_path_identity is None
        or not _same_identity(parent_identity, final_parent)
        or not _same_identity(post_path_identity, post_path)
        or not stat.S_ISREG(post_path.st_mode)
        or int(post_path.st_nlink) != 1
        or int(post_path.st_size) != len(payload)
    ):
        raise SecureImmutableArtifactError(
            "Created artifact failed final post-handle ancestry, identity, link-count, or size validation."
        )


def _posix_write(output: Path, payload: bytes) -> None:
    directory_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    parent_fd = os.open(output.parent, directory_flags)
    file_fd = -1
    preclose_succeeded = False
    try:
        parent_identity = os.fstat(parent_fd)
        file_flags = (
            os.O_RDWR | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
        )
        file_fd = os.open(output.name, file_flags, 0o600, dir_fd=parent_fd)
        initial_identity = os.fstat(file_fd)
        if not stat.S_ISREG(initial_identity.st_mode) or int(initial_identity.st_nlink) != 1:
            raise SecureImmutableArtifactError("Created artifact is not a single-link regular file.")
        offset = 0
        while offset < len(payload):
            offset += os.write(file_fd, payload[offset:])
        os.fsync(file_fd)
        written_identity = os.fstat(file_fd)
        if written_identity.st_size != len(payload) or not _same_identity(
            initial_identity,
            written_identity,
        ):
            raise SecureImmutableArtifactError("Created artifact identity changed during write.")
        current_parent = output.parent.lstat()
        current_output = output.lstat()
        if not _same_identity(parent_identity, current_parent) or not _same_identity(
            written_identity,
            current_output,
        ):
            raise SecureImmutableArtifactError("Created artifact ancestry changed before validation.")
        os.lseek(file_fd, 0, os.SEEK_SET)
        read_back = bytearray()
        while len(read_back) <= len(payload):
            block = os.read(file_fd, min(1024 * 1024, len(payload) + 1 - len(read_back)))
            if not block:
                break
            read_back.extend(block)
        if bytes(read_back) != payload:
            raise SecureImmutableArtifactError("Created artifact failed exact same-handle byte read-back.")
        if not _same_identity(parent_identity, output.parent.lstat()) or not _same_identity(
            written_identity,
            output.lstat(),
        ):
            raise SecureImmutableArtifactError("Created artifact ancestry changed during read-back.")
        preclose_succeeded = True
    finally:
        if not preclose_succeeded and file_fd >= 0:
            try:
                current = os.stat(output.name, dir_fd=parent_fd, follow_symlinks=False)
                if _same_identity(os.fstat(file_fd), current):
                    os.unlink(output.name, dir_fd=parent_fd)
            except OSError:
                pass
        if file_fd >= 0:
            os.close(file_fd)
    try:
        post_flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
        post_fd = os.open(output.name, post_flags, dir_fd=parent_fd)
        try:
            post_identity = os.fstat(post_fd)
            current = os.stat(output.name, dir_fd=parent_fd, follow_symlinks=False)
            if (
                not _same_identity(written_identity, post_identity)
                or not _same_identity(post_identity, current)
                or int(post_identity.st_nlink) != 1
                or int(post_identity.st_size) != len(payload)
            ):
                raise SecureImmutableArtifactError(
                    "Created artifact failed post-close identity, link-count, or size validation."
                )
            post_read = bytearray()
            while len(post_read) <= len(payload):
                block = os.read(
                    post_fd,
                    min(1024 * 1024, len(payload) + 1 - len(post_read)),
                )
                if not block:
                    break
                post_read.extend(block)
            if bytes(post_read) != payload:
                raise SecureImmutableArtifactError("Created artifact failed exact post-close byte read-back.")
        finally:
            os.close(post_fd)
        final_parent = output.parent.lstat()
        final_output = output.lstat()
        if (
            not _same_identity(parent_identity, final_parent)
            or not _same_identity(written_identity, final_output)
            or int(final_output.st_nlink) != 1
            or int(final_output.st_size) != len(payload)
        ):
            raise SecureImmutableArtifactError(
                "Created artifact failed final post-handle ancestry, identity, link-count, or size validation."
            )
    finally:
        os.close(parent_fd)


def write_new_file(
    output_path: Path,
    payload: bytes,
) -> None:
    """Exclusively write and read back one file through a bound kernel handle."""

    validate_no_alternate_stream_path(output_path, label="Artifact output path")
    output = Path(os.path.abspath(output_path))
    if not output.name or output.name in {".", ".."} or output.parent == output:
        raise SecureImmutableArtifactError("Artifact output path is invalid.")
    if not isinstance(payload, bytes):
        raise SecureImmutableArtifactError("Artifact payload must be exact bytes.")
    _ordinary_directory(output.parent, label="Artifact output parent")
    if output.exists() or output.is_symlink():
        raise SecureImmutableArtifactError("Immutable artifact output already exists.")
    if os.name == "nt":
        _windows_write_file(output, payload)
    else:
        _posix_write(output, payload)


__all__ = [
    "SecureImmutableArtifactError",
    "validate_no_alternate_stream_path",
    "write_new_file",
]
