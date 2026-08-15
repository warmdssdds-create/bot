from __future__ import annotations

import os

from dotenv import load_dotenv
from pybit.unified_trading import HTTP
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential


class BybitRESTClient:
    def __init__(self, testnet: bool = True) -> None:
        load_dotenv()
        self.symbol = os.getenv("BYBIT_SYMBOL", "ETCUSDT")
        self.client = HTTP(
            testnet=testnet,
            api_key=os.getenv("BYBIT_API_KEY"),
            api_secret=os.getenv("BYBIT_API_SECRET"),
        )

    @retry(wait=wait_exponential(min=1, max=8), stop=stop_after_attempt(3), retry=retry_if_exception_type(Exception))
    def get_ticker(self, symbol: str | None = None) -> dict:
        return self.client.get_tickers(category="linear", symbol=symbol or self.symbol)

    @retry(wait=wait_exponential(min=1, max=8), stop=stop_after_attempt(3), retry=retry_if_exception_type(Exception))
    def get_positions(self, symbol: str | None = None) -> dict:
        return self.client.get_positions(category="linear", symbol=symbol or self.symbol)

    @retry(wait=wait_exponential(min=1, max=8), stop=stop_after_attempt(3), retry=retry_if_exception_type(Exception))
    def place_market_order(
        self,
        *,
        side: str,
        qty: float,
        stop_loss: float,
        take_profit: float,
        order_link_id: str,
        symbol: str | None = None,
    ) -> dict:
        return self.client.place_order(
            category="linear",
            symbol=symbol or self.symbol,
            side="Buy" if side == "buy" else "Sell",
            orderType="Market",
            qty=str(qty),
            orderLinkId=order_link_id,
            stopLoss=str(stop_loss),
            takeProfit=str(take_profit),
            tpslMode="Full",
        )
