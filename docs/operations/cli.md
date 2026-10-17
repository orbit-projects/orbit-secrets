# Orbit CLI integration

`orbit-cli` displays control actions contributed by explicitly registered and enabled Core
plugins. This package provides an optional action helper without adding a CLI dependency to the
secret contract or discovering provider packages automatically.

Install the integration with the provider adapter and CLI:

```bash
python -m pip install 'orbit-secrets[control]' orbit-secrets-aws orbit-cli
```

Create the provider with the application's normal workload identity and attach the helper's
action to a trusted plugin:

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

Register and enable `SecretsOperations` using the application's normal Core composition. Open
that application with `orbit`, select **Check secret access**, and enter a provider-specific
resource name and optional immutable version. The fields are masked. The action uses the
provider's configured identity and permissions, returns only the resolved version, and does not
cache or persist the secret.

The example plugin owns the provider and closes it during deactivation. If the provider is shared,
its actual owner must close it through the application's established lifecycle. The helper
resolves secret bytes to verify access and then drops its local reference;
Python cannot guarantee zeroization of immutable byte strings. Use it only for deliberate local
checks, never as a substitute for application secret consumption or a remote administration API.
The CLI imports trusted local application code, so only use it with projects you trust.
