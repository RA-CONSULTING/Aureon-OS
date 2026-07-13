#!/usr/bin/env python3
"""
run_hnc_live.py  —  Queen HNC Human Interaction Loop · Live Terminal
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Type anything and press Enter.
The Queen's full pipeline fires:

  INTENT  →  HNC Λ(t)  →  AURIS 9-node  →  PHI PRIME TRAIN
  →  PHI BRIDGE  →  VIBRATION ADDER  →  TEMPORAL GROUND
  (hash chain · ZPE floor · cognitive superposition · governor)

Commands:
  /full      toggle full detail on / off   (default: summary)
  /super     show full superposition amplitudes
  /ladder    show full phi bridge ladder
  /primes    show full phi prime train
  /chain     show hash chain status
  /quit      exit
"""

import io
import logging
import math
import sys
import time

# Force UTF-8 on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

logging.basicConfig(level=logging.WARNING, stream=sys.stderr)

from aureon.queen.hnc_human_loop import HNCHumanLoop

# ── palette ──────────────────────────────────────────────────────────────────
RESET  = "\033[0m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
CYAN   = "\033[36m"
GREEN  = "\033[32m"
YELLOW = "\033[33m"
RED    = "\033[31m"
MAGENTA= "\033[35m"
BLUE   = "\033[34m"
WHITE  = "\033[97m"

GOV_COLOR = {
    "STABLE":     GREEN,
    "DRIFTING":   YELLOW,
    "CORRECTING": RED,
    "RESET":      MAGENTA,
}

LEVEL_COLOR = {
    "DORMANT": DIM, "DREAMING": DIM, "STIRRING": CYAN,
    "AWARE": CYAN, "PRESENT": CYAN, "FOCUSED": GREEN,
    "INTUITIVE": GREEN, "CONNECTED": YELLOW,
    "FLOWING": YELLOW, "TRANSCENDENT": MAGENTA, "UNIFIED": MAGENTA,
}

def c(color, text):
    return f"{color}{text}{RESET}"

def bar(val, width=20, filled="█", empty="░"):
    n = max(0, min(width, int(val * width)))
    return filled * n + empty * (width - n)

def nibble_bar(n):
    """0-15 as block bar."""
    return "█" * n + "░" * (15 - n)


# ── rendering helpers ─────────────────────────────────────────────────────────

