from __future__ import annotations

from collections.abc import Mapping


TRENDING_KEYS = (
    "ema_ribbon",
    "macd_cross",
    "rsi_recovery",
    "vwap_position",
    "volume_confirmation",
    "obv_divergence",
    "stochrsi_trigger",
    "structure_reaction",
)
RANGING_KEYS = (
    "bb_touch",
    "rsi_recovery",
    "stochrsi_trigger",
    "volume_confirmation",
    "structure_reaction",
    "trend_not_against",
)


def weighted_score(votes: Mapping[str, int], weights: Mapping[str, float]) -> float:
    return float(sum(votes.get(key, 0) * weights.get(key, 0.0) for key in weights))
