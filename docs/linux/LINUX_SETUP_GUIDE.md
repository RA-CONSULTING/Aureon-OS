# Aureon Linux protection status

Native Linux installation and startup are currently **HOLD**.

`scripts/linux/install-linux.sh`, `scripts/linux/aureon-up.sh`, and every
shipped systemd/Supervisor runtime route terminate at the fixed standard-library
protection bootstrap. They create no environment, install no package, start no
Aureon module, publish no port, and arm no trading mode.

## Safe verification

```bash
/usr/bin/python3 -I -S -B scripts/bootstrap/protected_bootstrap_v05.py --target-id linux-supervisor
bash -n scripts/linux/install-linux.sh scripts/linux/aureon-up.sh
```

The expected result is exit status 1 plus a registered, target-specific JSON
`HOLD` receipt with `process_start_authorized: false`. Exit status 2 is an
invalid bootstrap/request failure and is not acceptable evidence.

Do not install, enable systemd units, add credentials, use `--live`, or infer
health from localhost ports while the hold remains. Native process containment,
durable authenticated HNC evidence, full census closure, and an external trust
anchor are still required before a Linux runtime can be released.
