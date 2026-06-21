from src.error_handlers import DLQAction, DLQProcessor


def test_amount_mismatch_routes_to_manual_review() -> None:
    decision = DLQProcessor().categorize(["Total amount mismatch: procedures sum to 10"])
    assert decision.action == DLQAction.MANUAL_REVIEW


def test_missing_data_routes_to_retry() -> None:
    decision = DLQProcessor().categorize(["Claim has no diagnoses"])
    assert decision.action == DLQAction.RETRY
