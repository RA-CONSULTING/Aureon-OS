Running continuously (stocks enabled)

Two recommended options to keep the bot running forever and auto-restart on failure.

1) systemd (recommended on Linux servers)

- Copy the unit file to /etc/systemd/system and enable it:

```bash
# As root or with sudo
cp deploy/micro_profit_labyrinth.service /etc/systemd/system/micro_profit_labyrinth.service
# Optionally edit env vars: `systemctl edit --full micro_profit_labyrinth.service`
systemctl daemon-reload
systemctl enable --now micro_profit_labyrinth.service
```

- Check status & logs:

```bash
systemctl status micro_profit_labyrinth.service
journalctl -u micro_profit_labyrinth.service -f
```

2) Dev / Container mode (no systemd): use the restart loop

```bash
chmod +x scripts/run_micro_forever.sh
./scripts/run_micro_forever.sh --env-file .env
```

Notes:
- By default the service runs with `ALPACA_INCLUDE_STOCKS=true` and `ALPACA_EXECUTE=false` (verify-only). Edit the service file or supply an env file to change that.
- The CLI flag `--duration 0` means "run forever" and is the default used by the service/script.
- For production, run under a dedicated service account and secure your API keys.
