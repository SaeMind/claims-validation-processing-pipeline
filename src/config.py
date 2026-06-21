"""Runtime configuration for the claims validation, enrichment, and aggregation pipeline."""

from dataclasses import dataclass
from pathlib import Path
import os
from typing import Any


@dataclass(frozen=True)
class Settings:
    """Application settings loaded from environment variables."""

    # GCP project / region
    gcp_project_id: str
    gcp_region: str

    # Pub/Sub topics
    raw_claims_topic: str
    valid_claims_topic: str
    invalid_claims_topic: str
    retry_claims_topic: str
    manual_review_topic: str
    rejected_claims_topic: str
    alerts_topic: str

    # BigQuery
    bigquery_dataset: str
    bigquery_validated_table: str
    bigquery_aggregate_table: str
    member_risk_table: str
    icd10_reference_table: str
    cpt_reference_table: str

    # Provider reference store (Cloud SQL / local Postgres)
    cloudsql_instance: str
    cloudsql_database: str
    cloudsql_user: str
    cloudsql_password: str
    cloudsql_driver: str

    # Validation thresholds
    max_claim_amount: float
    max_procedure_amount: float
    max_claim_age_days: int
    max_future_service_days: int

    # Enrichment / fraud thresholds
    high_cost_threshold: float
    duplicate_cache_ttl_seconds: int

    # Output / runtime
    output_dir: Path
    log_level: str
    enable_bigquery: bool
    enable_pubsub_publish: bool
    local_mode: bool

    @property
    def validated_table_id(self) -> str:
        """Return fully qualified BigQuery table ID for validated/enriched claims."""
        return f"{self.gcp_project_id}.{self.bigquery_dataset}.{self.bigquery_validated_table}"

    @property
    def aggregate_table_id(self) -> str:
        """Return fully qualified BigQuery table ID for member-level aggregates."""
        return f"{self.gcp_project_id}.{self.bigquery_dataset}.{self.bigquery_aggregate_table}"

    @property
    def member_risk_table_id(self) -> str:
        """Return fully qualified BigQuery table ID for member risk lookup."""
        return f"{self.gcp_project_id}.{self.bigquery_dataset}.{self.member_risk_table}"

    @property
    def icd10_reference_table_id(self) -> str:
        """Return fully qualified BigQuery table ID for ICD-10 reference codes."""
        return f"{self.gcp_project_id}.{self.bigquery_dataset}.{self.icd10_reference_table}"

    @property
    def cpt_reference_table_id(self) -> str:
        """Return fully qualified BigQuery table ID for CPT reference codes."""
        return f"{self.gcp_project_id}.{self.bigquery_dataset}.{self.cpt_reference_table}"


def _get_bool(name: str, default: bool) -> bool:
    """
    Parse a boolean environment variable.

    Parameters:
        name: Environment variable name.
        default: Fallback boolean value.

    Returns:
        Parsed boolean value.
    """
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y"}


def load_settings() -> Settings:
    """
    Load application settings from environment variables.

    Parameters:
        None.

    Returns:
        Settings object.
    """
    return Settings(
        gcp_project_id=os.getenv("GCP_PROJECT_ID", "local-healthcare-project"),
        gcp_region=os.getenv("GCP_REGION", "us-central1"),
        raw_claims_topic=os.getenv("RAW_CLAIMS_TOPIC", "incoming-claims"),
        valid_claims_topic=os.getenv("VALID_CLAIMS_TOPIC", "valid-claims"),
        invalid_claims_topic=os.getenv("INVALID_CLAIMS_TOPIC", "invalid-claims"),
        retry_claims_topic=os.getenv("RETRY_CLAIMS_TOPIC", "retry-claims"),
        manual_review_topic=os.getenv("MANUAL_REVIEW_TOPIC", "manual-review-claims"),
        rejected_claims_topic=os.getenv("REJECTED_CLAIMS_TOPIC", "rejected-claims"),
        alerts_topic=os.getenv("ALERTS_TOPIC", "claims-alerts"),
        bigquery_dataset=os.getenv("BIGQUERY_DATASET", "claims_analytics"),
        bigquery_validated_table=os.getenv("BIGQUERY_VALIDATED_TABLE", "validated_claims"),
        bigquery_aggregate_table=os.getenv("BIGQUERY_AGGREGATE_TABLE", "member_claim_aggregates"),
        member_risk_table=os.getenv("MEMBER_RISK_TABLE", "member_risk_scores"),
        icd10_reference_table=os.getenv("ICD10_REFERENCE_TABLE", "icd10_codes"),
        cpt_reference_table=os.getenv("CPT_REFERENCE_TABLE", "cpt_codes"),
        cloudsql_instance=os.getenv("CLOUDSQL_INSTANCE", ""),
        cloudsql_database=os.getenv("CLOUDSQL_DATABASE", "claims_ref"),
        cloudsql_user=os.getenv("CLOUDSQL_USER", "postgres"),
        cloudsql_password=os.getenv("CLOUDSQL_PASSWORD", "postgres"),
        cloudsql_driver=os.getenv("CLOUDSQL_DRIVER", "postgresql+pg8000"),
        max_claim_amount=float(os.getenv("MAX_CLAIM_AMOUNT", "100000")),
        max_procedure_amount=float(os.getenv("MAX_PROCEDURE_AMOUNT", "50000")),
        max_claim_age_days=int(os.getenv("MAX_CLAIM_AGE_DAYS", "3650")),
        max_future_service_days=int(os.getenv("MAX_FUTURE_SERVICE_DAYS", "7")),
        high_cost_threshold=float(os.getenv("HIGH_COST_THRESHOLD", "10000")),
        duplicate_cache_ttl_seconds=int(os.getenv("DUPLICATE_CACHE_TTL_SECONDS", "86400")),
        output_dir=Path(os.getenv("OUTPUT_DIR", "outputs")),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        enable_bigquery=_get_bool("ENABLE_BIGQUERY", True),
        enable_pubsub_publish=_get_bool("ENABLE_PUBSUB_PUBLISH", True),
        local_mode=_get_bool("LOCAL_MODE", False),
    )


VALIDATION_RULES: dict[str, Any] = {
    "allowed_places_of_service": {"11", "21", "22", "23", "24", "31", "32", "81"},
    "frequency_limits": {
        "45398": {"days": 3650, "description": "screening colonoscopy"},
        "77056": {"days": 365, "description": "diagnostic mammography"},
        "G0438": {"days": 365, "description": "annual wellness visit"},
    },
    "medical_necessity": {
        "27447": {"allowed_diagnosis_prefixes": ["M16", "M17", "M19"]},
        "45398": {"allowed_diagnosis_prefixes": ["K62", "K63", "Z12"]},
        "93000": {"allowed_diagnosis_prefixes": ["I", "R07", "R00", "Z13"]},
    },
}

SETTINGS = load_settings()
