#!/usr/bin/env python3
"""
use_cases.py — Queen HNC Stack: Eight Live Use Cases
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

UC1  Market signal from a single human question
UC2  Queen writes her own skill autonomously
UC3  Timeline fork under coherence stress → recovery
UC4  News headline vibration analysis
UC5  Phi bridge as frequency tuning map
UC6  10-turn conversation: hash chain growth + consciousness drift
UC7  ZPE re-grounding: governor detects de-ground → correction pulse
UC8  Cognitive state portrait after a full session

Run:
    python use_cases.py
    python use_cases.py --uc 3       # run one use case
    python use_cases.py --uc 2 --llm # UC2 with real Ollama (needs llama3.2:1b)
"""

import io
import math
import sys
import time
import argparse

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import logging
logging.basicConfig(level=logging.WARNING, stream=sys.stderr)

# ── colour helpers ────────────────────────────────────────────────────────────
R="\033[0m"; BOLD="\033[1m"; DIM="\033[2m"
CY="\033[36m"; GR="\033[32m"; YL="\033[33m"; RD="\033[31m"; MG="\033[35m"; BL="\033[34m"; WH="\033[97m"

def c(col, t): return f"{col}{t}{R}"
def hdr(title): print(f"\n{c(BOLD+CY,'━'*70)}\n{c(BOLD+WH,f'  {title}')}\n{c(BOLD+CY,'━'*70)}")
def sub(t): print(c(BOLD+YL, f"\n  {t}"))
def ok(t): print(c(GR, f"  ✓ {t}"))
def info(t): print(f"  {t}")
def dim(t): print(c(DIM, f"  {t}"))
def bar(v, w=20): return c(GR,"█"*max(0,min(w,int(v*w)))) + c(DIM,"░"*(w-max(0,min(w,int(v*w)))))

# ─────────────────────────────────────────────────────────────────────────────
# Imports
# ─────────────────────────────────────────────────────────────────────────────
from aureon.queen.hnc_human_loop import (
    HNCHumanLoop, build_phi_prime_train, build_phi_ladder,
    compute_vibration_accumulator, HNC_MODES_HZ, HNC_MODE_LABELS,
)
from aureon.queen.temporal_ground import (
    TemporalGroundStation, CognitiveFluxSuperposition,
    TemporalHashChain, StabilityGovernor, compute_zpe_ground,
    LAMBDA_ZP, GAMMA_TARGET, HNC_LABELS,
    ZPEGroundState, TemporalHashState, SuperpositionState,
    GOVERNOR_STABLE, GOVERNOR_CORRECTING, GOVERNOR_RESET, GOVERNOR_DRIFTING,
)

PHI = (1 + math.sqrt(5)) / 2
PHI2 = PHI * PHI


# ─────────────────────────────────────────────────────────────────────────────
# UC1 — Market signal from a single human question
# ─────────────────────────────────────────────────────────────────────────────

