# ETCUSD Bybit trading bot

This repository contains a complete Python trading bot project for ETCUSDT perpetual futures on Bybit, including live-trading modules, a shared signal/risk stack, a no-lookahead event-driven backtester, and a walk-forward optimizer.

> **Important:** win rate is an empirical output of the strategy and dataset, not a target parameter. This project does **not** tune until it reaches 85%. It uses walk-forward optimization with out-of-sample reporting and an overfitting guard. After running the included pipeline in this task, the measured performance written below is the honest result from that run and must be re-validated on fresh data before any live use.

Measured run summary from this task: _pending execution_. See `/home/runner/work/bot/bot/results/walk_forward_report.md` for the generated report with the actual win rate, profit factor, drawdown, and expectancy from the completed run.

## Disclaimer

- No fixed win rate is guaranteed.
- Leveraged perpetual futures trading can lose substantial capital.
- Run on Bybit testnet first and validate results on fresh data before mainnet deployment.
- This software is educational infrastructure, not financial advice.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Fill `.env` with your Bybit credentials.

## Download real Binance data

The downloader script is provided verbatim:

```bash
python /home/runner/work/bot/bot/tools/download_etcusdt_m5.py
```

If network access to `data.binance.vision` is unavailable, the backtest CLI can generate a clearly labeled synthetic fallback dataset so the full pipeline still runs end-to-end.

## Run the walk-forward backtest

```bash
python -m src.backtest
```

Optional explicit CSV path:

```bash
python -m src.backtest --csv /home/runner/work/bot/bot/tools/data/ETCUSDT_5m_2020_2026.csv
```

Outputs:

- `/home/runner/work/bot/bot/results/walk_forward_report.md`
- `/home/runner/work/bot/bot/results/walk_forward_metrics.csv`

## Live trading

Testnet:

```bash
python -m src.main --testnet
```

Mainnet:

```bash
python -m src.main --mainnet
```

The live runner evaluates the strategy on confirmed 15m candles, reconciles exchange positions every 5 minutes, uses market orders with attached stop-loss/take-profit, and leaves exchange-side protective orders intact on graceful shutdown.

## Tests

```bash
pytest tests
```
