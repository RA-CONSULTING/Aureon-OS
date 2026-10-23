#!/usr/bin/env python3
"""
Signal Scanner — Safe read-only scan of all trading systems.
Shows what the fire trader + ecosystem would trade, without executing anything.
"""
import sys, os, time, json, requests
sys.path.insert(0, os.path.dirname(__file__))

from datetime import datetime

def main():
    print("=" * 70)
    print("  SIGNAL SCANNER — All Systems (Read-Only)")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 70)

    # ── 1. Seer Global Gate ──────────────────────────────────────────
    print("\n[1] SEER GLOBAL GATE")
    seer_ok = True
    seer_risk_mod = 1.0
    try:
        from aureon.intelligence.aureon_seer import get_seer
        seer = get_seer()
        vision = seer.see()
        grade = vision.grade
        action = vision.action
        risk_mod = vision.risk_modifier
        score = vision.unified_score

        oracles_bullish = 0
        oracles_total = 0
        for name, oracle in [("gaia", vision.gaia), ("cosmos", vision.cosmos),
                              ("harmony", vision.harmony), ("spirits", vision.spirits),
                              ("timeline", vision.timeline), ("runes", vision.runes),
                              ("sentiment", vision.sentiment)]:
            if oracle and hasattr(oracle, 'score'):
                oracles_total += 1
                mark = "+" if oracle.score > 0.55 else "-"
                if oracle.score > 0.55:
                    oracles_bullish += 1
                print(f"    [{mark}] {name:12s} score={oracle.score:.3f}  conf={oracle.confidence:.2f}")

        consensus = f"{oracles_bullish}/{oracles_total}"
        seer_risk_mod = risk_mod
        blocked_actions = {'BLIND', 'DEFEND', 'SELL_BIAS'}
        if action in blocked_actions and score < 0.5:
            seer_ok = False

        status = "OPEN" if seer_ok else "BLOCKED"
        print(f"  Seer: score={score:.3f} grade={grade} action={action} risk_mod={risk_mod:.2f}")
        print(f"  Oracle consensus: {consensus} bullish  →  Gate: {status}")
    except Exception as e:
        print(f"  Seer unavailable: {e}")

    # ── 2. Per-Symbol Signals (Binance 1h klines) ────────────────────
    print("\n[2] PER-SYMBOL DIRECTIONAL SIGNALS (Binance 1h candles)")
    top_coins = ['BTC', 'ETH', 'SOL', 'XRP', 'ADA', 'AVAX', 'DOT', 'MATIC',
                 'LINK', 'DOGE', 'SHIB', 'SUI', 'TAO', 'NEAR', 'FET',
                 'RENDER', 'INJ', 'TIA', 'SEI', 'APT']

    bullish_symbols = []
    bearish_symbols = []

    for coin in top_coins:
        symbol = f"{coin}USDT"
        try:
            resp = requests.get(
                "https://api.binance.com/api/v3/klines",
                params={"symbol": symbol, "interval": "1h", "limit": 12},
                timeout=5
            )
            if resp.status_code != 200:
                continue
            candles = resp.json()
            if len(candles) < 6:
                continue

            closes = [float(c[4]) for c in candles]
            highs = [float(c[2]) for c in candles]
            lows = [float(c[3]) for c in candles]
            volumes = [float(c[5]) for c in candles]

            current_price = closes[-1]
            high_24h = max(highs)
            low_24h = min(lows)
            price_range = high_24h - low_24h if high_24h > low_24h else 1

            recent = candles[-6:]
            bullish_candles = sum(1 for c in recent if float(c[4]) > float(c[1]))
            trend_score = bullish_candles / 6.0

            avg_recent_3 = sum(closes[-3:]) / 3
            avg_prior_3 = sum(closes[-6:-3]) / 3
            momentum_pct = ((avg_recent_3 - avg_prior_3) / avg_prior_3) * 100 if avg_prior_3 > 0 else 0

            range_position = (current_price - low_24h) / price_range

            vol_recent = sum(volumes[-3:])
            vol_prior = sum(volumes[-6:-3])
            vol_ratio = vol_recent / vol_prior if vol_prior > 0 else 1.0

            momentum_signal = min(1.0, max(0.0, 0.5 + momentum_pct / 4))
            range_signal = 1.0 - range_position
            vol_signal = min(1.0, max(0.0, 0.3 + vol_ratio * 0.35))

            direction_score = (
                trend_score * 0.35 +
                momentum_signal * 0.30 +
                range_signal * 0.15 +
                vol_signal * 0.20
            )

            signal_strength = abs(direction_score - 0.5) * 2
            momentum_conviction = min(1.0, abs(momentum_pct) / 2.0)
            trend_agreement = 1.0 if (trend_score >= 0.5 and momentum_pct > 0) or (trend_score < 0.5 and momentum_pct < 0) else 0.4
            confidence = min(1.0, signal_strength * 0.5 + momentum_conviction * 0.3 + trend_agreement * 0.2)

            bullish = (direction_score > 0.55 and momentum_pct > -0.3 and
                       trend_score >= 0.33 and confidence >= 0.15)

            direction = "BULL" if bullish else "BEAR"
            mark = "+" if bullish else "-"
            print(f"  [{mark}] {coin:6s} ${current_price:>10.4f}  dir={direction_score:.3f}  "
                  f"mom={momentum_pct:+.2f}%  trend={trend_score:.2f}  "
                  f"vol={vol_ratio:.2f}  conf={confidence:.3f}  → {direction}")

            if bullish:
                bullish_symbols.append((coin, direction_score, confidence, momentum_pct, current_price))
            else:
                bearish_symbols.append((coin, direction_score, confidence, momentum_pct, current_price))

            time.sleep(0.1)  # Rate limit
        except Exception as e:
            print(f"  [?] {coin:6s} error: {e}")

    # ── 3. War Strategy Signals ──────────────────────────────────────
    print("\n[3] WAR STRATEGY — Quick Kill Probability")
    try:
        from aureon.command_centers.war_strategy import should_attack, get_quick_kill_estimate
        for coin, dscore, conf, mom, price in bullish_symbols[:10]:
            try:
                go, reason, priority = should_attack(coin, 'kraken')
                est = get_quick_kill_estimate(coin, 'kraken')
                prob = est.prob_penny_profit if est else 0
                mark = "ATTACK" if go else "RETREAT"
                print(f"  [{mark:7s}] {coin:6s}  kill_prob={prob:.2f}  priority={priority}  {reason}")
            except Exception as e:
                print(f"  [?] {coin:6s}  war error: {e}")
    except ImportError:
        print("  War Strategy not available")

    # ── 4. Sniper Brain Entry Signals ────────────────────────────────
    print("\n[4] SNIPER BRAIN — Entry Signal Scoring")
    try:
        from aureon.trading.unified_sniper_brain import get_unified_brain
        sniper = get_unified_brain(exchange='kraken')
        for coin, dscore, conf, mom, price in bullish_symbols[:10]:
            try:
                prices = [price * (1 - mom/100 * (1 - i/20)) for i in range(20)]
                volumes_list = [1000.0] * 20
                sig = sniper.get_entry_signal(coin, prices, volumes_list)
                print(f"  [{sig.action:12s}] {coin:6s}  conf={sig.confidence:.3f}  "
                      f"prob={sig.probability_score:.3f}  wisdom={sig.wisdom_score:.3f}  "
                      f"phase={sig.phase}")
            except Exception as e:
                print(f"  [?] {coin:6s}  sniper error: {e}")
    except ImportError:
        print("  Sniper Brain not available")

    # ── 5. Nexus Predictor ───────────────────────────────────────────
    print("\n[5] NEXUS PREDICTOR — 79.6% Win Rate Validation")
    try:
        from aureon.intelligence.nexus_predictor import NexusPredictor
        nexus = NexusPredictor()
        for coin, dscore, conf, mom, price in bullish_symbols[:10]:
            try:
                pred = nexus.predict_instant(
                    price=price,
                    high_24h=price * 1.02,
                    low_24h=price * 0.98,
                    momentum=mom / 100.0
                )
                prob = pred.get('probability', 0.5)
                edge = pred.get('edge', 0)
                should = pred.get('should_trade', False)
                mark = "TRADE" if should else "SKIP"
                print(f"  [{mark:5s}] {coin:6s}  prob={prob:.3f}  edge={edge:+.3f}  "
                      f"patterns={pred.get('patterns_detected', [])}")
            except Exception as e:
                print(f"  [?] {coin:6s}  nexus error: {e}")
    except ImportError:
        print("  Nexus Predictor not available (numpy missing?)")

    # ── 6. Miner Brain / Timeline Oracle ─────────────────────────────
    print("\n[6] MINER BRAIN — Timeline Oracle Predictions")
    try:
        from aureon.utils.aureon_miner_brain import MinerBrain
        miner = MinerBrain()
        for coin, dscore, conf, mom, price in bullish_symbols[:5]:
            try:
                action, branch, m_conf = miner.select_timeline_branch(coin, price, 1000, mom)
                print(f"  [{action:5s}] {coin:6s}  confidence={m_conf:.3f}  branch={branch}")
            except Exception as e:
                print(f"  [?] {coin:6s}  miner error: {e}")
    except ImportError:
        print("  Miner Brain not available")

    # ── Summary ──────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  SUMMARY")
    print("=" * 70)
    print(f"  Seer Gate:     {'OPEN' if seer_ok else 'BLOCKED'}  (risk_mod={seer_risk_mod:.2f})")
    print(f"  Bullish coins: {len(bullish_symbols)} / {len(top_coins)}")
    if bullish_symbols:
        top3 = sorted(bullish_symbols, key=lambda x: x[2], reverse=True)[:5]
        print(f"  Top signals:   {', '.join(f'{c[0]}({c[2]:.2f})' for c in top3)}")
    print(f"  Bearish coins: {len(bearish_symbols)} / {len(top_coins)}")
    print("=" * 70)


if __name__ == '__main__':
    main()