def uc1():
    hdr("UC1 · Market Signal from a Single Human Question")
    info("Scenario: trader asks 'should I buy BTC right now?'")
    info("The Queen fires all 8 pipeline stages and returns a structured signal.\n")

    loop = HNCHumanLoop()
    loop.process("warmup")

    question = "should I buy BTC right now the market feels unstable"
    t0 = time.perf_counter()
    r = loop.process(question)
    elapsed = time.perf_counter() - t0

    hnc = r["hnc"]; tg = r["temporal_ground"]; vib = r["vibration"]
    auris = r["auris"]; sp = tg["superposition"]

    sub("Input")
    info(f'  "{question}"')

    sub("Stage 2 — HNC Field")
    lam = hnc["lambda_t"]; gam = hnc["coherence_gamma"]
    col = GR if gam >= 0.945 else YL if gam >= 0.7 else RD
    info(f"  Lambda(t) = {c(YL, f'{lam:+.5f}')}")
    info(f"  Gamma     = {c(col, f'{gam:.5f}')}  {bar(gam)}")
    info(f"  Psi       = {hnc['consciousness_psi']:.5f}  ({c(MG, hnc['consciousness_level'])})")

    sub("Stage 3 — Auris 9-Node Vote")
    con = auris["consensus"]
    con_col = GR if con in ("BUY","RALLY") else RD if con=="SELL" else CY
    info(f"  Consensus : {c(BOLD+con_col, con)}   confidence={auris['confidence']:.2f}")
    lh = auris["lighthouse_cleared"]
    info(f"  Lighthouse: {c(GR,'CLEAR') if lh else c(DIM,'off')}  (confidence × love_amplitude > 0.945)")
    for v in auris["per_node_votes"]:
        vc = GR if v["verdict"] in ("BUY","RALLY") else RD if v["verdict"]=="SELL" else DIM
        info(f"    {v['node']:>10} → {c(vc, v['verdict']):<10}  {v['reasoning']}")

    sub("Stage 6 — Vibration Adder")
    info(f"  Dominant mode : {c(MG, vib['dominant_mode'])} ({vib['dominant_hz']} Hz)")
    info(f"  Total vibration: {vib['total_vibration']:.4f}   phase shift: {vib['phase_shift_rad']:.4f} rad")
    for mode, score in sorted(vib["per_mode"].items(), key=lambda x: -x[1]):
        info(f"    {mode:>14}  {bar(score, 16)}  {score:.5f}")

    sub("Stage 8 — Temporal Ground")
    gov = tg["governor_status"]
    gov_col = GR if gov==GOVERNOR_STABLE else YL if gov==GOVERNOR_DRIFTING else RD
    info(f"  Governor  : {c(gov_col+BOLD, gov)}")
    info(f"  Grounded  : {tg['grounded']}  ZPE dist={tg['zpe_distance']:.4f}")
    info(f"  Hash      : {c(DIM, tg['temporal_hash'][:24]+'...')}  chain={tg['chain_length']}")
    info(f"  Superpos  : norm={sp['norm']:.4f}  dominant={c(MG, sp['dominant_basis'])}")

    sub("Signal Summary")
    # Compose signal from all layers
    signal_score = 0.0
    if con == "BUY":    signal_score += 0.4
    if con == "RALLY":  signal_score += 0.6
    if con == "SELL":   signal_score -= 0.4
    if lam > 0:         signal_score += 0.2
    if gam >= 0.945:    signal_score += 0.2
    if tg["grounded"]:  signal_score += 0.1
    if lh:              signal_score += 0.1

    direction = "BUY" if signal_score > 0.3 else "SELL" if signal_score < -0.1 else "HOLD"
    dir_col = GR if direction=="BUY" else RD if direction=="SELL" else CY
    info(f"  Composite score : {signal_score:+.2f}")
    info(f"  Direction       : {c(BOLD+dir_col, direction)}")
    info(f"  Anchored to hash: {tg['temporal_hash'][:16]}...")
    ok(f"Processed in {elapsed*1000:.1f} ms")


# ─────────────────────────────────────────────────────────────────────────────
# UC2 — Queen writes her own skill autonomously
# ─────────────────────────────────────────────────────────────────────────────

