from __future__ import annotations

import numpy as np
import pandas as pd


def ema(series: pd.Series, length: int) -> pd.Series:
    return series.ewm(span=length, adjust=False).mean()


def rsi(series: pd.Series, length: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / length, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / length, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def atr(df: pd.DataFrame, length: int = 14) -> pd.Series:
    prev_close = df["close"].shift(1)
    tr = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.ewm(alpha=1 / length, adjust=False).mean()


def adx(df: pd.DataFrame, length: int = 14) -> pd.Series:
    up_move = df["high"].diff()
    down_move = -df["low"].diff()
    plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
    minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0.0)
    tr = atr(df, 1)
    plus_di = 100 * (plus_dm.ewm(alpha=1 / length, adjust=False).mean() / tr.replace(0, np.nan))
    minus_di = 100 * (minus_dm.ewm(alpha=1 / length, adjust=False).mean() / tr.replace(0, np.nan))
    dx = ((plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)) * 100
    return dx.ewm(alpha=1 / length, adjust=False).mean()


def macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> tuple[pd.Series, pd.Series, pd.Series]:
    fast_ema = ema(series, fast)
    slow_ema = ema(series, slow)
    line = fast_ema - slow_ema
    signal_line = ema(line, signal)
    hist = line - signal_line
    return line, signal_line, hist


def stoch_rsi(series: pd.Series, length: int = 14, k: int = 3, d: int = 3) -> tuple[pd.Series, pd.Series]:
    base_rsi = rsi(series, length)
    lowest = base_rsi.rolling(length).min()
    highest = base_rsi.rolling(length).max()
    stoch = (base_rsi - lowest) / (highest - lowest).replace(0, np.nan)
    k_line = stoch.rolling(k).mean() * 100
    d_line = k_line.rolling(d).mean()
    return k_line, d_line


def bollinger_bands(series: pd.Series, length: int = 20, num_std: float = 2.0) -> tuple[pd.Series, pd.Series, pd.Series]:
    mid = series.rolling(length).mean()
    std = series.rolling(length).std(ddof=0)
    upper = mid + num_std * std
    lower = mid - num_std * std
    return lower, mid, upper


def session_vwap(df: pd.DataFrame) -> pd.Series:
    typical = (df["high"] + df["low"] + df["close"]) / 3.0
    session = pd.Series(df.index.date, index=df.index)
    cum_pv = (typical * df["volume"]).groupby(session).cumsum()
    cum_vol = df["volume"].groupby(session).cumsum()
    return cum_pv / cum_vol.replace(0, np.nan)


def obv(df: pd.DataFrame) -> pd.Series:
    direction = np.sign(df["close"].diff().fillna(0))
    return (direction * df["volume"]).cumsum()


def volume_zscore(series: pd.Series, length: int = 50) -> pd.Series:
    mean = series.rolling(length).mean()
    std = series.rolling(length).std(ddof=0)
    return (series - mean) / std.replace(0, np.nan)


def fractal_swings(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    highs = df["high"]
    lows = df["low"]
    swing_high = (
        (highs.shift(2) < highs)
        & (highs.shift(1) < highs)
        & (highs.shift(-1) < highs)
        & (highs.shift(-2) < highs)
    )
    swing_low = (
        (lows.shift(2) > lows)
        & (lows.shift(1) > lows)
        & (lows.shift(-1) > lows)
        & (lows.shift(-2) > lows)
    )
    return highs.where(swing_high), lows.where(swing_low)


def compute_indicator_frame(df: pd.DataFrame, *, include_intraday: bool = True) -> pd.DataFrame:
    enriched = df.copy()
    enriched["ema_21"] = ema(enriched["close"], 21)
    enriched["ema_55"] = ema(enriched["close"], 55)
    enriched["ema_200"] = ema(enriched["close"], 200)
    enriched["adx_14"] = adx(enriched, 14)
    enriched["rsi_14"] = rsi(enriched["close"], 14)
    macd_line, macd_signal, macd_hist = macd(enriched["close"])
    enriched["macd_line"] = macd_line
    enriched["macd_signal"] = macd_signal
    enriched["macd_hist"] = macd_hist
    stoch_k, stoch_d = stoch_rsi(enriched["close"])
    enriched["stochrsi_k"] = stoch_k
    enriched["stochrsi_d"] = stoch_d
    enriched["atr_14"] = atr(enriched, 14)
    enriched["atr_100_mean"] = enriched["atr_14"].rolling(100).mean()
    bb_low, bb_mid, bb_high = bollinger_bands(enriched["close"], 20, 2.0)
    enriched["bb_low"] = bb_low
    enriched["bb_mid"] = bb_mid
    enriched["bb_high"] = bb_high
    enriched["vwap"] = session_vwap(enriched) if include_intraday else np.nan
    enriched["obv"] = obv(enriched)
    enriched["obv_slope"] = enriched["obv"].diff(5)
    enriched["volume_zscore"] = volume_zscore(enriched["volume"], 50)
    swing_high, swing_low = fractal_swings(enriched)
    enriched["swing_high"] = swing_high
    enriched["swing_low"] = swing_low
    return enriched
