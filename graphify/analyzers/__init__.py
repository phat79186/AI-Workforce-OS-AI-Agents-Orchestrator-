"""Graphify analyzers — language-specific code analysis plugins."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

from graphify.core.schema import Language

if TYPE_CHECKING:
    from graphify.analyzers.base import BaseAnalyzer

__all__ = ["get_analyzer"]

_registry: dict[Language, BaseAnalyzer] | None = None
_registry_lock = threading.Lock()


def get_analyzer(language: Language) -> BaseAnalyzer | None:
    """Return the appropriate analyzer for a language, or None."""
    global _registry  # noqa: PLW0603
    if _registry is None:
        with _registry_lock:
            if _registry is None:
                from graphify.analyzers.config_analyzer import (  # pylint: disable=C0415
                    ConfigAnalyzer,
                )
                from graphify.analyzers.doc_analyzer import DocAnalyzer  # pylint: disable=C0415
                from graphify.analyzers.generic_analyzer import (  # pylint: disable=C0415
                    GenericAnalyzer,
                )
                from graphify.analyzers.javascript_analyzer import (
                    JavaScriptAnalyzer,  # pylint: disable=C0415
                )
                from graphify.analyzers.python_analyzer import (  # pylint: disable=C0415
                    PythonAnalyzer,
                )

                js_analyzer = JavaScriptAnalyzer()
                config_analyzer = ConfigAnalyzer()
                generic_analyzer = GenericAnalyzer()

                _registry = {
                    Language.PYTHON: PythonAnalyzer(),
                    Language.JAVASCRIPT: js_analyzer,
                    Language.TYPESCRIPT: js_analyzer,
                    Language.YAML: config_analyzer,
                    Language.JSON: config_analyzer,
                    Language.TOML: config_analyzer,
                    Language.DOCKERFILE: config_analyzer,
                    Language.MARKDOWN: DocAnalyzer(),
                    Language.HTML: generic_analyzer,
                    Language.CSS: generic_analyzer,
                    Language.SHELL: generic_analyzer,
                    Language.GO: generic_analyzer,
                    Language.RUST: generic_analyzer,
                    Language.JAVA: generic_analyzer,
                    Language.RUBY: generic_analyzer,
                    Language.CPP: generic_analyzer,
                    Language.C: generic_analyzer,
                    Language.CSHARP: generic_analyzer,
                    Language.SWIFT: generic_analyzer,
                    Language.KOTLIN: generic_analyzer,
                    Language.PHP: generic_analyzer,
                    Language.SQL: generic_analyzer,
                }
    return _registry.get(language)
