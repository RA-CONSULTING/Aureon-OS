# Aureon on Linux — current command boundary

All previously documented direct module, live-trading, Supervisor, frontend,
and systemd start commands are withdrawn while the OS protection release is on
HOLD.

| Purpose | Supported command | Expected result |
|---|---|---|
| Verify Linux boundary | `scripts/linux/aureon-up.sh` | terminal `linux-supervisor` HOLD |
| Verify installer boundary | `scripts/linux/install-linux.sh` | terminal `linux-supervisor` HOLD |
| Inspect legacy status | `scripts/linux/aureon-status.sh` | read-only; no health claim |
| Request legacy shutdown | `scripts/linux/aureon-down.sh` | socket acknowledgement or refusal; never raw PID kill |

Do not run `python -m aureon.*`, Node listeners, `--live`, or `systemctl enable
--now` as a substitute for the missing native process boundary. Source modules
remain available for tests and review, not as certified production entrypoints.
