# Copyright 2026-present Orbit Contributors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Exercise secret redaction, lifecycle, and cross-signal trace correlation."""

from __future__ import annotations

from app import create_app
from opentelemetry.sdk._logs.export import InMemoryLogRecordExporter
from opentelemetry.sdk.metrics.export import MetricExporter, MetricExportResult
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from orbit_testing import TestClient

from orbit_secrets import SecretReference, SecretValue


class _FakeSecretProvider:
    """Provide one known sensitive value and record explicit lifecycle cleanup."""

    def __init__(self) -> None:
        self.closed = False

    async def resolve(self, reference: SecretReference) -> SecretValue:
        assert reference.name == "demo/application-key"
        return SecretValue(b"integration-secret-must-not-leak", "version-7")

    async def refresh(self, reference: SecretReference) -> SecretValue:
        return await self.resolve(reference)

    async def aclose(self) -> None:
        self.closed = True


class _InMemoryMetricExporter(MetricExporter):
    """Capture immutable exported metric data for correlation assertions."""

    def __init__(self) -> None:
        super().__init__()
        self.items: list[object] = []

    def export(
        self, metrics_data: object, timeout_millis: float = 10_000, **kwargs: object
    ) -> MetricExportResult:
        self.items.append(metrics_data)
        return MetricExportResult.SUCCESS

    def force_flush(self, timeout_millis: float = 10_000) -> bool:
        return True

    def shutdown(self, timeout_millis: float = 30_000, **kwargs: object) -> None:
        return None


async def test_secret_request_exports_correlated_signals_without_value() -> None:
    provider = _FakeSecretProvider()
    spans = InMemorySpanExporter()
    logs = InMemoryLogRecordExporter()
    metrics = _InMemoryMetricExporter()
    asgi, _tracing = create_app(
        provider,
        span_exporter=spans,
        log_exporter=logs,
        metric_exporter=metrics,
    )

    async with TestClient(asgi) as client:
        response = await client.request("GET", "/secret-version")

    assert response.status == 200
    assert response.json() == {"version": "version-7"}
    assert b"integration-secret-must-not-leak" not in response.body
    assert provider.closed

    exported_spans = spans.get_finished_spans()
    assert len(exported_spans) == 1
    span_context = exported_spans[0].context
    assert span_context is not None
    trace_id = f"{span_context.trace_id:032x}"
    span_id = f"{span_context.span_id:016x}"

    exported_logs = logs.get_finished_logs()
    assert len(exported_logs) == 1
    log = exported_logs[0].log_record
    log_attributes = dict(log.attributes or {})
    assert log_attributes["orbit.trace.id"] == trace_id
    assert log_attributes["orbit.span.id"] == span_id
    assert b"integration-secret-must-not-leak" not in str(log).encode()
    assert b"integration-secret-must-not-leak" not in str(log_attributes).encode()

    metric_points = [
        point
        for data in metrics.items
        for resource in data.resource_metrics
        for scope in resource.scope_metrics
        for metric in scope.metrics
        for point in metric.data.data_points
    ]
    assert metric_points
    assert any(
        exemplar.trace_id == span_context.trace_id and exemplar.span_id == span_context.span_id
        for point in metric_points
        for exemplar in point.exemplars
    )
    assert all(
        "integration-secret-must-not-leak" not in str(point.attributes) for point in metric_points
    )
