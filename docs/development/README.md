# Development

The capability must remain provider-neutral and must not import Core, cloud SDKs, or telemetry SDKs. Add focused tests for input bounds, hidden representation, explicit disclosure, safe errors, cancellation, and protocol conformance. Do not put sample credentials in fixtures.

```bash
python -m pip install -e '.[dev]'
pytest
ruff check src tests
ruff format --check src tests
mypy
python -m build
```

Python 3.11–3.14 is the declared support range. Package builds and local tests are stabilization evidence only; hosted CI and release provenance remain separate.
