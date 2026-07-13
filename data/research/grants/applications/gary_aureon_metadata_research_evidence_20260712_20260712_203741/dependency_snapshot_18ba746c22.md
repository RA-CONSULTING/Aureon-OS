# Dependency Snapshot

Date: 2026-05-14

## Node package versions

From `npm ls --depth=0 --json`:

- `@xterm/addon-fit`: `0.11.0`
- `@xterm/xterm`: `6.0.0`
- `dockerode`: `5.0.0`
- `express`: `5.2.1`
- `node-pty`: `1.1.0`
- `ws`: `8.20.1`
- `wrangler`: `4.90.1`

## Lock and config files preserved

- `package-lock.json`
- `package.json`
- `runtime/Dockerfile`
- `wrangler.jsonc`

## Runtime shell/tooling assumptions

Host/local assumptions:
- Node.js available
- npm available
- bash available
- curl available
- Docker available for sandbox mode

Container assumptions in `runtime/Dockerfile`:
- Ubuntu 24.04 base
- python3
- nodejs
- npm
- git
- curl
- build-essential
- sudo
- nano
- vim
