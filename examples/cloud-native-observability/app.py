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
"""Compose a secret provider with isolated OpenTelemetry signal exporters."""

from __future__ import annotations

import logging
from typing import Any

from opentelemetry.sdk._logs.export import LogRecordExporter
from opentelemetry.sdk.metrics.export import MetricExporter
from opentelemetry.sdk.trace.export import SpanExporter
from orbit import Application, ApplicationConfig
from orbit.asgi import Response
from orbit.plugins import Plugin, PluginMetadata
from orbit.runtime import Runtime
from orbit_logging_opentelemetry import OpenTelemetryLoggingConfig, OpenTelemetryLoggingPlugin
from orbit_metrics_opentelemetry import OpenTelemetryMetricsConfig, OpenTelemetryMetricsPlugin
from orbit_tracing import OpenTelemetryConfig, OpenTelemetryPlugin

from orbit_secrets import SecretProvider, SecretReference

_LOG = logging.getLogger("orbit.example.secret-lookup")


class _SecretProviderLifecycle(Plugin):
    """Tie an application-owned secret provider's client cleanup to Core shutdown."""

    metadata = PluginMetadata(
        name="orbit-example-secret-provider-lifecycle",
        version="0.1.0",
        capabilities=frozenset({"secrets.resolve"}),
    )

    def __init__(self, provider: SecretProvider) -> None:
        """Retain the explicitly selected provider for the application lifetime."""
        self._provider = provider
        self._closed = False

    async def activate(self) -> None:
        """Keep provider construction lazy; adapters open clients on first use."""

    async def deactivate(self) -> None:
        """Close provider-owned SDK clients once during orderly application shutdown."""
        if not self._closed:
            self._closed = True
            await self._provider.aclose()


def create_app(
    provider: SecretProvider,
    *,
    span_exporter: SpanExporter,
    log_exporter: LogRecordExporter,
    metric_exporter: MetricExporter,
) -> tuple[Any, OpenTelemetryPlugin]:
    """Build an ASGI application whose signals share Orbit request and trace context.

    The response intentionally contains only the immutable secret version. Secret bytes remain
    inside the route and are never passed to logs, spans, metric attributes, or HTTP output.
    Exporters and the provider are injected so applications control credentials, transport,
    endpoint policy, and process configuration.
    """
    application = Application(ApplicationConfig(name="secret-demo"))
    # The named application logger must allow INFO records to reach its owned export handler.
    _LOG.setLevel(logging.INFO)
    secret_resolutions = application.diagnostics.metrics.counter("orbit_secret_resolutions_total")
    application.register_plugin(_SecretProviderLifecycle(provider))
    tracing = OpenTelemetryPlugin(
        OpenTelemetryConfig(service_name="secret-demo"), exporter=span_exporter
    )
    application.register_plugin(tracing)
    application.register_plugin(
        OpenTelemetryLoggingPlugin(
            OpenTelemetryLoggingConfig(
                service_name="secret-demo", logger_name=_LOG.name, schedule_delay_millis=50
            ),
            exporter=log_exporter,
            logger=_LOG,
        )
    )
    application.register_plugin(
        OpenTelemetryMetricsPlugin(
            OpenTelemetryMetricsConfig(service_name="secret-demo", export_interval_millis=100),
            exporter=metric_exporter,
        )
    )

    @application.router.route("/secret-version", method="GET", name="secret-version")
    async def secret_version(_request: Any) -> Response:
        """Resolve a current secret version without returning or logging its value."""
        value = await provider.resolve(SecretReference(name="demo/application-key"))
        secret_resolutions.inc()
        _LOG.info("Resolved application secret version")
        return Response.json({"version": value.version})

    runtime = Runtime(application, tracer=tracing)
    return tracing.wrap_asgi(runtime), tracing


__all__ = ["create_app"]
