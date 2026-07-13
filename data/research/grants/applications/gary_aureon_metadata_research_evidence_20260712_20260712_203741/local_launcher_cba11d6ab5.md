# Aureon Local Launcher, Setup Wizard, and Dashboard

This guide describes the new guided setup, encrypted config storage, launcher CLI, and lightweight dashboard.

## Guided setup
Run the wizard to collect exchange credentials and defaults. Keys are validated with a quick connectivity probe to your chosen exchange.
```bash
python -m cli.setup_wizard
```
Use `--dev-plaintext` (via the launcher) only for local development to store `config.json` unencrypted. Production defaults to encrypted `config.json.enc` protected by `config.key`.

## Launcher
Start trading plus the local dashboard from one entry point:
```bash
python -m cli.launcher --start
```
- `--no-dashboard` skips opening the browser UI.
- `--dashboard-port 8001` overrides the port.
- `--run-wizard` re-runs setup.
- `--register-autostart` creates an OS-level scheduled task (Windows) or writes shortcut instructions (Unix) and marks `auto_start` in the config.

## Dashboard
A minimal Flask UI is hosted locally (default `http://127.0.0.1:8000`) showing:
- Connection status (running/stopped)
- P&L, open positions
- Recent logs
- Start/Stop Trading control

The UI is intentionally lightweight for offline use; API status is also available at `/api/status` for integrations.

## Packaging
PyInstaller instructions and a post-build smoke test live in `packaging/pyinstaller_build.md`. Run the provided smoke test after building `aureon.exe` to ensure the binary starts cleanly.