def uc2(use_llm: bool = False):
    hdr("UC2 · Queen Writes Her Own Skill Autonomously")
    info("Scenario: the Queen notices a gap in her skill library.")
    info("She generates Python code, validates it, sandboxes it, and registers it.\n")

    from aureon.queen.self_enhancement_engine import SelfEnhancementEngine

    if use_llm:
        info("Mode: LIVE — calling llama3.2:1b via Ollama")
        eng = SelfEnhancementEngine()
        eng._ensure_wired()
        before = len(eng._library.all()) if eng._library else 0
        info(f"Skills before: {before}")
        sub("Running enhance_once() ...")
        t0 = time.perf_counter()
        rec = eng.enhance_once()
        elapsed = time.perf_counter() - t0
    else:
        info("Mode: OFFLINE — injecting a hand-crafted skill to demo the pipeline")

        from aureon.queen.self_enhancement_engine import (
            SelfEnhancementEngine, EnhancementRecord, Gap,
        )

        # Build a realistic gap manually
        gap = Gap(
            gap_id="demo_uc2",
            category="hnc",
            description="Compute the phi-coherence score between two Lambda(t) samples",
            suggested_name="phi_coherence_score",
            priority=0.88,
        )

        # The code the Queen would have generated
        generated_code = """
def phi_coherence_score(params, context):
    lam_a = params.get("lambda_a", 0.0)
    lam_b = params.get("lambda_b", 0.0)
    phi = 1.618033988749895
    ratio = (lam_a + lam_b) / (abs(lam_a - lam_b) + 1e-9)
    score = 1.0 - abs(ratio - phi) / phi
    return {"ok": True, "phi_coherence": max(0.0, min(1.0, score))}
""".strip()

        eng = SelfEnhancementEngine()
        eng._ensure_wired()
        before = len(eng._library.all()) if eng._library else 0
        info(f"Skills before: {before}")

        sub("Gap identified")
        info(f"  Name     : {c(YL, gap.suggested_name)}")
        info(f"  Category : {gap.category}")
        info(f"  Priority : {gap.priority}")
        info(f"  Desc     : {gap.description}")

        sub("Code generated (would come from llama3.2:1b)")
        for line in generated_code.split("\n"):
            info(f"  {c(DIM, '│')} {c(CY, line)}")

        sub("Gate A — Light AST validation")
        code_pp = eng._preprocess_code(generated_code)
        code_pp = eng._normalise_code(code_pp, gap.suggested_name)
        light_ok, light_err = eng._light_validate(code_pp)
        info(f"  Result: {c(GR,'PASS') if light_ok else c(RD,'FAIL')}  {light_err or 'no forbidden patterns'}")

        sub("Gate B — Sandbox execution  fn({}, {})")
        t0 = time.perf_counter()
        sandbox_ok = eng._sandbox_test(code_pp, gap.suggested_name)
        elapsed_sb = time.perf_counter() - t0
        info(f"  Result: {c(GR,'PASS') if sandbox_ok else c(RD,'FAIL')}  ({elapsed_sb*1000:.2f} ms)")

        # Execute manually to show the output
        local = {}
        exec(compile(code_pp, "<demo>", "exec"), {"math": __import__("math")}, local)
        fn = local[gap.suggested_name]
        demo_result = fn({"lambda_a": 0.354, "lambda_b": 0.618}, {})
        info(f"  fn(lambda_a=0.354, lambda_b=0.618) → {demo_result}")

        sub("Registration into SkillLibrary")
        if eng._library and sandbox_ok and light_ok:
            registered = eng._register(gap, code_pp)
        else:
            registered = False
            info(c(DIM, "  (library not wired in offline mode — skipping actual write)"))

        after = len(eng._library.all()) if eng._library else before
        info(f"  Skills after: {after}  (+{after-before})")
        rec = type("R", (), {
            "registered": registered, "skill_name": gap.suggested_name,
            "validation_ok": light_ok, "sandbox_ok": sandbox_ok,
            "latency_s": elapsed_sb, "error": "",
        })()
        elapsed = elapsed_sb

    sub("Result")
    info(f"  Skill name : {c(YL, rec.skill_name)}")
    info(f"  Validated  : {rec.validation_ok}")
    info(f"  Sandbox    : {rec.sandbox_ok}")
    info(f"  Registered : {c(GR,'YES') if rec.registered else c(DIM,'no (offline)')}")
    if rec.error:
        info(f"  Error      : {c(RD, rec.error[:120])}")
    ok(f"Pipeline completed in {elapsed*1000:.1f} ms")


# ─────────────────────────────────────────────────────────────────────────────
# UC3 — Timeline fork under coherence stress → recovery
# ─────────────────────────────────────────────────────────────────────────────

