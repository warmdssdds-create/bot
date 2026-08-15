from __future__ import annotations

from pathlib import Path

import pandas as pd


def save_csv(df: pd.DataFrame, path: str | Path) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output, index=True)


def load_csv(path: str | Path) -> pd.DataFrame:
    return pd.read_csv(path, index_col=0, parse_dates=True)
