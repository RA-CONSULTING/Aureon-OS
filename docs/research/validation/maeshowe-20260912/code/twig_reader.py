"""Candidate transliteration from supplied branch counts; no image interpretation.

The medieval preset follows Barnes, Runic Tradition in Orkney, p. 5 n. 1:
https://www.arild-hauge.com/PDF/Barnes_Orkney_2003_pp_4-17.pdf
It is a convention, not evidence that any particular mark uses that convention.
"""
import argparse
import hashlib
import itertools
import json
from pathlib import Path

# Transliteration alternatives remain alternatives, not resolved word meanings.
YOUNGER_GROUPS = (
    ("f", "u", "þ", "ą/o", "r", "k"),
    ("h", "n", "i", "a", "s"),
    ("t", "b", "m", "l", "ʀ/y"),
)
ELDER_GROUPS = (
    ("f", "u", "þ", "a", "r", "k", "g", "w"),
    ("h", "n", "i", "j", "ï", "p", "z", "s"),
    ("t", "b", "e", "m", "l", "ŋ", "d", "o"),
)


def count_options(value, field):
    if value is None:
        return None
    if not isinstance(value, list) or not value:
        raise ValueError(field + " must be null or a nonempty list of integer alternatives")
    if any(type(v) is not int or v < 0 or v > 32 for v in value):
        raise ValueError(field + " counts must be integers from 0 through 32")
    if len(value) != len(set(value)):
        raise ValueError(field + " contains duplicate alternatives")
    return sorted(value)


def candidate(group_count, position, alphabet, group_order):
    groups = YOUNGER_GROUPS if alphabet == "medieval_16" else ELDER_GROUPS
    if group_count not in (1, 2, 3):
        return None
    index = 3-group_count if group_order == "reverse" else group_count-1
    if position < 1 or position > len(groups[index]):
        return None
    return {"natural_group": index+1, "position": position,
            "transliteration": groups[index][position-1]}


def interpret(record):
    allowed = {"id", "left_counts", "right_counts", "group_side", "group_order",
               "alphabet", "provenance"}
    if not isinstance(record, dict) or set(record)-allowed:
        raise ValueError("record must be an object with only the documented fields")
    identifier = record.get("id")
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("nonempty id required")
    alphabet = record.get("alphabet", "medieval_16")
    if alphabet not in ("medieval_16", "elder_24_comparison"):
        raise ValueError("unknown alphabet")
    side = record.get("group_side")
    order = record.get("group_order")
    if side not in ("left", "right") or order not in ("forward", "reverse"):
        raise ValueError("group_side and group_order must be specified; they are never auto-selected")
    for key in ("left_counts", "right_counts"):
        if key not in record:
            raise ValueError(key + " required; use null if unobserved")
    left = count_options(record["left_counts"], "left_counts")
    right = count_options(record["right_counts"], "right_counts")
    provenance = record.get("provenance", {})
    if not isinstance(provenance, dict):
        raise ValueError("provenance must be an object")
    output = dict(id=identifier, alphabet=alphabet, group_side=side, group_order=order,
                  supplied_counts={"left": left, "right": right}, provenance=provenance,
                  candidates=[], rejected_count_pairs=[], physical_reading_verified=False,
                  interpretation="candidate transliteration only; no translation, frequency or historical confidence")
    if left is None or right is None:
        output["status"] = "UNOBSERVED_COUNTS"
        return output
    for l, r in itertools.product(left, right):
        g, p = (l, r) if side == "left" else (r, l)
        reading = candidate(g, p, alphabet, order)
        if reading is None:
            output["rejected_count_pairs"].append({"left": l, "right": r})
        else:
            output["candidates"].append(dict(reading, left=l, right=r))
    if not output["candidates"]:
        output["status"] = "NO_MATCH_UNDER_DECLARED_CONVENTION"
    elif len(left)*len(right) > 1:
        # Invalid alternatives do not turn an uncertain observation into certainty.
        output["status"] = "AMBIGUOUS_COUNTS"
    else:
        output["status"] = "SINGLE_CANDIDATE"
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    data = args.input.read_bytes()
    records = json.loads(data)
    if not isinstance(records, list):
        raise ValueError("input must be a list of mark records")
    ids = [r.get("id") for r in records if isinstance(r, dict)]
    if len(ids) != len(records) or len(ids) != len(set(ids)):
        raise ValueError("mark identifiers must be unique")
    results = [interpret(r) for r in records]
    payload = {"schema": "twig-count-candidates/v1", "input_sha256": hashlib.sha256(data).hexdigest(),
               "reader_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               "records": results}
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")


if __name__ == "__main__":
    main()