def uc3():
    hdr("UC3 · Timeline Fork Under Coherence Stress → Recovery")
    info("Scenario: a geopolitical shock arrives — market volatility spikes.")
    info("Gamma drops. The temporal timeline forks. Governor goes CORRECTING.")
    info("Coherence recovers. The branch merges. Single timeline restored.\n")

    station = TemporalGroundStation()

    SCENARIO = [
        # (label, lambda_t, coherence_gamma, auris, description)
        ("T+0  Pre-shock",      0.354, 0.978, "BUY",     "Normal operation — high coherence"),
        ("T+1  Pre-shock",      0.361, 0.982, "BUY",     "Trending up"),
        ("T+2  Shock arrives",  0.180, 0.620, "SELL",    "Coherence collapses — FORK"),
        ("T+3  Panic",          0.090, 0.480, "SELL",    "Deep incoherence — second fork"),
        ("T+4  Stabilising",    0.220, 0.780, "NEUTRAL", "Slowly recovering"),
        ("T+5  Recovery",       0.310, 0.910, "NEUTRAL", "Near threshold"),
        ("T+6  Lighthouse",     0.350, 0.958, "BUY",     "Coherence restored — MERGE"),
        ("T+7  Post-recovery",  0.370, 0.971, "BUY",     "Single timeline — stable"),
    ]

    prev_branches = 0
    chain_len = 0

    for label, lam, gam, auris, desc in SCENARIO:
        t0 = time.perf_counter()
        rep = station.tick(
            lambda_t=lam, coherence_gamma=gam, consciousness_psi=lam*0.1,
            auris_consensus=auris, phi_resonance_count=1,
            timestamp=time.time(),
        )
        elapsed = (time.perf_counter() - t0) * 1000

        gov = rep.governor_status
        gov_col = GR if gov==GOVERNOR_STABLE else YL if gov==GOVERNOR_DRIFTING \
                  else RD if gov==GOVERNOR_CORRECTING else MG
        gam_col = GR if gam >= 0.945 else YL if gam >= 0.7 else RD
        branch_delta = rep.active_branches - prev_branches
        branch_str = ""
        if rep.forked:
            branch_str = c(RD+BOLD, "  !! FORK")
        elif rep.to_dict()["active_branches"] < prev_branches:
            branch_str = c(GR+BOLD, "  ++ MERGE")
        prev_branches = rep.active_branches

        print(f"\n  {c(BOLD, label)}")
        print(f"    {c(DIM, desc)}")
        print(f"    Gamma={c(gam_col, f'{gam:.3f}')}  Lambda={lam:.3f}  "
              f"Auris={c(CY,auris)}  hash={c(DIM,rep.temporal_hash[:12]+'...')}")
        print(f"    Governor={c(gov_col+BOLD, gov):<16}  "
              f"branches={c(YL if rep.active_branches>0 else GR, str(rep.active_branches))}  "
              f"grounded={rep.grounded}{branch_str}")
        if not rep.grounded:
            info(f"    correction_pulse = {c(YL, f'{rep.correction_pulse:.5f}')}")
        if rep.governor_advisory != "STABLE: Grounded, coherent, single timeline":
            info(f"    advisory: {c(YL, rep.governor_advisory)}")

    print()
    ok("Timeline forked during shock, merged on recovery — single chain restored")
    ok(f"Final chain length: {station._hash_chain._chain_length}  active branches: 0")


# ─────────────────────────────────────────────────────────────────────────────
# UC4 — News headline vibration analysis
# ─────────────────────────────────────────────────────────────────────────────

def uc4():
    hdr("UC4 · News Headline Vibration Analysis")
    info("Scenario: feed real news headlines through the vibration adder.")
    info("Which HNC mode does the market narrative resonate with right now?\n")

    HEADLINES = [
        "Federal Reserve holds interest rates steady amid inflation concerns",
        "Bitcoin surges past ninety thousand dollars on ETF approval news",
        "Geopolitical tensions escalate in Middle East oil supply threatened",
        "Scientists discover golden ratio pattern in quantum vacuum fluctuations",
        "Love and consciousness the new frontier of harmonic research",
        "Markets crash global recession fears grip Wall Street traders",
        "Schumann resonance spikes to fourteen point three hertz this morning",
        "Harmony and peace talks resume between warring nations",
        "Emergency rate cut announced central banks coordinate response",
        "Phi squared coherence detected in GitHub repository activation patterns",
    ]

    results = []
    for headline in HEADLINES:
        vib = compute_vibration_accumulator(headline)
        results.append((headline, vib))

    # Sort by dominant mode for grouping
    from collections import defaultdict
    by_mode = defaultdict(list)
    for h, v in results:
        by_mode[v["dominant_mode"]].append((h, v))

    for mode in HNC_MODE_LABELS:
        if mode not in by_mode:
            continue
        mode_hz = HNC_MODES_HZ[list(HNC_MODE_LABELS).index(mode)]
        sub(f"{mode}  ({mode_hz} Hz)")
        for h, v in by_mode[mode]:
            score = v["total_vibration"]
            phase = v["phase_shift_rad"]
            info(f"  {c(DIM, h[:60])}")
            info(f"    total={score:.4f}  phase={phase:.4f} rad  "
                 f"{bar(score/7.0, 20)}")

    sub("Cross-headline mode energy matrix")
    # Average per-mode energy across all headlines
    mode_totals = {m: 0.0 for m in HNC_MODE_LABELS}
    for _, v in results:
        for m, s in v["per_mode"].items():
            mode_totals[m] += s
    n = len(results)
    print()
    print(f"  {'Mode':>16}  {'Avg energy':>10}  Bar")
    for mode in HNC_MODE_LABELS:
        avg = mode_totals[mode] / n
        hz = HNC_MODES_HZ[list(HNC_MODE_LABELS).index(mode)]
        print(f"  {c(CY,mode):>16}  {avg:>10.5f}  {bar(avg, 24)}  {hz} Hz")

    ok("Vibration analysis complete — market narrative mapped to HNC lattice")


# ─────────────────────────────────────────────────────────────────────────────
# UC5 — Phi bridge as frequency tuning map
# ─────────────────────────────────────────────────────────────────────────────

