---
description: Run the project test suite with optional filtering by marker or file
disable-model-invocation: false
argument-hint: [marker-or-file]
---

Run the test suite for this project.

If `$ARGUMENTS` is provided, use it as a filter:
- If it looks like a filename (contains `.py`): `python -m pytest tests/$ARGUMENTS --override-ini="addopts=" -q --timeout=30`
- If it's a marker name (unit, integration, slow, security, agentic_team): `python -m pytest tests/ --override-ini="addopts=" -q --timeout=30 -m "$ARGUMENTS"`
- Otherwise run all unit tests: `python -m pytest tests/ --override-ini="addopts=" -q --timeout=30 -m "not integration and not slow"`

Report the results: number passed, failed, and any failure details.
