variable "project_id" {
  description = "GCP project ID."
  type        = string
}

variable "region" {
  description = "GCP region for regional resources."
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "Deployment environment (dev, staging, prod)."
  type        = string
  default     = "dev"
}

variable "bigquery_dataset" {
  description = "BigQuery dataset for claims validation, enrichment, and aggregation."
  type        = string
  default     = "claims_analytics"
}
