from __future__ import annotations

import math

import numpy as np
import pandas as pd


def max_drawdown(equity_curve: pd.Series) -> float:
    running_max = equity_curve.cummax()
    drawdown = (equity_curve - running_max) / running_max.replace(0, np.nan)
    return float(drawdown.min()) if not drawdown.empty else 0.0


def longest_losing_streak(pnls: list[float]) -> int:
    best = streak = 0
    for pnl in pnls:
        if pnl < 0:
            streak += 1
            best = max(best, streak)
        else:
            streak = 0
    return best


def compute_metrics(trades: list[dict], equity_curve: pd.Series) -> dict[str, float | int | dict[str, float]]:
    if not trades:
        return {
            "trade_count": 0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "average_win": 0.0,
            "average_loss": 0.0,
            "payoff_ratio": 0.0,
            "expectancy": 0.0,
            "max_drawdown": 0.0,
            "sharpe": 0.0,
            "sortino": 0.0,
            "recovery_factor": 0.0,
            "longest_losing_streak": 0,
            "regime_win_rate": {},
        }

    pnls = np.array([trade["net_pnl"] for trade in trades], dtype=float)
    wins = pnls[pnls > 0]
    losses = pnls[pnls < 0]
    win_rate = len(wins) / len(pnls)
    gross_profit = wins.sum()
    gross_loss = abs(losses.sum())
    average_win = float(wins.mean()) if len(wins) else 0.0
    average_loss = float(losses.mean()) if len(losses) else 0.0
    payoff_ratio = abs(average_win / average_loss) if average_loss else 0.0
    expectancy = float(pnls.mean())
    drawdown = abs(max_drawdown(equity_curve))
    returns = equity_curve.pct_change().dropna()
    sharpe = float((returns.mean() / returns.std(ddof=0)) * math.sqrt(252 * 24 * 4)) if len(returns) and returns.std(ddof=0) else 0.0
    downside = returns[returns < 0]
    sortino = float((returns.mean() / downside.std(ddof=0)) * math.sqrt(252 * 24 * 4)) if len(downside) and downside.std(ddof=0) else 0.0
    recovery_factor = float(pnls.sum() / drawdown) if drawdown else 0.0

    regime_win_rate: dict[str, float] = {}
    regime_groups: dict[str, list[float]] = {}
    for trade in trades:
        regime_groups.setdefault(trade["regime"], []).append(trade["net_pnl"])
    for regime, values in regime_groups.items():
        values_arr = np.array(values)
        regime_win_rate[regime] = float((values_arr > 0).mean())

    return {
        "trade_count": int(len(pnls)),
        "win_rate": float(win_rate),
        "profit_factor": float(gross_profit / gross_loss) if gross_loss else float("inf") if gross_profit > 0 else 0.0,
        "average_win": average_win,
        "average_loss": average_loss,
        "payoff_ratio": float(payoff_ratio),
        "expectancy": expectancy,
        "max_drawdown": float(drawdown),
        "sharpe": sharpe,
        "sortino": sortino,
        "recovery_factor": recovery_factor,
        "longest_losing_streak": longest_losing_streak(pnls.tolist()),
        "regime_win_rate": regime_win_rate,
    }