def render_summary(r: dict, elapsed: float) -> None:
    hnc = r["hnc"]
    tg  = r["temporal_ground"]
    sp  = tg["superposition"]
    vib = r["vibration"]
    gov = tg["governor_status"]
    gov_col = GOV_COLOR.get(gov, WHITE)
    lvl = hnc["consciousness_level"]
    lvl_col = LEVEL_COLOR.get(lvl, WHITE)

    # ── header
    print(c(BOLD + CYAN, "\n┌─ HNC TICK ─────────────────────────────────────────────────────────"))

    # ── field
    lam  = hnc["lambda_t"]
    gam  = hnc["coherence_gamma"]
    psi  = hnc["consciousness_psi"]
    sls  = hnc["symbolic_life_score"]

    lam_sign = "+" if lam >= 0 else ""
    print(f"│  {c(BOLD,'Lambda(t)')}   {c(YELLOW, f'{lam_sign}{lam:.5f}')}   "
          f"{c(BOLD,'Gamma')} {c(GREEN if gam>=0.945 else RED, f'{gam:.5f}')}   "
          f"{c(BOLD,'Psi')} {c(lvl_col, f'{psi:.4f}')}   "
          f"{c(BOLD,'SymLife')} {c(CYAN, f'{sls:.4f}')}")
    print(f"│  {c(BOLD,'Consciousness')}  {c(lvl_col + BOLD, lvl)}   "
          f"  {c(BOLD,'Gamma bar')}  {c(GREEN if gam>=0.945 else YELLOW, bar(gam))}")

    # ── Auris
    auris   = r["auris"]
    con     = auris["consensus"]
    conf    = auris["confidence"]
    lh      = auris["lighthouse_cleared"]
    lh_str  = c(GREEN, "LIGHTHOUSE CLEAR") if lh else c(DIM, "lighthouse off")
    con_col = GREEN if con in ("BUY","RALLY") else RED if con=="SELL" else CYAN
    print(f"│  {c(BOLD,'Auris')}  {c(con_col+BOLD, con):20}  conf={conf:.2f}  {lh_str}")

    # ── Governor + hash
    print(f"│  {c(BOLD,'Governor')}  {c(gov_col+BOLD, gov):16}  "
          f"{c(BOLD,'Hash')} {c(DIM, tg['temporal_hash'][:16]+'...')}  "
          f"chain={tg['chain_length']}  "
          f"forks={tg['active_branches']}")
    if tg["forked"]:
        print(f"│  {c(YELLOW+BOLD,'  !! TIMELINE FORKED this tick !!')}")

    # ── ZPE
    grounded = tg["grounded"]
    dist     = tg["zpe_distance"]
    pulse    = tg["correction_pulse"]
    zpe_str  = c(GREEN, "GROUNDED") if grounded else c(RED, f"DE-GROUNDED  pulse={pulse:.4f}")
    print(f"│  {c(BOLD,'ZPE')}  {zpe_str}   dist={dist:.4f}")

    # ── Superposition snapshot (top 2 modes)
    probs = sp["probabilities"]
    dom   = sp["dominant_basis"]
    norm  = sp["norm"]
    cw    = sp["classical_weight"]
    vw    = sp["vacuum_weight"]
    sorted_modes = sorted(probs.items(), key=lambda x: -x[1])[:2]
    modes_str = "  ".join(f"{c(CYAN,m)}={p:.4f}" for m, p in sorted_modes)
    print(f"│  {c(BOLD,'Superposition')}  norm={norm:.4f}  "
          f"classical={cw:.3f}  vacuum={vw:.3f}")
    print(f"│    dominant→{c(MAGENTA+BOLD, dom)}   top modes: {modes_str}")

    # ── Vibration
    dom_mode = vib["dominant_mode"]
    dom_hz   = vib["dominant_hz"]
    total_v  = vib["total_vibration"]
    phase_r  = vib["phase_shift_rad"]
    print(f"│  {c(BOLD,'Vibration')}  total={total_v:.4f}  "
          f"dominant={c(MAGENTA, dom_mode)} ({dom_hz} Hz)  "
          f"phase={phase_r:.4f} rad")

    # ── Phi prime train (resonant only)
    resonant = [e for e in r["phi_prime_train"] if e["resonant"]]
    res_str = ", ".join(str(e["prime"]) for e in resonant) or "none"
    print(f"│  {c(BOLD,'Phi resonant primes')}  [{c(CYAN, res_str)}]  "
          f"({len(resonant)} of 13)")

    # ── Intent
    intent  = r["intent"]
    itype   = intent.get("intent_type", "?")
    action  = intent.get("action", "?")
    iconf   = intent.get("confidence", 0)
    print(f"│  {c(BOLD,'Intent')}  type={c(CYAN,itype)}  action={c(CYAN,action)}  conf={iconf:.3f}")

    # ── Motion hint
    if r.get("motion_code_hint"):
        print(f"│  {c(GREEN+BOLD,'Motion')}  {r['motion_code_hint']}")

    # ── governor advisory
    adv = tg["governor_advisory"]
    print(f"│  {c(gov_col,'Advisory')}  {adv}")

    print(f"│  {c(DIM, f'processed in {elapsed:.2f}s')}")
    print(c(BOLD + CYAN, "└────────────────────────────────────────────────────────────────────"))


def render_superposition(r: dict) -> None:
    sp = r["temporal_ground"]["superposition"]
    print(c(BOLD + MAGENTA, "\n  COGNITIVE FLUX SUPERPOSITION — full amplitudes"))
    print(f"  {'mode':>14}  {'re':>9}  {'im':>9}  {'|A|^2':>8}  {'phase(rad)':>10}  prob bar")
    probs_d = sp["probabilities"]
    phases_d = sp["phases_rad"]
    for amp in sp["amplitudes"]:
        m = amp["mode"]
        re, im = amp["re"], amp["im"]
        prob = round(re**2 + im**2, 5)
        ph = phases_d.get(m, 0)
        pb = bar(prob, width=16)
        print(f"  {c(CYAN,m):>14}  {re:>9.5f}  {im:>9.5f}  {prob:>8.5f}  "
              f"{ph:>10.5f}  {c(MAGENTA, pb)}")
    print(f"  norm={sp['norm']}  classical={sp['classical_weight']}  vacuum={sp['vacuum_weight']}")


