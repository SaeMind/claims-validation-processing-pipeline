"""Apache Beam Dataflow pipeline for member-level claim aggregation.

Consumes the valid_claims_topic subscription, which receives only claims that
have already passed deep validation and enrichment in
cloud_functions/validate_and_enrich_claim. Aggregates spend and claim volume
per member in 30-second fixed windows and flags simple volume/spend anomalies.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Iterable
from datetime import datetime, timezone
from typing import Any

import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions, SetupOptions
from apache_beam.transforms import window

from src.config import SETTINGS


class ParseClaimMessage(beam.DoFn):
    """Parse a Pub/Sub message into a claim dictionary."""

    def process(self, message: bytes) -> Iterable[dict[str, Any]]:
        """Yield parsed claim dictionaries from raw Pub/Sub messages."""
        try:
            claim = json.loads(message.decode("utf-8"))
            if isinstance(claim, dict):
                yield claim
        except json.JSONDecodeError:
            return


class ToMemberKey(beam.DoFn):
    """Convert claim dictionaries to keyed member aggregation records."""

    def process(self, claim: dict[str, Any]) -> Iterable[tuple[str, dict[str, Any]]]:
        """Yield member-keyed aggregation values."""
        member_id = str(claim.get("member_id", "UNKNOWN"))
        amount = float(claim.get("amount", 0.0))
        yield member_id, {
            "member_id": member_id,
            "claim_id": claim.get("claim_id"),
            "amount": amount,
            "service_date": claim.get("service_date"),
            "fraud_flags": claim.get("fraud_flags", []),
        }


class BuildMemberAggregate(beam.DoFn):
    """Build member spend and volume aggregates for a fixed window."""

    def process(
        self,
        element: tuple[str, Iterable[dict[str, Any]]],
        window_param: beam.DoFn.WindowParam = beam.DoFn.WindowParam,
    ) -> Iterable[dict[str, Any]]:
        """Yield one aggregate row per member per Beam window."""
        member_id, claims_iterable = element
        claims = list(claims_iterable)
        total_spend = sum(float(claim.get("amount", 0.0)) for claim in claims)
        claim_count = len(claims)
        anomaly_flags = []
        if claim_count >= 10:
            anomaly_flags.append("UNUSUAL_30_SECOND_CLAIM_VOLUME")
        if total_spend >= 25000:
            anomaly_flags.append("HIGH_30_SECOND_MEMBER_SPEND")

        yield {
            "member_id": member_id,
            "window_start": window_param.start.to_utc_datetime().isoformat(),
            "window_end": window_param.end.to_utc_datetime().isoformat(),
            "claim_count": claim_count,
            "member_window_spend": round(total_spend, 2),
            "anomaly_flags": anomaly_flags,
            "aggregated_at": datetime.now(timezone.utc).isoformat(),
        }


class AlertAnomalies(beam.DoFn):
    """Create Pub/Sub alert payloads for anomalous member aggregates."""

    def process(self, aggregate: dict[str, Any]) -> Iterable[bytes]:
        """Yield encoded alert payloads when an aggregate has anomaly flags."""
        if not aggregate.get("anomaly_flags"):
            return
        alert = {
            "alert_type": "MEMBER_AGGREGATION_ANOMALY",
            "member_id": aggregate["member_id"],
            "claim_count": aggregate["claim_count"],
            "member_window_spend": aggregate["member_window_spend"],
            "anomaly_flags": aggregate["anomaly_flags"],
            "window_start": aggregate["window_start"],
            "window_end": aggregate["window_end"],
            "alert_created_at": datetime.now(timezone.utc).isoformat(),
        }
        yield json.dumps(alert).encode("utf-8")


def build_pipeline(pipeline: beam.Pipeline, args: argparse.Namespace) -> None:
    """Build the Beam graph for windowed member claim aggregation."""
    input_subscription = f"projects/{SETTINGS.gcp_project_id}/subscriptions/{args.input_subscription}"
    aggregate_table = f"{SETTINGS.gcp_project_id}:{SETTINGS.bigquery_dataset}.{args.aggregate_table}"
    alerts_topic = f"projects/{SETTINGS.gcp_project_id}/topics/{SETTINGS.alerts_topic}"

    parsed_claims = (
        pipeline
        | "ReadValidClaims" >> beam.io.ReadFromPubSub(subscription=input_subscription)
        | "ParseClaimMessage" >> beam.ParDo(ParseClaimMessage())
    )

    aggregates = (
        parsed_claims
        | "WindowIntoThirtySeconds" >> beam.WindowInto(window.FixedWindows(30))
        | "KeyByMember" >> beam.ParDo(ToMemberKey())
        | "GroupByMember" >> beam.GroupByKey()
        | "BuildMemberAggregate" >> beam.ParDo(BuildMemberAggregate())
    )

    _ = (
        aggregates
        | "WriteAggregatesToBigQuery"
        >> beam.io.WriteToBigQuery(
            aggregate_table,
            schema=get_aggregate_schema(),
            write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND,
            create_disposition=beam.io.BigQueryDisposition.CREATE_IF_NEEDED,
        )
    )

    _ = (
        aggregates
        | "BuildAnomalyAlerts" >> beam.ParDo(AlertAnomalies())
        | "PublishAnomalyAlerts" >> beam.io.WriteToPubSub(alerts_topic)
    )


def get_aggregate_schema() -> dict[str, Any]:
    """Return BigQuery schema for member claim aggregation output."""
    return {
        "fields": [
            {"name": "member_id", "type": "STRING", "mode": "REQUIRED"},
            {"name": "window_start", "type": "TIMESTAMP", "mode": "REQUIRED"},
            {"name": "window_end", "type": "TIMESTAMP", "mode": "REQUIRED"},
            {"name": "claim_count", "type": "INTEGER", "mode": "REQUIRED"},
            {"name": "member_window_spend", "type": "FLOAT", "mode": "REQUIRED"},
            {"name": "anomaly_flags", "type": "STRING", "mode": "REPEATED"},
            {"name": "aggregated_at", "type": "TIMESTAMP", "mode": "REQUIRED"},
        ]
    }


def parse_args() -> argparse.Namespace:
    """Parse Dataflow pipeline command-line arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input_subscription",
        default="valid-claims-sub",
        help="Pub/Sub subscription receiving validated, enriched claims.",
    )
    parser.add_argument(
        "--aggregate_table",
        default=SETTINGS.bigquery_aggregate_table,
        help="BigQuery table name for aggregate output.",
    )
    known_args, pipeline_args = parser.parse_known_args()
    known_args.pipeline_args = pipeline_args
    return known_args


def run() -> None:
    """Run the Beam pipeline using parsed command-line options."""
    args = parse_args()
    pipeline_options = PipelineOptions(args.pipeline_args, save_main_session=True)
    pipeline_options.view_as(SetupOptions).save_main_session = True
    with beam.Pipeline(options=pipeline_options) as pipeline:
        build_pipeline(pipeline, args)


if __name__ == "__main__":
    run()
