from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


@dataclass
class CircuitBreakerState:
    start_equity_day: float
    start_equity_week: float
    paused_until: pd.Timestamp | None = None
    weekly_halt: bool = False
    consecutive_losses: int = 0
    last_day: pd.Timestamp | None = None
    last_week: int | None = None
    closed_pnl: list[tuple[pd.Timestamp, float]] = field(default_factory=list)


class CircuitBreaker:
    def __init__(self, daily_limit: float, weekly_limit: float, consecutive_loss_limit: int, pause_hours: int) -> None:
        self.daily_limit = daily_limit
        self.weekly_limit = weekly_limit
        self.consecutive_loss_limit = consecutive_loss_limit
        self.pause_hours = pause_hours

    def reset_periods(self, ts: pd.Timestamp, equity: float, state: CircuitBreakerState) -> None:
        if state.last_day is None or ts.normalize() != state.last_day.normalize():
            state.start_equity_day = equity
            state.last_day = ts
        week = int(ts.isocalendar().week)
        if state.last_week is None or week != state.last_week:
            state.start_equity_week = equity
            state.last_week = week
            state.weekly_halt = False

    def register_trade(self, ts: pd.Timestamp, pnl: float, equity: float, state: CircuitBreakerState) -> None:
        self.reset_periods(ts, equity, state)
        state.closed_pnl.append((ts, pnl))
        if pnl < 0:
            state.consecutive_losses += 1
            if state.consecutive_losses >= self.consecutive_loss_limit:
                state.paused_until = ts + pd.Timedelta(hours=self.pause_hours)
        else:
            state.consecutive_losses = 0

        if equity <= state.start_equity_day * (1 - self.daily_limit):
            state.paused_until = max(filter(None, [state.paused_until, ts + pd.Timedelta(days=1)]), default=ts + pd.Timedelta(days=1))
        if equity <= state.start_equity_week * (1 - self.weekly_limit):
            state.weekly_halt = True

    def can_trade(self, ts: pd.Timestamp, equity: float, state: CircuitBreakerState) -> bool:
        self.reset_periods(ts, equity, state)
        if state.weekly_halt:
            return False
        if state.paused_until and ts < state.paused_until:
            return False
        return True
