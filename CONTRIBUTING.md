# Contributing to orbit-secrets

Read [README](README.md), [architecture](docs/architecture/overview.md), [operations](docs/operations/README.md), and [security](docs/security/overview.md) before changing behavior. Keep changes within this package's documented boundary.

Install `.[dev]`, then run `pytest`, `ruff check src tests`, `ruff format --check src tests`, `mypy`, and `python -m build`. Add focused regression tests and update docs when public behavior or security assumptions change. Report exact Python and provider SDK versions checked. Fakes do not substitute for live-provider evidence.

Do not commit credentials, customer data, raw provider errors, local environments, or build output. Pull requests should state contract impact, validation, and remaining external gates. Contributions are licensed under Apache-2.0.
