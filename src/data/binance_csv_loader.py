from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


REQUIRED_COLUMNS = [
    "open_time",
    "open",
    "high",
    "low",
    "close",
    "volume",
]


def _validate(df: pd.DataFrame) -> pd.DataFrame:
    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f"missing required columns: {missing}")
    if df[REQUIRED_COLUMNS].isna().any().any():
        raise ValueError("input CSV contains NaN values in required columns")

    numeric_columns = ["open", "high", "low", "close", "volume"]
    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="raise")

    open_time = pd.to_numeric(df["open_time"], errors="raise").astype("int64")
    if not open_time.is_monotonic_increasing:
        raise ValueError("open_time must be monotonic increasing")

    bad = (
        (df["high"] < df["low"])
        | (df["high"] < df["open"])
        | (df["high"] < df["close"])
        | (df["low"] > df["open"])
        | (df["low"] > df["close"])
    )
    if bad.any():
        raise ValueError("invalid candle structure detected")

    out = df.copy()
    out["timestamp"] = pd.to_datetime(open_time, unit="ms", utc=True)
    out = out.drop_duplicates(subset=["timestamp"]).set_index("timestamp").sort_index()
    if not out.index.is_monotonic_increasing:
        raise ValueError("timestamps must remain monotonic after cleaning")
    return out[["open", "high", "low", "close", "volume"]]


def _resample(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    resampled = df.resample(rule, label="right", closed="right").agg(
        {
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum",
        }
    )
    return resampled.dropna()


def load_and_resample_binance_csv(path: str | Path) -> dict[str, pd.DataFrame]:
    csv_path = Path(path)
    df = pd.read_csv(csv_path)
    validated = _validate(df)
    return {
        "5m": validated,
        "15m": _resample(validated, "15min"),
        "1h": _resample(validated, "1h"),
    }


def generate_synthetic_binance_like_csv(path: str | Path, start: str = "2020-01-01", end: str = "2026-08-01") -> Path:
    timestamps = pd.date_range(start=start, end=end, freq="5min", tz="UTC")
    if len(timestamps) < 10:
        raise ValueError("synthetic date range too small")
    rng = np.random.default_rng(42)
    drift = 0.00002
    volatility = 0.004
    jumps = rng.choice([0.0, 1.0], size=len(timestamps), p=[0.995, 0.005]) * rng.normal(0, 0.02, len(timestamps))
    regime_vol = 1.0 + 0.5 * np.sin(np.linspace(0, 30, len(timestamps)))
    returns = drift + rng.normal(0, volatility, len(timestamps)) * regime_vol + jumps
    close = 6.0 * np.exp(np.cumsum(returns))
    open_ = np.r_[close[0], close[:-1]]
    spread = np.abs(rng.normal(0.002, 0.001, len(timestamps)))
    high = np.maximum(open_, close) * (1 + spread)
    low = np.minimum(open_, close) * np.maximum(1 - spread, 0.0001)
    volume = np.abs(rng.normal(15000, 5000, len(timestamps))) * (1 + np.abs(returns) * 150)

    out = pd.DataFrame(
        {
            "open_time": (timestamps.view("int64") // 10**6).astype("int64"),
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
            "close_time": (timestamps.view("int64") // 10**6 + 299999).astype("int64"),
            "quote_volume": volume * close,
            "trades": rng.integers(50, 500, len(timestamps)),
            "taker_buy_base_volume": volume * rng.uniform(0.35, 0.65, len(timestamps)),
            "taker_buy_quote_volume": volume * close * rng.uniform(0.35, 0.65, len(timestamps)),
            "ignore": 0,
        }
    )
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(output, index=False)
    return output