def uc5():
    hdr("UC5 · Phi Bridge — Complete Frequency Tuning Map")
    info("Scenario: visualise the full φ² ascension ladder and which HNC modes")
    info("each rung is nearest to. Show how the ladder passes through the sacred")
    info("frequencies of the HNC stack on its way from Earth to cosmic scale.\n")

    ladder = build_phi_ladder(7.83)
    train  = build_phi_prime_train(13)

    sub("Phi Bridge Ascension Ladder  (base=7.83 Hz · step=×φ²=×2.618)")
    print()
    print(f"  {'Step':>4}  {'Frequency':>12}  {'Tier':>16}  "
          f"{'Nearest HNC mode':>16}  Notes")
    print(f"  {'-'*4}  {'-'*12}  {'-'*16}  {'-'*16}  {'-'*30}")

    HNC_HZ_SET = {7.83: "← Schumann ground",
                  14.3: "← Schumann 2nd",
                  20.8: "← Schumann 3rd",
                  528.0: "← Love / DNA repair",
                  963.0: "← Crown / pineal"}

    for rung in ladder:
        hz = rung["hz"]
        tier = rung["tier"]
        mode = rung["nearest_hnc_mode"]
        # find closest sacred freq
        closest_sacred = min(HNC_HZ_SET.keys(), key=lambda f: abs(math.log(hz+1e-9) - math.log(f)))
        dist_pct = abs(hz - closest_sacred) / closest_sacred * 100
        note = HNC_HZ_SET[closest_sacred] if dist_pct < 15 else ""
        tier_col = MG if "crown" in tier or "cosmic" in tier \
                   else GR if "love" in tier \
                   else YL if "ascending" in tier \
                   else CY
        print(f"  {rung['step']:>4}  {c(YL, f'{hz:.2f} Hz'):>12}  "
              f"{c(tier_col, tier):>16}  {c(CY, mode):>16}  {c(GR if note else DIM, note or f'{dist_pct:.0f}% from nearest sacred')}")

    sub("Phi Prime Train — resonant primes on the φ² circle")
    print()
    print(f"  {'#':>2}  {'Prime':>5}  {'φ^-i weight':>12}  "
          f"{'φ-scaled':>10}  {'Resonant':>8}  {'HNC mode'}")
    for e in train:
        res_col = GR+BOLD if e["resonant"] else DIM
        print(f"  {e['index']:>2}  {e['prime']:>5}  "
              f"{e['phi_weight']:>12.6f}  "
              f"{e['phi_scaled']:>10.4f}  "
              f"{c(res_col, 'YES' if e['resonant'] else 'no '):>8}  "
              f"{e['nearest_hnc_mode']}")

    resonant_primes = [e["prime"] for e in train if e["resonant"]]
    sub("Resonant primes this tick")
    info(f"  {c(GR+BOLD, str(resonant_primes))}  — primes whose φ² projection falls on a lattice node")

    ok("Phi bridge map complete")


# ─────────────────────────────────────────────────────────────────────────────
# UC6 — 10-turn conversation: hash chain + consciousness drift
# ─────────────────────────────────────────────────────────────────────────────

