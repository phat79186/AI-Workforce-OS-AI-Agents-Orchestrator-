---
paths:
  - "tests/**/*.py"
---

# Testing Rules

- Follow existing test patterns: class-based grouping (`class TestFeatureName`) or top-level functions
- Use `tmp_path` fixture for filesystem tests, not `tempfile` directly
- Mark tests needing CLI tools with `@pytest.mark.integration`
- Mark slow tests with `@pytest.mark.slow`
- Use `--override-ini="addopts="` when running pytest to skip coverage in dev
- Assert specific values, not just truthiness — `assert data["key"] == "expected"` not `assert data`
- Mock external services (CLI tools, HTTP endpoints) in unit tests
- Integration tests live in `test_functional_e2e.py` and `test_integration.py`
