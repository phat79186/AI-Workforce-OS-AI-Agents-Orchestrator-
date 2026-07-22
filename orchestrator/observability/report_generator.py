# pylint: disable=too-many-lines
"""Report generation for orchestrator executions, health, and analytics."""

import json
import logging
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("orchestrator.reports")

# ======================================================================
# Hardcoded sample data — used for seeding initial reports and demos
# ======================================================================

SAMPLE_EXECUTION_HISTORY: List[Dict[str, Any]] = [
    {
        "task": "Implement user authentication with JWT tokens",
        "workflow": "default",
        "success": True,
        "iterations": [
            {
                "steps": [
                    {
                        "agent": "codex",
                        "task": "implement",
                        "success": True,
                        "output": (
                            "Created auth module with JWT signing, token refresh,"
                            " and middleware. Files: auth.py, middleware.py,"
                            " models/user.py"
                        ),
                        "error": None,
                        "files_modified": ["auth.py", "middleware.py", "models/user.py"],
                        "suggestions": [
                            "Add rate limiting to login endpoint",
                            "Consider token blacklisting for logout",
                        ],
                    },
                    {
                        "agent": "gemini",
                        "task": "review",
                        "success": True,
                        "output": (
                            "Code follows SOLID principles."
                            " Minor: missing input validation on email field."
                        ),
                        "error": None,
                        "files_modified": [],
                        "suggestions": ["Add email validation", "Add password complexity check"],
                    },
                    {
                        "agent": "claude",
                        "task": "refine",
                        "success": True,
                        "output": (
                            "Added email validation via regex, password"
                            " complexity enforcement, and rate limiting"
                            " decorator."
                        ),
                        "error": None,
                        "files_modified": ["auth.py", "validators.py"],
                        "suggestions": [],
                    },
                ],
                "final_output": (
                    "Authentication system complete with JWT," " validation, and rate limiting."
                ),
            }
        ],
    },
    {
        "task": "Build REST API for task management with CRUD operations",
        "workflow": "default",
        "success": True,
        "iterations": [
            {
                "steps": [
                    {
                        "agent": "codex",
                        "task": "implement",
                        "success": True,
                        "output": "Created FastAPI routes for tasks CRUD with SQLAlchemy models.",
                        "error": None,
                        "files_modified": ["routes/tasks.py", "models/task.py", "schemas/task.py"],
                        "suggestions": ["Add pagination", "Add filtering by status"],
                    },
                    {
                        "agent": "gemini",
                        "task": "review",
                        "success": True,
                        "output": (
                            "Well-structured. Suggest adding error"
                            " handling for database constraints."
                        ),
                        "error": None,
                        "files_modified": [],
                        "suggestions": ["Add unique constraint handling"],
                    },
                    {
                        "agent": "claude",
                        "task": "refine",
                        "success": True,
                        "output": (
                            "Added pagination, status filtering, and"
                            " proper HTTP error codes for constraint"
                            " violations."
                        ),
                        "error": None,
                        "files_modified": ["routes/tasks.py"],
                        "suggestions": [],
                    },
                ],
                "final_output": (
                    "Task management API complete with full CRUD,"
                    " pagination, and error handling."
                ),
            }
        ],
    },
    {
        "task": "Set up CI/CD pipeline with GitHub Actions",
        "workflow": "quick",
        "success": True,
        "iterations": [
            {
                "steps": [
                    {
                        "agent": "codex",
                        "task": "implement",
                        "success": True,
                        "output": (
                            "Created .github/workflows/ci.yml with"
                            " lint, test, build, and deploy stages."
                        ),
                        "error": None,
                        "files_modified": [".github/workflows/ci.yml", "Dockerfile"],
                        "suggestions": [],
                    },
                ],
                "final_output": "CI/CD pipeline configured with 4-stage workflow.",
            }
        ],
    },
    {
        "task": "Refactor database layer to support async operations",
        "workflow": "thorough",
        "success": True,
        "iterations": [
            {
                "steps": [
                    {
                        "agent": "codex",
                        "task": "implement",
                        "success": True,
                        "output": "Migrated SQLAlchemy to async with asyncpg driver.",
                        "error": None,
                        "files_modified": [
                            "database.py",
                            "models/base.py",
                            "routes/tasks.py",
                            "routes/users.py",
                        ],
                        "suggestions": ["Add connection pooling config", "Add retry logic"],
                    },
                    {
                        "agent": "gemini",
                        "task": "review",
                        "success": True,
                        "output": (
                            "Async migration looks correct."
                            " Connection pool size should be"
                            " configurable."
                        ),
                        "error": None,
                        "files_modified": [],
                        "suggestions": [
                            "Make pool size configurable",
                            "Add health check endpoint for DB",
                        ],
                    },
                    {
                        "agent": "claude",
                        "task": "refine",
                        "success": True,
                        "output": (
                            "Added configurable pool size, health"
                            " check, and retry with exponential"
                            " backoff."
                        ),
                        "error": None,
                        "files_modified": ["database.py", "config.py", "routes/health.py"],
                        "suggestions": [],
                    },
                ],
                "final_output": (
                    "Database layer fully async with connection" " pooling and health monitoring."
                ),
            },
            {
                "steps": [
                    {
                        "agent": "codex",
                        "task": "implement",
                        "success": True,
                        "output": "Updated all remaining sync DB calls to async equivalents.",
                        "error": None,
                        "files_modified": ["services/task_service.py", "services/user_service.py"],
                        "suggestions": [],
                    },
                    {
                        "agent": "gemini",
                        "task": "review",
                        "success": True,
                        "output": (
                            "All database operations are now async." " Test coverage looks good."
                        ),
                        "error": None,
                        "files_modified": [],
                        "suggestions": [],
                    },
                    {
                        "agent": "claude",
                        "task": "refine",
                        "success": True,
                        "output": "Final polish: added type annotations and docstrings.",
                        "error": None,
                        "files_modified": ["services/task_service.py", "services/user_service.py"],
                        "suggestions": [],
                    },
                ],
                "final_output": "Async refactor complete across all service layers.",
            },
        ],
    },
    {
        "task": "Add WebSocket support for real-time notifications",
        "workflow": "default",
        "success": False,
        "iterations": [
            {
                "steps": [
                    {
                        "agent": "codex",
                        "task": "implement",
                        "success": True,
                        "output": "Created WebSocket endpoint with connection manager.",
                        "error": None,
                        "files_modified": ["websocket.py", "connection_manager.py"],
                        "suggestions": ["Add authentication to WS connections"],
                    },
                    {
                        "agent": "gemini",
                        "task": "review",
                        "success": False,
                        "output": "",
                        "error": "TimeoutError: Agent did not respond within 60s",
                        "files_modified": [],
                        "suggestions": [],
                    },
                    {
                        "agent": "claude",
                        "task": "refine",
                        "success": True,
                        "output": "Added WS auth and reconnection logic despite missing review.",
                        "error": None,
                        "files_modified": ["websocket.py"],
                        "suggestions": ["Needs full review pass"],
                    },
                ],
                "final_output": "WebSocket implemented but review step failed — needs re-review.",
            }
        ],
    },
    {
        "task": "Generate API documentation with OpenAPI spec",
        "workflow": "document",
        "success": True,
        "iterations": [
            {
                "steps": [
                    {
                        "agent": "claude",
                        "task": "document",
                        "success": True,
                        "output": (
                            "Generated comprehensive OpenAPI 3.1 spec"
                            " with examples for all endpoints."
                        ),
                        "error": None,
                        "files_modified": ["docs/openapi.yaml", "docs/README.md"],
                        "suggestions": ["Add webhook documentation"],
                    },
                    {
                        "agent": "gemini",
                        "task": "review",
                        "success": True,
                        "output": "Documentation is thorough and follows OpenAPI best practices.",
                        "error": None,
                        "files_modified": [],
                        "suggestions": [],
                    },
                ],
                "final_output": "API documentation complete with OpenAPI spec.",
            }
        ],
    },
    {
        "task": "Implement rate limiting middleware",
        "workflow": "default",
        "success": True,
        "iterations": [
            {
                "steps": [
                    {
                        "agent": "codex",
                        "task": "implement",
                        "success": False,
                        "output": "",
                        "error": "ConnectionError: API unreachable",
                        "files_modified": [],
                        "suggestions": [],
                        "fallback_from": None,
                    },
                    {
                        "agent": "gemini",
                        "task": "review",
                        "success": True,
                        "output": "Skipped — no implementation to review.",
                        "error": None,
                        "files_modified": [],
                        "suggestions": ["Need implementation first"],
                    },
                    {
                        "agent": "claude",
                        "task": "refine",
                        "success": True,
                        "output": (
                            "Implemented rate limiter with sliding"
                            " window algorithm, Redis backend, and"
                            " configurable limits per endpoint."
                        ),
                        "error": None,
                        "files_modified": ["middleware/rate_limit.py", "config.py"],
                        "suggestions": [],
                    },
                ],
                "final_output": "Rate limiting implemented via Claude after Codex failure.",
            }
        ],
    },
    {
        "task": "Add comprehensive test suite for auth module",
        "workflow": "review-only",
        "success": True,
        "iterations": [
            {
                "steps": [
                    {
                        "agent": "gemini",
                        "task": "review",
                        "success": True,
                        "output": (
                            "Auth module needs tests for: login,"
                            " register, token refresh, invalid tokens,"
                            " expired tokens, rate limiting."
                        ),
                        "error": None,
                        "files_modified": [],
                        "suggestions": [
                            "Test expired tokens",
                            "Test concurrent logins",
                            "Test brute force protection",
                        ],
                    },
                    {
                        "agent": "claude",
                        "task": "refine",
                        "success": True,
                        "output": (
                            "Created 24 test cases covering all" " auth flows including edge cases."
                        ),
                        "error": None,
                        "files_modified": ["tests/test_auth.py", "tests/conftest.py"],
                        "suggestions": [],
                    },
                ],
                "final_output": "Test suite complete with 24 test cases and 96% coverage.",
            }
        ],
    },
]

