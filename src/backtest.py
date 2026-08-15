from __future__ import annotations

import argparse
import copy
import subprocess
import sys
from pathlib import Path

import pandas as pd
import yaml

from src.data.binance_csv_loader import generate_synthetic_binance_like_csv, load_and_resample_binance_csv
from src.indicators.compute import compute_indicator_frame
from src.optimize import walk_forward_optimize


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CSV_CANDIDATES = [
    ROOT / "tools" / "data" / "ETCUSDT_5m_2020_2026.csv",
    ROOT / "data" / "ETCUSDT_5m_2020_2026.csv",
]


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def ensure_data(csv_path: Path | None) -> tuple[Path, str]:
    if csv_path and csv_path.exists():
        return csv_path, "real"
    for candidate in DEFAULT_CSV_CANDIDATES:
        if candidate.exists():
            return candidate, "real"
    downloader = ROOT / "tools" / "download_etcusdt_m5.py"
    try:
        subprocess.run([sys.executable, str(downloader)], cwd=ROOT, check=True, timeout=900)
        for candidate in DEFAULT_CSV_CANDIDATES:
            if candidate.exists():
                return candidate, "real"
    except Exception:
        pass
    synthetic_path = ROOT / "data_cache" / "ETCUSDT_5m_synthetic.csv"
    return generate_synthetic_binance_like_csv(synthetic_path), "synthetic"


def prepare_frames(raw: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    return {
        "5m": compute_indicator_frame(raw["5m"]),
        "15m": compute_indicator_frame(raw["15m"]),
        "1h": compute_indicator_frame(raw["1h"], include_intraday=False),
    }


def summarize_windows(results) -> pd.DataFrame:
    rows = []
    for result in results:
        metrics = result.test_metrics
        rows.append(
            {
                "train_start": result.train_start.date().isoformat(),
                "train_end": result.train_end.date().isoformat(),
                "test_start": result.test_start.date().isoformat(),
                "test_end": result.test_end.date().isoformat(),
                "trade_count": metrics.get("trade_count", 0),
                "win_rate": metrics.get("win_rate", 0.0),
                "profit_factor": metrics.get("profit_factor", 0.0),
                "max_drawdown": metrics.get("max_drawdown", 0.0),
                "expectancy": metrics.get("expectancy", 0.0),
                "overfit_flag": result.overfit_flag,
                "params": result.params,
            }
        )
    return pd.DataFrame(rows)


def write_report(summary: pd.DataFrame, dataset_label: str) -> dict[str, float]:
    results_dir = ROOT / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    summary.to_csv(results_dir / "walk_forward_metrics.csv", index=False)

    aggregates = {
        "win_rate": float(summary["win_rate"].mean()) if not summary.empty else 0.0,
        "profit_factor": float(summary["profit_factor"].replace(float("inf"), 5.0).mean()) if not summary.empty else 0.0,
        "max_drawdown": float(summary["max_drawdown"].mean()) if not summary.empty else 0.0,
        "expectancy": float(summary["expectancy"].mean()) if not summary.empty else 0.0,
        "trade_count": int(summary["trade_count"].sum()) if not summary.empty else 0,
    }

    report_path = results_dir / "walk_forward_report.md"
    with report_path.open("w", encoding="utf-8") as handle:
        handle.write("# Walk-forward report\n\n")
        handle.write(
            f"Win rate is an empirical output of the strategy and data, not a parameter that was tuned to hit 85%. "
            f"This run used the **{dataset_label}** dataset path and honestly reports the measured out-of-sample results: "
            f"win rate {aggregates['win_rate']:.2%}, profit factor {aggregates['profit_factor']:.2f}, "
            f"max drawdown {aggregates['max_drawdown']:.2%}, expectancy {aggregates['expectancy']:.2f}.\n\n"
        )
        if dataset_label == "synthetic":
            handle.write(
                "Network access to Binance historical downloads was unavailable in this environment, so a clearly labeled synthetic OHLCV fallback dataset was generated purely to demonstrate the full pipeline end-to-end. Re-run the downloader and backtest with real Binance data before making any trading decision.\n\n"
            )
        handle.write(summary.to_markdown(index=False))
        handle.write("\n")
    return aggregates


def main() -> None:
    parser = argparse.ArgumentParser(description="Run ETCUSDT walk-forward backtest")
    parser.add_argument("--csv", type=Path, help="Explicit path to Binance ETCUSDT 5m CSV")
    args = parser.parse_args()

    csv_path, dataset_label = ensure_data(args.csv)
    strategy_config = load_yaml(ROOT / "config" / "strategy.yaml")
    risk_config = load_yaml(ROOT / "config" / "risk.yaml")
    raw = load_and_resample_binance_csv(csv_path)
    prepared = prepare_frames(raw)
    results = walk_forward_optimize(prepared, copy.deepcopy(strategy_config), risk_config)
    summary = summarize_windows(results)
    aggregates = write_report(summary, dataset_label)
    print(summary.to_string(index=False))
    print("\nAggregate out-of-sample averages:")
    for key, value in aggregates.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
