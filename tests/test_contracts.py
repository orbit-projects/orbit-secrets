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
"""Input bounds, representation redaction, and stable errors for Orbit Secrets."""

import pytest
from pydantic import ValidationError

from orbit_secrets import (
    SecretAccessDeniedError,
    SecretOperationError,
    SecretReference,
    SecretValue,
)


def test_secret_reference_hides_resource_identifier_from_repr() -> None:
    reference = SecretReference(name="prod/orders/db", version="version-17")
    assert "prod/orders/db" not in repr(reference)
    assert "version-17" not in repr(reference)


@pytest.mark.parametrize("name", ["", " name", "name\n", "x" * 2049])
def test_secret_reference_rejects_invalid_identifiers(name: str) -> None:
    with pytest.raises(ValidationError):
        SecretReference(name=name)


def test_secret_value_requires_explicit_reveal_and_hides_bytes() -> None:
    value = SecretValue(b"sensitive-value", "v3")
    assert "sensitive-value" not in repr(value)
    assert value.reveal() == b"sensitive-value"
    assert value.reveal_text() == "sensitive-value"


def test_secret_value_bounds_bytes() -> None:
    with pytest.raises(ValueError, match="cannot exceed"):
        SecretValue(b"x" * (1_048_576 + 1), "v1")


def test_safe_errors_never_accept_provider_messages() -> None:
    denied = SecretAccessDeniedError()
    failure = SecretOperationError("provider-failure")
    assert "token" not in str(denied)
    assert "token" not in repr(denied)
    assert failure.code == "provider-failure"
    assert "provider detail" not in str(failure)
    with pytest.raises(ValueError):
        SecretOperationError("provider detail\naccess-token")
