from datetime import date, timedelta

from src.claim_validator import ClaimsValidator
from src.schemas import ClaimRecord, ClaimStatus
from tests.test_schema_validation import valid_claim_payload


def test_valid_claim_passes() -> None:
    result = ClaimsValidator().validate(ClaimRecord(**valid_claim_payload()))
    assert result.status == ClaimStatus.VALID
    assert result.is_valid is True


def test_future_service_date_fails() -> None:
    payload = valid_claim_payload()
    payload["date_of_service"] = str(date.today() + timedelta(days=1))
    result = ClaimsValidator().validate(ClaimRecord(**payload))
    assert result.status == ClaimStatus.INVALID
    assert any("future" in error.lower() for error in result.errors)


def test_total_amount_mismatch_fails() -> None:
    payload = valid_claim_payload()
    payload["total_amount"] = 999.0
    result = ClaimsValidator().validate(ClaimRecord(**payload))
    assert result.status == ClaimStatus.INVALID
