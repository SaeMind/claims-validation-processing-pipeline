"""BigQuery persistence for validated and enriched claim records."""

import logging
from typing import Any

try:
    from google.cloud import bigquery
except ImportError:  # pragma: no cover - optional local dependency fallback
    bigquery = None  # type: ignore[assignment]

from src.config import SETTINGS, Settings

logger = logging.getLogger(__name__)


class ClaimsBigQueryWriter:
    """Write validated and enriched claim records to BigQuery for analytics and audit."""

    def __init__(self, settings: Settings = SETTINGS, client: Any | None = None) -> None:
        """Initialize the BigQuery writer."""
        self.settings = settings
        if client is not None:
            self.client = client
        else:
            if bigquery is None:
                raise ImportError("google-cloud-bigquery is required when no BigQuery client is injected")
            self.client = bigquery.Client(project=settings.gcp_project_id)
        self.table_id = settings.validated_table_id

    def write_claim(self, row: dict[str, Any]) -> None:
        """
        Persist one validated/enriched claim row to BigQuery.

        Parameters:
            row: Fully assembled claim record, combining validation and enrichment fields.

        Returns:
            None.
        """
        row_id = str(row.get("idempotency_key") or row.get("claim_id"))
        errors = self.client.insert_rows_json(self.table_id, [row], row_ids=[row_id])
        if errors:
            raise RuntimeError(f"BigQuery insert failed: {errors}")
        logger.info(
            "bigquery_write_success",
            extra={"context": {"claim_id": row.get("claim_id"), "table_id": self.table_id}},
        )


def build_validated_claim_row(
    claim_id: str,
    member_id: str,
    provider_npi: str,
    service_date: str,
    amount: float,
    codes: list[str],
    is_valid: bool,
    status: str,
    errors: list[str],
    warnings: list[str],
    confidence: float,
    validation_latency_ms: float,
    valid_codes: list[str] | None = None,
    invalid_codes: list[str] | None = None,
    member_risk_score: float | None = None,
    provider_specialty: str | None = None,
    fraud_flags: list[str] | None = None,
    quality_flags: list[str] | None = None,
    idempotency_key: str | None = None,
    event_received_at: str | None = None,
    processed_at: str | None = None,
    processing_latency_ms: int | None = None,
) -> dict[str, Any]:
    """
    Assemble a single merged BigQuery row combining validation and enrichment fields.

    Parameters:
        claim_id: Unique claim identifier.
        member_id: Member/patient identifier.
        provider_npi: Rendering/billing provider NPI.
        service_date: ISO date string of service.
        amount: Total claim amount.
        codes: Combined CPT/HCPCS + ICD-10 codes on the claim.
        is_valid: Whether the claim passed deep validation.
        status: ClaimStatus value as a string.
        errors: List of validation error messages.
        warnings: List of validation warning messages.
        confidence: Validation confidence score (0.0-1.0).
        validation_latency_ms: Time spent in the validation stage, in milliseconds.
        valid_codes: Codes confirmed against reference tables, if enrichment ran.
        invalid_codes: Codes not found in reference tables, if enrichment ran.
        member_risk_score: Member risk score from enrichment, if enrichment ran.
        provider_specialty: Provider specialty from enrichment, if enrichment ran.
        fraud_flags: Rule-based fraud signals, if enrichment ran.
        quality_flags: Data/care quality signals, if enrichment ran.
        idempotency_key: Deterministic dedupe key, if enrichment ran.
        event_received_at: ISO timestamp the raw event was received.
        processed_at: ISO timestamp processing completed.
        processing_latency_ms: End-to-end processing latency, in milliseconds.

    Returns:
        Dictionary shaped for the validated_claims BigQuery table.
    """
    return {
        "claim_id": claim_id,
        "member_id": member_id,
        "provider_npi": provider_npi,
        "service_date": service_date,
        "amount": amount,
        "codes": codes,
        "is_valid": is_valid,
        "status": status,
        "errors": errors,
        "warnings": warnings,
        "confidence": confidence,
        "validation_latency_ms": validation_latency_ms,
        "valid_codes": valid_codes or [],
        "invalid_codes": invalid_codes or [],
        "member_risk_score": member_risk_score,
        "provider_specialty": provider_specialty,
        "fraud_flags": fraud_flags or [],
        "quality_flags": quality_flags or [],
        "idempotency_key": idempotency_key,
        "event_received_at": event_received_at,
        "processed_at": processed_at,
        "processing_latency_ms": processing_latency_ms,
    }