SAMPLE_DAILY_METRICS: List[Dict[str, Any]] = [
    {
        "date": "2025-03-10",
        "tasks": 12,
        "success": 11,
        "avg_duration": 34.2,
        "agents_used": {"codex": 12, "gemini": 10, "claude": 12},
    },
    {
        "date": "2025-03-11",
        "tasks": 8,
        "success": 7,
        "avg_duration": 41.5,
        "agents_used": {"codex": 8, "gemini": 8, "claude": 7},
    },
    {
        "date": "2025-03-12",
        "tasks": 15,
        "success": 14,
        "avg_duration": 28.7,
        "agents_used": {"codex": 15, "gemini": 13, "claude": 15},
    },
    {
        "date": "2025-03-13",
        "tasks": 10,
        "success": 10,
        "avg_duration": 22.1,
        "agents_used": {"codex": 10, "gemini": 10, "claude": 10},
    },
    {
        "date": "2025-03-14",
        "tasks": 18,
        "success": 16,
        "avg_duration": 38.9,
        "agents_used": {"codex": 18, "gemini": 16, "claude": 18},
    },
    {
        "date": "2025-03-15",
        "tasks": 6,
        "success": 6,
        "avg_duration": 19.3,
        "agents_used": {"codex": 6, "gemini": 6, "claude": 6},
    },
    {
        "date": "2025-03-16",
        "tasks": 4,
        "success": 4,
        "avg_duration": 25.0,
        "agents_used": {"codex": 4, "gemini": 4, "claude": 4},
    },
    {
        "date": "2025-03-17",
        "tasks": 14,
        "success": 13,
        "avg_duration": 31.4,
        "agents_used": {"codex": 14, "gemini": 12, "claude": 14},
    },
    {
        "date": "2025-03-18",
        "tasks": 20,
        "success": 18,
        "avg_duration": 36.8,
        "agents_used": {"codex": 20, "gemini": 18, "claude": 19},
    },
    {
        "date": "2025-03-19",
        "tasks": 16,
        "success": 15,
        "avg_duration": 29.5,
        "agents_used": {"codex": 16, "gemini": 14, "claude": 16},
    },
]


