"""Neutral, dependency-free home for `warn_simulated()`.

This lives at the project root (not inside `providers/` or
`orchestrator/integrations/`) specifically so that both packages can import
it without creating a circular import: `providers/prompt_optimizer.py` is
imported by `orchestrator/integrations/openclaw_processor.py` (via
`providers.openclaw_provider`), so if `prompt_optimizer.py` imported the
warning helper from *inside* `orchestrator.integrations`, importing
`providers` first would trigger `orchestrator/integrations/__init__.py`,
which imports `openclaw_processor`, which imports back into
`providers.openclaw_provider` while it's still mid-initialization — a real
`ImportError`. Keeping this helper at the root breaks that cycle.

`orchestrator/integrations/_simulated.py` re-exports this same function so
existing `from orchestrator.integrations._simulated import warn_simulated`
imports keep working unchanged.
"""

from __future__ import annotations

import warnings


def warn_simulated(class_name: str, source_repo: str | None = None) -> None:
    """Emit a runtime warning that ``class_name`` is a simulated/mock integration.

    Args:
        class_name: Name of the class raising the warning (for a clear message).
        source_repo: Optional "org/repo" the mock is naming itself after, if any.
    """
    inspired_by = f" (named after, but not connected to, {source_repo})" if source_repo else ""
    warnings.warn(
        f"{class_name} is a SIMULATED/MOCK integration{inspired_by}. It returns "
        "illustrative hardcoded data and does NOT call any real external tool, "
        "repository, or API. Do not use its output for real decisions. See "
        "orchestrator/integrations/README.md for details.",
        category=UserWarning,
        stacklevel=3,
    )
