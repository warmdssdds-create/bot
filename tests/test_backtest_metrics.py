from __future__ import annotations

import pandas as pd

from src.backtesting.metrics import compute_metrics


def test_backtest_metrics_compute_expected_values() -> None:
    trades = [
        {"net_pnl": 10.0, "regime": "TRENDING"},
        {"net_pnl": -5.0, "regime": "TRENDING"},
        {"net_pnl": 20.0, "regime": "RANGING"},
    ]
    equity_curve = pd.Series([100, 110, 105, 125], index=pd.date_range("2024-01-01", periods=4, freq="15min", tz="UTC"))
    metrics = compute_metrics(trades, equity_curve)
    assert metrics["trade_count"] == 3
    assert round(metrics["win_rate"], 4) == 0.6667
    assert metrics["profit_factor"] == 6.0
    assert metrics["longest_losing_streak"] == 1