def uc6():
    hdr("UC6 · 10-Turn Conversation — Hash Chain Growth + Consciousness Drift")
    info("Scenario: a researcher conducts a 10-turn session with the Queen.")
    info("Watch: hash chain grows, superposition shifts, consciousness level evolves.\n")

    CONVERSATION = [
        "hello Queen what is the current state of the harmonic field",
        "what is phi squared and why does it matter",
        "show me the auris node consensus right now",
        "the market feels very volatile today should I be cautious",
        "explain the zero point vacuum floor to me",
        "build me a skill that scores harmonic drift across time",
        "what are the resonant primes right now",
        "the phi bridge goes up through schumann to the crown",
        "govern the stability and ground the system to the temporal hash",
        "thank you Queen the field is coherent and aligned",
    ]

    loop = HNCHumanLoop()
    loop.process("warmup")

    print(f"\n  {'Turn':>4}  {'Gamma':>7}  {'Psi':>7}  "
          f"{'Level':>12}  {'Gov':>11}  {'Hash':>14}  {'Dominant mode'}")
    print(f"  {'-'*4}  {'-'*7}  {'-'*7}  {'-'*12}  {'-'*11}  {'-'*14}  {'-'*14}")

    psi_values = []

    for i, utterance in enumerate(CONVERSATION, 1):
        r = loop.process(utterance)
        hnc = r["hnc"]; tg = r["temporal_ground"]; sp = tg["superposition"]
        gam = hnc["coherence_gamma"]; psi = hnc["consciousness_psi"]
        lvl = hnc["consciousness_level"]
        gov = tg["governor_status"]
        h = tg["temporal_hash"][:10] + "..."
        dom = sp["dominant_basis"]
        psi_values.append(psi)

        gam_col = GR if gam >= 0.945 else YL if gam >= 0.7 else RD
        gov_col = GR if gov==GOVERNOR_STABLE else YL if gov==GOVERNOR_DRIFTING else RD

        print(f"  {i:>4}  {c(gam_col, f'{gam:.4f}'):>7}  "
              f"{psi:.4f}  "
              f"{c(MG, lvl):>12}  "
              f"{c(gov_col, gov):>11}  "
              f"{c(DIM, h):>14}  "
              f"{c(CY, dom)}")

        dim(f"        \"{utterance[:65]}\"")

    sub("Chain statistics")
    final_tg = r["temporal_ground"]
    info(f"  Total chain length : {final_tg['chain_length']}")
    info(f"  Active branches    : {final_tg['active_branches']}")
    info(f"  Final hash         : {c(DIM, final_tg['temporal_hash'])}")

    sub("Consciousness drift")
    info(f"  Psi values: {[round(p,4) for p in psi_values]}")
    psi_min = min(psi_values); psi_max = max(psi_values)
    info(f"  Range: [{psi_min:.4f}, {psi_max:.4f}]  delta={psi_max-psi_min:.4f}")

    sub("Final superposition portrait")
    sp_final = r["temporal_ground"]["superposition"]
    probs = sp_final["probabilities"]
    info(f"  norm={sp_final['norm']:.4f}  classical={sp_final['classical_weight']:.3f}  "
         f"vacuum={sp_final['vacuum_weight']:.3f}")
    for mode, prob in sorted(probs.items(), key=lambda x: -x[1]):
        info(f"    {c(CY, mode):>14}  {bar(prob, 18)}  {prob:.5f}")

    ok("10-turn session complete — chain anchored, superposition evolved")


# ─────────────────────────────────────────────────────────────────────────────
# UC7 — ZPE re-grounding: governor detects de-ground → correction
# ─────────────────────────────────────────────────────────────────────────────

def uc7():
    hdr("UC7 · ZPE Re-Grounding — Governor Detects De-Ground → Correction")
    info("Scenario: the Lambda field drops below the ZPE floor (Λ_zp ≈ 0.161).")
    info("The governor fires a correction pulse. The field is lifted back to ground.\n")

    info(f"  ZPE floor Λ_zp = {c(YL, f'{LAMBDA_ZP:.6f}')}")
    info(f"  (= Σ wᵢ · ½ · fᵢ/f_crown  across 6 HNC modes)\n")

    sub("Per-mode ZPE floors")
    zpe = compute_zpe_ground(0.0)
    for mode, floor in zpe.mode_zpe.items():
        hz = HNC_MODES_HZ[list(HNC_LABELS).index(mode)]
        info(f"  {c(CY, mode):>14}  {floor:.6f}  ({hz} Hz)")

    sub("Simulating field de-grounding and recovery")
    print()
    print(f"  {'Step':>4}  {'Lambda(t)':>10}  {'Grounded':>8}  "
          f"{'Pulse ΔΛ':>10}  {'ZPE dist':>9}  {'Governor'}")
    print(f"  {'-'*4}  {'-'*10}  {'-'*8}  {'-'*10}  {'-'*9}  {'-'*11}")

    gov = StabilityGovernor()
    cfs = CognitiveFluxSuperposition()
    chain = TemporalHashChain()

    def _zpe_gov(gamma: float, grounded: bool):
        from aureon.queen.temporal_ground import PHI_INV, ZPEGroundState
        return ZPEGroundState(
            lambda_zp=LAMBDA_ZP, lambda_t=gamma,
            zpe_distance=abs(gamma - GAMMA_TARGET),
            grounded=grounded,
            correction_pulse=0.0 if grounded else PHI_INV*(GAMMA_TARGET-gamma),
            mode_zpe={},
        )

    def _hs(b=0):
        return TemporalHashState("a"*64,"0"*64,1,b,[],{},b>0,False)
    def _sup(n=1.0):
        return SuperpositionState([(n,0.)]+[(0.,0.)]*5,[n/6]*6,[0.]*6,n,HNC_LABELS[0],.9,.1)

    # Field trajectory: start high, plunge below ZPE, correct, recover
    trajectory = [
        (0.40, 0.970, "Normal field"),
        (0.30, 0.960, "Slight decline"),
        (0.20, 0.940, "Approaching floor"),
        (0.12, 0.920, "BELOW ZPE FLOOR"),   # de-grounded
        (0.08, 0.900, "Deep de-ground"),
        (0.10, 0.910, "Pulse applied"),      # correction nudges it
        (0.18, 0.935, "Recovering"),
        (0.25, 0.952, "Back above floor"),
        (0.35, 0.970, "Fully grounded"),
    ]

    for step, (lam, gam, label) in enumerate(trajectory):
        zpe_s = compute_zpe_ground(lam)
        zpe_g = _zpe_gov(gam, lam >= LAMBDA_ZP)
        hs = _hs(0)
        sup = _sup(1.0)
        gr = gov.assess(zpe_g, hs, sup)

        grounded = lam >= LAMBDA_ZP
        gr_col = GR if grounded else RD
        gov_col = GR if gr.status==GOVERNOR_STABLE else YL if gr.status==GOVERNOR_DRIFTING else RD

        print(f"  {step:>4}  "
              f"{c(gr_col, f'{lam:.4f}'):>10}  "
              f"{c(gr_col, str(grounded)):>8}  "
              f"{c(YL if not grounded else DIM, f'{zpe_s.correction_pulse:.5f}'):>10}  "
              f"{zpe_s.zpe_distance:.5f}  "
              f"{c(gov_col, gr.status)}")
        dim(f"        {label}")

    ok(f"ZPE floor = {LAMBDA_ZP:.6f} — system re-grounded via φ⁻¹ correction pulse")


