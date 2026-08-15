from __future__ import annotations

import logging
import logging.config
from pathlib import Path

import yaml


def configure_logging(config_path: str | Path) -> None:
    path = Path(config_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    for handler in config.get("handlers", {}).values():
        filename = handler.get("filename")
        if filename:
            Path(filename).parent.mkdir(parents=True, exist_ok=True)
    logging.config.dictConfig(config)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
