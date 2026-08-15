from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.strategy.confluence import weighted_score
from src.strategy.regime_filter import ema_ribbon_stacked


@dataclass(frozen=True)
class SignalDecision:
    side: str
    score: float
    regime: str
    votes: dict[str, int]


def _cross_signal(series_a: pd.Series, series_b: pd.Series) -> int:
    if len(series_a) < 2 or len(series_b) < 2:
        return 0
    prev_diff = series_a.iloc[-2] - series_b.iloc[-2]
    curr_diff = series_a.iloc[-1] - series_b.iloc[-1]
    if prev_diff <= 0 < curr_diff:
        return 1
    if prev_diff >= 0 > curr_diff:
        return -1
    return 0


def _rsi_recovery(series: pd.Series) -> int:
    if len(series) < 2:
        return 0
    prev_val = series.iloc[-2]
    curr_val = series.iloc[-1]
    if prev_val < 30 <= curr_val:
        return 1
    if prev_val > 70 >= curr_val:
        return -1
    return 0


def _stochrsi_trigger(k: pd.Series, d: pd.Series) -> int:
    cross = _cross_signal(k, d)
    if cross == 1 and k.iloc[-1] < 25:
        return 1
    if cross == -1 and k.iloc[-1] > 75:
        return -1
    return 0


def _structure_vote(price_row: pd.Series, reference: pd.DataFrame) -> int:
    recent_high = reference["swing_high"].dropna().tail(1)
    recent_low = reference["swing_low"].dropna().tail(1)
    if not recent_low.empty and price_row["close"] > recent_low.iloc[-1]:
        bull = 1
    else:
        bull = 0
    if not recent_high.empty and price_row["close"] < recent_high.iloc[-1]:
        bear = -1
    else:
        bear = 0
    return bull if abs(bull) >= abs(bear) else bear


def build_votes(
    regime: str,
    df_15m: pd.DataFrame,
    df_5m: pd.DataFrame,
    threshold_config: dict,
) -> dict[str, int]:
    current = df_15m.iloc[-1]
    votes: dict[str, int] = {}
    votes["ema_ribbon"] = ema_ribbon_stacked(current)
    votes["macd_cross"] = _cross_signal(df_15m["macd_line"], df_15m["macd_signal"])
    votes["rsi_recovery"] = _rsi_recovery(df_15m["rsi_14"])
    votes["vwap_position"] = 1 if current["close"] > current.get("vwap", current["close"]) else -1
    volume_cutoff = 0.5 if regime == "TRENDING" else 0.3
    votes["volume_confirmation"] = 1 if current["volume_zscore"] > volume_cutoff else 0
    votes["obv_divergence"] = 1 if current["obv_slope"] > 0 and current["close"] >= df_15m["close"].iloc[-2] else -1 if current["obv_slope"] < 0 and current["close"] <= df_15m["close"].iloc[-2] else 0
    votes["stochrsi_trigger"] = _stochrsi_trigger(df_5m["stochrsi_k"], df_5m["stochrsi_d"])
    votes["structure_reaction"] = _structure_vote(current, df_15m)
    votes["bb_touch"] = 1 if current["close"] <= current["bb_low"] else -1 if current["close"] >= current["bb_high"] else 0
    votes["trend_not_against"] = 0 if votes["ema_ribbon"] == 0 else votes["ema_ribbon"]
    return votes


def evaluate_signal(
    regime: str,
    df_15m: pd.DataFrame,
    df_5m: pd.DataFrame,
    confluence_config: dict,
) -> SignalDecision | None:
    if regime in {"TRANSITIONAL", "VOLATILITY_SPIKE"}:
        return None
    if len(df_15m) < 3 or len(df_5m) < 3:
        return None

    votes = build_votes(regime, df_15m, df_5m, confluence_config)
    weights = (
        confluence_config["trending_weights"]
        if regime == "TRENDING"
        else confluence_config["ranging_weights"]
    )
    score = weighted_score(votes, weights)
    threshold = confluence_config.get("threshold", 0.65)
    if abs(score) < threshold:
        return None
    return SignalDecision(side="buy" if score > 0 else "sell", score=score, regime=regime, votes=votes)
