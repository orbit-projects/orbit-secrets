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
"""Bounded contracts for resolving and refreshing provider-managed secrets."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field, StrictStr, field_validator

MAX_SECRET_BYTES = 1_048_576
_MAX_NAME_LENGTH = 2_048
_MAX_VERSION_LENGTH = 256
_ERROR_CODE = re.compile(r"[a-z][a-z0-9-]{0,63}\Z")


def _safe_identifier(value: str, *, field_name: str, maximum: int) -> str:
    """Validate bounded provider identifiers without including values in errors."""
    if not value or len(value) > maximum or value != value.strip():
        raise ValueError(f"{field_name} must be non-empty trimmed text within its size limit.")
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise ValueError(f"{field_name} cannot contain control characters.")
    return value


class SecretReference(BaseModel):
    """Identify a secret and optionally an immutable provider version.

    ``name`` is interpreted by the selected adapter (for example, an AWS secret ARN or a
    Google Secret Manager resource name). The contract never embeds credentials in references.
    Provider-specific resource syntax is validated by the adapter that owns it.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    name: StrictStr = Field(min_length=1, max_length=_MAX_NAME_LENGTH, repr=False)
    version: StrictStr | None = Field(default=None, max_length=_MAX_VERSION_LENGTH, repr=False)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        """Reject unbounded or control-bearing resource identifiers."""
        return _safe_identifier(value, field_name="Secret name", maximum=_MAX_NAME_LENGTH)

    @field_validator("version")
    @classmethod
    def validate_version(cls, value: str | None) -> str | None:
        """Validate an optional opaque immutable provider version identifier."""
        if value is not None:
            return _safe_identifier(value, field_name="Secret version", maximum=_MAX_VERSION_LENGTH)
        return None


@dataclass(frozen=True, slots=True, repr=False)
class SecretValue:
    """Secret bytes and the immutable version from which they were resolved.

    Secret material is intentionally omitted from representation and comparison. Callers must
    explicitly invoke :meth:`reveal` to obtain bytes. Python cannot guarantee zeroization of
    immutable byte strings; keep the returned value short-lived and never log it.
    """

    _value: bytes = field(repr=False, compare=False)
    version: str

    def __post_init__(self) -> None:
        """Require bounded immutable bytes and a safe, provider-returned version string."""
        if not isinstance(self._value, bytes):
            raise TypeError("Secret values must be immutable bytes.")
        if len(self._value) > MAX_SECRET_BYTES:
            raise ValueError(f"Secret values cannot exceed {MAX_SECRET_BYTES:,} bytes.")
        if not isinstance(self.version, str):
            raise TypeError("Secret version must be text.")
        _safe_identifier(self.version, field_name="Secret version", maximum=_MAX_VERSION_LENGTH)

    def reveal(self) -> bytes:
        """Return the secret bytes; this explicit operation is the only value access path."""
        return self._value

    def reveal_text(self, *, encoding: str = "utf-8") -> str:
        """Decode secret bytes explicitly, raising a generic error for invalid text encodings."""
        if not isinstance(encoding, str) or not encoding or len(encoding) > 40:
            raise ValueError("Secret text encoding must be a valid bounded codec name.")
        try:
            return self._value.decode(encoding, errors="strict")
        except (LookupError, UnicodeDecodeError):
            raise ValueError(
                "Secret value cannot be decoded using the requested encoding."
            ) from None


class SecretError(Exception):
    """Base class for sanitized secret-provider failures."""

    code = "secret-error"
    retryable = False

    def __init__(self) -> None:
        """Use a fixed safe message so SDK diagnostics cannot leak secret contents."""
        super().__init__("Secret operation failed.")


class SecretConfigurationError(SecretError, ValueError):
    """Raised when a secret reference or adapter configuration is invalid."""

    code = "invalid-configuration"

    def __init__(self) -> None:
        Exception.__init__(self, "Secret reference or provider configuration is invalid.")


class SecretNotFoundError(SecretError):
    """Raised when the requested secret does not exist."""

    code = "not-found"

    def __init__(self) -> None:
        Exception.__init__(self, "The requested secret was not found.")


class SecretVersionNotFoundError(SecretError):
    """Raised when a requested immutable version does not exist."""

    code = "version-not-found"

    def __init__(self) -> None:
        Exception.__init__(self, "The requested secret version was not found.")


class SecretAccessDeniedError(SecretError):
    """Raised when provider identity is not authorized to read the secret."""

    code = "access-denied"

    def __init__(self) -> None:
        Exception.__init__(self, "The provider denied access to the requested secret.")


class SecretUnavailableError(SecretError):
    """Raised for retryable provider or transport failures without raw SDK details."""

    code = "provider-unavailable"
    retryable = True

    def __init__(self) -> None:
        Exception.__init__(self, "The secret provider is temporarily unavailable.")


class SecretProviderClosedError(SecretError):
    """Raised when an operation is attempted after provider shutdown begins."""

    code = "provider-closed"

    def __init__(self) -> None:
        Exception.__init__(self, "The secret provider is closed.")


class SecretOperationError(SecretError):
    """Safe fallback for non-retryable provider failures with a bounded stable code."""

    def __init__(self, code: str = "provider-failure", *, retryable: bool = False) -> None:
        """Create a generic failure without accepting provider messages or response objects."""
        if not isinstance(code, str) or _ERROR_CODE.fullmatch(code) is None:
            raise ValueError("Secret error codes must be lowercase bounded identifiers.")
        if not isinstance(retryable, bool):
            raise TypeError("retryable must be a boolean.")
        self.code = code
        self.retryable = retryable
        Exception.__init__(self, "Secret provider operation failed.")


@runtime_checkable
class SecretProvider(Protocol):
    """Asynchronous interface implemented by separately installable secret adapters.

    ``resolve`` returns the selected version, or the provider's current version when ``version``
    is omitted. ``refresh`` performs a fresh provider read of the current version and must bypass
    any adapter cache. The Core capability intentionally defines no cache or background polling.
    """

    async def resolve(self, reference: SecretReference) -> SecretValue:
        """Resolve the selected or current version of one secret."""

    async def refresh(self, reference: SecretReference) -> SecretValue:
        """Fetch the current version again, bypassing adapter-side caches."""

    async def aclose(self) -> None:
        """Release SDK clients, credentials, sockets and other provider-owned resources."""


__all__ = [
    "MAX_SECRET_BYTES",
    "SecretAccessDeniedError",
    "SecretConfigurationError",
    "SecretError",
    "SecretNotFoundError",
    "SecretOperationError",
    "SecretProvider",
    "SecretProviderClosedError",
    "SecretReference",
    "SecretUnavailableError",
    "SecretValue",
    "SecretVersionNotFoundError",
]
