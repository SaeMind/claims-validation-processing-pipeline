"""Unit tests for src.dataflow_pipeline — testing DoFn logic directly without a Beam runner.

apache-beam is a heavy optional dependency. These tests are skipped automatically
if apache-beam is not installed in the current environment, so the rest of the
test suite (validation, enrichment, BigQuery writer) remains runnable without it.
"""

import json

import pytest

beam = pytest.importorskip("apache_beam")

from src.dataflow_pipeline import AlertAnomalies, ParseClaimMessage, ToMemberKey  # noqa: E402


def test_parse_claim_message_valid_json() -> None:
    message = json.dumps({"claim_id": "CLM-1", "member_id": "MEM-1", "amount": 50.0}).encode("utf-8")
    results = list(ParseClaimMessage().process(message))
    assert len(results) == 1
    assert results[0]["claim_id"] == "CLM-1"


def test_parse_claim_message_invalid_json_yields_nothing() -> None:
    message = b"not-json"
    results = list(ParseClaimMessage().process(message))
    assert results == []


def test_to_member_key_groups_by_member_id() -> None:
    claim = {"member_id": "MEM-1", "claim_id": "CLM-1", "amount": 100.0, "service_date": "2026-01-01"}
    results = list(ToMemberKey().process(claim))
    assert len(results) == 1
    member_id, payload = results[0]
    assert member_id == "MEM-1"
    assert payload["amount"] == 100.0


def test_alert_anomalies_skips_clean_aggregates() -> None:
    aggregate = {"anomaly_flags": [], "member_id": "MEM-1"}
    results = list(AlertAnomalies().process(aggregate))
    assert results == []


def test_alert_anomalies_emits_alert_for_flagged_aggregate() -> None:
    aggregate = {
        "member_id": "MEM-1",
        "claim_count": 12,
        "member_window_spend": 30000.0,
        "anomaly_flags": ["UNUSUAL_30_SECOND_CLAIM_VOLUME", "HIGH_30_SECOND_MEMBER_SPEND"],
        "window_start": "2026-01-01T00:00:00+00:00",
        "window_end": "2026-01-01T00:00:30+00:00",
    }
    results = list(AlertAnomalies().process(aggregate))
    assert len(results) == 1
    alert = json.loads(results[0])
    assert alert["alert_type"] == "MEMBER_AGGREGATION_ANOMALY"
    assert alert["member_id"] == "MEM-1"
