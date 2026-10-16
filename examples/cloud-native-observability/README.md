# Secret lookup with correlated OpenTelemetry

This consumer example composes the provider-neutral `orbit-secrets` contract with Core's ASGI
runtime and the separate tracing, logging, and metrics adapters. The route returns a secret's
immutable version only. The value is never placed in the response, logs, spans, or metric labels.

## Local integration check

From this directory, install the neighboring workspace packages in editable mode, along with the
example's declared dependencies and test extra. Then run `pytest`. The integration test injects a
fake secret provider and in-memory exporters, starts the real Core ASGI lifespan, sends a request,
and checks provider cleanup, version-only output, trace/span correlation on logs, and trace-linked
metric exemplars. It does not need cloud credentials or a telemetry collector.

## Provider-backed deployment

Install one provider extra (`aws`, `gcp`, or `azure`) and construct its adapter from workload
identity. Install `orbit-tracing[otlp-http]` and the matching OTLP exporters, then pass those
exporters and the provider into `create_app`. Keep collector endpoints and TLS policy in the
deployment environment. The example deliberately does not select credentials, disable certificate
verification, or configure a process-global OpenTelemetry provider. Use Uvicorn for development
and Gunicorn with Uvicorn workers for production, as described in the Core hosting documentation.

The offline integration test proves local composition and correlation only. A non-production
cloud account, least-privilege provider policy, live collector, workload identity, and deployment
shutdown behavior remain release validation gates.
