from __future__ import annotations

import hashlib


def make_order_link_id(timestamp: str, symbol: str, side: str) -> str:
    payload = f"{timestamp}|{symbol}|{side}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:32]
