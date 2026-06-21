terraform {
  required_version = ">= 1.6.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.45"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

resource "google_storage_bucket" "function_source" {
  name                        = "${var.project_id}-${var.environment}-claims-functions-source"
  location                    = var.region
  uniform_bucket_level_access = true
}

resource "google_storage_bucket" "dataflow_staging" {
  name                        = "${var.project_id}-${var.environment}-claims-dataflow-staging"
  location                    = var.region
  uniform_bucket_level_access = true
}
