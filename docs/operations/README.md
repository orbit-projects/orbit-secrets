# Operations

Register one adapter explicitly and close it as part of application shutdown. Use workload identity where available. Do not place credentials in source, command-line arguments, package defaults, logs, traces, metric labels, or exception messages.

Secret payloads are bounded to 1 MiB. Requests use finite adapter timeouts and concurrency caps. SDK retry behavior is provider-specific and bounded by configuration or documented SDK defaults. Caller cancellation is propagated; adapters do not retry cancellation.

Rotation is pull-based in v1: call `refresh()` at an application-controlled safe point, validate the returned version, then update dependent resources using their own transactional/drain behavior. The previous value cannot be erased from Python memory. Do not assume a version switch is atomic across a pool or cluster.

Run fake-client tests without credentials. Live checks should use a dedicated non-production secret, a least-privilege identity, and a cleanup plan; record provider and SDK versions.
