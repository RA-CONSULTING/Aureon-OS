# Aureon on Linux — protection HOLD check

The Linux launcher and installer do not start Aureon. They execute only the
fixed, isolated `linux-supervisor` boundary:

```bash
scripts/linux/install-linux.sh
scripts/linux/aureon-up.sh
```

Each command must exit non-zero with `decision: HOLD` and
`process_start_authorized: false`. No listener, frontend, daemon, trading mode,
or service is expected. `scripts/linux/aureon-status.sh` reports only a legacy
Supervisor socket if one already exists; `aureon-down.sh` never signals an
unverified PID file.

See [`LINUX_SETUP_GUIDE.md`](LINUX_SETUP_GUIDE.md) for the current release
requirements.
