from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class RegimeThresholds:
    trending_adx_min: float = 22.0
    ranging_adx_max: float = 18.0
    atr_ranging_multiplier: float = 1.5
    atr_spike_multiplier: float = 2.5


def ema_ribbon_stacked(row: pd.Series) -> int:
    if row["ema_21"] > row["ema_55"] > row["ema_200"]:
        return 1
    if row["ema_21"] < row["ema_55"] < row["ema_200"]:
        return -1
    return 0


def classify_regime(row: pd.Series, thresholds: RegimeThresholds) -> str:
    atr_avg = row.get("atr_100_mean")
    if pd.notna(atr_avg) and atr_avg > 0 and row["atr_14"] > thresholds.atr_spike_multiplier * atr_avg:
        return "VOLATILITY_SPIKE"
    if row["adx_14"] > thresholds.trending_adx_min and ema_ribbon_stacked(row) != 0:
        return "TRENDING"
    if (
        row["adx_14"] < thresholds.ranging_adx_max
        and pd.notna(atr_avg)
        and atr_avg > 0
        and row["atr_14"] < thresholds.atr_ranging_multiplier * atr_avg
    ):
        return "RANGING"
    if thresholds.ranging_adx_max <= row["adx_14"] <= thresholds.trending_adx_min:
        return "TRANSITIONAL"
    return "TRANSITIONAL"