class ReportGenerator:
    """Generates JSON and HTML reports into the configured reports directory."""

    def __init__(self, reports_dir: str = "./reports") -> None:
        self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self._index_path = self.reports_dir / "INDEX.json"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_execution_report(
        self,
        task: str,
        workflow: str,
        results: Dict[str, Any],
        duration_seconds: float,
        available_agents: List[str],
    ) -> Path:
        """Generate a report for a single task execution."""
        now = datetime.now(timezone.utc)
        report_id = f"exec_{now.strftime('%Y%m%d_%H%M%S')}"

        step_summaries: List[Dict[str, Any]] = []
        total_suggestions = 0
        fallback_count = 0
        for iteration in results.get("iterations", []):
            for step in iteration.get("steps", []):
                total_suggestions += len(step.get("suggestions", []))
                if step.get("fallback_from"):
                    fallback_count += 1
                step_summaries.append(
                    {
                        "agent": step.get("agent"),
                        "task_type": step.get("task"),
                        "success": step.get("success", False),
                        "has_output": bool(step.get("output")),
                        "error": step.get("error"),
                        "files_modified": step.get("files_modified", []),
                        "suggestion_count": len(step.get("suggestions", [])),
                        "fallback_from": step.get("fallback_from"),
                    }
                )

        report: Dict[str, Any] = {
            "report_type": "execution_summary",
            "report_id": report_id,
            "generated_at": now.isoformat(),
            "task": task,
            "workflow": workflow,
            "success": results.get("success", False),
            "iterations": len(results.get("iterations", [])),
            "duration_seconds": round(duration_seconds, 3),
            "available_agents": available_agents,
            "total_suggestions": total_suggestions,
            "fallback_count": fallback_count,
            "steps": step_summaries,
        }

        path = self._write_report(report_id, report)
        self._update_index(report_id, "execution_summary", task[:120], path)
        return path

    def generate_health_report(self, health_results: Optional[Dict[str, Any]] = None) -> Path:
        """Generate a system health report."""
        now = datetime.now(timezone.utc)
        report_id = f"health_{now.strftime('%Y%m%d_%H%M%S')}"

        if health_results is None:
            from orchestrator.observability.health import HealthChecker

            health_results = HealthChecker().run_all_checks()

        disk = shutil.disk_usage(".")
        report: Dict[str, Any] = {
            "report_type": "system_health",
            "report_id": report_id,
            "generated_at": now.isoformat(),
            "overall_status": health_results.get("status"),
            "checks": health_results.get("checks", []),
            "system": {
                "python_version": (
                    f"{sys.version_info.major}"
                    f".{sys.version_info.minor}"
                    f".{sys.version_info.micro}"
                ),
                "platform": sys.platform,
                "disk_free_gb": round(disk.free / (1024**3), 2),
                "disk_total_gb": round(disk.total / (1024**3), 2),
            },
        }

        path = self._write_report(report_id, report)
        self._update_index(report_id, "system_health", report["overall_status"], path)
        return path

    def generate_config_audit(self, config: Dict[str, Any]) -> Path:
        """Generate a configuration audit report."""
        now = datetime.now(timezone.utc)
        report_id = f"config_{now.strftime('%Y%m%d_%H%M%S')}"

        agents = config.get("agents", {})
        workflows = config.get("workflows", {})
        settings = config.get("settings", {})

        agent_summaries = {}
        for name, cfg in agents.items():
            agent_summaries[name] = {
                "type": cfg.get("type"),
                "enabled": cfg.get("enabled", True),
                "role": cfg.get("role"),
                "command": cfg.get("command"),
                "endpoint": cfg.get("endpoint"),
                "offline": cfg.get("offline", False),
                "timeout": cfg.get("timeout"),
                "available": bool(shutil.which(cfg["command"])) if cfg.get("command") else None,
            }

        workflow_summaries = {}
        for name, wf in workflows.items():
            steps = wf if isinstance(wf, list) else wf.get("steps", [])
            workflow_summaries[name] = {
                "step_count": len(steps),
                "agents_used": [s.get("agent") for s in steps],
                "task_types": [s.get("task") or s.get("role") for s in steps],
            }

        report: Dict[str, Any] = {
            "report_type": "config_audit",
            "report_id": report_id,
            "generated_at": now.isoformat(),
            "agents": agent_summaries,
            "workflows": workflow_summaries,
            "settings": {
                "max_iterations": settings.get("max_iterations"),
                "output_dir": str(settings.get("output_dir", "")),
                "reports_dir": str(settings.get("reports_dir", "")),
                "offline_enabled": (
                    settings.get("offline", {}).get("enabled", False)
                    if isinstance(settings.get("offline"), dict)
                    else False
                ),
                "fallback_enabled": (
                    settings.get("fallback", {}).get("enabled", False)
                    if isinstance(settings.get("fallback"), dict)
                    else False
                ),
            },
            "enabled_agent_count": sum(1 for c in agents.values() if c.get("enabled", True)),
            "workflow_count": len(workflows),
        }

        path = self._write_report(report_id, report)
        self._update_index(report_id, "config_audit", f"{len(agents)} agents", path)
        return path

    def generate_agent_performance_report(
        self,
        execution_history: List[Dict[str, Any]],
    ) -> Path:
        """Generate an aggregate agent performance report from past execution results."""
        now = datetime.now(timezone.utc)
        report_id = f"perf_{now.strftime('%Y%m%d_%H%M%S')}"

        agent_stats: Dict[str, Dict[str, Any]] = {}

        for result in execution_history:
            for iteration in result.get("iterations", []):
                for step in iteration.get("steps", []):
                    agent = step.get("agent", "unknown")
                    if agent not in agent_stats:
                        agent_stats[agent] = {
                            "total_calls": 0,
                            "successes": 0,
                            "failures": 0,
                            "fallback_uses": 0,
                            "task_types": {},
                        }
                    stats = agent_stats[agent]
                    stats["total_calls"] += 1
                    if step.get("success"):
                        stats["successes"] += 1
                    else:
                        stats["failures"] += 1
                    if step.get("fallback_from"):
                        stats["fallback_uses"] += 1
                    task_type = step.get("task", "unknown")
                    stats["task_types"][task_type] = stats["task_types"].get(task_type, 0) + 1

        for stats in agent_stats.values():
            total = stats["total_calls"]
            stats["success_rate"] = round(stats["successes"] / total, 4) if total else 0.0

        report: Dict[str, Any] = {
            "report_type": "agent_performance",
            "report_id": report_id,
            "generated_at": now.isoformat(),
            "executions_analysed": len(execution_history),
            "agents": agent_stats,
        }

        path = self._write_report(report_id, report)
        self._update_index(
            report_id,
            "agent_performance",
            f"{len(agent_stats)} agents, {len(execution_history)} runs",
            path,
        )
        return path

    def generate_workflow_analytics(
        self,
        execution_history: List[Dict[str, Any]],
    ) -> Path:
        """Generate workflow-level analytics from past execution results."""
        now = datetime.now(timezone.utc)
        report_id = f"workflow_{now.strftime('%Y%m%d_%H%M%S')}"

        wf_stats: Dict[str, Dict[str, Any]] = {}

        for result in execution_history:
            wf = result.get("workflow", "unknown")
            if wf not in wf_stats:
                wf_stats[wf] = {
                    "total_runs": 0,
                    "successes": 0,
                    "failures": 0,
                    "total_iterations": 0,
                }
            stats = wf_stats[wf]
            stats["total_runs"] += 1
            if result.get("success"):
                stats["successes"] += 1
            else:
                stats["failures"] += 1
            stats["total_iterations"] += len(result.get("iterations", []))

        for stats in wf_stats.values():
            total = stats["total_runs"]
            stats["success_rate"] = round(stats["successes"] / total, 4) if total else 0.0
            stats["avg_iterations"] = round(stats["total_iterations"] / total, 2) if total else 0.0

        report: Dict[str, Any] = {
            "report_type": "workflow_analytics",
            "report_id": report_id,
            "generated_at": now.isoformat(),
            "executions_analysed": len(execution_history),
            "workflows": wf_stats,
        }

        path = self._write_report(report_id, report)
        self._update_index(
            report_id,
            "workflow_analytics",
            f"{len(wf_stats)} workflows",
            path,
        )
        return path

    def generate_html_dashboard(
        self,
        execution_history: Optional[List[Dict[str, Any]]] = None,
        daily_metrics: Optional[List[Dict[str, Any]]] = None,
    ) -> Path:
        """Generate an HTML dashboard with embedded charts from execution data."""
        if execution_history is None:
            execution_history = SAMPLE_EXECUTION_HISTORY
        if daily_metrics is None:
            daily_metrics = SAMPLE_DAILY_METRICS

        now = datetime.now(timezone.utc)
        report_id = f"dashboard_{now.strftime('%Y%m%d_%H%M%S')}"

        # Compute agent stats for charts
        agent_stats: Dict[str, Dict[str, int]] = {}
        for result in execution_history:
            for iteration in result.get("iterations", []):
                for step in iteration.get("steps", []):
                    agent = step.get("agent", "unknown")
                    if agent not in agent_stats:
                        agent_stats[agent] = {"success": 0, "failure": 0}
                    if step.get("success"):
                        agent_stats[agent]["success"] += 1
                    else:
                        agent_stats[agent]["failure"] += 1

        # Compute workflow stats
        wf_counts: Dict[str, int] = {}
        for result in execution_history:
            wf = result.get("workflow", "unknown")
            wf_counts[wf] = wf_counts.get(wf, 0) + 1

        total_tasks = len(execution_history)
        total_success = sum(1 for r in execution_history if r.get("success"))
        total_fail = total_tasks - total_success
        success_pct = round(total_success / total_tasks * 100, 1) if total_tasks else 0

        # Build chart data
        agent_names = json.dumps(list(agent_stats.keys()))
        agent_successes = json.dumps([s["success"] for s in agent_stats.values()])
        agent_failures = json.dumps([s["failure"] for s in agent_stats.values()])
        wf_labels = json.dumps(list(wf_counts.keys()))
        wf_values = json.dumps(list(wf_counts.values()))
        daily_labels = json.dumps([d["date"][-5:] for d in daily_metrics])
        daily_tasks = json.dumps([d["tasks"] for d in daily_metrics])
        daily_success = json.dumps([d["success"] for d in daily_metrics])
        daily_duration = json.dumps([d["avg_duration"] for d in daily_metrics])

        # Recent tasks table
        task_rows = ""
        for r in execution_history:
            status = "✅" if r.get("success") else "❌"
            iters = len(r.get("iterations", []))
            wf = r.get("workflow", "—")
            task_rows += (
                f"<tr><td>{status}</td><td>{r['task']}</td>"
                f"<td><code>{wf}</code></td>"
                f"<td>{iters}</td></tr>\n"
            )

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>📊 AI Orchestrator — Reports Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"></script>
<style>
  :root {{
    --bg: #0f172a; --surface: #1e293b; --border: #334155;
    --text: #e2e8f0; --muted: #94a3b8; --accent: #38bdf8;
    --green: #4ade80; --red: #f87171; --amber: #fbbf24;
    --purple: #a78bfa; --pink: #f472b6;
  }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: 'Inter', -apple-system, system-ui, sans-serif;
    background: var(--bg); color: var(--text); padding: 2rem;
  }}
  h1 {{ font-size: 1.8rem; margin-bottom: .25rem; }}
  .subtitle {{ color: var(--muted); margin-bottom: 2rem; font-size: .9rem; }}
  .grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 1.5rem; margin-bottom: 2rem;
  }}
  .card {{
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 12px; padding: 1.5rem;
  }}
  .card h3 {{
    font-size: .85rem; color: var(--muted);
    text-transform: uppercase; letter-spacing: .05em;
    margin-bottom: .5rem;
  }}
  .stat {{ font-size: 2.2rem; font-weight: 700; }}
  .stat.green {{ color: var(--green); }}
  .stat.red {{ color: var(--red); }}
  .stat.accent {{ color: var(--accent); }}
  .stat.amber {{ color: var(--amber); }}
  .chart-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(420px, 1fr));
    gap: 1.5rem; margin-bottom: 2rem;
  }}
  .chart-card {{
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 12px; padding: 1.5rem;
  }}
  .chart-card h3 {{ font-size: 1rem; margin-bottom: 1rem; }}
  canvas {{ max-height: 280px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: .9rem; }}
  th {{
    text-align: left; padding: .75rem 1rem;
    border-bottom: 2px solid var(--border);
    color: var(--muted); font-size: .8rem;
    text-transform: uppercase; letter-spacing: .05em;
  }}
  td {{ padding: .75rem 1rem; border-bottom: 1px solid var(--border); }}
  tr:hover td {{ background: rgba(56, 189, 248, .05); }}
  code {{
    background: rgba(56, 189, 248, .1); padding: 2px 6px;
    border-radius: 4px; font-size: .85rem; color: var(--accent);
  }}
  .footer {{ text-align: center; color: var(--muted); font-size: .8rem; margin-top: 3rem; }}
