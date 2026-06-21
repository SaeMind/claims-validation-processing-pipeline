"""Structured JSON logging helpers."""

import json
import logging
from datetime import datetime, timezone
from typing import Any


class JsonFormatter(logging.Formatter):
    """Format log records as JSON for Cloud Logging ingestion."""

    def format(self, record: logging.LogRecord) -> str:
        """Convert a log record into a JSON string."""
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "severity": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "context"):
            payload["context"] = record.context
        return json.dumps(payload, default=str)


def configure_logging(level: str = "INFO") -> None:
    """
    Configure root logging with JSON output.

    Parameters:
        level: Logging level name.

    Returns:
        None.
    """
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())
