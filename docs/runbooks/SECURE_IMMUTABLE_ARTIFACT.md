# Secure immutable artifact creation

`aureon/operator/secure_immutable_artifact.py` closes the gap between path
preflight and exclusive file creation.

NTFS alternate-data-stream syntax is rejected before any filesystem action.
On Windows, creation uses a kernel file handle with delete access, no sharing,
`CREATE_NEW`, write-through, and reparse-point control. Before bytes
are written, the handle's kernel-resolved final path, link count, file id,
volume id, and empty size must match the intended new file. The same handle
stays open through an exact same-handle byte read-back, preventing rename,
replacement, or parent-directory substitution during creation. Before return,
the path is reopened without sharing and the file id, volume id, link count,
size, final path and exact bytes are checked again. A final path observation
follows handle close. Failure while the original handle is open requests
handle-bound best-effort disposition; a later replay failure never deletes a
lexical path.

On POSIX, creation is relative to an opened no-follow parent directory. Parent
and created-file device/inode identities are checked before and after
same-descriptor byte read-back. The name is reopened relative to the still-open
parent descriptor after close, and identity, link count, size and bytes are
checked again. Pre-close cleanup unlinks only when the name in that bound
parent still identifies the created inode. Post-close failure is fail-closed
and does not delete the path.

This is not a malicious same-user tamper boundary. An equally privileged
process can create or remove a hard-link alias in an observation window or
modify the artifact after return. The pre/post-close checks narrow and detect
observed races; they cannot provide continuous integrity or exact-object
cleanup semantics across every Windows hard-link alias. That requires an
OS-enforced isolated principal, ACL or filesystem boundary.

The control does not make artifact content authoritative. After bound creation,
callers must still perform their own schema, hash, source, authority, and
current-binding replay. They must never clean up a replay failure by unlinking
the current lexical path, because it may no longer be the created identity.
