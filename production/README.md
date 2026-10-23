# Aureon installer

`install.sh` (Linux and macOS) and `Install-AUREON.ps1` (Windows; the `.bat`
wrappers call it) install Python tooling when the host can, write `.env` from
`.env.example` only when `.env` is absent, and start the master-launcher
preflight. Live trading stays off. When the UI answers, the installer prints
`Aureon UI: http://127.0.0.1:8080/`. Dashboard and Command Center are tabs of
that page. The thought bus listens on `http://127.0.0.1:8765/health`.

`entrypoint.sh`, `Dockerfile`, `docker-compose.yml`, and `supervisord.conf` in
this directory stay on the isolated hold. They do not start the UI.

The hold entrypoints above still stop before a process start. The installer
does not. It does not arm live trading and it does not place an order.
