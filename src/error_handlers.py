"""Dead letter queue processing and error categorization."""

from dataclasses import dataclass
from enum import Enum


class DLQAction(str, Enum):
    """Supported DLQ routing actions."""

    RETRY = "retry"
    MANUAL_REVIEW = "manual_review"
    REJECT = "reject"


@dataclass(frozen=True)
class DLQDecision:
    """Decision output from DLQ processing."""

    action: DLQAction
    reason: str


class DLQProcessor:
    """Categorize invalid claim events for retry, manual review, or rejection."""

    def categorize(self, errors: list[str], warnings: list[str] | None = None) -> DLQDecision:
        """
        Categorize validation failures.

        Parameters:
            errors: Validation error messages.
            warnings: Optional warning messages.

        Returns:
            DLQDecision with routing action and reason.
        """
        normalized = " ".join(errors).lower()
        if "invalid npi" in normalized or "invalid icd" in normalized or "invalid cpt" in normalized:
            return DLQDecision(DLQAction.REJECT, "Non-correctable code or provider identifier syntax failure")
        if "total amount mismatch" in normalized or "exceeds threshold" in normalized:
            return DLQDecision(DLQAction.MANUAL_REVIEW, "Financial discrepancy requires analyst review")
        if "no diagnoses" in normalized or "no procedures" in normalized:
            return DLQDecision(DLQAction.RETRY, "Missing data may be resolvable by upstream replay")
        return DLQDecision(DLQAction.MANUAL_REVIEW, "Unclassified validation failure")
