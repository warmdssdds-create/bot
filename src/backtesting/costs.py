from __future__ import annotations

import math


TAKER_FEE_RATE = 0.00055
SLIPPAGE_BPS_PER_SIDE = 1.5


def apply_slippage(price: float, side: str, is_entry: bool) -> float:
    slippage = SLIPPAGE_BPS_PER_SIDE / 10000
    if side == "buy":
        return price * (1 + slippage if is_entry else 1 - slippage)
    return price * (1 - slippage if is_entry else 1 + slippage)


def taker_fee(notional: float) -> float:
    return abs(notional) * TAKER_FEE_RATE


def funding_cost(notional: float, periods_8h: int, funding_rate_per_8h: float) -> float:
    return abs(notional) * funding_rate_per_8h * max(0, periods_8h)


def eight_hour_periods(entry_ts, exit_ts) -> int:
    seconds = max(0.0, (exit_ts - entry_ts).total_seconds())
    return math.floor(seconds / (8 * 3600))
