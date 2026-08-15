from __future__ import annotations

import pandas as pd

from src.strategy.signals import evaluate_signal


def test_trending_signal_triggers_buy_when_votes_align() -> None:
    index = pd.date_range("2024-01-01", periods=4, freq="15min", tz="UTC")
    df_15m = pd.DataFrame(
        {
            "close": [100, 101, 102, 103],
            "ema_21": [99, 100, 101, 102],
            "ema_55": [98, 99, 100, 101],
            "ema_200": [97, 98, 99, 100],
            "macd_line": [0.1, 0.2, 0.1, 0.3],
            "macd_signal": [0.2, 0.2, 0.2, 0.2],
            "rsi_14": [25, 29, 35, 40],
            "vwap": [99, 100, 101, 102],
            "volume_zscore": [0.1, 0.2, 0.6, 0.8],
            "obv_slope": [1, 1, 2, 3],
            "bb_low": [95, 96, 97, 98],
            "bb_high": [105, 106, 107, 108],
            "swing_high": [None, None, 104, None],
            "swing_low": [None, 98, None, None],
        },
        index=index,
    )
    index_5m = pd.date_range("2024-01-01", periods=4, freq="5min", tz="UTC")
    df_5m = pd.DataFrame({"stochrsi_k": [10, 20, 15, 18], "stochrsi_d": [20, 18, 16, 17]}, index=index_5m)
    decision = evaluate_signal(
        "TRENDING",
        df_15m,
        df_5m,
        {
            "threshold": 0.65,
            "trending_weights": {
                "ema_ribbon": 0.20,
                "macd_cross": 0.15,
                "rsi_recovery": 0.10,
                "vwap_position": 0.10,
                "volume_confirmation": 0.10,
                "obv_divergence": 0.10,
                "stochrsi_trigger": 0.10,
                "structure_reaction": 0.15,
            },
            "ranging_weights": {},
        },
    )
    assert decision is not None
    assert decision.side == "buy"
