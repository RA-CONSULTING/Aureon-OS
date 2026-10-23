"""Checkout seat standing in for the missing workspace real_time_data_feeder.py."""

from aureon.launch.checkout_daemons import main

if __name__ == "__main__":
    raise SystemExit(main("real_time_data_feeder"))
