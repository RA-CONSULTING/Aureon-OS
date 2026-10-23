"""Workspace name for the checkout planetary seat. No ephemeris is invented."""

from aureon.launch.checkout_daemons import main

if __name__ == "__main__":
    raise SystemExit(main("planetary_monitor_daemon"))
