"""Frozen-model reproduction and exhaustive conditional assignment controls."""
import argparse
import collections
import csv
import dataclasses
import datetime
import gzip
import hashlib
import importlib.util
import io
import itertools
import json
import math
import os
from pathlib import Path
import platform
import socket
import sys
import time
import unittest

HERE = Path(__file__).resolve().parent
ORIGINALS = {
    "759f5501fe42901b0250b5f02b600a6d3fcd44d0": "e75541e3d47c5d1ac2ef4823f0fb7cd042ccb6089b53c565374faafe2457ef5c",
    "c2d6a2910d9fb95b151c920021fbaf2591522e58": "0c066ed68863f7742273d26ad1b15fed6806d25efe50174cad9821706d23746b",
}
WALLS = ("NE", "NW", "SW", "SE")
PHI = (1+math.sqrt(5))/2


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_module(blob, expected):
    path = HERE/"originals"/(blob+".py")
    assert sha(path) == expected, "original source hash mismatch"
    spec = importlib.util.spec_from_file_location("frozen_"+blob, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def stable(value):
    obj = dataclasses.asdict(value)
    obj.pop("timestamp")
    return obj


def phi_metrics(freq, node):
    distance_raw = min(abs(r-target) for r in (freq/node, node/freq)
                       for target in (PHI, 1/PHI))
    dist = round(distance_raw, 6)
    resonant, exact = distance_raw < .01, distance_raw < .0001
    if exact:
        score = 1.0
    elif resonant:
        score = 1.0-dist/.01*.2
    elif dist < .05:
        score = max(.2, .8-dist*10)
    else:
        score = .1
    return score, int(resonant), int(exact), dist


def schumann(beat, modes):
    # Match the frozen model's search across all seven stored targets.
    idx = min(range(len(modes)), key=lambda i: abs(beat-modes[i]))
    delta = abs(beat-modes[idx])
    return idx+1, modes[idx], round(delta, 4), round(max(0, 1-delta/modes[idx]), 6)


def wall_assignments():
    indices = tuple(range(9))
    result = []
    for ne in itertools.combinations(indices, 3):
        rest = tuple(i for i in indices if i not in ne)
        for nw in itertools.combinations(rest, 1):
            rest2 = tuple(i for i in rest if i not in nw)
            for sw in itertools.combinations(rest2, 2):
                assignment = tuple(0 if i in ne else 1 if i in nw else 2 if i in sw else 3 for i in indices)
                result.append(assignment)
    assert len(result) == len(set(result)) == 5040
    assert all(collections.Counter(a) == {0: 3, 1: 1, 2: 2, 3: 3} for a in result)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--job-id")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    mods = [source_module(b, s) for b, s in ORIGINALS.items()]
    baselines = [m.MaeshoweDecoder().read() for m in mods]
    assert stable(baselines[0]) == stable(baselines[1])
    m, base = mods[0], baselines[0]
    assert base.gamma == .493163 and base.master_beat_hz == 29.2832
    test_stream = io.StringIO()
    suite = unittest.defaultTestLoader.discover(str(HERE), pattern="test_twig_reader.py")
    test_result = unittest.TextTestRunner(stream=test_stream, verbosity=2).run(suite)
    (args.output/"reader-tests.txt").write_text(test_stream.getvalue(), encoding="utf-8")
    assert test_result.wasSuccessful() and test_result.testsRun == 12
    complete = [r for r in base.readings if r.complete and r.seer_hz is not None]
    assert len(complete) == 9 and len(set(r.rune_name for r in complete)) == 9
    nodes = tuple(m.WALL_AURIS[w]["freq"] for w in WALLS)
    assignments = wall_assignments()
    original_assignment = tuple(WALLS.index(r.wall) for r in complete)
    assert original_assignment in assignments
    # Verify all 24 x 4 original rune/frequency pairs, not only the baseline.
    for rune in m._RUNE_TABLE:
        for wall, node in zip(WALLS, nodes):
            reference = m.test_phi_resonance(rune, wall)
            score, hit, exact, dist = phi_metrics(rune.effective_hz, node)
            assert (hit, exact, dist) == (reference.is_phi_resonant, reference.is_exact, reference.phi_distance)
            assert abs(score-m.MaeshoweDecoder()._phi_score(reference)) < 1e-12
    phi_table = [[phi_metrics(r.seer_hz, n) for n in nodes] for r in complete]
    phi_average = sum(phi_table[i][w][0] for i, w in enumerate(original_assignment))/9
    mean_caller = sum(r.caller_hz for r in base.readings)/13
    mean_seer = sum(r.seer_hz for r in complete)/9
    nearest = schumann(abs(mean_seer-mean_caller), m.SCHUMANN_MODES)
    independent_gamma = round(.5*phi_average+.3*9/13+.2*nearest[3], 6)
    assert independent_gamma == base.gamma
    pivot_rows = []
    for left, right in itertools.product(range(1, 4), range(1, 9)):
        decoder = m.MaeshoweDecoder()
        rune = decoder.set_pivot_rune(left, right)
        value = decoder.read()
        pivot_rows.append(dict(left=left, right=right, rune=rune.name, gamma=value.gamma, status=value.gamma_status))
    result = dict(schema="maeshowe-repair-controls/v1", utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  status="PREFLIGHT_PASS", host=socket.gethostname(), python=sys.version,
                  platform=platform.platform(), job_id=args.job_id or os.environ.get("SLURM_JOB_ID"),
                  protocol_sha256=sha(HERE/"PROTOCOL.md"), original_hashes=ORIGINALS,
                  reader_tests_passed=test_result.testsRun, verified_phi_pairs=96,
                  baseline=m.MaeshoweDecoder().lattice_to_dict(base), baseline_independent_gamma=independent_gamma,
                  equivalent_original_versions=True, assignments=len(assignments),
                  original_assignment_index=assignments.index(original_assignment),
                  hypothetical_pivots=pivot_rows,
                  qualification="Conditional model controls; no observed twig counts, no decipherment and no historical probability.")
    if not args.preflight:
        permutations = list(itertools.permutations(range(4)))
        all_wall_counts = [sum(r.wall == wall for r in base.readings) for wall in WALLS]
        control_path = args.output/"conditional-controls.csv.gz"
        total, gamma_ge, phi_ge, schumann_le = 0, 0, 0, 0
        original_map_gamma_ge, original_map_phi_ge = 0, 0
        gamma_min, gamma_max = 1.0, 0.0
        seen_original = 0
        identity = (0, 1, 2, 3)
        with gzip.open(control_path, "wt", encoding="utf-8", newline="") as out:
            writer = csv.writer(out)
            writer.writerow(["wall_frequency_permutation", "rune_wall_assignment", "gamma", "phi_hits", "exact_phi_hits", "master_beat_hz", "nearest_schumann_delta_hz"])
            for pi, perm in enumerate(permutations):
                caller = sum(all_wall_counts[w]*nodes[perm[w]] for w in range(4))/13
                beat = abs(caller-mean_seer)
                sch = schumann(beat, m.SCHUMANN_MODES)
                for ai, assignment in enumerate(assignments):
                    values = [phi_table[i][perm[w]] for i, w in enumerate(assignment)]
                    gamma = round(.5*sum(v[0] for v in values)/9+.3*9/13+.2*sch[3], 6)
                    hits = sum(v[1] for v in values)
                    exact = sum(v[2] for v in values)
                    assert math.isfinite(gamma) and 0 <= gamma <= 1
                    total += 1
                    gamma_ge += gamma >= base.gamma
                    phi_ge += hits >= base.n_phi_resonant
                    schumann_le += sch[2] <= base.schumann_delta
                    if perm == identity:
                        original_map_gamma_ge += gamma >= base.gamma
                        original_map_phi_ge += hits >= base.n_phi_resonant
                        if assignment == original_assignment:
                            assert (gamma, hits, exact) == (base.gamma, base.n_phi_resonant, base.n_exact_phi)
                            seen_original += 1
                    gamma_min, gamma_max = min(gamma_min, gamma), max(gamma_max, gamma)
                    writer.writerow([pi, ai, format(gamma, ".6f"), hits, exact, format(beat, ".4f"), format(sch[2], ".4f")])
        assert total == 120960 and seen_original == 1
        mapping = dict(walls=WALLS, wall_frequencies_hz=nodes, completed_rune_order=[r.rune_name for r in complete],
                       completed_wall_counts=[3, 1, 2, 3], all_entry_wall_counts=all_wall_counts,
                       permutations=permutations, assignments=assignments)
        (args.output/"configuration-index.json").write_text(json.dumps(mapping, separators=(",", ":"))+"\n", encoding="utf-8")
        neutral = [m.RUNE_BY_NAME[r.rune_name].solfeggio_base_hz for r in complete]
        neutral_phi = [phi_metrics(f, nodes[w]) for f, w in zip(neutral, original_assignment)]
        neutral_beat = abs(sum(neutral)/9-mean_caller)
        neutral_sch = schumann(neutral_beat, m.SCHUMANN_MODES)
        result.update(status="COMPLETED", configurations=total, gamma_range=[gamma_min, gamma_max],
            conditional_ranks=dict(
                gamma_ge_baseline={"count": gamma_ge, "denominator": total, "fraction": gamma_ge/total},
                phi_hits_ge_baseline={"count": phi_ge, "denominator": total, "fraction": phi_ge/total},
                schumann_delta_le_baseline={"count": schumann_le, "denominator": total, "fraction": schumann_le/total},
                original_wall_map_gamma_ge={"count": original_map_gamma_ge, "denominator": 5040, "fraction": original_map_gamma_ge/5040},
                original_wall_map_phi_hits_ge={"count": original_map_phi_ge, "denominator": 5040, "fraction": original_map_phi_ge/5040}),
            neutral_amplitude=dict(factors=[1, 1, 1], targets_unchanged=True,
                phi_hits=sum(v[1] for v in neutral_phi), exact_phi_hits=sum(v[2] for v in neutral_phi),
                mean_seer_hz=sum(neutral)/9, master_beat_hz=neutral_beat,
                gamma=round(.5*sum(v[0] for v in neutral_phi)/9+.3*9/13+.2*neutral_sch[3], 6)))
    result["elapsed_s"] = time.monotonic()-started
    (args.output/"summary.json").write_text(json.dumps(result, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    files = [p for p in sorted(args.output.iterdir()) if p.is_file() and p.name != "results.sha256"]
    (args.output/"results.sha256").write_text("".join(sha(p)+"  "+p.name+"\n" for p in files), encoding="utf-8")
    print(json.dumps({k:result[k] for k in ("status", "job_id", "reader_tests_passed", "elapsed_s")}))
    if not args.preflight:
        print(json.dumps(result["conditional_ranks"]))


if __name__ == "__main__":
    main()
