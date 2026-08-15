from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class TradeLevels:
    entry: float
    stop_loss: float
    take_profit: float
    risk_per_unit: float
    breakeven_trigger: float
    trailing_trigger: float


def calculate_trade_levels(
    side: str,
    entry: float,
    atr_value: float,
    nearest_swing: float | None,
    atr_stop_multiplier: float,
    structure_buffer_atr: float,
    reward_risk_ratio: float,
) -> TradeLevels:
    atr_stop_distance = atr_value * atr_stop_multiplier
    if side == "buy":
        atr_stop = entry - atr_stop_distance
        structure_stop = (
            nearest_swing - atr_value * structure_buffer_atr if nearest_swing is not None else atr_stop
        )
        stop_loss = max(atr_stop, structure_stop)
        risk_per_unit = entry - stop_loss
        take_profit = entry + risk_per_unit * reward_risk_ratio
    else:
        atr_stop = entry + atr_stop_distance
        structure_stop = (
            nearest_swing + atr_value * structure_buffer_atr if nearest_swing is not None else atr_stop
        )
        stop_loss = min(atr_stop, structure_stop)
        risk_per_unit = stop_loss - entry
        take_profit = entry - risk_per_unit * reward_risk_ratio

    return TradeLevels(
        entry=entry,
        stop_loss=stop_loss,
        take_profit=take_profit,
        risk_per_unit=risk_per_unit,
        breakeven_trigger=entry + risk_per_unit * 0.5 if side == "buy" else entry - risk_per_unit * 0.5,
        trailing_trigger=entry + risk_per_unit if side == "buy" else entry - risk_per_unit,
    )


def position_size_from_risk(
    equity: float,
    risk_per_trade: float,
    entry: float,
    stop_loss: float,
    max_leverage: float,
) -> float:
    risk_budget = equity * risk_per_trade
    stop_distance = abs(entry - stop_loss)
    if stop_distance <= 0:
        return 0.0
    raw_size = risk_budget / stop_distance
    leverage_cap_size = (equity * max_leverage) / entry
    return max(0.0, min(raw_size, leverage_cap_size))