def render_ladder(r: dict) -> None:
    print(c(BOLD + BLUE, "\n  PHI BRIDGE ASCENSION LADDER"))
    print(f"  {'step':>4}  {'hz':>10}  {'tier':>16}  {'hnc_mode':>16}")
    for rung in r["phi_ladder"]:
        hz_str = f"{rung['hz']:.2f} Hz"
        print(f"  {rung['step']:>4}  {c(CYAN, hz_str):>10}  "
              f"{rung['tier']:>16}  {c(BLUE, rung['nearest_hnc_mode']):>16}")


def render_primes(r: dict) -> None:
    print(c(BOLD + YELLOW, "\n  PHI PRIME TRAIN  (first 13 primes on the phi lattice)"))
    print(f"  {'#':>2}  {'prime':>5}  {'phi_weight':>10}  {'phi_scaled':>10}  "
          f"{'resonant':>8}  {'hnc_mode'}")
    for e in r["phi_prime_train"]:
        res = c(GREEN, "YES") if e["resonant"] else c(DIM, "no ")
        print(f"  {e['index']:>2}  {e['prime']:>5}  {e['phi_weight']:>10.6f}  "
              f"{e['phi_scaled']:>10.4f}  {res:>8}  {e['nearest_hnc_mode']}")


def render_chain(r: dict) -> None:
    tg = r["temporal_ground"]
    print(c(BOLD + GREEN, "\n  TEMPORAL MULTIVERSE HASH CHAIN"))
    print(f"  Current hash  : {c(DIM, tg['temporal_hash'])}")
    print(f"  Chain length  : {tg['chain_length']}")
    print(f"  Active forks  : {tg['active_branches']}")
    print(f"  Forked        : {tg['forked']}")
    print(f"  ZPE grounded  : {tg['grounded']}   dist={tg['zpe_distance']:.5f}")
    print(c(BOLD, "  Harmonic fingerprint (hash nibbles → HNC modes):"))
    for mode, val in tg["harmonic_fingerprint"].items():
        print(f"    {c(CYAN, mode):>14} : {val:>2}  {c(GREEN, nibble_bar(val))}")
    print(c(BOLD, "  ZPE mode floors:"))
    for mode, floor in tg["zpe_mode_floors"].items():
        print(f"    {c(CYAN, mode):>14} : {floor:.6f}  {c(BLUE, bar(floor * 2, width=12))}")


# ── main loop ─────────────────────────────────────────────────────────────────

def main() -> None:
    print(c(BOLD + CYAN, """
╔══════════════════════════════════════════════════════════════════════╗
║   AUREON  ·  HNC HUMAN INTERACTION LOOP  ·  LIVE TERMINAL          ║
║   Temporal Ground  ·  ZPE  ·  Superposition  ·  Governor           ║
╚══════════════════════════════════════════════════════════════════════╝
"""))
    print(c(DIM, "  Initialising HNCHumanLoop …"))
    loop = HNCHumanLoop()
    # warm up (suppress first-call overhead from lazy imports)
    loop.process("warmup")
    print(c(GREEN, "  Ready.\n"))
    print(c(DIM, "  Commands: /full  /super  /ladder  /primes  /chain  /quit\n"))

    full_mode = False
    last_result = None

    while True:
        try:
            raw = input(c(BOLD + CYAN, "You > ") + RESET).strip()
        except (EOFError, KeyboardInterrupt):
            print(c(DIM, "\n  Goodbye."))
            break

        if not raw:
            continue

        # ── commands ──
        if raw == "/quit":
            print(c(DIM, "  Goodbye."))
            break
        if raw == "/full":
            full_mode = not full_mode
            print(c(DIM, f"  Full mode {'ON' if full_mode else 'OFF'}"))
            continue
        if raw == "/super":
            if last_result:
                render_superposition(last_result)
            else:
                print(c(DIM, "  No result yet — type something first."))
            continue
        if raw == "/ladder":
            if last_result:
                render_ladder(last_result)
            else:
                print(c(DIM, "  No result yet."))
            continue
        if raw == "/primes":
            if last_result:
                render_primes(last_result)
            else:
                print(c(DIM, "  No result yet."))
            continue
        if raw == "/chain":
            if last_result:
                render_chain(last_result)
            else:
                print(c(DIM, "  No result yet."))
            continue

        # ── process ──
        t0 = time.time()
        result = loop.process(raw)
        elapsed = time.time() - t0
        last_result = result

        render_summary(result, elapsed)

        if full_mode:
            render_superposition(result)
            render_ladder(result)
            render_primes(result)
            render_chain(result)


if __name__ == "__main__":
    main()
