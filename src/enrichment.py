"""Claim enrichment: member risk scoring, provider lookups, and fraud/quality signals."""

from __future__ import annotations

import hashlib
import logging
from collections.abc import Iterable, Mapping
from datetime import datetime, timezone
from typing import Any

try:
    from google.api_core.exceptions import GoogleAPIError
    from google.cloud import bigquery
except ImportError:  # pragma: no cover - optional local dependency fallback
    GoogleAPIError = Exception  # type: ignore[assignment,misc]
    bigquery = None  # type: ignore[assignment]

try:
    from sqlalchemy import create_engine, text
    from sqlalchemy.engine import Engine
except ImportError:  # pragma: no cover - optional local dependency fallback
    create_engine = None  # type: ignore[assignment]
    text = None  # type: ignore[assignment]
    Engine = object  # type: ignore[assignment,misc]

from src.config import Settings

logger = logging.getLogger(__name__)

_sql_engine: Engine | None = None


def lookup_member_risk_score(
    member_id: str, settings: Settings, client: object | None = None
) -> float:
    """
    Look up a member risk score from BigQuery.

    Parameters:
        member_id: Member identifier to look up.
        settings: Application settings.
        client: Optional injected BigQuery client (for testing).

    Returns:
        Risk score as a float. Defaults to 1.0 (baseline risk) on lookup failure.
    """
    if bigquery is None and client is None:
        return 1.0
    bq_client = client if client is not None else bigquery.Client(project=settings.gcp_project_id)
    query = f"""
        SELECT risk_score
        FROM `{settings.member_risk_table_id}`
        WHERE member_id = @member_id
        LIMIT 1
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("member_id", "STRING", member_id)]
    )
    try:
        rows = list(bq_client.query(query, job_config=job_config).result())
    except GoogleAPIError as exc:
        logger.warning("member_risk_lookup_failed", extra={"context": {"member_id": member_id, "error": str(exc)}})
        return 1.0
    return float(rows[0].risk_score) if rows else 1.0


def get_sql_engine(settings: Settings) -> Engine:
    """
    Create or return a cached SQLAlchemy engine for provider reference data.

    Parameters:
        settings: Application settings.

    Returns:
        SQLAlchemy Engine connected to the provider reference store.
    """
    global _sql_engine
    if _sql_engine is not None:
        return _sql_engine
    if create_engine is None:
        raise ImportError("sqlalchemy is required to connect to the provider reference store")
    if settings.local_mode or not settings.cloudsql_instance:
        connection_url = (
            f"{settings.cloudsql_driver}://{settings.cloudsql_user}:"
            f"{settings.cloudsql_password}@postgres:5432/{settings.cloudsql_database}"
        )
    else:
        connection_url = (
            f"{settings.cloudsql_driver}://{settings.cloudsql_user}:"
            f"{settings.cloudsql_password}@/{settings.cloudsql_database}"
            f"?unix_sock=/cloudsql/{settings.cloudsql_instance}/.s.PGSQL.5432"
        )
    _sql_engine = create_engine(connection_url, pool_pre_ping=True)
    return _sql_engine


def lookup_provider_specialty(provider_id: str, settings: Settings) -> str:
    """
    Look up provider specialty from Cloud SQL or local PostgreSQL.

    Parameters:
        provider_id: Provider identifier to look up.
        settings: Application settings.

    Returns:
        Provider specialty string, or "UNKNOWN" on lookup failure.
    """
    try:
        engine = get_sql_engine(settings)
        with engine.connect() as connection:
            row = connection.execute(
                text("SELECT specialty FROM providers WHERE provider_id = :provider_id LIMIT 1"),
                {"provider_id": provider_id},
            ).fetchone()
        return str(row[0]) if row else "UNKNOWN"
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.warning("provider_lookup_failed", extra={"context": {"provider_id": provider_id, "error": str(exc)}})
        return "UNKNOWN"


def validate_codes_against_references(
    codes: Iterable[str], settings: Settings, client: object | None = None
) -> tuple[list[str], list[str]]:
    """
    Cross-check claim procedure/diagnosis codes against BigQuery reference tables.

    Parameters:
        codes: Iterable of code strings on the claim.
        settings: Application settings.
        client: Optional injected BigQuery client (for testing).

    Returns:
        Tuple of (valid_codes, invalid_codes).
    """
    clean_codes = [code.strip().upper() for code in codes]
    if not clean_codes:
        return [], []
    if bigquery is None and client is None:
        return clean_codes, []
    bq_client = client if client is not None else bigquery.Client(project=settings.gcp_project_id)
    query = f"""
        SELECT code FROM `{settings.icd10_reference_table_id}` WHERE code IN UNNEST(@codes)
        UNION DISTINCT
        SELECT code FROM `{settings.cpt_reference_table_id}` WHERE code IN UNNEST(@codes)
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ArrayQueryParameter("codes", "STRING", clean_codes)]
    )
    try:
        rows = bq_client.query(query, job_config=job_config).result()
        valid_code_set = {str(row.code) for row in rows}
    except GoogleAPIError as exc:
        logger.warning("code_reference_lookup_failed", extra={"context": {"error": str(exc)}})
        valid_code_set = set()
    valid_codes = [code for code in clean_codes if code in valid_code_set]
    invalid_codes = [code for code in clean_codes if code not in valid_code_set]
    return valid_codes, invalid_codes


