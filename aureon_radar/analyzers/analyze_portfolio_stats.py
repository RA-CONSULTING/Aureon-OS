# -*- coding: utf-8 -*-
"""Analyze full portfolio win rate (standalone CLI script)."""
import json
import os


def analyze(path='cost_basis_history.json'):
    with open(path, 'r') as f:
        data = json.load(f)

    positions = data.get('positions', {})

    winners = 0
    losers = 0
    breakeven = 0
    total_cost = 0
    total_current = 0

    for symbol, pos in positions.items():
        if not isinstance(pos, dict):
            continue

        qty = float(pos.get('total_quantity', 0) or 0)
        cost = float(pos.get('total_cost', 0) or 0)
        entry = float(pos.get('avg_entry_price', 0) or 0)
        current_val = qty * entry  # Rough estimate

        if cost > 0.01:
            pnl = current_val - cost
            if pnl > 0.01:
                winners += 1
            elif pnl < -0.01:
                losers += 1
            else:
                breakeven += 1

            total_cost += cost
            total_current += current_val

    total = winners + losers + breakeven
    win_pct = (winners / total * 100) if total > 0 else 0
    loss_pct = (losers / total * 100) if total > 0 else 0

    print(f'ANALYSIS OF ALL {total} POSITIONS:')
    print(f'   Winners:   {winners} ({win_pct:.1f}%)')
    print(f'   Losers:    {losers} ({loss_pct:.1f}%)')
    print(f'   Breakeven: {breakeven}')
    print()
    print('PORTFOLIO VALUE:')
    print(f'   Total Cost Basis:                ${total_cost:,.2f}')
    print(f'   Using entry prices as current:   ${total_current:,.2f}')
    print(f'   Unrealized P&L:                  ${total_current - total_cost:,.2f}')


if __name__ == '__main__':
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else 'cost_basis_history.json'
    if not os.path.exists(path):
        print(f'[skip] {path} not found — portfolio analysis needs a live cost basis history file')
        sys.exit(0)
    analyze(path)
