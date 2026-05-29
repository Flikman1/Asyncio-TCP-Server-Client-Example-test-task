"""Structured JSONL logging helpers."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any


class JsonLineFormatter(logging.Formatter):
    """Format log records as one JSON object per line."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now().isoformat(timespec="milliseconds"),
            "level": record.levelname.lower(),
            "logger": record.name,
        }

        event = getattr(record, "event", None)
        if event is not None:
            payload["event"] = event

        event_data = getattr(record, "event_data", None)
        if isinstance(event_data, dict):
            payload.update(event_data)

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False)


def configure_json_logger(name: str, log_path: str | Path) -> logging.Logger:
    """Create or return a JSONL logger bound to the given path."""

    resolved_path = Path(log_path)
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    logger_name = f"{name}:{resolved_path.resolve()}"
    logger = logging.getLogger(logger_name)

    if logger.handlers:
        return logger

    handler = logging.FileHandler(resolved_path, encoding="utf-8")
    handler.setFormatter(JsonLineFormatter())

    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    logger.propagate = False
    return logger


def log_event(logger: logging.Logger, event: str, **fields: Any) -> None:
    """Write a structured log event."""

    logger.info("", extra={"event": event, "event_data": fields})
