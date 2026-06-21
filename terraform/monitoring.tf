resource "google_monitoring_dashboard" "claims_validation" {
  dashboard_json = jsonencode({
    displayName = "Claims Validation Operations"
    gridLayout = {
      columns = 2
      widgets = [
        {
          title = "Validation Logs"
          text = { content = "Monitor claim validation throughput, invalid claim rate, DLQ routing, and BigQuery persistence failures." }
        }
      ]
    }
  })
}