def detect_fraud_flags(enriched_claim: Mapping[str, Any], settings: Settings) -> list[str]:
    """
    Detect rule-based fraud signals on an enriched claim.

    Parameters:
        enriched_claim: Claim dictionary after validation and enrichment.
        settings: Application settings.

    Returns:
        List of fraud flag strings.
    """
    flags: list[str] = []
    if float(enriched_claim.get("amount", 0.0)) >= settings.high_cost_threshold:
        flags.append("HIGH_COST_CLAIM")
    if enriched_claim.get("provider_specialty") == "UNKNOWN":
        flags.append("UNKNOWN_PROVIDER_SPECIALTY")
    if enriched_claim.get("invalid_codes"):
        flags.append("INVALID_BILLING_CODES")
    if float(enriched_claim.get("member_risk_score", 1.0)) >= 3.0:
        flags.append("HIGH_RISK_MEMBER")
    return flags


def detect_quality_flags(enriched_claim: Mapping[str, Any]) -> list[str]:
    """
    Detect care-quality and data-quality issues on an enriched claim.

    Parameters:
        enriched_claim: Claim dictionary after validation and enrichment.

    Returns:
        List of quality flag strings.
    """
    flags: list[str] = []
    if len(enriched_claim.get("codes", [])) > 12:
        flags.append("EXCESSIVE_CODE_COUNT")
    if not enriched_claim.get("valid_codes"):
        flags.append("NO_VALID_CODES")
    return flags


def build_idempotency_key(claim: Mapping[str, Any]) -> str:
    """
    Build a deterministic idempotency key for duplicate claim prevention.

    Parameters:
        claim: Claim dictionary containing identifying fields.

    Returns:
        SHA-256 hex digest derived from stable claim identifiers.
    """
    key_source = "|".join(
        [
            str(claim.get("claim_id", "")),
            str(claim.get("member_id", "")),
            str(claim.get("provider_id", "")),
            str(claim.get("service_date", "")),
            str(claim.get("amount", "")),
        ]
    )
    return hashlib.sha256(key_source.encode("utf-8")).hexdigest()


def calculate_latency_ms(received_at: datetime) -> int:
    """
    Calculate processing latency in milliseconds from receipt to now.

    Parameters:
        received_at: UTC timestamp when the event was received.

    Returns:
        Elapsed latency in whole milliseconds.
    """
    return int((datetime.now(timezone.utc) - received_at).total_seconds() * 1000)
