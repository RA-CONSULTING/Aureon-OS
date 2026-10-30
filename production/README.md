# Installer

> **New users: stay on the five-minute quickstart in the root README. Do not add your own exchange keys.** This installer calls the master launcher, which defaults to full autonomy. If exchange keys are in `.env`, that boot can go live and trade.

`install.sh` is the Linux and macOS installer. `Install-AUREON.ps1` is the Windows installer. `install-windows.bat` and `Install-AUREON-Windows.bat` call that PowerShell script. Re-running any of them is safe.

From a fresh clone:

```bash
bash production/install.sh
```

Windows:

```bat
production\Install-AUREON.ps1
```

The installer adds the system toolchain when apt, dnf, Homebrew, or winget can (Python 3, venv, Node, npm, git, curl). It writes `.env` from `.env.example` when `.env` is absent and does not rewrite an existing file. It installs the frontend packages, runs `npm run build`, and notes whether Docker is answering. It then starts the organism with `scripts/launch/aureon-master.sh` (Windows: `scripts\launch\aureon-master.ps1`). That launcher installs Python requirements into `.venv`, Node packages if they are still missing, and Docker images when the daemon answers. With no daemon it uses the native fallbacks. When the UI answers, the installer prints:

```
Aureon UI: http://127.0.0.1:5173/
Aureon UI is reachable: http://127.0.0.1:5173/ (HTTP 200)
```

An existing `.env` is left alone. Credentials are not written into the repo. The installer does not place an order.

`entrypoint.sh`, `Dockerfile`, `docker-compose.yml`, and `supervisord.conf` in this directory stay on the isolated hold. They are not this installer. `scripts/linux/install-linux.sh` stays on that hold as well.
