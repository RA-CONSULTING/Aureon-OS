#!/usr/bin/env bash
set -euo pipefail

# Audit the checkout and the current user's caches. No host home is named.

echo "== Filesystem =="
df -h .

echo
echo "== Checkout =="
du -sh . .git frontend aureon 2>/dev/null | sort -h || true

echo
echo "== Home caches (current user) =="
du -sh "$HOME/.cache" "$HOME/.npm" "$HOME/.local" 2>/dev/null | sort -h || true

echo
echo "== Desktop hotspots =="
du -sh "$HOME/Desktop"/* 2>/dev/null | sort -h | tail -n 20 || true

echo
echo "== Cache hotspots =="
du -sh "$HOME/.cache"/* 2>/dev/null | sort -h | tail -n 20 || true
