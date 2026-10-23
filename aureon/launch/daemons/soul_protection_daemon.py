"""Checkout seat standing in for the missing workspace soul_protection_daemon.py."""

from aureon.launch.checkout_daemons import main

if __name__ == "__main__":
    raise SystemExit(main("soul_protection_daemon"))
