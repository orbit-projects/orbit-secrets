# Security

Resolved secret values are highly sensitive. `SecretValue.__repr__` omits payload bytes and equality does not compare payloads. `reveal()` and `reveal_text()` are explicit disclosure operations. Python immutable values cannot be reliably zeroized; never retain revealed values longer than needed.

The capability does not redact arbitrary application logs. Never add secrets to log messages, exception messages, trace attributes, metric names or labels, URLs, or support bundles. Adapters discard raw provider exceptions, request/response bodies, and secret text.

Use provider workload identity and grant only read access to required resources and versions. Keep TLS certificate verification enabled. Treat secret names as potentially sensitive metadata even though they are not secret payloads. Do not expose version identifiers or resource names in public endpoints without a need.

Report vulnerabilities privately through the configured repository security channel. The alpha API has no stable-release or response-time commitment.
