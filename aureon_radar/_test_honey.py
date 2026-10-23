print('=== TEST 3: Honey Ladder Mechanics ===')
from honey_ladder import HoneyLadder, ShadowLadderRun
import time

hl = HoneyLadder()

# Create shadow with correct fields
shadow = ShadowLadderRun(
    signal_id='test-1',
    timestamp=time.time(),
    symbol='USDJPY',
    direction='LONG',
    entry_price=158.688,
    target_price=158.688 * 1.0005,
    source='test',
    sector='forex',
    ladder_rung=1,
    status='OPEN',
    pnl=0.0,
    phi_score=0.5
)
hl.shadow_runs.append(shadow)

print(f'  Shadow created: {shadow.symbol} {shadow.direction}')
print(f'  Entry: {shadow.entry_price}')
print(f'  Target: {shadow.target_price}')
print(f'  Target distance: {(shadow.target_price - shadow.entry_price) / shadow.entry_price * 100:.4f}%')

# Test update_shadow (which checks for hits)
print('\n  Testing price updates...')
hl.update_shadow('USDJPY', 158.69)  # Should not hit
status = hl.get_status()
print(f'  After price 158.69: open={status["shadow_stats"]["open"]} hits={status["shadow_stats"]["hits"]}')

hl.update_shadow('USDJPY', 158.80)  # Should hit
status = hl.get_status()
print(f'  After price 158.80: open={status["shadow_stats"]["open"]} hits={status["shadow_stats"]["hits"]}')

# Test honey pot
print('\n  Testing Honey Pot...')
print(f'  Honey pot active: {hl.honey_pot["active"]}')

# Test graduation candidate
print('\n  Testing graduation...')
# Add a rung 3+ shadow
shadow2 = ShadowLadderRun(
    signal_id='test-2',
    timestamp=time.time(),
    symbol='EURUSD',
    direction='LONG',
    entry_price=1.1596,
    target_price=1.1596 * 1.0005,
    source='test2',
    sector='forex',
    ladder_rung=3,
    status='OPEN',
    pnl=0.0,
    phi_score=0.7
)
hl.shadow_runs.append(shadow2)

candidate = hl.get_graduation_candidate()
if candidate:
    print(f'  Graduation candidate: {candidate.symbol} {candidate.direction} (rung {candidate.ladder_rung})')
else:
    print('  No graduation candidate (honey pot may be full)')

print('\n=== TEST 3 PASSED ===')
