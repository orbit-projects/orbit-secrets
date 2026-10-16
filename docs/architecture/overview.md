# Architecture

The capability package owns only provider-neutral identifiers, values, errors, and lifecycle methods. It has no Core dependency and imports no cloud SDK. Each adapter maps its provider's current/versioned read semantics into `SecretValue`.

## Resolution model

- `SecretReference.name` names one provider resource; provider-specific syntax is validated at the adapter boundary.
- `SecretReference.version=None` means the provider's current version. An explicit version is immutable and pinned.
- `resolve()` returns the selected value and exact immutable provider version.
- `refresh()` always performs a new read; the v1 adapters maintain no value cache. A pinned reference remains pinned.
- `aclose()` drains in-flight requests and closes owned SDK transports and credentials. Calls after shutdown starts fail closed.

The returned value is bounded to 1 MiB and hides its bytes from `repr` and equality. Value bytes are available only through explicit reveal methods. Provider errors use a stable, sanitized class and message; adapters never forward provider messages or response bodies.

## Deliberate exclusions

There is no generic secret URI grammar, secret write/delete support, automatic rotation coordinator, process environment injection, local file provider, persistent cache, or cross-provider fallback. Those features would create additional policy and lifecycle decisions and should be proposed as separate contracts with concrete use cases.
