"""Workspace name for the checkout real-time feeder. Live trading stays off."""

from aureon.launch.checkout_daemons import main

if __name__ == "__main__":
    raise SystemExit(main("real_time_data_feeder"))
