"""Shared helper for honestly marking integration modules as simulated/mock.

Every class in `orchestrator/integrations/` is a **local, offline stand-in**
inspired by the naming of a real external tool or GitHub repository. None of
them make a real network call, run a real external binary, or use the real
upstream project's code (a handful now run genuinely real logic — see
`orchestrator/integrations/README.md` for the current per-module status).

`warn_simulated()` emits a `UserWarning` the first time each mock engine is
instantiated, so that anyone who wires one of these into a real decision path
gets an unmissable runtime signal, not just a comment buried in the source.

The actual implementation lives in the project-root `simulated_integration_warning`
module (not here) to avoid a circular import: `providers/prompt_optimizer.py`
needs this helper too, and `providers` is itself imported by
`orchestrator/integrations/openclaw_processor.py`. This module just re-exports
it so existing `from orchestrator.integrations._simulated import warn_simulated`
call sites keep working.
"""

from __future__ import annotations

from simulated_integration_warning import warn_simulated

__all__ = ["warn_simulated"]
