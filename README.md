# Claims Validation & Processing Pipeline

A production-style, serverless healthcare claims pipeline for Clinical Data
Science, Healthcare Data Engineering, and Real-World Evidence portfolios. The
pipeline validates incoming claim events against coding and business rules,
enriches valid claims with risk and provider context, flags potential fraud,
and aggregates member-level spend in near real time.

> **Provenance note:** this repository merges two originally separate
> portfolio builds — *Serverless Claims Validation Pipeline (Cloud
> Functions)* and *Pub/Sub Event-Driven Claims Processing Pipeline* — into
> one pipeline, because they shared the same domain, the same default
> Pub/Sub topic naming, and a naturally sequential relationship (validate,
> then enrich and aggregate). See `docs/architecture.md` for the full
> rationale and event flow.

## What this demonstrates

- Pydantic V2 schema validation for healthcare claim structure
- Rules-based validation: CPT/HCPCS syntax, ICD-10-CM syntax, NPI checksum, medical necessity, frequency limits, amount reconciliation
- Enrichment: member risk scoring, provider specialty lookup, reference-table code cross-validation
- Rule-based fraud and data-quality flagging
- Dead-letter queue routing (retry / manual review / reject)
- Streaming member-level aggregation with Apache Beam / Dataflow (30-second fixed windows)
- BigQuery as the analytics sink, partitioned and clustered for query performance
- Infrastructure as code (Terraform) with least-privilege, per-stage service accounts
- CI (lint, type-check, test, coverage gate) via GitHub Actions

## Architecture

```
Pub/Sub (incoming-claims)
        |
        v
validate_and_enrich_claim (Cloud Function)
        |
        +-- INVALID --> invalid-claims --> dlq_processor --> retry / manual-review / rejected
        |
        +-- VALID --> enrich --> valid-claims --> Dataflow (30s member aggregation) --> BigQuery
        |                                                                            \-> claims-alerts (anomalies)
        +-- BigQuery (validated_claims: one audit row per claim, valid or invalid)
        |
        +-- claims-alerts (if fraud flags present)
```

Full event-by-event flow: `docs/architecture.md`.

## Repository layout

```
src/                          Shared validation, enrichment, and aggregation logic
  config.py                   Merged runtime settings
  schemas.py                  Pydantic ClaimRecord / ValidationResult models
  claim_validator.py          Business rules engine (deep validation)
  cpt_validator.py, icd10_validator.py, npi_validator.py
  enrichment.py                Member risk, provider lookup, fraud/quality flags
  bigquery_writer.py           Unified BigQuery row writer
  dataflow_pipeline.py          Apache Beam aggregation job
  error_handlers.py             DLQ categorization logic
cloud_functions/
  validate_and_enrich_claim/   Merged validation + enrichment entry point
  dlq_processor/                Dead-letter routing entry point
terraform/                     Pub/Sub, BigQuery, IAM, monitoring, storage
tests/                          Unit tests (validators, enrichment, DLQ, Dataflow DoFns)
docs/architecture.md            Event flow and design priorities
deployment_guide.md             Step-by-step GCP deployment
```

## Running tests locally

```bash
pip install -r requirements.txt
pytest
```

Tests that require `apache-beam` are automatically skipped if it isn't
installed, so the validation/enrichment/DLQ test suite runs independently of
the heavier Dataflow dependency.

## Running locally with docker-compose

```bash
docker compose up
```

This starts a Pub/Sub emulator, a local Postgres instance (provider reference
data), the validation function on port 8080, and a one-shot test runner.

## Deployment

See `deployment_guide.md` for the full GCP deployment sequence: Terraform
infrastructure, both Cloud Functions, and the Dataflow streaming job.

## Data note

This is a portfolio artifact. All sample claim payloads, validation rules,
and reference tables are illustrative. No protected health information (PHI)
is included anywhere in this repository. Before quoting any performance
metric from this project on a resume or in a preprint, run it against real or
synthetic data and disclose the data source, per standard credibility
practice for portfolio artifacts.
