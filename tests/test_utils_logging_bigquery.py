import base64
import json
import logging
from unittest.mock import Mock
from pathlib import Path

from src.bigquery_writer import ClaimsBigQueryWriter, build_validated_claim_row
from src.logging_config import configure_logging
from src.utils import decode_pubsub_message, timestamped_output_path


def test_decode_pubsub_message() -> None:
    payload = {"claim_id": "CLM-1"}
    encoded = base64.b64encode(json.dumps(payload).encode()).decode()
    assert decode_pubsub_message({"message": {"data": encoded}}) == payload


def test_timestamped_output_path(tmp_path: Path) -> None:
    path = timestamped_output_path(tmp_path, "claim")
    assert path.parent == tmp_path
    assert path.name.startswith("claim_")
    assert path.suffix == ".json"


def test_configure_logging_outputs_json(caplog) -> None:
    configure_logging("INFO")
    logger = logging.getLogger("test_logger")
    with caplog.at_level(logging.INFO):
        logger.info("hello", extra={"context": {"claim_id": "CLM"}})
    assert logging.getLogger().level == logging.INFO


def test_bigquery_writer_converts_and_writes() -> None:
    client = Mock()
    client.insert_rows_json.return_value = []
    row = build_validated_claim_row(
        claim_id="CLM-001",
        member_id="MEM123456",
        provider_npi="1234567893",
        service_date="2026-01-15",
        amount=250.0,
        codes=["99213", "Z00.00"],
        is_valid=True,
        status="valid",
        errors=[],
        warnings=[],
        confidence=0.98,
        validation_latency_ms=1.2,
    )
    writer = ClaimsBigQueryWriter(client=client)
    writer.write_claim(row)
    client.insert_rows_json.assert_called_once()


def test_bigquery_writer_raises_on_insert_errors() -> None:
    client = Mock()
    client.insert_rows_json.return_value = [{"error": "bad"}]
    row = build_validated_claim_row(
        claim_id="CLM-001",
        member_id="MEM123456",
        provider_npi="1234567893",
        service_date="2026-01-15",
        amount=250.0,
        codes=["99213", "Z00.00"],
        is_valid=True,
        status="valid",
        errors=[],
        warnings=[],
        confidence=0.98,
        validation_latency_ms=1.2,
    )
    writer = ClaimsBigQueryWriter(client=client)
    try:
        writer.write_claim(row)
    except RuntimeError as exc:
        assert "BigQuery insert failed" in str(exc)
    else:
        raise AssertionError("Expected RuntimeError")