</style>
</head>
<body>

<h1>📊 AI Coding Tools — Reports Dashboard</h1>
<p class="subtitle">
  Generated {now.strftime('%B %d, %Y at %H:%M UTC')}
  &middot; {total_tasks} tasks analysed
</p>

<!-- KPI Cards -->
<div class="grid">
  <div class="card"><h3>📋 Total Tasks</h3><div class="stat accent">{total_tasks}</div></div>
  <div class="card"><h3>✅ Succeeded</h3><div class="stat green">{total_success}</div></div>
  <div class="card"><h3>❌ Failed</h3><div class="stat red">{total_fail}</div></div>
  <div class="card"><h3>📈 Success Rate</h3>
    <div class="stat green">{success_pct}%</div>
  </div>
  <div class="card"><h3>🤖 Active Agents</h3>
    <div class="stat accent">{len(agent_stats)}</div>
  </div>
  <div class="card"><h3>⚡ Workflows Used</h3><div class="stat amber">{len(wf_counts)}</div></div>
</div>

<!-- Charts -->
<div class="chart-grid">
  <div class="chart-card">
    <h3>📈 Daily Task Volume &amp; Success</h3>
    <canvas id="dailyChart"></canvas>
  </div>
  <div class="chart-card">
    <h3>🤖 Agent Success vs Failure</h3>
    <canvas id="agentChart"></canvas>
  </div>
  <div class="chart-card">
    <h3>⏱️ Average Duration (seconds)</h3>
    <canvas id="durationChart"></canvas>
  </div>
  <div class="chart-card">
    <h3>🔀 Workflow Distribution</h3>
    <canvas id="workflowChart"></canvas>
  </div>
