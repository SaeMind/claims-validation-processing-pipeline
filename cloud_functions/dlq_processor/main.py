"""Cloud Function for invalid-claims dead letter queue processing."""

import json
import logging
from typing import Any

import functions_framework
from google.cloud import pubsub_v1

from src.config import SETTINGS
from src.error_handlers import DLQAction, DLQProcessor
from src.logging_config import configure_logging
from src.utils import decode_pubsub_message

configure_logging(SETTINGS.log_level)
logger = logging.getLogger(__name__)
publisher = pubsub_v1.PublisherClient()


def _topic_for_action(action: DLQAction) -> str:
    """Map DLQ action to configured Pub/Sub topic."""
    if action == DLQAction.RETRY:
        return SETTINGS.retry_claims_topic
    if action == DLQAction.REJECT:
        return SETTINGS.rejected_claims_topic
    return SETTINGS.manual_review_topic


def _publish(topic: str, payload: dict[str, Any]) -> str:
    """Publish routed DLQ payload to Pub/Sub."""
    future = publisher.publish(
        publisher.topic_path(SETTINGS.gcp_project_id, topic),
        json.dumps(payload, default=str).encode("utf-8"),
    )
    return str(future.result())


@functions_framework.cloud_event
def process_invalid_claim(cloud_event: Any) -> None:
    """
    Process an invalid claim result and route to retry, manual review, or reject topic.

    Parameters:
        cloud_event: Pub/Sub CloudEvent containing validation failure payload.

    Returns:
        None.
    """
    payload = decode_pubsub_message(cloud_event.data)
    errors = payload.get("errors", [])
    warnings = payload.get("warnings", [])
    decision = DLQProcessor().categorize(errors=errors, warnings=warnings)
    payload["dlq_decision"] = {"action": decision.action.value, "reason": decision.reason}
    topic = _topic_for_action(decision.action)
    message_id = _publish(topic, payload)
    logger.info(
        "dlq_routed",
        extra={
            "context": {
                "claim_id": payload.get("claim_id"),
                "action": decision.action.value,
                "topic": topic,
                "message_id": message_id,
            }
        },
    )
