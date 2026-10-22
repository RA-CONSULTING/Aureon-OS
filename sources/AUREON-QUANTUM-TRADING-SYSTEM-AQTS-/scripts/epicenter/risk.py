import math


def floor_to_step(qty: float, step: float) -> float:
    if step <= 0:
        return qty
    return math.floor(qty / step) * step


def enforce_rules(qty: float, price: float, min_qty: float, step: float, min_notional: float):
    q = max(qty, min_qty)
    q = floor_to_step(q, step) if step else q
    if q <= 0:
        return None
    if min_notional:
        notional = q*price
        if notional < min_notional:
            need = min_notional/price
            q2 = floor_to_step(max(need, min_qty), step)
            if q2*price < min_notional:
                return None
            q = q2
    return q
