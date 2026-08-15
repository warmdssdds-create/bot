from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.data.binance_csv_loader import load_and_resample_binance_csv


def load_market_data(csv_path: str | Path) -> dict[str, pd.DataFrame]:
    return load_and_resample_binance_csv(csv_path)
