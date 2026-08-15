#!/usr/bin/env python3
"""
Download Binance ETCUSDT 5-minute historical candles for 2020-01-01 through
the current date, then merge them into one CSV.

Source:
  https://data.binance.vision/data/spot/monthly/klines/ETCUSDT/5m/

Output:
  data/ETCUSDT_5m_2020_2026.csv
"""

from __future__ import annotations

import csv
import io
import zipfile
from datetime import date
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE = "https://data.binance.vision/data/spot/monthly/klines/ETCUSDT/5m"
START_YEAR, START_MONTH = 2020, 1
END_YEAR, END_MONTH = date.today().year, date.today().month

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
RAW_DIR = ROOT / "raw_monthly"
OUT = DATA_DIR / "ETCUSDT_5m_2020_2026.csv"
DATA_DIR.mkdir(exist_ok=True)
RAW_DIR.mkdir(exist_ok=True)

HEADER = [
    "open_time", "open", "high", "low", "close", "volume",
    "close_time", "quote_volume", "trades",
    "taker_buy_base_volume", "taker_buy_quote_volume", "ignore"
]

def months():
    y, m = START_YEAR, START_MONTH
    while (y, m) <= (END_YEAR, END_MONTH):
        yield y, m
        m += 1
        if m == 13:
            y += 1
            m = 1

def download(url: str) -> bytes:
    req = Request(url, headers={"User-Agent": "ETCUSDT-M5-Historical-Downloader/1.0"})
    with urlopen(req, timeout=60) as r:
        return r.read()

def extract_csv(zdata: bytes) -> list[list[str]]:
    with zipfile.ZipFile(io.BytesIO(zdata)) as z:
        names = [n for n in z.namelist() if n.lower().endswith(".csv")]
        if not names:
            raise RuntimeError("ZIP did not contain a CSV file")
        with z.open(names[0]) as f:
            text = io.TextIOWrapper(f, encoding="utf-8", newline="")
            rows = []
            for row in csv.reader(text):
                if not row:
                    continue
                if row[0].lower() in {"open_time", "open time"}:
                    continue
                if len(row) >= 12:
                    rows.append(row[:12])
            return rows

def main():
    total = 0
    missing = []
    temp = ROOT / "ETCUSDT_5m_merged.tmp.csv"

    with temp.open("w", newline="", encoding="utf-8") as out:
        writer = csv.writer(out)
        writer.writerow(HEADER)

        for y, m in months():
            ym = f"{y:04d}-{m:02d}"
            filename = f"ETCUSDT-5m-{ym}.zip"
            url = f"{BASE}/{filename}"
            raw_file = RAW_DIR / filename

            try:
                if raw_file.exists():
                    data = raw_file.read_bytes()
                else:
                    print(f"Downloading {filename} ...")
                    data = download(url)
                    raw_file.write_bytes(data)

                rows = extract_csv(data)
                writer.writerows(rows)
                total += len(rows)
                print(f"  OK {ym}: {len(rows):,} candles")
            except HTTPError as e:
                if e.code == 404:
                    missing.append(ym)
                    print(f"  MISSING {ym} (404)")
                    continue
                raise
            except (URLError, OSError, zipfile.BadZipFile) as e:
                print(f"  ERROR {ym}: {e}")
                raise

    import csv as _csv

    rows = []
    with temp.open("r", newline="", encoding="utf-8") as f:
        for r in _csv.DictReader(f):
            rows.append(r)

    rows.sort(key=lambda r: int(r["open_time"]))
    deduped = []
    last = None
    for r in rows:
        key = r["open_time"]
        if key != last:
            deduped.append(r)
            last = key

    with OUT.open("w", newline="", encoding="utf-8") as f:
        writer = _csv.DictWriter(f, fieldnames=HEADER)
        writer.writeheader()
        writer.writerows(deduped)

    temp.unlink(missing_ok=True)

    print()
    print(f"Finished: {len(deduped):,} unique candles")
    print(f"Output:   {OUT}")
    if missing:
        print("Missing months:", ", ".join(missing))

if __name__ == "__main__":
    main()