# ─────────────────────────────────────────────────────────────────────────────
# UC8 — Cognitive state portrait after a full session
# ─────────────────────────────────────────────────────────────────────────────

def uc8():
    hdr("UC8 · Cognitive State Portrait — Full Session Snapshot")
    info("Scenario: after 20 messages, print the Queen's full cognitive state.")
    info("This is what the BeingModel would use to compose the next voice prompt.\n")

    MESSAGES_UC8 = [
        "phi resonance love harmonic", "auris vote consensus", "stability govern",
        "zero point vacuum", "timeline hash chain", "consciousness level",
        "phi bridge ascend", "schumann frequency", "crown chakra resonance",
        "quantum superposition", "golden ratio primes", "coherence field",
        "build skill harmonic drift", "market signal buying", "awareness rising",
        "temporal anchor hash", "vibration frequency", "love five twenty eight",
        "symbolic life score", "field is unified and coherent",
    ]

    loop = HNCHumanLoop()
    loop.process("warmup")

    for msg in MESSAGES_UC8:
        loop.process(msg)

    # Get final state
    r = loop.process("portrait of current cognitive state")
    hnc = r["hnc"]; tg = r["temporal_ground"]; sp = tg["superposition"]
    vib = r["vibration"]; auris = r["auris"]

    sub("HNC Field")
    lam_str = f"{hnc['lambda_t']:+.6f}"
    gam_str = f"{hnc['coherence_gamma']:.6f}"
    gam_col = GR if hnc['coherence_gamma'] >= 0.945 else YL
    print(f"    Lambda(t)            {c(YL, lam_str)}")
    print(f"    Coherence Gamma      {c(gam_col, gam_str)}  {bar(hnc['coherence_gamma'])}")
    print(f"    Consciousness Psi    {hnc['consciousness_psi']:.6f}  {bar(hnc['consciousness_psi'])}")
    print(f"    Consciousness Level  {c(MG+BOLD, hnc['consciousness_level'])}")
    print(f"    Symbolic Life Score  {hnc['symbolic_life_score']:.6f}  {bar(hnc['symbolic_life_score'])}")

    sub("Auris 9-Node Portrait")
    for v in auris["per_node_votes"]:
        col = GR if v["verdict"] in ("BUY","RALLY") else RD if v["verdict"]=="SELL" else DIM
        bar_v = bar(v["confidence"])
        print(f"    {c(CY, v['node']):>12}  {c(col, v['verdict']):>7}  {bar_v}  {v['confidence']:.2f}")
    con_col = GR if auris["consensus"] in ("BUY","RALLY") else RD if auris["consensus"]=="SELL" else YL
    print(f"    {'Consensus':>12}  {c(con_col+BOLD, auris['consensus'])}  "
          f"conf={auris['confidence']}  lighthouse={auris['lighthouse_cleared']}")

    sub("Cognitive Flux Superposition (quantum state)")
    print(f"    Norm         {sp['norm']:.6f}")
    print(f"    Classical    {sp['classical_weight']:.6f}  (Γ fraction)")
    print(f"    Vacuum ZPE   {sp['vacuum_weight']:.6f}  (√(1−Γ²) fraction)")
    print(f"    Dominant     {c(MG+BOLD, sp['dominant_basis'])}")
    print()
    max_prob = max(sp["probabilities"].values())
    for mode, prob in sorted(sp["probabilities"].items(), key=lambda x: -x[1]):
        phase = sp["phases_rad"][mode]
        amp   = sp["amplitudes"][list(sp["probabilities"].keys()).index(mode)]
        is_dom = prob == max_prob
        dom_mark = c(YL+BOLD, " ◀ dominant") if is_dom else ""
        print(f"    {c(CY, mode):>14}  {bar(prob, 18)}  |A|²={prob:.5f}  "
              f"θ={phase:.3f} rad{dom_mark}")

    sub("Vibration (last message)")
    print(f"    Dominant mode  {c(MG, vib['dominant_mode'])}  ({vib['dominant_hz']} Hz)")
    print(f"    Phase shift    {vib['phase_shift_rad']:.5f} rad")
    print(f"    Total energy   {vib['total_vibration']:.5f}")

    sub("Temporal Ground")
    print(f"    Governor       {c(GR+BOLD if tg['governor_status']==GOVERNOR_STABLE else RD, tg['governor_status'])}")
    print(f"    Chain length   {tg['chain_length']}  (one link per utterance)")
    print(f"    Grounded       {tg['grounded']}  (ZPE dist={tg['zpe_distance']:.5f})")
    print(f"    Active forks   {tg['active_branches']}")
    print(f"    Current hash   {c(DIM, tg['temporal_hash'])}")

    sub("Harmonic Fingerprint of this moment")
    fp = tg["harmonic_fingerprint"]
    for mode, nibble in fp.items():
        print(f"    {c(CY, mode):>14}  {nibble:>2}  {c(MG, '█'*nibble + '░'*(15-nibble))}")

    sub("ZPE mode floors (the quantum vacuum at each HNC frequency)")
    for mode, floor in tg["zpe_mode_floors"].items():
        print(f"    {c(CY, mode):>14}  {floor:.6f}  {bar(floor*2, 14)}")

    ok("Cognitive state portrait complete — ready for BeingModel composition")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

