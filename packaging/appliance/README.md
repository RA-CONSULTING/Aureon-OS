# Aureon appliance protection status

The appliance build and first-boot runtime are on terminal **HOLD**. The image
profile enables only boot attestation and the first-boot console HOLD service.
It declares no service or target that may be enabled after first boot.

`aureon-firstboot` accepts status/console-gate syntax only to emit a deterministic
no-write receipt with `process_start_authorized: false` and `target_enabled:
false`. It does not request an owner phrase, create a marker or receipt file,
enable systemd units, start a target, bind port 8790, or claim provisioning.

The operator, organism, and HNC unit definitions also point only at the fixed
isolated bootstrap and use `Restart=no`; they are not enabled by the profile.
An inert image build is not a running or protected Aureon OS.

Safe source checks:

```bash
bash -n packaging/appliance/mkosi.postinst.chroot
bash -n packaging/appliance/rootfs/usr/sbin/aureon-firstboot
python -I -S -B scripts/bootstrap/protected_bootstrap_v05.py --target-id linux-supervisor
```
