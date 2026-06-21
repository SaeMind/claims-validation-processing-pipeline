from datetime import date
from pydantic import ValidationError
import pytest
from src.schemas import ClaimRecord


def valid_claim_payload() -> dict:
    return {
        "claim_id": "CLM-001",
        "member_id": "MEM123456",
        "provider_npi": "1234567893",
        "date_of_service": str(date.today()),
        "total_amount": 150.0,
        "procedures": [{"procedure_code": "99213", "units": 1, "amount": 150.0}],
        "diagnoses": [{"icd10_code": "I10", "primary": True}],
        "place_of_service": "11",
    }


def test_claim_schema_accepts_valid_payload() -> None:
    claim = ClaimRecord(**valid_claim_payload())
    assert claim.claim_id == "CLM-001"


def test_claim_schema_rejects_bad_npi() -> None:
    payload = valid_claim_payload()
    payload["provider_npi"] = "1234567890"
    with pytest.raises(ValidationError):
        ClaimRecord(**payload)
