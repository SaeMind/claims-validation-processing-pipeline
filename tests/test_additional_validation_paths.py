from datetime import date
import pytest
from pydantic import ValidationError

from src.claim_validator import ClaimsValidator
from src.schemas import ClaimRecord, MedicalProcedure, DiagnosisCode
from tests.test_schema_validation import valid_claim_payload


def test_no_primary_diagnosis_conditional() -> None:
    payload = valid_claim_payload()
    payload["diagnoses"] = [{"icd10_code": "I10", "primary": False}]
    result = ClaimsValidator().validate(ClaimRecord(**payload))
    assert result.warnings


def test_uncommon_place_of_service_warns() -> None:
    payload = valid_claim_payload()
    payload["place_of_service"] = "99"
    result = ClaimsValidator().validate(ClaimRecord(**payload))
    assert any("place of service" in warning.lower() for warning in result.warnings)


def test_medical_necessity_warning() -> None:
    payload = valid_claim_payload()
    payload["procedures"] = [{"procedure_code": "27447", "units": 1, "amount": 1000.0}]
    payload["diagnoses"] = [{"icd10_code": "I10", "primary": True}]
    payload["total_amount"] = 1000.0
    result = ClaimsValidator().validate(ClaimRecord(**payload))
    assert any("not typically supported" in warning for warning in result.warnings)


def test_duplicate_procedure_warning() -> None:
    payload = valid_claim_payload()
    payload["procedures"] = [
        {"procedure_code": "99213", "modifier": "25", "units": 1, "amount": 75.0},
        {"procedure_code": "99213", "modifier": "25", "units": 1, "amount": 75.0},
    ]
    payload["total_amount"] = 150.0
    result = ClaimsValidator().validate(ClaimRecord(**payload))
    assert any("duplicate" in warning.lower() for warning in result.warnings)


def test_high_amount_warnings() -> None:
    payload = valid_claim_payload()
    payload["procedures"] = [{"procedure_code": "99213", "units": 1, "amount": 60000.0}]
    payload["total_amount"] = 60000.0
    result = ClaimsValidator().validate(ClaimRecord(**payload))
    assert result.warnings


def test_frequency_limit_warning() -> None:
    payload = valid_claim_payload()
    payload["procedures"] = [{"procedure_code": "45398", "units": 1, "amount": 150.0}]
    payload["diagnoses"] = [{"icd10_code": "K63.5", "primary": True}]
    result = ClaimsValidator().validate(ClaimRecord(**payload))
    assert any("frequency" in warning.lower() for warning in result.warnings)


def test_invalid_modifier_raises() -> None:
    with pytest.raises(ValidationError):
        MedicalProcedure(procedure_code="99213", modifier="LONG", units=1, amount=1.0)


def test_invalid_icd_raises() -> None:
    with pytest.raises(ValidationError):
        DiagnosisCode(icd10_code="123", primary=True)


def test_multiple_primary_diagnoses_rejected() -> None:
    payload = valid_claim_payload()
    payload["diagnoses"] = [
        {"icd10_code": "I10", "primary": True},
        {"icd10_code": "E11.9", "primary": True},
    ]
    with pytest.raises(ValidationError):
        ClaimRecord(**payload)
