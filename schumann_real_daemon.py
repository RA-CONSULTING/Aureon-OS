"""Workspace name for the checkout Schumann seat. Live trading stays off."""

from aureon.launch.checkout_daemons import main

if __name__ == "__main__":
    raise SystemExit(main("schumann_real_daemon"))
