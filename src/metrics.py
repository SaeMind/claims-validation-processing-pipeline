"""OpenTelemetry metrics and tracing utilities."""

from contextlib import contextmanager
from time import perf_counter
from typing import Iterator
from opentelemetry import metrics, trace

_meter = metrics.get_meter("serverless_claims_validation")
_tracer = trace.get_tracer("serverless_claims_validation")

validation_counter = _meter.create_counter(
    "claims.validation.count",
    description="Number of claim validations by outcome.",
)
validation_latency = _meter.create_histogram(
    "claims.validation.latency_ms",
    description="Claim validation latency in milliseconds.",
)

def record_validation(status: str, latency_ms: float) -> None:
    """
    Record validation counter and latency metrics.

    Parameters:
        status: Validation status.
        latency_ms: Elapsed validation time.

    Returns:
        None.
    """
    attrs = {"status": status}
    validation_counter.add(1, attrs)
    validation_latency.record(latency_ms, attrs)


@contextmanager
def traced_span(name: str) -> Iterator[None]:
    """
    Create an OpenTelemetry span context.

    Parameters:
        name: Span name.

    Returns:
        Iterator yielding control to wrapped block.
    """
    with _tracer.start_as_current_span(name):
        yield


@contextmanager
def timer() -> Iterator[callable]:
    """
    Measure elapsed time in milliseconds.

    Parameters:
        None.

    Returns:
        Callable returning elapsed milliseconds.
    """
    start = perf_counter()
    yield lambda: (perf_counter() - start) * 1000