</div>

<!-- Recent Tasks Table -->
<div class="chart-card">
  <h3>📋 Recent Task Executions</h3>
  <table>
    <thead><tr><th>Status</th><th>Task</th><th>Workflow</th><th>Iterations</th></tr></thead>
    <tbody>{task_rows}</tbody>
  </table>
</div>

<div class="footer">🚀 AI Coding Tools Collaborative &middot; Orchestrator Reports</div>

<script>
Chart.defaults.color = '#94a3b8';
Chart.defaults.borderColor = '#334155';
const fontOpts = {{ family: "'Inter', system-ui, sans-serif" }};

// Daily Task Volume
new Chart(document.getElementById('dailyChart'), {{
  type: 'bar',
  data: {{
    labels: {daily_labels},
    datasets: [
      {{ label: 'Total Tasks', data: {daily_tasks},
        backgroundColor: 'rgba(56,189,248,.6)',
        borderRadius: 4 }},
      {{ label: 'Succeeded', data: {daily_success},
        backgroundColor: 'rgba(74,222,128,.6)',
        borderRadius: 4 }}
    ]
  }},
  options: {{
    responsive: true,
    plugins: {{ legend: {{ labels: {{ font: fontOpts }} }} }},
    scales: {{
      y: {{ beginAtZero: true, ticks: {{ font: fontOpts }} }},
      x: {{ ticks: {{ font: fontOpts }} }}
    }}
  }}
}});

