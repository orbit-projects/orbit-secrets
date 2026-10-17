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
"""Optional Core control-room actions for explicitly checking secret references.

Install ``orbit-secrets[control]`` to use this integration. The generated action resolves one
reference to verify provider access, but only reports the immutable version; it never returns,
prints, or persists the resolved value. Python cannot guarantee zeroization of immutable bytes,
so this action is intended for deliberate local checks, not secret consumption by applications.
"""

from __future__ import annotations

from collections.abc import Mapping

from orbit.plugins import ControlAction, ControlInput, ControlResult

from orbit_secrets.contracts import SecretError, SecretProvider, SecretReference


def secret_provider_control_actions(provider: SecretProvider) -> tuple[ControlAction, ...]:
    """Return one masked, read-only control-room action for a configured secret provider.

    The action requests a secret name and optional immutable version, resolves it using the
    provider's normal identity and authorization, then reports only the returned version. The
    caller retains ownership of ``provider`` and its lifecycle.

    Args:
        provider: An explicitly configured implementation of :class:`SecretProvider`.

    Returns:
        A single Core ``ControlAction`` suitable for a plugin's ``control_actions`` attribute.
    """
    if not isinstance(provider, SecretProvider):
        raise TypeError("provider must implement the async SecretProvider contract.")

    async def resolve_version(inputs: Mapping[str, object]) -> ControlResult:
        """Resolve one requested reference while keeping its value out of operator output."""
        name = inputs.get("name")
        version = inputs.get("version")
        if not isinstance(name, str) or not name.strip():
            return ControlResult("Secret reference is invalid.", succeeded=False)
        if version is not None and (not isinstance(version, str) or not version.strip()):
            return ControlResult("Secret reference is invalid.", succeeded=False)

        try:
            reference = SecretReference(name=name, version=version)
            value = await provider.resolve(reference)
        except SecretError as exc:
            return ControlResult(
                f"Secret lookup failed ({exc.code}). Check provider configuration and permissions.",
                succeeded=False,
            )
        except (TypeError, ValueError):
            return ControlResult("Secret reference is invalid.", succeeded=False)
        except Exception:
            return ControlResult(
                "Secret lookup failed. Check the provider's redacted logs.", succeeded=False
            )

        provider_version = value.version
        del value
        return ControlResult(
            "Secret access succeeded; the value was not displayed.",
            details=(f"Provider version: {provider_version}",),
        )

    return (
        ControlAction(
            id="resolve-version",
            title="Check secret access",
            description=(
                "Resolve one configured secret reference and show its provider version only. "
                "The secret value is never displayed."
            ),
            handler=resolve_version,
            inputs=(
                ControlInput(
                    id="name",
                    label="Secret reference",
                    kind="secret",
                    description="Provider-specific resource name; input is masked.",
                    max_length=2_048,
                ),
                ControlInput(
                    id="version",
                    label="Version (optional)",
                    kind="secret",
                    required=False,
                    description="Leave blank to check the provider's current version.",
                    max_length=256,
                ),
            ),
        ),
    )


__all__ = ["secret_provider_control_actions"]
