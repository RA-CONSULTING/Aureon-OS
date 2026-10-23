"""Workspace name for the checkout NOAA seat. Live trading stays off."""

from aureon.launch.checkout_daemons import main

if __name__ == "__main__":
    raise SystemExit(main("sero_space_weather"))