// Agent Success/Failure
new Chart(document.getElementById('agentChart'), {{
  type: 'bar',
  data: {{
    labels: {agent_names},
    datasets: [
      {{ label: 'Success', data: {agent_successes},
        backgroundColor: 'rgba(74,222,128,.7)',
        borderRadius: 4 }},
      {{ label: 'Failure', data: {agent_failures},
        backgroundColor: 'rgba(248,113,113,.7)',
        borderRadius: 4 }}
    ]
  }},
  options: {{
    responsive: true,
    plugins: {{ legend: {{ labels: {{ font: fontOpts }} }} }},
    scales: {{
      x: {{ stacked: true, ticks: {{ font: fontOpts }} }},
      y: {{ stacked: true, beginAtZero: true,
        ticks: {{ font: fontOpts }} }}
    }}
  }}
}});

// Duration Trend
new Chart(document.getElementById('durationChart'), {{
  type: 'line',
  data: {{
    labels: {daily_labels},
    datasets: [{{
      label: 'Avg Duration (s)',
      data: {daily_duration},
      borderColor: '#fbbf24',
      backgroundColor: 'rgba(251,191,36,.15)',
      fill: true,
      tension: .4,
      pointRadius: 4,
      pointBackgroundColor: '#fbbf24'
    }}]
  }},
  options: {{
    responsive: true,
    plugins: {{ legend: {{ labels: {{ font: fontOpts }} }} }},
    scales: {{
      y: {{ beginAtZero: true, ticks: {{ font: fontOpts }} }},
      x: {{ ticks: {{ font: fontOpts }} }}
    }}
  }}
}});