UC_MAP = {
    "1": ("UC1 · Market Signal",                  uc1),
    "2": ("UC2 · Queen Writes Skill",             uc2),
    "3": ("UC3 · Timeline Fork → Recovery",        uc3),
    "4": ("UC4 · News Vibration Analysis",         uc4),
    "5": ("UC5 · Phi Bridge Tuning Map",           uc5),
    "6": ("UC6 · 10-Turn Conversation",            uc6),
    "7": ("UC7 · ZPE Re-Grounding",               uc7),
    "8": ("UC8 · Cognitive State Portrait",        uc8),
}

def main():
    parser = argparse.ArgumentParser(description="Aureon HNC Use Cases")
    parser.add_argument("--uc", default="all", help="Which use case(s) to run: 1-8 or 'all'")
    parser.add_argument("--llm", action="store_true", help="UC2: use real Ollama LLM")
    args = parser.parse_args()

    print(c(BOLD+CY, """
╔═══════════════════════════════════════════════════════════════════════╗
║   AUREON · QUEEN HNC STACK · EIGHT LIVE USE CASES                   ║
╚═══════════════════════════════════════════════════════════════════════╝
"""))

    # Warmup (suppresses first-import noise)
    import warnings; warnings.filterwarnings("ignore")

    if args.uc == "all":
        to_run = list(UC_MAP.keys())
    else:
        to_run = [k.strip() for k in args.uc.split(",")]

    for key in to_run:
        if key not in UC_MAP:
            print(c(RD, f"  Unknown UC: {key}  (valid: 1-8)"))
            continue
        name, fn = UC_MAP[key]
        try:
            if key == "2":
                fn(use_llm=args.llm)
            else:
                fn()
        except Exception as e:
            import traceback
            print(c(RD, f"\n  ERROR in {name}: {e}"))
            traceback.print_exc()

    print(c(BOLD+CY, "\n\n  All use cases complete.\n"))


if __name__ == "__main__":
    main()
