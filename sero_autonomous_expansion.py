"""Workspace name for the checkout expansion seat. It does not place an order."""

from aureon.launch.checkout_daemons import main

if __name__ == "__main__":
    raise SystemExit(main("sero_autonomous_expansion"))
