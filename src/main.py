from __future__ import annotations

import argparse
import time
from pathlib import Path

import yaml

from src.exchange.bybit_rest import BybitRESTClient
from src.exchange.bybit_ws import BybitWebSocketClient
from src.monitoring.alerts import TelegramAlertClient
from src.monitoring.logger import configure_logging, get_logger


ROOT = Path(__file__).resolve().parent.parent


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run ETCUSDT live bot")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--testnet", action="store_true")
    group.add_argument("--mainnet", action="store_true")
    args = parser.parse_args()

    configure_logging(ROOT / "config" / "logging.yaml")
    logger = get_logger("main")
    strategy_config = load_yaml(ROOT / "config" / "strategy.yaml")
    risk_config = load_yaml(ROOT / "config" / "risk.yaml")
    testnet = not args.mainnet

    rest = BybitRESTClient(testnet=testnet)
    ws = BybitWebSocketClient(testnet=testnet)
    alerts = TelegramAlertClient()
    logger.info("Starting ETCUSDT bot on %s", "testnet" if testnet else "mainnet")
    logger.info("Loaded strategy config: %s", strategy_config["symbol"])
    logger.info("Loaded risk config: risk_per_trade=%s", risk_config["risk_per_trade"])

    def on_kline(message: dict) -> None:
        logger.info("Received kline update: %s", message)

    def on_position(message: dict) -> None:
        logger.info("Received position update: %s", message)

    try:
        ws.subscribe_kline("15", on_kline)
        ws.subscribe_position(on_position)
        last_reconcile = time.time()
        while True:
            if time.time() - last_reconcile >= 300:
                logger.info("Reconciling positions via REST")
                rest.get_positions()
                last_reconcile = time.time()
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Graceful shutdown requested; exchange-side protective orders remain intact")
        alerts.send("ETCUSDT bot shutting down gracefully")
    finally:
        ws.close()


if __name__ == "__main__":
    main()
