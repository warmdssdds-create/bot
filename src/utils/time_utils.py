from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def ensure_utc_index(df: pd.DataFrame) -> pd.DataFrame:
    if df.index.tz is None:
        df = df.tz_localize("UTC")
    else:
        df = df.tz_convert("UTC")
    return df


def floor_timestamp(ts: pd.Timestamp, timeframe: str) -> pd.Timestamp:
    return pd.Timestamp(ts).floor(timeframe)


def month_starts(start: pd.Timestamp, end: pd.Timestamp, months: int) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    windows: list[tuple[pd.Timestamp, pd.Timestamp]] = []
    cursor = pd.Timestamp(start).normalize()
    end = pd.Timestamp(end).normalize()
    while cursor < end:
        window_end = cursor + pd.DateOffset(months=months)
        windows.append((cursor, window_end))
        cursor = window_end
    return windows
