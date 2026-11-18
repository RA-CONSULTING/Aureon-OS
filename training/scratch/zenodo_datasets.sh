#!/bin/bash
# Size the real trading-data population on Zenodo.
#
# Two corrections over the previous attempt:
#   * `resource_type:dataset` is not a queryable field -- it returns 0 for
#     everything, which reads as "no datasets exist" but means "bad field name".
#     The API exposes resource type as a request parameter, `type=dataset`.
#   * Firing ~36 requests back to back trips anonymous throttling, and the
#     throttled body has no "hits" key, so every later row failed with KeyError.
#     One request per 1.5 s stays under the limit.
set -u

API=https://zenodo.org/api/records

# $1 = query, $2 = optional type filter. Prints total, or the HTTP status on error.
total() {
    local extra=()
    [ -n "${2:-}" ] && extra=(--data-urlencode "type=$2")
    curl -s -G "$API" --data-urlencode "q=$1" "${extra[@]}" \
        --data-urlencode 'size=1' -w '\n%{http_code}' \
        | python3 -c '
import json, sys
raw = sys.stdin.read().rsplit("\n", 1)
code = raw[1] if len(raw) > 1 else "?"
try:
    body = json.loads(raw[0])
    print(body["hits"]["total"])
except Exception:
    print("HTTP " + code)
'
    sleep 1.5
}

printf '=== population ===\n'
printf '%-40s %10s\n' "all datasets on Zenodo" "$(total '*' dataset)"
printf '%-40s %10s\n' "all publications"      "$(total '*' publication)"

printf '\n=== per phrase: all types vs datasets only ===\n'
printf '%-30s %8s %8s\n' "phrase" "all" "dataset"
while IFS= read -r phrase; do
    [ -z "$phrase" ] && continue
    printf '%-30s %8s %8s\n' "$phrase" \
        "$(total "\"$phrase\"")" \
        "$(total "\"$phrase\"" dataset)"
done <<'QUERIES'
limit order book
order book
high frequency trading
market microstructure
financial time series
tick data
order flow
stock prices
stock market
cryptocurrency
bitcoin
ohlcv
intraday
trading strategy
backtesting
price prediction
exchange rates
volatility
QUERIES
