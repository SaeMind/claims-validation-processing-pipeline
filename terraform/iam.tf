resource "google_service_account" "claims_validator" {
  account_id   = "claims-validator-sa"
  display_name = "Claims Validation & Enrichment Cloud Function Service Account"
}

resource "google_project_iam_member" "validator_pubsub_publisher" {
  project = var.project_id
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${google_service_account.claims_validator.email}"
}

resource "google_project_iam_member" "validator_pubsub_subscriber" {
  project = var.project_id
  role    = "roles/pubsub.subscriber"
  member  = "serviceAccount:${google_service_account.claims_validator.email}"
}

resource "google_project_iam_member" "validator_bigquery_data_editor" {
  project = var.project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${google_service_account.claims_validator.email}"
}

resource "google_project_iam_member" "validator_cloudsql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.claims_validator.email}"
}

resource "google_project_iam_member" "validator_log_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.claims_validator.email}"
}

resource "google_service_account" "dataflow_worker" {
  account_id   = "claims-dataflow-worker-sa"
  display_name = "Claims Aggregation Dataflow Worker Service Account"
}

resource "google_project_iam_member" "dataflow_worker_role" {
  project = var.project_id
  role    = "roles/dataflow.worker"
  member  = "serviceAccount:${google_service_account.dataflow_worker.email}"
}

resource "google_project_iam_member" "dataflow_pubsub_subscriber" {
  project = var.project_id
  role    = "roles/pubsub.subscriber"
  member  = "serviceAccount:${google_service_account.dataflow_worker.email}"
}

resource "google_project_iam_member" "dataflow_pubsub_publisher" {
  project = var.project_id
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${google_service_account.dataflow_worker.email}"
}

resource "google_project_iam_member" "dataflow_bigquery_data_editor" {
  project = var.project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${google_service_account.dataflow_worker.email}"
}
