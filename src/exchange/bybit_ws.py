from __future__ import annotations

import os
from collections.abc import Callable

from dotenv import load_dotenv
from pybit.unified_trading import WebSocket


class BybitWebSocketClient:
    def __init__(self, testnet: bool = True, channel_type: str = "linear") -> None:
        load_dotenv()
        self.symbol = os.getenv("BYBIT_SYMBOL", "ETCUSDT")
        self.ws = WebSocket(
            testnet=testnet,
            channel_type=channel_type,
            api_key=os.getenv("BYBIT_API_KEY"),
            api_secret=os.getenv("BYBIT_API_SECRET"),
        )

    def subscribe_kline(self, interval: str, callback: Callable[[dict], None]) -> None:
        self.ws.kline_stream(interval=interval, symbol=self.symbol, callback=callback)

    def subscribe_position(self, callback: Callable[[dict], None]) -> None:
        self.ws.position_stream(callback=callback)

    def close(self) -> None:
        self.ws.exit()
