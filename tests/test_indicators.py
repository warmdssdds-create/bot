from __future__ import annotations

import pandas as pd

from src.indicators.compute import bollinger_bands, ema, rsi


def test_ema_matches_hand_computed_values() -> None:
    series = pd.Series([1.0, 2.0, 3.0, 4.0])
    result = ema(series, 3).round(4).tolist()
    assert result == [1.0, 1.5, 2.25, 3.125]


def test_rsi_recovers_on_rising_series() -> None:
    series = pd.Series([1, 2, 1, 2, 3, 4, 5, 6, 7, 8], dtype=float)
    assert rsi(series, 3).iloc[-1] > 70


def test_bollinger_band_midline_is_mean() -> None:
    series = pd.Series([1, 2, 3, 4, 5], dtype=float)
    _, mid, _ = bollinger_bands(series, 5, 2)
    assert mid.iloc[-1] == 3.0
