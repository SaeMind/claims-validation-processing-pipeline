# Deployment Guide

## Prerequisites

- GCP project with billing enabled
- Python 3.11+
- Terraform 1.6+
- gcloud CLI authenticated

## 1. Configure environment

```bash
export PROJECT_ID="my-healthcare-project"
export REGION="us-central1"
gcloud config set project "$PROJECT_ID"
```

## 2. Enable APIs

```bash
gcloud services enable \
  cloudfunctions.googleapis.com \
  pubsub.googleapis.com \
  bigquery.googleapis.com \
  dataflow.googleapis.com \
  sqladmin.googleapis.com \
  logging.googleapis.com \
  monitoring.googleapis.com \
  cloudbuild.googleapis.com \
  storage.googleapis.com
```

## 3. Deploy infrastructure

```bash
cd terraform
terraform init
terraform plan -var="project_id=$PROJECT_ID" -var="region=$REGION" -out=tfplan
terraform apply tfplan
```

## 4. Deploy the validation & enrichment function

```bash
gcloud functions deploy validate-and-enrich-claim \
  --gen2 \
  --runtime=python311 \
  --region="$REGION" \
  --source=. \
  --entry-point=validate_and_enrich_claim \
  --trigger-topic=incoming-claims \
  --service-account="claims-validator-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --set-env-vars=GCP_PROJECT_ID="$PROJECT_ID",ENABLE_BIGQUERY=true,ENABLE_PUBSUB_PUBLISH=true
```

## 5. Deploy the DLQ processor

```bash
gcloud functions deploy process-invalid-claim \
  --gen2 \
  --runtime=python311 \
  --region="$REGION" \
  --source=. \
  --entry-point=process_invalid_claim \
  --trigger-topic=invalid-claims \
  --service-account="claims-validator-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --set-env-vars=GCP_PROJECT_ID="$PROJECT_ID"
```

## 6. Launch the Dataflow aggregation job

This is a separate deploy target from the two Cloud Functions above — it runs
continuously, consuming already-validated claims from `valid-claims-sub`.

```bash
python src/dataflow_pipeline.py \
  --runner=DataflowRunner \
  --project="$PROJECT_ID" \
  --region="$REGION" \
  --temp_location="gs://${PROJECT_ID}-dev-claims-dataflow-staging/temp" \
  --staging_location="gs://${PROJECT_ID}-dev-claims-dataflow-staging/staging" \
  --service_account_email="claims-dataflow-worker-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --input_subscription=valid-claims-sub \
  --aggregate_table=member_claim_aggregates
```

## 7. Publish a test claim

```bash
gcloud pubsub topics publish incoming-claims --message='{
  "claim_id":"CLM-001",
  "member_id":"MEM123456",
  "provider_npi":"1234567893",
  "date_of_service":"2026-06-15",
  "total_amount":150.00,
  "procedures":[{"procedure_code":"99213","units":1,"amount":150.00}],
  "diagnoses":[{"icd10_code":"I10","primary":true}],
  "place_of_service":"11"
}'
```

## 8. Monitor

```bash
gcloud functions logs read validate-and-enrich-claim --region="$REGION" --limit=50
bq query --use_legacy_sql=false 'SELECT status, is_valid, COUNT(*) FROM `claims_analytics.validated_claims` GROUP BY status, is_valid'
bq query --use_legacy_sql=false 'SELECT member_id, claim_count, member_window_spend, anomaly_flags FROM `claims_analytics.member_claim_aggregates` WHERE ARRAY_LENGTH(anomaly_flags) > 0 ORDER BY aggregated_at DESC LIMIT 20'
```
