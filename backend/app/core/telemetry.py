"""Disable Chroma event delivery without invoking incompatible PostHog APIs."""

from chromadb.telemetry.product import ProductTelemetryClient, ProductTelemetryEvent
from overrides import override


class DisabledProductTelemetry(ProductTelemetryClient):
    """Explicit opt-out implementation for Chroma's telemetry interface."""

    @override
    def capture(self, event: ProductTelemetryEvent) -> None:
        return None
