# Orbit Secrets

`orbit-secrets` defines a small asynchronous capability for resolving and refreshing versioned secret values. Provider adapters own SDKs, identity, endpoint configuration, transport, and provider-specific error translation. Core and configuration packages do not acquire cloud credentials.

```text
application
  └── orbit-secrets (SecretProvider contract)
        ├── orbit-secrets-aws
        ├── orbit-secrets-gcp
        └── orbit-secrets-azure
```

The v1 contract has no cache, watch loop, mutation API, or implicit environment-variable fallback. `resolve()` retrieves a requested immutable version or the provider's current version; `refresh()` performs a fresh provider read and bypasses adapter caches. Each returned value carries the provider version. Callers own rotation policy and must replace dependent resources safely.

## Install

```bash
python -m pip install orbit-secrets orbit-secrets-aws
```

To expose a safe provider access check in the Orbit CLI control room, install the optional Core
integration and add its action to an explicitly registered application plugin:

```bash
python -m pip install 'orbit-secrets[control]' orbit-secrets-aws orbit-cli
```

```python
from orbit.plugins import Plugin, PluginMetadata
from orbit_secrets.control import secret_provider_control_actions
from orbit_secrets_aws import AWSSecretsProvider


class SecretsOperations(Plugin):
    metadata = PluginMetadata(name="orbit-secrets-operations", version="0.1.0a1")

    def __init__(self, provider: AWSSecretsProvider) -> None:
        self._provider = provider
        self.control_actions = secret_provider_control_actions(provider)

    async def deactivate(self) -> None:
        await self._provider.aclose()
```

Register and enable the plugin in the application as usual. The CLI masks the reference inputs;
the action checks provider access and displays only the immutable version. It never displays or
persists secret bytes. The application remains responsible for provider configuration, identity,
authorization, and lifecycle cleanup. See [CLI integration](docs/operations/cli.md) for the full
example and security limits.

## Resolve a value

```python
from orbit_secrets import SecretReference
from orbit_secrets_aws import AWSSecretsProvider

provider = AWSSecretsProvider()  # standard AWS credential chain; no embedded credentials
try:
    value = await provider.resolve(SecretReference(name="prod/orders/database"))
    password = value.reveal_text()  # explicit disclosure at the use site
    await connect(password=password)
finally:
    await provider.aclose()
```

Values and references omit sensitive material from `repr`. Do not log resolved values, SDK responses, provider exception text, or request payloads. Python cannot guarantee zeroization of immutable bytes or strings. Keep revealed values short-lived and restrict their use to the component that needs them.

## Contract behavior

`SecretProvider` exposes async `resolve`, `refresh`, and `aclose`. `SecretReference.name` and optional `version` are opaque bounded identifiers interpreted by the adapter. `SecretValue` stores at most 1 MiB of immutable bytes and a bounded immutable provider version. Decode text only with `reveal_text()`. Provider errors use stable safe categories and fixed messages; retryability is explicit and raw SDK exception text is discarded. Cancellation propagates.

No secret values are persisted by this package. Adapters do not cache, retry beyond the provider SDK's explicitly bounded retry policy, or silently fall back to another identity.

## Security limits

This package cannot erase secret material after it has been revealed to application code, prevent application logging, enforce provider IAM, or verify that a deployment rotates dependent connections atomically. Use workload identity, least privilege, TLS verification, redacted diagnostics, and a documented rotation procedure. See [security guidance](docs/security/overview.md).

The [cloud-native observability example](examples/cloud-native-observability/README.md) composes
this contract with Core's ASGI lifecycle and the separate OpenTelemetry tracing, logging, and
metrics adapters. Its offline integration test checks version-only responses, provider cleanup,
trace-linked log context, and metric exemplars without cloud credentials or a collector.

## Documentation

Read [architecture](docs/architecture/overview.md), [operations](docs/operations/README.md), [security](docs/security/overview.md), and [development](docs/development/README.md).

## Development

```bash
python -m pip install -e '.[dev]'
pytest
ruff check src tests
ruff format --check src tests
mypy
python -m build
```

This package is an unpublished v0.1.0-alpha review candidate. It supports Python 3.11–3.14. No live provider or production deployment validation is implied. Licensed under Apache-2.0.
