#!/usr/bin/env python3
"""Seed both context graphs with generic, universally applicable development data.

Usage:
    python scripts/seed_context_graphs.py                        # Seed both systems
    python scripts/seed_context_graphs.py --system orchestrator  # Seed only orchestrator
    python scripts/seed_context_graphs.py --system agentic_team  # Seed only agentic team
    python scripts/seed_context_graphs.py --force                # Re-seed even if data exists
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

SEED_MARKER_TITLE = "Task: Code review and quality improvement"

# -- Shared seed data (consumed by both seeders) ----------------------------

_TASK_DEFS: list[dict[str, Any]] = [
    {
        "task_description": "Code review and quality improvement",
        "outcome": "Reviewed codebase for quality issues. Improved test coverage from 62% to 85%, "
        "resolved 14 linting warnings, and refactored 3 overly complex functions.",
        "success": True,
        "duration_ms": 3600000,
        "agents_involved": ["claude", "copilot"],
        "tags": ["quality", "code-review", "testing"],
    },
    {
        "task_description": "Documentation generation",
        "outcome": "Generated API reference docs, architecture overview, and onboarding guide. "
        "Added docstrings to 47 public functions missing documentation.",
        "success": True,
        "duration_ms": 1800000,
        "agents_involved": ["claude"],
        "tags": ["documentation", "onboarding"],
    },
    {
        "task_description": "Dependency audit and update",
        "outcome": "Audited project dependencies. Updated 12 packages with known vulnerabilities, "
        "pinned transitive versions, and removed 5 unused packages.",
        "success": True,
        "duration_ms": 2400000,
        "agents_involved": ["codex", "copilot"],
        "tags": ["dependencies", "security", "maintenance"],
    },
    {
        "task_description": "Performance profiling and optimization",
        "outcome": "Profiled application hot paths. Identified and resolved 3 bottlenecks: "
        "redundant database calls, unoptimized loops, and missing caching layer.",
        "success": True,
        "duration_ms": 5400000,
        "agents_involved": ["claude", "gemini"],
        "tags": ["performance", "profiling", "optimization"],
    },
    {
        "task_description": "Security vulnerability scan",
        "outcome": "Ran static analysis and dependency vulnerability scans. Found 2 high-severity "
        "issues (missing input validation, outdated TLS config) and 5 medium-severity warnings.",
        "success": True,
        "duration_ms": 1200000,
        "agents_involved": ["claude"],
        "tags": ["security", "scanning", "vulnerability"],
    },
]

_MISTAKE_DEFS: list[dict[str, str]] = [
    {
        "category": "unhandled_exception",
        "severity": "high",
        "message": "Uncaught exception at API boundary returned raw stack trace to client",
        "context": "Error handler was missing for a route, exposing internal details",
        "correction": "Added global error middleware returning safe, structured error responses",
        "prevention": "Wrap all API entry points in error handlers; never expose stack traces",
    },
    {
        "category": "missing_input_validation",
        "severity": "critical",
        "message": "Untrusted user input passed directly to query without validation",
        "context": "API endpoint forwarded raw user input without sanitization",
        "correction": "Added schema validation at the API boundary before processing input",
        "prevention": "Validate all external inputs at system boundaries; reject malformed data early",
    },
    {
        "category": "hardcoded_configuration",
        "severity": "high",
        "message": "Database connection string and API keys embedded in source code",
        "context": "Config values hardcoded during prototyping, never extracted",
        "correction": "Moved all config to environment variables with validation",
        "prevention": "Never hardcode config; use env vars; add pre-commit secret detection",
    },
    {
        "category": "missing_tests",
        "severity": "high",
        "message": "Deployed code change broke functionality — no tests caught it",
        "context": "Refactoring merged without test coverage caused production regression",
        "correction": "Added unit and integration tests achieving 90% branch coverage",
        "prevention": "Require test coverage thresholds in CI; block merges without tests",
    },
    {
        "category": "stale_dependencies",
        "severity": "critical",
        "message": "Production compromised via known vulnerability in outdated package",
        "context": "Dependencies not updated in 8 months; critical CVE in transitive dep",
        "correction": "Updated all deps, enabled automated vulnerability scanning",
        "prevention": "Run dependency audits in CI; enable Dependabot; schedule regular reviews",
    },
]

_PATTERN_DEFS: list[dict[str, Any]] = [
    {
        "name": "Input Validation",
        "category": "security",
        "desc": "Validate all external inputs at system boundaries. Reject malformed "
        "data before it reaches business logic. Prefer allowlists over denylists.",
        "example": "def process(data: dict) -> Response:\n"
        "    validated = schema.validate(data)\n    return handle(validated)",
        "anti": [
            "Trusting client-side validation alone",
            "Passing raw input to downstream services",
        ],
        "langs": ["python", "typescript", "go", "java"],
        "tags": ["pattern", "security", "validation"],
    },
    {
        "name": "Error Handling",
        "category": "reliability",
        "desc": "Structured error handling with context propagation. Catch at boundaries, "
        "add context, propagate or handle gracefully.",
        "example": "try:\n    result = svc.call(params)\nexcept SvcError as e:\n"
        "    log.error('failed', err=str(e))\n    raise AppError('Op failed') from e",
        "anti": ["Bare except that swallows errors", "Returning raw exceptions to users"],
        "langs": ["python", "typescript", "go", "java"],
        "tags": ["pattern", "reliability", "error-handling"],
    },
    {
        "name": "Configuration Management",
        "category": "devops",
        "desc": "Externalize config from source code. Use environment variables or "
        "config files with sensible defaults and validation.",
        "example": "import os\n\nclass Config:\n"
        "    DB_URL = os.environ.get('DB_URL', 'sqlite:///local.db')\n"
        "    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')",
        "anti": ["Hardcoded connection strings or API keys", "Different config per environment"],
        "langs": ["python", "typescript", "go"],
        "tags": ["pattern", "devops", "configuration"],
    },
    {
        "name": "Logging and Observability",
        "category": "observability",
        "desc": "Structured logging with consistent fields and correlation IDs. Emit "
        "logs as structured data for searching and aggregation.",
        "example": "log.info("
        "'request_done', correlation_id=req.id, duration_ms=elapsed, status=resp.status)",
        "anti": ["Unstructured print in production", "Logging passwords or tokens"],
        "langs": ["python", "typescript", "go", "java"],
        "tags": ["pattern", "observability", "logging"],
    },
    {
        "name": "Dependency Injection",
        "category": "architecture",
        "desc": "Decouple components by injecting dependencies rather than creating "
        "them internally. Improves testability and flexibility.",
        "example": "class OrderSvc:\n"
        "    def __init__(self, repo: OrderRepo, notifier: Notifier):\n"
        "        self._repo = repo\n        self._notifier = notifier",
        "anti": ["Hard-wiring concrete implementations", "Global singletons preventing testing"],
        "langs": ["python", "typescript", "java", "go"],
        "tags": ["pattern", "architecture", "dependency-injection"],
    },
]

_DECISION_DEFS: list[dict[str, Any]] = [
    {
        "title": "Test Before Deploy",
        "desc": "Always run the full automated test suite before deploying.",
        "rationale": "Catching regressions before deployment is far cheaper than in production.",
        "alternatives": ["Manual QA only", "Deploy then monitor", "Canary releases only"],
        "chosen": "Mandatory CI test gate before every deployment",
        "tags": ["decision", "testing", "deployment"],
    },
    {
        "title": "Semantic Versioning",
        "desc": "Follow semver for all packages and services.",
        "rationale": "Shared language for change impact; enables informed upgrade decisions.",
        "alternatives": ["Calendar versioning", "Commit-hash versioning", "No versioning"],
        "chosen": "Strict semver with automated version bumps",
        "tags": ["decision", "versioning", "releases"],
    },
    {
        "title": "Code Review Required",
        "desc": "All changes require at least one peer review before merge.",
        "rationale": "Catches bugs, shares knowledge, maintains quality, documents decisions.",
        "alternatives": ["Pair programming only", "Automated review only", "No review"],
        "chosen": "Mandatory peer review with branch protection rules",
        "tags": ["decision", "process", "quality"],
    },
]

_CONV_DEFS: list[dict[str, Any]] = [
    {
        "messages": [
            {
                "role": "user",
                "content": "We should establish coding standards. What are the essentials?",
            },
            {
                "role": "assistant",
                "content": "Start with: 1) a shared formatter, 2) a linter, "
                "3) type annotations, and 4) naming conventions. Automate via pre-commit hooks and CI.",
            },
            {
                "role": "user",
                "content": "Should we enforce these in CI or just rely on developers?",
            },
            {
                "role": "assistant",
                "content": "Enforce in CI. Automated checks remove ambiguity and "
                "prevent style debates in code reviews.",
            },
        ],
        "summary": "Establishing coding standards with automated enforcement",
        "session_id": "session-seed-001",
        "participants": ["user", "assistant"],
        "tags": ["standards", "quality", "ci"],
    },
    {
        "messages": [
            {"role": "user", "content": "What should our deployment checklist look like?"},
            {
                "role": "assistant",
                "content": "Essential checklist: 1) All tests pass, 2) No critical "
                "security findings, 3) Dependencies up to date, 4) Docs reflect changes, "
                "5) Rollback plan documented.",
            },
            {"role": "user", "content": "How do we handle rollbacks?"},
            {
                "role": "assistant",
                "content": "Deploy the previous known-good version. Use immutable "
                "artifacts so rollback is just re-deploying an older build. Test regularly.",
            },
        ],
        "summary": "Deployment checklist and rollback strategy",
        "session_id": "session-seed-002",
        "participants": ["user", "assistant"],
        "tags": ["deployment", "checklist", "rollback"],
    },
]


def _build_edges(
    EdgeType: Any,  # noqa: N803
    tasks: list[str],
    mistakes: list[str],
    patterns: list[str],
    decisions: list[str],
    convs: list[str],
) -> list[tuple[str, str, Any, float, dict[str, str]]]:
    """Build edge definitions from node ID lists."""
    t1, _, _, _, t5 = tasks
    m1, m2, m3, _, _ = mistakes
    p1, p2, p3, p4, p5 = patterns
    d1, _, d3 = decisions
    c1, c2 = convs
    return [
        (p1, m2, EdgeType.FIXED_BY, 1.0, {"context": "Validation prevents untrusted input"}),
        (
            p2,
            m1,
            EdgeType.FIXED_BY,
            1.0,
            {"context": "Error handling catches unhandled exceptions"},
        ),
        (
            p3,
            m3,
            EdgeType.FIXED_BY,
            1.0,
            {"context": "Config management eliminates hardcoded values"},
        ),
        (d1, p2, EdgeType.REFERENCES, 0.9, {"context": "Testing policy relies on error handling"}),
        (d3, p1, EdgeType.REFERENCES, 0.8, {"context": "Code review catches missing validation"}),
        (p4, m1, EdgeType.LEARNED_FROM, 0.8, {"context": "Logging adopted to diagnose errors"}),
        (
            p5,
            m3,
            EdgeType.LEARNED_FROM,
            0.7,
            {"context": "DI adopted to decouple hardcoded config"},
        ),
        (c1, t1, EdgeType.RELATED_TO, 0.9, {"context": "Standards discussion tied to review task"}),
        (c2, t5, EdgeType.RELATED_TO, 0.8, {"context": "Deploy checklist tied to security scan"}),
        (p1, p2, EdgeType.SIMILAR_TO, 0.7, {"context": "Both are defensive programming practices"}),
        (p3, p4, EdgeType.SIMILAR_TO, 0.6, {"context": "Both support operational excellence"}),
    ]


# -- Orchestrator seeding ----------------------------------------------------


def _check_orchestrator_seeded(manager: object) -> bool:
    """Return True if the orchestrator graph already contains seed data."""
    from orchestrator.context.models.schemas import NodeType

    nodes = manager.graph_store.query_nodes(node_type=NodeType.TASK, limit=200)  # type: ignore[attr-defined]
    return any(n.title == SEED_MARKER_TITLE for n in nodes)


def seed_orchestrator(force: bool = False) -> dict[str, int]:
    """Populate the orchestrator context graph with generic best-practice data."""
    try:
        from orchestrator.context import MemoryManager
        from orchestrator.context.models.schemas import EdgeType
    except ImportError as exc:
        print(f"  ⚠  Orchestrator context module unavailable: {exc}")
        return {}

    mgr = MemoryManager()
    s: dict[str, int] = dict.fromkeys(
        ["tasks", "mistakes", "patterns", "decisions", "conversations", "edges"],
        0,
    )
    try:
        if not force and _check_orchestrator_seeded(mgr):
            print("  ✓  Orchestrator graph already seeded — skipping (use --force to re-seed)")
            return s

        tasks = [mgr.store_task(**d) for d in _TASK_DEFS]
        s["tasks"] = len(tasks)

        mistakes = [
            mgr.log_mistake(
                error_type=md["category"],
                error_message=md["message"],
                context_description=md["context"],
                correction=md["correction"],
                prevention_strategy=md["prevention"],
                severity=md["severity"],
                tags=["mistake", md["category"], md["severity"]],
            )
            for md in _MISTAKE_DEFS
        ]
        s["mistakes"] = len(mistakes)

        patterns = [
            mgr.store_pattern(
                pattern_name=pd["name"],
                pattern_type=pd["category"],
                description=pd["desc"],
                examples=[pd["example"]],
                anti_patterns=pd["anti"],
                languages=pd["langs"],
                tags=pd["tags"],
            )
            for pd in _PATTERN_DEFS
        ]
        s["patterns"] = len(patterns)

        decisions = [
            mgr.store_decision(
                decision_title=dd["title"],
                decision_description=dd["desc"],
                rationale=dd["rationale"],
                alternatives_considered=dd["alternatives"],
                trade_offs=dd["chosen"],
                status="accepted",
                tags=dd["tags"],
            )
            for dd in _DECISION_DEFS
        ]
        s["decisions"] = len(decisions)

        convs = [mgr.store_conversation(**d) for d in _CONV_DEFS]
        s["conversations"] = len(convs)

        edges = _build_edges(EdgeType, tasks, mistakes, patterns, decisions, convs)
        for src, tgt, etype, w, meta in edges:
            mgr.link_nodes(source_id=src, target_id=tgt, edge_type=etype, weight=w, metadata=meta)
        s["edges"] = len(edges)
    finally:
        mgr.close()
    return s


# -- Agentic Team seeding ---------------------------------------------------


def _check_agentic_seeded(manager: object) -> bool:
    """Return True if the agentic team graph already contains seed data."""
    from agentic_team.context.models.schemas import NodeType

    nodes = manager.graph_store.query_nodes(node_type=NodeType.TASK, limit=200)  # type: ignore[attr-defined]
    return any(n.title == SEED_MARKER_TITLE for n in nodes)


def seed_agentic_team(force: bool = False) -> dict[str, int]:
    """Populate the agentic team context graph with generic best-practice data."""
    try:
        from agentic_team.context import MemoryManager
        from agentic_team.context.models.schemas import EdgeType
    except ImportError as exc:
        print(f"  ⚠  Agentic team context module unavailable: {exc}")
        return {}

    mgr = MemoryManager()
    s: dict[str, int] = dict.fromkeys(
        ["tasks", "mistakes", "patterns", "decisions", "conversations", "edges"],
        0,
    )
    try:
        if not force and _check_agentic_seeded(mgr):
            print("  ✓  Agentic team graph already seeded — skipping (use --force to re-seed)")
            return s

        tasks = [mgr.store_task(**d) for d in _TASK_DEFS]
        s["tasks"] = len(tasks)

        mistakes = [
            mgr.log_mistake(
                error_description=md["message"],
                context=md["context"],
                correction=md["correction"],
                prevention=md["prevention"],
                category=md["category"],
                severity=md["severity"],
            )
            for md in _MISTAKE_DEFS
        ]
        s["mistakes"] = len(mistakes)

        patterns = [
            mgr.store_pattern(
                name=pd["name"],
                category=pd["category"],
                description=pd["desc"],
                code_example=pd["example"],
                language="python",
                tags=pd["tags"],
            )
            for pd in _PATTERN_DEFS
        ]
        s["patterns"] = len(patterns)

        decisions = [
            mgr.store_decision(
                title=dd["title"],
                description=dd["desc"],
                rationale=dd["rationale"],
                alternatives=dd["alternatives"],
                chosen=dd["chosen"],
                tags=dd["tags"],
            )
            for dd in _DECISION_DEFS
        ]
        s["decisions"] = len(decisions)

        convs = [mgr.store_conversation(**d) for d in _CONV_DEFS]
        s["conversations"] = len(convs)

        edges = _build_edges(EdgeType, tasks, mistakes, patterns, decisions, convs)
        for src, tgt, etype, w, meta in edges:
            mgr.link_nodes(source_id=src, target_id=tgt, edge_type=etype, weight=w, metadata=meta)
        s["edges"] = len(edges)
    finally:
        mgr.close()
    return s


# -- CLI entry point ---------------------------------------------------------


def _print_summary(name: str, summary: dict[str, int]) -> None:
    """Pretty-print the seeding summary for one system."""
    total = sum(summary.values()) if summary else 0
    if total == 0:
        return
    print(f"\n  📊  {name} summary:")
    for kind, count in summary.items():
        print(f"       {kind:>15s}: {count}")
    print(f"       {'total':>15s}: {total}")


def main() -> None:
    """CLI entrypoint for seeding context graphs."""
    ap = argparse.ArgumentParser(description="Seed context graphs with generic best practices.")
    ap.add_argument(
        "--system",
        choices=["orchestrator", "agentic_team"],
        default=None,
        help="Seed only the specified system (default: both)",
    )
    ap.add_argument("--force", action="store_true", help="Re-seed even if data already exists")
    args = ap.parse_args()

    print("🌱  Context Graph Seeder")
    print("=" * 40)

    if args.system in (None, "orchestrator"):
        print("\n▶  Seeding orchestrator context graph …")
        _print_summary("Orchestrator", seed_orchestrator(force=args.force))

    if args.system in (None, "agentic_team"):
        print("\n▶  Seeding agentic team context graph …")
        _print_summary("Agentic Team", seed_agentic_team(force=args.force))

    print("\n✅  Done.")


if __name__ == "__main__":
    main()
