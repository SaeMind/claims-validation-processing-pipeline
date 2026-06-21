"""Shared utility functions."""

import base64
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def decode_pubsub_message(cloud_event_data: dict[str, Any]) -> dict[str, Any]:
    """
    Decode a Pub/Sub CloudEvent payload into a JSON dictionary.

    Parameters:
        cloud_event_data: CloudEvent data payload.

    Returns:
        Parsed JSON message body.
    """
    raw = cloud_event_data["message"]["data"]
    decoded = base64.b64decode(raw).decode("utf-8")
    parsed: dict[str, Any] = json.loads(decoded)
    return parsed


def timestamped_output_path(output_dir: Path, prefix: str, suffix: str = ".json") -> Path:
    """
    Create a timestamped output file path.

    Parameters:
        output_dir: Output directory.
        prefix: Filename prefix.
        suffix: Filename suffix.

    Returns:
        Timestamped Path object.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    return output_dir / f"{prefix}_{stamp}{suffix}"
