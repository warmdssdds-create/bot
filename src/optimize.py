from __future__ import annotations

import copy
from dataclasses import dataclass

import pandas as pd

from src.backtesting.event_engine import EventDrivenBacktester


@dataclass
class WalkForwardWindowResult:
    train_start: pd.Timestamp
    train_end: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp
    params: dict
    train_metrics: dict
    test_metrics: dict
    overfit_flag: bool


def _normalized(values: list[float]) -> list[float]:
    if not values:
        return []
    low, high = min(values), max(values)
    if high == low:
        return [1.0 for _ in values]
    return [(value - low) / (high - low) for value in values]


def _objective(metrics: dict, pf_range: tuple[float, float], wr_range: tuple[float, float], dd_range: tuple[float, float]) -> float:
    pf = 1.0 if pf_range[1] == pf_range[0] else (metrics["profit_factor"] - pf_range[0]) / (pf_range[1] - pf_range[0])
    wr = 1.0 if wr_range[1] == wr_range[0] else (metrics["win_rate"] - wr_range[0]) / (wr_range[1] - wr_range[0])
    dd = 1.0 if dd_range[1] == dd_range[0] else (metrics["max_drawdown"] - dd_range[0]) / (dd_range[1] - dd_range[0])
    return 0.4 * pf + 0.3 * wr + 0.3 * (1 - dd)


def walk_forward_optimize(data: dict[str, pd.DataFrame], strategy_config: dict, risk_config: dict) -> list[WalkForwardWindowResult]:
    index = data["15m"].index
    start = index.min().normalize()
    end = index.max().normalize()
    results: list[WalkForwardWindowResult] = []

    train_months = 6
    test_months = 2
    cursor = start
    grid = {
        "trending_adx_min": [20, 22, 24, 26],
        "ranging_adx_max": [16, 18, 20],
        "atr_spike_multiplier": [2.2, 2.5, 2.8, 3.0],
        "threshold": [0.55, 0.60, 0.65, 0.70, 0.75],
    }

    while cursor + pd.DateOffset(months=train_months + test_months) <= end:
        train_start = cursor
        train_end = cursor + pd.DateOffset(months=train_months)
        test_end = train_end + pd.DateOffset(months=test_months)
        train = {tf: frame.loc[(frame.index >= train_start) & (frame.index < train_end)] for tf, frame in data.items()}
        test = {tf: frame.loc[(frame.index >= train_end) & (frame.index < test_end)] for tf, frame in data.items()}

        candidates: list[tuple[dict, dict, dict, bool]] = []
        for trending_adx_min in grid["trending_adx_min"]:
            for ranging_adx_max in grid["ranging_adx_max"]:
                if ranging_adx_max >= trending_adx_min:
                    continue
                for atr_spike_multiplier in grid["atr_spike_multiplier"]:
                    for threshold in grid["threshold"]:
                        candidate = copy.deepcopy(strategy_config)
                        candidate["regime"]["trending_adx_min"] = trending_adx_min
                        candidate["regime"]["ranging_adx_max"] = ranging_adx_max
                        candidate["regime"]["atr_spike_multiplier"] = atr_spike_multiplier
                        candidate["confluence"]["threshold"] = threshold
                        train_result = EventDrivenBacktester(candidate, risk_config).run(train)
                        train_metrics = train_result["metrics"]
                        if train_metrics["trade_count"] < 30:
                            continue
                        test_result = EventDrivenBacktester(candidate, risk_config).run(test)
                        test_metrics = test_result["metrics"]
                        overfit_flag = (train_metrics["win_rate"] - test_metrics["win_rate"]) > 0.15
                        candidates.append((candidate, train_metrics, test_metrics, overfit_flag))

        if candidates:
            pf_values = [candidate[1]["profit_factor"] if candidate[1]["profit_factor"] != float("inf") else 5.0 for candidate in candidates]
            wr_values = [candidate[1]["win_rate"] for candidate in candidates]
            dd_values = [candidate[1]["max_drawdown"] for candidate in candidates]
            pf_range = (min(pf_values), max(pf_values))
            wr_range = (min(wr_values), max(wr_values))
            dd_range = (min(dd_values), max(dd_values))

            scored: list[tuple[float, dict, dict, dict, bool]] = []
            for candidate, train_metrics, test_metrics, overfit_flag in candidates:
                score = _objective(train_metrics, pf_range, wr_range, dd_range)
                scored.append((score, candidate, train_metrics, test_metrics, overfit_flag))
            scored.sort(key=lambda item: item[0], reverse=True)

            selected = next((row for row in scored if not row[4]), scored[0])
            _, params, train_metrics, test_metrics, overfit_flag = selected
        else:
            params = {}
            train_metrics = {}
            test_metrics = {"trade_count": 0, "win_rate": 0.0, "profit_factor": 0.0, "max_drawdown": 0.0, "expectancy": 0.0}
            overfit_flag = True

        results.append(
            WalkForwardWindowResult(
                train_start=train_start,
                train_end=train_end,
                test_start=train_end,
                test_end=test_end,
                params=params,
                train_metrics=train_metrics,
                test_metrics=test_metrics,
                overfit_flag=overfit_flag,
            )
        )
        cursor = cursor + pd.DateOffset(months=test_months)

    return results
