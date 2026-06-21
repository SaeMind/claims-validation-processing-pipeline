"""Pydantic V2 schemas for healthcare claim validation."""

from datetime import date, datetime, timezone
from enum import Enum
from typing import Any
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.cpt_validator import is_valid_modifier, is_valid_procedure_code, normalize_procedure_code
from src.icd10_validator import is_valid_icd10, normalize_icd10
from src.npi_validator import validate_npi_checksum


class ClaimStatus(str, Enum):
    """Possible validation statuses."""

    VALID = "valid"
    INVALID = "invalid"
    CONDITIONAL = "conditional"


class ErrorSeverity(str, Enum):
    """Validation severity levels."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ValidationIssue(BaseModel):
    """Structured validation issue."""

    rule_id: str
    severity: ErrorSeverity
    message: str
    field: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class MedicalProcedure(BaseModel):
    """Individual procedure line on a healthcare claim."""

    model_config = ConfigDict(str_strip_whitespace=True)

    procedure_code: str = Field(..., description="CPT or HCPCS code")
    modifier: str | None = Field(default=None, description="Procedure modifier")
    units: int = Field(..., gt=0, description="Number of units")
    amount: float = Field(..., ge=0, description="Allowed amount")

    @field_validator("procedure_code")
    @classmethod
    def validate_procedure_code(cls, value: str) -> str:
        """Validate CPT/HCPCS code syntax."""
        normalized = normalize_procedure_code(value)
        if not is_valid_procedure_code(normalized):
            raise ValueError(f"Invalid CPT/HCPCS code: {value}")
        return normalized

    @field_validator("modifier")
    @classmethod
    def validate_modifier(cls, value: str | None) -> str | None:
        """Validate optional procedure modifier syntax."""
        if value is None:
            return value
        normalized = value.strip().upper()
        if not is_valid_modifier(normalized):
            raise ValueError(f"Invalid procedure modifier: {value}")
        return normalized


class DiagnosisCode(BaseModel):
    """Diagnosis line on a healthcare claim."""

    model_config = ConfigDict(str_strip_whitespace=True)

    icd10_code: str = Field(..., description="ICD-10-CM diagnosis code")
    description: str | None = Field(default=None, description="Diagnosis description")
    primary: bool = Field(default=False, description="Whether this is the primary diagnosis")

    @field_validator("icd10_code")
    @classmethod
    def validate_icd10_code(cls, value: str) -> str:
        """Validate ICD-10-CM syntax."""
        normalized = normalize_icd10(value)
        if not is_valid_icd10(normalized):
            raise ValueError(f"Invalid ICD-10-CM code: {value}")
        return normalized


class ClaimRecord(BaseModel):
    """Healthcare claim record received from a payer/provider event stream."""

    model_config = ConfigDict(str_strip_whitespace=True)

    claim_id: str = Field(..., min_length=3, description="Unique claim identifier")
    member_id: str = Field(..., min_length=6, description="Member/patient identifier")
    provider_npi: str = Field(..., description="Rendering or billing provider NPI")
    date_of_service: date = Field(..., description="Service date")
    total_amount: float = Field(..., ge=0, description="Total claim amount")
    procedures: list[MedicalProcedure] = Field(default_factory=list)
    diagnoses: list[DiagnosisCode] = Field(default_factory=list)
    place_of_service: str = Field(..., description="CMS place of service code")
    source_system: str | None = Field(default=None, description="Source system name")
    received_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("provider_npi")
    @classmethod
    def validate_provider_npi(cls, value: str) -> str:
        """Validate NPI length, digits, and checksum."""
        if not validate_npi_checksum(value):
            raise ValueError(f"Invalid NPI checksum: {value}")
        return value

    @field_validator("place_of_service")
    @classmethod
    def validate_pos_format(cls, value: str) -> str:
        """Validate POS code basic format."""
        normalized = value.zfill(2)
        if len(normalized) != 2 or not normalized.isdigit():
            raise ValueError(f"Invalid place of service: {value}")
        return normalized

    @model_validator(mode="after")
    def validate_primary_diagnosis(self) -> "ClaimRecord":
        """Ensure no more than one diagnosis is flagged as primary."""
        primary_count = sum(1 for diagnosis in self.diagnoses if diagnosis.primary)
        if primary_count > 1:
            raise ValueError("Only one diagnosis may be marked primary")
        return self


class ValidationResult(BaseModel):
    """Output of the claims validation workflow."""

    claim_id: str
    member_id: str
    status: ClaimStatus
    is_valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    issues: list[ValidationIssue] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    validation_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    validation_latency_ms: float
    routed_topic: str | None = None