// Workflow Distribution
new Chart(document.getElementById('workflowChart'), {{
  type: 'doughnut',
  data: {{
    labels: {wf_labels},
    datasets: [{{
      data: {wf_values},
      backgroundColor: [
        '#38bdf8', '#4ade80', '#fbbf24',
        '#a78bfa', '#f472b6', '#fb923c'
      ],
      borderWidth: 0
    }}]
  }},
  options: {{
    responsive: true,
    plugins: {{ legend: {{
      position: 'bottom',
      labels: {{ font: fontOpts, padding: 16 }}
    }} }}
  }}
}});
</script>
</body>
</html>
"""
        path = self.reports_dir / f"{report_id}.html"
        path.write_text(html)
        logger.info("HTML dashboard written: %s", path)
        self._update_index(report_id, "html_dashboard", f"{total_tasks} tasks", path)
        return path

    def seed_reports(self, config: Optional[Dict[str, Any]] = None) -> List[Path]:
        """Generate a full set of seed reports using hardcoded sample data."""
        paths: List[Path] = []
        paths.append(self.generate_agent_performance_report(SAMPLE_EXECUTION_HISTORY))
        paths.append(self.generate_workflow_analytics(SAMPLE_EXECUTION_HISTORY))
        paths.append(self.generate_health_report())
        if config:
            paths.append(self.generate_config_audit(config))
        paths.append(self.generate_html_dashboard(SAMPLE_EXECUTION_HISTORY, SAMPLE_DAILY_METRICS))
        return paths

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _write_report(self, report_id: str, data: Dict[str, Any]) -> Path:
        path = self.reports_dir / f"{report_id}.json"
        path.write_text(json.dumps(data, indent=2, default=str) + "\n")
        logger.info("Report written: %s", path)
        return path

    def _update_index(self, report_id: str, report_type: str, summary: str, path: Path) -> None:
        index: List[Dict[str, Any]] = []
        if self._index_path.exists():
            try:
                index = json.loads(self._index_path.read_text())
            except (json.JSONDecodeError, OSError):
                index = []

        index.append(
            {
                "report_id": report_id,
                "type": report_type,
                "summary": summary,
                "file": path.name,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }
        )

        self._index_path.write_text(json.dumps(index, indent=2) + "\n")
