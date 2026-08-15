from __future__ import annotations

import pandas as pd

from src.risk.circuit_breaker import CircuitBreaker, CircuitBreakerState
from src.risk.position_sizing import calculate_trade_levels, position_size_from_risk


def test_position_size_matches_fixed_fractional_formula() -> None:
    size = position_size_from_risk(equity=10000, risk_per_trade=0.0075, entry=100, stop_loss=98, max_leverage=3)
    assert size == 37.5


def test_trade_levels_for_long_and_short() -> None:
    long_levels = calculate_trade_levels("buy", 100, 4, 97, 1.5, 0.1, 0.75)
    short_levels = calculate_trade_levels("sell", 100, 4, 103, 1.5, 0.1, 0.75)
    assert long_levels.stop_loss == 96.6
    assert round(long_levels.take_profit, 2) == 102.55
    assert short_levels.stop_loss == 103.4
    assert round(short_levels.take_profit, 2) == 97.45


def test_circuit_breaker_pauses_after_loss_streak() -> None:
    breaker = CircuitBreaker(0.03, 0.08, 5, 4)
    state = CircuitBreakerState(start_equity_day=10000, start_equity_week=10000)
    ts = pd.Timestamp("2024-01-01T00:00:00Z")
    equity = 10000
    for _ in range(5):
        equity -= 100
        breaker.register_trade(ts, -100, equity, state)
        ts += pd.Timedelta(minutes=15)
    assert state.paused_until is not None
    assert breaker.can_trade(pd.Timestamp("2024-01-01T01:30:00Z"), equity, state) is False
