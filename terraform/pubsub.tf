resource "google_pubsub_topic" "incoming_claims" {
  name                       = "incoming-claims"
  message_retention_duration = "86600s"
}

resource "google_pubsub_topic" "valid_claims" {
  name                       = "valid-claims"
  message_retention_duration = "86600s"
}

resource "google_pubsub_topic" "invalid_claims" {
  name                       = "invalid-claims"
  message_retention_duration = "604800s"
}

resource "google_pubsub_topic" "retry_claims" {
  name = "retry-claims"
}

resource "google_pubsub_topic" "manual_review_claims" {
  name = "manual-review-claims"
}

resource "google_pubsub_topic" "rejected_claims" {
  name = "rejected-claims"
}

resource "google_pubsub_topic" "alerts" {
  name                       = "claims-alerts"
  message_retention_duration = "604800s"
}

# Triggers the validate_and_enrich_claim Cloud Function
resource "google_pubsub_subscription" "incoming_claims_sub" {
  name  = "incoming-claims-sub"
  topic = google_pubsub_topic.incoming_claims.name

  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.invalid_claims.id
    max_delivery_attempts = 5
  }
}

resource "google_pubsub_subscription" "invalid_claims_sub" {
  name  = "invalid-claims-sub"
  topic = google_pubsub_topic.invalid_claims.name
}

# Consumed by the Dataflow aggregation job
resource "google_pubsub_subscription" "valid_claims_sub" {
  name  = "valid-claims-sub"
  topic = google_pubsub_topic.valid_claims.name

  ack_deadline_seconds       = 20
  message_retention_duration = "86600s"
}

resource "google_pubsub_subscription" "alerts_sub" {
  name  = "claims-alerts-sub"
  topic = google_pubsub_topic.alerts.name
}
