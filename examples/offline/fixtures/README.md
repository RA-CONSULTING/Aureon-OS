# Offline gallery fixtures

Committed stand-ins for the three gallery commands. Nothing here was fetched for this gallery.

`kraken_ohlc.json` and `kraken_spread.json` are synthetic public-shaped venue bodies. The prices are a short arithmetic series (closes 100 through 112, then one still-open bar at 999 that the loader drops). They are not a live Kraken capture and they are not a trading signal.

`cold_boot_child.json` is the child-probe shape `judge_default` reads. `measured_on_this_machine` is false. It is not `reports/measured/native_process_containment.json`.
