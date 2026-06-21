"""Unit tests for src.enrichment — fraud/quality flagging and idempotency keys."""

from datetime import datetime, timedelta, timezone

from src.config import Settings, load_settings
from src.enrichment import (
    build_idempotency_key,
    calculate_latency_ms,
    detect_fraud_flags,
    detect_quality_flags,
)


def _settings() -> Settings:
    return load_settings()


def test_detect_fraud_flags_high_cost_claim() -> None:
    settings = _settings()
    claim = {
        "amount": settings.high_cost_threshold + 1,
        "provider_specialty": "CARDIOLOGY",
        "invalid_codes": [],
        "member_risk_score": 1.0,
    }
    flags = detect_fraud_flags(claim, settings)
    assert "HIGH_COST_CLAIM" in flags


def test_detect_fraud_flags_unknown_provider() -> None:
    settings = _settings()
    claim = {
        "amount": 100.0,
        "provider_specialty": "UNKNOWN",
        "invalid_codes": [],
        "member_risk_score": 1.0,
    }
    flags = detect_fraud_flags(claim, settings)
    assert "UNKNOWN_PROVIDER_SPECIALTY" in flags


def test_detect_fraud_flags_invalid_codes_and_high_risk_member() -> None:
    settings = _settings()
    claim = {
        "amount": 100.0,
        "provider_specialty": "FAMILY_MEDICINE",
        "invalid_codes": ["BADCODE"],
        "member_risk_score": 3.5,
    }
    flags = detect_fraud_flags(claim, settings)
    assert "INVALID_BILLING_CODES" in flags
    assert "HIGH_RISK_MEMBER" in flags


def test_detect_fraud_flags_clean_claim_has_no_flags() -> None:
    settings = _settings()
    claim = {
        "amount": 100.0,
        "provider_specialty": "FAMILY_MEDICINE",
        "invalid_codes": [],
        "member_risk_score": 1.0,
    }
    assert detect_fraud_flags(claim, settings) == []


def test_detect_quality_flags_excessive_code_count() -> None:
    claim = {"codes": [f"CODE{i}" for i in range(13)], "valid_codes": [f"CODE{i}" for i in range(13)]}
    flags = detect_quality_flags(claim)
    assert "EXCESSIVE_CODE_COUNT" in flags


def test_detect_quality_flags_no_valid_codes() -> None:
    claim = {"codes": ["X1"], "valid_codes": []}
    flags = detect_quality_flags(claim)
    assert "NO_VALID_CODES" in flags


def test_build_idempotency_key_is_deterministic() -> None:
    claim = {
        "claim_id": "CLM-1",
        "member_id": "MEM-1",
        "provider_id": "PRV-1",
        "service_date": "2026-01-01",
        "amount": 100.0,
    }
    key_a = build_idempotency_key(claim)
    key_b = build_idempotency_key(dict(claim))
    assert key_a == key_b
    assert len(key_a) == 64  # sha256 hex digest length


def test_build_idempotency_key_changes_with_input() -> None:
    base = {"claim_id": "CLM-1", "member_id": "MEM-1", "provider_id": "PRV-1", "service_date": "2026-01-01", "amount": 100.0}
    changed = dict(base, amount=200.0)
    assert build_idempotency_key(base) != build_idempotency_key(changed)


def test_calculate_latency_ms_is_non_negative() -> None:
    received_at = datetime.now(timezone.utc) - timedelta(milliseconds=5)
    latency = calculate_latency_ms(received_at)
    assert latency >= 0
