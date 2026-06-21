"""Business rules engine for healthcare claims validation."""

import logging
from datetime import date

from src.config import SETTINGS, VALIDATION_RULES, Settings
from src.metrics import record_validation, timer, traced_span
from src.schemas import ClaimRecord, ClaimStatus, ErrorSeverity, ValidationIssue, ValidationResult

logger = logging.getLogger(__name__)


class ClaimsValidator:
    """Validate claims against structural, coding, medical necessity, and financial rules."""

    def __init__(self, settings: Settings = SETTINGS, rules: dict = VALIDATION_RULES) -> None:
        """
        Initialize the claims validator.

        Parameters:
            settings: Runtime settings.
            rules: Validation rule dictionary.

        Returns:
            None.
        """
        self.settings = settings
        self.rules = rules
        self.issues: list[ValidationIssue] = []

    def validate(self, claim: ClaimRecord) -> ValidationResult:
        """
        Execute all configured validations against a claim.

        Parameters:
            claim: ClaimRecord object.

        Returns:
            ValidationResult with status, errors, warnings, and confidence.
        """
        self.issues = []
        with timer() as elapsed_ms:
            with traced_span("validate_claim_business_rules"):
                self._validate_structure(claim)
                self._validate_place_of_service(claim)
                self._validate_medical_necessity(claim)
                self._validate_coding_rules(claim)
                self._validate_amount_thresholds(claim)
                self._validate_frequency_limits(claim)

        errors = [issue.message for issue in self.issues if issue.severity == ErrorSeverity.ERROR]
        warnings = [issue.message for issue in self.issues if issue.severity == ErrorSeverity.WARNING]
        is_valid = not errors
        if errors:
            status = ClaimStatus.INVALID
        elif warnings:
            status = ClaimStatus.CONDITIONAL
        else:
            status = ClaimStatus.VALID
        confidence = self._calculate_confidence(error_count=len(errors), warning_count=len(warnings))
        latency = elapsed_ms()
        record_validation(status.value, latency)
        return ValidationResult(
            claim_id=claim.claim_id,
            member_id=claim.member_id,
            status=status,
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            issues=self.issues,
            confidence=confidence,
            validation_latency_ms=latency,
        )

    def _add_issue(self, rule_id: str, severity: ErrorSeverity, message: str, field: str | None = None) -> None:
        """Add a structured validation issue to the current result."""
        self.issues.append(ValidationIssue(rule_id=rule_id, severity=severity, message=message, field=field))

    def _validate_structure(self, claim: ClaimRecord) -> None:
        """Validate required claim sections and service date semantics."""
        if not claim.procedures:
            self._add_issue("STRUCTURE_001", ErrorSeverity.ERROR, "Claim has no procedures", "procedures")
        if not claim.diagnoses:
            self._add_issue("STRUCTURE_002", ErrorSeverity.ERROR, "Claim has no diagnoses", "diagnoses")
        if claim.date_of_service > date.today():
            self._add_issue(
                "STRUCTURE_003",
                ErrorSeverity.ERROR,
                f"Service date in future: {claim.date_of_service}",
                "date_of_service",
            )
        if claim.diagnoses and not any(dx.primary for dx in claim.diagnoses):
            self._add_issue("STRUCTURE_004", ErrorSeverity.WARNING, "No primary diagnosis indicated", "diagnoses")

    def _validate_place_of_service(self, claim: ClaimRecord) -> None:
        """Validate place of service against configured allowed values."""
        allowed = self.rules.get("allowed_places_of_service", set())
        if claim.place_of_service not in allowed:
            self._add_issue(
                "POS_001",
                ErrorSeverity.WARNING,
                f"Place of service {claim.place_of_service} is uncommon or not configured",
                "place_of_service",
            )

    def _validate_medical_necessity(self, claim: ClaimRecord) -> None:
        """Validate diagnosis-procedure combinations against configured medical necessity rules."""
        diagnosis_codes = [diagnosis.icd10_code for diagnosis in claim.diagnoses]
        medical_rules = self.rules.get("medical_necessity", {})
        for procedure in claim.procedures:
            rule = medical_rules.get(procedure.procedure_code)
            if not rule:
                continue
            allowed_prefixes = tuple(rule.get("allowed_diagnosis_prefixes", []))
            if allowed_prefixes and not any(code.startswith(allowed_prefixes) for code in diagnosis_codes):
                self._add_issue(
                    "MED_NEC_001",
                    ErrorSeverity.WARNING,
                    f"Procedure {procedure.procedure_code} is not typically supported by diagnoses {diagnosis_codes}",
                    "procedures",
                )

    def _validate_coding_rules(self, claim: ClaimRecord) -> None:
        """Validate duplicate procedures and claim total reconciliation."""
        line_keys = [(p.procedure_code, p.modifier) for p in claim.procedures]
        if len(line_keys) != len(set(line_keys)):
            self._add_issue(
                "CODING_001",
                ErrorSeverity.WARNING,
                "Claim has duplicate procedure/modifier combinations",
                "procedures",
            )
        procedure_total = round(sum(procedure.amount for procedure in claim.procedures), 2)
        claim_total = round(claim.total_amount, 2)
        if abs(procedure_total - claim_total) > 0.01:
            self._add_issue(
                "CODING_002",
                ErrorSeverity.ERROR,
                f"Total amount mismatch: procedures sum to {procedure_total}, but claim total is {claim_total}",
                "total_amount",
            )

    def _validate_amount_thresholds(self, claim: ClaimRecord) -> None:
        """Validate claim and procedure amount thresholds."""
        if claim.total_amount > self.settings.max_claim_amount:
            self._add_issue(
                "AMOUNT_001",
                ErrorSeverity.ERROR,
                f"Claim amount {claim.total_amount} exceeds threshold {self.settings.max_claim_amount}",
                "total_amount",
            )
        for procedure in claim.procedures:
            if procedure.amount > self.settings.max_procedure_amount:
                self._add_issue(
                    "AMOUNT_002",
                    ErrorSeverity.WARNING,
                    f"Procedure {procedure.procedure_code} amount {procedure.amount} exceeds procedure threshold",
                    "procedures",
                )
            amount_per_unit = procedure.amount / procedure.units
            if amount_per_unit > 5000:
                self._add_issue(
                    "AMOUNT_003",
                    ErrorSeverity.WARNING,
                    f"High per-unit amount: ${amount_per_unit:.2f} for procedure {procedure.procedure_code}",
                    "procedures",
                )

    def _validate_frequency_limits(self, claim: ClaimRecord) -> None:
        """Flag procedures requiring historical utilization checks."""
        frequency_limits = self.rules.get("frequency_limits", {})
        for procedure in claim.procedures:
            if procedure.procedure_code in frequency_limits:
                description = frequency_limits[procedure.procedure_code].get("description", "procedure")
                self._add_issue(
                    "FREQ_001",
                    ErrorSeverity.WARNING,
                    f"Procedure {procedure.procedure_code} ({description}) requires member history frequency check",
                    "procedures",
                )

    def _calculate_confidence(self, error_count: int, warning_count: int) -> float:
        """Calculate validation confidence score based on issues."""
        score = 0.98 - (error_count * 0.2) - (warning_count * 0.05)
        return max(0.1, min(0.98, round(score, 2)))
