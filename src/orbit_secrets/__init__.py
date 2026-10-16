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
"""Provider-neutral asynchronous secret access contracts for Orbit."""

from orbit_secrets.contracts import (
    MAX_SECRET_BYTES,
    SecretAccessDeniedError,
    SecretConfigurationError,
    SecretError,
    SecretNotFoundError,
    SecretOperationError,
    SecretProvider,
    SecretProviderClosedError,
    SecretReference,
    SecretUnavailableError,
    SecretValue,
    SecretVersionNotFoundError,
)

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
