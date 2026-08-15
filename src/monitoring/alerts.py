from __future__ import annotations

import logging
import os

import requests


class TelegramAlertClient:
    def __init__(self, token: str | None = None, chat_id: str | None = None) -> None:
        self.token = token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID")
        self.logger = logging.getLogger(self.__class__.__name__)

    def enabled(self) -> bool:
        return bool(self.token and self.chat_id)

    def send(self, message: str) -> bool:
        if not self.enabled():
            self.logger.info("Telegram alerts disabled: %s", message)
            return False
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        response = requests.post(url, json={"chat_id": self.chat_id, "text": message}, timeout=10)
        response.raise_for_status()
        return True
