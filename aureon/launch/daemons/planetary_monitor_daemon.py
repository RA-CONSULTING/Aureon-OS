"""Checkout seat standing in for the missing workspace planetary_monitor_daemon.py."""

from aureon.launch.checkout_daemons import main

if __name__ == "__main__":
    raise SystemExit(main("planetary_monitor_daemon"))
