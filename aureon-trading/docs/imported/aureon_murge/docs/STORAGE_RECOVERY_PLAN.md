# Storage Recovery Plan

## Current State
- Root filesystem: `/dev/mmcblk0p2`
- Free space initially observed: about `228M-391M`
- Free space after offload: about `3.9G`
- This is acceptable for short build/test cycles, but still below a comfortable long-running development target.
- Target working reserve: at least `8G-12G` free on `/`.

## Completed Offload
- Mounted `LSC_DATA` at `/media/l/LSC_DATA`.
- Mounted `LSC_BUF` at `/media/l/LSC_BUF`.
- Copied these directories with `rsync -aH`:
  - `/home/l/Desktop/prace dark neutrino `
  - `/home/l/Desktop/gary repo nexus`
- Verified source and destination sizes before deleting originals.
- Replaced original Desktop paths with symlinks pointing to:
  - `/media/l/LSC_DATA/flameborn-offload-2026-05-14/Desktop/prace dark neutrino `
  - `/media/l/LSC_DATA/flameborn-offload-2026-05-14/Desktop/gary repo nexus`

## Largest Known Targets
- `/home/l/Desktop/prace dark neutrino `: `2.8G`
- `/home/l/.cache/google-chrome`: `1.6G`
- `/home/l/Desktop/gary repo nexus`: `880M`
- `/home/l/CodexPROsSparrow/desktop/node_modules`: `480M`
- `/home/l/CodexPROsSparrow/node_modules`: `304M`
- `/home/l/CodexPROsSparrow/desktop/dist`: `279M`

## Important Constraint
`/mnt/lsc_data` and `/mnt/lsc_buf` currently behave like ordinary directories on the root filesystem, not active mounts.

They contain about:
- `/mnt/lsc_data`: `992M`
- `/mnt/lsc_buf`: `4K`

Do not mount a disk over these paths blindly, because that would hide the current on-root contents until unmounted.

## Safer Mount Strategy
If the secondary disk should be used, prefer dedicated mountpoints such as:
- `/media/l/LSC_DATA`
- `/media/l/LSC_BUF`

Suggested commands:
```bash
sudo mkdir -p /media/l/LSC_DATA /media/l/LSC_BUF
sudo mount -L LSC_DATA /media/l/LSC_DATA
sudo mount -L LSC_BUF /media/l/LSC_BUF
```

Then verify:
```bash
df -h /media/l/LSC_DATA /media/l/LSC_BUF
```

## Immediate Low-Risk Space Recovery Options
1. Clear browser cache manually if more working space is needed:
```bash
rm -rf ~/.cache/google-chrome/*
```
This should free about `1.6G`, but it is destructive and should be user-approved.

2. Remove build artifact if it is no longer needed locally:
```bash
rm -rf /home/l/CodexPROsSparrow/desktop/dist
```
This frees about `279M` and can be rebuilt.

3. Completed: offload large research directories to the secondary disk after mounting it:
- `/home/l/Desktop/prace dark neutrino `
- `/home/l/Desktop/gary repo nexus`

## Recommended Order
1. Mount secondary disk to new mountpoints under `/media/l`.
2. Move large archival/research directories there.
3. Re-check free space.
4. Only if still needed, clear caches or rebuildable artifacts.

## Rollback Notes
- Mounting to `/media/l/LSC_DATA` and `/media/l/LSC_BUF` is reversible with `umount`.
- Moving directories should be done with `rsync -a` followed by validation before deleting originals.
- Do not delete project directories until the copied data is verified.
