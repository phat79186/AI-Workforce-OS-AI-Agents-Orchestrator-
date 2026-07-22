"""
Core orchestration logic for coordinating AI agents.
"""

import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from orchestrator.adapters import (
    BaseAdapter,
    ClaudeAdapter,
    CodexAdapter,
    CopilotAdapter,
    GeminiAdapter,
    LlamaCppAdapter,
    OllamaAdapter,
)
from orchestrator.core.task_manager import TaskManager
from orchestrator.core.workflow import WorkflowEngine, WorkflowStep
from orchestrator.resilience.fallback import FallbackManager
from orchestrator.resilience.offline import OfflineDetector


class Orchestrator:
    """Main orchestrator for coordinating AI agents."""

    def __init__(
        self,
        config_path: Optional[str] = None,
        force_offline: bool = False,
        offline_detector: Optional[OfflineDetector] = None,
    ):
        """
        Initialize the orchestrator.

        Args:
            config_path: Path to configuration file
            force_offline: If True, initialize local/offline agents only
            offline_detector: Optional detector for auto-offline mode
        """
        self.logger = logging.getLogger("orchestrator")
        self.config = self._load_config(config_path)
        self.force_offline = force_offline
        self.offline_detector = offline_detector or OfflineDetector()
        self.adapters: Dict[str, BaseAdapter] = {}
        self.workflow_engine = WorkflowEngine()
        self.task_manager = TaskManager()
        self.fallback_manager = FallbackManager(self.config, logger=self.logger)
        self.workspace_dir: Optional[Path] = None
        self.session_dir: Optional[Path] = None
        self.is_offline_mode = self._resolve_offline_mode()
        self._initialize_adapters()
        self._maybe_register_project()

    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Load configuration from file."""
        if config_path is None:
            config_path_obj: Path = Path(__file__).parent.parent / "config" / "agents.yaml"
        else:
            config_path_obj = Path(config_path)

        if not config_path_obj.exists():
            self.logger.warning("Config file not found: %s, using defaults", config_path_obj)
            return self._get_default_config()

        with open(config_path_obj, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            "agents": {
                "codex": {
                    "type": "cli",
                    "enabled": True,
                    "command": "codex",
                    "role": "implementation",
                    "timeout": 3600,
                },
                "gemini": {
                    "type": "cli",
                    "enabled": True,
                    "command": "gemini-cli",
                    "role": "review",
                    "timeout": 3600,
                },
                "claude": {
                    "type": "cli",
                    "enabled": True,
                    "command": "claude",
                    "role": "refinement",
                    "timeout": 3600,
                },
                "copilot": {
                    "type": "cli",
                    "enabled": False,
                    "command": "github-copilot-cli",
                    "role": "suggestions",
                    "timeout": 3600,
                },
                "local-code": {
                    "type": "ollama",
                    "enabled": False,
                    "model": "codellama:13b",
                    "endpoint": "http://localhost:11434",
                    "offline": True,
                    "timeout": 3600,
                },
                "local-instruct": {
                    "type": "ollama",
                    "enabled": False,
                    "model": "mistral:7b-instruct",
                    "endpoint": "http://localhost:11434",
                    "offline": True,
                    "timeout": 3600,
                },
                "local-large": {
                    "type": "llamacpp",
                    "enabled": False,
                    "endpoint": "http://localhost:8080",
                    "offline": True,
                    "timeout": 3600,
                },
            },
            "workflows": {
                "default": [
                    {"agent": "codex", "task": "implement"},
                    {"agent": "gemini", "task": "review"},
                    {"agent": "claude", "task": "refine"},
                ],
                "offline-default": [
                    {"agent": "local-code", "task": "implement"},
                    {"agent": "local-instruct", "task": "review"},
                ],
            },
            "settings": {
                "max_iterations": 3,
                "output_dir": "./output",
                "log_level": "INFO",
                "offline": {"enabled": False, "auto_detect": True},
                "fallback": {
                    "enabled": False,
                    "map": {"claude": "local-instruct", "codex": "local-code"},
                },
            },
        }

    def _resolve_offline_mode(self) -> bool:
        """Resolve offline mode from CLI force flag and config auto-detection."""
        if self.force_offline:
            return True

        offline_settings = self.config.get("settings", {}).get("offline", {})
        if isinstance(offline_settings, dict):
            if offline_settings.get("enabled", False):
                return True
            if offline_settings.get("auto_detect", False):
                return self.offline_detector.is_offline()
        return False

    def _resolve_adapter_class(self, agent_name: str, agent_config: Dict[str, Any]):
        """Resolve adapter class by explicit type first, then legacy name mapping."""
        cli_adapter_classes = {
            "codex": CodexAdapter,
            "gemini": GeminiAdapter,
            "claude": ClaudeAdapter,
            "copilot": CopilotAdapter,
        }
        cli_command_aliases = {
            "gemini-cli": "gemini",
            "github-copilot-cli": "copilot",
            "gh-copilot": "copilot",
        }
        type_adapter_classes = {
            "ollama": OllamaAdapter,
            "llamacpp": LlamaCppAdapter,
            "localai": LlamaCppAdapter,
            "text-generation-webui": LlamaCppAdapter,
            "openai-compatible": LlamaCppAdapter,
        }

        agent_type = str(agent_config.get("type", "")).strip().lower()
        if agent_type:
            if agent_type == "cli":
                provider = (
                    str(
                        agent_config.get("provider")
                        or agent_config.get("adapter")
                        or agent_name
                        or ""
                    )
                    .strip()
                    .lower()
                )
                if provider in cli_adapter_classes:
                    return cli_adapter_classes[provider]

                command_name = str(agent_config.get("command", "")).strip().lower()
                command_name = command_name.rsplit("/", maxsplit=1)[-1]
                command_name = cli_command_aliases.get(command_name, command_name)
                return cli_adapter_classes.get(command_name)

            return type_adapter_classes.get(agent_type)

        return cli_adapter_classes.get(agent_name)

    def _is_local_agent(self, agent_config: Dict[str, Any]) -> bool:
        agent_type = str(agent_config.get("type", "")).strip().lower()
        return bool(agent_config.get("offline", False)) or agent_type in {
            "ollama",
            "llamacpp",
            "localai",
            "text-generation-webui",
            "openai-compatible",
        }

    def _initialize_adapters(self):
        """Initialize all configured adapters."""
        agents_config = self.config.get("agents", {})

        for agent_name, agent_config in agents_config.items():
            if not agent_config.get("enabled", True):
                self.logger.info("Agent %s is disabled", agent_name)
                continue

            if self.is_offline_mode and not self._is_local_agent(agent_config):
                self.logger.info("Skipping non-local agent in offline mode: %s", agent_name)
                continue

            adapter_class = self._resolve_adapter_class(agent_name, agent_config)
            if adapter_class is None:
                self.logger.warning(
                    "Unknown agent type for '%s' (type=%s)",
                    agent_name,
                    agent_config.get("type"),
                )
                continue

            # Add name to config
            agent_runtime_config = dict(agent_config)
            agent_runtime_config["name"] = agent_name

            try:
                adapter = adapter_class(agent_runtime_config)  # type: ignore[abstract]

                # Check if available
                if not adapter.is_available():
                    endpoint = agent_runtime_config.get("endpoint")
                    if endpoint:
                        self.logger.warning(
                            "Agent %s is not available. Endpoint '%s' is unreachable.",
                            agent_name,
                            endpoint,
                        )
                    else:
                        self.logger.warning(
                            "Agent %s is not available. Command '%s' not found.",
                            agent_name,
                            adapter.command,
                        )
                    continue

                self.adapters[agent_name] = adapter
                self.logger.info("Initialized adapter: %s", agent_name)

            except Exception as e:
                self.logger.error("Failed to initialize %s: %s", agent_name, e)

    def execute_task(
        self, task: str, workflow_name: str = "default", max_iterations: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Execute a task using the specified workflow.

        Args:
            task: The task description
            workflow_name: Name of the workflow to use
            max_iterations: Maximum iterations (overrides config)

        Returns:
            Dictionary with execution results
        """
        execution_start = time.monotonic()
        self.logger.info("Executing task: %s", task)
        self.logger.info("Workflow: %s", workflow_name)

        # Get workflow
        workflows = self.config.get("workflows", {})

        if workflow_name == "dynamic":
            self.logger.info("Using dynamic PlannerAgent to build workflow.")
            from orchestrator.core.planner import PlannerAgent

            planner = PlannerAgent(self.adapters, self.logger)
            workflow_steps_config = planner.plan_workflow(task)
        else:
            workflow_config = workflows.get(workflow_name)
            if not workflow_config:
                if workflow_name == "default":
                    self.logger.info("Default workflow not found in config. Using dynamic planner.")
                    from orchestrator.core.planner import PlannerAgent

                    planner = PlannerAgent(self.adapters, self.logger)
                    workflow_steps_config = planner.plan_workflow(task)
                else:
                    raise ValueError(f"Workflow '{workflow_name}' not found")
            else:
                workflow_steps_config = self._extract_workflow_steps(workflow_config)

        steps = self._build_workflow_steps(workflow_steps_config)
        if not steps:
            raise ValueError(
                f"Workflow '{workflow_name}' has no executable steps "
                f"(check agent availability/offline mode)."
            )
        self.workflow_engine.set_workflow(steps)

        # Get max iterations
        if max_iterations is None:
            max_iterations = self.config.get("settings", {}).get("max_iterations", 3)

        # Resolve working directory: prefer configured output_dir, fall back to
        # the project root (parent of config/) so CLI tools run inside a valid repo.
        configured_dir = self.config.get("settings", {}).get("output_dir", "./output")
        working_dir = str(configured_dir)
        if not Path(working_dir).is_dir():
            project_root = Path(__file__).resolve().parent.parent.parent
            working_dir = str(project_root)

        # Execute workflow
        # Resolve project context
        project_id = self._resolve_project_id()

        context = {
            "task": task,
            "iteration": 0,
            "max_iterations": max_iterations,
            "working_dir": working_dir,
            "offline_mode": self.is_offline_mode,
            "project_id": project_id,
        }

        results = {
            "task": task,
            "workflow": workflow_name,
            "iterations": [],
            "final_output": None,
            "success": False,
        }

        for iteration in range(max_iterations):
            self.logger.info("\n%s", "=" * 60)
            self.logger.info("Iteration %d/%d", iteration + 1, max_iterations)
            self.logger.info("%s", "=" * 60)

            context["iteration"] = iteration

            iteration_results = self._execute_workflow_iteration(steps, context)
            results["iterations"].append(iteration_results)  # type: ignore[attr-defined]

            # Check if we should continue
            if self._should_stop_iteration(iteration_results, context):
                self.logger.info("Stopping iterations: task appears complete")
                results["success"] = True
                break

            # Update context with results
            context = self._update_context(context, iteration_results)
        else:
            # All iterations exhausted — mark success if last iteration steps all passed
            iterations_list: List[Dict[str, Any]] = results.get("iterations", [])  # type: ignore[assignment]
            last_iter = iterations_list[-1] if iterations_list else {}
            if all(s.get("success", False) for s in last_iter.get("steps", [])):
                results["success"] = True

        # Set final output
        if results["iterations"]:  # type: ignore[index]
            last_iteration = results["iterations"][-1]  # type: ignore[index]
            results["final_output"] = last_iteration.get("final_output")

        # Generate execution report if enabled
        self._maybe_generate_report(task, workflow_name, results, execution_start)

        # Store in context memory if available
        execution_time = time.monotonic() - execution_start
        self._store_task_in_context(task, workflow_name, results, execution_time)

        return results

    def _extract_workflow_steps(self, workflow_config: Any) -> List[Dict[str, Any]]:
        """Normalize workflow config to a list of step dictionaries."""
        if isinstance(workflow_config, list):
            return workflow_config
        if isinstance(workflow_config, dict):
            steps = workflow_config.get("steps", [])
            if isinstance(steps, list):
                return steps
        return []

    def _normalize_task_type(self, raw_task: Optional[str]) -> str:
        if not raw_task:
            return "implement"
        task = raw_task.strip().lower()
        role_map = {
            "implementer": "implement",
            "reviewer": "review",
            "refiner": "refine",
            "writer": "document",
            "tester": "test",
        }
        return role_map.get(task, task)

    def _build_workflow_steps(self, workflow_config: List[Dict[str, Any]]) -> List[WorkflowStep]:
        """Build workflow steps from configuration."""
        steps: List[WorkflowStep] = []

        for step_config in workflow_config:
            agent_name = step_config.get("agent")
            task_type = self._normalize_task_type(
                step_config.get("task") or step_config.get("role")
            )

            if agent_name not in self.adapters:
                self.logger.warning("Agent %s not available, skipping step", agent_name)
                continue

            step = WorkflowStep(
                agent_name=agent_name,
                task_type=task_type,
                adapter=self.adapters[agent_name],
                config=step_config,
            )
            steps.append(step)

        return steps

    def _execute_workflow_iteration(
        self, steps: List[WorkflowStep], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute one iteration of the workflow."""
        iteration_results: Dict[str, Any] = {"steps": [], "final_output": None}

        for i, step in enumerate(steps):
            self.logger.info("\nStep %d: %s - %s", i + 1, step.agent_name, step.task_type)

            try:
                task = step.build_task_description(context)
                step_context = step.build_step_context(context)

                agent_used, response, fallback_from = self.fallback_manager.execute_with_fallback(
                    primary_agent=step.agent_name,
                    adapters=self.adapters,
                    task=task,
                    context=step_context,
                    explicit_fallback=step.config.get("fallback"),
                )

                step_result = {
                    "agent": agent_used,
                    "task": step.task_type,
                    "success": response.success,
                    "output": response.output,
                    "error": response.error,
                    "files_modified": response.files_modified,
                    "suggestions": response.suggestions,
                }
                if fallback_from:
                    step_result["fallback_from"] = fallback_from

                iteration_results["steps"].append(step_result)

                # Log the result
                if response.success:
                    if fallback_from:
                        self.logger.info(
                            "✓ %s completed successfully via fallback from %s",
                            agent_used,
                            fallback_from,
                        )
                    else:
                        self.logger.info("✓ %s completed successfully", agent_used)
                    if response.suggestions:
                        self.logger.info("  Suggestions: %d", len(response.suggestions))
                else:
                    self.logger.error("✗ %s failed: %s", agent_used, response.error)

                # Update context for next step
                context["previous_output"] = response.output
                context["previous_agent"] = agent_used

                if step.task_type == "review":
                    context["feedback"] = response.output
                    context["suggestions"] = response.suggestions
                elif step.task_type == "implement":
                    context["implementation"] = response.output
                    context["files"] = response.files_modified

                iteration_results["final_output"] = response.output

            except Exception as e:
                self.logger.error("Error executing step: %s", e, exc_info=True)
                step_result = {
                    "agent": step.agent_name,
                    "task": step.task_type,
                    "success": False,
                    "output": "",
                    "error": str(e),
                    "files_modified": [],
                    "suggestions": [],
                }
                iteration_results["steps"].append(step_result)

        return iteration_results

    def _should_stop_iteration(
        self, iteration_results: Dict[str, Any], context: Dict[str, Any]
    ) -> bool:
        """Determine if we should stop iterating."""
        # Stop if all steps succeeded and no significant feedback
        all_success = all(step.get("success", False) for step in iteration_results.get("steps", []))

        # Check if review step had minimal feedback
        has_minimal_feedback = True
        for step in iteration_results.get("steps", []):
            if step.get("task") == "review":
                suggestions = step.get("suggestions", [])
                # If review has many suggestions, continue iterating
                if len(suggestions) > 3:
                    has_minimal_feedback = False

        return all_success and has_minimal_feedback

    def _update_context(
        self, context: Dict[str, Any], iteration_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update context with iteration results."""
        # Preserve iteration count
        context["iteration"] += 1

        # Keep track of all iterations
        if "all_iterations" not in context:
            context["all_iterations"] = []
        context["all_iterations"].append(iteration_results)

        return context

    def _maybe_generate_report(
        self,
        task: str,
        workflow_name: str,
        results: Dict[str, Any],
        execution_start: float,
    ) -> None:
        """Generate an execution report if create_reports is enabled in config."""
        settings = self.config.get("settings", {})
        if not settings.get("create_reports", False):
            return

        try:
            from orchestrator.observability.report_generator import ReportGenerator

            reports_dir = settings.get("reports_dir", "./reports")
            gen = ReportGenerator(reports_dir=str(reports_dir))
            duration = time.monotonic() - execution_start
            gen.generate_execution_report(
                task=task,
                workflow=workflow_name,
                results=results,
                duration_seconds=duration,
                available_agents=self.get_available_agents(),
            )
        except Exception as e:
            self.logger.warning("Failed to generate execution report: %s", e)

    def _store_task_in_context(
        self,
        task: str,
        workflow_name: str,
        results: Dict[str, Any],
        execution_time: float,
    ) -> None:
        """Store task execution in context memory for learning."""
        settings = self.config.get("settings", {})
        if not settings.get("enable_context_memory", True):
            return

        try:
            import os

            from orchestrator.context import MemoryManager

            db_path = os.environ.get(
                "ORCHESTRATOR_CONTEXT_DB", os.path.expanduser("~/.orchestrator/context.db")
            )
            os.makedirs(os.path.dirname(db_path), exist_ok=True)

            manager = MemoryManager(db_path)

            # Get agents involved
            agents_involved = []
            for iteration in results.get("iterations", []):
                for step in iteration.get("steps", []):
                    agent = step.get("agent")
                    if agent and agent not in agents_involved:
                        agents_involved.append(agent)

            # Store the task
            manager.store_task(
                task_description=task,
                outcome=str(results.get("final_output", ""))[:5000],
                success=results.get("success", False),
                duration_ms=int(execution_time * 1000),
                workflow_used=workflow_name,
                agents_involved=agents_involved,
                tags=["orchestrator"],
                project_id=self._resolve_project_id(),
            )

            self.logger.debug("Stored task in context memory")
        except ImportError:
            self.logger.debug("Context system not available")
        except Exception as e:
            self.logger.debug("Failed to store task in context: %s", e)

    def _resolve_project_id(self) -> str:
        """Resolve the active project_id from env or config.

        Returns:
            project_id string, or "" if no project configured.
        """
        import os

        project_path = os.environ.get("PROJECT_PATH", "").strip()
        if not project_path:
            project_path = self.config.get("settings", {}).get("project_path", "")
        if not project_path or not Path(project_path).is_dir():
            return ""

        try:
            from orchestrator.context.ops.project_scanner import generate_project_id

            return generate_project_id(project_path)
        except Exception:
            return ""

    def _maybe_register_project(self) -> None:
        """Register project in context graph if configured and not yet scanned."""
        import os

        project_path = os.environ.get("PROJECT_PATH", "").strip()
        if not project_path:
            project_path = self.config.get("settings", {}).get("project_path", "")
        if not project_path or not Path(project_path).is_dir():
            return

        try:
            from orchestrator.context import MemoryManager

            db_path = os.environ.get(
                "ORCHESTRATOR_CONTEXT_DB",
                os.path.expanduser("~/.orchestrator/context.db"),
            )
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            manager = MemoryManager(db_path)
            try:
                manager.register_project(project_path)
            finally:
                manager.close()
        except Exception as e:
            self.logger.debug("Failed to register project: %s", e)

    def get_relevant_context(self, task_description: str) -> Dict[str, Any]:
        """Get relevant context for a task from memory.

        Args:
            task_description: Description of the task

        Returns:
            Dictionary with relevant mistakes, patterns, and decisions
        """
        try:
            import os

            from orchestrator.context import MemoryManager

            db_path = os.environ.get(
                "ORCHESTRATOR_CONTEXT_DB", os.path.expanduser("~/.orchestrator/context.db")
            )

            if not os.path.exists(db_path):
                return {}

            manager = MemoryManager(db_path)
            try:
                return manager.get_relevant_context(task_description)
            finally:
                manager.close()
        except ImportError:
            return {}
        except Exception as e:
            self.logger.debug("Failed to get context: %s", e)
            return {}

    def get_available_agents(self) -> List[str]:
        """Get list of available agent names."""
        return list(self.adapters.keys())

    def get_workflows(self) -> List[str]:
        """Get list of available workflow names."""
        return list(self.config.get("workflows", {}).keys())
