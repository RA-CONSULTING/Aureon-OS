#!/bin/bash
# Diagnose the two Zenodo API limits that shape the harvest design.
#
# 1. Result window: Elasticsearch refuses from+size > 10000, so page 401 at
#    size=25 answers HTTP 400 and every query is silently capped at 10k records.
# 2. Match semantics: a bare `q=limit order book` is an OR match, so it reports
#    354k hits -- mostly records that merely contain the word "order". Phrase
#    quoting collapses that to the records actually about limit order books.
#
# Run on the login node (only place with outbound network).
set -u

API=https://zenodo.org/api/records

total() {
    curl -s -G "$API" --data-urlencode "q=$1" --data-urlencode 'size=1' \
        | python3 -c 'import json,sys; print(json.load(sys.stdin)["hits"]["total"])'
}

row() {
    printf '%-28s %10s\n' "$1" "$(total "$2")"
}

row "loose OR (limit order book)"        'limit order book'
row "phrase (\"limit order book\")"      '"limit order book"'
row "phrase AND dataset"                 '"limit order book" AND resource_type:dataset'
row "phrase, year 2020"                  '"limit order book" AND publication_date:[2020-01-01 TO 2020-12-31]'
row "phrase, year 2024"                  '"limit order book" AND publication_date:[2024-01-01 TO 2024-12-31]'

row "loose OR (high frequency trading)"  'high frequency trading'
row "phrase hft"                         '"high frequency trading"'
row "phrase hft AND dataset"             '"high frequency trading" AND resource_type:dataset'

row "loose OR (market microstructure)"   'market microstructure'
row "phrase microstructure"              '"market microstructure"'
