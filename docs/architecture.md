# Architecture Notes

## Background

This repository merges two originally separate portfolio builds into one
coherent pipeline:

1. **Serverless Claims Validation Pipeline (Cloud Functions)** — deep
   structural and coding validation (CPT/HCPCS syntax, ICD-10-CM syntax, NPI
   checksum, medical necessity, frequency limits, amount reconciliation).
2. **Pub/Sub Event-Driven Claims Processing Pipeline** — enrichment (member
   risk score, provider specialty), fraud/quality flagging, and streaming
   member-level aggregation via Dataflow.

They shared the same domain (healthcare claims), the same default Pub/Sub
topic names (`valid-claims` / `invalid-claims`), and a complementary
relationship — validation naturally precedes enrichment and aggregation in a
production claims pipeline. Rather than ship two overlapping GCP-pattern
repositories, this merge combines them into a single, more representative
production-style pipeline.

## Event Flow

1. A raw claim JSON payload is published to `incoming-claims`.
2. `validate_and_enrich_claim` (Cloud Function) parses the Pub/Sub CloudEvent.
3. Pydantic V2 schemas enforce structural validity (`ClaimRecord`).
4. Business rules execute deep healthcare validation checks (CPT/HCPCS, ICD-10-CM, NPI, medical necessity, frequency limits, amount reconciliation).
5. **If invalid:** the claim is published to `invalid-claims`, written to BigQuery (`validated_claims`, `is_valid=false`), and routed to the DLQ processor (retry, manual review, or reject).
6. **If valid:** the claim is enriched — member risk score (BigQuery lookup), provider specialty (Cloud SQL lookup), code cross-validation against ICD-10/CPT reference tables, fraud flags, quality flags, and a deterministic idempotency key.
7. The enriched, validated claim is written to BigQuery (`validated_claims`, `is_valid=true`) and published to `valid-claims`.
8. If fraud flags are present, an alert is published to `claims-alerts`.
9. A separate Dataflow streaming job subscribes to `valid-claims-sub`, windows claims into 30-second fixed windows per member, computes claim count and spend, flags simple volume/spend anomalies, writes to BigQuery (`member_claim_aggregates`), and publishes anomaly alerts to `claims-alerts`.

## Design Priorities

- Stateless compute for the Cloud Function stage
- Idempotent event processing (deterministic idempotency key)
- Structured logs
- Config-driven healthcare validation rules
- Least-privilege IAM (separate service accounts for the validation function and the Dataflow worker)
- BigQuery-first analytics output, partitioned and clustered for query performance
- Validation and aggregation as decoupled stages connected only by Pub/Sub topics, so either can be redeployed or scaled independently

## Known Limitations (disclosed, not hidden)

- The Dataflow stage is a separate deploy target from the Cloud Function stage; this repo does not orchestrate a single combined deployment — see `deployment_guide.md`.
- Enrichment lookups (member risk score, provider specialty, code cross-validation) require live BigQuery and Cloud SQL connectivity in production. Locally, these are exercised through dependency injection in unit tests rather than a live database — `docker-compose.yml` provides a local Postgres instance for integration testing if desired.
- Test coverage threshold is set to 80% (not 85%) in `pyproject.toml` to reflect the larger integration surface added by the merge (SQLAlchemy/BigQuery fallback branches in `src/enrichment.py` are harder to exercise without live infrastructure).
