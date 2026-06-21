resource "google_bigquery_dataset" "claims_analytics" {
  dataset_id                 = var.bigquery_dataset
  location                   = "US"
  delete_contents_on_destroy = false
}

resource "google_bigquery_table" "validated_claims" {
  dataset_id          = google_bigquery_dataset.claims_analytics.dataset_id
  table_id            = "validated_claims"
  deletion_protection = true

  time_partitioning {
    type  = "DAY"
    field = "processed_at"
  }

  clustering = ["member_id", "provider_npi", "service_date"]

  schema = jsonencode([
    { name = "claim_id", type = "STRING", mode = "REQUIRED" },
    { name = "member_id", type = "STRING", mode = "REQUIRED" },
    { name = "provider_npi", type = "STRING", mode = "REQUIRED" },
    { name = "service_date", type = "DATE", mode = "REQUIRED" },
    { name = "amount", type = "FLOAT", mode = "REQUIRED" },
    { name = "codes", type = "STRING", mode = "REPEATED" },
    { name = "is_valid", type = "BOOLEAN", mode = "REQUIRED" },
    { name = "status", type = "STRING", mode = "REQUIRED" },
    { name = "errors", type = "STRING", mode = "REPEATED" },
    { name = "warnings", type = "STRING", mode = "REPEATED" },
    { name = "confidence", type = "FLOAT", mode = "REQUIRED" },
    { name = "validation_latency_ms", type = "FLOAT", mode = "REQUIRED" },
    { name = "valid_codes", type = "STRING", mode = "REPEATED" },
    { name = "invalid_codes", type = "STRING", mode = "REPEATED" },
    { name = "member_risk_score", type = "FLOAT", mode = "NULLABLE" },
    { name = "provider_specialty", type = "STRING", mode = "NULLABLE" },
    { name = "fraud_flags", type = "STRING", mode = "REPEATED" },
    { name = "quality_flags", type = "STRING", mode = "REPEATED" },
    { name = "idempotency_key", type = "STRING", mode = "NULLABLE" },
    { name = "event_received_at", type = "TIMESTAMP", mode = "NULLABLE" },
    { name = "processed_at", type = "TIMESTAMP", mode = "REQUIRED" },
    { name = "processing_latency_ms", type = "INTEGER", mode = "NULLABLE" }
  ])
}

resource "google_bigquery_table" "member_claim_aggregates" {
  dataset_id          = google_bigquery_dataset.claims_analytics.dataset_id
  table_id            = "member_claim_aggregates"
  deletion_protection = true

  time_partitioning {
    type  = "DAY"
    field = "aggregated_at"
  }

  clustering = ["member_id"]

  schema = jsonencode([
    { name = "member_id", type = "STRING", mode = "REQUIRED" },
    { name = "window_start", type = "TIMESTAMP", mode = "REQUIRED" },
    { name = "window_end", type = "TIMESTAMP", mode = "REQUIRED" },
    { name = "claim_count", type = "INTEGER", mode = "REQUIRED" },
    { name = "member_window_spend", type = "FLOAT", mode = "REQUIRED" },
    { name = "anomaly_flags", type = "STRING", mode = "REPEATED" },
    { name = "aggregated_at", type = "TIMESTAMP", mode = "REQUIRED" }
  ])
}
